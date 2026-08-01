"""Orquestador de ingestión asincrona."""

import asyncio
import logging
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.agent.language_detector import detect_language
from server.app.modules.agents_hub.ingestion.bilingual_bridge import terminos_bilingues
from server.app.modules.agents_hub.database.operational_models import (
    HubDocument,
    HubDocumentChunk,
    HubIngestionJob,
)
from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker
from server.app.modules.agents_hub.ingestion.docling_processor import DoclingProcessor
from server.app.modules.agents_hub.ingestion.hasher import hash_content
from server.app.modules.agents_hub.ingestion.markdown_utils import (
    estimate_tokens,
    extract_title_from_markdown,
)

logger = logging.getLogger(__name__)


class EmbeddingService(Protocol):
    async def embed(self, text: str) -> list[float]: ...


class StorageService(Protocol):
    async def get(self, key: str) -> bytes: ...


class ChatbotConfigProvider(Protocol):
    async def get_retrieval_mode(self, chatbot_id: uuid.UUID) -> str: ...


class IngestionWatcher:
    """Orquesta la ingestión de documentos.

    Crea/actualiza HubDocument como unidad citable canonica.
    Genera chunks solo cuando retrieval_mode == 'RAG'.
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: EmbeddingService,
        storage: StorageService | None = None,
        chatbot_provider: ChatbotConfigProvider | None = None,
    ):
        self._session = session
        self._embedding = embedding_service
        self._storage = storage
        self._chatbot_provider = chatbot_provider
        self._processor: DoclingProcessor | None = None
        # RAG.8: el chunker por defecto es el de plataforma. `_chunker_para` lo sustituye
        # por el resuelto en la cascada cuando hay chatbot; se conserva este para los
        # caminos que no lo tienen (subidas temporales) y para no romper a quien lo use.
        self.chunker = MarkdownChunker()
        # Keep legacy attribute for backward compatibility
        self.session = session
        self.embedding_service = embedding_service

    async def _get_processor(self) -> DoclingProcessor:
        if self._processor is None:
            self._processor = await asyncio.to_thread(DoclingProcessor)
        return self._processor

    async def process_source(
        self,
        source_url: str,
        chatbot_id: uuid.UUID,
        language: str | None = None,
        citation_url: str | None = None,
        prefetched_content: str | None = None,
        title: str | None = None,
        crawled_page_id: uuid.UUID | None = None,
    ) -> tuple[HubDocument, int]:
        """Crea/actualiza un HubDocument. Genera chunks SOLO si retrieval_mode == 'RAG'.

        Returns:
            (HubDocument, chunks_created_count) — idempotente por content_hash.
        """
        if prefetched_content is not None:
            content = prefetched_content
        else:
            processor = await self._get_processor()
            content = await asyncio.to_thread(processor.process, source_url)

        if language is None:
            language = detect_language(content)
        content_hash = hash_content(content)
        canonical = citation_url or source_url
        doc_title = title or extract_title_from_markdown(content) or canonical
        token_count = estimate_tokens(content)

        # Idempotencia: mismo chatbot + mismo hash → actualizar sin rechunkear
        existing = await self._session.execute(
            select(HubDocument).where(
                HubDocument.chatbot_id == chatbot_id,
                HubDocument.content_hash == content_hash,
            ).limit(1)
        )
        doc = existing.scalar_one_or_none()
        if doc:
            doc.canonical_url = canonical
            doc.title = doc_title
            doc.updated_at = datetime.now(timezone.utc)
            if crawled_page_id is not None:
                doc.crawled_page_id = crawled_page_id
        else:
            # Si ya existia un documento con esta URL e idioma → reemplazar.
            # Idiomas distintos de la misma URL coexisten sin borrarse mutuamente.
            old_result = await self._session.execute(
                select(HubDocument).where(
                    HubDocument.chatbot_id == chatbot_id,
                    HubDocument.canonical_url == canonical,
                    HubDocument.language == language,
                )
            )
            for old_doc in old_result.scalars():
                await self._session.execute(
                    delete(HubDocumentChunk).where(
                        HubDocumentChunk.document_id == old_doc.id
                    )
                )
                await self._session.delete(old_doc)

            source_kind = (
                "crawler"
                if source_url.startswith(("http://", "https://"))
                else "upload"
            )
            doc = HubDocument(
                chatbot_id=chatbot_id,
                title=doc_title,
                canonical_url=canonical,
                markdown_content=content,
                content_hash=content_hash,
                language=language,
                source_kind=source_kind,
                token_count=token_count,
                crawled_page_id=crawled_page_id,
            )
            self._session.add(doc)
            try:
                # Savepoint: si falla por clave duplicada solo se revierte el savepoint,
                # no la transacción exterior (que mantiene el job válido).
                async with self._session.begin_nested():
                    await self._session.flush()
            except IntegrityError:
                # Dos jobs concurrentes procesaron el mismo contenido: usar el existente.
                # Tras el rollback del savepoint, doc puede estar ya desvinculado.
                try:
                    self._session.expunge(doc)
                except Exception:
                    pass
                existing_dup = await self._session.execute(
                    select(HubDocument).where(
                        HubDocument.chatbot_id == chatbot_id,
                        HubDocument.content_hash == content_hash,
                    ).limit(1)
                )
                doc = existing_dup.scalar_one()
                return doc, 0

        # Chunking + embedding solo si el chatbot está en modo vector
        retrieval_mode = (
            await self._chatbot_provider.get_retrieval_mode(chatbot_id)
            if self._chatbot_provider
            else "RAG"
        )
        n_chunks = 0
        if retrieval_mode == "RAG":
            n_chunks = await self._regenerate_chunks_for_document(doc)
        else:
            # Limpiar chunks previos si el modo cambió
            await self._session.execute(
                delete(HubDocumentChunk).where(HubDocumentChunk.document_id == doc.id)
            )

        await self._session.commit()
        return doc, n_chunks

    async def _chunker_para(self, chatbot_id: uuid.UUID) -> MarkdownChunker:
        """Chunker con los parámetros resueltos en la cascada (RAG.8).

        Antes se instanciaba con los defaults del código, así que la configuración por
        chatbot no existía: el admin podía cambiar `chunk_size` en la API y no pasaba nada.
        Si la cascada no responde —chatbot inexistente, o llamada fuera de contexto—, se
        usa el chunker de plataforma en vez de reventar la ingesta por un dato de tuning.
        """
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            get_effective_public_graph_config,
        )

        try:
            cfg = await get_effective_public_graph_config(chatbot_id, self._session)
            return MarkdownChunker(
                chunk_size=int(cfg.chunk_size),
                chunk_overlap=int(cfg.chunk_overlap),
                strategy=str(cfg.chunking_strategy),
            )
        except Exception:  # pragma: no cover - la ingesta no cae por la config de troceado
            logger.warning(
                "No se pudo resolver la config de troceado; se usa la de plataforma"
            )
            return self.chunker

    async def _embed_en_lote(self, textos: list[str]) -> list[list[float]]:
        """Embebe una lista, usando el lote del servicio si lo expone."""
        if not textos:
            return []
        en_lote = getattr(self._embedding, "embed_batch", None)
        if en_lote is not None:
            return await en_lote(textos)
        return [await self._embedding.embed(t) for t in textos]

    async def _regenerate_chunks_for_document(self, doc: HubDocument) -> int:
        """Borra los chunks del documento y los regenera. Devuelve el numero creado."""
        await self._session.execute(
            delete(HubDocumentChunk).where(HubDocumentChunk.document_id == doc.id)
        )
        chunker = await self._chunker_para(doc.chatbot_id)
        chunks = chunker.split(
            doc.markdown_content,
            metadata={
                "document_id": str(doc.id),
                "source_url": doc.canonical_url,
            },
            # RAG.7: el título encabeza el texto que se embebe, no el que se almacena.
            document_title=doc.title,
        )
        terminos = terminos_bilingues(doc)
        # MOD.1: la procedencia se graba CON el vector. Sin ella, cambiar de modelo es una
        # avería silenciosa; con ella, `assert_embedding_space_matches` puede detectarla.
        modelo = getattr(self._embedding, "model_name", None)
        dimension = getattr(self._embedding, "dimensions", None)
        # RAG.7: se embebe `embedding_text` —jerarquía + contenido—, no el contenido crudo.
        # Y por LOTES cuando el servicio lo soporta: el watcher iba chunk a chunk, o sea una
        # llamada por fragmento, que con un proveedor por API es una ida y vuelta de red por
        # cada uno. `embed` suelto se conserva para los servicios que no expongan lote.
        vectores = await self._embed_en_lote([ch.embedding_text for ch in chunks])
        for ch, embedding in zip(chunks, vectores):
            self._session.add(HubDocumentChunk(
                chatbot_id=doc.chatbot_id,
                document_id=doc.id,
                content=ch.content,
                source_url=doc.canonical_url,
                content_hash=hash_content(ch.content),
                embedding=embedding,
                chunk_metadata={**ch.metadata, "document_id": str(doc.id)},
                language=doc.language,
                bilingual_terms=terminos,
                embedding_model=modelo,
                embedding_dim=dimension,
                parent_content=ch.parent_content or None,
            ))
        return len(chunks)

    async def process_user_upload(
        self,
        source_url: str,
        chatbot_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> list[HubDocumentChunk]:
        """Procesa un documento subido por un usuario (siempre re-procesa, marca como temporal)."""
        def _process() -> str:
            return DoclingProcessor().process(source_url)

        content = await asyncio.to_thread(_process)
        language = detect_language(content)
        chunks = self.chunker.split(content, metadata={"source_url": source_url})
        created_chunks = []

        for chunk in chunks:
            embedding = await self._embedding.embed(chunk.content)
            db_chunk = HubDocumentChunk(
                chatbot_id=chatbot_id,
                content=chunk.content,
                source_url=source_url,
                content_hash=hash_content(chunk.content),
                embedding=embedding,
                chunk_metadata=chunk.metadata,
                language=language,
                is_temporary=True,
                owner_id=owner_id,
            )
            self._session.add(db_chunk)
            created_chunks.append(db_chunk)

        await self._session.commit()
        return created_chunks

    async def run_job(
        self,
        job_id: uuid.UUID,
        prefetched_content: str | None = None,
    ) -> None:
        """Ejecuta un job de ingestión."""
        job = await self._session.get(HubIngestionJob, job_id)
        if not job:
            return

        job.status = "running"
        await self._session.commit()

        tmp_path: str | None = None
        error: Exception | None = None
        try:
            source_for_docling = job.source_url
            citation_url = job.canonical_url

            if self._storage and not job.source_url.startswith(("http://", "https://")):
                pdf_bytes = await self._storage.get(job.source_url)
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(pdf_bytes)
                    tmp_path = tmp.name
                source_for_docling = tmp_path
                if not citation_url:
                    citation_url = job.source_url  # storage key como identificador canónico

            filename_hint = Path(job.original_filename).stem if job.original_filename else None
            doc, n_chunks = await self.process_source(
                source_for_docling,
                job.chatbot_id,
                citation_url=citation_url,
                prefetched_content=prefetched_content,
                language=job.language,
                title=filename_hint,
            )
            job.status = "completed"
            job.chunks_processed = n_chunks
        except Exception as e:
            logger.error("Job %s falló: %s", job_id, e, exc_info=True)
            error = e
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)

        if error is not None:
            try:
                await self._session.rollback()
                job = await self._session.get(HubIngestionJob, job_id)
                if job:
                    job.status = "failed"
                    job.error_message = str(error)
                    await self._session.commit()
            except Exception as save_err:
                logger.error("No se pudo guardar el estado 'failed' del job %s: %s", job_id, save_err, exc_info=True)
        else:
            await self._session.commit()


async def cleanup_temporary_chunks(session: AsyncSession, ttl_hours: int = 24) -> int:
    """Elimina chunks temporales que han superado el TTL."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
    result = await session.execute(
        select(HubDocumentChunk).where(HubDocumentChunk.is_temporary)
    )
    deleted = 0
    for chunk in result.scalars():
        if chunk.is_temporary and chunk.created_at < cutoff:
            await session.delete(chunk)
            deleted += 1
    await session.commit()
    return deleted

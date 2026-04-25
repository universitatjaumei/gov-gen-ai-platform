"""Orquestador de ingestión asíncrona."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.operational_models import (
    HubDocumentChunk,
    HubIngestionJob,
)
from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker
from server.app.modules.agents_hub.ingestion.docling_processor import DoclingProcessor
from server.app.modules.agents_hub.ingestion.hasher import hash_content


class EmbeddingService(Protocol):
    """Protocolo para servicio de embeddings."""

    async def embed(self, text: str) -> list[float]: ...


class IngestionWatcher:
    """Orquesta la ingestión de documentos."""

    def __init__(self, session: AsyncSession, embedding_service: EmbeddingService):
        self.session = session
        self.embedding_service = embedding_service
        self._processor: DoclingProcessor | None = None
        self.chunker = MarkdownChunker()

    async def _get_processor(self) -> DoclingProcessor:
        if self._processor is None:
            self._processor = await asyncio.to_thread(DoclingProcessor)
        return self._processor

    async def process_source(
        self,
        source_url: str,
        chatbot_id: uuid.UUID,
        language: str = "es",
        citation_url: str | None = None,
        prefetched_content: str | None = None,
    ) -> list[HubDocumentChunk]:
        """Procesa una fuente y crea chunks.

        Args:
            source_url: Ruta física o URL al documento (usado para leer el archivo)
            chatbot_id: ID del chatbot
            language: Idioma del documento
            citation_url: URL pública canónica para citar la fuente en el chat.
                Si se proporciona, se almacena en los chunks en lugar de source_url.
                También se usa como clave de deduplicación.
            prefetched_content: Contenido ya procesado a Markdown (evita un segundo
                fetch cuando el llamador ya tiene el contenido, p.ej. el scheduler).
        """
        if prefetched_content is not None:
            content = prefetched_content
        else:
            processor = await self._get_processor()
            content = await asyncio.to_thread(processor.process, source_url)
        content_hash = hash_content(content)
        chunk_source = citation_url or source_url

        # Verificar si ya existe con el mismo hash
        existing = await self.session.execute(
            select(HubDocumentChunk)
            .where(HubDocumentChunk.source_url == chunk_source)
            .where(HubDocumentChunk.content_hash == content_hash)
            .limit(1)
        )
        if existing.scalar_one_or_none():
            return []

        # Eliminar chunks antiguos de esta fuente
        old_chunks = await self.session.execute(
            select(HubDocumentChunk).where(HubDocumentChunk.source_url == chunk_source)
        )
        for chunk in old_chunks.scalars():
            await self.session.delete(chunk)

        # Crear nuevos chunks
        chunks = self.chunker.split(content, metadata={"source_url": chunk_source})
        created_chunks = []

        for chunk in chunks:
            embedding = await self.embedding_service.embed(chunk.content)
            db_chunk = HubDocumentChunk(
                chatbot_id=chatbot_id,
                content=chunk.content,
                source_url=chunk_source,
                content_hash=hash_content(chunk.content),
                embedding=embedding,
                chunk_metadata=chunk.metadata,
                language=language,
            )
            self.session.add(db_chunk)
            created_chunks.append(db_chunk)

        await self.session.commit()
        return created_chunks

    async def process_user_upload(
        self,
        source_url: str,
        chatbot_id: uuid.UUID,
        owner_id: uuid.UUID,
        language: str = "es",
    ) -> list[HubDocumentChunk]:
        """Procesa un documento subido por un usuario (siempre re-procesa, marca como temporal).

        Args:
            source_url: URL o ruta al documento
            chatbot_id: ID del chatbot
            owner_id: ID del usuario propietario
            language: Idioma del documento

        Returns:
            Lista de chunks creados
        """
        processor = await self._get_processor()
        content = await asyncio.to_thread(processor.process, source_url)
        chunks = self.chunker.split(content, metadata={"source_url": source_url})
        created_chunks = []

        for chunk in chunks:
            embedding = await self.embedding_service.embed(chunk.content)
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
            self.session.add(db_chunk)
            created_chunks.append(db_chunk)

        await self.session.commit()
        return created_chunks

    async def run_job(
        self,
        job_id: uuid.UUID,
        prefetched_content: str | None = None,
    ) -> None:
        """Ejecuta un job de ingestión.

        Args:
            job_id: ID del job
            prefetched_content: Contenido ya procesado (opcional; lo usa el scheduler
                para evitar un segundo fetch cuando ya obtuvo el Markdown para comparar el hash).
        """
        job = await self.session.get(HubIngestionJob, job_id)
        if not job:
            return

        job.status = "running"
        await self.session.commit()

        try:
            chunks = await self.process_source(
                job.source_url,
                job.chatbot_id,
                citation_url=job.canonical_url,
                prefetched_content=prefetched_content,
            )
            job.status = "completed"
            job.chunks_processed = len(chunks)
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)

        await self.session.commit()


async def cleanup_temporary_chunks(session: AsyncSession, ttl_hours: int = 24) -> int:
    """Elimina chunks temporales que han superado el TTL.

    Args:
        session: Sesión de base de datos
        ttl_hours: Horas de vida de los chunks temporales

    Returns:
        Número de chunks eliminados
    """
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

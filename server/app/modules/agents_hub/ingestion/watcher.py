"""Orquestador de ingestión asíncrona."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.models import HubDocumentChunk, HubIngestionJob
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
        self.processor = DoclingProcessor()
        self.chunker = MarkdownChunker()

    async def process_source(
        self,
        source_url: str,
        chatbot_id: uuid.UUID,
        language: str = "es",
    ) -> list[HubDocumentChunk]:
        """Procesa una fuente y crea chunks.

        Args:
            source_url: URL o ruta al documento
            chatbot_id: ID del chatbot
            language: Idioma del documento

        Returns:
            Lista de chunks creados
        """
        content = self.processor.process(source_url)
        content_hash = hash_content(content)

        # Verificar si ya existe con el mismo hash
        existing = await self.session.execute(
            select(HubDocumentChunk)
            .where(HubDocumentChunk.source_url == source_url)
            .where(HubDocumentChunk.content_hash == content_hash)
            .limit(1)
        )
        if existing.scalar_one_or_none():
            return []

        # Eliminar chunks antiguos de esta fuente
        old_chunks = await self.session.execute(
            select(HubDocumentChunk).where(HubDocumentChunk.source_url == source_url)
        )
        for chunk in old_chunks.scalars():
            await self.session.delete(chunk)

        # Crear nuevos chunks
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
        content = self.processor.process(source_url)
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

    async def run_job(self, job_id: uuid.UUID) -> None:
        """Ejecuta un job de ingestión.

        Args:
            job_id: ID del job
        """
        job = await self.session.get(HubIngestionJob, job_id)
        if not job:
            return

        job.status = "running"
        await self.session.commit()

        try:
            chunks = await self.process_source(job.source_url, job.chatbot_id)
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
        select(HubDocumentChunk).where(HubDocumentChunk.is_temporary == True)
    )
    deleted = 0
    for chunk in result.scalars():
        if chunk.is_temporary and chunk.created_at < cutoff:
            await session.delete(chunk)
            deleted += 1
    await session.commit()
    return deleted

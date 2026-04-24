"""Router de administración (Hub) para la ingestión de documentos.

Deploy: cloud
"""

import tempfile
import uuid
from pathlib import Path
from typing import List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user
from server.app.core.auth import UserInfo
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.database.operational_models import (
    HubDocumentChunk,
    HubIngestionJob,
)
from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher

router = APIRouter(prefix="/hub/ingestion", tags=["hub-ingestion"])


class _NoOpEmbeddingService:
    """Placeholder — se reemplaza por el LLM Gateway en Fase 4."""

    async def embed(self, text: str) -> list[float]:
        return [0.0] * 1536


@router.get("/{chatbot_id}/jobs")
async def get_ingestion_jobs(
    chatbot_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
):
    """Obtiene los trabajos de ingestión de un chatbot."""
    # TODO: Validar que el usuario tiene acceso al chatbot (Cloud logic)
    stmt = (
        select(HubIngestionJob)
        .where(HubIngestionJob.chatbot_id == chatbot_id)
        .order_by(HubIngestionJob.created_at.desc())
    )
    result = await session.execute(stmt)
    jobs = result.scalars().all()
    return {"jobs": jobs}


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    chatbot_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
):
    """Sube un documento y lanza su ingestión en background."""
    if file.content_type not in ("application/pdf",):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo se admiten archivos PDF.",
        )

    # Validar tamaño del archivo (10 MB = 10 * 1024 * 1024 bytes)
    # UploadFile no provee un content_length exacto sin leer, así que leemos y limitamos.
    max_size = 10 * 1024 * 1024
    content = await file.read(max_size + 1)
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo supera el límite de 10 MB.",
        )

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    # Crear el Job
    job = HubIngestionJob(
        chatbot_id=chatbot_id,
        source_url=tmp_path,  # Local temporal, en produccion sería un S3 uri
        status="pending",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Lanzar tarea en background
    async def process_job(job_id: uuid.UUID, file_path: str):
        # Necesitamos una nueva sesión para la tarea en background
        # Usamos el generador manual
        async for bg_session in get_async_session():
            try:
                watcher = IngestionWatcher(
                    session=bg_session,
                    embedding_service=_NoOpEmbeddingService(),
                )
                await watcher.run_job(job_id)
            finally:
                Path(file_path).unlink(missing_ok=True)

    background_tasks.add_task(process_job, job.id, tmp_path)

    return {"job": job, "message": "Documento subido y encolado."}


@router.delete("/{chatbot_id}/chunks", status_code=status.HTTP_200_OK)
async def clear_chatbot_collection(
    chatbot_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
):
    """Elimina todos los chunks y jobs de un chatbot."""
    # Buscar chunks y eliminarlos
    chunks_stmt = select(HubDocumentChunk).where(
        HubDocumentChunk.chatbot_id == chatbot_id
    )
    result = await session.execute(chunks_stmt)
    chunks = result.scalars().all()
    for chunk in chunks:
        await session.delete(chunk)

    # Buscar jobs y eliminarlos
    jobs_stmt = select(HubIngestionJob).where(HubIngestionJob.chatbot_id == chatbot_id)
    result = await session.execute(jobs_stmt)
    jobs = result.scalars().all()
    for job in jobs:
        # Si el documento temporal aún existe, intentamos borrarlo
        Path(job.source_url).unlink(missing_ok=True)
        await session.delete(job)

    await session.commit()

    return {
        "message": "Colección vaciada correctamente.",
        "chunks_deleted": len(chunks),
        "jobs_deleted": len(jobs),
    }

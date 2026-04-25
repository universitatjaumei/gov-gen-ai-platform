"""Router de administración (Hub) para la ingestión de documentos.

Deploy: cloud
"""

import tempfile
import uuid
from pathlib import Path
from typing import Literal

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
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user
from server.app.core.auth import UserInfo
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.database.operational_models import (
    HubDocumentChunk,
    HubIngestionJob,
    HubIngestionSource,
)
from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher
from server.app.modules.agents_hub.services.embedding_service import get_embedding_service


class IngestionSourceCreate(BaseModel):
    url: str
    label: str | None = None
    check_interval_hours: int = Field(24, ge=1, le=168)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("La URL debe empezar por http:// o https://")
        return v


class IngestionSourceUpdate(BaseModel):
    label: str | None = None
    check_interval_hours: int | None = Field(None, ge=1, le=168)
    status: Literal["active", "paused"] | None = None

router = APIRouter(prefix="/hub/ingestion", tags=["hub-ingestion"])


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
    canonical_url: str | None = Form(None),
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
        original_filename=file.filename,
        canonical_url=canonical_url or None,
        status="pending",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Lanzar tarea en background
    async def process_job(job_id: uuid.UUID, file_path: str):
        async for bg_session in get_async_session():
            try:
                watcher = IngestionWatcher(
                    session=bg_session,
                    embedding_service=get_embedding_service(),
                )
                await watcher.run_job(job_id)
            finally:
                Path(file_path).unlink(missing_ok=True)

    background_tasks.add_task(process_job, job.id, tmp_path)

    return {"job": job, "message": "Documento subido y encolado."}


@router.delete("/{chatbot_id}/jobs/{job_id}", status_code=status.HTTP_200_OK)
async def delete_ingestion_job(
    chatbot_id: uuid.UUID,
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
):
    """Elimina un job de ingestión y todos sus chunks asociados."""
    job = await session.get(HubIngestionJob, job_id)
    if not job or job.chatbot_id != chatbot_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job no encontrado.")

    if job.status in ("pending", "running"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar un job en curso.",
        )

    chunks_stmt = select(HubDocumentChunk).where(
        HubDocumentChunk.chatbot_id == chatbot_id,
        HubDocumentChunk.source_url == job.source_url,
    )
    result = await session.execute(chunks_stmt)
    chunks = result.scalars().all()
    for chunk in chunks:
        await session.delete(chunk)

    Path(job.source_url).unlink(missing_ok=True)
    await session.delete(job)
    await session.commit()

    return {"message": "Documento eliminado.", "chunks_deleted": len(chunks)}


# ── Fuentes web monitorizadas ──────────────────────────────────────────────────

@router.get("/{chatbot_id}/sources", status_code=status.HTTP_200_OK)
async def list_sources(
    chatbot_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
):
    """Lista las fuentes web monitorizadas de un chatbot."""
    result = await session.execute(
        select(HubIngestionSource)
        .where(HubIngestionSource.chatbot_id == chatbot_id)
        .order_by(HubIngestionSource.created_at.desc())
    )
    return {"sources": result.scalars().all()}


@router.post("/{chatbot_id}/sources", status_code=status.HTTP_201_CREATED)
async def create_source(
    chatbot_id: uuid.UUID,
    body: IngestionSourceCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
):
    """Añade una URL a monitorizar para un chatbot."""
    existing = await session.execute(
        select(HubIngestionSource).where(
            HubIngestionSource.chatbot_id == chatbot_id,
            HubIngestionSource.url == body.url,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esta URL ya está registrada para este chatbot.",
        )
    source = HubIngestionSource(
        chatbot_id=chatbot_id,
        url=body.url,
        label=body.label,
        check_interval_hours=body.check_interval_hours,
    )
    session.add(source)
    await session.commit()
    await session.refresh(source)
    return {"source": source}


@router.patch("/{chatbot_id}/sources/{source_id}", status_code=status.HTTP_200_OK)
async def update_source(
    chatbot_id: uuid.UUID,
    source_id: uuid.UUID,
    body: IngestionSourceUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
):
    """Actualiza etiqueta, intervalo o estado (active/paused) de una fuente."""
    source = await session.get(HubIngestionSource, source_id)
    if not source or source.chatbot_id != chatbot_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fuente no encontrada.")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(source, key, value)
    await session.commit()
    await session.refresh(source)
    return {"source": source}


@router.delete("/{chatbot_id}/sources/{source_id}", status_code=status.HTTP_200_OK)
async def delete_source(
    chatbot_id: uuid.UUID,
    source_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
):
    """Elimina una fuente monitorizada (no borra los chunks ya ingestados)."""
    source = await session.get(HubIngestionSource, source_id)
    if not source or source.chatbot_id != chatbot_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fuente no encontrada.")
    await session.delete(source)
    await session.commit()
    return {"message": "Fuente eliminada."}


@router.post("/{chatbot_id}/sources/{source_id}/check", status_code=status.HTTP_202_ACCEPTED)
async def trigger_source_check(
    chatbot_id: uuid.UUID,
    source_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
):
    """Fuerza una comprobación inmediata de una fuente en background."""
    source = await session.get(HubIngestionSource, source_id)
    if not source or source.chatbot_id != chatbot_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fuente no encontrada.")
    if source.status == "paused":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La fuente está pausada. Reactívala antes de comprobar.",
        )

    async def do_check() -> None:
        from server.app.modules.agents_hub.ingestion.source_scheduler import check_source
        async for bg_session in get_async_session():
            await check_source(source_id, bg_session)

    background_tasks.add_task(do_check)
    return {"message": "Comprobación iniciada."}


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

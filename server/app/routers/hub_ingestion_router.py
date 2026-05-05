"""Router de administración (Hub) para la ingestión de documentos.

Deploy: cloud
"""

import uuid
from typing import Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user
from server.app.core.auth import UserInfo
from server.app.core.storage import FsspecStorageService, get_storage_service
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.database.operational_models import (
    HubDocument,
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
    language: str | None = None
    spider_type: str | None = "generic"
    config_json: dict = Field(default_factory=dict)

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


class AnalyzeHtmlRequest(BaseModel):
    html: str
    url_hint: str = ""


router = APIRouter(prefix="/hub/ingestion", tags=["hub-ingestion"])


async def _get_llm_service(session: AsyncSession = Depends(get_async_session)):
    from server.app.modules.agents_hub.services.config_provider import LocalConfigProvider
    from server.app.modules.agents_hub.services.model_factory import get_model_for_tier
    from server.app.modules.agents_hub.services.html_analyzer_service import LangChainLLMAdapter

    provider = LocalConfigProvider(session)
    model = await get_model_for_tier(1, provider)
    return LangChainLLMAdapter(model)


@router.post("/analyze-html", status_code=status.HTTP_200_OK)
async def analyze_html(
    body: AnalyzeHtmlRequest,
    current_user: UserInfo = Depends(get_current_user),
    llm_service=Depends(_get_llm_service),
):
    """Propone selectores CSS para el contenido principal de un HTML institucional.

    Deploy: cloud
    """
    from server.app.modules.agents_hub.services.html_analyzer_service import (
        HtmlAnalyzerService,
        EmptyHtmlError,
    )

    service = HtmlAnalyzerService(llm_service=llm_service)
    try:
        result = await service.analyze(html=body.html, url_hint=body.url_hint)
    except EmptyHtmlError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El HTML no puede estar vacío.",
        )
    return {
        "proposed_selectors": result.proposed_selectors,
        "confidence": result.confidence,
        "sample_extraction": result.sample_extraction,
    }


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


@router.get("/{chatbot_id}/documents")
async def list_documents(
    chatbot_id: uuid.UUID,
    language: str | None = Query(None, description="Filtrar por idioma (es, ca, en…)"),
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
):
    """Lista los documentos ingestados de un chatbot (unidades citables).

    Acepta ?language=es para filtrar por idioma.
    """
    stmt = (
        select(HubDocument)
        .where(HubDocument.chatbot_id == chatbot_id)
        .order_by(HubDocument.created_at.desc())
    )
    if language:
        stmt = stmt.where(HubDocument.language == language)
    result = await session.execute(stmt)
    docs = result.scalars().all()
    return {
        "documents": [
            {
                "id": str(d.id),
                "chatbot_id": str(d.chatbot_id),
                "title": d.title,
                "canonical_url": d.canonical_url,
                "language": d.language,
                "source_kind": d.source_kind,
                "token_count": d.token_count,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            }
            for d in docs
        ]
    }


@router.get("/{chatbot_id}/documents/{document_id}")
async def get_document(
    chatbot_id: uuid.UUID,
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
):
    """Devuelve un documento con su contenido markdown (para preview en la UI)."""
    doc = await session.get(HubDocument, document_id)
    if not doc or doc.chatbot_id != chatbot_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado.")
    return {
        "id": str(doc.id),
        "chatbot_id": str(doc.chatbot_id),
        "title": doc.title,
        "canonical_url": doc.canonical_url,
        "language": doc.language,
        "source_kind": doc.source_kind,
        "token_count": doc.token_count,
        "markdown_content": doc.markdown_content,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


@router.delete("/{chatbot_id}/documents/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(
    chatbot_id: uuid.UUID,
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
):
    """Elimina un documento ingestado y todos sus chunks."""
    from sqlalchemy import delete as sa_delete

    doc = await session.get(HubDocument, document_id)
    if not doc or doc.chatbot_id != chatbot_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento no encontrado.")

    await session.execute(
        sa_delete(HubDocumentChunk).where(HubDocumentChunk.document_id == document_id)
    )
    await session.delete(doc)
    await session.commit()
    return {"message": "Documento eliminado."}


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    chatbot_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    canonical_url: str | None = Form(None),
    language: str | None = Form(None),
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
    storage: FsspecStorageService = Depends(get_storage_service),
):
    """Sube un documento y lanza su ingestión en background."""
    if file.content_type not in ("application/pdf",):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Solo se admiten archivos PDF.",
        )

    # Validar tamaño (10 MB). Leer todo de una vez para verificar antes de persistir.
    max_size = 10 * 1024 * 1024
    content = await file.read(max_size + 1)
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo supera el límite de 10 MB.",
        )

    # Generar el UUID explícitamente para poder construir la storage key antes del commit
    # (mapped_column default= es un default SQL, no Python; job.id sería None hasta el flush)
    job_id = uuid.uuid4()
    storage_key = f"ingestion/{chatbot_id}/{job_id}.pdf"
    await storage.put(storage_key, content)

    job = HubIngestionJob(
        id=job_id,
        chatbot_id=chatbot_id,
        source_url=storage_key,
        original_filename=file.filename,
        canonical_url=canonical_url or None,
        status="pending",
        language=language,
    )

    session.add(job)
    await session.commit()
    await session.refresh(job)

    # Lanzar tarea en background — el PDF queda en storage (no se borra)
    async def process_job(job_id: uuid.UUID) -> None:
        async for bg_session in get_async_session():
            watcher = IngestionWatcher(
                session=bg_session,
                embedding_service=get_embedding_service(),
                storage=get_storage_service(),
            )
            await watcher.run_job(job_id)

    background_tasks.add_task(process_job, job.id)

    return {"job": job, "message": "Documento subido y encolado."}


@router.delete("/{chatbot_id}/jobs/{job_id}", status_code=status.HTTP_200_OK)
async def delete_ingestion_job(
    chatbot_id: uuid.UUID,
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
    storage: FsspecStorageService = Depends(get_storage_service),
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

    canonical = job.canonical_url or job.source_url
    doc_result = await session.execute(
        select(HubDocument).where(
            HubDocument.chatbot_id == chatbot_id,
            HubDocument.canonical_url == canonical,
        )
    )
    docs = doc_result.scalars().all()

    from sqlalchemy import delete as sa_delete

    chunks_deleted = 0
    for doc in docs:
        await session.execute(
            sa_delete(HubDocumentChunk).where(HubDocumentChunk.document_id == doc.id)
        )
        chunks_deleted += 1
        await session.delete(doc)

    # Borrar el PDF de storage solo si es una clave de storage (no una URL HTTP)
    if not job.source_url.startswith(("http://", "https://")):
        try:
            await storage.delete(job.source_url)
        except FileNotFoundError:
            pass

    await session.delete(job)
    await session.commit()

    return {"message": "Documento eliminado.", "documents_deleted": len(docs)}


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
        language=body.language,
        spider_type=body.spider_type,
        config_json=body.config_json,
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
    storage: FsspecStorageService = Depends(get_storage_service),
):
    """Elimina todos los documentos, chunks y jobs de un chatbot."""
    from sqlalchemy import delete as sa_delete

    await session.execute(
        sa_delete(HubDocumentChunk).where(HubDocumentChunk.chatbot_id == chatbot_id)
    )

    docs_result = await session.execute(
        select(HubDocument).where(HubDocument.chatbot_id == chatbot_id)
    )
    docs = docs_result.scalars().all()
    docs_deleted = len(docs)
    for doc in docs:
        await session.delete(doc)

    jobs_stmt = select(HubIngestionJob).where(HubIngestionJob.chatbot_id == chatbot_id)
    result = await session.execute(jobs_stmt)
    jobs = result.scalars().all()
    for job in jobs:
        if not job.source_url.startswith(("http://", "https://")):
            try:
                await storage.delete(job.source_url)
            except FileNotFoundError:
                pass
        await session.delete(job)

    await session.commit()

    return {
        "message": "Colección vaciada correctamente.",
        "documents_deleted": docs_deleted,
        "jobs_deleted": len(jobs),
    }

"""Router de administración (Hub) para la ingestión de documentos.

Deploy: cloud
"""

import uuid
from datetime import datetime
from typing import Any

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
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user
from server.app.core.auth import UserInfo
from server.app.core.auth.tenancy import assert_org_access
from server.app.core.storage import FsspecStorageService, get_storage_service
from server.app.core.uploads import (
    UploadKind,
    assert_within_document_quota,
    validate_upload,
)
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.database.operational_models import (
    HubDocument,
    HubDocumentChunk,
    HubIngestionJob,
)
from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher
from server.app.modules.agents_hub.services.embedding_resolver import (
    resolve_embedding_service,
)


class AnalyzeHtmlRequest(BaseModel):
    html: str
    url_hint: str = ""


# ── Contrato de respuesta (CAL.2) ──────────────────────────────────────────────
# Estos endpoints nacieron devolviendo dicts sueltos. FastAPI documenta eso como un
# objeto vacío, Orval lo genera como `Promise<unknown>` y el frontend acababa
# redeclarando la forma del dato a mano en `shared/api/ingestion.ts`. Declarar el
# `response_model` es lo que hace que el tipo del panel venga del contrato.
#
# `status` va como `str` y no como `Literal`: es un campo de presentación, la tabla de
# jobs ya tiene rama por defecto, y un valor inesperado en una fila debe pintarse "en
# cola", no tumbar el listado entero con un 500 de validación de respuesta.


class IngestionJob(BaseModel):
    """Trabajo de ingesta tal y como lo pinta la tabla técnica del panel."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chatbot_id: uuid.UUID
    source_url: str
    original_filename: str | None = None
    canonical_url: str | None = None
    language: str | None = None
    status: str
    chunks_processed: int
    error_message: str | None = None
    # Progreso y estadísticas por etapa (RAG.12). Van en el contrato porque el panel
    # los pinta: sin ellos, un job trabajando y un job colgado se ven igual.
    progress_current: int = 0
    progress_total: int | None = None
    progress_message: str = ""
    processing_stats: dict[str, Any] = Field(default_factory=dict)
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    created_at: datetime


class IngestionJobsOut(BaseModel):
    jobs: list[IngestionJob]


class HubDocumentOut(BaseModel):
    """Documento citable, en la forma resumida que lista la tabla del corpus."""

    id: uuid.UUID
    chatbot_id: uuid.UUID
    title: str
    canonical_url: str
    language: str
    source_kind: str
    token_count: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class HubDocumentDetailOut(HubDocumentOut):
    """El mismo documento con su markdown, que es lo que alimenta el preview."""

    markdown_content: str


class HubDocumentsOut(BaseModel):
    documents: list[HubDocumentOut]


class MessageOut(BaseModel):
    message: str


class UploadDocumentOut(BaseModel):
    job: IngestionJob
    message: str


class DeleteIngestionJobOut(BaseModel):
    message: str
    documents_deleted: int


class ClearCollectionOut(BaseModel):
    message: str
    documents_deleted: int
    jobs_deleted: int


class AnalyzeHtmlOut(BaseModel):
    proposed_selectors: dict[str, str | None]
    confidence: float
    sample_extraction: dict[str, str]


router = APIRouter(prefix="/hub/ingestion", tags=["hub-ingestion"])


async def _get_llm_service(session: AsyncSession = Depends(get_async_session)):
    from server.app.modules.agents_hub.services.config_provider import LocalConfigProvider
    from server.app.modules.agents_hub.services.model_factory import get_model_for_tier
    from server.app.modules.agents_hub.services.html_analyzer_service import LangChainLLMAdapter

    provider = LocalConfigProvider(session)
    model = await get_model_for_tier(1, provider)
    return LangChainLLMAdapter(model)


@router.post("/analyze-html", status_code=status.HTTP_200_OK, response_model=AnalyzeHtmlOut)
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



async def _chatbot_autorizado(session, chatbot_id, principal):
    """Lee el chatbot y comprueba la organización (SEC.2).

    Aquí vivía un `# TODO: Validar que el usuario tiene acceso al chatbot`. Mientras estuvo
    sin cerrar, cualquier administrador podía leer los trabajos de ingesta —y por tanto las
    URL y los nombres de fichero del corpus— de cualquier organización.
    """
    from server.app.modules.agents_hub.database.config_models import HubChatbot

    chatbot = await session.get(HubChatbot, chatbot_id)
    if chatbot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chatbot not found")
    assert_org_access(principal, chatbot.organizacion_id)
    return chatbot


@router.get("/{chatbot_id}/jobs", response_model=IngestionJobsOut)
async def get_ingestion_jobs(
    chatbot_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
):
    """Obtiene los trabajos de ingestión de un chatbot."""
    await _chatbot_autorizado(session, chatbot_id, current_user)
    stmt = (
        select(HubIngestionJob)
        .where(HubIngestionJob.chatbot_id == chatbot_id)
        .order_by(HubIngestionJob.created_at.desc())
    )
    result = await session.execute(stmt)
    jobs = result.scalars().all()
    return {"jobs": jobs}


@router.get("/{chatbot_id}/documents", response_model=HubDocumentsOut)
async def list_documents(
    chatbot_id: uuid.UUID,
    language: str | None = Query(None, description="Filtrar por idioma (es, ca, en…)"),
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
):
    """Lista los documentos ingestados de un chatbot (unidades citables).

    Acepta ?language=es para filtrar por idioma.
    """
    await _chatbot_autorizado(session, chatbot_id, current_user)
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


@router.get("/{chatbot_id}/documents/{document_id}", response_model=HubDocumentDetailOut)
async def get_document(
    chatbot_id: uuid.UUID,
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
):
    """Devuelve un documento con su contenido markdown (para preview en la UI)."""
    await _chatbot_autorizado(session, chatbot_id, current_user)
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


@router.delete(
    "/{chatbot_id}/documents/{document_id}",
    status_code=status.HTTP_200_OK,
    response_model=MessageOut,
)
async def delete_document(
    chatbot_id: uuid.UUID,
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
):
    """Elimina un documento ingestado y todos sus chunks."""
    await _chatbot_autorizado(session, chatbot_id, current_user)
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


@router.post(
    "/upload", status_code=status.HTTP_202_ACCEPTED, response_model=UploadDocumentOut
)
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
    await _chatbot_autorizado(session, chatbot_id, current_user)
    # Validación compartida (SEC.6): extensión + magic bytes + corte por tamaño
    # durante la lectura. No se mira content_type: lo fija el cliente y es
    # spoofeable. El límite sale de MAX_UPLOAD_MB.
    validado = await validate_upload(file, kind=UploadKind.PDF)
    content = validado.read()
    validado.close()

    documentos_actuales = await session.scalar(
        select(func.count())
        .select_from(HubIngestionJob)
        .where(HubIngestionJob.chatbot_id == chatbot_id)
    )
    assert_within_document_quota(documentos_actuales or 0)

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
                embedding_service=await resolve_embedding_service(session, chatbot_id),
                storage=get_storage_service(),
            )
            await watcher.run_job(job_id)

    background_tasks.add_task(process_job, job.id)

    return {"job": job, "message": "Documento subido y encolado."}


@router.delete(
    "/{chatbot_id}/jobs/{job_id}",
    status_code=status.HTTP_200_OK,
    response_model=DeleteIngestionJobOut,
)
async def delete_ingestion_job(
    chatbot_id: uuid.UUID,
    job_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
    storage: FsspecStorageService = Depends(get_storage_service),
):
    """Elimina un job de ingestión y todos sus chunks asociados."""
    await _chatbot_autorizado(session, chatbot_id, current_user)
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


@router.delete(
    "/{chatbot_id}/chunks",
    status_code=status.HTTP_200_OK,
    response_model=ClearCollectionOut,
)
async def clear_chatbot_collection(
    chatbot_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserInfo = Depends(get_current_user),
    storage: FsspecStorageService = Depends(get_storage_service),
):
    """Elimina todos los documentos, chunks y jobs de un chatbot."""
    await _chatbot_autorizado(session, chatbot_id, current_user)
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

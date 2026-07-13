"""CRUD de chatbots del Hub + jerarquía router->hijos.

Deploy: cloud
"""

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete as sql_delete
from sqlalchemy import func
from sqlalchemy import select

from server.app.api.deps import require_role
from server.app.core.auth.models import UserInfo
from server.app.modules.agents_hub.database.config_models import HubChatbot
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.database.operational_models import HubDocument
from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher
from server.app.modules.agents_hub.services.corpus_recalculator import recalculate_corpus
from server.app.modules.agents_hub.services.corpus_recommender import recommend_retrieval_mode
from server.app.modules.agents_hub.services.embedding_service import get_embedding_service

router = APIRouter(prefix="/hub/chatbots", tags=["hub-chatbots"])

_require_admin = require_role("superadmin", "admin")


class ChatbotRead(BaseModel):
    id: uuid.UUID
    name: str
    organizacion_id: uuid.UUID
    llm_config_id: uuid.UUID
    system_prompt: str
    sources: list[str]
    is_active: bool
    retrieval_mode: Literal["RAG", "MD_LONG_CONTEXT", "MD_AGENT_SELECTOR"]
    retrieval_top_k: int
    use_prompt_caching: bool
    cache_ttl: int
    kind: str
    parent_chatbot_id: uuid.UUID | None
    public_graph_profile: str
    language_mode: str
    quality_threshold: float
    min_retrieval_results: int
    min_retrieval_score: float
    reranker_enabled: bool
    answer_template: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatbotCreate(BaseModel):
    name: str
    organizacion_id: uuid.UUID
    llm_config_id: uuid.UUID
    system_prompt: str
    sources: list[str] = []
    is_active: bool = True
    retrieval_mode: Literal["RAG", "MD_LONG_CONTEXT", "MD_AGENT_SELECTOR"] = "RAG"
    retrieval_top_k: int = 8
    use_prompt_caching: bool = False
    cache_ttl: int = 3600
    kind: str = "atomic"
    public_graph_profile: str = "PUBLIC_KB_RICH"
    language_mode: str = "prefer"
    quality_threshold: float = 0.6
    min_retrieval_results: int = 2
    min_retrieval_score: float = 0.25
    reranker_enabled: bool = True
    answer_template: str = "generic"


class ChatbotUpdate(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    sources: list[str] | None = None
    is_active: bool | None = None
    retrieval_mode: Literal["RAG", "MD_LONG_CONTEXT", "MD_AGENT_SELECTOR"] | None = None
    retrieval_top_k: int | None = None
    use_prompt_caching: bool | None = None
    cache_ttl: int | None = None
    kind: str | None = None
    parent_chatbot_id: uuid.UUID | None = None
    public_graph_profile: str | None = None
    language_mode: str | None = None
    quality_threshold: float | None = None
    min_retrieval_results: int | None = None
    min_retrieval_score: float | None = None
    reranker_enabled: bool | None = None
    answer_template: str | None = None


class AssignChildIn(BaseModel):
    child_chatbot_id: uuid.UUID


class CorpusStatsOut(BaseModel):
    total_documents: int
    total_tokens: int
    by_language: dict[str, int]
    recommended_mode: str
    recommendation_reason: str


class RegenerateChunksOut(BaseModel):
    task_id: str
    message: str
    documents_processed: int
    chunks_created: int

class RecalculateCorpusOut(BaseModel):
    task_id: str
    message: str
    documents_queued: int
    chunks_created: int
    chunks_deleted: int


async def _get_chatbot_or_404(session, chatbot_id: uuid.UUID) -> HubChatbot:
    chatbot = await session.get(HubChatbot, chatbot_id)
    if not chatbot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chatbot not found"
        )
    return chatbot


@router.get("", response_model=list[ChatbotRead])
async def list_chatbots(
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    result = await session.execute(
        select(HubChatbot).order_by(HubChatbot.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ChatbotRead, status_code=status.HTTP_201_CREATED)
async def create_chatbot(
    body: ChatbotCreate,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    chatbot = HubChatbot(
        organizacion_id=body.organizacion_id,
        llm_config_id=body.llm_config_id,
        name=body.name,
        system_prompt=body.system_prompt,
        sources=body.sources,
        is_active=body.is_active,
        retrieval_mode=body.retrieval_mode,
        retrieval_top_k=body.retrieval_top_k,
        use_prompt_caching=body.use_prompt_caching,
        cache_ttl=body.cache_ttl,
        kind=body.kind,
        public_graph_profile=body.public_graph_profile,
        language_mode=body.language_mode,
        quality_threshold=body.quality_threshold,
        min_retrieval_results=body.min_retrieval_results,
        min_retrieval_score=body.min_retrieval_score,
        reranker_enabled=body.reranker_enabled,
        answer_template=body.answer_template,
    )
    session.add(chatbot)
    await session.commit()
    await session.refresh(chatbot)
    return chatbot


@router.patch("/{chatbot_id}", response_model=ChatbotRead)
async def update_chatbot(
    chatbot_id: uuid.UUID,
    body: ChatbotUpdate,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    chatbot = await _get_chatbot_or_404(session, chatbot_id)

    payload = body.model_dump(exclude_none=True)
    next_mode = payload.get("retrieval_mode", chatbot.retrieval_mode)

    if next_mode == "MD_LONG_CONTEXT":
        total_tokens_row = await session.execute(
            select(func.coalesce(func.sum(HubDocument.token_count), 0)).where(
                HubDocument.chatbot_id == chatbot_id
            )
        )
        total_tokens = int(total_tokens_row.scalar_one() or 0)
        if total_tokens > 128_000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "El corpus excede el límite del modo MD_LONG_CONTEXT (128K tokens). "
                    "Reduce el corpus o cambia a MD_AGENT_SELECTOR."
                ),
            )

    for field, value in payload.items():
        setattr(chatbot, field, value)
    chatbot.updated_at = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(chatbot)
    return chatbot


@router.delete("/{chatbot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chatbot(
    chatbot_id: uuid.UUID,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    await _get_chatbot_or_404(session, chatbot_id)
    await session.execute(sql_delete(HubChatbot).where(HubChatbot.id == chatbot_id))
    await session.commit()


@router.get("/{chatbot_id}/corpus-stats", response_model=CorpusStatsOut)
async def get_corpus_stats(
    chatbot_id: uuid.UUID,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    await _get_chatbot_or_404(session, chatbot_id)

    total_docs_row = await session.execute(
        select(func.count(HubDocument.id)).where(HubDocument.chatbot_id == chatbot_id)
    )
    total_documents = int(total_docs_row.scalar_one() or 0)

    total_tokens_row = await session.execute(
        select(func.coalesce(func.sum(HubDocument.token_count), 0)).where(
            HubDocument.chatbot_id == chatbot_id
        )
    )
    total_tokens = int(total_tokens_row.scalar_one() or 0)

    by_lang_rows = await session.execute(
        select(HubDocument.language, func.coalesce(func.sum(HubDocument.token_count), 0))
        .where(HubDocument.chatbot_id == chatbot_id)
        .group_by(HubDocument.language)
    )
    by_language = {str(lang): int(tokens or 0) for lang, tokens in by_lang_rows.all()}

    context_window = 128_000

    recommended_mode, recommendation_reason = recommend_retrieval_mode(
        total_tokens=total_tokens,
        context_window=context_window,
    )

    return CorpusStatsOut(
        total_documents=total_documents,
        total_tokens=total_tokens,
        by_language=by_language,
        recommended_mode=recommended_mode,
        recommendation_reason=recommendation_reason,
    )


@router.post("/{chatbot_id}/regenerate-chunks", response_model=RegenerateChunksOut)
async def regenerate_chunks(
    chatbot_id: uuid.UUID,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    chatbot = await _get_chatbot_or_404(session, chatbot_id)
    if chatbot.retrieval_mode != "RAG":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se puede regenerar chunks cuando retrieval_mode == 'RAG'.",
        )

    docs_result = await session.execute(
        select(HubDocument).where(HubDocument.chatbot_id == chatbot_id)
    )
    docs = list(docs_result.scalars().all())

    watcher = IngestionWatcher(
        session=session,
        embedding_service=get_embedding_service(),
    )
    created = 0
    for doc in docs:
        created += await watcher._regenerate_chunks_for_document(doc)

    task_id = str(uuid.uuid4())
    return RegenerateChunksOut(
        task_id=task_id,
        message="Regeneración completada",
        documents_processed=len(docs),
        chunks_created=created,
    )

@router.post(
    "/{chatbot_id}/recalculate-corpus",
    response_model=RecalculateCorpusOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def recalculate_corpus_endpoint(
    chatbot_id: uuid.UUID,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    chatbot = await _get_chatbot_or_404(session, chatbot_id)

    embedding_service = get_embedding_service()
    current_dimensions = int(getattr(embedding_service, "dimensions", 1024))
    configured_dimensions = int(
        getattr(getattr(chatbot, "llm_config", None), "embedding_dimensions", current_dimensions)
    )

    if configured_dimensions != current_dimensions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "La dimensión del modelo de embeddings configurado "
                f"({configured_dimensions}) difiere de la activa ({current_dimensions}). "
                "Ejecuta la migración de dimensión antes de recalcular."
            ),
        )

    documents_processed, chunks_created, chunks_deleted = await recalculate_corpus(
        session=session,
        chatbot_id=chatbot_id,
        retrieval_mode=chatbot.retrieval_mode,
        embedding_service=embedding_service,
    )
    await session.commit()

    task_id = str(uuid.uuid4())
    return RecalculateCorpusOut(
        task_id=task_id,
        message=f"Recálculo completado. {documents_processed} documentos procesados.",
        documents_queued=documents_processed,
        chunks_created=chunks_created,
        chunks_deleted=chunks_deleted,
    )


@router.get("/{chatbot_id}/children", response_model=list[ChatbotRead])
async def list_children(
    chatbot_id: uuid.UUID,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    router_cb = await _get_chatbot_or_404(session, chatbot_id)
    if router_cb.kind != "router":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo los chatbots de tipo router pueden tener hijos",
        )

    result = await session.execute(
        select(HubChatbot).where(HubChatbot.parent_chatbot_id == chatbot_id)
    )
    return result.scalars().all()


@router.post("/{chatbot_id}/children", response_model=ChatbotRead)
async def assign_child(
    chatbot_id: uuid.UUID,
    body: AssignChildIn,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    router_cb = await _get_chatbot_or_404(session, chatbot_id)
    if router_cb.kind != "router":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo los chatbots de tipo router pueden tener hijos",
        )
    if router_cb.parent_chatbot_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se permite jerarquía de más de 2 niveles",
        )

    child_cb = await _get_chatbot_or_404(session, body.child_chatbot_id)

    if child_cb.id == router_cb.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un chatbot no puede ser hijo de sí mismo",
        )
    if child_cb.kind == "router":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede asignar un hijo de tipo router",
        )
    if child_cb.organizacion_id != router_cb.organizacion_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El hijo debe pertenecer a la misma organización que el router",
        )
    if (
        child_cb.parent_chatbot_id is not None
        and child_cb.parent_chatbot_id != router_cb.id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se permite crear nietos ni reparentar desde otro router",
        )

    child_cb.parent_chatbot_id = router_cb.id
    child_cb.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(child_cb)
    return child_cb


@router.delete("/{chatbot_id}/children/{child_chatbot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_child(
    chatbot_id: uuid.UUID,
    child_chatbot_id: uuid.UUID,
    _: UserInfo = Depends(_require_admin),
    session=Depends(get_async_session),
):
    router_cb = await _get_chatbot_or_404(session, chatbot_id)
    if router_cb.kind != "router":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo los chatbots de tipo router pueden tener hijos",
        )

    child_cb = await _get_chatbot_or_404(session, child_chatbot_id)
    if child_cb.parent_chatbot_id != router_cb.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ese chatbot no está asignado a este router",
        )

    child_cb.parent_chatbot_id = None
    child_cb.updated_at = datetime.now(timezone.utc)
    await session.commit()

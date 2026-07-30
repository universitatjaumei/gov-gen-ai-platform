"""Endpoint de chat con LangGraph + streaming SSE.

POST /api/v1/hub/chat/{chatbot_id}
  Invoca el grafo LangGraph y devuelve la respuesta del agente
  en tiempo real como Server-Sent Events (text/event-stream).

Protocolo SSE:
  event: status   data: {"node": "<node_name>", "msg": "<mensaje_progreso>"}
  event: token    data: {"delta": "<fragmento>"}
  event: done     data: {"interaction_id": "<uuid>", "sources": [...],
                          "language_fallback": bool, "translation_warning": str | null}
  event: error    data: {"message": "<descripcion>"}

Deploy: edge
"""

import json
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user, require_scopes
from server.app.core.auth import UserInfo
from server.app.modules.agents_hub.agent.public_graphs.core.graph_factory import GraphFactory
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_pipeline_protocol import (
    GraphDeps,
)
from server.app.modules.agents_hub.agent.router_node import build_route_to_subagent_node
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.database.config_models import HubChatbot
from server.app.modules.agents_hub.database.operational_models import HubInteraction
from server.app.modules.agents_hub.services.config_provider import LocalConfigProvider
from server.app.modules.agents_hub.services.embedding_service import get_embedding_service
from server.app.modules.agents_hub.services.model_factory import get_model
from server.app.modules.agents_hub.services.observability import create_callback_handler

router = APIRouter(prefix="/hub/chat", tags=["hub-chat"])


class _ChatbotChildrenProvider:
    def __init__(self, db_session: AsyncSession):
        self._session = db_session

    async def get_children(self, parent_id: uuid.UUID):
        result = await self._session.execute(
            select(HubChatbot).where(HubChatbot.parent_chatbot_id == parent_id)
        )
        return list(result.scalars().all())

# Nodos del CoreGraph → mensaje de progreso. RAG.2 cambió los nombres internos de los
# nodos (search_or_skip → retrieve, generate_response → generate_answer) pero NO el
# contrato SSE observable: los tres mensajes que ve el usuario son los mismos, y los nodos
# internos que no tenían mensaje (merge, log, fallback) siguen sin emitir status.
NODE_STATUS_MESSAGES: dict[str, str] = {
    "detect_language":  "Detectando idioma...",
    "retrieve":         "Buscando en la base de conocimiento...",
    "generate_answer":  "Generando respuesta...",
}

# Nodo del CoreGraph cuyo on_chain_end trae el estado final del que salen las fuentes.
_FINAL_NODES = ("generate_answer", "fallback")

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10_000)


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _build_translation_warning(language: str) -> str | None:
    if not language or language == "es":
        return None
    lang_names = {"ca": "catalan", "en": "ingles", "fr": "frances"}
    lang_display = lang_names.get(language, language)
    return f"⚠️ La pregunta se detecto en {lang_display}. La respuesta puede estar en ese idioma."


def _es_citable(source) -> bool:
    """Sólo van al done las evidencias con URL: sin URL no hay cita verificable.

    En modo selector eso descarta además las entradas de índice, que llegan sin haber
    sido leídas.
    """
    if getattr(source, "metadata", None) and source.metadata.get("index_entry"):
        return False
    return bool(getattr(source, "source_url", None) or getattr(source, "url", None))


def _source_to_dict(source) -> dict:
    """Serializa una evidencia al shape del evento done.

    RAG.2 unificó el contrato interno en EvidenceItem (source_id / source_url), pero el
    shape JSON que ve el frontend **no cambia**: document_id, title, url, score. Se acepta
    también el dialecto `Source` (document_id/url) porque los tools y las estrategias de
    `services/retrieval/` siguen hablándolo por debajo de los pipelines.
    """
    document_id = getattr(source, "source_id", None) or getattr(source, "document_id", None)
    url = getattr(source, "source_url", None) or getattr(source, "url", None)
    score = getattr(source, "score", None)
    return {
        "document_id": str(document_id),
        "title": source.title,
        "url": url,
        "score": round(score, 3) if score is not None else None,
    }


@router.post(
    "/{chatbot_id}",
    status_code=200,
    dependencies=[Depends(require_scopes("chat:test"))],
)
async def chat_stream(
    chatbot_id: uuid.UUID,
    request: ChatRequest,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """Chat con streaming SSE."""
    result = await session.execute(
        select(HubChatbot).where(HubChatbot.id == chatbot_id)
    )
    chatbot = result.scalar_one_or_none()
    if chatbot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chatbot {chatbot_id} not found",
        )

    embedding_service = get_embedding_service()
    config_provider = LocalConfigProvider(session)

    router_status_message: str | None = None
    selected_chatbot_id = chatbot_id
    if getattr(chatbot, "kind", "atomic") == "router":
        router_llm = await get_model(chatbot.id, config_provider)
        router_node = build_route_to_subagent_node(
            embedding_service=embedding_service,
            chatbot_provider=_ChatbotChildrenProvider(session),
            llm_fallback=router_llm,
        )
        try:
            routing = await router_node(
                {
                    "messages": [type("M", (), {"content": request.message})()],
                    "chatbot_id": str(chatbot.id),
                }
            )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        selected_chatbot_id = uuid.UUID(str(routing["selected_child_id"]))
        child_result = await session.execute(
            select(HubChatbot).where(HubChatbot.id == selected_chatbot_id)
        )
        child_chatbot = child_result.scalar_one_or_none()
        if child_chatbot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Child chatbot {selected_chatbot_id} not found",
            )
        chatbot = child_chatbot
        router_status_message = f"Materia detectada: {chatbot.name}"

    llm = await get_model(selected_chatbot_id, config_provider)

    # El grafo lo construye la GraphFactory: resuelve la cascada de config
    # (Plataforma → Organización → Chatbot) y selecciona el perfil y el pipeline de
    # retrieval a partir de cfg.retrieval_mode. El endpoint ya no elige estrategia.
    deps = GraphDeps(session=session, embedder=embedding_service, llm=llm)
    core_graph = await GraphFactory().build(selected_chatbot_id, deps, llm)
    compiled = core_graph.compile()

    initial_state = {
        "query": request.message,
        "chatbot_id": str(selected_chatbot_id),
        "language": None,
        "retrieval_output": None,
        "merged_items": [],
        "answer": None,
        "quality_score": 0.0,
        "fallback_used": False,
        "translation_warning": False,
        "fallback_reason": None,
        "sources": [],
    }
    interaction_id = uuid.uuid4()

    langfuse_handler = create_callback_handler(
        session_id=str(interaction_id), user_id=user.user_id
    )
    stream_config = (
        {
            "callbacks": [langfuse_handler],
            "metadata": {
                "langfuse_session_id": str(interaction_id),
                "langfuse_user_id": user.user_id,
            },
        }
        if langfuse_handler
        else {}
    )

    async def event_generator() -> AsyncIterator[str]:
        collected_tokens: list[str] = []
        final_sources: list = []
        language_fallback = False
        detected_language = "es"
        fallback_reason: str | None = None
        fallback_answer: str | None = None

        try:
            if router_status_message:
                yield _sse(
                    "status",
                    {"node": "route_to_subagent", "msg": router_status_message},
                )

            async for event in compiled.astream_events(initial_state, stream_config, version="v2"):
                kind = event["event"]
                name = event.get("name", "")

                if kind == "on_chain_start" and name in NODE_STATUS_MESSAGES:
                    yield _sse("status", {"node": name, "msg": NODE_STATUS_MESSAGES[name]})

                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk is not None:
                        delta = chunk.content if hasattr(chunk, "content") else str(chunk)
                        if delta:
                            collected_tokens.append(delta)
                            yield _sse("token", {"delta": delta})

                elif kind == "on_chain_end" and name in _FINAL_NODES:
                    output = event.get("data", {}).get("output") or {}
                    raw_sources = output.get("sources", [])
                    final_sources = [
                        _source_to_dict(s) for s in raw_sources if _es_citable(s)
                    ]
                    fallback_reason = output.get("fallback_reason")
                    if output.get("fallback_used"):
                        fallback_answer = output.get("answer")

                elif kind == "on_chain_end" and name == "detect_language":
                    output = event.get("data", {}).get("output") or {}
                    detected_language = output.get("language") or "es"

                elif kind == "on_chain_end" and name == "merge":
                    output = event.get("data", {}).get("output") or {}
                    language_fallback = bool(output.get("translation_warning"))

        except Exception as exc:  # noqa: BLE001
            yield _sse("error", {"message": str(exc)})
            return

        # El fallback y el mensaje del validador de citas no pasan por el stream de tokens
        # del LLM, así que hay que emitirlos aquí para que el usuario vea una respuesta.
        if fallback_answer and not collected_tokens:
            collected_tokens.append(fallback_answer)
            yield _sse("token", {"delta": fallback_answer})

        assistant_message = "".join(collected_tokens)
        interaction = HubInteraction(
            id=interaction_id,
            chatbot_id=selected_chatbot_id,
            user_id=user.user_id,
            user_message=request.message,
            assistant_message=assistant_message,
            run_id=interaction_id,
            fallback_reason=fallback_reason,
        )
        session.add(interaction)
        await session.commit()

        translation_warning = (
            _build_translation_warning(detected_language) if language_fallback else None
        )
        yield _sse(
            "done",
            {
                "interaction_id": str(interaction_id),
                "sources": final_sources,
                "language_fallback": language_fallback,
                "translation_warning": translation_warning,
            },
        )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )

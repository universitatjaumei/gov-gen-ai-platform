"""Endpoint de chat con LangGraph + streaming SSE.

POST /api/v1/hub/chat/{chatbot_id}
  Invoca el grafo LangGraph y devuelve la respuesta del agente
  en tiempo real como Server-Sent Events (text/event-stream).

Protocolo SSE:
  event: status   data: {"node": "<node_name>", "msg": "<mensaje_progreso>"}
  event: token    data: {"delta": "<fragmento>"}
  event: done     data: {"interaction_id": "<uuid>", "sources": [...],
                          "language_fallback": bool, "translation_warning": str | null}
  event: error    data: {"message": "<descripción>"}

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

from server.app.api.deps import get_current_user
from server.app.core.auth import UserInfo
from server.app.modules.agents_hub.agent.graph import create_agent_graph
from server.app.modules.agents_hub.agent.state import create_initial_state
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.database.config_models import HubChatbot
from server.app.modules.agents_hub.database.operational_models import HubInteraction
from server.app.modules.agents_hub.services.embedding_service import get_embedding_service
from server.app.modules.agents_hub.services.observability import create_callback_handler
from server.app.modules.agents_hub.services.retriever import HybridRetriever

router = APIRouter(prefix="/hub/chat", tags=["hub-chat"])

# ---------------------------------------------------------------------------
# Mapeo de nodos LangGraph → mensajes de progreso para el cliente
# ---------------------------------------------------------------------------
NODE_STATUS_MESSAGES: dict[str, str] = {
    "route_by_capability":       "Iniciando...",
    "detect_language":           "Detectando idioma...",
    "query_classifier":          "Clasificando consulta...",
    "search_knowledge":          "Buscando en la base de conocimiento...",
    "validate_retrieval":        "Validando resultados...",
    "search_knowledge_fallback": "Buscando en otros idiomas...",
    "reranker":                  "Reordenando resultados...",
    "generate_response":         "Generando respuesta...",
    "quality_evaluator":         "Evaluando calidad...",
    "log_interaction":           "Guardando interacción...",
}

# Cabeceras necesarias para que proxies y nginx no almacenen en búfer el stream
_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10_000)


def _sse(event: str, payload: dict) -> str:
    """Formatea un evento SSE con nombre explícito."""
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _build_translation_warning(language: str) -> str | None:
    """Genera una advertencia si la respuesta puede estar en un idioma diferente."""
    if not language or language == "es":
        return None
    lang_names = {"ca": "catalán", "en": "inglés", "fr": "francés"}
    lang_display = lang_names.get(language, language)
    return f"⚠️ La pregunta se detectó en {lang_display}. La respuesta puede estar en ese idioma."


@router.post("/{chatbot_id}", status_code=200)
async def chat_stream(
    chatbot_id: uuid.UUID,
    request: ChatRequest,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """Chat con streaming SSE.

    Emite eventos tipados mientras el grafo LangGraph procesa la petición:
    - `status` por cada nodo que comienza a ejecutarse
    - `token` con cada fragmento del LLM durante la generación
    - `done` al finalizar (con fuentes y posible advertencia de idioma)
    - `error` si se produce una excepción durante el streaming
    """
    result = await session.execute(
        select(HubChatbot).where(HubChatbot.id == chatbot_id)
    )
    chatbot = result.scalar_one_or_none()
    if chatbot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chatbot {chatbot_id} not found",
        )

    retriever = HybridRetriever(session)
    embedding_service = get_embedding_service()
    initial_state = create_initial_state(
        user_id=user.user_id,
        chatbot_id=str(chatbot_id),
        initial_message=request.message,
    )
    interaction_id = uuid.uuid4()
    graph = create_agent_graph(retriever, embedding_service, user_id=user.user_id)
    compiled = graph.compile()

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
        final_sources: list[str] = []
        language_fallback = False
        detected_language = "es"

        try:
            async for event in compiled.astream_events(initial_state, stream_config, version="v2"):
                kind = event["event"]
                name = event.get("name", "")

                # ── Nodo iniciando → evento status ──────────────────────────
                if kind == "on_chain_start" and name in NODE_STATUS_MESSAGES:
                    yield _sse("status", {"node": name, "msg": NODE_STATUS_MESSAGES[name]})

                # ── Fragmento del LLM → evento token ────────────────────────
                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk is not None:
                        delta = chunk.content if hasattr(chunk, "content") else str(chunk)
                        if delta:
                            collected_tokens.append(delta)
                            yield _sse("token", {"delta": delta})

                # ── Nodo generate_response finalizado → recoger fuentes ──────
                elif kind == "on_chain_end" and name == "generate_response":
                    output = event.get("data", {}).get("output", {})
                    final_sources = output.get("sources", [])
                    language_fallback = output.get("language_fallback_triggered", False)
                    detected_language = output.get("language", "es")

        except Exception as exc:  # noqa: BLE001
            yield _sse("error", {"message": str(exc)})
            return

        # ── Guardar interacción en BD ────────────────────────────────────────
        assistant_message = "".join(collected_tokens)
        interaction = HubInteraction(
            id=interaction_id,
            chatbot_id=chatbot_id,
            user_id=user.user_id,
            user_message=request.message,
            assistant_message=assistant_message,
            run_id=interaction_id,
        )
        session.add(interaction)
        await session.commit()

        # ── Evento final ─────────────────────────────────────────────────────
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

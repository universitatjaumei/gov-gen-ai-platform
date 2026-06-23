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
from server.app.modules.agents_hub.agent.graph import create_agent_graph
from server.app.modules.agents_hub.agent.router_node import build_route_to_subagent_node
from server.app.modules.agents_hub.agent.state import create_initial_state
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.database.config_models import HubChatbot
from server.app.modules.agents_hub.database.operational_models import HubInteraction
from server.app.modules.agents_hub.services.config_provider import LocalConfigProvider
from server.app.modules.agents_hub.services.embedding_service import get_embedding_service
from server.app.modules.agents_hub.services.model_factory import get_model
from server.app.modules.agents_hub.services.observability import create_callback_handler
from server.app.modules.agents_hub.services.retrieval.agentic_strategy import AgenticRetrievalStrategy
from server.app.modules.agents_hub.services.retrieval.long_context_strategy import LongContextRetrievalStrategy
from server.app.modules.agents_hub.services.retrieval.vector_strategy import VectorRetrievalStrategy

router = APIRouter(prefix="/hub/chat", tags=["hub-chat"])


class _ChatbotChildrenProvider:
    def __init__(self, db_session: AsyncSession):
        self._session = db_session

    async def get_children(self, parent_id: uuid.UUID):
        result = await self._session.execute(
            select(HubChatbot).where(HubChatbot.parent_chatbot_id == parent_id)
        )
        return list(result.scalars().all())

NODE_STATUS_MESSAGES: dict[str, str] = {
    "detect_language":    "Detectando idioma...",
    "search_or_skip":     "Buscando en la base de conocimiento...",
    "generate_response":  "Generando respuesta...",
}

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


def _source_to_dict(source) -> dict:
    return {
        "document_id": str(source.document_id),
        "title": source.title,
        "url": source.url,
        "score": round(source.score, 3),
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

    retrieval_mode = getattr(chatbot, "retrieval_mode", "RAG")
    if retrieval_mode == "MD_LONG_CONTEXT":
        strategy = LongContextRetrievalStrategy(session)
    elif retrieval_mode == "MD_AGENT_SELECTOR":
        strategy = AgenticRetrievalStrategy(session)
    else:
        strategy = VectorRetrievalStrategy(
            session, embedding_service, top_k=chatbot.retrieval_top_k
        )

    llm = await get_model(selected_chatbot_id, config_provider)

    initial_state = create_initial_state(
        user_id=user.user_id,
        chatbot_id=str(selected_chatbot_id),
        initial_message=request.message,
    )
    interaction_id = uuid.uuid4()
    graph = create_agent_graph(
        retrieval_strategy=strategy,
        llm=llm,
        base_system_prompt=chatbot.system_prompt,
        user_id=user.user_id,
    )
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
        final_sources: list = []
        language_fallback = False
        detected_language = "es"

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

                elif kind == "on_chain_end" and name == "generate_response":
                    output = event.get("data", {}).get("output", {})
                    raw_sources = output.get("sources", [])
                    final_sources = [_source_to_dict(s) for s in raw_sources if hasattr(s, "url")]
                    language_fallback = output.get("language_fallback_triggered", False)
                    detected_language = output.get("language", "es")

        except Exception as exc:  # noqa: BLE001
            yield _sse("error", {"message": str(exc)})
            return

        assistant_message = "".join(collected_tokens)
        interaction = HubInteraction(
            id=interaction_id,
            chatbot_id=selected_chatbot_id,
            user_id=user.user_id,
            user_message=request.message,
            assistant_message=assistant_message,
            run_id=interaction_id,
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

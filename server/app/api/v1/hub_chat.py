"""Endpoint de chat con LangGraph + streaming SSE.

POST /api/v1/hub/chat/{chatbot_id}
  Invoca el grafo LangGraph y devuelve la respuesta del agente
  en tiempo real como Server-Sent Events (text/event-stream).
  Guarda la interacción completa en hub_interactions al terminar el stream.
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
from server.app.modules.agents_hub.database.models import HubChatbot, HubInteraction
from server.app.modules.agents_hub.services.embedding_service import GoogleEmbeddingService
from server.app.modules.agents_hub.services.retriever import HybridRetriever

router = APIRouter(prefix="/hub/chat", tags=["hub-chat"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10_000)


@router.post("/{chatbot_id}", status_code=200)
async def chat(
    chatbot_id: uuid.UUID,
    request: ChatRequest,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    """Chat con streaming SSE.

    Carga el chatbot, construye el grafo LangGraph y emite cada fragmento
    de la respuesta como un evento SSE. Al finalizar guarda la interacción
    en la base de datos y emite un evento final {done: true}.
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
    embedding_service = GoogleEmbeddingService()
    initial_state = create_initial_state(
        user_id=user.user_id,
        chatbot_id=str(chatbot_id),
        initial_message=request.message,
    )
    run_id = uuid.uuid4()
    graph = create_agent_graph(retriever, embedding_service, user_id=user.user_id)
    compiled = graph.compile()
    collected: list[str] = []

    async def generate() -> AsyncIterator[str]:
        async for chunk in compiled.astream(initial_state):
            if "generate_response" in chunk:
                for msg in chunk["generate_response"].get("messages", []):
                    content = msg.content if hasattr(msg, "content") else str(msg)
                    collected.append(content)
                    yield f"data: {json.dumps({'content': content, 'run_id': str(run_id)})}\n\n"

        interaction = HubInteraction(
            id=run_id,
            chatbot_id=chatbot_id,
            user_id=user.user_id,
            user_message=request.message,
            assistant_message="".join(collected),
            run_id=run_id,
        )
        session.add(interaction)
        await session.commit()
        yield f"data: {json.dumps({'done': True, 'run_id': str(run_id)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

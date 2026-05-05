"""Estado del agente LangGraph."""

from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Estado compartido del grafo del agente."""

    messages: Annotated[list[BaseMessage], add_messages]
    language: str
    chatbot_id: str
    user_id: str | None
    # Retrieval
    retrieved_sources: list        # list[Source] tras search_or_skip
    retrieval_mode: str            # vector | long_context | agentic
    total_tokens: int
    sources: list                  # Source[] final emitidas en done SSE
    available_tools: list[str]


def create_initial_state(
    user_id: str | None,
    chatbot_id: str,
    initial_message: str,
) -> AgentState:
    """Crea el estado inicial del agente.

    Args:
        user_id: ID del usuario (None para modo público)
        chatbot_id: ID del chatbot
        initial_message: Mensaje inicial del usuario

    Returns:
        Estado inicial del agente
    """
    return AgentState(
        messages=[HumanMessage(content=initial_message)],
        language="es",
        chatbot_id=chatbot_id,
        user_id=user_id,
        retrieved_sources=[],
        retrieval_mode="RAG",
        total_tokens=0,
        sources=[],
        available_tools=[],
    )

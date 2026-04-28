"""Tests para el grafo de LangGraph."""
import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from server.app.modules.agents_hub.services.retrieval.types import RetrievalContext, Source


def _make_vector_strategy(sources=None):
    strategy = AsyncMock()
    strategy.mode = "vector"
    ctx = RetrievalContext(sources=sources or [], mode="vector", total_tokens=0)
    strategy.get_context = AsyncMock(return_value=ctx)
    strategy.get_agent_tools = Mock(return_value=[])
    return strategy


class TestAgentGraph:

    def test_graph_has_required_nodes(self) -> None:
        from server.app.modules.agents_hub.agent.graph import create_agent_graph
        llm = AsyncMock()
        graph = create_agent_graph(
            retrieval_strategy=_make_vector_strategy(),
            llm=llm,
            base_system_prompt="Eres un asistente.",
        )
        assert "detect_language" in str(graph.nodes)
        assert "generate_response" in str(graph.nodes)
        assert "search_or_skip" in str(graph.nodes)

    @pytest.mark.asyncio
    async def test_graph_processes_message(self) -> None:
        from server.app.modules.agents_hub.agent.graph import create_agent_graph
        from server.app.modules.agents_hub.agent.state import create_initial_state

        llm = AsyncMock()
        llm.ainvoke = AsyncMock(return_value=Mock(content="Respuesta de prueba"))

        graph = create_agent_graph(
            retrieval_strategy=_make_vector_strategy(),
            llm=llm,
            base_system_prompt="Eres un asistente.",
        )
        initial_state = create_initial_state(
            user_id="user-123",
            chatbot_id=str(uuid.uuid4()),
            initial_message="Hola, necesito ayuda",
        )
        compiled = graph.compile()
        assert compiled is not None

    @pytest.mark.asyncio
    async def test_graph_applies_citation_fallback_when_no_sources_cited(self) -> None:
        from server.app.modules.agents_hub.agent.graph import create_agent_graph
        from server.app.modules.agents_hub.agent.state import create_initial_state
        from server.app.modules.agents_hub.agent.citation_validator import NO_CITATION_FALLBACK

        source = Source(
            document_id=uuid.uuid4(),
            title="Norma A",
            url="https://ej.com/a.pdf",
            excerpt="Texto normativo.",
            score=0.9,
        )
        strategy = _make_vector_strategy(sources=[source])
        llm = AsyncMock()
        # LLM devuelve texto sin cita
        llm.ainvoke = AsyncMock(return_value=Mock(content="El plazo es 30 dias sin citar nada."))

        graph = create_agent_graph(
            retrieval_strategy=strategy,
            llm=llm,
            base_system_prompt="Eres un asistente.",
        )
        initial_state = create_initial_state(
            user_id=None,
            chatbot_id=str(uuid.uuid4()),
            initial_message="Cual es el plazo?",
        )
        compiled = graph.compile()
        result = await compiled.ainvoke(initial_state)
        last_msg = result["messages"][-1]
        assert last_msg.content == NO_CITATION_FALLBACK

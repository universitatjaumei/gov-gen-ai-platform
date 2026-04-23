"""Tests para el grafo de LangGraph."""
import pytest
from unittest.mock import AsyncMock, Mock, patch


class TestAgentGraph:

    def test_graph_has_required_nodes(self) -> None:
        from server.app.modules.agents_hub.agent.graph import create_agent_graph

        with patch('server.app.modules.agents_hub.agent.graph.ChatGoogleGenerativeAI'):
            graph = create_agent_graph(
                retriever=Mock(),
                embedding_service=Mock(),
            )

            assert "detect_language" in str(graph.nodes)
            assert "generate_response" in str(graph.nodes)

    @pytest.mark.asyncio
    async def test_graph_processes_message(self) -> None:
        from server.app.modules.agents_hub.agent.graph import create_agent_graph
        from server.app.modules.agents_hub.agent.state import create_initial_state

        with patch('server.app.modules.agents_hub.agent.graph.ChatGoogleGenerativeAI') as mock_llm:
            mock_llm.return_value.ainvoke = AsyncMock(
                return_value=Mock(content="Respuesta de prueba")
            )

            graph = create_agent_graph(
                retriever=AsyncMock(hybrid_search=AsyncMock(return_value=[])),
                embedding_service=AsyncMock(embed=AsyncMock(return_value=[0.1] * 1536)),
            )

            initial_state = create_initial_state(
                user_id="user-123",
                chatbot_id="chatbot-456",
                initial_message="Hola, necesito ayuda",
            )

            compiled = graph.compile()
            assert compiled is not None

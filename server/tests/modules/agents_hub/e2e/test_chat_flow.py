"""Tests E2E del flujo completo de chat (Prompt 6.1).

Requieren PostgreSQL con pgvector corriendo.
El LLM se mockea para evitar llamadas reales a la API.
Usan httpx.AsyncClient + ASGITransport para ejecutar todo en el mismo
event loop que los fixtures async de BD (evita conflictos de loop).

Rutas reales (monorepo):
  tests/e2e/test_chat_flow.py → server/tests/modules/agents_hub/e2e/test_chat_flow.py
"""
import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage
from sqlalchemy import select


class TestChatFlowE2E:

    @pytest.mark.asyncio
    async def test_full_chat_flow(self, test_app, setup_chatbot, auth_headers) -> None:
        """Flujo completo: petición → agente LangGraph → respuesta SSE."""
        chatbot = setup_chatbot

        async def _mock_astream(state):
            yield {"generate_response": {"messages": [AIMessage(content="Python es muy versátil.")]}}

        mock_compiled = MagicMock()
        mock_compiled.astream = _mock_astream
        mock_graph = MagicMock()
        mock_graph.compile = MagicMock(return_value=mock_compiled)

        with (
            patch("server.app.api.v1.hub_chat.create_agent_graph", return_value=mock_graph),
            patch("server.app.api.v1.hub_chat.GoogleEmbeddingService"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                async with client.stream(
                    "POST",
                    f"/api/v1/hub/chat/{chatbot.id}",
                    json={"message": "¿Qué es Python?"},
                    headers=auth_headers,
                ) as response:
                    assert response.status_code == 200
                    assert "text/event-stream" in response.headers.get("content-type", "")
                    lines = [l async for l in response.aiter_lines() if l.startswith("data:")]

        assert len(lines) >= 1
        payload = json.loads(lines[0].removeprefix("data:").strip())
        assert "content" in payload
        assert payload["content"] == "Python es muy versátil."

    @pytest.mark.asyncio
    async def test_chat_stores_interaction(
        self, test_app, setup_chatbot, auth_headers, db_session
    ) -> None:
        """Tras el chat, la interacción queda guardada en hub_interactions."""
        from server.app.modules.agents_hub.database.operational_models import HubInteraction

        chatbot = setup_chatbot

        async def _mock_astream(state):
            yield {"generate_response": {"messages": [AIMessage(content="Respuesta guardada")]}}

        mock_compiled = MagicMock()
        mock_compiled.astream = _mock_astream
        mock_graph = MagicMock()
        mock_graph.compile = MagicMock(return_value=mock_compiled)

        run_id = None
        with (
            patch("server.app.api.v1.hub_chat.create_agent_graph", return_value=mock_graph),
            patch("server.app.api.v1.hub_chat.GoogleEmbeddingService"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                async with client.stream(
                    "POST",
                    f"/api/v1/hub/chat/{chatbot.id}",
                    json={"message": "Pregunta de prueba"},
                    headers=auth_headers,
                ) as response:
                    data_lines = [l async for l in response.aiter_lines() if l.startswith("data:")]

        last = json.loads(data_lines[-1].removeprefix("data:").strip())
        assert last.get("done") is True
        run_id = uuid.UUID(last["run_id"])

        # Verificar persistencia en BD
        result = await db_session.execute(
            select(HubInteraction).where(HubInteraction.run_id == run_id)
        )
        interaction = result.scalar_one_or_none()
        assert interaction is not None
        assert interaction.user_message == "Pregunta de prueba"
        assert interaction.assistant_message == "Respuesta guardada"
        assert interaction.chatbot_id == chatbot.id


class TestExportFlowE2E:

    @pytest.mark.asyncio
    async def test_export_after_chat(
        self, test_app, setup_chatbot, auth_headers
    ) -> None:
        """El usuario puede exportar la interacción como Markdown tras el chat."""
        chatbot = setup_chatbot

        async def _mock_astream(state):
            yield {"generate_response": {"messages": [AIMessage(content="## Respuesta\n\nContenido exportable.")]}}

        mock_compiled = MagicMock()
        mock_compiled.astream = _mock_astream
        mock_graph = MagicMock()
        mock_graph.compile = MagicMock(return_value=mock_compiled)

        with (
            patch("server.app.api.v1.hub_chat.create_agent_graph", return_value=mock_graph),
            patch("server.app.api.v1.hub_chat.GoogleEmbeddingService"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                async with client.stream(
                    "POST",
                    f"/api/v1/hub/chat/{chatbot.id}",
                    json={"message": "Genera un informe"},
                    headers=auth_headers,
                ) as response:
                    data_lines = [l async for l in response.aiter_lines() if l.startswith("data:")]

                last = json.loads(data_lines[-1].removeprefix("data:").strip())
                run_id = last["run_id"]

                export_response = await client.get(
                    f"/api/v1/hub/tasks/export/{run_id}",
                    headers=auth_headers,
                )
                assert export_response.status_code == 200
                assert "Genera un informe" in export_response.text
                assert "Respuesta" in export_response.text

    @pytest.mark.asyncio
    async def test_export_forbidden_for_other_user(
        self, test_app, setup_chatbot, auth_headers
    ) -> None:
        """Otro usuario no puede exportar una interacción que no le pertenece."""
        from server.app.core.auth import UserInfo, create_token

        chatbot = setup_chatbot

        async def _mock_astream(state):
            yield {"generate_response": {"messages": [AIMessage(content="Datos privados")]}}

        mock_compiled = MagicMock()
        mock_compiled.astream = _mock_astream
        mock_graph = MagicMock()
        mock_graph.compile = MagicMock(return_value=mock_compiled)

        other_token = create_token(
            UserInfo(user_id="intruder-99", email="intruder@test.com", role="user")
        )
        other_headers = {"Authorization": f"Bearer {other_token}"}

        with (
            patch("server.app.api.v1.hub_chat.create_agent_graph", return_value=mock_graph),
            patch("server.app.api.v1.hub_chat.GoogleEmbeddingService"),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                async with client.stream(
                    "POST",
                    f"/api/v1/hub/chat/{chatbot.id}",
                    json={"message": "Mensaje privado"},
                    headers=auth_headers,
                ) as response:
                    data_lines = [l async for l in response.aiter_lines() if l.startswith("data:")]

                last = json.loads(data_lines[-1].removeprefix("data:").strip())
                run_id = last["run_id"]

                forbidden = await client.get(
                    f"/api/v1/hub/tasks/export/{run_id}",
                    headers=other_headers,
                )
                assert forbidden.status_code == 403

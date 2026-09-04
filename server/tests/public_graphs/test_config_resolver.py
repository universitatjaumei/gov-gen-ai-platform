"""Tests del ConfigResolver de grafo público — TDD RED (9B.3).

La cascada es: PlatformDefaults → OrgDefaults → ChatbotOverrides.
None en un campo del mock indica "heredar del nivel superior".
"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_session(chatbot=None, client=None):
    """Devuelve un session mock cuyo `.get()` distingue por clase.

    **`execute` hay que darlo aparte, y por eso este arnés estaba roto.** Cuando se escribió, el
    resolver sólo hacía `session.get`. Después ganó una consulta de vocabulario que hace
    `result.scalars().all()`, y sobre un `AsyncMock` pelado `scalars()` devuelve una corrutina:
    `AttributeError: 'coroutine' object has no attribute 'all'`. El test llevaba en rojo desde
    entonces sin que nadie lo viera, porque este árbol vivía fuera de `server/tests/` y CI sólo
    lo colectaba.
    """
    from unittest.mock import AsyncMock as _AsyncMock

    session = AsyncMock()

    async def _get(model_class, pk):
        from server.app.modules.agents_hub.database.config_models import HubChatbot, HubOrganizacion
        if model_class is HubChatbot:
            return chatbot
        if model_class is HubOrganizacion:
            return client
        return None

    resultado = MagicMock()
    resultado.scalars.return_value.all.return_value = []
    session.get = _get
    session.execute = _AsyncMock(return_value=resultado)
    return session


def _mock_chatbot(organizacion_id=None, **kwargs):
    bot = MagicMock()
    bot.organizacion_id = organizacion_id or uuid.uuid4()
    # Todos los campos de grafo a None por defecto (se hereda del org/plataforma)
    for field in [
        "public_graph_profile", "retrieval_mode", "language_mode",
        "quality_threshold", "min_retrieval_results", "min_retrieval_score",
        "reranker_enabled", "answer_template",
    ]:
        setattr(bot, field, kwargs.get(field, None))
    return bot


def _mock_organizacion(**kwargs):
    client = MagicMock()
    for field in [
        "default_public_graph_profile", "default_retrieval_mode", "default_language_mode",
        "default_quality_threshold", "default_min_retrieval_results", "default_min_retrieval_score",
        "default_reranker_enabled", "default_answer_template",
    ]:
        setattr(client, field, kwargs.get(field, None))
    return client


class TestConfigResolver:

    @pytest.mark.asyncio
    async def test_effective_config_uses_platform_defaults(self) -> None:
        """Sin chatbot en BD → todos los valores son los de la plataforma."""
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            get_effective_public_graph_config,
        )

        session = _make_session(chatbot=None, client=None)
        config = await get_effective_public_graph_config(uuid.uuid4(), session)

        assert config.profile == "PUBLIC_KB_RICH"
        assert config.retrieval_mode == "RAG"
        assert config.language_mode == "prefer"
        # Los tres valores que 9B.2 escribió (0,6 / 0,25 / True) los cambiaron bloques
        # posteriores **midiendo**: HIB.R el umbral, RAG.5 el mínimo de puntuación y RAG.6 el
        # reranker. La razón de cada uno vive junto a su constante en `config_resolver.py`, con
        # las cifras del lote delante; aquí no se duplica, se afirma que la cascada entrega el
        # valor de plataforma cuando no hay nada por debajo.
        assert config.quality_threshold == pytest.approx(0.65)
        assert config.min_retrieval_results == 2
        assert config.min_retrieval_score == pytest.approx(0.0)
        assert config.reranker_enabled is False
        assert config.answer_template == "generic"

    @pytest.mark.asyncio
    async def test_effective_config_org_overrides_platform(self) -> None:
        """Los defaults de la organización reemplazan los de la plataforma."""
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            get_effective_public_graph_config,
        )

        client_id = uuid.uuid4()
        client = _mock_organizacion(
            default_public_graph_profile="PUBLIC_PORTAL_AGGREGATOR",
            default_retrieval_mode="MD_LONG_CONTEXT",
            default_language_mode="strict",
            default_quality_threshold=0.8,
            default_min_retrieval_results=3,
            default_min_retrieval_score=0.4,
            default_reranker_enabled=False,
            default_answer_template="institutional",
        )
        # Chatbot existe pero no tiene ningún campo configurado (todo None → hereda org)
        chatbot = _mock_chatbot(organizacion_id=client_id)

        session = _make_session(chatbot=chatbot, client=client)
        config = await get_effective_public_graph_config(uuid.uuid4(), session)

        assert config.profile == "PUBLIC_PORTAL_AGGREGATOR"
        assert config.retrieval_mode == "MD_LONG_CONTEXT"
        assert config.language_mode == "strict"
        assert config.quality_threshold == pytest.approx(0.8)
        assert config.reranker_enabled is False
        assert config.answer_template == "institutional"

    @pytest.mark.asyncio
    async def test_effective_config_chatbot_overrides_org(self) -> None:
        """Los valores explícitos del chatbot prevalecen sobre los del org."""
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            get_effective_public_graph_config,
        )

        client_id = uuid.uuid4()
        client = _mock_organizacion(
            default_public_graph_profile="PUBLIC_PORTAL_AGGREGATOR",
            default_retrieval_mode="MD_LONG_CONTEXT",
            default_language_mode="strict",
        )
        chatbot = _mock_chatbot(
            organizacion_id=client_id,
            public_graph_profile="PUBLIC_KB_RICH",   # override del org
            retrieval_mode="MD_AGENT_SELECTOR",       # override del org
            language_mode="none",                     # override del org
        )

        session = _make_session(chatbot=chatbot, client=client)
        config = await get_effective_public_graph_config(uuid.uuid4(), session)

        assert config.profile == "PUBLIC_KB_RICH"
        assert config.retrieval_mode == "MD_AGENT_SELECTOR"
        assert config.language_mode == "none"

    @pytest.mark.asyncio
    async def test_effective_config_includes_retrieval_mode(self) -> None:
        """retrieval_mode siempre está presente en el config resuelto."""
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            get_effective_public_graph_config,
            PublicGraphConfig,
        )

        session = _make_session(chatbot=None)
        config = await get_effective_public_graph_config(uuid.uuid4(), session)

        assert isinstance(config, PublicGraphConfig)
        assert hasattr(config, "retrieval_mode")
        assert config.retrieval_mode is not None

    @pytest.mark.asyncio
    async def test_partial_chatbot_override_inherits_org_for_rest(self) -> None:
        """Si el chatbot sólo sobreescribe algunos campos, el resto viene del org."""
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            get_effective_public_graph_config,
        )

        client_id = uuid.uuid4()
        client = _mock_organizacion(
            default_retrieval_mode="MD_LONG_CONTEXT",
            default_language_mode="strict",
            default_answer_template="institutional",
        )
        # Chatbot sólo sobreescribe language_mode; el resto hereda del org
        chatbot = _mock_chatbot(organizacion_id=client_id, language_mode="prefer")

        session = _make_session(chatbot=chatbot, client=client)
        config = await get_effective_public_graph_config(uuid.uuid4(), session)

        assert config.language_mode == "prefer"          # del chatbot
        assert config.retrieval_mode == "MD_LONG_CONTEXT"  # del org
        assert config.answer_template == "institutional"    # del org

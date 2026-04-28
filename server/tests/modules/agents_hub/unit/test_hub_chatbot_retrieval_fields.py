"""Tests de los nuevos campos de HubChatbot -- TDD RED (Prompt 9CBis.1).

Deben fallar con AttributeError hasta que se implementen retrieval_mode,
kind y parent_chatbot_id en config_models.py (Prompt 9CBis.2).
"""
import uuid
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chatbot(**kwargs):
    from server.app.modules.agents_hub.database.config_models import HubChatbot
    defaults = dict(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        llm_config_id=uuid.uuid4(),
        name=f"chatbot-{uuid.uuid4().hex[:6]}",
        system_prompt="Asistente de prueba",
    )
    defaults.update(kwargs)
    return HubChatbot(**defaults)


# ---------------------------------------------------------------------------
# Tests de retrieval_mode
# ---------------------------------------------------------------------------

class TestHubChatbotRetrievalMode:

    def test_retrieval_mode_field_exists(self):
        from server.app.modules.agents_hub.database.config_models import HubChatbot
        assert hasattr(HubChatbot, "retrieval_mode")

    def test_retrieval_mode_defaults_to_vector(self):
        """La columna ORM tiene default 'vector' para chatbots existentes."""
        from server.app.modules.agents_hub.database.config_models import HubChatbot
        col = HubChatbot.__table__.c["retrieval_mode"]
        assert col.default is not None
        assert col.default.arg == "vector"

    def test_retrieval_mode_accepts_long_context(self):
        cb = _make_chatbot(retrieval_mode="long_context")
        assert cb.retrieval_mode == "long_context"

    def test_retrieval_mode_accepts_agentic(self):
        cb = _make_chatbot(retrieval_mode="agentic")
        assert cb.retrieval_mode == "agentic"

    def test_retrieval_mode_column_is_in_table(self):
        from server.app.modules.agents_hub.database.config_models import HubChatbot
        assert "retrieval_mode" in HubChatbot.__table__.c


# ---------------------------------------------------------------------------
# Tests de kind
# ---------------------------------------------------------------------------

class TestHubChatbotKind:

    def test_kind_field_exists(self):
        from server.app.modules.agents_hub.database.config_models import HubChatbot
        assert hasattr(HubChatbot, "kind")

    def test_kind_defaults_to_atomic(self):
        """La columna ORM tiene default 'atomic'."""
        from server.app.modules.agents_hub.database.config_models import HubChatbot
        col = HubChatbot.__table__.c["kind"]
        assert col.default is not None
        assert col.default.arg == "atomic"

    def test_kind_accepts_router(self):
        cb = _make_chatbot(kind="router")
        assert cb.kind == "router"

    def test_kind_column_is_in_table(self):
        from server.app.modules.agents_hub.database.config_models import HubChatbot
        assert "kind" in HubChatbot.__table__.c


# ---------------------------------------------------------------------------
# Tests de parent_chatbot_id
# ---------------------------------------------------------------------------

class TestHubChatbotParentId:

    def test_parent_chatbot_id_field_exists(self):
        from server.app.modules.agents_hub.database.config_models import HubChatbot
        assert hasattr(HubChatbot, "parent_chatbot_id")

    def test_parent_chatbot_id_defaults_to_none(self):
        cb = _make_chatbot()
        assert cb.parent_chatbot_id is None

    def test_parent_chatbot_id_accepts_uuid(self):
        parent_id = uuid.uuid4()
        cb = _make_chatbot(parent_chatbot_id=parent_id)
        assert cb.parent_chatbot_id == parent_id

    def test_parent_chatbot_id_column_is_nullable(self):
        from server.app.modules.agents_hub.database.config_models import HubChatbot
        col = HubChatbot.__table__.c["parent_chatbot_id"]
        assert col.nullable is True

    def test_parent_chatbot_id_column_is_in_table(self):
        from server.app.modules.agents_hub.database.config_models import HubChatbot
        assert "parent_chatbot_id" in HubChatbot.__table__.c


# ---------------------------------------------------------------------------
# Tests de combinaciones
# ---------------------------------------------------------------------------

class TestHubChatbotFieldCombinations:

    def test_atomic_chatbot_with_agentic_mode(self):
        cb = _make_chatbot(kind="atomic", retrieval_mode="agentic")
        assert cb.kind == "atomic"
        assert cb.retrieval_mode == "agentic"

    def test_router_chatbot_has_no_retrieval_mode_enforced(self):
        """Un router puede tener cualquier retrieval_mode en Python
        (la restriccion de no-corpus es semantica, no de BD)."""
        cb = _make_chatbot(kind="router", retrieval_mode="vector")
        assert cb.kind == "router"

    def test_child_chatbot_references_parent_id(self):
        parent_id = uuid.uuid4()
        child = _make_chatbot(
            kind="atomic",
            retrieval_mode="agentic",
            parent_chatbot_id=parent_id,
        )
        assert child.parent_chatbot_id == parent_id
        assert child.kind == "atomic"

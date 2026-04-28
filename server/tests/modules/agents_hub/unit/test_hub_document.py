"""Tests del modelo HubDocument -- TDD RED (Prompt 9CBis.1).

Deben fallar con ImportError o AttributeError hasta que se implemente
HubDocument en operational_models.py (Prompt 9CBis.2).
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_async_session():
    """Sesion asyncpg mockeada con comportamiento minimo."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.delete = AsyncMock()
    session.get = AsyncMock(return_value=None)
    return session


def _minimal_doc(**kwargs):
    from server.app.modules.agents_hub.database.operational_models import HubDocument
    defaults = dict(
        chatbot_id=uuid.uuid4(),
        title="Reglamento de Permanencia",
        canonical_url="https://uji.es/normativa/permanencia.pdf",
        markdown_content="# Reglamento\n\nArt. 1...",
        content_hash="a" * 64,
        language="es",
        source_kind="upload",
        token_count=1234,
    )
    defaults.update(kwargs)
    return HubDocument(**defaults)


# ---------------------------------------------------------------------------
# Tests del modelo HubDocument
# ---------------------------------------------------------------------------

class TestHubDocumentModel:

    def test_hub_document_class_exists(self):
        """HubDocument debe existir en operational_models."""
        from server.app.modules.agents_hub.database.operational_models import HubDocument
        assert HubDocument is not None

    def test_hub_document_has_required_fields(self):
        from server.app.modules.agents_hub.database.operational_models import HubDocument
        required = [
            "id", "chatbot_id", "title", "canonical_url",
            "markdown_content", "content_hash", "language",
            "source_kind", "token_count", "created_at", "updated_at",
        ]
        for field in required:
            assert hasattr(HubDocument, field), f"HubDocument falta campo: {field}"

    def test_hub_document_optional_fields(self):
        from server.app.modules.agents_hub.database.operational_models import HubDocument
        assert hasattr(HubDocument, "section_path")

    def test_hub_document_lives_in_operational_base(self):
        from server.app.modules.agents_hub.database.base import HubOperationalBase
        from server.app.modules.agents_hub.database.operational_models import HubDocument
        assert issubclass(HubDocument, HubOperationalBase)

    def test_hub_document_tablename(self):
        from server.app.modules.agents_hub.database.operational_models import HubDocument
        assert HubDocument.__tablename__ == "hub_documents"

    def test_hub_document_source_kind_values(self):
        """source_kind acepta upload, crawler y manual."""
        from server.app.modules.agents_hub.database.operational_models import HubDocument
        # Solo comprobamos que el campo existe; la restriccion CHECK se valida en BD
        doc = _minimal_doc(source_kind="upload")
        assert doc.source_kind == "upload"
        doc2 = _minimal_doc(source_kind="crawler")
        assert doc2.source_kind == "crawler"

    def test_hub_document_instantiation(self):
        doc = _minimal_doc()
        assert doc.title == "Reglamento de Permanencia"
        assert doc.token_count == 1234
        assert doc.language == "es"
        assert doc.section_path is None


# ---------------------------------------------------------------------------
# Tests de HubDocumentChunk.document_id (FK opcional)
# ---------------------------------------------------------------------------

class TestHubDocumentChunkDocumentId:

    def test_hub_document_chunk_has_document_id_field(self):
        from server.app.modules.agents_hub.database.operational_models import HubDocumentChunk
        assert hasattr(HubDocumentChunk, "document_id")

    def test_hub_document_chunk_document_id_is_nullable(self):
        """document_id debe ser nullable para retrocompatibilidad con chunks anteriores."""
        from server.app.modules.agents_hub.database.operational_models import HubDocumentChunk
        col = HubDocumentChunk.__table__.c["document_id"]
        assert col.nullable is True

    def test_hub_document_chunk_can_set_document_id(self):
        from server.app.modules.agents_hub.database.operational_models import HubDocumentChunk
        doc_id = uuid.uuid4()
        chunk = HubDocumentChunk(
            chatbot_id=uuid.uuid4(),
            document_id=doc_id,
            content="fragmento",
            source_url="https://uji.es/normativa.pdf",
            content_hash="b" * 64,
            language="es",
        )
        assert chunk.document_id == doc_id

    def test_hub_document_chunk_document_id_defaults_to_none(self):
        from server.app.modules.agents_hub.database.operational_models import HubDocumentChunk
        chunk = HubDocumentChunk(
            chatbot_id=uuid.uuid4(),
            content="fragmento",
            source_url="u",
            content_hash="c" * 64,
            language="es",
        )
        assert chunk.document_id is None

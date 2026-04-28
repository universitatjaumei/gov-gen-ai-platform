"""Tests del post-validador de citas -- TDD."""
import uuid
from unittest.mock import MagicMock

from server.app.modules.agents_hub.services.retrieval.types import Source


def _make_source(url: str) -> Source:
    return Source(
        document_id=uuid.uuid4(),
        title="Norma",
        url=url,
        excerpt="texto",
        score=1.0,
    )


class TestHasValidCitations:

    def test_returns_true_when_at_least_one_valid_citation_present(self):
        from server.app.modules.agents_hub.agent.citation_validator import has_valid_citations
        text = "Consulta el reglamento [Norma Municipal](https://ej.com/norma.pdf) vigente."
        assert has_valid_citations(text, {"https://ej.com/norma.pdf"}) is True

    def test_returns_false_when_no_markdown_links(self):
        from server.app.modules.agents_hub.agent.citation_validator import has_valid_citations
        text = "La respuesta no tiene citas."
        assert has_valid_citations(text, {"https://ej.com/norma.pdf"}) is False

    def test_returns_false_when_citation_url_not_in_allowed(self):
        from server.app.modules.agents_hub.agent.citation_validator import has_valid_citations
        text = "Ver [otra fuente](https://otro.com/doc.pdf)."
        assert has_valid_citations(text, {"https://ej.com/norma.pdf"}) is False

    def test_detects_multiple_citations_in_same_paragraph(self):
        from server.app.modules.agents_hub.agent.citation_validator import has_valid_citations
        text = "Ver [A](https://a.com) y [B](https://b.com)."
        assert has_valid_citations(text, {"https://a.com", "https://b.com"}) is True


class TestEnforceCitationContract:

    def test_returns_text_unchanged_when_no_sources(self):
        from server.app.modules.agents_hub.agent.citation_validator import enforce_citation_contract
        text = "Hola! En que te puedo ayudar?"
        result = enforce_citation_contract(text, [], "vector")
        assert result == text

    def test_returns_text_when_at_least_one_valid_citation_present(self):
        from server.app.modules.agents_hub.agent.citation_validator import enforce_citation_contract
        sources = [_make_source("https://ej.com/norma.pdf")]
        text = "Segun [Norma](https://ej.com/norma.pdf) el plazo es 30 dias."
        result = enforce_citation_contract(text, sources, "vector")
        assert result == text

    def test_returns_fallback_when_sources_exist_but_no_citation(self):
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract, NO_CITATION_FALLBACK,
        )
        sources = [_make_source("https://ej.com/norma.pdf")]
        text = "El plazo es 30 dias."
        result = enforce_citation_contract(text, sources, "vector")
        assert result == NO_CITATION_FALLBACK

    def test_agentic_mode_with_empty_sources_returns_text_unchanged(self):
        from server.app.modules.agents_hub.agent.citation_validator import enforce_citation_contract
        text = "Buenos dias! Como puedo ayudarte?"
        result = enforce_citation_contract(text, [], "agentic")
        assert result == text

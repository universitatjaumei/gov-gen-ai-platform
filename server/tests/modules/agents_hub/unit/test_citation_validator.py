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
        result = enforce_citation_contract(text, [], "RAG")
        assert result == text

    def test_returns_text_when_at_least_one_valid_citation_present(self):
        from server.app.modules.agents_hub.agent.citation_validator import enforce_citation_contract
        sources = [_make_source("https://ej.com/norma.pdf")]
        text = "Segun [Norma](https://ej.com/norma.pdf) el plazo es 30 dias."
        result = enforce_citation_contract(text, sources, "RAG")
        assert result == text

    def test_returns_fallback_when_sources_exist_but_no_citation(self):
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract, NO_CITATION_FALLBACK,
        )
        sources = [_make_source("https://ej.com/norma.pdf")]
        text = "El plazo es 30 dias."
        result = enforce_citation_contract(text, sources, "RAG")
        assert result == NO_CITATION_FALLBACK

    def test_agentic_mode_with_empty_sources_returns_text_unchanged(self):
        from server.app.modules.agents_hub.agent.citation_validator import enforce_citation_contract
        text = "Buenos dias! Como puedo ayudarte?"
        result = enforce_citation_contract(text, [], "MD_AGENT_SELECTOR")
        assert result == text


class TestCitaDegradadaAlDocumento:
    """El contrato dejaba de proteger y empezaba a destruir.

    Medido el 2026-08-24 sobre las 25 consultas del lote ujirag: nueve respuestas se
    descartaban por citas, y ocho de ellas tenian la mejor recuperacion de toda la tanda
    -una con calidad 0,902-. Las dos causas, con las dos URLs delante:

    - SEIS de ocho arrastraban un guion bajo de mas: el bloque de fuentes del prompt escribia
      la URL en cursiva (`_URL: ..._`) y el modelo copiaba el caracter de cierre. Eso se
      arregla en el prompt, no aqui.
    - Las otras dos citaban el documento correcto con un ancla distinta de la admitida:
      `#art-1.7.a` cuando el fragmento venia anclado en `#art-1`, y `#Primer` cuando el
      fragmento no traia ancla ninguna.

    Tirar la respuesta entera por eso no protege de nada: el documento SI se recupero y SI se
    leyo. Lo que se hace ahora es degradar el enlace a la URL de la norma. Se pierde
    precision -el lector aterriza en la portada en vez de en el articulo-, nunca veracidad.

    Lo que el contrato sigue atrapando intacto, que es para lo que existe: que se cite un
    documento que nunca se recupero, y que no se cite nada.
    """

    def test_should_rewrite_an_unknown_anchor_to_the_document_url(self):
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )

        texto = "Pots anul·lar fins al 15 de desembre [Directrius, art. 1.7.a](https://uji.es/dir.html#art-1.7.a)."
        fuentes = [_make_source("https://uji.es/dir.html#art-1")]

        resultado = enforce_citation_contract(texto, fuentes, "RAG")

        assert "https://uji.es/dir.html)" in resultado
        assert "#art-1.7.a" not in resultado
        assert "15 de desembre" in resultado

    def test_should_rewrite_an_invented_anchor_when_the_source_has_none(self):
        """ORI-11: la URL admitida no traia ancla y el modelo se invento `#Primer`."""
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )

        texto = "Cal tenir 60 credits [Instruccio, apartat Primer](https://uji.es/ins.html#Primer)."
        fuentes = [_make_source("https://uji.es/ins.html")]

        resultado = enforce_citation_contract(texto, fuentes, "RAG")

        assert "(https://uji.es/ins.html)" in resultado
        assert "#Primer" not in resultado

    def test_should_keep_an_exact_anchor_untouched(self):
        """Si el modelo acierta el ancla, la cita fina se conserva: es mas util."""
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )

        texto = "Son quatre [Directrius, art. 3](https://uji.es/dir.html#art-3)."
        fuentes = [_make_source("https://uji.es/dir.html#art-3")]

        assert enforce_citation_contract(texto, fuentes, "RAG") == texto

    def test_should_still_reject_a_document_that_was_never_retrieved(self):
        """La proteccion que no se toca: citar algo que no se recupero sigue siendo fallback."""
        from server.app.modules.agents_hub.agent.citation_validator import (
            NO_CITATION_FALLBACK,
            enforce_citation_contract,
        )

        texto = "Segons la norma [Altra cosa](https://uji.es/otra.html#art-1)."
        fuentes = [_make_source("https://uji.es/dir.html#art-1")]

        assert enforce_citation_contract(texto, fuentes, "RAG") == NO_CITATION_FALLBACK

    def test_should_still_reject_an_answer_without_any_citation(self):
        from server.app.modules.agents_hub.agent.citation_validator import (
            NO_CITATION_FALLBACK,
            enforce_citation_contract,
        )

        fuentes = [_make_source("https://uji.es/dir.html#art-1")]

        assert (
            enforce_citation_contract("Son quatre convocatories.", fuentes, "RAG")
            == NO_CITATION_FALLBACK
        )

    def test_should_use_the_configured_no_answer_message_when_given(self):
        """El mensaje configurado por el chatbot solo se respetaba en la rama del quality
        gate. Por esta salia un texto fijo en castellano a preguntas hechas en valenciano."""
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )

        propio = "No he trobat fonament suficient. Contacta amb Infocampus."
        fuentes = [_make_source("https://uji.es/dir.html#art-1")]

        resultado = enforce_citation_contract(
            "Sense cap cita.", fuentes, "RAG", no_answer_message=propio
        )

        assert resultado == propio

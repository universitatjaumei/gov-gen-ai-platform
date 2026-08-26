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


class TestRemisionesAOtrasNormas:
    """HIB.0 — una remision no es una cita falsa.

    La regla, en palabras del usuario (2026-08-26): la respuesta debe citar la norma
    principal y, en su caso, las otras normas recuperadas y utilizadas para redactarla,
    pero NO las normas citadas por esas normas.

    Con `parent_child` el fragmento inyectado es el articulo entero, que trae dentro
    remisiones («conforme al articulo 118 de la Ley 9/2017»). El modelo las enlaza. Antes de
    este cambio, el contrato tiraba la respuesta ENTERA por eso: medido sobre el lote
    ujirag-2024, los descartes por citas pasaron de 1 con `structural` a 5 de 25 con padre,
    con la recuperacion sin cambios.
    """

    def test_should_keep_the_answer_when_it_mentions_a_norm_outside_the_retrieved_set(self):
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )

        texto = (
            "El termini es de sis anys [Reglament, art. 9](https://uji.es/reg.html#art-9), "
            "conforme a l'article 118 de la "
            "[Llei 9/2017](https://boe.es/buscar/act.php?id=BOE-A-2017-12902)."
        )
        fuentes = [_make_source("https://uji.es/reg.html#art-9")]

        resultado = enforce_citation_contract(texto, fuentes, "RAG")

        assert "sis anys" in resultado
        assert "[Reglament, art. 9](https://uji.es/reg.html#art-9)" in resultado

    def test_should_strip_the_link_of_a_reference_outside_the_retrieved_set(self):
        """La mencion se conserva; lo que se va es el enlace, que apunta a un texto que al
        modelo no se le entrego y que por tanto no puede fundamentar nada."""
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )

        texto = (
            "Segons el [Reglament, art. 9](https://uji.es/reg.html#art-9) i la "
            "[Llei 9/2017](https://boe.es/buscar/act.php?id=BOE-A-2017-12902)."
        )
        fuentes = [_make_source("https://uji.es/reg.html#art-9")]

        resultado = enforce_citation_contract(texto, fuentes, "RAG")

        assert "boe.es" not in resultado
        assert "Llei 9/2017" in resultado

    def test_should_still_reject_when_there_is_no_grounded_citation_at_all(self):
        """Si TODO lo que cita esta fuera del conjunto recuperado, no hay fundamento y se
        rinde: quitar los enlaces no puede convertir una respuesta sin apoyo en una valida."""
        from server.app.modules.agents_hub.agent.citation_validator import (
            NO_CITATION_FALLBACK,
            enforce_citation_contract,
        )

        texto = "Ho regula la [Llei 9/2017](https://boe.es/buscar/act.php?id=BOE-A-2017-12902)."
        fuentes = [_make_source("https://uji.es/reg.html#art-9")]

        assert enforce_citation_contract(texto, fuentes, "RAG") == NO_CITATION_FALLBACK

    def test_should_not_count_a_stripped_reference_as_a_grounded_citation(self):
        """El orden importa: primero se despoja, despues se comprueba que quede fundamento.
        Al reves, una remision enlazada contaria como cita y el contrato dejaria de proteger."""
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )

        texto = "Ho regula la [Llei 9/2017](https://boe.es/x)."
        fuentes = [_make_source("https://uji.es/reg.html#art-9")]
        propio = "No he trobat fonament suficient."

        assert enforce_citation_contract(texto, fuentes, "RAG", propio) == propio

    def test_should_degrade_the_anchor_before_stripping_the_link(self):
        """Un enlace al documento CORRECTO con un ancla que no es la recuperada se degrada al
        documento (2026-08-24) y sobrevive: no se despoja como si fuera una remision."""
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )

        texto = "Segons el [Reglament, art. 9.2](https://uji.es/reg.html#art-9-2)."
        fuentes = [_make_source("https://uji.es/reg.html#art-9")]

        resultado = enforce_citation_contract(texto, fuentes, "RAG")

        assert "(https://uji.es/reg.html)" in resultado
        assert "Reglament, art. 9.2" in resultado


class TestEnlazadoDeterministaDeCitasEnProsa:
    """HIB.0 — el modelo nombra bien la norma pero se deja la URL, y la respuesta se tira.

    Medido con la sonda el 2026-08-26 sobre SGE-01: el modelo respondio con detalle y correcto
    —1,5 creditos ECTS por claustral, 80% de asistencia— citando asi:

        [Reglamento sobre reconocimiento y transferencia de creditos..., ANEXO II, apartado 3]

    Corchetes sin URL: no es un enlace markdown, el contrato no encuentra ninguna cita valida y
    descarta la respuesta entera. RES.5 ya habia previsto esta forma y aplazo el enlazado
    determinista porque midio CERO casos en 85 respuestas; ese cero ha caducado.

    La regla que esto respeta (usuario, 2026-08-26): se enlaza la norma que se USA. Un titulo
    que no esta entre lo recuperado NO se enlaza, aunque el modelo lo escriba entre corchetes.
    """

    TITULO = (
        "Reglamento sobre reconocimiento y transferencia de creditos en los estudios "
        "universitarios oficiales de grado y máster en la Universitat Jaume I"
    )
    URL = "http://127.0.0.1:4174/html/es_Reglamento_sobre_reconocimiento.html#annex-2"

    def _fuente(self):
        import uuid as _uuid

        from server.app.modules.agents_hub.services.retrieval.types import Source

        return Source(
            document_id=_uuid.uuid4(), title=self.TITULO, url=self.URL,
            excerpt="texto", score=1.0,
        )

    def test_should_link_a_prose_citation_that_names_a_retrieved_document(self):
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )

        texto = (
            f"Pots convalidar 1,5 credits ECTS [{self.TITULO}, ANEXO II, apartado 3]."
        )

        resultado = enforce_citation_contract(texto, [self._fuente()], "RAG")

        assert self.URL in resultado
        assert "1,5 credits" in resultado

    def test_should_keep_the_prose_detail_after_the_title(self):
        """«ANEXO II, apartado 3» es informacion que el lector necesita: el enlace se anade,
        el detalle no se pierde."""
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )

        texto = f"Segons [{self.TITULO}, ANEXO II, apartado 3]."

        resultado = enforce_citation_contract(texto, [self._fuente()], "RAG")

        assert "ANEXO II, apartado 3" in resultado

    def test_should_not_link_a_prose_citation_of_a_document_not_retrieved(self):
        """El enlazado determinista NO amplia lo citable: solo pone la URL de lo que ya se
        recupero. Una norma que el articulo menciona sigue sin enlace."""
        from server.app.modules.agents_hub.agent.citation_validator import (
            NO_CITATION_FALLBACK,
            enforce_citation_contract,
        )

        texto = "Ho regula la [Llei 9/2017, de 8 de novembre, de Contractes, art. 118]."

        resultado = enforce_citation_contract(texto, [self._fuente()], "RAG")

        assert resultado == NO_CITATION_FALLBACK

    def test_should_prefer_the_longest_matching_title(self):
        """Dos normas cuyo titulo empieza igual: gana la mas especifica, no la primera."""
        import uuid as _uuid

        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )
        from server.app.modules.agents_hub.services.retrieval.types import Source

        corto = Source(
            document_id=_uuid.uuid4(), title="Reglament de permanencia",
            url="https://uji.es/corto.html", excerpt="t", score=1.0,
        )
        largo = Source(
            document_id=_uuid.uuid4(),
            title="Reglament de permanencia per als estudis de grau i master",
            url="https://uji.es/largo.html", excerpt="t", score=1.0,
        )
        texto = "Segons el [Reglament de permanencia per als estudis de grau i master, art. 4]."

        resultado = enforce_citation_contract(texto, [corto, largo], "RAG")

        assert "https://uji.es/largo.html" in resultado
        assert "https://uji.es/corto.html" not in resultado

    def test_should_leave_an_existing_markdown_link_untouched(self):
        from server.app.modules.agents_hub.agent.citation_validator import (
            enforce_citation_contract,
        )

        texto = f"Segons [{self.TITULO}]({self.URL})."

        resultado = enforce_citation_contract(texto, [self._fuente()], "RAG")

        assert resultado == texto

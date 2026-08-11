"""Tests FAQ.1 — una pregunta, un encabezado, un fragmento.

Las preguntas frecuentes se ingieren como documentos (`content_class: faq`), no como
ejemplos en el prompt ni como dataset dorado. La razón de fondo: **el texto de la pregunta es
un objetivo de embedding casi perfecto**, porque se parece a lo que la persona escribe mucho
más que el artículo que la fundamenta. Una FAQ recupera mejor que su propia norma.

Pero eso solo funciona si **cada pregunta y su respuesta caen en el mismo fragmento**. El
troceador parte por encabezados; si las preguntas van en negrita o en una lista, el documento
entero cae en uno o dos fragmentos y la recuperación devuelve un bloque con veinte preguntas
de las que diecinueve no vienen a cuento. Y en el peor caso, un corte deja **media pregunta
con la respuesta de otra** — que es un error que no se ve al leer la respuesta.

De ahí el formato: la pregunta **es** el encabezado, con su ancla `{#faq-N}` para que la cita
apunte a la pregunta y no al documento entero.
"""
from __future__ import annotations

import pytest

FAQ_CONFORME = """---
language: es
id_publicacio: FAQ-UGITJ
title: Preguntas frecuentes de la UGITJ
content_class: faq
---

# Preguntas frecuentes de la UGITJ

##### ¿Cómo se justifica una dieta por asistencia a un curso? {#faq-1}

Se justifica con el formulario de la unidad y el certificado de asistencia. El importe
máximo es el del grupo que corresponda al puesto.

Norma que lo sostiene: Decreto 80/2025 de indemnizaciones.

##### ¿Qué plazo hay para presentar la justificación? {#faq-2}

Un mes desde la finalización del curso. Pasado el plazo hay que motivar el retraso.
"""

FAQ_CON_NEGRITAS = """---
language: es
id_publicacio: FAQ-MALA
title: Preguntas frecuentes mal formateadas
content_class: faq
---

# Preguntas frecuentes

**¿Cómo se justifica una dieta por asistencia a un curso?**

Se justifica con el formulario de la unidad.

**¿Qué plazo hay para presentar la justificación?**

Un mes desde la finalización del curso.
"""

FAQ_EN_LISTA = """---
language: es
id_publicacio: FAQ-LISTA
title: Preguntas frecuentes en lista
content_class: faq
---

# Preguntas frecuentes

- ¿Cómo se justifica una dieta? Con el formulario de la unidad.
- ¿Qué plazo hay? Un mes desde la finalización.
"""


def _cuerpo(md: str) -> str:
    from server.app.modules.agents_hub.ingestion.corpus.frontmatter import (
        parse_frontmatter,
    )

    _, cuerpo = parse_frontmatter(md)
    return cuerpo


class TestElTroceadoDeUnaFaqBienFormateada:

    def test_should_chunk_one_question_and_its_answer_together(self):
        from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker

        chunks = MarkdownChunker().split(_cuerpo(FAQ_CONFORME))

        con_dieta = [c for c in chunks if "dieta" in c.content.lower()]
        assert con_dieta, "no se recuperó el fragmento de la pregunta de la dieta"
        # La respuesta viaja con su pregunta: si no, el fragmento recuperado no responde.
        assert any("formulario" in c.content.lower() for c in con_dieta)

    def test_should_not_merge_two_consecutive_questions_in_one_chunk(self):
        """Es el fallo que hace inútil una FAQ: recuperar un bloque con veinte preguntas."""
        from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker

        chunks = MarkdownChunker().split(_cuerpo(FAQ_CONFORME))

        mezclados = [
            c
            for c in chunks
            if "dieta" in c.content.lower() and "plazo" in c.content.lower()
        ]
        assert not mezclados, "dos preguntas distintas cayeron en el mismo fragmento"

    def test_should_keep_the_faq_anchor_in_the_chunk_metadata(self):
        """El ancla es lo que permite citar LA PREGUNTA y no el documento entero."""
        from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker

        chunks = MarkdownChunker().split(_cuerpo(FAQ_CONFORME))
        anclas = {c.metadata.get("ancora") for c in chunks}

        assert "faq-1" in anclas, anclas
        assert "faq-2" in anclas, anclas


class TestLaValidacionDelFormato:
    """La comprobación existe porque el error es fácil de cometer y difícil de ver: un `.md`
    de FAQ con negritas se ingiere sin protestar y responde mal a partir de entonces."""

    def test_should_reject_a_faq_whose_questions_are_bold_instead_of_headings(self):
        from server.app.modules.agents_hub.ingestion.corpus.faq import (
            FaqFormatoInvalido,
            assert_formato_faq,
        )

        with pytest.raises(FaqFormatoInvalido):
            assert_formato_faq(_cuerpo(FAQ_CON_NEGRITAS))

    def test_should_reject_a_faq_written_as_a_list(self):
        from server.app.modules.agents_hub.ingestion.corpus.faq import (
            FaqFormatoInvalido,
            assert_formato_faq,
        )

        with pytest.raises(FaqFormatoInvalido):
            assert_formato_faq(_cuerpo(FAQ_EN_LISTA))

    def test_should_explain_the_format_instead_of_just_refusing(self):
        """Quien escribe la FAQ tiene que saber qué corregir sin abrir el código."""
        from server.app.modules.agents_hub.ingestion.corpus.faq import (
            FaqFormatoInvalido,
            assert_formato_faq,
        )

        with pytest.raises(FaqFormatoInvalido) as exc:
            assert_formato_faq(_cuerpo(FAQ_CON_NEGRITAS))

        mensaje = str(exc.value).lower()
        assert "encabezado" in mensaje
        assert "faq-" in mensaje

    def test_should_accept_a_faq_document_that_conforms(self):
        from server.app.modules.agents_hub.ingestion.corpus.faq import assert_formato_faq

        assert_formato_faq(_cuerpo(FAQ_CONFORME))  # no lanza

    def test_should_require_an_anchor_on_every_question(self):
        """Sin ancla, la cita apunta al documento entero y se pierde qué pregunta lo dijo."""
        from server.app.modules.agents_hub.ingestion.corpus.faq import (
            FaqFormatoInvalido,
            assert_formato_faq,
        )

        sin_ancla = FAQ_CONFORME.replace(" {#faq-2}", "")

        with pytest.raises(FaqFormatoInvalido, match="(?i)ancla"):
            assert_formato_faq(_cuerpo(sin_ancla))

    def test_should_only_apply_to_faq_documents(self):
        """Una norma NO tiene que cumplir esto: sus unidades citables son artículos."""
        from server.app.modules.agents_hub.ingestion.corpus.faq import (
            debe_validarse_como_faq,
        )

        assert debe_validarse_como_faq({"content_class": "faq"}) is True
        assert debe_validarse_como_faq({"content_class": "regulation"}) is False
        assert debe_validarse_como_faq({}) is False


class TestLaValidacionEstaEnchufada:
    """Un validador que nadie llama es documentación con sintaxis de Python. Estos dos tests
    comprueban que está en el camino de las **dos** vías de entrada al corpus."""

    async def test_should_reject_a_bad_faq_from_the_cli_source(self, tmp_path):
        from server.app.modules.agents_hub.ingestion.corpus.manifest import (
            CorpusValidationError,
        )
        from server.app.modules.agents_hub.ingestion.corpus.source import (
            LocalDirectorySource,
        )

        (tmp_path / "faq.md").write_text(FAQ_CON_NEGRITAS, encoding="utf-8")

        with pytest.raises(CorpusValidationError, match="(?i)encabezado"):
            await LocalDirectorySource(tmp_path).list_entries()

    async def test_should_accept_a_good_faq_from_the_cli_source(self, tmp_path):
        from server.app.modules.agents_hub.ingestion.corpus.source import (
            LocalDirectorySource,
        )

        (tmp_path / "faq.md").write_text(FAQ_CONFORME, encoding="utf-8")

        entradas = await LocalDirectorySource(tmp_path).list_entries()

        assert len(entradas) == 1
        assert entradas[0].content_class == "faq"

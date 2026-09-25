"""Issue #164 — el encabezado del fragmento no puede perder el separador.

**Qué se vio en producción el 2026-09-25.** La base guardaba esto como encabezado del artículo 1
de la Ley 39/2015:

    'Art\\xedculo1. Objeto de la Ley'

Sin separador. Igual el 2, el 3, y los 133 artículos de esa ley, y los de la Ley 40/2015. En total
**343 encabezados de 7 normas externas**.

**El `.md` no tiene la culpa**: escribe `Artículo\\xa01.` con espacio duro, que es como titula el BOE
esas normas. Quien lo borra somos nosotros: `MarkdownHeaderTextSplitter` limpia la línea del
encabezado con `"".join(filter(str.isprintable, linea))`, y `str.isprintable` considera **no
imprimible cualquier separador Unicode que no sea el espacio ASCII** —toda la categoría `Zs`—. Así
que no lo sustituye: lo suprime.

**Por qué importa y no es cosmético.** El encabezado es el contexto estructural que viaja con el
fragmento hasta el modelo —`embedding_text` lleva título del documento y jerarquía de encabezados,
y nada más— y es lo que se le enseña al usuario junto a la cita. Además `articulo1` no es el mismo
token que `artículo 1` para la búsqueda de texto completo.

**Y tiene un efecto de segundo orden ya medido**: el detector de la issue #158 cruza el corpus con
el BOE por esa cadena, y 292 preceptos de esas dos leyes no cruzaban. Se supo sólo porque ese
detector lleva la cuenta de lo que no consigue leer; sin ella habría informado «ningún artículo
derogado en la LPAC» sin fallar ni una vez.

**Se arregla antes de partir, no después.** Una vez `str.isprintable` ha borrado el separador, el
hueco no se puede recuperar sin inventárselo, que es justo lo que este proyecto no hace con las
citas.
"""

from __future__ import annotations

from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker


def _encabezados(chunks) -> list[str]:
    return [c.metadata.get("header_5", "") for c in chunks]


class TestElSeparadorSobreviveALaParticion:

    def test_el_espacio_duro_se_conserva_como_espacio(self):
        """El caso real: `Artículo\xa01.` del texto consolidado de la Ley 39/2015."""
        md = "# Ley 39/2015\n\n##### Artículo\xa01. Objeto de la Ley {#art-1}\n\nTexto del artículo.\n"

        chunks = MarkdownChunker(chunk_size=500).split(md)

        assert any("Artículo 1. Objeto de la Ley" == e for e in _encabezados(chunks)), (
            f"el encabezado ha perdido el separador: {_encabezados(chunks)}"
        )

    def test_ningun_separador_unicode_desaparece_del_encabezado(self):
        """No es sólo el `\xa0`. `str.isprintable` descarta **toda** la categoría `Zs` menos el
        espacio ASCII, así que el espacio fino y el ideográfico caerían igual el día que el BOE
        use uno."""
        for raro in ("\xa0", " ", " ", "　"):
            md = f"# Norma\n\n##### Artículo{raro}7. Rúbrica {{#art-7}}\n\nCuerpo.\n"

            chunks = MarkdownChunker(chunk_size=500).split(md)

            assert "Artículo 7. Rúbrica" in _encabezados(chunks), (
                f"con el separador {raro!r} el encabezado sale como {_encabezados(chunks)}"
            )

    def test_el_ancla_se_sigue_extrayendo(self):
        """La normalización va antes de partir, así que no puede estropear lo que ya funcionaba."""
        md = "# Norma\n\n##### Artículo\xa07. Rúbrica {#art-7}\n\nCuerpo.\n"

        chunks = MarkdownChunker(chunk_size=500).split(md)

        assert {c.metadata.get("ancora") for c in chunks} == {"art-7"}

    def test_el_cuerpo_tampoco_se_queda_con_palabras_pegadas(self):
        """El espacio duro abunda en el cuerpo del BOE —«artículo\xa020 de la Ley»—, y ahí nadie lo
        borra pero tampoco es un espacio para la búsqueda de texto completo. Si se normaliza el
        encabezado y no el cuerpo, el mismo artículo queda escrito de dos maneras dentro del mismo
        fragmento."""
        md = "# Norma\n\n##### Artículo 7. Rúbrica {#art-7}\n\nSegún el artículo\xa020 de la Ley.\n"

        chunks = MarkdownChunker(chunk_size=500).split(md)

        assert any("artículo 20 de la Ley" in c.content for c in chunks), (
            f"el cuerpo conserva el separador raro: {[c.content for c in chunks]}"
        )

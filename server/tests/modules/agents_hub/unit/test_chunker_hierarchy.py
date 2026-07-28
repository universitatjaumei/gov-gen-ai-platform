"""Tests TDD — Chunker jerárquico de 5 niveles, anclas y tablas (Prompt ING.0.4).

Especificación del formato: `docs/CONTRATO_MD_CORPUS.md`. Este prompt implementa el lado
consumidor: el nivel lo determina el TIPO de elemento, así que el chunker puede fiarse de
él, y hay saltos de nivel legítimos (`#####` bajo `##` en las disposiciones) que no son
errores.
"""
from __future__ import annotations

import pytest

NORMA = """# Reglament sobre indemnitzacions

## Preàmbul {#preambul}

Text del preàmbul.

## Títol I. Disposicions generals {#tit-1}

### Capítol I. Objecte {#cap-1}

##### Article 1. Objecte {#art-1}

Aquest reglament regula les indemnitzacions.

## Títol II. Indemnitzacions {#tit-2}

### Capítol III. Dietes {#cap-3}

#### Secció 2a. Manutenció {#cap-3-sec-2}

##### Article 14. Import de la dieta {#art-14}

L'import de la dieta és de 53,34 euros.

## Disposicions addicionals

##### Disposició addicional primera. Actualització {#da-1}

Els imports s'actualitzen anualment.

## Annex I. Quadre d'imports {#annex-1}

Contingut de l'annex.
"""

SIN_DIVISIONES = """# Instrucció 1/2023

##### Article 1. Objecte {#art-1}

Text.

##### Article 2. Àmbit {#art-2}

Més text.
"""


def _chunks(contenido: str, **kwargs):
    from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker

    return MarkdownChunker(**kwargs).split(contenido)


def _por_ancora(contenido: str, **kwargs) -> dict:
    return {
        c.metadata.get("ancora"): c
        for c in _chunks(contenido, **kwargs)
        if c.metadata.get("ancora")
    }


# ───────────────────────── Jerarquía ─────────────────────────


class TestJerarquia:

    def test_should_split_on_five_heading_levels(self):
        from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker

        niveles = dict(MarkdownChunker().headers_to_split)
        assert niveles["#"] == "header_1"
        assert niveles["##"] == "header_2"
        assert niveles["###"] == "header_3"
        assert niveles["####"] == "header_4"
        assert niveles["#####"] == "header_5"

    def test_should_treat_article_as_level_five_without_intermediate_divisions(self):
        """Una norma sin títulos ni capítulos: los artículos siguen en '#####'."""
        anclas = _por_ancora(SIN_DIVISIONES)

        assert set(anclas) == {"art-1", "art-2"}
        assert anclas["art-1"].metadata["header_5"].startswith("Article 1")
        # No se inventan niveles intermedios
        assert "header_3" not in anclas["art-1"].metadata

    def test_should_handle_level_jump_from_group_to_citable_unit(self):
        """Las disposiciones son '#####' bajo un grupo '##': salto legítimo."""
        anclas = _por_ancora(NORMA)

        da = anclas["da-1"]
        assert da.metadata["header_2"].startswith("Disposicions addicionals")
        assert da.metadata["header_5"].startswith("Disposició addicional primera")
        assert "header_3" not in da.metadata
        assert "header_4" not in da.metadata

    def test_should_handle_document_without_articulado(self):
        """41 de los 226 documentos son así: protocolos, planes, anexos de tablas."""
        sin_articulado = "# Pla d'igualtat\n\n## Objectius\n\nText.\n\n## Mesures\n\nMés.\n"
        chunks = _chunks(sin_articulado)

        assert len(chunks) >= 2
        assert all(c.metadata.get("ancora") is None for c in chunks)

    def test_should_handle_md_without_anchors_or_hierarchy(self):
        plano = "Text sense cap encapçalament ni ancora.\n"
        chunks = _chunks(plano)

        assert len(chunks) == 1
        assert chunks[0].metadata.get("ancora") is None
        assert chunks[0].metadata.get("ruta") == []


# ───────────────────────── Anclas ─────────────────────────


class TestAnclas:

    def test_should_extract_article_anchor_into_metadata(self):
        anclas = _por_ancora(NORMA)
        assert "art-14" in anclas
        assert "art-1" in anclas

    def test_should_extract_anchor_from_disposicio_and_annex(self):
        anclas = _por_ancora(NORMA)
        assert "da-1" in anclas
        assert "annex-1" in anclas
        assert "preambul" in anclas

    def test_should_strip_anchor_token_from_chunk_text(self):
        """El token es ruido para el embedding y para el usuario."""
        for chunk in _chunks(NORMA):
            assert "{#" not in chunk.content, chunk.content[:80]

    def test_should_strip_anchor_token_from_header_metadata(self):
        anclas = _por_ancora(NORMA)
        for chunk in anclas.values():
            for clave, valor in chunk.metadata.items():
                if clave.startswith("header_"):
                    assert "{#" not in valor

    def test_should_keep_heading_text_in_chunk_content(self):
        """strip_headers=False sigue vigente: RAG.7 necesita el encabezado en el texto."""
        art14 = _por_ancora(NORMA)["art-14"]
        assert "Article 14" in art14.content
        assert "Import de la dieta" in art14.content

    def test_una_ancla_mal_formada_no_rompe_el_troceado(self):
        roto = "# T\n\n##### Article 1. Objecte {#}\n\nText.\n"
        chunks = _chunks(roto)
        assert len(chunks) >= 1
        assert chunks[-1].metadata.get("ancora") is None


# ───────────────────────── Ruta estructural ─────────────────────────


class TestRuta:

    def test_should_record_ancestor_route_in_metadata(self):
        """Un artículo recuperado aislado no debe perder el contexto de su capítulo."""
        art14 = _por_ancora(NORMA)["art-14"]
        ruta = art14.metadata["ruta"]

        assert "Títol II. Indemnitzacions" in ruta
        assert "Capítol III. Dietes" in ruta
        # el propio encabezado del artículo NO forma parte de su ruta
        assert not any("Article 14" in paso for paso in ruta)

    def test_should_include_seccio_in_the_route(self):
        """La Sección es el nivel que faltaba en la primera versión del plan."""
        art14 = _por_ancora(NORMA)["art-14"]
        assert "Secció 2a. Manutenció" in art14.metadata["ruta"]

    def test_la_ruta_conserva_el_orden_de_lo_general_a_lo_particular(self):
        ruta = _por_ancora(NORMA)["art-14"].metadata["ruta"]
        indices = [
            ruta.index(p) for p in ruta if p.startswith(("Títol", "Capítol", "Secció"))
        ]
        assert indices == sorted(indices)
        assert ruta[0].startswith("Reglament")  # el título del documento abre la ruta


# ───────────────────────── URL de cita ─────────────────────────


class TestUrlDeCita:

    def test_should_build_citation_url_with_anchor_fragment(self):
        from server.app.modules.agents_hub.services.retrieval.citations import with_anchor

        assert (
            with_anchor("https://www.uji.es/REG-020", {"ancora": "art-14"})
            == "https://www.uji.es/REG-020#art-14"
        )

    def test_sin_ancla_devuelve_la_url_intacta(self):
        from server.app.modules.agents_hub.services.retrieval.citations import with_anchor

        assert with_anchor("https://www.uji.es/x", {}) == "https://www.uji.es/x"
        assert with_anchor("https://www.uji.es/x", {"ancora": None}) == "https://www.uji.es/x"

    def test_no_duplica_el_fragmento_si_la_url_ya_lo_trae(self):
        from server.app.modules.agents_hub.services.retrieval.citations import with_anchor

        assert (
            with_anchor("https://www.uji.es/x#art-9", {"ancora": "art-14"})
            == "https://www.uji.es/x#art-14"
        )

    def test_tolera_url_vacia(self):
        from server.app.modules.agents_hub.services.retrieval.citations import with_anchor

        assert with_anchor("", {"ancora": "art-14"}) == ""
        assert with_anchor(None, {"ancora": "art-14"}) is None


# ───────────────────────── Regla dura heredada por RAG.7 ─────────────────────────


class TestSinTaxonomiaEnElTexto:

    def test_should_not_include_taxonomy_in_embedded_text(self):
        """CLAUDE.md §5: la taxonomía nunca entra en el texto que se embebe. Si entrara,
        cada revisión del vocabulario costaría un re-embedding del corpus."""
        from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker

        chunks = MarkdownChunker().split(
            NORMA,
            metadata={
                "document_id": "abc",
                "ambit_principal": "administracio",
                "submateries": ["indemnitzacions-i-dietes"],
            },
        )
        for chunk in chunks:
            assert "administracio" not in chunk.content
            assert "indemnitzacions-i-dietes" not in chunk.content


# ───────────────────────── Tablas ─────────────────────────

TABLA_PEQUENA = """# Conveni

##### Article 20. Retribucions {#art-20}

Les retribucions són les següents:

<!-- TABLE-IMG: img/conveni/t01.png | page=21 2x6 -->

<!-- TABLA-TEXT: t01.png | pàg. 21 | 2x6 | markdown -->
| Sou | CD | CE |
| --- | --- | --- |
| 1.288,31 € | 924,48 € | 294,95 € |
<!-- /TABLA-TEXT -->
"""


def _tabla_grande(filas: int = 60) -> str:
    cuerpo = "\n".join(
        f"| Categoria {i} | {1000 + i},00 € | {500 + i},00 € | {200 + i},00 € |"
        for i in range(filas)
    )
    return (
        "# Pressupost\n\n##### Article 5. Preus públics {#art-5}\n\n"
        "<!-- TABLE-IMG: img/pressupost/t07.png | page=53 60x4 -->\n\n"
        f"<!-- TABLA-TEXT: t07.png | pàg. 53 | {filas}x4 | markdown -->\n"
        "| Categoria | Import A | Import B | Import C |\n"
        "| --- | --- | --- | --- |\n"
        f"{cuerpo}\n"
        "<!-- /TABLA-TEXT -->\n"
    )


TABLA_HTML = """# Documentació

##### Article 3. Calendari {#art-3}

<!-- TABLA-TEXT: t02.png | pàg. 4 | 30x3 | html -->
<table>
<thead><tr><th>Titulació</th><th>Curs</th><th>Observacions</th></tr></thead>
<tbody>
""" + "\n".join(
    f"<tr><td>Titulacio {i}</td><td>2026/{i:02d}</td><td>Observacio prou llarga per omplir {i}</td></tr>"
    for i in range(40)
) + """
</tbody>
</table>
<!-- /TABLA-TEXT -->
"""


class TestTablas:

    def _tabla_chunks(self, contenido: str, **kwargs):
        return [c for c in _chunks(contenido, **kwargs) if c.metadata.get("es_taula")]

    def test_should_keep_small_table_block_in_one_chunk(self):
        tablas = self._tabla_chunks(TABLA_PEQUENA)
        assert len(tablas) == 1
        assert "1.288,31" in tablas[0].content

    def test_should_not_split_table_block_that_fits_even_over_chunk_size(self):
        """Una tabla partida vale menos que una tabla larga: si cabe en el presupuesto
        de tabla, no se parte aunque supere chunk_size."""
        contenido = _tabla_grande(filas=20)
        tablas = self._tabla_chunks(contenido, chunk_size=200, table_chunk_size=4000)

        assert len(tablas) == 1
        assert len(tablas[0].content) > 200

    def test_should_repeat_header_row_in_every_chunk_of_a_split_pipe_table(self):
        """Sin esto, todo fragmento menos el primero queda con importes sin nombre de
        columna: se recupera igual y sostiene una respuesta segura y falsa."""
        tablas = self._tabla_chunks(_tabla_grande(60), table_chunk_size=600)

        assert len(tablas) > 1
        for chunk in tablas:
            assert "| Categoria | Import A | Import B | Import C |" in chunk.content
            assert "| --- |" in chunk.content

    def test_should_split_pipe_table_on_row_boundaries_never_mid_row(self):
        tablas = self._tabla_chunks(_tabla_grande(60), table_chunk_size=600)

        for chunk in tablas:
            for linea in chunk.content.splitlines():
                if linea.strip().startswith("|"):
                    assert linea.strip().endswith("|"), f"fila cortada: {linea!r}"

    def test_ninguna_fila_se_pierde_ni_se_duplica_al_partir(self):
        tablas = self._tabla_chunks(_tabla_grande(60), table_chunk_size=600)

        filas = []
        for chunk in tablas:
            for linea in chunk.content.splitlines():
                if linea.startswith("| Categoria ") and "Import A" not in linea:
                    filas.append(linea)
        assert len(filas) == 60
        assert len(set(filas)) == 60

    def test_repite_la_leyenda_y_la_cabecera_cuando_la_tabla_lleva_titulo(self):
        """El corpus curado mete la leyenda DENTRO del bloque, antes de la tabla. La fila
        de cabecera es la que precede al separador `| --- |`, no la primera línea."""
        con_leyenda = _tabla_grande(60).replace(
            "| Categoria | Import A | Import B | Import C |",
            "**Retribucions del professorat permanent laboral**\n"
            "| Categoria | Import A | Import B | Import C |",
            1,
        )
        tablas = self._tabla_chunks(con_leyenda, table_chunk_size=600)

        assert len(tablas) > 1
        for chunk in tablas:
            assert "**Retribucions del professorat permanent laboral**" in chunk.content
            assert "| Categoria | Import A | Import B | Import C |" in chunk.content
            # y la cabecera no se cuela como fila de datos
            assert chunk.content.count("| Categoria | Import A |") == 1

    def test_should_repeat_thead_and_reopen_table_tag_for_split_html_table(self):
        tablas = self._tabla_chunks(TABLA_HTML, table_chunk_size=800)

        assert len(tablas) > 1
        for chunk in tablas:
            assert chunk.content.count("<table") == 1
            assert "</table>" in chunk.content
            assert "<th>Titulació</th>" in chunk.content

    def test_should_record_table_provenance_in_chunk_metadata(self):
        tabla = self._tabla_chunks(TABLA_PEQUENA)[0]

        assert tabla.metadata["taula_origen"] == "t01.png"
        assert "21" in str(tabla.metadata["pagina"])
        assert tabla.metadata["dimensions"] == "2x6"
        assert tabla.metadata["taula_format"] == "markdown"

    def test_should_read_format_from_marker_not_from_content(self):
        """El marcador manda: no se adivina mirando el contenido."""
        marcado_html = TABLA_PEQUENA.replace("| markdown -->", "| html -->")
        tabla = self._tabla_chunks(marcado_html)[0]
        assert tabla.metadata["taula_format"] == "html"

    def test_should_handle_table_block_without_declared_format(self):
        sin_formato = TABLA_PEQUENA.replace(" | markdown -->", " -->")
        tablas = self._tabla_chunks(sin_formato)
        assert len(tablas) == 1
        assert tablas[0].metadata["taula_format"] == "markdown"

    def test_la_tabla_hereda_la_ancora_y_la_ruta_de_su_articulo(self):
        tabla = self._tabla_chunks(TABLA_PEQUENA)[0]
        assert tabla.metadata["ancora"] == "art-20"
        assert tabla.metadata["ruta"][0].startswith("Conveni")

    def test_la_prosa_y_la_tabla_de_una_seccion_no_se_mezclan(self):
        chunks = _chunks(TABLA_PEQUENA)
        prosa = [c for c in chunks if not c.metadata.get("es_taula")]

        assert any("Les retribucions són les següents" in c.content for c in prosa)
        assert all("1.288,31" not in c.content for c in prosa)

    def test_el_marcador_de_imagen_no_contamina_el_chunk_de_la_tabla(self):
        tabla = self._tabla_chunks(TABLA_PEQUENA)[0]
        assert "TABLE-IMG" not in tabla.content


# ───────────────────────── section_path retirada (Caso B) ─────────────────────────


class TestSectionPathRetirada:

    def test_la_columna_ya_no_existe_en_el_modelo(self):
        """Declarada y JAMÁS escrita en todo server/app. Se retira por Caso B en vez de
        dejarla en el limbo: la ruta estructural vive en chunk_metadata['ruta']."""
        from server.app.modules.agents_hub.database.operational_models import HubDocument

        assert "section_path" not in HubDocument.__table__.c

    def test_no_queda_ninguna_referencia_en_el_codigo(self):
        from pathlib import Path

        raiz = Path(__file__).resolve().parents[4] / "app"
        con_referencia = [
            str(p.relative_to(raiz))
            for p in raiz.rglob("*.py")
            if "section_path" in p.read_text(encoding="utf-8", errors="replace")
        ]
        assert con_referencia == []

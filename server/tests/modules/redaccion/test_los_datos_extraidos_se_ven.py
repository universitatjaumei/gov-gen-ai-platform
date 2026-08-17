"""PRO.3 — los datos extraídos tienen que verse en el informe.

Con el script aprobado ejecutándose, el bloque acababa `extracted` con su tabla y su métrica
dentro… y el informe salía vacío. Dos renderizadores y los dos se lo comían:

- La **vista previa** (`_block_content_to_html`) sólo mira `content['text']` y
  `content['value']`. El contenido de cualquier extracción es `{tables, metrics, free_text}`,
  así que devolvía cadena vacía: ninguna extracción se ha visto nunca en la vista previa, ni
  por script ni por Excel ni por PDF.
- El **ensamblado** hacía `content.get('text') or str(content)`, o sea que volcaba el
  diccionario de Python tal cual en el documento final. Un informe con `{'tables': [{'name':`
  dentro no es un informe.

Lo que se ve no es un detalle estético: es el producto.
"""
from __future__ import annotations

_CONTENIDO = {
    "tables": [{
        "name": "ejecucion_presupuestaria",
        "headers": ["capitulo", "credito_inicial", "obligaciones_reconocidas"],
        "rows": [["1 Personal", "120000", "96000"], ["2 Corrientes", "45000", "40500"]],
        "source_page": None,
    }],
    "metrics": [{"name": "porcentaje_ejecucion", "value": 68.52, "unit": "%"}],
    "free_text": None,
}


class TestVistaPrevia:
    def test_should_pintar_la_tabla_extraida(self) -> None:
        from server.app.modules.redaccion.services.preview_builder import (
            _block_content_to_html,
        )

        html = _block_content_to_html(_CONTENIDO)

        assert "<table" in html
        assert "capitulo" in html
        assert "1 Personal" in html
        assert "96000" in html

    def test_should_pintar_las_metricas_con_su_unidad(self) -> None:
        from server.app.modules.redaccion.services.preview_builder import (
            _block_content_to_html,
        )

        html = _block_content_to_html(_CONTENIDO)

        assert "porcentaje_ejecucion" in html
        assert "68.52" in html
        assert "%" in html

    def test_should_escapar_lo_que_venga_del_fichero(self) -> None:
        """Los datos vienen de un fichero que sube cualquiera: no son HTML de confianza."""
        from server.app.modules.redaccion.services.preview_builder import (
            _block_content_to_html,
        )

        html = _block_content_to_html({
            "tables": [{
                "name": "t",
                "headers": ["a"],
                "rows": [["<script>alert(1)</script>"]],
                "source_page": None,
            }],
            "metrics": [],
            "free_text": None,
        })

        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_should_seguir_pintando_el_texto_de_un_bloque_de_ia(self) -> None:
        from server.app.modules.redaccion.services.preview_builder import (
            _block_content_to_html,
        )

        assert "<p>Hola</p>" in _block_content_to_html({"text": "Hola"})

    def test_should_devolver_vacio_sin_contenido(self) -> None:
        from server.app.modules.redaccion.services.preview_builder import (
            _block_content_to_html,
        )

        assert _block_content_to_html(None) == ""
        assert _block_content_to_html({}) == ""
        assert _block_content_to_html({"tables": [], "metrics": [], "free_text": None}) == ""


class TestDocumentoEnsamblado:
    def test_should_escribir_la_tabla_en_markdown_y_no_un_diccionario(self) -> None:
        from server.app.modules.redaccion.graph.nodes.final_assembler import (
            contenido_a_markdown,
        )

        md = contenido_a_markdown(_CONTENIDO)

        assert "{'tables'" not in md, "el documento final no puede llevar un dict de Python"
        assert "| capitulo |" in md
        assert "| 1 Personal |" in md
        assert "porcentaje_ejecucion" in md
        assert "68.52" in md

    def test_should_conservar_el_texto_libre(self) -> None:
        from server.app.modules.redaccion.graph.nodes.final_assembler import (
            contenido_a_markdown,
        )

        md = contenido_a_markdown({"tables": [], "metrics": [], "free_text": "Un resumen."})

        assert md.strip() == "Un resumen."

    def test_should_usar_el_texto_de_un_bloque_de_ia(self) -> None:
        from server.app.modules.redaccion.graph.nodes.final_assembler import (
            contenido_a_markdown,
        )

        assert contenido_a_markdown({"text": "Párrafo redactado."}) == "Párrafo redactado."

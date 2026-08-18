"""SEG.3 — leer las tablas de un Markdown, literales.

Los orígenes de datos eran `excel`, `pdf_text`, `pdf_table`, `manual` y `admin_script`. Los datos
de entrada de los informes de seguimiento son **Markdown con unas treinta tablas**, uno por
programa, y ya existen. Mañana serán un JSON o una consulta a una API: la abstracción de pipeline
ya está, así que esto es aditivo.

Este pipeline **reproduce, no interpreta**. Si hay que calcular algo, lo hace una operación
declarativa aguas abajo, que es auditable.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from server.app.modules.redaccion.pipelines.contracts import ExtractionInput, StorageRef
from server.app.modules.redaccion.pipelines.md_table_pipeline import (
    MarkdownTableExtractionPipeline,
)

#: Fragmento tomado literal del informe real de un programa de doctorado.
_FRAGMENTO_REAL = """\
## **CRITERIO 1\\. ORGANIZACIÓN Y DESARROLLO**

La siguiente tabla muestra el indicador del número de plazas.

| Indicador | 2024 |
| :---- | :---- |
| Plazas del programa | 45.00 |

Tabla 1.1 Número de Plazas del Programa de Doctorado

En la tabla (T1.1) se indica el número de plazas ofertadas anualmente.

| Indicador | 2024 | 2023 | 2022 |
| :---- | :---- | :---- | :---- |
| Matriculados Totales a tiempo parcial | 13.00 | 14.00 | 13.00 |
| Matriculados Totales | 138.00 | 143.00 | 119.00 |
| Matriculados de nuevo ingreso por linea de investigación | Fisiología vegetal (1) Física aplicada y óptica (9) Matemáticas (6) | Fisiología vegetal (3) Física aplicada y óptica (15) | Fisiología vegetal (4) |

Tabla 1.2 Evolución de la Matrícula

| Indicador | 2024 | 2023 | 2022 | 2021 |
| :---- | :---- | :---- | :---- | :---- |
| El contenido de las actividades formativas específicas | No hay valor | 4.20 | No hay valor | 4.30 |

Tabla 1.4.2 Satisfacción con la organización de las actividades formativas.
"""


@pytest.fixture
def fichero(tmp_path: Path) -> StorageRef:
    destino = tmp_path / "informe_resumen.md"
    destino.write_text(_FRAGMENTO_REAL, encoding="utf-8")
    # Convención de VER.4: bucket vacío + ruta completa en key = ya materializado en disco.
    return StorageRef(bucket="", key=str(destino))


def _extraer(fichero: StorageRef, **opciones):
    pipeline = MarkdownTableExtractionPipeline()
    return pipeline.extract(
        ExtractionInput(source_kind="md_table", file_ref=fichero, options=opciones)
    )


def test_el_pipeline_se_declara_para_markdown() -> None:
    pipeline = MarkdownTableExtractionPipeline()
    assert pipeline.supports("md_table")
    assert not pipeline.supports("excel")


def test_saca_las_tres_tablas_del_fragmento(fichero: StorageRef) -> None:
    resultado = _extraer(fichero)
    assert len(resultado.tables) == 3


def test_el_codigo_de_la_tabla_va_como_nombre(fichero: StorageRef) -> None:
    """En este formato el código va **debajo** de la tabla, no encima.

    Es lo que permite que una plantilla diga «valora la Tabla 1.2» y que el informe final las
    reproduzca con su numeración original.
    """
    nombres = [t.name for t in _extraer(fichero).tables]
    assert nombres[0].startswith("Tabla 1.1")
    assert nombres[1].startswith("Tabla 1.2")
    assert nombres[2].startswith("Tabla 1.4.2")


def test_las_cabeceras_y_las_filas_son_literales(fichero: StorageRef) -> None:
    tabla = _extraer(fichero).tables[1]
    assert tabla.headers == ["Indicador", "2024", "2023", "2022"]
    assert tabla.rows[1] == ["Matriculados Totales", "138.00", "143.00", "119.00"]


def test_la_fila_de_alineacion_no_es_una_fila_de_datos(fichero: StorageRef) -> None:
    """`| :---- |` es sintaxis de Markdown; colarla como dato ensuciaría todas las tablas."""
    for tabla in _extraer(fichero).tables:
        for fila in tabla.rows:
            assert not all(c.strip(": -") == "" for c in fila), f"fila de alineación: {fila}"


def test_no_hay_valor_sobrevive_literal(fichero: StorageRef) -> None:
    """Es la regla que el intento anterior perdía: ausencia no es cero."""
    tabla = _extraer(fichero).tables[2]
    assert tabla.rows[0][1] == "No hay valor"
    assert tabla.rows[0][3] == "No hay valor"


def test_una_celda_larga_con_varios_valores_no_se_parte(fichero: StorageRef) -> None:
    """La celda de matriculados por línea de investigación es un párrafo dentro de una celda."""
    tabla = _extraer(fichero).tables[1]
    celda = tabla.rows[2][1]
    assert "Fisiología vegetal (1)" in celda
    assert "Matemáticas (6)" in celda


def test_la_procedencia_dice_de_donde_sale(fichero: StorageRef) -> None:
    resultado = _extraer(fichero)
    assert resultado.provenance.pipeline_id == "md_table_pipeline_v1"


def test_un_markdown_sin_tablas_no_es_un_error_silencioso(tmp_path: Path) -> None:
    """Cero tablas es un aviso: el fichero puede no ser el que se creía."""
    vacio = tmp_path / "sin_tablas.md"
    vacio.write_text("# Solo un título\n\nY un párrafo.\n", encoding="utf-8")

    resultado = _extraer(StorageRef(bucket="", key=str(vacio)))

    assert resultado.tables == []
    assert any(a.code == "NO_TABLES_FOUND" for a in resultado.warnings)


def test_el_pipeline_esta_registrado_en_la_factoria() -> None:
    """Si no está en la factoría, una plantilla que lo pida falla en ejecución."""
    from server.app.modules.redaccion.pipelines.factory import build_default_factory

    factory = build_default_factory()
    assert factory.get("md_table") is not None


# ----------------------------------------------------------------------
# Que una plantilla pueda pedirlo
# ----------------------------------------------------------------------


def test_una_plantilla_puede_declarar_un_hueco_para_un_markdown() -> None:
    """Sin un `kind` de slot para `.md`, el informe no tiene dónde recibir su fichero."""
    from server.app.modules.redaccion.contracts.inputs import InputSlot

    slot = InputSlot(
        slot_id="datos_del_programa",
        kind="markdown",
        label={"es": "Informe resumen", "ca": "Informe resum", "en": "Summary report"},
    )
    assert slot.kind == "markdown"


def test_el_hueco_de_markdown_acepta_la_extension() -> None:
    """El dropzone tiene que ofrecer `.md`; si no, el navegador filtra el fichero correcto."""
    from server.app.modules.redaccion.services.spec_builder import _ACEPTA

    assert ".md" in _ACEPTA["markdown"]


def test_el_borrador_conoce_el_origen_markdown() -> None:
    """El prompt enumeraba los pipelines a mano: el mismo problema que GUI.3 ya arregló dos veces."""
    from server.app.modules.redaccion.services.llm_spec_service import _campos_obligatorios

    texto = _campos_obligatorios()
    assert "md_table" in texto
    for otro in ("excel", "pdf_text", "pdf_table", "manual", "admin_script"):
        assert otro in texto, f"se ha perdido {otro} al generar la lista"


def test_el_borrador_conoce_el_hueco_de_markdown() -> None:
    """La lista de tipos de slot también estaba a mano, y también se quedó corta."""
    from server.app.modules.redaccion.services.llm_spec_service import _campos_obligatorios

    texto = _campos_obligatorios()
    assert "markdown" in texto
    for otro in ("pdf", "excel", "csv", "selector"):
        assert otro in texto, f"se ha perdido {otro}"

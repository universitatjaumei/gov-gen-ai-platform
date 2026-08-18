"""Un bloque TABLE no pintaba nada (SEG.5).

`TABLE` está en el contrato desde el principio, el validador exige que traiga `data_block_ref`,
el prompt lo ofrece al modelo... y **ningún nodo del grafo lo rellenaba**. Un informe con nueve
tablas salía con las nueve vacías: `content` a cero, `status: draft`, sin error y sin aviso. Las
cifras que aparecían en la vista previa venían de la prosa del modelo, no de las tablas.

Es el mismo agujero que PRO.5 tapó para los gráficos —`ChartHandler` escrito y probado, y nadie
lo llamaba— y por eso este nodo es hermano de `ChartRenderNode`: escribe en el bloque lo que hay
que imprimir, y de ahí lo cogen igual la vista previa y el DOCX, que ya saben pintar `tables`
desde PRO.3.

En un informe de seguimiento la tabla es la parte que **no** puede proponerla un modelo: se
reproduce del dato o no se pone.
"""
from __future__ import annotations

import pytest

from datetime import datetime, timezone

from server.app.modules.redaccion.contracts.runtime import BlockState, WorkspaceState
from server.app.modules.redaccion.contracts.template import ReportTemplateSpec
from server.app.modules.redaccion.graph.nodes.table_render import TableRenderNode

_TABLA_EXTRAIDA = {
    "name": "Tabla 1.3 Evolución de los indicadores",
    "headers": ["Indicador", "2024", "2023"],
    "rows": [
        ["TASA DE OFERTA Y DEMANDA DOCTORADO", "46.67", "102.22"],
        ["TASA ABANDONO DOCTORADO A TIEMPO COMPLETO", "21.21", "15.15"],
    ],
}


def _spec(*, ref: str = "t_indicadores") -> ReportTemplateSpec:
    return ReportTemplateSpec.model_validate({
        "sections": [
            {"id": "s1", "title": "Criterio 1", "order": 1, "block_ids": ["tabla_indicadores"]}
        ],
        "blocks": [
            {
                "id": "t_indicadores", "kind": "DETERMINISTIC_DATA", "order": 1,
                "title": "Indicadores", "source_pipeline": "md_table",
                "options": {"table": "Tabla 1.3"},
            },
            {
                "id": "tabla_indicadores", "kind": "TABLE", "order": 2,
                "title": "Evolución de los indicadores", "data_block_ref": ref,
            },
        ],
        "input_contract": {"required_slots": [], "optional_slots": []},
        "ui_contract": {
            "wizard_steps": [], "manual_fields": [], "dropzones": [],
            "block_editor_enabled": True, "ai_review_panel_enabled": True,
            "preview_layout": "markdown",
        },
        "ai_block_policy": "allowed", "review_policy": "required", "export_policy": "docx",
    })


def _estado(*, ref: str = "t_indicadores", datos: dict | None = None) -> WorkspaceState:
    contenido = {"tables": [_TABLA_EXTRAIDA]} if datos is None else datos
    ahora = datetime.now(timezone.utc)
    return WorkspaceState(
        workspace_id="11111111-1111-1111-1111-111111111111",
        template_version_id="22222222-2222-2222-2222-222222222222",
        report_profile="DOCTORATE_PROGRAM_REPORT",
        inputs={},
        status="drafting",
        warnings=[],
        spec=_spec(ref=ref),
        blocks={
            "t_indicadores": BlockState(
                block_id="t_indicadores", kind="DETERMINISTIC_DATA",
                status="extracted", content=contenido,
                last_updated_by="system", updated_at=ahora,
            ),
            "tabla_indicadores": BlockState(
                block_id="tabla_indicadores", kind="TABLE", status="draft", content={},
                last_updated_by="system", updated_at=ahora,
            ),
        },
    )


@pytest.mark.asyncio
async def test_la_tabla_reproduce_los_datos_del_bloque_que_referencia():
    resultado = await TableRenderNode()(_estado())

    bloque = resultado["blocks"]["tabla_indicadores"]
    assert bloque.content["tables"] == [_TABLA_EXTRAIDA]
    assert bloque.status == "extracted"


@pytest.mark.asyncio
async def test_la_tabla_conserva_los_huecos_tal_cual():
    """«No hay valor» no es cero: si la tabla lo convierte o lo borra, miente."""
    con_hueco = {
        "name": "Tabla 1.4.2 Satisfacción",
        "headers": ["Indicador", "2024", "2023"],
        "rows": [["El contenido de las actividades formativas", "No hay valor", "4.20"]],
    }
    resultado = await TableRenderNode()(_estado(datos={"tables": [con_hueco]}))

    assert resultado["blocks"]["tabla_indicadores"].content["tables"][0]["rows"] == [
        ["El contenido de las actividades formativas", "No hay valor", "4.20"]
    ]


@pytest.mark.asyncio
async def test_una_referencia_a_un_bloque_que_no_existe_avisa_y_no_revienta():
    resultado = await TableRenderNode()(_estado(ref="fantasma"))

    bloque = resultado["blocks"]["tabla_indicadores"]
    assert bloque.status != "extracted"
    assert any("fantasma" in a.message for a in resultado["warnings"])


@pytest.mark.asyncio
async def test_un_bloque_de_datos_sin_tablas_avisa_en_vez_de_pintar_una_tabla_vacia():
    """Una tabla vacía en un informe institucional pasa por dato; el aviso, no."""
    resultado = await TableRenderNode()(_estado(datos={"tables": []}))

    bloque = resultado["blocks"]["tabla_indicadores"]
    assert bloque.status != "extracted"
    assert any("tabla_indicadores" in a.block_id for a in resultado["warnings"])


@pytest.mark.asyncio
async def test_sin_spec_el_nodo_no_hace_nada():
    estado = _estado()
    estado.spec = None
    assert await TableRenderNode()(estado) == {}


def test_el_nodo_esta_cableado_en_el_grafo():
    """El nodo suelto no pinta nada: el fallo de origen fue justo ese."""
    import inspect

    from server.app.modules.redaccion.graph import core_graph

    fuente = inspect.getsource(core_graph)
    assert "TableRenderNode" in fuente
    assert '"table_render"' in fuente

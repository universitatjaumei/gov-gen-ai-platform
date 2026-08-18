"""GUI.3 — el informe que se describe puede llevar una transformación y cualquier gráfico.

Encontrado al escribir la guía de pruebas para el usuario: **la PRUEBA H no se podía hacer**. El
`.bat` le pedía crear «un informe con un bloque de transformación» y no hay forma de crearlo:

- No existe ninguna pantalla que configure bloques —los bloques sólo entran por el borrador—.
- Y `_BLOCK_KINDS` del borrador **no incluía `DATA_TRANSFORM`**, con un «Do NOT use any block
  kind not in this list» detrás.

O sea que todo el ETL de PRO.4 y PRO.9 era inalcanzable para una persona: puerta cerrada y, al
otro lado, el camino que se acabó de asfaltar ayer. Lo mismo con los gráficos: la lista de tipos
del prompt estaba **escrita a mano** (`bar | line | pie | scatter | histogram`), así que los seis
que PRO.8 añadió no se podían pedir aunque el renderizador supiera dibujarlos.

La cadena que esto habilita es la de una hoja de cálculo real:
`DETERMINISTIC_DATA (excel)` → `DATA_TRANSFORM (to_number, compute_column, sort_rows)` → `TABLE`/`CHART`.
"""
from __future__ import annotations

from server.app.modules.redaccion.contracts.drafts import ReportTemplateDraft
from server.app.modules.redaccion.services.draft_validator import DraftValidator
from server.app.modules.redaccion.services.llm_spec_service import (
    _BLOCK_KINDS,
    _campos_obligatorios,
)


# ----------------------------------------------------------------------
# Lo que el modelo llega a saber que existe
# ----------------------------------------------------------------------


def test_el_borrador_puede_proponer_una_transformacion() -> None:
    assert "DATA_TRANSFORM" in _BLOCK_KINDS


def test_el_prompt_explica_los_campos_de_la_transformacion() -> None:
    """Sin los campos, el modelo propone algo razonable que el contrato rechaza con un 422."""
    texto = _campos_obligatorios()
    assert "DATA_TRANSFORM" in texto
    assert "source_block_ref" in texto
    assert "operations" in texto
    assert "nl_instruction" in texto


def test_el_prompt_lleva_el_catalogo_de_operaciones_generado_del_contrato() -> None:
    """Si el catálogo se escribe a mano, el modelo dejará de usar la mitad en el primer cambio."""
    texto = _campos_obligatorios()
    for operacion in ("to_number", "compute_column", "sort_rows", "unpivot", "groupby"):
        assert f'"op": "{operacion}"' in texto, f"el modelo no sabe que existe {operacion}"


def test_el_prompt_ofrece_los_once_tipos_de_grafico() -> None:
    """La lista estaba escrita a mano con cinco. PRO.8 dejó once y el modelo veía cinco."""
    texto = _campos_obligatorios()
    for tipo in ("bar", "barh", "bar_stacked", "line", "pie", "donut",
                 "scatter", "bubble", "histogram", "boxplot", "heatmap"):
        assert tipo in texto, f"el modelo no puede pedir un {tipo}"


def test_el_prompt_avisa_de_convertir_los_importes_antes_de_calcular() -> None:
    """Es el fallo silencioso de PRO.9: sumar texto no da error, da una cifra mal."""
    texto = _campos_obligatorios()
    assert "to_number" in texto
    assert "text" in texto.lower()


# ----------------------------------------------------------------------
# Lo que el validador acepta
# ----------------------------------------------------------------------

_HOJA = {
    "id": "datos",
    "title": "Ejecución presupuestaria",
    "order": 1,
    "kind": "DETERMINISTIC_DATA",
    "source_pipeline": "excel",
}
_TRANSFORMACION = {
    "id": "limpio",
    "title": "Importes y porcentaje",
    "order": 2,
    "kind": "DATA_TRANSFORM",
    "config": {
        "mode": "deterministic",
        "source_block_ref": {"block_id": "datos"},
        "operations": [
            {"op": "to_number", "columns": ["obligaciones", "credito"]},
            {
                "op": "compute_column",
                "target": "pct_ejecucion",
                "left": "obligaciones",
                "operator": "/",
                "right": "credito",
                "scale": 100,
                "round_to": 2,
            },
            {"op": "sort_rows", "by": ["obligaciones"], "ascending": False},
        ],
    },
}


def _borrador(*bloques: dict) -> ReportTemplateDraft:
    return ReportTemplateDraft.model_validate(
        {
            "proposed_profile": "GENERIC_REPORT",
            "proposed_sections": [{"id": "s1", "title": "Datos", "order": 1}],
            "proposed_blocks": list(bloques),
            "proposed_inputs": {
                "required_slots": [
                    {
                        "slot_id": "presupuesto",
                        "kind": "excel",
                        "label": {"es": "Hoja", "ca": "Full", "en": "Sheet"},
                    }
                ]
            },
            "rationale": "",
            "model_used": "prueba",
            "prompt_version": "prueba",
        }
    )


def test_un_grafico_puede_colgar_de_una_transformacion() -> None:
    """La cadena natural de una hoja real: extraer, limpiar y **entonces** dibujar.

    El validador exigía que un CHART apuntara a un `DETERMINISTIC_DATA`, así que la cadena
    entera se caía en cuanto se metía la limpieza en medio — que es cuando el gráfico vale algo.
    """
    grafico = {
        "id": "grafico",
        "title": "Gasto por capítulo",
        "order": 3,
        "kind": "CHART",
        "data_block_ref": "limpio",
        "config": {
            "chart_type": "barh",
            "x_axis": "capitulo",
            "y_axis": "obligaciones",
            "title": "Obligaciones por capítulo",
            "show_values": True,
            "sort": "desc",
        },
    }
    resultado = DraftValidator().validate(_borrador(_HOJA, _TRANSFORMACION, grafico))
    assert resultado.ok, resultado.errors


def test_una_tabla_puede_colgar_de_una_transformacion() -> None:
    tabla = {
        "id": "tabla",
        "title": "Detalle",
        "order": 3,
        "kind": "TABLE",
        "data_block_ref": "limpio",
    }
    resultado = DraftValidator().validate(_borrador(_HOJA, _TRANSFORMACION, tabla))
    assert resultado.ok, resultado.errors


def test_una_transformacion_que_no_apunta_a_nada_no_pasa() -> None:
    """Una referencia a un bloque inexistente deja el informe sin datos y sin explicación."""
    roto = {
        **_TRANSFORMACION,
        "config": {**_TRANSFORMACION["config"], "source_block_ref": {"block_id": "no_existe"}},
    }
    resultado = DraftValidator().validate(_borrador(_HOJA, roto))
    assert not resultado.ok
    assert any("no_existe" in e.message for e in resultado.errors)


def test_un_grafico_que_apunta_a_un_bloque_de_texto_sigue_siendo_invalido() -> None:
    """Ampliar lo que se acepta no es aceptar cualquier cosa: un texto no tiene columnas."""
    texto = {"id": "intro", "title": "Intro", "order": 1, "kind": "STATIC_TEXT", "content": "Hola"}
    grafico = {
        "id": "grafico",
        "title": "Gráfico",
        "order": 2,
        "kind": "CHART",
        "data_block_ref": "intro",
    }
    resultado = DraftValidator().validate(_borrador(texto, grafico))
    assert not resultado.ok

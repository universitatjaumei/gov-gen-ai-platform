"""PRO.9 — las cuatro operaciones que una hoja de cálculo real necesita para llegar a un informe.

Comprobado antes de escribir nada: **lo determinista del legacy está portado al 100%** en PRO.4.
Estas cuatro no son una migración pendiente, son un hueco que allí tampoco estaba cubierto, y
hoy cada una cuesta un script generado, auditado y ejecutado en el sandbox.

La segunda es la peor de las cuatro y es la razón de que este prompt exista: cuando los importes
llegan como texto —`"1.234,56 €"`, que es como los exporta cualquier aplicación de aquí—,
`sum()` **concatena o revienta**, y el informe sale con una cifra mal **sin un solo error que
mirar**.
"""
from __future__ import annotations

import pandas as pd
import pytest

from server.app.modules.redaccion.services.transformation.deterministic_etl import (
    ColumnaInexistenteError,
    DeterministicETLService,
    TransformacionImposibleError,
)
from server.app.modules.redaccion.services.transformation.operations import parse_operations


def _ejecutar(df: pd.DataFrame, *ops: dict) -> pd.DataFrame:
    return DeterministicETLService().execute(df, parse_operations(list(ops)))


# ----------------------------------------------------------------------
# 1. Columna calculada — la transformación de un informe presupuestario
# ----------------------------------------------------------------------


def test_el_porcentaje_de_ejecucion_se_calcula_sin_escribir_codigo() -> None:
    df = pd.DataFrame(
        {"capitulo": ["Cap. 1", "Cap. 2"], "credito": [1000.0, 200.0], "obligaciones": [910.0, 50.0]}
    )
    salida = _ejecutar(
        df,
        {
            "op": "compute_column",
            "target": "pct_ejecucion",
            "left": "obligaciones",
            "operator": "/",
            "right": "credito",
            "scale": 100,
            "round_to": 2,
        },
    )
    assert salida["pct_ejecucion"].tolist() == [91.0, 25.0]


def test_lo_compuesto_se_consigue_encadenando() -> None:
    """Sin campo `formula` y sin `eval`: es la puerta trasera que el auditor cierra en un script.

    Tres operaciones en vez de una expresión. Más verboso, auditable, y se puede pintar en una
    pantalla.
    """
    df = pd.DataFrame({"cap1": [100.0], "cap2": [300.0], "total": [1000.0]})
    salida = _ejecutar(
        df,
        {"op": "compute_column", "target": "suma", "left": "cap1", "operator": "+", "right": "cap2"},
        {
            "op": "compute_column",
            "target": "peso",
            "left": "suma",
            "operator": "/",
            "right": "total",
            "scale": 100,
        },
        {"op": "drop_columns", "columns": ["suma"]},
    )
    assert salida["peso"].tolist() == [40.0]
    assert "suma" not in salida.columns


def test_el_operando_puede_ser_una_constante() -> None:
    df = pd.DataFrame({"importe": [100.0, 250.0]})
    salida = _ejecutar(
        df,
        {"op": "compute_column", "target": "con_iva", "left": "importe", "operator": "*", "right": 1.21},
    )
    assert salida["con_iva"].round(2).tolist() == [121.0, 302.5]


def test_una_columna_que_no_existe_no_se_toma_por_una_constante_de_texto() -> None:
    """Confundir «la columna `credito`» con «el texto `credito`» daría una columna de basura."""
    df = pd.DataFrame({"importe": [1.0]})
    with pytest.raises(ColumnaInexistenteError):
        _ejecutar(
            df,
            {"op": "compute_column", "target": "x", "left": "importe", "operator": "/", "right": "credito"},
        )


def test_dividir_por_cero_deja_el_hueco_vacio_y_no_un_infinito() -> None:
    """Un `inf` en una tabla de informe es basura publicada; un hueco se ve."""
    df = pd.DataFrame({"a": [10.0, 5.0], "b": [0.0, 5.0]})
    salida = _ejecutar(
        df, {"op": "compute_column", "target": "r", "left": "a", "operator": "/", "right": "b"}
    )
    assert pd.isna(salida["r"].iloc[0])
    assert salida["r"].iloc[1] == 1.0


def test_no_hay_ninguna_forma_de_colar_una_expresion() -> None:
    """El contrato no admite un campo de fórmula. Si lo admitiera, el auditor sobraría."""
    from server.app.modules.redaccion.services.transformation.operations import ComputeColumnOp

    prohibidos = {"formula", "expression", "expr", "eval", "code"}
    assert not prohibidos & set(ComputeColumnOp.model_fields)


# ----------------------------------------------------------------------
# 2. Números de verdad — la peor de las cuatro, porque es silenciosa
# ----------------------------------------------------------------------


def test_los_importes_en_formato_de_aqui_se_pueden_sumar() -> None:
    df = pd.DataFrame(
        {
            "concepto": ["Personal", "Bienes", "Inversión"],
            "importe": ["1.234,56 €", "89,00 €", "12.000,00 €"],
        }
    )
    salida = _ejecutar(df, {"op": "to_number", "columns": ["importe"]})

    assert salida["importe"].dtype.kind == "f"
    assert salida["importe"].sum() == pytest.approx(13323.56)


def test_lo_que_no_es_un_numero_queda_vacio_y_se_ve() -> None:
    """Mismo criterio que `format_dates`: el valor ausente se ve; uno inventado, no."""
    df = pd.DataFrame({"importe": ["100,00", "sin datos", "50,50"]})
    salida = _ejecutar(df, {"op": "to_number", "columns": ["importe"]})

    assert salida["importe"].tolist()[0] == 100.0
    assert pd.isna(salida["importe"].iloc[1])
    assert salida["importe"].sum() == pytest.approx(150.5)


def test_una_columna_entera_ilegible_es_un_error_de_configuracion_no_un_dato_ausente() -> None:
    """Si NADA se convierte, callarlo vaciaría la tabla y el informe con ella."""
    df = pd.DataFrame({"importe": ["N/D", "pendiente"]})
    with pytest.raises(TransformacionImposibleError):
        _ejecutar(df, {"op": "to_number", "columns": ["importe"]})


def test_los_separadores_al_reves_no_pasan_por_un_numero_distinto() -> None:
    """Este test se escribió esperando que no se convirtiera nada. Se convierte, y **da otro
    número**: `1,234.56` leído con la coma como decimal sale 1,23456 en vez de 1234,56.

    Eso es peor que una columna vacía, porque una columna vacía se ve. Y es detectable sin
    adivinar nada: si el separador de millares aparece **después** del decimal, la configuración
    contradice al dato.
    """
    df = pd.DataFrame({"importe": ["1,234.56", "7,890.00"]})  # formato inglés
    with pytest.raises(TransformacionImposibleError):
        _ejecutar(
            df,
            {"op": "to_number", "columns": ["importe"], "decimal_separator": ",", "thousands_separator": "."},
        )


def test_los_separadores_se_pueden_declarar_para_una_hoja_en_ingles() -> None:
    df = pd.DataFrame({"importe": ["1,234.56"]})
    salida = _ejecutar(
        df,
        {"op": "to_number", "columns": ["importe"], "decimal_separator": ".", "thousands_separator": ","},
    )
    assert salida["importe"].tolist() == [1234.56]


def test_el_porcentaje_pierde_su_simbolo() -> None:
    df = pd.DataFrame({"ejecucion": ["91,5 %", "40,0 %"]})
    salida = _ejecutar(df, {"op": "to_number", "columns": ["ejecucion"]})
    assert salida["ejecucion"].tolist() == [91.5, 40.0]


def test_el_parentesis_contable_es_un_negativo() -> None:
    """En una hoja de contabilidad `(1.500,00)` es −1500, no un texto raro."""
    df = pd.DataFrame({"saldo": ["(1.500,00)", "2.000,00"]})
    salida = _ejecutar(df, {"op": "to_number", "columns": ["saldo"]})
    assert salida["saldo"].tolist() == [-1500.0, 2000.0]


def test_una_columna_ya_numerica_no_se_estropea() -> None:
    df = pd.DataFrame({"importe": [1234.56, 89.0]})
    salida = _ejecutar(df, {"op": "to_number", "columns": ["importe"]})
    assert salida["importe"].tolist() == [1234.56, 89.0]


# ----------------------------------------------------------------------
# 3. Ordenar — una tabla de informe se lee ordenada
# ----------------------------------------------------------------------


def test_la_tabla_sale_ordenada_de_mayor_a_menor() -> None:
    df = pd.DataFrame({"capitulo": ["A", "B", "C"], "importe": [50.0, 500.0, 200.0]})
    salida = _ejecutar(df, {"op": "sort_rows", "by": ["importe"], "ascending": False})
    assert salida["capitulo"].tolist() == ["B", "C", "A"]
    assert salida.index.tolist() == [0, 1, 2], "el índice se reinicia: la tabla se numera al leerla"


def test_se_puede_ordenar_por_varias_columnas() -> None:
    df = pd.DataFrame({"anyo": [2025, 2024, 2025], "importe": [10.0, 99.0, 30.0]})
    salida = _ejecutar(df, {"op": "sort_rows", "by": ["anyo", "importe"], "ascending": True})
    assert salida["importe"].tolist() == [99.0, 10.0, 30.0]


def test_ordenar_por_una_columna_inexistente_falla() -> None:
    with pytest.raises(ColumnaInexistenteError):
        _ejecutar(pd.DataFrame({"a": [1]}), {"op": "sort_rows", "by": ["b"]})


# ----------------------------------------------------------------------
# 4. Unpivot — las hojas de aquí son anchas y un informe necesita largo
# ----------------------------------------------------------------------


def test_las_cabeceras_de_mes_pasan_a_ser_una_columna() -> None:
    df = pd.DataFrame(
        {"capitulo": ["Cap. 1", "Cap. 2"], "ene": [10.0, 40.0], "feb": [20.0, 50.0], "mar": [30.0, 60.0]}
    )
    salida = _ejecutar(
        df,
        {
            "op": "unpivot",
            "id_columns": ["capitulo"],
            "value_columns": ["ene", "feb", "mar"],
            "variable_name": "mes",
            "value_name": "importe",
        },
    )
    assert list(salida.columns) == ["capitulo", "mes", "importe"]
    assert len(salida) == 6
    fila = salida[(salida["capitulo"] == "Cap. 2") & (salida["mes"] == "mar")]
    assert fila["importe"].iloc[0] == 60.0


def test_sin_value_columns_se_toman_todas_las_que_no_son_identificador() -> None:
    df = pd.DataFrame({"unidad": ["A"], "2024": [1.0], "2025": [2.0]})
    salida = _ejecutar(df, {"op": "unpivot", "id_columns": ["unidad"], "variable_name": "anyo"})
    assert sorted(salida["anyo"].tolist()) == ["2024", "2025"]


def test_el_unpivot_deshace_lo_que_hace_el_pivot() -> None:
    largo = pd.DataFrame(
        {"capitulo": ["A", "A", "B", "B"], "anyo": [2024, 2025, 2024, 2025], "importe": [1.0, 2.0, 3.0, 4.0]}
    )
    ancho = _ejecutar(largo, {"op": "pivot", "index": "capitulo", "columns": "anyo", "values": "importe"})
    de_vuelta = _ejecutar(
        ancho.reset_index() if ancho.index.name else ancho,
        {"op": "unpivot", "id_columns": ["capitulo"], "variable_name": "anyo", "value_name": "importe"},
    )
    assert sorted(de_vuelta["importe"].tolist()) == [1.0, 2.0, 3.0, 4.0]


# ----------------------------------------------------------------------
# El modelo tiene que enterarse de que existen
# ----------------------------------------------------------------------


def test_el_catalogo_del_prompt_incluye_las_cuatro_nuevas() -> None:
    """Se genera del contrato (PRO.4), así que esto debería salir gratis. Comprobarlo."""
    from server.app.modules.redaccion.services.transformation.operations import (
        catalogo_de_operaciones,
    )

    catalogo = catalogo_de_operaciones()
    for op in ("compute_column", "to_number", "sort_rows", "unpivot"):
        assert f'"op": "{op}"' in catalogo, f"el modelo no sabe que existe {op}"
    # Y el orden importa: convertir a número va antes de calcular con ellos.
    assert catalogo.index("to_number") < catalogo.index("compute_column")

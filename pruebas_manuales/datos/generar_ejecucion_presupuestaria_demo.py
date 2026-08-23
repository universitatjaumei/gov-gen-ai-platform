"""Genera el juego de datos ficticio de la plantilla «ejecución presupuestaria».

La plantilla declara un único hueco obligatorio —`budget_data`, de tipo `excel`— y sus
transformaciones deterministas nombran **tres columnas exactas**:

    Concepto | Credito Inicial | Obligaciones Reconocidas

`Credito Inicial` y `Obligaciones Reconocidas` pasan por `to_number` con separador decimal
`,`, de millares `.` y retirando `€`, así que aquí se escriben **como texto y en formato
español**: si se generaran ya numéricos, el fichero no ejercitaría la conversión, que es
justamente la parte que se rompe en silencio con una hoja real.

De ahí sale `Porcentaje Ejecucion` (obligaciones / crédito × 100), la tabla se ordena por esa
columna descendente y el gráfico es un `barh` con `Concepto` en el eje Y.

Los datos son **inventados**: ni son el presupuesto de la UJI ni de nadie. Se eligen doce
conceptos plausibles y porcentajes repartidos entre el 31 % y el 97 % para que la barra
ordenada tenga algo que enseñar y el resumen de la IA tenga de qué hablar.

Uso:
    cd server && uv run python ../pruebas_manuales/datos/generar_ejecucion_presupuestaria_demo.py
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

#: (concepto, crédito inicial, obligaciones reconocidas) en euros.
FILAS: list[tuple[str, float, float]] = [
    ("Retribuciones del personal docente e investigador", 42_150_000.00, 40_886_550.00),
    ("Retribuciones del PTGAS", 18_400_000.00, 17_664_000.00),
    ("Cuotas sociales a cargo de la universidad", 14_275_000.00, 13_418_500.00),
    ("Suministros y energía", 6_800_000.00, 5_984_000.00),
    ("Mantenimiento y conservación de edificios", 4_250_000.00, 3_145_000.00),
    ("Servicios informáticos y licencias de software", 3_920_000.00, 3_449_600.00),
    ("Becas y ayudas al estudiantado", 5_600_000.00, 4_368_000.00),
    ("Proyectos de investigación competitiva", 9_340_000.00, 5_697_400.00),
    ("Inversión en equipamiento científico", 7_180_000.00, 2_872_000.00),
    ("Material de oficina y consumibles", 1_150_000.00, 908_500.00),
    ("Publicaciones y difusión cultural", 780_000.00, 421_200.00),
    ("Gastos de protocolo y representación", 145_000.00, 44_950.00),
]


def euros(importe: float) -> str:
    """El importe tal y como sale de una hoja de contabilidad española: `1.234.567,89 €`."""
    entero, decimal = f"{importe:,.2f}".split(".")
    return f"{entero.replace(',', '.')},{decimal} €"


def main() -> None:
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Ejecucion"
    hoja.append(["Concepto", "Credito Inicial", "Obligaciones Reconocidas"])
    for concepto, credito, obligaciones in FILAS:
        hoja.append([concepto, euros(credito), euros(obligaciones)])

    hoja.column_dimensions["A"].width = 52
    hoja.column_dimensions["B"].width = 20
    hoja.column_dimensions["C"].width = 26

    destino = Path(__file__).with_name("ejecucion_presupuestaria_demo.xlsx")
    libro.save(destino)

    print(f"[OK] {destino}  ({len(FILAS)} conceptos)")
    for concepto, credito, obligaciones in FILAS:
        print(f"  {obligaciones / credito * 100:5.1f} %  {concepto}")


if __name__ == "__main__":
    main()

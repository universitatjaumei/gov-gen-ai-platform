"""Una función determinista empaquetada, como la escribiría un equipo con su propio repositorio.

Es el ejemplo que acompaña a `docs/CATALOGO_FUNCIONES.md`. Tres cosas que no son obvias y que son
justo las que un primer equipo se salta:

1. **El descriptor se expone como una constante**, no como una factoría. El *entry point* apunta
   a una instancia, así que el cargador no tiene que invocar nada para leer el contrato: puede
   validarlo antes de ejecutar una sola línea del paquete.
2. **El contrato declara finalidad y categorías de datos.** Una función corporativa también
   declara (Instrucció 02/2026 §8.2); lo que cambia en el nivel 3 es quién valora, no si hay
   declaración. Sin `finalidad`, el `ContratoFuncion` ni se construye.
3. **`run` recibe una `EntradaValidada` y devuelve un `ExtractionResult`.** La entrada ya viene
   comprobada contra el contrato: no hace falta defenderse de un slot que falta, porque la
   plataforma no llama a `run` en ese caso. Lo que sí hay que devolver es un `ExtractionResult`
   con su `provenance`, que es lo que el `RunManifest` usa para poder decir de dónde salió cada
   cifra de un informe meses después.

La firma no importa aquí (es un ejemplo), pero en un paquete real el `run` va con sus tests en el
CI del equipo. Eso es lo que este origen compra: el código se queda donde quien lo mantiene
puede probarlo, y la plataforma se queda con el contrato, la revisión y la trazabilidad.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from server.app.modules.redaccion.contracts.funciones import (
    ContratoFuncion,
    EntradaValidada,
)
from server.app.modules.redaccion.funciones_paquete import FuncionEmpaquetada
from server.app.modules.redaccion.pipelines.contracts import (
    ExtractedMetric,
    ExtractionProvenance,
    ExtractionResult,
)

CONTRATO = ContratoFuncion(
    slots=[
        {
            "slot_id": "gastos",
            "kind": "excel",
            "required": True,
            "label": {
                "es": "Fichero de gastos",
                "ca": "Fitxer de despeses",
                "en": "Expenses file",
            },
        }
    ],
    parametros=[],
    finalidad="Contar las filas del fichero de gastos de un servicio",
    categorias_datos=["dades_pressupostaries"],
)


async def contar_filas(entrada: EntradaValidada) -> ExtractionResult:
    """Cuenta las filas del fichero de gastos.

    El slot `gastos` está garantizado: el contrato lo declara obligatorio y la plataforma valida
    antes de llamar. Por eso no hay un `if` defensivo aquí — y si lo hubiera, escondería el día
    en que la validación deje de correr (la lección de `una_guarda_defensiva_esconde_un_bug`).

    **Es `async` porque lee un fichero**, y leerlo es pedírselo al almacenamiento. Un `run`
    síncrono sigue valiendo —la plataforma lo manda a un hilo— pero en cuanto hay entrada que
    abrir, ésta es la forma natural.
    """
    # **La referencia no se abre: la resuelve la plataforma** (APER.14). `entrada.ficheros`
    # guarda la clave del almacenamiento —que es lo que se cita en la procedencia— y
    # `entrada.fichero(slot)` entrega una ruta local que existe mientras dure el bloque y se
    # borra al salir. Antes esto hacía `load_workbook(entrada.ficheros["gastos"])`, y eso no
    # funcionaba con un almacén que no fuera de ficheros y dejaba que quien llamara eligiera
    # qué fichero del servidor se abría.
    #
    # El recuento va **dentro** del bloque: con `read_only` openpyxl lee de forma perezosa, así
    # que fuera el fichero ya no existiría.
    # **La lectura va a un hilo (APER.25), y aquí importa el doble**: esto es lo que copia quien
    # escribe una función nueva. `openpyxl` lee de forma síncrona, así que sin esto una hoja
    # grande deja el servidor sin atender peticiones mientras la parsea. El trabajo sigue
    # **dentro** del `async with`, porque con `read_only` la lectura es perezosa y fuera del
    # bloque el fichero ya no existe.
    async with entrada.fichero("gastos") as ruta:
        filas = await asyncio.to_thread(_contar_filas, ruta)

    return ExtractionResult(
        tables=[],
        metrics=[ExtractedMetric(name="filas_de_gasto", value=filas, unit="filas")],
        free_text=f"El fichero trae {filas} filas de gasto.",
        provenance=ExtractionProvenance(
            pipeline_id="paquete-funcion-demo:contar_filas",
            source_kind="paquete",
            source_ref=entrada.ficheros["gastos"],
            extracted_at=datetime.now(timezone.utc),
        ),
    )


def _contar_filas(ruta) -> int:
    """El trabajo síncrono, en una función aparte para poder mandarlo a un hilo entero.

    Partirlo así —y no envolver sólo `load_workbook`— es lo que hace que el recuento perezoso de
    `read_only` también corra fuera del bucle. Envolver la apertura y dejar el barrido de filas
    en la corrutina habría dejado el bloqueo donde estaba, sólo que más difícil de ver.
    """
    # El import sigue siendo perezoso, como estaba: `openpyxl` es dependencia del paquete de
    # demostración, no del servidor, y cargarlo al importar el módulo lo metería en el arranque.
    import openpyxl

    libro = openpyxl.load_workbook(ruta, read_only=True)
    try:
        hoja = libro.active
        # `max_row` cuenta la cabecera, que no es un gasto.
        return max((hoja.max_row or 1) - 1, 0)
    finally:
        libro.close()


#: A esto apunta el *entry point*. El nombre y la versión los lee el catálogo; la versión tiene
#: que coincidir con la del `pyproject.toml`, porque es la que el anclaje por mayor compara.
CONTAR_FILAS = FuncionEmpaquetada(
    nombre="contar_filas",
    version="1.2.0",
    contrato=CONTRATO,
    run=contar_filas,
)

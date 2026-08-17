"""Qué actividades del módulo hablan con un modelo, con qué nivel y con qué prompt.

Escribir código y juzgar si es peligroso son tareas distintas, así que no las hace el mismo
modelo: **nivel 2 programa** y **nivel 3, superior, audita** (PRO.2). Esa asignación vive aquí
—y con ella el texto del prompt— por dos razones:

1. Es la **lista de actividades que existen**. Sin ella, saber qué partes del módulo llaman a
   un modelo exige leer seis ficheros.
2. Es lo que la biblioteca de prompts **sobreescribe** (PRO.2.1). Es la forma del legacy
   —`DEFAULT_TIER_MAPPING` en código y `tier_override` en base de datos—: el código dice qué
   actividades hay, con qué nivel corren y qué se les dice; la base de datos sólo guarda la
   excepción.

Dos reglas que hacen esto revisable, y que los tests defienden:

- **Sin fila en base de datos, todo funciona igual que antes.** La fila es una excepción, no
  un requisito, y una actividad no se puede inventar desde la pantalla: si no está aquí, no
  hay nada que la consuma.
- **El texto por defecto no se copia a la base de datos.** Copiarlo congela el prompt: a
  partir de ahí, mejorarlo aquí no llegaría a quien ya lo abrió en la pantalla.

El catálogo crece **cuando se cablea un consumidor**, no antes. Hoy están las dos actividades
de PRO.2; ETL (PRO.4), gráficos (PRO.5) y copiloto (PRO.6) entran con su prompt cuando su
consumidor pase por aquí.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal


class ActividadLLM(StrEnum):
    """Una actividad del módulo que necesita un modelo.

    El valor es la clave estable con la que se guarda el override, así que **no se renombra**
    sin migrar los datos: es el `name` de `SystemPrompt` del legacy.
    """

    PROPUESTA_DE_SCRIPT = "propuesta_de_script"
    AUDITORIA_DE_SCRIPT = "auditoria_de_script"
    TRANSFORMACION_ETL = "transformacion_etl"


#: Nivel por defecto de cada actividad. Los niveles son 1 (rápido), 2 (lógica) y 3 (supervisión).
TIER_POR_ACTIVIDAD: dict[ActividadLLM, int] = {
    # Programar es lógica: nivel 2.
    ActividadLLM.PROPUESTA_DE_SCRIPT: 2,
    # Juzgar el código de otro pide el modelo superior, y va **encima** de la auditoría
    # determinista de PRO.1, nunca en su lugar.
    ActividadLLM.AUDITORIA_DE_SCRIPT: 3,
    # Traducir «quita los duplicados y agrupa por capítulo» a operaciones también es
    # programar, aunque el resultado sea JSON y no Python: nivel 2.
    ActividadLLM.TRANSFORMACION_ETL: 2,
}


#: Para qué sirve cada actividad, en una línea. Es lo que hace legible un 503 que dice
#: «falta el nivel 2»: sin esto, quien lo lee no sabe qué se ha quedado sin hacer.
PARA_QUE_SIRVE: dict[ActividadLLM, str] = {
    ActividadLLM.PROPUESTA_DE_SCRIPT: "escribe el script de extracción",
    ActividadLLM.AUDITORIA_DE_SCRIPT: "audita el script escrito",
    ActividadLLM.TRANSFORMACION_ETL: "traduce a operaciones lo que hay que transformar",
}


# ---------------------------------------------------------------------------
# Los prompts por defecto
#
# Llevan variables `{asi}` que rellena el consumidor. Las listas de módulos y de nombres
# prohibidos **no se escriben a mano**: salen del auditor, porque un prompt que enumera lo
# que otro fichero bloquea divergen en el primer cambio, y el síntoma es una propuesta
# rechazada sin motivo entendible.
# ---------------------------------------------------------------------------

_PROMPT_PROPUESTA = """\
Eres un asistente experto en escribir scripts de extracción de datos en Python.

REGLAS DURAS:
- Sólo puedes importar de esta lista blanca: {lista_blanca}.
  Importar cualquier otro módulo es una ADVERTENCIA: el script no se ejecuta hasta que una \
persona la acepta, así que no lo hagas sin necesidad.
- Estos módulos están PROHIBIDOS y son un rechazo inmediato: {modulos_prohibidos}.
- Está PROHIBIDO usar eval, exec, __import__, compile, open.
- Está PROHIBIDO usar estos nombres, incluso de la forma más inocente: {nombres_prohibidos}. \
Dan alcance al intérprete y el auditor los marca como CRÍTICO aunque los uses para algo \
razonable (`getattr(df, metodo)` también cuenta).
- Está PROHIBIDO tocar estos atributos: {atributos_prohibidos}.
- Está PROHIBIDO escribir una ruta absoluta —ni `C:\\...`, ni `C:/...`, ni `/etc/...`, \
`/home/...`, `/tmp/...`—, ni siquiera en un comentario: es CRÍTICO. El único fichero que \
puedes leer es el que llega en `file_path`.
- El script DEBE asignar la variable `result` (dict) con las claves:
    tables   : list[dict]  → cada dict: name, headers, rows, source_page
    metrics  : list[dict]  → cada dict: name, value, unit (opcional)
    free_text: str | None
- Variables disponibles para tu script: file_path (str), raw_text (str), options (dict).
- Usa preferentemente pandas y openpyxl para Excel; pdfplumber para PDFs.
- Devuelve SÓLO código Python, sin explicaciones ni markdown.{schema}"""


_PROMPT_AUDITORIA = """\
Eres un revisor de seguridad y de calidad de scripts de extracción de datos.

El script que vas a leer **ya ha pasado un análisis estático** que bloquea por su forma las \
llamadas peligrosas, la introspección del intérprete, los módulos prohibidos y las rutas \
absolutas. Tu trabajo NO es repetir ese análisis: es mirar lo que un AST no puede ver.

Fíjate en:
- Si el script hace lo que el usuario pidió, o algo parecido pero distinto.
- Si asume nombres de columna, hojas o formatos que no consten en la petición.
- Si puede devolver datos vacíos o basura sin fallar, que es peor que fallar.
- Si mete en `free_text` información que no debería salir del fichero de entrada.

Responde SÓLO con este JSON, sin markdown ni explicaciones alrededor:
{"veredicto": "acepta|duda|rechaza", "motivos": ["...", "..."]}

`acepta` es «hace lo pedido y no veo riesgo»; `duda` es «funciona pero asume algo»; \
`rechaza` es «no hace lo pedido o es peligroso por lo que hace, no por cómo está escrito». \
Sé concreto y breve: cada motivo, una frase."""


_PROMPT_ETL = """\
Eres un planificador de transformaciones tabulares. Dado un esquema de datos y una instrucción \
en lenguaje natural, produces un plan declarativo en JSON.

DEVUELVE ÚNICAMENTE JSON VÁLIDO sin texto adicional, sin markdown, sin fences.

FORMATO:
{"mode": "operations", "operations": [ ... ]}

CADA OPERACIÓN TIENE QUE SER UNA DE ESTAS, con exactamente estos campos:
{esquema_de_operaciones}

REGLAS:
  - Usa sólo columnas presentes en el esquema de datos. Una columna que no existe **hace \
fallar la transformación**: no la inventes ni la adivines.
  - Primero limpiar y después analizar. Un fichero real llega con columnas que no se usan, \
fechas en varios formatos, filas duplicadas y celdas vacías.
  - En `format_dates`, si conoces el formato de origen decláralo: `01/03/2026` es ambiguo.
  - No inventes operaciones nuevas. Si la petición no encaja en el catálogo, devuelve \
{"mode": "operations", "operations": []}.

ESQUEMA DE LOS DATOS:
{esquema_de_datos}"""


PROMPT_POR_ACTIVIDAD: dict[ActividadLLM, str] = {
    ActividadLLM.PROPUESTA_DE_SCRIPT: _PROMPT_PROPUESTA,
    ActividadLLM.AUDITORIA_DE_SCRIPT: _PROMPT_AUDITORIA,
    ActividadLLM.TRANSFORMACION_ETL: _PROMPT_ETL,
}


#: Variables que el consumidor rellena en cada prompt. Se declaran para que la pantalla
#: pueda enseñarlas: un override que se invente una variable no se puede rellenar, y sin
#: declararlas el aviso llegaría como un hueco raro en la respuesta del modelo.
VARIABLES_POR_ACTIVIDAD: dict[ActividadLLM, tuple[str, ...]] = {
    ActividadLLM.PROPUESTA_DE_SCRIPT: (
        "lista_blanca",
        "modulos_prohibidos",
        "nombres_prohibidos",
        "atributos_prohibidos",
        "schema",
    ),
    ActividadLLM.AUDITORIA_DE_SCRIPT: (),
    ActividadLLM.TRANSFORMACION_ETL: ("esquema_de_operaciones", "esquema_de_datos"),
}


_VARIABLE = re.compile(r"\{(\w+)\}")


def variables_de(actividad: ActividadLLM) -> set[str]:
    """Las variables que de verdad aparecen en el texto del prompt de esta actividad."""
    return set(_VARIABLE.findall(PROMPT_POR_ACTIVIDAD[actividad]))


def rellenar(texto: str, valores: dict[str, Any]) -> str:
    """Sustituye `{variable}` por su valor y **deja intacto lo que no reconoce**.

    No es `str.format`: el prompt del auditor lleva dentro un JSON de ejemplo
    (`{"veredicto": ...}`) que `format` interpretaría como campo y con el que reventaría. Y
    un override escrito a mano puede inventarse una variable: mejor que se vea el hueco en la
    respuesta que un `KeyError` en la petición.
    """
    return _VARIABLE.sub(lambda m: str(valores.get(m.group(1), m.group(0))), texto)


def tier_de(actividad: ActividadLLM) -> int:
    return TIER_POR_ACTIVIDAD[actividad]


# ---------------------------------------------------------------------------
# La resolución: código por defecto, base de datos como excepción
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ActividadResuelta:
    """Con qué nivel y con qué texto corre una actividad, y de dónde sale cada cosa.

    `origen_*` no es decoración: es lo que la pantalla necesita para poder decir «Tier 2 (por
    defecto)» en vez de dejar un hueco que nadie sabe interpretar.
    """

    actividad: ActividadLLM
    tier: int
    template_text: str
    origen_del_tier: Literal["codigo", "override"]
    origen_del_texto: Literal["codigo", "override"]


async def resolver_actividad(actividad: ActividadLLM, proveedor: Any) -> ActividadResuelta:
    """Resuelve nivel y prompt de una actividad contra el `ConfigProvider`.

    Un proveedor que no sepa de actividades —o una fila que no exista— deja el código como
    está: la biblioteca añade excepciones, no requisitos.
    """
    override = None
    obtener = getattr(proveedor, "get_activity_prompt", None)
    if obtener is not None:
        override = await obtener(str(actividad))

    tier = TIER_POR_ACTIVIDAD[actividad]
    origen_del_tier: Literal["codigo", "override"] = "codigo"
    if override is not None and override.override_tier is not None:
        tier = override.override_tier
        origen_del_tier = "override"

    texto = PROMPT_POR_ACTIVIDAD[actividad]
    origen_del_texto: Literal["codigo", "override"] = "codigo"
    # Un texto en blanco significa «usa el del código», no «prompt vacío»: es lo que permite
    # volver atrás desde la pantalla sin borrar la fila por SQL.
    if override is not None and (override.template_text or "").strip():
        texto = override.template_text  # type: ignore[assignment]
        origen_del_texto = "override"

    return ActividadResuelta(
        actividad=actividad,
        tier=tier,
        template_text=texto,
        origen_del_tier=origen_del_tier,
        origen_del_texto=origen_del_texto,
    )

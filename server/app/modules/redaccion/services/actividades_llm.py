"""Qué actividades del módulo hablan con un modelo, y con qué nivel — PRO.2.

Escribir código y juzgar si es peligroso son tareas distintas, así que no las hace el mismo
modelo: **nivel 2 programa** y **nivel 3, superior, audita**. Esa asignación vive aquí y no
como un `2` y un `3` escritos en la raíz de composición, por dos razones:

1. Es la **lista de actividades que existen**. Sin ella, saber qué partes del módulo llaman a
   un modelo exige leer seis ficheros.
2. Es lo que PRO.2.1 podrá **sobreescribir** desde la biblioteca de prompts. Es la forma del
   legacy —`DEFAULT_TIER_MAPPING` en código y `tier_override` en base de datos—: el código
   dice qué actividades hay y con qué nivel corren por defecto, y la base de datos sólo
   guarda la excepción.

El catálogo crece **cuando se cablea un consumidor**, no antes: una actividad que nadie
resuelve es configuración que parece funcionar y no hace nada. Hoy están las dos de PRO.2;
ETL, gráficos, propuesta de plantilla, redacción de bloque y copiloto entran con su prompt.
"""
from __future__ import annotations

from enum import StrEnum


class ActividadLLM(StrEnum):
    """Una actividad del módulo que necesita un modelo.

    El valor es la clave estable con la que se guarda el override, así que **no se renombra**
    sin migrar los datos: es el `name` de `SystemPrompt` del legacy.
    """

    PROPUESTA_DE_SCRIPT = "propuesta_de_script"
    AUDITORIA_DE_SCRIPT = "auditoria_de_script"


#: Nivel por defecto de cada actividad. Los niveles son 1 (rápido), 2 (lógica) y 3 (supervisión).
TIER_POR_ACTIVIDAD: dict[ActividadLLM, int] = {
    # Programar es lógica: nivel 2.
    ActividadLLM.PROPUESTA_DE_SCRIPT: 2,
    # Juzgar el código de otro pide el modelo superior, y va **encima** de la auditoría
    # determinista de PRO.1, nunca en su lugar.
    ActividadLLM.AUDITORIA_DE_SCRIPT: 3,
}


#: Para qué sirve cada actividad, en una línea. Es lo que hace legible un 503 que dice
#: «falta el nivel 2»: sin esto, quien lo lee no sabe qué se ha quedado sin hacer.
PARA_QUE_SIRVE: dict[ActividadLLM, str] = {
    ActividadLLM.PROPUESTA_DE_SCRIPT: "escribe el script de extracción",
    ActividadLLM.AUDITORIA_DE_SCRIPT: "audita el script escrito",
}


def tier_de(actividad: ActividadLLM) -> int:
    return TIER_POR_ACTIVIDAD[actividad]

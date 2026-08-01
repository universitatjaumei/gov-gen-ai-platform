"""Reescritura de la consulta con el historial, antes del retrieve (RAG.10). Deploy: edge.

El problema: «i si es a l'estranger?» no contiene ninguna de las palabras por las que se
encontraría la norma. Su vector apunta a cualquier sitio y la rama léxica no tiene de dónde
agarrarse; el turno anterior sí sabe de qué se hablaba. La reescritura convierte el
seguimiento en una consulta autónoma **solo para buscar**.

Dos reglas que no se negocian, y son las que hacen que esto sea seguro de encender:

- **El chat nunca falla por la reescritura.** Excepción, timeout o respuesta anómala ⇒ se
  usa el mensaje del usuario tal cual. Es una optimización de recuperación, no un paso
  crítico, y un paso no crítico no puede tumbar la conversación.
- **La reescritura no llega a la generación.** El usuario no la escribió, y responder a una
  pregunta reformulada suena a estar contestando a otra cosa.

La plantilla vive aquí y **no es editable por el admin**: es una instrucción de máquina, no
un texto de producto, y exponerla convertiría un fallo de recuperación en una consulta de
soporte. Si algún día hay que afinarla, se afina con el dorado delante.
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

# Ventana del historial. Con más, el paso barato deja de serlo; con menos, se pierde el
# antecedente en conversaciones que van y vienen sobre dos normas.
MAX_MENSAJES = 10
TIMEOUT_POR_DEFECTO = 2.0
# Una consulta de búsqueda no pasa de una línea. Más largo que esto es que el modelo se ha
# puesto a explicar, y buscar con una explicación es peor que buscar con la pregunta.
MAX_CARACTERES = 300

PLANTILLA = """Eres un reformulador de consultas de búsqueda. A partir de la conversación,
genera la consulta de búsqueda autónoma que capture la intención del último mensaje del
usuario, resolviendo los pronombres y las referencias implícitas con el contexto.

Responde ÚNICAMENTE con la consulta, sin comillas, sin explicaciones y en el mismo idioma
que el último mensaje.

Conversación:
{historial}

Último mensaje del usuario: {consulta}

Consulta de búsqueda:"""


def necesita_reescritura(habilitado: bool, historial: list[str]) -> bool:
    """Solo con el flag encendido y al menos dos turnos previos.

    Con menos de dos no hay antecedente que resolver, así que la llamada al LLM se pagaría
    para devolver la misma consulta.
    """
    return bool(habilitado) and len(historial or []) >= 2


def _es_anomala(texto: str) -> bool:
    return not texto.strip() or len(texto) > MAX_CARACTERES


async def reescribir_consulta(
    consulta: str,
    historial: list[str],
    llm,
    timeout: float = TIMEOUT_POR_DEFECTO,
) -> str:
    """Consulta autónoma para buscar, o la original si algo no sale bien.

    Los tres fallbacks son el mismo compromiso visto desde tres sitios: excepción del
    proveedor, tardanza y respuesta que no parece una consulta. En los tres se devuelve
    `consulta`, se registra el motivo y la conversación sigue.
    """
    ventana = list(historial or [])[-MAX_MENSAJES:]
    prompt = PLANTILLA.format(historial="\n".join(ventana), consulta=consulta)

    try:
        respuesta = await asyncio.wait_for(
            llm.ainvoke([{"role": "user", "content": prompt}]), timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning("Reescritura descartada: el modelo tardó más de %ss", timeout)
        return consulta
    except Exception as fallo:  # noqa: BLE001 - cualquier fallo del proveedor cae aquí
        logger.warning("Reescritura descartada por error del modelo: %s", fallo)
        return consulta

    texto = getattr(respuesta, "content", None)
    texto = texto if isinstance(texto, str) else str(respuesta)
    if _es_anomala(texto):
        logger.warning("Reescritura descartada por respuesta anómala (%s car.)", len(texto))
        return consulta

    return texto.strip()

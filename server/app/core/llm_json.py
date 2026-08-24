"""Sacar el JSON de la respuesta de un modelo, que casi nunca viene limpio (AIS.3).

Un modelo al que se le pide JSON lo devuelve a menudo envuelto en un bloque de código, con o sin
la etiqueta del lenguaje. Quitarlo es la misma operación en todos los sitios donde se pide una
respuesta estructurada, y hasta AIS.3 vivía en `modules/redaccion/services/llm_spec_service.py`
**como función privada** — de la que `modules/curation/semantic_detector.py` tiraba por su nombre
con guion bajo.

Era el único import de módulo a módulo que no tenía justificación: no es que curación necesitara
algo de Informes, es que la utilidad estaba en el sitio equivocado. Aquí la comparten los dos sin
que ninguno dependa del otro, que es lo que pide `CONTRIBUTING.md` §5.
"""
from __future__ import annotations

import re

#: El bloque de código, con la etiqueta del lenguaje opcional. No ancla al principio de la cadena
#: a propósito: los modelos suelen añadir una frase antes («Aquí tienes el JSON:»).
_BLOQUE_DE_CODIGO = re.compile(r"```(?:json)?\s*([\s\S]*?)```")


def extraer_json(texto: str) -> str:
    """El JSON de la respuesta, sin el bloque de código si venía envuelto.

    **No valida ni parsea**: devuelve texto, y quien llama decide qué hacer con un
    `JSONDecodeError`. Es deliberado — el mensaje de error útil depende de qué se estaba
    pidiendo, y aquí no se sabe.

    Sin bloque de código devuelve el texto recortado, no una cadena vacía: una respuesta que ya
    es JSON limpio es el caso bueno y no debería pasar por una rama de fallo.
    """
    encaje = _BLOQUE_DE_CODIGO.search(texto)
    if encaje:
        return encaje.group(1).strip()
    return texto.strip()

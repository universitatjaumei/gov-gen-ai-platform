"""El contenido de una respuesta de modelo, como texto plano. Deploy: shared.

Gemini devuelve `content` como **lista de bloques** en cuanto la respuesta tiene más de una
parte. Quien asume que siempre es `str` no falla al recibirla: falla más tarde y en otro
sitio —el validador de citas del chatbot murió con `TypeError: expected string or bytes-like
object, got 'list'`, y en redacción la lista acabaría escrita dentro del informe—.

Vive en `core/` porque el problema no es de ningún módulo: es de la frontera con el
proveedor, y ya mordió en dos.
"""
from __future__ import annotations

from typing import Any


def texto_de(contenido: Any) -> str:
    """Texto plano de una respuesta de LangChain, venga como mensaje, cadena o bloques.

    Acepta el mensaje entero además del `content` porque el desenvoltorio se escribía a mano en
    ocho sitios, siempre igual: leer `.content` con un `hasattr` de guarda y un `str()` de
    reserva. Esa forma protege del caso raro —que no llegue un mensaje— y deja pasar el
    frecuente, que el `content` sea una lista de bloques. Con el desenvoltorio aquí, el sitio de
    llamada no tiene ocasión de equivocarse, y un guardarraíl de USR.8 impide que vuelva.
    """
    contenido = getattr(contenido, "content", contenido)
    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        partes: list[str] = []
        for bloque in contenido:
            if isinstance(bloque, str):
                partes.append(bloque)
            elif isinstance(bloque, dict) and bloque.get("type") == "text":
                partes.append(bloque.get("text") or "")
        return "".join(partes)
    return str(contenido or "")

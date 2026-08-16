"""Tool: lista las fichas de los documentos disponibles para el chatbot.

VIS.2: acepta `submateries` para pedir el indice de 1-3 temas del indice de materias que
el modelo ya tiene en el system prompt. No hay un tool `list_submateries` hermano: el
indice esta en el prompt, asi que preguntarlo seria una llamada de mas.
"""

import uuid
from typing import Annotated, Any, Protocol

from langchain_core.tools import InjectedToolArg


class DocumentIndexProtocol(Protocol):
    async def list_index(
        self,
        chatbot_id: uuid.UUID,
        language: str | None,
        submateries: list[str] | None = None,
    ) -> list[dict]: ...


# `chatbot_id`, `index` e `language` van **inyectados**: los pone el AgenticLoop y el modelo
# no tiene forma de saberlos. Pedírselos en el esquema era, además del ruido, lo que hacía
# morir a `bind_tools` con `SchemaError` al intentar validar el Protocol.
async def list_documents(
    chatbot_id: Annotated[str, InjectedToolArg] = "",
    index: Annotated[Any, InjectedToolArg] = None,
    language: Annotated[str | None, InjectedToolArg] = None,
    submateries: list[str] | None = None,
) -> str:
    """Devuelve las fichas de los documentos de las submaterias pedidas.

    Cada entrada: `[id] titulo (rango, idioma, ~tokens) — resumen`. El LLM la lee y
    decide que cargar con `read_document(id=<uuid>)`. La ficha no lleva el contenido.
    """
    items = await index.list_index(uuid.UUID(chatbot_id), language, submateries)
    if not items:
        return "No hay documentos disponibles para este chatbot."
    lines = ["Documentos disponibles (usa read_document(id=<id>) para leer uno):"]
    for it in items:
        atributos = [a for a in (it.get("rang"), it["language"]) if a]
        atributos.append(f"~{it['token_count']} tokens")
        resumen = f" — {it['resum_router']}" if it.get("resum_router") else ""
        lines.append(f"[{it['id']}] {it['title']} ({', '.join(atributos)}){resumen}")
        lines.append(f"    {it['url']}")
    return "\n".join(lines)

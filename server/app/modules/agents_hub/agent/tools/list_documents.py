"""Tool: lista el indice de documentos disponibles para el chatbot."""

import uuid
from typing import Protocol


class DocumentIndexProtocol(Protocol):
    async def list_index(self, chatbot_id: uuid.UUID, language: str | None) -> list[dict]: ...


async def list_documents(
    chatbot_id: str,
    index: DocumentIndexProtocol,
    language: str | None = None,
) -> str:
    """Devuelve un indice formateado de documentos disponibles.

    Cada entrada: `[id] titulo -- seccion_path (idioma, ~tokens)`. El LLM lo lee y decide
    que cargar con `read_document(id=<uuid>)`.
    """
    items = await index.list_index(uuid.UUID(chatbot_id), language)
    if not items:
        return "No hay documentos disponibles para este chatbot."
    lines = ["Documentos disponibles (usa read_document(id=<id>) para leer uno):"]
    for it in items:
        section = f" -- {it['section_path']}" if it.get("section_path") else ""
        lines.append(
            f"[{it['id']}] {it['title']}{section} "
            f"({it['language']}, ~{it['token_count']} tokens, {it['url']})"
        )
    return "\n".join(lines)

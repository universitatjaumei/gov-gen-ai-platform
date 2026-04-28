"""Tool: devuelve el markdown completo de un documento."""

import uuid
from typing import Protocol


class DocumentReaderProtocol(Protocol):
    async def read(self, document_id: uuid.UUID) -> dict | None: ...


async def read_document(
    document_id: str,
    reader: DocumentReaderProtocol,
) -> str:
    """Devuelve el markdown completo del documento solicitado para que el LLM lo cite.

    El LLM debe citar como `[titulo](url)` tras cada afirmacion factual basada en este
    contenido. Si el documento no existe, devuelve un mensaje explicito.
    """
    doc = await reader.read(uuid.UUID(document_id))
    if not doc:
        return f"Documento {document_id} no encontrado."
    return (
        f"# {doc['title']}\n"
        f"_Fuente: {doc['url']}_\n\n"
        f"{doc['markdown_content']}"
    )

"""Tool: devuelve el markdown completo de un documento."""

import uuid
from typing import Annotated, Any, Protocol

from langchain_core.tools import InjectedToolArg


class DocumentReaderProtocol(Protocol):
    async def read(self, document_id: uuid.UUID) -> dict | None: ...


# `reader` va como argumento **inyectado**: lo pone el AgenticLoop, no el modelo. Sin la
# marca, `bind_tools` intenta construir un validador para el Protocol y muere con
# `SchemaError`, así que el modo selector no llegaba a ejecutar ni una vuelta.
async def read_document(
    document_id: str,
    reader: Annotated[Any, InjectedToolArg] = None,
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

"""Herramienta de búsqueda en la base de conocimiento."""

import uuid
from typing import Annotated, Any, Protocol

from langchain_core.tools import InjectedToolArg


class RetrieverProtocol(Protocol):
    async def hybrid_search(
        self,
        query: str,
        query_embedding: list[float],
        chatbot_id: uuid.UUID,
        top_k: int,
        language: str | None,
    ) -> list: ...


class EmbeddingProtocol(Protocol):
    async def embed(self, text: str) -> list[float]: ...


# Todo lo que no es la consulta va **inyectado**: el chatbot, el retriever, los embeddings
# y el idioma los pone quien orquesta. El modelo solo aporta lo que solo él sabe.
async def search_knowledge(
    query: str,
    chatbot_id: Annotated[str, InjectedToolArg] = "",
    retriever: Annotated[Any, InjectedToolArg] = None,
    embedding_service: Annotated[Any, InjectedToolArg] = None,
    top_k: int = 5,
    language: Annotated[str | None, InjectedToolArg] = None,
) -> str:
    """Busca fragmentos concretos dentro del corpus, sin cargar los documentos enteros.

    Es la vía para consultar las normas externas —la Ley de Contratos y similares—, que son
    demasiado largas para leerlas completas con `read_document`.

    Args:
        query: Qué se busca, con las palabras de la norma
        top_k: Número de fragmentos a traer

    Returns:
        Texto formateado con los resultados
    """
    query_embedding = await embedding_service.embed(query)

    results = await retriever.hybrid_search(
        query=query,
        query_embedding=query_embedding,
        chatbot_id=uuid.UUID(chatbot_id),
        top_k=top_k,
        language=language,
    )

    if not results:
        return "No se encontró información relevante para tu consulta."

    formatted = "**Información encontrada:**\n\n"
    for i, result in enumerate(results, 1):
        formatted += f"{i}. {result.content[:200]}...\n"
        src = result.source_url
        if src.startswith("http://") or src.startswith("https://"):
            formatted += f"   _Fuente: [{src}]({src})_\n\n"
        else:
            formatted += f"   _Fuente: {result.source_url.split('/')[-1].split(chr(92))[-1]}_\n\n"

    return formatted

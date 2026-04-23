"""Herramienta de búsqueda en la base de conocimiento."""
import uuid
from typing import Protocol


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


async def search_knowledge(
    query: str,
    chatbot_id: str,
    retriever: RetrieverProtocol,
    embedding_service: EmbeddingProtocol,
    top_k: int = 5,
    language: str | None = None,
) -> str:
    """Busca información relevante en la base de conocimiento.

    Args:
        query: Consulta de búsqueda
        chatbot_id: ID del chatbot
        retriever: Servicio de recuperación
        embedding_service: Servicio de embeddings
        top_k: Número de resultados
        language: Filtro de idioma

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
        formatted += f"   _Fuente: {result.source_url}_\n\n"

    return formatted

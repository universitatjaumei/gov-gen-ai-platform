"""Tipos compartidos entre las distintas RetrievalStrategy."""

import uuid
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Source:
    """Documento citable devuelto por una RetrievalStrategy."""
    document_id: uuid.UUID
    title: str
    url: str
    excerpt: str            # fragmento mostrado al LLM (puede ser el documento completo)
    score: float            # relevancia [0, 1] (1.0 si la strategy no calcula score)
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalContext:
    """Contexto agregado que se pasa al nodo generate_response."""
    sources: list[Source]
    mode: str                       # "RAG" | "MD_LONG_CONTEXT" | "MD_AGENT_SELECTOR"
    total_tokens: int               # suma estimada de tokens del excerpt agregado


class RetrievalStrategy(Protocol):
    """Contrato comun a las tres estrategias.

    Las strategies que pre-recuperan (vector, long_context) implementan get_context.
    AgenticRetrievalStrategy devuelve un RetrievalContext vacio y expone tools al grafo.
    """

    mode: str  # "RAG" | "MD_LONG_CONTEXT" | "MD_AGENT_SELECTOR"

    async def get_context(
        self,
        query: str,
        chatbot_id: uuid.UUID,
        language: str | None = None,
    ) -> RetrievalContext: ...

    def get_agent_tools(self) -> list:
        """Devuelve lista de tools LangChain (vacia salvo en agentic)."""
        ...

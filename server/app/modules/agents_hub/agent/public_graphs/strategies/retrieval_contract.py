"""Contrato común de salida del retrieval para grafos públicos.

Todas las RetrievalPipeline deben devolver un RetrievalResult con
EvidenceItem uniformes, independientemente de la estrategia usada
(RAG vectorial, MD long context, MD agent selector).

Deploy: edge
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvidenceItem:
    """Un fragmento de evidencia devuelto por cualquier pipeline de retrieval."""

    source_id: str
    content: str
    source_url: str | None = None
    title: str | None = None
    language: str | None = None
    score: float | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Resultado completo de un pipeline de retrieval.

    context_source_language: idioma predominante de los items recuperados
        (None si los items no tienen idioma homogéneo o no hay items).
    debug: información trazable (tokens_used, docs_selected, pipeline_mode, etc.).
    """

    items: list[EvidenceItem]
    debug: dict
    context_source_language: str | None = None

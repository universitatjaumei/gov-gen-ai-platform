"""Perfil PUBLIC_KB_RICH — chatbot público genérico con KB enriquecida.

Compatible con los tres modos de retrieval (RAG, MD_LONG_CONTEXT, MD_AGENT_SELECTOR).
Sin lógica de dominio; apto para grupos, oferta académica, FAQs municipales, etc.

Deploy: edge
"""
from __future__ import annotations

from server.app.modules.agents_hub.agent.language_detector import (
    detect_language as _detect_language,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.protocols import (
    PipelineRetrievalStrategy,
    PreferLanguagePolicy,
    RetrievalOutput,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
)


class SingleSourceRetrievalStrategy(PipelineRetrievalStrategy):
    """Retrieval desde una única fuente, seleccionada por cfg.retrieval_mode.

    Hereda PipelineRetrievalStrategy sin modificaciones; el nombre explicita
    que este perfil usa siempre una sola fuente por consulta.
    """


class PassthroughMergeStrategy:
    """Fusiona los buckets aplanando todos sus items en una lista única."""

    def merge(self, output: RetrievalOutput) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []
        for bucket in output.buckets:
            items.extend(bucket.items)
        return items


class GenericAnswerTemplateStrategy:
    """Plantilla genérica: instrucción de sistema + evidencias enumeradas."""

    def build_prompt_context(
        self,
        items: list[EvidenceItem],
        language: str | None,
        query: str,
    ) -> str:
        lang_hint = f"Responde en idioma: {language}." if language else ""
        if not items:
            return (
                f"{lang_hint}\n\n"
                "No hay evidencias disponibles para responder esta consulta."
            ).strip()
        blocks = "\n\n".join(
            f"[{i + 1}] {item.title or item.source_id}\n{item.content}"
            for i, item in enumerate(items)
        )
        return (
            f"{lang_hint}\n\n"
            "Usa únicamente la información de las siguientes evidencias para responder.\n\n"
            f"{blocks}"
        ).strip()


class DefaultLanguagePolicy(PreferLanguagePolicy):
    """Política de idioma por defecto para PUBLIC_KB_RICH: prefer con langdetect."""

    def detect(self, query: str) -> str | None:
        return _detect_language(query)

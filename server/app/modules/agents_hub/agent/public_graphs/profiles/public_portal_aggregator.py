"""Perfil PUBLIC_PORTAL_AGGREGATOR (UJI) — dos fuentes (procedimientos + normativa).

  - UjiDualSourceRetrievalStrategy : recupera de ambas fuentes y devuelve dos buckets
  - UjiMergeStrategy               : procedimiento top + normativa enlazada; solo normativa si no hay candidato
  - UjiAnswerTemplateStrategy      : secciones Procedimiento / Normativa + warning de traducción

Deploy: edge
"""
from __future__ import annotations

import uuid
from collections import Counter
from typing import TYPE_CHECKING

from server.app.modules.agents_hub.agent.public_graphs.strategies.protocols import (
    RetrievalOutput,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_pipeline_factory import (
    get_pipeline,
)

if TYPE_CHECKING:
    from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
        PublicGraphConfig,
    )
    from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_pipeline_protocol import (
        GraphDeps,
    )


class UjiDualSourceRetrievalStrategy:
    """Recupera de procedimientos y normativa por separado y devuelve dos buckets."""

    def __init__(
        self,
        procedimientos_chatbot_id: uuid.UUID,
        normativa_chatbot_id: uuid.UUID,
    ) -> None:
        self.procedimientos_chatbot_id = procedimientos_chatbot_id
        self.normativa_chatbot_id = normativa_chatbot_id

    async def retrieve(
        self,
        query: str,
        chatbot_id: str,
        cfg: "PublicGraphConfig",
        deps: "GraphDeps",
    ) -> RetrievalOutput:
        pipeline = get_pipeline(cfg.retrieval_mode)
        proc_result = await pipeline.run(
            query, str(self.procedimientos_chatbot_id), cfg, deps
        )
        norm_result = await pipeline.run(
            query, str(self.normativa_chatbot_id), cfg, deps
        )
        return RetrievalOutput(buckets=[proc_result, norm_result])


class UjiMergeStrategy:
    """Fusión UJI: procedimiento top + normativa; solo normativa si no hay candidato."""

    def merge(self, output: RetrievalOutput) -> list:
        proc_items = list(output.buckets[0].items) if output.buckets else []
        norm_items = list(output.buckets[1].items) if len(output.buckets) > 1 else []

        if not proc_items:
            return norm_items
        return proc_items + norm_items


class UjiAnswerTemplateStrategy:
    """Plantilla UJI: secciones Procedimiento / Normativa + warning de traducción."""

    def build_prompt_context(
        self,
        items: list,
        language: str | None,
        query: str,
    ) -> str:
        proc_items = [
            i for i in items if i.metadata.get("source_type") == "procedimiento"
        ]
        norm_items = [
            i for i in items if i.metadata.get("source_type") == "normativa"
        ]

        lang_counts = Counter(
            getattr(i, "language", None) for i in items if getattr(i, "language", None)
        )
        dominant_lang = lang_counts.most_common(1)[0][0] if lang_counts else None

        parts: list[str] = []

        if dominant_lang and language and dominant_lang != language:
            parts.append(
                f"[Nota de traducción / Nota de traducció: "
                f"El contenido está en '{dominant_lang}' pero la consulta está en '{language}'. "
                f"Idioma solicitado: {language}]"
            )

        parts.append("## Procedimiento")
        for item in proc_items:
            title = getattr(item, "title", None) or item.source_id
            parts.append(f"**{title}**\n{item.content}")
        if not proc_items:
            parts.append("(Sin procedimiento disponible)")

        parts.append("## Normativa")
        for item in norm_items:
            title = getattr(item, "title", None) or item.source_id
            parts.append(f"**{title}**\n{item.content}")
        if not norm_items:
            parts.append("(Sin normativa disponible)")

        return "\n\n".join(parts)

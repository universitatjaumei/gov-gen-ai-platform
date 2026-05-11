"""Tests del perfil PUBLIC_PORTAL_AGGREGATOR (UJI) — 9B.10 (RED).

El perfil UJI agrega dos fuentes (procedimientos + normativa) con cualquier retrieval_mode.
Estos tests FALLAN con el stub y pasarán tras la implementación del prompt 9B.11.

Contrato esperado:
  UjiDualSourceRetrievalStrategy.retrieve():
    - Llama al pipeline(cfg.retrieval_mode) para cada fuente
    - Devuelve RetrievalOutput con dos buckets: [0]=procedimientos, [1]=normativa

  UjiMergeStrategy.merge():
    - Si hay procedimiento candidato: procedimiento top + normativa enlazada + respaldo
    - Si no: sólo normativa

  UjiAnswerTemplateStrategy.build_prompt_context():
    - Contiene secciones "Procedimiento" y "Normativa"
    - Añade warning de traducción cuando context_language != query_language
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
    PublicGraphConfig,
)
from server.app.modules.agents_hub.agent.public_graphs.profiles.public_portal_aggregator import (
    UjiAnswerTemplateStrategy,
    UjiDualSourceRetrievalStrategy,
    UjiMergeStrategy,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.protocols import RetrievalOutput
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
    RetrievalResult,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_pipeline_protocol import (
    GraphDeps,
)

# ---------------------------------------------------------------------------
# Fixtures y helpers
# ---------------------------------------------------------------------------

PROC_ID = uuid.uuid4()
NORM_ID = uuid.uuid4()

_PROC_ITEM = EvidenceItem(
    source_id=str(PROC_ID),
    content="Procedimiento de matrícula universitaria.",
    title="Matrícula",
    score=0.92,
    language="es",
    metadata={"source_type": "procedimiento"},
)
_NORM_ITEM = EvidenceItem(
    source_id=str(NORM_ID),
    content="Artículo 10 del Reglamento de Acceso.",
    title="Reglamento de Acceso",
    score=0.87,
    language="es",
    metadata={"source_type": "normativa"},
)
_PROC_ITEM_CA = EvidenceItem(
    source_id=str(PROC_ID),
    content="Procediment de matrícula universitària.",
    title="Matrícula",
    score=0.92,
    language="ca",
    metadata={"source_type": "procedimiento"},
)
_NORM_ITEM_CA = EvidenceItem(
    source_id=str(NORM_ID),
    content="Article 10 del Reglament d'Accés.",
    title="Reglament d'Accés",
    score=0.87,
    language="ca",
    metadata={"source_type": "normativa"},
)


def _make_cfg(mode: str) -> PublicGraphConfig:
    return PublicGraphConfig(
        profile="PUBLIC_PORTAL_AGGREGATOR",
        retrieval_mode=mode,
        language_mode="prefer",
        quality_threshold=0.6,
        min_retrieval_results=1,
        min_retrieval_score=0.25,
        reranker_enabled=False,
        answer_template="uji",
    )


def _make_mock_pipeline(proc_item: EvidenceItem, norm_item: EvidenceItem, mode: str):
    """Pipeline mock que distingue la fuente por el chatbot_id recibido."""
    proc_result = RetrievalResult(
        items=[proc_item],
        debug={"pipeline_mode": mode, "source": "procedimientos"},
    )
    norm_result = RetrievalResult(
        items=[norm_item],
        debug={"pipeline_mode": mode, "source": "normativa"},
    )

    async def run_side_effect(query, chatbot_id, cfg, deps):
        return proc_result if chatbot_id == str(PROC_ID) else norm_result

    pipeline = MagicMock()
    pipeline.run = run_side_effect
    return pipeline


# ---------------------------------------------------------------------------
# Tests del UjiDualSourceRetrievalStrategy
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestUjiDualSourceRetrievalStrategy:

    async def _run(self, mode: str) -> RetrievalOutput:
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())
        cfg = _make_cfg(mode)
        mock_pipeline = _make_mock_pipeline(_PROC_ITEM, _NORM_ITEM, mode)

        with patch(
            "server.app.modules.agents_hub.agent.public_graphs.profiles.public_portal_aggregator.get_pipeline",
            return_value=mock_pipeline,
        ):
            strategy = UjiDualSourceRetrievalStrategy(
                procedimientos_chatbot_id=PROC_ID,
                normativa_chatbot_id=NORM_ID,
            )
            return await strategy.retrieve(
                "¿Cuál es el procedimiento de matrícula?",
                str(uuid.uuid4()),
                cfg,
                deps,
            )

    async def test_uji_aggregator_rag_mode_combines_procedure_and_normativa(self):
        """En modo RAG, retrieve() devuelve buckets con items de procedimiento y normativa."""
        output = await self._run("RAG")

        assert len(output.buckets) == 2
        all_items = [item for b in output.buckets for item in b.items]
        source_types = {item.metadata.get("source_type") for item in all_items}
        assert "procedimiento" in source_types, "Falta bucket de procedimientos"
        assert "normativa" in source_types, "Falta bucket de normativa"

    async def test_uji_aggregator_md_long_context_mode_combines_procedure_and_normativa(self):
        """En modo MD_LONG_CONTEXT, retrieve() devuelve buckets de ambas fuentes."""
        output = await self._run("MD_LONG_CONTEXT")

        assert len(output.buckets) == 2
        all_items = [item for b in output.buckets for item in b.items]
        source_types = {item.metadata.get("source_type") for item in all_items}
        assert "procedimiento" in source_types
        assert "normativa" in source_types

    async def test_uji_aggregator_md_agent_selector_mode_combines_procedure_and_normativa(self):
        """En modo MD_AGENT_SELECTOR, retrieve() devuelve buckets de ambas fuentes."""
        output = await self._run("MD_AGENT_SELECTOR")

        assert len(output.buckets) == 2
        all_items = [item for b in output.buckets for item in b.items]
        source_types = {item.metadata.get("source_type") for item in all_items}
        assert "procedimiento" in source_types
        assert "normativa" in source_types


# ---------------------------------------------------------------------------
# Tests del UjiMergeStrategy
# ---------------------------------------------------------------------------

class TestUjiMergeStrategy:

    def test_uji_normativa_only_when_no_procedure_candidate(self):
        """Sin ítems de procedimiento, merge devuelve únicamente normativa."""
        proc_bucket = RetrievalResult(items=[], debug={"source": "procedimientos"})
        norm_bucket = RetrievalResult(items=[_NORM_ITEM], debug={"source": "normativa"})
        output = RetrievalOutput(buckets=[proc_bucket, norm_bucket])

        merged = UjiMergeStrategy().merge(output)

        assert len(merged) > 0, "Debe devolver al menos los ítems de normativa"
        for item in merged:
            assert item.metadata.get("source_type") == "normativa", (
                f"Sin candidato de procedimiento, no deben aparecer ítems de tipo "
                f"'{item.metadata.get('source_type')}'"
            )

    def test_uji_merge_includes_both_when_procedure_candidate_exists(self):
        """Con candidato de procedimiento, merge incluye ítems de ambas fuentes."""
        proc_bucket = RetrievalResult(items=[_PROC_ITEM], debug={"source": "procedimientos"})
        norm_bucket = RetrievalResult(items=[_NORM_ITEM], debug={"source": "normativa"})
        output = RetrievalOutput(buckets=[proc_bucket, norm_bucket])

        merged = UjiMergeStrategy().merge(output)

        source_types = {item.metadata.get("source_type") for item in merged}
        assert "procedimiento" in source_types, "Debe incluir el procedimiento candidato"
        assert "normativa" in source_types, "Debe incluir normativa de respaldo"


# ---------------------------------------------------------------------------
# Tests del UjiAnswerTemplateStrategy
# ---------------------------------------------------------------------------

class TestUjiAnswerTemplateStrategy:

    def test_uji_answer_template_sections_present(self):
        """El contexto generado debe contener secciones de Procedimiento y Normativa."""
        items = [_PROC_ITEM, _NORM_ITEM]
        context = UjiAnswerTemplateStrategy().build_prompt_context(items, "es", "consulta")

        assert "procedimiento" in context.lower(), "Falta sección de procedimiento"
        assert "normativa" in context.lower(), "Falta sección de normativa"

    def test_uji_translation_warning_only_when_context_language_differs(self):
        """Warning de traducción sólo cuando context_language != query_language."""
        # Contexto en español, usuario en catalán → warning esperado
        items_es = [_PROC_ITEM, _NORM_ITEM]  # language="es"
        context_with_warning = UjiAnswerTemplateStrategy().build_prompt_context(
            items_es, "ca", "Quina és la matrícula?"
        )
        assert any(
            kw in context_with_warning.lower()
            for kw in ("traducc", "traducción", "traducció", "language", "idioma")
        ), "Debe incluir un aviso de traducción cuando los idiomas difieren"

        # Contexto en catalán, usuario en catalán → sin warning
        items_ca = [_PROC_ITEM_CA, _NORM_ITEM_CA]  # language="ca"
        context_no_warning = UjiAnswerTemplateStrategy().build_prompt_context(
            items_ca, "ca", "Quina és la matrícula?"
        )
        assert not any(
            kw in context_no_warning.lower()
            for kw in ("traducc", "traducción", "traducció")
        ), "No debe incluir warning de traducción cuando los idiomas coinciden"

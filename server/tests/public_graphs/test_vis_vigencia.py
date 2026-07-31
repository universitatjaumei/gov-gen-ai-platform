"""Tests VIS.3 — la advertencia de vigencia es una garantía, no una instrucción.

El riesgo nº1 del corpus medido en el informe: 312 de 314 fichas dicen «vigent?». Si el
asistente cita una de ellas sin decir que su vigencia no está validada, está afirmando algo
que nadie ha comprobado.

Por eso el aviso NO es una frase suelta en el system prompt: sale de un flag de la
evidencia y lo emite el CoreGraph después de generar la respuesta. Una instrucción al modelo
se cumple casi siempre, y «casi siempre» no es una garantía.
"""
from __future__ import annotations

import uuid

import pytest

from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
)


def _item(titulo: str, sin_validar: bool) -> EvidenceItem:
    return EvidenceItem(
        source_id=str(uuid.uuid4()),
        content=f"Article 1 de {titulo}",
        source_url=f"https://www.uji.es/{titulo}",
        title=titulo,
        language="ca",
        score=0.9,
        metadata={"vigencia_no_validada": sin_validar},
    )


class TestPlantilla:

    def test_should_mark_unvalidated_documents_in_the_sources_block(self):
        from server.app.modules.agents_hub.agent.public_graphs.profiles.public_kb_rich import (
            GenericAnswerTemplateStrategy,
        )

        prompt = GenericAnswerTemplateStrategy().build_prompt_context(
            [_item("Sense validar", True), _item("Validada", False)],
            "ca",
            "quant cobro?",
        )

        bloque_sin_validar = prompt.split("## Sense validar")[1].split("## Validada")[0]
        assert "VIGENCIA NO VALIDADA" in bloque_sin_validar
        bloque_validado = prompt.split("## Validada")[1]
        assert "VIGENCIA NO VALIDADA" not in bloque_validado


class TestAvisoEnLaRespuesta:

    @pytest.mark.asyncio
    async def test_should_warn_when_cited_document_has_unvalidated_vigencia(self):
        from server.app.modules.agents_hub.agent.public_graphs.core.core_graph import CoreGraph
        from server.app.modules.agents_hub.services.retrieval.vigencia import (
            AVISO_VIGENCIA_NO_VALIDADA,
        )

        estado = await _ejecutar_grafo([_item("Sense validar", True)])

        assert AVISO_VIGENCIA_NO_VALIDADA in estado["answer"]
        assert CoreGraph is not None  # el aviso lo pone el grafo, no la estrategia

    @pytest.mark.asyncio
    async def test_should_not_warn_when_vigencia_is_validated(self):
        from server.app.modules.agents_hub.services.retrieval.vigencia import (
            AVISO_VIGENCIA_NO_VALIDADA,
        )

        estado = await _ejecutar_grafo([_item("Validada", False)])

        assert AVISO_VIGENCIA_NO_VALIDADA not in estado["answer"]

    @pytest.mark.asyncio
    async def test_should_name_the_unvalidated_document_in_the_warning(self):
        """Un aviso genérico no sirve: hay que saber DE QUÉ norma se duda."""
        estado = await _ejecutar_grafo(
            [_item("Sense validar", True), _item("Validada", False)]
        )

        assert "Sense validar" in estado["answer"].split("---")[-1]
        assert "Validada" not in estado["answer"].split("---")[-1]


# ───────────────────────── Andamiaje del grafo ─────────────────────────


async def _ejecutar_grafo(items: list[EvidenceItem]) -> dict:
    from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
        PublicGraphConfig,
    )
    from server.app.modules.agents_hub.agent.public_graphs.core.core_graph import CoreGraph
    from server.app.modules.agents_hub.agent.public_graphs.profiles.public_kb_rich import (
        GenericAnswerTemplateStrategy,
    )
    from server.app.modules.agents_hub.agent.public_graphs.strategies.protocols import (
        RetrievalOutput,
    )
    from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
        RetrievalResult,
    )

    class _Retrieval:
        async def retrieve(self, query, chatbot_id, cfg, deps):
            return RetrievalOutput(
                buckets=[RetrievalResult(items=items, debug={}, context_source_language="ca")]
            )

    class _Merge:
        def merge(self, output):
            return [i for b in output.buckets for i in b.items]

    class _Lang:
        def detect(self, query):
            return "ca"

        def filter_items(self, language, items):
            return items

        def should_warn_translation(self, a, b):
            return False

    class _Resp:
        def __init__(self, content):
            self.content = content

    class _LLM:
        async def ainvoke(self, mensajes):
            citas = " ".join(f"[{i.title}]({i.source_url})" for i in items)
            return _Resp(f"L'import es X. {citas}")

    cfg = PublicGraphConfig(
        profile="PUBLIC_KB_RICH", retrieval_mode="RAG", language_mode="prefer",
        quality_threshold=0.0, min_retrieval_results=1, min_retrieval_score=0.0,
        reranker_enabled=False, answer_template="generic",
    )
    grafo = CoreGraph(
        retrieval_strategy=_Retrieval(),
        merge_strategy=_Merge(),
        template_strategy=GenericAnswerTemplateStrategy(),
        language_policy=_Lang(),
        cfg=cfg,
        deps=type("D", (), {"session": None, "embedder": None, "llm": None})(),
        llm=_LLM(),
    )
    return await grafo.run("quant cobro?", str(uuid.uuid4()))

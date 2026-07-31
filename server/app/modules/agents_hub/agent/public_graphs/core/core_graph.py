"""CoreGraph — orquestación común de grafos públicos.

Flujo: detect_language → retrieve → merge → quality_gate
         → generate_answer → log → END
         → fallback → END

No contiene lógica específica de dominio ni de retrieval_mode.
Todas las decisiones de dominio están encapsuladas en las estrategias inyectadas.

Deploy: edge
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from typing_extensions import TypedDict

from langgraph.graph import END, StateGraph

from server.app.modules.agents_hub.agent.public_graphs.strategies.protocols import (
    LanguagePolicy,
    MergeStrategy,
    RetrievalOutput,
    RetrievalStrategy,
    TemplateStrategy,
)
from server.app.modules.agents_hub.agent.citation_validator import (
    NO_CITATION_FALLBACK,
    enforce_citation_contract,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
)
from server.app.modules.agents_hub.services.retrieval.vigencia import (
    aviso_para as aviso_de_vigencia,
)

if TYPE_CHECKING:
    from server.app.modules.agents_hub.agent.public_graphs.strategies.agentic_loop import (
        AgenticLoop,
    )
    from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
        PublicGraphConfig,
    )
    from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_pipeline_protocol import (
        GraphDeps,
    )


class CoreGraphState(TypedDict):
    """Estado interno del CoreGraph."""

    query: str
    chatbot_id: str
    language: str | None
    retrieval_output: Any          # RetrievalOutput | None
    merged_items: list             # list[EvidenceItem]
    answer: str | None
    quality_score: float
    fallback_used: bool
    translation_warning: bool
    fallback_reason: str | None     # 'quality_gate' | 'citation' | None (RAG.2)
    sources: list                  # list[EvidenceItem] citables emitidas en el done SSE


class CoreGraph:
    """Orquestador común para todos los grafos públicos.

    Acepta estrategias intercambiables y ejecuta el flujo canónico sin
    conocer el retrieval_mode ni la lógica de dominio del chatbot.
    """

    def __init__(
        self,
        retrieval_strategy: RetrievalStrategy,
        merge_strategy: MergeStrategy,
        template_strategy: TemplateStrategy,
        language_policy: LanguagePolicy,
        cfg: "PublicGraphConfig",
        deps: "GraphDeps",
        llm: Any = None,
        agentic_loop: "AgenticLoop | None" = None,
    ) -> None:
        self.retrieval_strategy = retrieval_strategy
        self.merge_strategy = merge_strategy
        self.template_strategy = template_strategy
        self.language_policy = language_policy
        self.cfg = cfg
        self.deps = deps
        self.llm = llm
        self.agentic_loop = agentic_loop

    def compile(self):
        """Compila y devuelve el grafo LangGraph listo para invocar."""
        graph = StateGraph(CoreGraphState)

        async def detect_language_node(state: CoreGraphState) -> dict:
            lang = self.language_policy.detect(state["query"])
            return {"language": lang}

        async def retrieve_node(state: CoreGraphState) -> dict:
            output = await self.retrieval_strategy.retrieve(
                state["query"],
                state["chatbot_id"],
                self.cfg,
                self.deps,
            )
            return {"retrieval_output": output}

        async def merge_node(state: CoreGraphState) -> dict:
            raw = state.get("retrieval_output")
            output: RetrievalOutput = raw if raw is not None else RetrievalOutput()
            items: list[EvidenceItem] = self.merge_strategy.merge(output)

            query_language = state.get("language")
            items = self.language_policy.filter_items(query_language, items)

            context_source_language: str | None = None
            if output.buckets:
                context_source_language = output.buckets[0].context_source_language

            translation_warning = self.language_policy.should_warn_translation(
                query_language, context_source_language
            )

            if not items:
                score = 0.0
            else:
                scores = [i.score for i in items if i.score is not None]
                avg = sum(scores) / len(scores) if scores else 0.5
                count_ok = len(items) >= self.cfg.min_retrieval_results
                score = avg if count_ok else avg * 0.5

            return {
                "merged_items": items,
                "quality_score": score,
                "translation_warning": translation_warning,
            }

        def quality_gate(
            state: CoreGraphState,
        ) -> Literal["generate_answer", "fallback"]:
            if state["quality_score"] >= self.cfg.quality_threshold:
                return "generate_answer"
            return "fallback"

        async def generate_answer_node(state: CoreGraphState) -> dict:
            items: list[EvidenceItem] = state["merged_items"]
            context = self.template_strategy.build_prompt_context(
                items,
                state.get("language"),
                state["query"],
            )
            if self.llm is None:
                return {
                    "answer": context,
                    "fallback_used": False,
                    "fallback_reason": None,
                    "sources": items,
                }

            if self.agentic_loop is not None:
                # Modo MD_AGENT_SELECTOR: los items recuperados son el ÍNDICE, y sólo se
                # pueden citar los documentos que el loop lea de verdad.
                citables, answer = await self.agentic_loop.run(
                    llm=self.llm,
                    system=context,
                    query=state["query"],
                    chatbot_id=state["chatbot_id"],
                    language=state.get("language"),
                )
            else:
                response = await self.llm.ainvoke([
                    {"role": "system", "content": context},
                    {"role": "user", "content": state["query"]},
                ])
                answer = response.content if hasattr(response, "content") else str(response)
                citables = items

            validated = enforce_citation_contract(answer, citables, self.cfg.retrieval_mode)
            incumplio_citas = validated != answer
            # VIS.3: el aviso de vigencia se AÑADE aquí, después del contrato de citas y
            # sobre la evidencia realmente citable. No es una instrucción al modelo: una
            # instrucción se cumple casi siempre, y «casi siempre» no basta para decir si
            # una norma rige. Si el fallback ya sustituyó la respuesta, no hay nada citado
            # de lo que advertir.
            if not incumplio_citas:
                aviso = aviso_de_vigencia(citables)
                if aviso:
                    validated = f"{validated}\n\n{aviso}"
            return {
                "answer": validated,
                "fallback_used": incumplio_citas,
                "fallback_reason": "citation" if incumplio_citas else None,
                "sources": citables,
            }

        async def fallback_node(state: CoreGraphState) -> dict:
            # El fallback EMITE el mensaje, no deja answer=None: el endpoint lo manda por
            # SSE como una respuesta normal y el usuario ve una explicación en vez de nada.
            return {
                "answer": NO_CITATION_FALLBACK,
                "fallback_used": True,
                "fallback_reason": "quality_gate",
                "sources": [],
            }

        async def log_node(state: CoreGraphState) -> dict:
            return {}

        graph.add_node("detect_language", detect_language_node)
        graph.add_node("retrieve", retrieve_node)
        graph.add_node("merge", merge_node)
        graph.add_node("generate_answer", generate_answer_node)
        graph.add_node("fallback", fallback_node)
        graph.add_node("log", log_node)

        graph.set_entry_point("detect_language")
        graph.add_edge("detect_language", "retrieve")
        graph.add_edge("retrieve", "merge")
        graph.add_conditional_edges(
            "merge",
            quality_gate,
            {"generate_answer": "generate_answer", "fallback": "fallback"},
        )
        graph.add_edge("generate_answer", "log")
        graph.add_edge("log", END)
        graph.add_edge("fallback", END)

        return graph.compile()

    async def run(self, query: str, chatbot_id: str) -> dict:
        """Ejecuta el grafo y devuelve el estado final."""
        compiled = self.compile()
        initial: CoreGraphState = {
            "query": query,
            "chatbot_id": chatbot_id,
            "language": None,
            "retrieval_output": None,
            "merged_items": [],
            "answer": None,
            "quality_score": 0.0,
            "fallback_used": False,
            "translation_warning": False,
            "fallback_reason": None,
            "sources": [],
        }
        return await compiled.ainvoke(initial)

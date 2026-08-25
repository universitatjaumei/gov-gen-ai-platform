"""CoreGraph — orquestación común de grafos públicos.

Flujo: detect_language → retrieve → merge → quality_gate
         → generate_answer → log → END
         → fallback → END

No contiene lógica específica de dominio ni de retrieval_mode.
Todas las decisiones de dominio están encapsuladas en las estrategias inyectadas.

Deploy: edge
"""
from __future__ import annotations

import uuid
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
from server.app.modules.agents_hub.agent.public_graphs.core.query_rewriter import (
    necesita_reescritura,
    reescribir_consulta,
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
    # RAG.10: turnos previos, ya formateados como 'rol: texto'. Los manda el cliente: la API
    # es sin estado y no hay entidad conversación.
    history: list                  # list[str]
    # La consulta autónoma con la que se BUSCA, cuando la reescritura está encendida y sale
    # bien. None significa «se buscó con lo que escribió el usuario» — y hay que poder
    # distinguirlo, porque es lo que se lee en la traza y en el bypass de RAG.11.
    rewritten_query: str | None
    # RAG.11: ejecutar todo el pipeline y pararse ANTES de invocar al modelo.
    debug_bypass: bool
    # RAG.13: compone la MISMA instantánea pero **sin** detener el grafo. Es lo que permite
    # que un escenario guarde a la vez la respuesta y el contexto con el que se produjo,
    # sin recomponerlo desde fuera —recomponerlo daría un contexto parecido, no el mismo—.
    capture_context: bool
    bypass: dict | None            # lo que se envió (o se iba a enviar, si debug_bypass)
    retrieval_output: Any          # RetrievalOutput | None
    merged_items: list             # list[EvidenceItem]
    answer: str | None
    quality_score: float
    fallback_used: bool
    translation_warning: bool
    # VIS.5 — en qué lengua está la evidencia que se ha citado. Viaja junto al aviso porque el
    # texto que ve el usuario se redacta con ella: sin este dato, el chat sólo sabía «hay que
    # avisar» y acababa hablando de la lengua de la pregunta.
    context_source_language: str | None
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
        rewrite_llm: Any = None,
    ) -> None:
        self.retrieval_strategy = retrieval_strategy
        self.merge_strategy = merge_strategy
        self.template_strategy = template_strategy
        self.language_policy = language_policy
        self.cfg = cfg
        self.deps = deps
        self.llm = llm
        self.agentic_loop = agentic_loop
        # RAG.10: modelo pequeño y rápido para reescribir. Lo resuelve la GraphFactory, que
        # es quien ve la cascada; el nodo solo lo usa. None = no hay reescritura posible,
        # que es lo mismo que tenerla apagada.
        self.rewrite_llm = rewrite_llm

    def compile(self):
        """Compila y devuelve el grafo LangGraph listo para invocar."""
        graph = StateGraph(CoreGraphState)

        async def detect_language_node(state: CoreGraphState) -> dict:
            lang = self.language_policy.detect(state["query"])
            return {"language": lang}

        async def rewrite_query_node(state: CoreGraphState) -> dict:
            """Passthrough salvo que el flag esté encendido Y haya conversación previa."""
            historial = list(state.get("history") or [])
            habilitado = getattr(self.cfg, "query_rewriting_enabled", False)
            if self.rewrite_llm is None or not necesita_reescritura(habilitado, historial):
                return {"rewritten_query": None}

            reescrita = await reescribir_consulta(
                state["query"], historial, self.rewrite_llm
            )
            # Si el fallback devolvió la original, no hubo reescritura: dejarla en None
            # evita que la traza y el bypass muestren un paso que no ocurrió.
            return {"rewritten_query": reescrita if reescrita != state["query"] else None}

        async def retrieve_node(state: CoreGraphState) -> dict:
            output = await self.retrieval_strategy.retrieve(
                # Se BUSCA con la reescrita; a partir de aquí nadie más la ve.
                state.get("rewritten_query") or state["query"],
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
                # VIS.5 — **qué** lengua, no sólo que hay que avisar. El booleano llegaba hasta
                # el chat y allí el texto se construía con la lengua de la PREGUNTA, que es la
                # que quien pregunta ya conoce; lo que necesita saber es en qué lengua está la
                # norma a la que le lleva el enlace. El dato existía aquí y no viajaba.
                "context_source_language": context_source_language,
            }

        def quality_gate(
            state: CoreGraphState,
        ) -> Literal["generate_answer", "fallback"]:
            # RAG.11: en bypass el gate INFORMA pero no desvía. Si desviara, el caso que
            # más interesa depurar —puntuación baja— sería justo el que no enseña ningún
            # prompt, que es lo único que el bypass existe para enseñar.
            if state.get("debug_bypass"):
                return "generate_answer"
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
            instantanea = (
                self._instantanea_de_bypass(state, context, items)
                if state.get("debug_bypass") or state.get("capture_context")
                else None
            )
            if state.get("debug_bypass"):
                return {
                    "bypass": instantanea,
                    "answer": None,
                    "fallback_used": False,
                    "fallback_reason": None,
                    "sources": items,
                }

            if self.llm is None:
                return {
                    "answer": context,
                    "fallback_used": False,
                    "fallback_reason": None,
                    "sources": items,
                    "bypass": instantanea,
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

            # UX.4: el mensaje de «no lo sé» es del chatbot. Esta rama lo ignoraba y
            # devolvía el texto fijo en castellano; el `fallback_node` de abajo sí lo
            # respetaba, así que el mismo asistente contestaba dos cosas distintas según
            # por dónde se rindiera.
            sin_respuesta = (
                getattr(self.cfg, "no_answer_message", None) or NO_CITATION_FALLBACK
            )
            validated = enforce_citation_contract(
                answer,
                citables,
                self.cfg.retrieval_mode,
                no_answer_message=sin_respuesta,
            )
            # Se compara contra el mensaje de rendición, no contra la respuesta original:
            # el contrato ahora también AJUSTA —degrada al documento una cita cuyo ancla no
            # reconoce— y un ajuste no es rendirse. Compararlo con el original contaba esos
            # ajustes como fallback y, peor, se saltaba el aviso de vigencia de abajo.
            incumplio_citas = validated == sin_respuesta
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
                "bypass": instantanea,
            }

        async def fallback_node(state: CoreGraphState) -> dict:
            # El fallback EMITE el mensaje, no deja answer=None: el endpoint lo manda por
            # SSE como una respuesta normal y el usuario ve una explicación en vez de nada.
            #
            # UX.4: el mensaje es configurable por chatbot. «No lo sé» a secas deja al
            # ciudadano en el mismo sitio en el que estaba; decirle a quién preguntar es el
            # servicio. Y a quién preguntar depende del asistente —Infocampus atiende al
            # público, no al personal de Gerencia—, así que no puede ser una constante.
            return {
                "answer": getattr(self.cfg, "no_answer_message", None) or NO_CITATION_FALLBACK,
                "fallback_used": True,
                "fallback_reason": "quality_gate",
                "sources": [],
            }

        async def log_node(state: CoreGraphState) -> dict:
            return {}

        graph.add_node("detect_language", detect_language_node)
        graph.add_node("rewrite_query", rewrite_query_node)
        graph.add_node("retrieve", retrieve_node)
        graph.add_node("merge", merge_node)
        graph.add_node("generate_answer", generate_answer_node)
        graph.add_node("fallback", fallback_node)
        graph.add_node("log", log_node)

        graph.set_entry_point("detect_language")
        graph.add_edge("detect_language", "rewrite_query")
        graph.add_edge("rewrite_query", "retrieve")
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

    def _instantanea_de_bypass(
        self, state: CoreGraphState, context: str, items: list
    ) -> dict:
        """Lo que se iba a enviar al modelo, más el porqué (RAG.11).

        Se serializa aquí y no en el endpoint porque el endpoint no ve la evidencia ni el
        contexto construido: solo el estado final. Y va todo junto a propósito — el valor
        del bypass es leer el prompt y su configuración resuelta **en la misma pantalla**.
        """
        from dataclasses import asdict, is_dataclass

        salida = state.get("retrieval_output")
        debug: dict = {}
        if salida is not None and getattr(salida, "buckets", None):
            for bucket in salida.buckets:
                debug.update(getattr(bucket, "debug", None) or {})

        def _evidencia(item) -> dict:
            # Se aceptan los dos dialectos por el mismo motivo que `_serialize_source` en
            # el endpoint: RAG.2 unificó el contrato en `EvidenceItem`, pero las
            # estrategias de `services/retrieval/` siguen hablando `Source` por debajo.
            identificador = (
                getattr(item, "source_id", None) or getattr(item, "document_id", None)
            )
            return {
                "document_id": str(identificador) if identificador else None,
                "title": getattr(item, "title", None),
                "url": getattr(item, "source_url", None) or getattr(item, "url", None),
                "excerpt": (
                    getattr(item, "content", None) or getattr(item, "excerpt", None)
                ),
                "score": getattr(item, "score", None),
            }

        return {
            "system_prompt": context,
            "messages": [
                {"role": "system", "content": context},
                {"role": "user", "content": state["query"]},
            ],
            "packed_context": {
                "evidencias": [_evidencia(i) for i in items],
                "dropped_count": debug.get("dropped_count", 0),
                "total_tokens": debug.get("total_tokens"),
                "context_token_budget": debug.get("context_token_budget"),
            },
            "sources": [_evidencia(i) for i in items],
            "rewritten_query": state.get("rewritten_query"),
            "resolved_config": (
                {k: str(v) if isinstance(v, uuid.UUID) else v
                 for k, v in asdict(self.cfg).items()}
                if is_dataclass(self.cfg) else {}
            ),
            "quality_gate": {
                "score": state.get("quality_score", 0.0),
                "passed": state.get("quality_score", 0.0) >= self.cfg.quality_threshold,
            },
        }

    async def run(
        self,
        query: str,
        chatbot_id: str,
        history: list[str] | None = None,
        debug_bypass: bool = False,
        capture_context: bool = False,
    ) -> dict:
        """Ejecuta el grafo y devuelve el estado final."""
        compiled = self.compile()
        initial: CoreGraphState = {
            "query": query,
            "chatbot_id": chatbot_id,
            "language": None,
            "history": list(history or []),
            "rewritten_query": None,
            "debug_bypass": debug_bypass,
            "capture_context": capture_context,
            "bypass": None,
            "retrieval_output": None,
            "merged_items": [],
            "answer": None,
            "quality_score": 0.0,
            "fallback_used": False,
            "translation_warning": False,
            "context_source_language": None,
            "fallback_reason": None,
            "sources": [],
        }
        return await compiled.ainvoke(initial)

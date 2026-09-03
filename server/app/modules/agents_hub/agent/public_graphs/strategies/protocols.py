"""Protocolos de estrategias para grafos públicos.

RetrievalStrategy / MergeStrategy / TemplateStrategy / LanguagePolicy.
RetrievalStrategy delega al pipeline que corresponde a cfg.retrieval_mode
usando RetrievalPipelineFactory — sin que CoreGraph necesite conocer el modo.

Deploy: edge
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
    RetrievalResult,
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


@dataclass
class RetrievalOutput:
    """Salida de RetrievalStrategy.

    Contiene uno o varios buckets (RetrievalResult). Cada bucket corresponde
    a una fuente o estrategia de retrieval distinta; CoreGraph los fusiona
    antes de generar la respuesta.
    """

    buckets: list[RetrievalResult] = field(default_factory=list)


class RetrievalStrategy(Protocol):
    """Protocolo de estrategia de retrieval para grafos públicos."""

    async def retrieve(
        self,
        query: str,
        chatbot_id: str,
        cfg: "PublicGraphConfig",
        deps: "GraphDeps",
        language: str | None = None,
    ) -> RetrievalOutput: ...


class MergeStrategy(Protocol):
    """Fusiona los buckets de un RetrievalOutput en una lista plana de EvidenceItem."""

    def merge(self, output: RetrievalOutput) -> list[EvidenceItem]: ...


class TemplateStrategy(Protocol):
    """Construye el contexto de prompt que se entrega al LLM."""

    def build_prompt_context(
        self,
        items: list[EvidenceItem],
        language: str | None,
        query: str,
    ) -> str: ...


class LanguagePolicy(Protocol):
    """Política de idioma: detección + filtros post-merge + warning de traducción."""

    def detect(self, query: str) -> str | None: ...

    def needs_secondary_search(
        self,
        query_language: str | None,
        items: list[EvidenceItem],
    ) -> bool:
        """True si conviene lanzar una segunda búsqueda en el idioma del usuario."""
        ...

    def filter_items(
        self,
        query_language: str | None,
        items: list[EvidenceItem],
    ) -> list[EvidenceItem]:
        """Devuelve los items permitidos por esta política (filtrado o pass-through)."""
        ...

    def should_warn_translation(
        self,
        query_language: str | None,
        context_source_language: str | None,
    ) -> bool:
        """True si la diferencia de idioma entre consulta y contexto merece un aviso."""
        ...


def _no_se_puede_presentar_como_vigente(item: EvidenceItem) -> bool:
    """La señal de vigencia que VIS.3 ya pone en cada evidencia (VIS.4).

    Se lee de `metadata` y no se recalcula: el dato lo tiene la capa de recuperación, que es la
    que ve el documento, y duplicar aquí la regla —`estat_vigencia` distinto de `vigent`, o sin
    validar— las dejaría discrepando en cuanto una de las dos cambiara.

    Ausente cuenta como **vigente**: los pipelines que no marcan vigencia son los que no manejan
    corpus normativo, y ahí esta ordenación no debe alterar nada.
    """
    from server.app.modules.agents_hub.services.retrieval.vigencia import CLAVE_METADATO

    return bool((item.metadata or {}).get(CLAVE_METADATO, False))


class PreferLanguagePolicy:
    """prefer: prioriza el idioma del usuario **dentro de la misma vigencia** (VIS.4).

    Omite la doble búsqueda si ya hay evidencia en la lengua de la pregunta.
    """

    def detect(self, query: str) -> str | None:
        return None  # subclases con detector real anulan este método

    def needs_secondary_search(
        self,
        query_language: str | None,
        items: list[EvidenceItem],
    ) -> bool:
        if query_language is None:
            return False
        return not any(item.language == query_language for item in items)

    def filter_items(
        self,
        query_language: str | None,
        items: list[EvidenceItem],
    ) -> list[EvidenceItem]:
        """No filtra: **ordena**. Primero vigente, después lengua (VIS.4).

        `prefer` sigue pasando todos los items —quitar evidencia sería cambiar de política— pero
        el orden decide qué entra en el contexto cuando hay que recortar, y ahí estaba el
        problema: la preferencia de lengua no distinguía «la única versión está en otra lengua»
        de «la única versión de tu lengua es de otro curso», y son cosas muy distintas para quien
        pregunta. Citar lo que ya no rige en la lengua correcta es un error de fondo; citar lo
        vigente en otra lengua es una incomodidad, y encima se avisa.

        Así que la lengua opera **dentro** de la misma vigencia y no por encima de ella. Dentro
        de cada grupo se conserva el orden que traían —la relevancia—, porque esta regla añade un
        criterio por encima del que ya había, no lo sustituye: por eso `sorted` con clave, que es
        estable, y no una reordenación completa.
        """
        if query_language is None:
            return items

        def prioridad(item: EvidenceItem) -> tuple[int, int]:
            # 0 antes que 1: menor ordena primero.
            no_vigente = 1 if _no_se_puede_presentar_como_vigente(item) else 0
            otra_lengua = 0 if item.language == query_language else 1
            return (no_vigente, otra_lengua)

        return sorted(items, key=prioridad)

    def should_warn_translation(
        self,
        query_language: str | None,
        context_source_language: str | None,
    ) -> bool:
        return (
            query_language is not None
            and context_source_language is not None
            and query_language != context_source_language
        )


class FixedLanguagePolicy(PreferLanguagePolicy):
    """`fixed:<lang>`: responde siempre en esa lengua, pregunten como pregunten (LANG.1).

    El modo que no existía. Hoy el grafo detecta la lengua de la pregunta e instruye «Responde en
    {esa}», así que a quien escriba en catalán a un ayuntamiento castellanohablante se le contesta
    en catalán, y el organismo no tenía dónde decidir lo contrario.

    **Hereda de `PreferLanguagePolicy` y solo cambia `detect`**, y eso no es economía: es el
    comportamiento que se quiere. Todo lo que hay aguas abajo cuelga de `detect()` —el
    «Responde en {lang}» del prompt, el `language=` de la recuperación, la segunda búsqueda y el
    aviso de traducción—, así que devolver siempre la misma lengua **fija la respuesta y prefiere
    esa versión del corpus** sin tocar el CoreGraph. Y la preferencia sigue operando **dentro** de
    la vigencia, que es la regla de VIS.4: citar lo derogado en la lengua correcta sería peor que
    citar lo vigente en la otra.

    Sin `langdetect`: no se mira la consulta, que es el punto entero del modo. De paso se ahorra
    la detección en cada consulta.
    """

    def __init__(self, lang: str) -> None:
        self._lang = lang

    def detect(self, query: str) -> str | None:
        return self._lang


class StrictLanguagePolicy:
    """strict: filtra items al idioma del usuario; puede disparar fallback si quedan pocos."""

    def detect(self, query: str) -> str | None:
        return None

    def needs_secondary_search(
        self,
        query_language: str | None,
        items: list[EvidenceItem],
    ) -> bool:
        return False  # strict filtra y acepta fallback; no busca de nuevo

    def filter_items(
        self,
        query_language: str | None,
        items: list[EvidenceItem],
    ) -> list[EvidenceItem]:
        if query_language is None:
            return items
        return [item for item in items if item.language == query_language]

    def should_warn_translation(
        self,
        query_language: str | None,
        context_source_language: str | None,
    ) -> bool:
        return (
            query_language is not None
            and context_source_language is not None
            and query_language != context_source_language
        )


class NeutralLanguagePolicy:
    """none: sin filtros de idioma ni warnings de traducción."""

    def detect(self, query: str) -> str | None:
        return None

    def needs_secondary_search(
        self,
        query_language: str | None,
        items: list[EvidenceItem],
    ) -> bool:
        return False

    def filter_items(
        self,
        query_language: str | None,
        items: list[EvidenceItem],
    ) -> list[EvidenceItem]:
        return items

    def should_warn_translation(
        self,
        query_language: str | None,
        context_source_language: str | None,
    ) -> bool:
        return False


class PipelineRetrievalStrategy:
    """Estrategia por defecto: delega al pipeline indicado por cfg.retrieval_mode.

    Así CoreGraph puede cambiar de modo de retrieval sin modificar su lógica:
    sólo cambia cfg.retrieval_mode y esta estrategia enruta al pipeline correcto.
    """

    async def retrieve(
        self,
        query: str,
        chatbot_id: str,
        cfg: "PublicGraphConfig",
        deps: "GraphDeps",
        language: str | None = None,
    ) -> RetrievalOutput:
        pipeline = get_pipeline(cfg.retrieval_mode)
        result = await pipeline.run(query, chatbot_id, cfg, deps, language=language)
        return RetrievalOutput(buckets=[result])

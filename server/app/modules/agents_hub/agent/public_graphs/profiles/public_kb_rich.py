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


CITATION_RULES = """\
REGLAS DE CITA (obligatorias):
1. Cada afirmacion factual basada en los documentos debe ir seguida de una cita en formato
   markdown `[titulo del documento](url)`. La cita va al final de la frase citada.
2. Si una afirmacion combina varios documentos, cita todos: `[doc1](url1) [doc2](url2)`.
3. Si la pregunta no puede responderse con la informacion disponible, dilo explicitamente:
   "No tengo informacion suficiente en los documentos disponibles para responder a esta
   pregunta con citas verificables." NO inventes informacion ni cites documentos no
   recuperados.
4. NUNCA inventes URLs ni titulos. Usa SOLO los proporcionados en el contexto."""

_INSTRUCCION_TOOLS = (
    "Usa la tool `list_documents` para ver el indice y `read_document(id=...)` "
    "para cargar el texto completo de cada documento que necesites antes de responder."
)


class GenericAnswerTemplateStrategy:
    """Plantilla genérica y **única fuente del system prompt** (RAG.2).

    Absorbe `agent/prompts.py` (`build_system_prompt`, `format_sources_block`,
    `CITATION_RULES`), que se retiró con el grafo antiguo. Tener dos sitios donde se
    componía el system prompt era la razón por la que las reglas de cita y el bloque de
    fuentes podían divergir entre el grafo viejo y el CoreGraph.

    `base_system_prompt` es el del `HubChatbot`, que llega por la cascada del
    ConfigResolver.
    """

    def __init__(
        self,
        base_system_prompt: str | None = None,
        retrieval_mode: str = "RAG",
    ) -> None:
        self._base = (base_system_prompt or "").strip()
        self._retrieval_mode = retrieval_mode

    def _bloque_de_fuentes(self, items: list[EvidenceItem]) -> str:
        lineas: list[str] = []
        for item in items:
            lineas.append(f"## {item.title or item.source_id}")
            if item.source_url:
                lineas.append(f"_URL: {item.source_url}_")
            lineas.append("")
            lineas.append(item.content)
            lineas.append("")
        return "\n".join(lineas)

    def build_prompt_context(
        self,
        items: list[EvidenceItem],
        language: str | None,
        query: str,
    ) -> str:
        partes: list[str] = []
        if self._base:
            partes.extend([self._base, ""])
        if language:
            partes.extend([f"Responde en {language}.", ""])
        partes.append(CITATION_RULES.strip())

        if self._retrieval_mode == "MD_AGENT_SELECTOR":
            partes.extend(["", _INSTRUCCION_TOOLS])
        elif items:
            partes.extend(["", "DOCUMENTOS DISPONIBLES:", "", self._bloque_de_fuentes(items)])
        else:
            partes.extend(["", "No hay evidencias disponibles para responder esta consulta."])

        return "\n".join(partes).strip()


class DefaultLanguagePolicy(PreferLanguagePolicy):
    """Política de idioma por defecto para PUBLIC_KB_RICH: prefer con langdetect."""

    def detect(self, query: str) -> str | None:
        return _detect_language(query)

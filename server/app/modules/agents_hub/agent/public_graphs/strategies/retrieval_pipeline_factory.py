"""RetrievalPipelineFactory — devuelve el pipeline correcto según retrieval_mode.

Deploy: edge
"""
from __future__ import annotations

from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_pipeline_protocol import (
    RetrievalPipeline,
)

_VALID_MODES = ("RAG", "MD_LONG_CONTEXT", "MD_AGENT_SELECTOR")


def get_pipeline(mode: str) -> RetrievalPipeline:
    """Devuelve una instancia del pipeline correspondiente a *mode*.

    Raises:
        ValueError: si *mode* no es uno de los modos soportados.
    """
    if mode == "RAG":
        from server.app.modules.agents_hub.agent.public_graphs.strategies.rag_vector_pipeline import (
            RagVectorPipeline,
        )
        return RagVectorPipeline()

    if mode == "MD_LONG_CONTEXT":
        from server.app.modules.agents_hub.agent.public_graphs.strategies.md_long_context_pipeline import (
            MdLongContextPipeline,
        )
        return MdLongContextPipeline()

    if mode == "MD_AGENT_SELECTOR":
        from server.app.modules.agents_hub.agent.public_graphs.strategies.md_agent_selector_pipeline import (
            MdAgentSelectorPipeline,
        )
        return MdAgentSelectorPipeline()

    raise ValueError(
        f"Unknown retrieval mode: {mode!r}. Valid modes: {list(_VALID_MODES)}"
    )

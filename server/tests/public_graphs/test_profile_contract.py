"""Tests de contrato de perfiles — 9B.14.

Todo perfil registrado en GraphProfileRegistry **y configurado** debe:
- producir un CoreGraph con strategies no nulas
- compilar el grafo sin errores
- poder ejecutarse (smoke) con cada retrieval_mode

Los perfiles de `PERFILES_SIN_CONFIGURAR` quedan fuera a propósito: no tienen implementación
y su factoría lanza `NotImplementedError` en vez de construir un grafo que recuperaría vacío
en silencio. Que aquí se comprobara lo contrario es lo que mantuvo vivo el hallazgo I5 de la
auditoría — el contrato certificaba como «compila» un perfil que no servía para nada. Lo que
se les exige está en `tests/modules/agents_hub/unit/test_stub_profiles_fail_loudly.py`.

La importación de graph_factory dispara el registro de los tres perfiles en
_default_registry, por lo que list_profiles() ya está poblado al evaluar
los decoradores @parametrize.
"""
import uuid
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Trigger profile registration in _default_registry
from server.app.modules.agents_hub.agent.public_graphs.core.graph_factory import (
    PERFILES_SIN_CONFIGURAR,
)

from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
    PublicGraphConfig,
)
from server.app.modules.agents_hub.agent.public_graphs.core.core_graph import CoreGraph
from server.app.modules.agents_hub.agent.public_graphs.registry import _default_registry
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
    RetrievalResult,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_pipeline_protocol import (
    GraphDeps,
)

_RETRIEVAL_MODES = ("RAG", "MD_LONG_CONTEXT", "MD_AGENT_SELECTOR")

# Paths para parchear get_pipeline en los tres lugares donde se usa
_PATCH_PROTO = (
    "server.app.modules.agents_hub.agent.public_graphs.strategies.protocols.get_pipeline"
)
_PATCH_AGGR = (
    "server.app.modules.agents_hub.agent.public_graphs.profiles.public_portal_aggregator.get_pipeline"
)


def _make_cfg(profile: str, mode: str) -> PublicGraphConfig:
    return PublicGraphConfig(
        profile=profile,
        retrieval_mode=mode,
        language_mode="prefer",
        quality_threshold=0.6,
        min_retrieval_results=1,
        min_retrieval_score=0.25,
        reranker_enabled=False,
        answer_template="generic",
    )


def _smoke_pipeline(mode: str) -> MagicMock:
    item = EvidenceItem(source_id="doc-smoke", content="contenido smoke", score=0.9)
    result = RetrievalResult(items=[item, item], debug={"pipeline_mode": mode})
    pipeline = MagicMock()
    pipeline.run = AsyncMock(return_value=result)
    return pipeline


_PERFILES_CONFIGURADOS = [
    nombre
    for nombre in _default_registry.list_profiles()
    if nombre not in PERFILES_SIN_CONFIGURAR
]


def test_should_keep_at_least_one_profile_under_contract():
    """Excluir perfiles no puede dejar el contrato vacío.

    Sin esto, meter todos los perfiles en `PERFILES_SIN_CONFIGURAR` haría que toda la clase de
    abajo pasara sin ejecutar una sola comprobación — verde por ausencia de casos.
    """
    assert _PERFILES_CONFIGURADOS, (
        "Ningún perfil queda bajo el contrato: revisa PERFILES_SIN_CONFIGURAR en graph_factory"
    )


@pytest.mark.parametrize("profile_name", _PERFILES_CONFIGURADOS)
class TestProfileContract:

    def test_profile_compiles_with_non_null_strategies(self, profile_name):
        """Todo perfil debe producir un CoreGraph compilable con strategies no nulas."""
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())
        cfg = _make_cfg(profile_name, "RAG")

        profile_factory = _default_registry.get_profile(profile_name)
        graph = profile_factory(cfg, deps)

        assert isinstance(graph, CoreGraph), "La factoría debe devolver una instancia de CoreGraph"
        assert graph.retrieval_strategy is not None
        assert graph.merge_strategy is not None
        assert graph.template_strategy is not None
        assert graph.language_policy is not None
        assert graph.compile() is not None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", _RETRIEVAL_MODES)
    async def test_profile_smoke_run_with_retrieval_mode(self, profile_name, mode):
        """Todo perfil puede ejecutarse (smoke) con cualquier retrieval_mode sin lanzar excepciones."""
        deps = GraphDeps(session=AsyncMock(), embedder=AsyncMock())
        cfg = _make_cfg(profile_name, mode)

        profile_factory = _default_registry.get_profile(profile_name)
        graph = profile_factory(cfg, deps)

        mock_pipeline = _smoke_pipeline(mode)

        with ExitStack() as stack:
            stack.enter_context(patch(_PATCH_PROTO, return_value=mock_pipeline))
            stack.enter_context(patch(_PATCH_AGGR, return_value=mock_pipeline))
            result = await graph.run("¿consulta de prueba?", str(uuid.uuid4()))

        assert "answer" in result, "El estado final debe contener 'answer'"
        assert "fallback_used" in result, "El estado final debe contener 'fallback_used'"
        assert "translation_warning" in result, "El estado final debe contener 'translation_warning'"

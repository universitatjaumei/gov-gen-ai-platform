"""RES.2 — Si la puerta rechaza, se reformula y se busca otra vez. Una sola vez.

El defecto que arregla no es un flag apagado, y por eso costó verlo:
`query_rewriting_enabled` está en `t` en los tres chatbots, pero el paso exige **dos turnos
previos** —se diseñó para resolver referencias de seguimiento («i si és a l'estranger?»)—, así que
en una primera pregunta no se ejecuta nunca. Medido: `rewritten_query` fue `None` en las 14
ejecuciones de la batería de Gerencia.

El efecto es de vocabulario. Una pregunta redactada como **intención** («quiero tramitar una compra
de un equipo de 6.500 euros») se busca tal cual contra un corpus redactado como **norma**
(«expedients de contractes menors»), y no comparten ni una palabra clave: ni el vector se parece ni
la rama léxica tiene de dónde agarrarse. Reformulada a mano al vocabulario de la norma, esa consulta
pasa de **0,126 a 0,640**.

La prueba interna de que es vocabulario y no corpus: `REAL-02` («quin és el límit d'un contracte
menor?») **sí se contesta**, porque usa las palabras de la norma.

Diseño que estos tests fijan:

- **Sólo se paga cuando falla.** Si la primera pasada supera el umbral, no hay segunda llamada.
- **Una y sólo una.** Sin la guarda esto es un bucle infinito con coste por vuelta.
- **La reformulación no llega a la generación**, igual que la reescritura de RAG.10: el usuario no
  la escribió, y responder a una pregunta reformulada suena a estar contestando a otra cosa.
- **El chat nunca falla por esto**: excepción o tardanza ⇒ se sigue con lo que ya había.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
    PublicGraphConfig,
)
from server.app.modules.agents_hub.agent.public_graphs.core.core_graph import CoreGraph
from server.app.modules.agents_hub.agent.public_graphs.strategies.protocols import RetrievalOutput
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_contract import (
    EvidenceItem,
)
from server.app.modules.agents_hub.agent.public_graphs.strategies.retrieval_pipeline_protocol import (
    GraphDeps,
)

_UMBRAL = 0.5


def _cfg(**extra) -> PublicGraphConfig:
    base = dict(
        profile="PUBLIC_KB_RICH",
        retrieval_mode="RAG",
        language_mode="prefer",
        quality_threshold=_UMBRAL,
        min_retrieval_results=1,
        min_retrieval_score=0.0,
        reranker_enabled=False,
        answer_template="generic",
    )
    base.update(extra)
    return PublicGraphConfig(**base)


def _item(score: float) -> EvidenceItem:
    return EvidenceItem(
        source_id=str(uuid.uuid4()), content="texto", title="Norma", score=score
    )


class _Reformulador:
    """LLM de reformulación con cuenta de llamadas: el coste es parte del contrato."""

    def __init__(self, devuelve="contracte menor de subministrament", fallo=None):
        self.llamadas = 0
        self._devuelve = devuelve
        self._fallo = fallo

    async def ainvoke(self, *_args, **_kwargs):
        self.llamadas += 1
        if self._fallo is not None:
            raise self._fallo
        return MagicMock(content=self._devuelve)


def _grafo(cfg, tandas, reformulador=None):
    """`tandas` es la lista de resultados que devuelve el merge, en orden de pasada."""
    pendientes = list(tandas)
    consultas_buscadas = []

    retrieval = MagicMock()

    async def _retrieve(consulta, chatbot_id, config, deps):
        consultas_buscadas.append(consulta)
        return RetrievalOutput(buckets=[])

    retrieval.retrieve = AsyncMock(side_effect=_retrieve)

    merge = MagicMock()
    merge.merge = MagicMock(side_effect=lambda _salida: pendientes.pop(0) if pendientes else [])

    contextos = []
    template = MagicMock()

    def _contexto(items, language, query):
        contextos.append(query)
        return "contexto"

    template.build_prompt_context = MagicMock(side_effect=_contexto)

    language = MagicMock()
    language.detect = MagicMock(return_value="es")
    language.filter_items = MagicMock(side_effect=lambda lang, elementos: elementos)
    language.should_warn_translation = MagicMock(return_value=False)

    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=MagicMock(content="respuesta"))

    grafo = CoreGraph(
        retrieval_strategy=retrieval,
        merge_strategy=merge,
        template_strategy=template,
        language_policy=language,
        cfg=cfg,
        deps=GraphDeps(session=AsyncMock(), embedder=AsyncMock(), llm=llm),
        llm=llm,
    )
    if reformulador is not None:
        grafo.rewrite_llm = reformulador
    return grafo, consultas_buscadas, contextos


async def _ejecutar(grafo, *, consulta="quiero tramitar una compra de 6.500 euros",
                    historial=None, bypass=False) -> dict:
    return await grafo.compile().ainvoke({
        "query": consulta,
        "chatbot_id": str(uuid.uuid4()),
        "language": None,
        "history": list(historial or []),
        "rewritten_query": None,
        "debug_bypass": bypass,
        "capture_context": False,
        "bypass": None,
        "retrieval_output": None,
        "merged_items": [],
        "answer": None,
        "quality_score": 0.0,
        "quality_source": None,
        "fallback_used": False,
        "translation_warning": False,
        "fallback_reason": None,
        "sources": [],
    })


@pytest.mark.asyncio
class TestSoloSePagaCuandoFalla:

    async def test_should_not_reformulate_when_the_first_pass_passes(self):
        """Es el argumento del diseño entero: normalizar siempre costaría una llamada en el
        camino crítico de TODAS las consultas; así se paga en el 28% de Normativa y el 71% de
        Gerencia."""
        reformulador = _Reformulador()
        grafo, buscadas, _ = _grafo(_cfg(), [[_item(0.8)]], reformulador)

        await _ejecutar(grafo)

        assert reformulador.llamadas == 0
        assert len(buscadas) == 1

    async def test_should_reformulate_when_the_first_pass_fails(self):
        reformulador = _Reformulador(devuelve="contracte menor de subministrament")
        grafo, buscadas, _ = _grafo(_cfg(), [[_item(0.12)], [_item(0.64)]], reformulador)

        estado = await _ejecutar(grafo)

        assert reformulador.llamadas == 1
        assert len(buscadas) == 2
        assert buscadas[1] == "contracte menor de subministrament"
        assert estado["quality_score"] == pytest.approx(0.64)


@pytest.mark.asyncio
class TestUnaYSoloUna:

    async def test_should_reformulate_once_and_only_once(self):
        """Sin la guarda esto es un bucle infinito con coste por vuelta."""
        reformulador = _Reformulador()
        grafo, buscadas, _ = _grafo(
            _cfg(), [[_item(0.10)], [_item(0.11)], [_item(0.12)]], reformulador
        )

        estado = await _ejecutar(grafo)

        assert reformulador.llamadas == 1
        assert len(buscadas) == 2
        assert estado["fallback_used"] is True
        assert estado["fallback_reason"] == "quality_gate"


@pytest.mark.asyncio
class TestLaReformulacionNoLlegaALaGeneracion:

    async def test_should_never_send_the_reformulation_to_the_generator(self):
        """El usuario no la escribió. Responder a una pregunta reformulada suena a estar
        contestando a otra cosa — es la misma regla que RAG.10 fijó para la reescritura."""
        reformulador = _Reformulador(devuelve="contracte menor de subministrament")
        grafo, _, contextos = _grafo(_cfg(), [[_item(0.12)], [_item(0.64)]], reformulador)

        await _ejecutar(grafo, consulta="quiero comprar un equipo de 6.500 euros")

        assert contextos, "no se llegó a construir el contexto"
        assert all("contracte menor" not in c for c in contextos)
        assert contextos[-1] == "quiero comprar un equipo de 6.500 euros"


@pytest.mark.asyncio
class TestElChatNoSeCaePorEsto:

    async def test_should_not_break_the_chat_when_the_reformulation_fails(self):
        reformulador = _Reformulador(fallo=RuntimeError("el proveedor dice que no"))
        grafo, buscadas, _ = _grafo(_cfg(), [[_item(0.12)]], reformulador)

        estado = await _ejecutar(grafo)

        assert estado["fallback_used"] is True
        assert estado["fallback_reason"] == "quality_gate"
        assert len(buscadas) == 1, (
            "si la reformulación no sale, no se repite la búsqueda con lo mismo: seria pagar "
            "una consulta al corpus para obtener el resultado que ya se tiene"
        )

    async def test_should_not_reformulate_without_a_rewrite_model(self):
        grafo, buscadas, _ = _grafo(_cfg(), [[_item(0.12)]], reformulador=None)

        estado = await _ejecutar(grafo)

        assert estado["fallback_used"] is True
        assert len(buscadas) == 1


@pytest.mark.asyncio
class TestElBypassDeDepuracionSigueMandando:
    """RAG.11: en bypass el gate informa pero no desvía. Si la reformulación se disparara, el
    caso que más interesa depurar —puntuación baja— dejaría de enseñar el prompt que se envió."""

    async def test_should_not_reformulate_in_debug_bypass(self):
        reformulador = _Reformulador()
        grafo, buscadas, _ = _grafo(_cfg(), [[_item(0.12)], [_item(0.64)]], reformulador)

        await _ejecutar(grafo, bypass=True)

        assert reformulador.llamadas == 0
        assert len(buscadas) == 1


@pytest.mark.asyncio
class TestSeSabeQueLaRespuestaVieneDeUnaReformulacion:
    """Una respuesta rescatada reformulando no se revisa igual que una directa, así que el hecho
    tiene que estar en el contrato. Cómo se le cuenta al usuario es decisión de producto."""

    async def test_should_expose_that_the_answer_came_from_a_reformulation(self):
        reformulador = _Reformulador(devuelve="contracte menor de subministrament")
        grafo, _, _ = _grafo(_cfg(), [[_item(0.12)], [_item(0.64)]], reformulador)

        estado = await _ejecutar(grafo)

        assert estado.get("reformulada") is True
        assert estado.get("reformulated_query") == "contracte menor de subministrament"

    async def test_should_not_claim_a_reformulation_that_did_not_happen(self):
        reformulador = _Reformulador()
        grafo, _, _ = _grafo(_cfg(), [[_item(0.8)]], reformulador)

        estado = await _ejecutar(grafo)

        assert estado.get("reformulada") is False
        assert estado.get("reformulated_query") is None


class TestElHechoLlegaAQuienRevisa:
    """Sin esto, la segunda búsqueda es invisible desde las dos herramientas con las que se mira
    si el asistente responde bien — que es exactamente el error que VIS.5 tuvo que corregir con
    el aviso de lengua."""

    def test_should_record_the_reformulation_in_the_run(self):
        from server.app.modules.agents_hub.database.operational_models import HubTestRun

        assert "reformulada" in HubTestRun.__table__.columns
        assert "reformulated_query" in HubTestRun.__table__.columns

    def test_should_expose_the_reformulation_in_the_contract(self):
        from server.app.routers.hub_test_scenarios_router import RunRead

        assert "reformulada" in RunRead.model_fields
        assert "reformulated_query" in RunRead.model_fields

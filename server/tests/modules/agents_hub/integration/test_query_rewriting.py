"""Tests RAG.10 — reescritura de la consulta con el historial, antes del retrieve.

El problema que resuelve: «¿y si es a l'estranger?» no contiene ninguna de las palabras por
las que se encontraría la norma. El vector de una consulta así apunta a cualquier sitio, y
la rama léxica no tiene de dónde agarrarse. El turno anterior sí sabe de qué se hablaba.

Dos invariantes que estos tests fijan, y son los que hacen que la función sea segura:

- **El chat NUNCA falla por la reescritura.** Excepción, timeout o respuesta anómala ⇒ se
  usa el último mensaje tal cual. Es una optimización de recuperación, no un paso crítico.
- **La consulta reescrita se usa SOLO para recuperar.** La generación recibe el mensaje
  original, porque el usuario no escribió la reescritura y la respuesta no puede sonar
  como si contestara a otra pregunta.
"""
from __future__ import annotations

import asyncio
import uuid

import pytest

HISTORIAL = (
    "usuario: quant cobro de dieta per anar a Madrid?",
    "asistente: L'import de la dieta per dia complet es de 53,34 euros.",
)
SEGUIMIENTO = "i si es a l'estranger?"
REESCRITA = "import de la dieta per desplacament a l'estranger"


class _LLM:
    """Doble del LLM de reescritura: registra lo que se le pide y devuelve lo pactado."""

    def __init__(self, respuesta: str = REESCRITA) -> None:
        self.respuesta = respuesta
        self.prompts: list[str] = []

    async def ainvoke(self, mensajes, **kwargs):
        self.prompts.append(str(mensajes))

        class _R:
            content = self.respuesta

        return _R()


class _LLMQueRevienta:
    async def ainvoke(self, mensajes, **kwargs):
        raise RuntimeError("el proveedor devuelve 500")


class _LLMLento:
    async def ainvoke(self, mensajes, **kwargs):
        await asyncio.sleep(5)

        class _R:
            content = "llego tarde"

        return _R()


class TestCascadaDeConfiguracion:

    @pytest.mark.asyncio
    async def test_should_default_to_disabled_on_the_platform(self, db_session):
        """Apagado por defecto: cuesta una llamada al LLM por turno y no se ha medido."""
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            get_effective_public_graph_config,
        )
        from server.tests.modules.agents_hub.integration.test_embedding_resolution import (
            _organizacion_y_chatbot,
        )

        _, chatbot = await _organizacion_y_chatbot(db_session)
        await db_session.commit()

        cfg = await get_effective_public_graph_config(chatbot.id, db_session)

        assert cfg.query_rewriting_enabled is False
        assert cfg.rewrite_llm_config_id is None

    @pytest.mark.asyncio
    async def test_should_let_the_chatbot_override_the_organizacion(self, db_session):
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            get_effective_public_graph_config,
        )
        from server.tests.modules.agents_hub.integration.test_embedding_resolution import (
            _organizacion_y_chatbot,
        )

        org, chatbot = await _organizacion_y_chatbot(db_session)
        org.default_query_rewriting_enabled = True
        chatbot.query_rewriting_enabled = False
        await db_session.commit()

        cfg = await get_effective_public_graph_config(chatbot.id, db_session)

        assert cfg.query_rewriting_enabled is False

    @pytest.mark.asyncio
    async def test_should_inherit_the_organizacion_rewrite_llm(self, db_session):
        """El LLM de reescritura se configura en la organización: es otro modelo, más
        pequeño y más rápido, y no tiene sentido repetirlo en cada chatbot."""
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            get_effective_public_graph_config,
        )
        from server.app.modules.agents_hub.database.config_models import (
            HubLLMConfig,
            HubProvider,
        )
        from server.tests.modules.agents_hub.integration.test_embedding_resolution import (
            _organizacion_y_chatbot,
        )

        org, chatbot = await _organizacion_y_chatbot(db_session)
        await db_session.merge(
            HubProvider(id="google", name="Google", provider_type="google_genai")
        )
        rapido = HubLLMConfig(provider="google", model_name="gemini-flash-lite")
        db_session.add(rapido)
        await db_session.flush()
        org.default_query_rewriting_enabled = True
        org.rewrite_llm_config_id = rapido.id
        await db_session.commit()

        cfg = await get_effective_public_graph_config(chatbot.id, db_session)

        assert cfg.query_rewriting_enabled is True
        assert cfg.rewrite_llm_config_id == rapido.id


class TestReescritura:

    @pytest.mark.asyncio
    async def test_should_rewrite_followup_query_using_history(self):
        from server.app.modules.agents_hub.agent.public_graphs.core.query_rewriter import (
            reescribir_consulta,
        )

        llm = _LLM()
        resultado = await reescribir_consulta(SEGUIMIENTO, list(HISTORIAL), llm)

        assert resultado == REESCRITA
        assert "Madrid" in llm.prompts[0], "el historial tiene que llegar al modelo"
        assert SEGUIMIENTO in llm.prompts[0]

    @pytest.mark.asyncio
    async def test_should_skip_rewriting_on_first_turn(self):
        """Sin turnos previos no hay nada que resolver, y llamar al LLM sería pagar por nada."""
        from server.app.modules.agents_hub.agent.public_graphs.core.query_rewriter import (
            necesita_reescritura,
        )

        assert necesita_reescritura(True, []) is False
        assert necesita_reescritura(True, ["usuario: hola"]) is False
        assert necesita_reescritura(True, list(HISTORIAL)) is True

    def test_should_skip_rewriting_when_disabled(self):
        from server.app.modules.agents_hub.agent.public_graphs.core.query_rewriter import (
            necesita_reescritura,
        )

        assert necesita_reescritura(False, list(HISTORIAL)) is False

    @pytest.mark.asyncio
    async def test_should_fallback_to_last_message_on_llm_error(self):
        from server.app.modules.agents_hub.agent.public_graphs.core.query_rewriter import (
            reescribir_consulta,
        )

        assert await reescribir_consulta(SEGUIMIENTO, list(HISTORIAL), _LLMQueRevienta()) == (
            SEGUIMIENTO
        )

    @pytest.mark.asyncio
    async def test_should_fallback_to_last_message_on_timeout(self):
        from server.app.modules.agents_hub.agent.public_graphs.core.query_rewriter import (
            reescribir_consulta,
        )

        resultado = await reescribir_consulta(
            SEGUIMIENTO, list(HISTORIAL), _LLMLento(), timeout=0.05
        )

        assert resultado == SEGUIMIENTO

    @pytest.mark.asyncio
    async def test_should_fallback_on_an_empty_or_anomalous_answer(self):
        """Un modelo pequeño a veces devuelve vacío, o una parrafada en vez de una consulta.
        Buscar con eso es peor que buscar con el mensaje original."""
        from server.app.modules.agents_hub.agent.public_graphs.core.query_rewriter import (
            reescribir_consulta,
        )

        for anomala in ("", "   ", "x" * 1000):
            assert await reescribir_consulta(
                SEGUIMIENTO, list(HISTORIAL), _LLM(anomala)
            ) == SEGUIMIENTO

    @pytest.mark.asyncio
    async def test_should_only_send_the_last_messages(self):
        """Una conversación larga no puede convertir un paso barato en uno caro."""
        from server.app.modules.agents_hub.agent.public_graphs.core.query_rewriter import (
            MAX_MENSAJES,
            reescribir_consulta,
        )

        largo = [f"usuario: mensaje {i}" for i in range(40)]
        llm = _LLM()
        await reescribir_consulta(SEGUIMIENTO, largo, llm)

        assert "mensaje 39" in llm.prompts[0]
        assert f"mensaje {40 - MAX_MENSAJES - 1}" not in llm.prompts[0]


class TestNodoEnElGrafo:

    def _grafo(self, *, enabled: bool, llm_reescritura=None):
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            PublicGraphConfig,
        )
        from server.app.modules.agents_hub.agent.public_graphs.core.core_graph import (
            CoreGraph,
        )
        from server.app.modules.agents_hub.agent.public_graphs.strategies.protocols import (
            RetrievalOutput,
        )

        recuperadas: list[str] = []

        class _Retrieval:
            async def retrieve(self, query, chatbot_id, cfg, deps):
                recuperadas.append(query)
                return RetrievalOutput()

        class _Merge:
            def merge(self, output):
                return []

        class _Template:
            def build_prompt_context(self, items, language, query):
                return f"CONTEXTO para: {query}"

        class _Language:
            def detect(self, query):
                return "ca"

            def filter_items(self, language, items):
                return items

            def should_warn_translation(self, a, b):
                return False

        cfg = PublicGraphConfig(
            profile="PUBLIC_KB_RICH", retrieval_mode="RAG", language_mode="prefer",
            quality_threshold=0.0, min_retrieval_results=0, min_retrieval_score=0.0,
            reranker_enabled=False, answer_template="generic",
            query_rewriting_enabled=enabled,
        )
        grafo = CoreGraph(
            retrieval_strategy=_Retrieval(), merge_strategy=_Merge(),
            template_strategy=_Template(), language_policy=_Language(),
            cfg=cfg, deps=object(), llm=None, rewrite_llm=llm_reescritura,
        )
        return grafo, recuperadas

    @pytest.mark.asyncio
    async def test_should_use_rewritten_query_only_for_retrieval(self):
        """Se recupera con la reescrita; se responde a la que el usuario escribió."""
        grafo, recuperadas = self._grafo(enabled=True, llm_reescritura=_LLM())

        estado = await grafo.run(
            SEGUIMIENTO, str(uuid.uuid4()), history=list(HISTORIAL)
        )

        assert recuperadas == [REESCRITA]
        assert estado["query"] == SEGUIMIENTO
        assert SEGUIMIENTO in estado["answer"], (
            "la generacion recibe el mensaje original, no la reescritura"
        )

    @pytest.mark.asyncio
    async def test_should_record_rewritten_query_in_graph_state(self):
        """Queda en el estado: es lo que hace la reescritura visible en las trazas y en el
        bypass de RAG.11. Un paso que cambia lo que se busca y no se puede inspeccionar es
        un paso que nadie va a poder depurar."""
        grafo, _ = self._grafo(enabled=True, llm_reescritura=_LLM())

        estado = await grafo.run(SEGUIMIENTO, str(uuid.uuid4()), history=list(HISTORIAL))

        assert estado["rewritten_query"] == REESCRITA

    @pytest.mark.asyncio
    async def test_should_be_a_passthrough_when_disabled(self):
        grafo, recuperadas = self._grafo(enabled=False, llm_reescritura=_LLM())

        estado = await grafo.run(SEGUIMIENTO, str(uuid.uuid4()), history=list(HISTORIAL))

        assert recuperadas == [SEGUIMIENTO]
        assert estado["rewritten_query"] is None

    @pytest.mark.asyncio
    async def test_should_not_break_the_chat_when_the_rewriter_fails(self):
        grafo, recuperadas = self._grafo(
            enabled=True, llm_reescritura=_LLMQueRevienta()
        )

        estado = await grafo.run(SEGUIMIENTO, str(uuid.uuid4()), history=list(HISTORIAL))

        assert recuperadas == [SEGUIMIENTO]
        assert estado["answer"] is not None


class TestHistorialEnLaPeticion:

    def test_should_accept_history_in_the_chat_request(self):
        """El historial llega del cliente: la API es sin estado y no hay entidad conversación.

        RAG.10 daba el historial por supuesto y no existía en ninguna parte — ni en
        `ChatRequest` ni en el estado del grafo.
        """
        from server.app.api.v1.hub_chat import ChatRequest

        peticion = ChatRequest(
            message=SEGUIMIENTO,
            history=[
                {"role": "user", "content": "quant cobro de dieta?"},
                {"role": "assistant", "content": "53,34 euros."},
            ],
        )

        assert len(peticion.history) == 2
        assert peticion.history[0].role == "user"

    def test_should_default_history_to_empty(self):
        from server.app.api.v1.hub_chat import ChatRequest

        assert ChatRequest(message="hola").history == []


class TestDoradoConversacional:
    """El criterio de done de RAG.10, y hubo que construir su instrumento.

    El dorado de RAG.1 declaraba el campo `history` y **no tenía ni una consulta que lo
    usara**: el subconjunto 'conversacional' que este prompt manda medir no existía. Vive en
    un fichero aparte, no dentro de `golden_dietes.json`, y eso es deliberado: mezclarlo
    movería la media contra la que se compararon RAG.3–RAG.9 y dejaría sin sentido la línea
    base del gate.
    """

    def test_el_subconjunto_conversacional_existe_y_es_anaforico(self):
        from pathlib import Path

        from server.app.modules.agents_hub.evaluation.golden_dataset import (
            load_golden_dataset,
        )

        dataset = load_golden_dataset(
            Path(__file__).parent.parent / "evaluation" / "golden_conversacional.json"
        )

        assert len(dataset.queries) >= 10
        for consulta in dataset.queries:
            assert consulta.history, f"{consulta.query!r} no tiene historial"
            assert len(consulta.history) >= 2
            # Anafórica de verdad: la consulta suelta no puede contener el término por el
            # que se encontraría el documento. Si lo contiene, la reescritura no mide nada.
            assert len(consulta.query) < 45, consulta.query

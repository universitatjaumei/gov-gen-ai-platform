"""Tests VIS.2 — Niveles 0/1/2: el router ve temas, no documentos.

Nivel 0: el índice de submaterias entra en el system prompt (2.307 tokens medidos en el
informe, frente a los ~72k del catálogo de fichas, que no cabe).
Nivel 1: el modelo selecciona 1-3 submaterias con `list_documents(submateries=[...])` y
recibe fichas, no contenido. Si nada encaja, retroceso escalonado.
Nivel 2: `read_document` sobre 1-3 documentos; la inyección es un SUBCONJUNTO y, cuando no
cabe, se recorta en vez de reventar.

Los tests de índice van contra BD real: el escalonado se decide con los mismos filtros SQL
de VIS.1 (`&&` de arrays, JOIN), y un fake no probaría el retroceso.
"""
from __future__ import annotations

import uuid

import pytest

from server.tests.modules.agents_hub.integration.test_metadata_filter import (
    _documento,
)


# ───────────────────────── Helpers ─────────────────────────


async def _organizacion_con_chatbot(session, **chatbot_kwargs):
    """Organización + chatbot reales: la cascada del ConfigResolver los consulta."""
    from server.app.modules.agents_hub.database.config_models import (
        HubChatbot,
        HubLLMConfig,
        HubOrganizacion,
        HubProvider,
    )

    await session.merge(HubProvider(id="google", name="Google", provider_type="google_genai"))
    llm = HubLLMConfig(provider="google", model_name="gemini-flash")
    session.add(llm)
    org_kwargs = chatbot_kwargs.pop("_organizacion", {})
    org = HubOrganizacion(name="UJI", partner_id="partner_dev", **org_kwargs)
    session.add(org)
    await session.flush()

    chatbot = HubChatbot(
        organizacion_id=org.id,
        llm_config_id=llm.id,
        name="Assistent normatiu",
        system_prompt="Eres un asistente normativo.",
        sources=[],
        **chatbot_kwargs,
    )
    session.add(chatbot)
    await session.flush()
    return org, chatbot


class _FakeVocabularySource:
    def __init__(self, terms: list) -> None:
        self._terms = terms

    async def list_vocabulary(self, axis: str, organizacion_id):
        return [t for t in self._terms if t.axis == axis]


def _vocabulario(n_submateries: int):
    """Un vocabulario del tamaño real medido: 5 ámbitos y N submaterias."""
    from server.app.modules.agents_hub.services.vocabulary_service import VocabularyTermDTO

    ambits = [
        VocabularyTermDTO(axis="ambit", codi=f"ambit-{i}", nom_primari=f"Àmbit {i}", ordre=i)
        for i in range(5)
    ]
    submateries = [
        VocabularyTermDTO(
            axis="submateria",
            codi=f"submateria-{i}",
            nom_primari=f"Submatèria número {i}",
            parent_codi=f"ambit-{i % 5}",
            descripcio_router=(
                "Descripció orientativa per al router sobre què regula aquesta submatèria."
            ),
            ordre=i,
        )
        for i in range(n_submateries)
    ]
    return _FakeVocabularySource([*ambits, *submateries])


class _RespuestaLLM:
    def __init__(self, content: str = "", tool_calls: list | None = None) -> None:
        self.content = content
        self.tool_calls = tool_calls or []


class _FakeLLM:
    """LLM que reproduce una secuencia fija de respuestas; registra lo que se le pide."""

    def __init__(self, respuestas: list[_RespuestaLLM]) -> None:
        self._respuestas = list(respuestas)
        self.mensajes_vistos: list = []

    def bind_tools(self, tools):
        self.tools = tools
        return self

    async def ainvoke(self, mensajes):
        self.mensajes_vistos.append(mensajes)
        return self._respuestas.pop(0)


# ───────────────────────── Nivel 0 ─────────────────────────


class TestNivel0:

    def test_should_include_submateria_index_in_system_prompt(self):
        from server.app.modules.agents_hub.agent.public_graphs.profiles.public_kb_rich import (
            GenericAnswerTemplateStrategy,
        )

        index = "## Administració (administracio)\n- dietes: Dietes — Imports i justificació"
        prompt = GenericAnswerTemplateStrategy(
            base_system_prompt="Eres un asistente normativo.",
            retrieval_mode="MD_AGENT_SELECTOR",
            router_index=index,
        ).build_prompt_context([], "ca", "quant cobro de dieta?")

        assert "dietes" in prompt
        assert "Administració" in prompt
        # El router necesita saber qué TEMAS existen, y con qué reglas citarlos
        assert "rang" in prompt.lower()
        assert "vigen" in prompt.lower()

    def test_should_not_include_router_index_in_non_selector_modes(self):
        """En RAG el índice serían 2.300 tokens de prompt que nadie usa."""
        from server.app.modules.agents_hub.agent.public_graphs.profiles.public_kb_rich import (
            GenericAnswerTemplateStrategy,
        )

        prompt = GenericAnswerTemplateStrategy(
            retrieval_mode="RAG",
            router_index="## Administració (administracio)\n- dietes: Dietes",
        ).build_prompt_context([], "ca", "q")

        assert "dietes" not in prompt

    @pytest.mark.asyncio
    async def test_should_keep_level0_index_within_token_order_of_magnitude(self):
        """58 submaterias medidas = 2.307 tokens. El presupuesto del Nivel 0 son ~6k."""
        from server.app.modules.agents_hub.services.vocabulary_service import VocabularyService

        index = await VocabularyService(_vocabulario(58), uuid.uuid4()).build_router_index()

        tokens_estimados = len(index) // 4
        assert tokens_estimados < 6_000, f"el índice ocupa ~{tokens_estimados} tokens"


# ───────────────────────── Nivel 1 ─────────────────────────


class TestNivel1:

    @pytest.mark.asyncio
    async def test_should_list_documents_filtered_by_selected_submateries(self, db_session):
        from server.app.modules.agents_hub.services.retrieval.agentic_strategy import (
            AgenticRetrievalStrategy,
        )

        cb = uuid.uuid4()
        await _documento(
            db_session, cb, title="Dietes", ambit_principal="administracio",
            submateries=["indemnitzacions-i-dietes"],
            doc_metadata={"resum_router": "Imports de dieta", "rang": "reglament"},
        )
        await _documento(
            db_session, cb, title="Contractacio", ambit_principal="administracio",
            submateries=["contractacio"],
        )
        await db_session.commit()

        estrategia = AgenticRetrievalStrategy(db_session)
        fichas = await estrategia.list_index(
            cb, language=None, submateries=["indemnitzacions-i-dietes"]
        )

        assert [f["title"] for f in fichas] == ["Dietes"]
        assert estrategia.last_index_level == "submateries"
        # Ficha, no contenido: el resumen del router entra, el markdown no
        assert fichas[0]["resum_router"] == "Imports de dieta"
        assert fichas[0]["rang"] == "reglament"
        assert "markdown_content" not in fichas[0]

    @pytest.mark.asyncio
    async def test_should_fall_back_to_ambit_wide_index_when_nothing_matches(self, db_session):
        from server.app.modules.agents_hub.services.retrieval.agentic_strategy import (
            AgenticRetrievalStrategy,
        )
        from server.app.modules.agents_hub.services.retrieval.metadata_filter import (
            MetadataFilter,
        )

        cb = uuid.uuid4()
        await _documento(
            db_session, cb, title="Altres", ambit_principal="administracio",
            submateries=["altres"],
        )
        await _documento(db_session, cb, title="Fora", ambit_principal="academica")
        await db_session.commit()

        estrategia = AgenticRetrievalStrategy(
            db_session, metadata_filter=MetadataFilter(ambits=("administracio",))
        )
        fichas = await estrategia.list_index(cb, language=None, submateries=["dietes"])

        assert [f["title"] for f in fichas] == ["Altres"]
        assert estrategia.last_index_level == "ambit"

    @pytest.mark.asyncio
    async def test_should_fall_back_to_global_catalog_as_last_resort(self, db_session):
        from server.app.modules.agents_hub.services.retrieval.agentic_strategy import (
            AgenticRetrievalStrategy,
        )
        from server.app.modules.agents_hub.services.retrieval.metadata_filter import (
            MetadataFilter,
        )

        cb = uuid.uuid4()
        await _documento(db_session, cb, title="Fora d'ambit", ambit_principal="academica")
        await db_session.commit()

        estrategia = AgenticRetrievalStrategy(
            db_session, metadata_filter=MetadataFilter(ambits=("administracio",))
        )
        fichas = await estrategia.list_index(cb, language=None, submateries=["dietes"])

        assert [f["title"] for f in fichas] == ["Fora d'ambit"]
        assert estrategia.last_index_level == "global"

    @pytest.mark.asyncio
    async def test_should_not_leak_documents_outside_the_actor_filter(self, db_session):
        """VIS.1 sigue mandando: el retroceso ensancha el TEMA, nunca el permiso."""
        from server.app.modules.agents_hub.services.retrieval.agentic_strategy import (
            AgenticRetrievalStrategy,
        )
        from server.app.modules.agents_hub.services.retrieval.metadata_filter import (
            MetadataFilter,
        )

        cb = uuid.uuid4()
        await _documento(
            db_session, cb, title="Intern", nivell_acces="intern",
            ambit_principal="administracio", submateries=["dietes"],
        )
        await _documento(db_session, cb, title="Exclos", us_assistents="no")
        await db_session.commit()

        estrategia = AgenticRetrievalStrategy(
            db_session, metadata_filter=MetadataFilter.for_actor(nivell_acces=None)
        )
        fichas = await estrategia.list_index(cb, language=None, submateries=["dietes"])

        assert fichas == []
        assert estrategia.last_index_level == "global"

    @pytest.mark.asyncio
    async def test_should_pass_selected_submateries_from_the_tool_call(self):
        """El tool no gana un hermano `list_submateries`: el índice ya está en el prompt."""
        from server.app.modules.agents_hub.agent.tools.list_documents import list_documents

        class _Index:
            def __init__(self) -> None:
                self.recibido = None

            async def list_index(self, chatbot_id, language, submateries=None):
                self.recibido = submateries
                return [{
                    "id": str(uuid.uuid4()), "title": "Dietes", "url": "https://uji.es/d",
                    "language": "ca", "token_count": 900,
                    "resum_router": "Imports de dieta", "rang": "reglament",
                }]

        index = _Index()
        texto = await list_documents(str(uuid.uuid4()), index, submateries=["dietes"])

        assert index.recibido == ["dietes"]
        assert "Dietes" in texto
        assert "Imports de dieta" in texto

    @pytest.mark.asyncio
    async def test_should_record_fallback_level_in_evidence_debug(self):
        from server.app.modules.agents_hub.agent.public_graphs.strategies.agentic_loop import (
            AgenticLoop,
        )

        doc_id = str(uuid.uuid4())

        class _Reader:
            last_index_level = "global"

            async def list_index(self, chatbot_id, language, submateries=None):
                return "Documentos disponibles: ..."

            async def read(self, document_id):
                return {
                    "title": "Norma", "url": "https://uji.es/n",
                    "markdown_content": "Article 1. Text.", "language": "ca",
                }

        llm = _FakeLLM([
            _RespuestaLLM(tool_calls=[
                {"id": "1", "name": "list_documents", "args": {"submateries": ["dietes"]}}
            ]),
            _RespuestaLLM(tool_calls=[
                {"id": "2", "name": "read_document", "args": {"document_id": doc_id}}
            ]),
            _RespuestaLLM(content="Respuesta [Norma](https://uji.es/n)"),
        ])

        evidencias, _ = await AgenticLoop(reader=_Reader(), tools=[]).run(
            llm=llm, system="sys", query="quant cobro?", chatbot_id=str(uuid.uuid4()),
        )

        assert len(evidencias) == 1
        assert evidencias[0].metadata["index_fallback_level"] == "global"


# ───────────────────────── Nivel 2 ─────────────────────────


class TestNivel2:

    @pytest.mark.asyncio
    async def test_should_inject_only_selected_documents_not_whole_corpus(self, db_session):
        """MD_LONG_CONTEXT deja de significar «todo el corpus del chatbot»."""
        from server.app.modules.agents_hub.services.retrieval.long_context_strategy import (
            LongContextRetrievalStrategy,
        )
        from server.app.modules.agents_hub.services.retrieval.metadata_filter import (
            MetadataFilter,
        )

        cb = uuid.uuid4()
        await _documento(
            db_session, cb, title="Dietes", submateries=["dietes"], token_count=100,
        )
        for i in range(5):
            await _documento(
                db_session, cb, title=f"Altra {i}", submateries=["altres"], token_count=100,
            )
        await db_session.commit()

        ctx = await LongContextRetrievalStrategy(
            db_session, metadata_filter=MetadataFilter(submateries=("dietes",))
        ).get_context(query="dietes", chatbot_id=cb)

        assert [s.title for s in ctx.sources] == ["Dietes"]
        assert ctx.total_tokens == 100

    @pytest.mark.asyncio
    async def test_should_truncate_instead_of_raising_when_over_budget(self):
        """En producción una excepción por corpus grande es una caída, no un aviso."""
        from unittest.mock import AsyncMock, MagicMock

        from server.app.modules.agents_hub.services.retrieval.long_context_strategy import (
            LongContextRetrievalStrategy,
        )

        def _doc(titulo: str, tokens: int):
            doc = MagicMock()
            doc.id = uuid.uuid4()
            doc.title = titulo
            doc.canonical_url = "https://uji.es/n"
            doc.markdown_content = "Text."
            doc.language = "ca"
            doc.token_count = tokens
            doc.created_at = None
            return doc

        scalars = MagicMock()
        scalars.all.return_value = [_doc("A", 600), _doc("B", 600), _doc("C", 600)]
        resultado = MagicMock()
        resultado.scalars.return_value = scalars
        session = AsyncMock()
        session.execute = AsyncMock(return_value=resultado)

        ctx = await LongContextRetrievalStrategy(session, token_limit=1_000).get_context(
            query="q", chatbot_id=uuid.uuid4()
        )

        assert [s.title for s in ctx.sources] == ["A"]
        assert ctx.truncated is True
        assert ctx.discarded_documents == 2
        assert ctx.total_tokens == 600

    @pytest.mark.asyncio
    async def test_should_resolve_context_budget_from_cascade(self, db_session):
        from server.app.modules.agents_hub.agent.public_graphs.core.config_resolver import (
            get_effective_public_graph_config,
        )

        # 1. Sin nada declarado: default de plataforma
        org, chatbot = await _organizacion_con_chatbot(db_session)
        await db_session.commit()
        cfg = await get_effective_public_graph_config(chatbot.id, db_session)
        assert cfg.context_token_budget == 128_000

        # 2. La organización lo baja
        org.default_context_token_budget = 60_000
        await db_session.commit()
        cfg = await get_effective_public_graph_config(chatbot.id, db_session)
        assert cfg.context_token_budget == 60_000

        # 3. El chatbot manda sobre la organización
        chatbot.context_token_budget = 20_000
        await db_session.commit()
        cfg = await get_effective_public_graph_config(chatbot.id, db_session)
        assert cfg.context_token_budget == 20_000

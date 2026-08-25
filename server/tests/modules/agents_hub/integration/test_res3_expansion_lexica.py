"""RES.3 — Del fallo al término, con una persona en medio.

El objetivo es que el sistema aprenda el vocabulario de sus usuarios **sin pagar una llamada al
modelo por consulta**, y sin repetir el intento que ya fracasó: para el chatbot anterior se pidió a
los servicios que generaran lotes de preguntas y respuestas en hojas Excel y no funcionó. El motivo
importa para el diseño — aquel método pedía **inventar** pares en frío, que es trabajo cognitivo
alto y sin recompensa visible. Aquí el candidato no lo inventa nadie: lo produce RES.2 cada vez que
una reformulación rescata una pregunta, y a la persona sólo se le pide **aprobar o rechazar**.

Tres invariantes que estos tests fijan, y cada uno tiene su motivo:

1. **`bilingual_terms` es DERIVADO.** Se calcula sólo a partir de los pares aprobados y se puede
   regenerar entero desde la tabla. Sin esto, en seis meses nadie sabe de dónde salió un término ni
   cómo quitarlo, y «reclasificar» —que debe costar un `UPDATE`— vuelve a ser «reindexar».
2. **Nada se aplica sin que una persona lo apruebe.** Un par propuesto por un modelo que entrara
   solo en la búsqueda sería el corpus cambiando sin que nadie lo haya decidido.
3. **El léxico NUNCA entra en el texto que se embebe.** Va al `tsvector`, que se regenera con una
   sentencia SQL; un embedding necesita GPU y horas.
"""
import uuid

import pytest
from sqlalchemy import select

from server.app.modules.agents_hub.database.operational_models import (
    HubDocument,
    HubDocumentChunk,
    HubLexiconPair,
)
from server.app.modules.agents_hub.services.lexicon import (
    aprobar_par,
    proponer_par,
    proyectar_lexico,
    rechazar_par,
)


class TestLaTablaEstaDelLadoQueLeToca:
    """**La tabla nació en `HubConfigBase` y el guardarraíl de la frontera lo rechazó con razón.**

    `termino_de_usuario` es literalmente lo que escribió una persona, y la configuración se
    sincroniza cloud→edge: ponerla ahí obligaba a que el texto de las preguntas del cliente
    existiera en el cloud, que es exactamente lo que el modo edge+cloud está montado para evitar.
    Mismo motivo por el que `hub_test_scenarios` es operacional.

    Lo que decide el lado no es «es vocabulario» —`hub_vocabulary_terms` es configuración y está
    bien—, es **si lleva dentro lo que escribió una persona**.
    """

    def test_should_live_on_the_operational_side(self):
        from server.app.modules.agents_hub.database.base import (
            HubConfigBase,
            HubOperationalBase,
        )

        assert issubclass(HubLexiconPair, HubOperationalBase)
        assert not issubclass(HubLexiconPair, HubConfigBase)

    def test_should_not_reference_config_tables_with_a_foreign_key(self):
        """Ningún modelo operacional de este esquema lo hace: las dos bases tienen que poder
        vivir separadas, y el acotado por organización lo garantiza el código."""
        for columna in ("organizacion_id", "document_id"):
            assert not HubLexiconPair.__table__.columns[columna].foreign_keys

    def test_should_not_express_the_terms_as_an_enum(self):
        """El vocabulario es dato, no código: está para revisarse."""
        columnas = HubLexiconPair.__table__.columns
        for nombre in ("termino_de_usuario", "termino_normativo"):
            tipo = columnas[nombre].type
            assert getattr(tipo, "enums", None) is None, (
                f"{nombre} no puede ser un Enum: renombrar un término tendría que costar una "
                "migración, y por eso ING.0.1 puso el vocabulario en tabla"
            )

    def test_should_be_revisable_like_the_vocabulary(self):
        """Misma forma que `hub_vocabulary_terms`, y por lo mismo: renombrar y fusionar sin
        migración."""
        columnas = set(HubLexiconPair.__table__.columns.keys())
        assert {"vigent", "substituit_per_codi"} <= columnas


@pytest.mark.asyncio
class TestElCandidatoSaleDelFallo:

    async def test_should_propose_a_pair_from_a_working_reformulation(self, db_session):
        """El par llega **ya validado por haber funcionado**: la reformulación que rescató la
        pregunta es, literalmente, la consulta que sí encontró el documento."""
        seed_org = await _organizacion(db_session, "Org de RES.3")
        documento = await _documento(db_session, seed_org)

        par = await proponer_par(
            db_session,
            organizacion_id=seed_org,
            document_id=documento.id,
            termino_de_usuario="quiero tramitar una compra de un equipo de 6.500 euros",
            termino_normativo="contracte menor de subministrament",
            origen="reformulacion",
        )

        assert par.estado == "propuesto"
        assert par.origen == "reformulacion"

    async def test_should_not_apply_a_pair_until_a_person_approves_it(self, db_session):
        seed_org = await _organizacion(db_session, "Org de RES.3")
        documento = await _documento(db_session, seed_org)
        await proponer_par(
            db_session,
            organizacion_id=seed_org,
            document_id=documento.id,
            termino_de_usuario="compra de 6.500 euros",
            termino_normativo="contracte menor de subministrament",
            origen="reformulacion",
        )

        await proyectar_lexico(db_session, organizacion_id=seed_org)

        trozos = await _trozos(db_session, documento.id)
        assert all(not (t.bilingual_terms or "") for t in trozos), (
            "un par propuesto por un modelo que entrara solo en la búsqueda seria el corpus "
            "cambiando sin que nadie lo haya decidido"
        )


@pytest.mark.asyncio
class TestLaProyeccionEsDerivada:

    async def test_should_project_approved_pairs_into_bilingual_terms(self, db_session):
        seed_org = await _organizacion(db_session, "Org de RES.3")
        documento = await _documento(db_session, seed_org)
        par = await proponer_par(
            db_session,
            organizacion_id=seed_org,
            document_id=documento.id,
            termino_de_usuario="compra de 6.500 euros",
            termino_normativo="contracte menor de subministrament",
            origen="reformulacion",
        )
        await aprobar_par(db_session, par.id, revisado_por="fabra@uji.es")

        await proyectar_lexico(db_session, organizacion_id=seed_org)

        trozos = await _trozos(db_session, documento.id)
        assert trozos
        for trozo in trozos:
            assert "compra de 6.500 euros" in (trozo.bilingual_terms or "")

    async def test_should_regenerate_the_projection_from_the_table_alone(
        self, db_session
    ):
        """Nadie edita `bilingual_terms` a mano: si la proyección no se puede reconstruir, el
        término se queda ahí para siempre y nadie sabe por qué."""
        seed_org = await _organizacion(db_session, "Org de RES.3")
        documento = await _documento(db_session, seed_org)
        par = await proponer_par(
            db_session,
            organizacion_id=seed_org,
            document_id=documento.id,
            termino_de_usuario="compra de 6.500 euros",
            termino_normativo="contracte menor de subministrament",
            origen="reformulacion",
        )
        await aprobar_par(db_session, par.id, revisado_por="fabra@uji.es")
        await proyectar_lexico(db_session, organizacion_id=seed_org)
        primera = [t.bilingual_terms for t in await _trozos(db_session, documento.id)]

        # Basura escrita a mano: la regeneración tiene que borrarla. Se escribe con un UPDATE
        # directo justo porque eso es lo que se quiere simular — alguien tocando la columna por
        # fuera de la tabla de pares.
        from sqlalchemy import update

        await db_session.execute(
            update(HubDocumentChunk)
            .where(HubDocumentChunk.document_id == documento.id)
            .values(bilingual_terms="algo que nadie aprobo")
        )
        await db_session.commit()

        await proyectar_lexico(db_session, organizacion_id=seed_org)
        segunda = [t.bilingual_terms for t in await _trozos(db_session, documento.id)]

        assert segunda == primera

    async def test_should_drop_a_rejected_pair_from_the_projection(self, db_session):
        seed_org = await _organizacion(db_session, "Org de RES.3")
        documento = await _documento(db_session, seed_org)
        par = await proponer_par(
            db_session,
            organizacion_id=seed_org,
            document_id=documento.id,
            termino_de_usuario="compra de 6.500 euros",
            termino_normativo="contracte menor de subministrament",
            origen="reformulacion",
        )
        await aprobar_par(db_session, par.id, revisado_por="fabra@uji.es")
        await proyectar_lexico(db_session, organizacion_id=seed_org)

        await rechazar_par(db_session, par.id, revisado_por="fabra@uji.es")
        await proyectar_lexico(db_session, organizacion_id=seed_org)

        trozos = await _trozos(db_session, documento.id)
        assert all(not (t.bilingual_terms or "") for t in trozos), (
            "reversible por construcción: quitar un término tiene que costar lo mismo que ponerlo"
        )


@pytest.mark.asyncio
class TestElLexicoNoEntraEnElEmbedding:
    """Regla dura del proyecto: en `embedding_text` sólo va contexto **estructural**. Si un
    término del léxico se cuela ahí, reclasificar deja de costar un `UPDATE` y pasa a costar una
    reingesta con GPU."""

    async def test_should_never_put_the_lexicon_into_the_embedded_text(
        self, db_session
    ):
        seed_org = await _organizacion(db_session, "Org de RES.3")
        documento = await _documento(db_session, seed_org)
        par = await proponer_par(
            db_session,
            organizacion_id=seed_org,
            document_id=documento.id,
            termino_de_usuario="compra de 6.500 euros",
            termino_normativo="contracte menor de subministrament",
            origen="reformulacion",
        )
        await aprobar_par(db_session, par.id, revisado_por="fabra@uji.es")
        antes = [t.embedding_text for t in await _trozos(db_session, documento.id)]

        await proyectar_lexico(db_session, organizacion_id=seed_org)

        despues = [t.embedding_text for t in await _trozos(db_session, documento.id)]
        assert despues == antes
        assert all("compra de 6.500" not in (t or "") for t in despues)


@pytest.mark.asyncio
class TestElParAprobadoHaceEncontrarElDocumento:
    """El extremo a extremo, y es el objetivo del prompt: quitar la llamada al modelo. Si el par
    aprobado hace que la rama léxica encuentre el documento, la segunda pasada de RES.2 deja de
    ser necesaria para esa consulta."""

    async def test_should_retrieve_the_document_after_approving_the_pair(
        self, db_session
    ):
        from server.app.modules.agents_hub.services.retriever import HybridRetriever

        seed_org = await _organizacion(db_session, "Org de RES.3")
        documento = await _documento(db_session, seed_org)
        retriever = HybridRetriever(db_session)

        antes = await retriever.keyword_search(
            "compra de 6.500 euros", documento.chatbot_id, top_k=5
        )

        par = await proponer_par(
            db_session,
            organizacion_id=seed_org,
            document_id=documento.id,
            termino_de_usuario="compra de 6.500 euros",
            termino_normativo="contracte menor de subministrament",
            origen="reformulacion",
        )
        await aprobar_par(db_session, par.id, revisado_por="fabra@uji.es")
        await proyectar_lexico(db_session, organizacion_id=seed_org)

        despues = await retriever.keyword_search(
            "compra de 6.500 euros", documento.chatbot_id, top_k=5
        )

        assert not antes
        assert despues, (
            "el término aprobado va al tsvector, que es columna generada: la rama léxica tiene "
            "que encontrar el documento sin que nadie haya recalculado un embedding"
        )


@pytest.mark.asyncio
class TestLosParesNoSeFiltranEntreOrganizaciones:

    async def test_should_scope_pairs_to_the_organizacion(self, db_session):
        seed_org = await _organizacion(db_session, "Org de RES.3")
        documento = await _documento(db_session, seed_org)
        par = await proponer_par(
            db_session,
            organizacion_id=seed_org,
            document_id=documento.id,
            termino_de_usuario="compra de 6.500 euros",
            termino_normativo="contracte menor de subministrament",
            origen="reformulacion",
        )
        await aprobar_par(db_session, par.id, revisado_por="fabra@uji.es")

        # Se proyecta la OTRA organización: no debe tocar nada de esta.
        otra_org = await _organizacion(db_session, "Otra org")
        await proyectar_lexico(db_session, organizacion_id=otra_org)

        trozos = await _trozos(db_session, documento.id)
        assert all(not (t.bilingual_terms or "") for t in trozos)


# ---------------------------------------------------------------------------
# Ayudas
# ---------------------------------------------------------------------------

async def _organizacion(session, nombre: str) -> uuid.UUID:
    from server.app.modules.agents_hub.database.config_models import HubOrganizacion

    organizacion = HubOrganizacion(name=nombre, partner_id="partner_dev")
    session.add(organizacion)
    await session.flush()
    return organizacion.id


async def _documento(session, organizacion_id) -> HubDocument:
    """Un documento con dos trozos, para que la proyección tenga que alcanzar a los dos."""
    from server.app.modules.agents_hub.database.config_models import (
        HubChatbot,
        HubLLMConfig,
        HubProvider,
    )

    await session.merge(
        HubProvider(id="google", name="Google", provider_type="google_genai")
    )
    llm = HubLLMConfig(provider="google", model_name="gemini-flash")
    session.add(llm)
    await session.flush()

    chatbot = HubChatbot(
        organizacion_id=organizacion_id,
        llm_config_id=llm.id,
        name="Chatbot de prueba RES.3",
        system_prompt="Test",
        sources=[],
    )
    session.add(chatbot)
    await session.flush()

    documento = HubDocument(
        chatbot_id=chatbot.id,
        title="INSTRUCCIO D'EXPEDIENTS DE CONTRACTES MENORS",
        canonical_url="https://example.test/instruccio",
        markdown_content="# Instruccio\n\nContingut.",
        content_hash="doc-res3",
        language="ca",
        source_kind="normativa",
    )
    session.add(documento)
    await session.flush()

    for orden, texto in enumerate(
        [
            "Els expedients de contractes menors de subministrament...",
            "El limit per a serveis es de 15.000 euros...",
        ]
    ):
        session.add(
            HubDocumentChunk(
                chatbot_id=chatbot.id,
                document_id=documento.id,
                content=texto,
                embedding_text=texto,
                content_hash=f"h{orden}",
                source_url="https://example.test/instruccio",
                embedding=[0.1] * 1024,
                embedding_model="BAAI/bge-m3",
                embedding_dim=1024,
                language="ca",
            )
        )
    await session.commit()
    documento.chatbot_id = chatbot.id
    return documento


async def _trozos(session, document_id) -> list:
    """Las columnas, no los objetos.

    `proyectar_lexico` escribe con un `UPDATE` masivo, así que los objetos que la sesión tiene en
    memoria quedan obsoletos; y refrescarlos por atributo dispara una carga diferida fuera del
    contexto async (`MissingGreenlet`). Pedir las columnas en la propia consulta evita las dos
    cosas y además deja claro qué se está comprobando.
    """
    filas = await session.execute(
        select(
            HubDocumentChunk.content_hash,
            HubDocumentChunk.bilingual_terms,
            HubDocumentChunk.embedding_text,
        )
        .where(HubDocumentChunk.document_id == document_id)
        .order_by(HubDocumentChunk.content_hash)
    )
    return list(filas.all())


@pytest.mark.asyncio
class TestLaCosechaCierraElBucle:
    """El par lo produce RES.2 al rescatar una pregunta. Nadie lo inventa, y eso es lo que
    distingue esto del intento de los lotes en Excel."""

    async def test_should_propose_pairs_from_the_rescued_runs(self, db_session):
        from server.app.modules.agents_hub.database.operational_models import (
            HubTestRun,
            HubTestScenario,
        )
        from server.app.modules.agents_hub.services.lexicon import (
            cosechar_de_las_ejecuciones,
        )

        seed_org = await _organizacion(db_session, "Org de RES.3")
        documento = await _documento(db_session, seed_org)

        escenario = HubTestScenario(
            chatbot_id=documento.chatbot_id,
            name="REAL-04",
            prompt="Quiero tramitar una compra de un equipo de 6.500 euros.",
        )
        db_session.add(escenario)
        await db_session.flush()
        db_session.add(
            HubTestRun(
                scenario_id=escenario.id,
                answer="Se tramita como contrato menor...",
                sources=[{"document_id": str(documento.id), "title": "Instruccio"}],
                reformulada=True,
                reformulated_query="contrato menor de suministro",
            )
        )
        await db_session.commit()

        pares = await cosechar_de_las_ejecuciones(
            db_session, organizacion_id=seed_org, chatbot_id=documento.chatbot_id
        )

        assert len(pares) == 1
        assert pares[0].termino_de_usuario.startswith("Quiero tramitar")
        assert pares[0].termino_normativo == "contrato menor de suministro"
        assert pares[0].estado == "propuesto", (
            "la cosecha propone; aplicar es decision de una persona"
        )

    async def test_should_not_propose_from_a_run_that_cited_nothing(self, db_session):
        """Sin documento, la proyección no sabría dónde escribir."""
        from server.app.modules.agents_hub.database.operational_models import (
            HubTestRun,
            HubTestScenario,
        )
        from server.app.modules.agents_hub.services.lexicon import (
            cosechar_de_las_ejecuciones,
        )

        seed_org = await _organizacion(db_session, "Org de RES.3")
        documento = await _documento(db_session, seed_org)

        escenario = HubTestScenario(
            chatbot_id=documento.chatbot_id, name="sin citas", prompt="algo"
        )
        db_session.add(escenario)
        await db_session.flush()
        db_session.add(
            HubTestRun(
                scenario_id=escenario.id,
                answer="respuesta sin fuentes",
                sources=[],
                reformulada=True,
                reformulated_query="otra cosa",
            )
        )
        await db_session.commit()

        pares = await cosechar_de_las_ejecuciones(
            db_session, organizacion_id=seed_org, chatbot_id=documento.chatbot_id
        )

        assert pares == []

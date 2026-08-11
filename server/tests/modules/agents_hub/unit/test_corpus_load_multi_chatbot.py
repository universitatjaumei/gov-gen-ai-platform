"""DER.1 — una carga, varios chatbots.

Se descartó COR (compartir el documento entre chatbots) porque la deduplicación casi nunca se
dispararía y porque filas separadas conservan que cada asistente elija su modelo de embedding.
Lo que sí resuelve el problema de mantenimiento es **no duplicar la fuente**: un solo `.md` en
disco y una sola pasada que lo carga en los asistentes que haga falta.

Lo que se lee, parsea y valida es común; lo que se repite es la reconciliación, que es lo
único que depende del destino.

Deploy: edge
"""
from __future__ import annotations

import argparse
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ORG = uuid.UUID("00000000-0000-0000-0000-0000000000c1")
OTRA_ORG = uuid.UUID("00000000-0000-0000-0000-0000000000c2")


def _chatbot(organizacion_id=ORG):
    return MagicMock(organizacion_id=organizacion_id)


def _informe(**kw):
    m = MagicMock()
    m.detalle = kw.get("detalle", [])
    m.motivos_omision = []
    m.poda_omitida_por_no_censo = False
    m.render.return_value = kw.get("render", "ingeridos=2")
    return m


def _args(chatbot_ids, **kw):
    return argparse.Namespace(
        dir=Path("corpus"),
        manifest=None,
        chatbot_ids=list(chatbot_ids),
        dry_run=kw.get("dry_run", True),
        census=False,
        prune=False,
        force_prune=False,
        prune_threshold=0.10,
        verbose=False,
    )


class _Escenario:
    """Monta los dobles de `_run` y deja a mano lo que cada test quiere mirar."""

    def __init__(self, chatbots, *, entradas=(), reconcile=None, embedding=None,
                 divergencias=()):
        self.session = AsyncMock()
        self.session.get = AsyncMock(side_effect=list(chatbots))
        # `_run` consulta los chatbots de la organización para el aviso de deriva (DER.2).
        # Sin esto, un AsyncMock devuelve corrutinas encadenadas en vez de filas.
        chatbots_org = MagicMock()
        chatbots_org.scalars.return_value.all.return_value = []
        self.session.execute = AsyncMock(return_value=chatbots_org)

        self.fabrica = MagicMock()
        self.fabrica.return_value.__aenter__ = AsyncMock(return_value=self.session)
        self.fabrica.return_value.__aexit__ = AsyncMock(return_value=False)

        self.fuente = MagicMock()
        self.fuente.list_entries = AsyncMock(return_value=list(entradas))

        self.reconciliador = MagicMock()
        self.reconciliador.reconcile = reconcile or AsyncMock(return_value=_informe())

        self.resolver = embedding or AsyncMock(
            return_value=MagicMock(model_name="BAAI/bge-m3")
        )
        self.guarda = AsyncMock()
        # DER.2: la comprobación de deriva del final tiene sus propios tests.
        self.divergencias = AsyncMock(return_value=list(divergencias))

    def parches(self, load):
        return (
            patch.object(load, "LocalDirectorySource", return_value=self.fuente),
            patch.object(load, "assert_vocabulary", AsyncMock()) ,
            patch.object(load, "CorpusReconciler", return_value=self.reconciliador),
            patch(
                "server.app.modules.agents_hub.database.connection.create_async_engine",
                return_value=MagicMock(dispose=AsyncMock()),
            ),
            patch(
                "server.app.modules.agents_hub.database.connection.create_session_factory",
                return_value=self.fabrica,
            ),
            patch(
                "server.app.modules.agents_hub.services.embedding_resolver."
                "resolve_embedding_service",
                self.resolver,
            ),
            patch(
                "server.app.modules.agents_hub.services.embedding_space."
                "assert_embedding_space_matches",
                self.guarda,
            ),
            patch(
                "server.app.modules.agents_hub.ingestion.divergence_detector.detectar_divergencias",
                self.divergencias,
            ),
            patch("server.app.modules.agents_hub.ingestion.watcher.IngestionWatcher"),
        )


async def _ejecutar(escenario, args):
    from server.app.modules.agents_hub.ingestion.corpus import load

    parches = escenario.parches(load)
    for p in parches:
        p.start()
    try:
        return await load._run(args)
    finally:
        for p in parches:
            p.stop()


class TestUnaSolaLectura:

    @pytest.mark.asyncio
    async def test_should_parse_the_source_once_for_several_chatbots(self):
        """Leer, parsear y validar el corpus dos veces sería trabajo idéntico repetido.

        Con 262 documentos no es una micro-optimización: es la diferencia entre una pasada y
        dos, y sobre todo garantiza que **los dos asistentes reciben exactamente lo mismo**.
        Dos lecturas de la misma carpeta pueden diferir si alguien toca un fichero a mitad.
        """
        esc = _Escenario([_chatbot(), _chatbot()])

        codigo = await _ejecutar(esc, _args([uuid.uuid4(), uuid.uuid4()]))

        assert codigo == 0
        assert esc.fuente.list_entries.await_count == 1
        assert esc.reconciliador.reconcile.await_count == 2

    @pytest.mark.asyncio
    async def test_should_resolve_the_embedding_service_per_chatbot(self):
        """Cada asistente embebe con el suyo: es justo la libertad por la que se descartó COR."""
        esc = _Escenario([_chatbot(), _chatbot()])

        await _ejecutar(esc, _args([uuid.uuid4(), uuid.uuid4()]))

        assert esc.resolver.await_count == 2


class TestLaComprobacionVaAntesDeEscribir:

    @pytest.mark.asyncio
    async def test_should_refuse_chatbots_from_different_organizations(self):
        """Cargar corpus curado de una administración en otra no puede pasar ni a medias."""
        esc = _Escenario([_chatbot(ORG), _chatbot(OTRA_ORG)])

        codigo = await _ejecutar(esc, _args([uuid.uuid4(), uuid.uuid4()]))

        assert codigo != 0
        esc.reconciliador.reconcile.assert_not_awaited()
        esc.session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_refuse_when_a_chatbot_does_not_exist(self):
        esc = _Escenario([_chatbot(), None])

        codigo = await _ejecutar(esc, _args([uuid.uuid4(), uuid.uuid4()]))

        assert codigo != 0
        esc.reconciliador.reconcile.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_should_check_every_embedding_space_before_loading_any_chatbot(self):
        """La guarda de FIX.4, pero para todos antes de empezar.

        Comprobarla justo antes de cada carga dejaría el primer asistente ya cargado cuando
        se descubriera que el segundo tiene el corpus en otro espacio vectorial. Y entonces
        la pasada no se puede repetir limpia: hay que deshacer a mano.
        """
        from server.app.modules.agents_hub.services.embedding_space import (
            EmbeddingSpaceMismatch,
        )

        esc = _Escenario([_chatbot(), _chatbot()])
        esc.guarda.side_effect = [None, EmbeddingSpaceMismatch("BAAI/bge-m3 (1024)")]

        codigo = await _ejecutar(esc, _args([uuid.uuid4(), uuid.uuid4()]))

        assert codigo == 3
        esc.reconciliador.reconcile.assert_not_awaited()


class TestElInformeEsPorChatbot:

    @pytest.mark.asyncio
    async def test_should_report_results_per_chatbot(self, capsys):
        """«12 nuevos, 3 actualizados» sin decir en cuál no sirve para nada."""
        primero, segundo = uuid.uuid4(), uuid.uuid4()
        esc = _Escenario(
            [_chatbot(), _chatbot()],
            reconcile=AsyncMock(
                side_effect=[_informe(render="ingeridos=2"), _informe(render="ingeridos=0")]
            ),
        )

        await _ejecutar(esc, _args([primero, segundo]))

        salida = capsys.readouterr().out
        assert str(primero) in salida
        assert str(segundo) in salida
        assert "ingeridos=2" in salida
        assert "ingeridos=0" in salida

    @pytest.mark.asyncio
    async def test_should_not_mark_the_run_successful_when_one_chatbot_fails(self, capsys):
        """Un fallo en el segundo no puede salir con 0: quien lo automatice no se enteraría.

        Y el que sí funcionó se conserva —la reconciliación es incremental, así que repetir
        la pasada solo rehace lo que falta—, pero se dice cuál fue cada cosa.
        """
        from server.app.modules.agents_hub.ingestion.corpus.reconciler import (
            PruneThresholdExceeded,
        )

        primero, segundo = uuid.uuid4(), uuid.uuid4()
        esc = _Escenario(
            [_chatbot(), _chatbot()],
            reconcile=AsyncMock(
                side_effect=[_informe(), PruneThresholdExceeded("poda del 40%")]
            ),
        )

        codigo = await _ejecutar(esc, _args([primero, segundo], dry_run=False))

        assert codigo != 0
        salida = capsys.readouterr().out + capsys.readouterr().err
        assert str(segundo) in salida


class TestElAvisoDeDeriva:
    """DER.2 — cargar en A no toca a B, y este es el único momento en que alguien mira."""

    @pytest.mark.asyncio
    async def test_should_warn_about_chatbots_left_with_the_previous_version(self, capsys):
        from server.app.modules.agents_hub.ingestion.divergence_detector import Divergencia

        atrasado = uuid.uuid4()
        divergencia = Divergencia(
            chatbot_id=atrasado,
            canonical_url="https://uji.es/instruccio-1-2019",
            title="Instrucció 1/2019",
            id_publicacio="UJI-GER-2019-1",
            document_id=uuid.uuid4(),
            content_hash="hash-viejo",
            hash_vigent="hash-nuevo",
            actualitzat=None,
            actualitzat_vigent=None,
            chatbots_afectats=(atrasado,),
            indeterminat=False,
            vigencia_en_disputa=False,
        )
        esc = _Escenario([_chatbot()], divergencias=[divergencia])

        await _ejecutar(esc, _args([uuid.uuid4()], dry_run=False))

        salida = capsys.readouterr().out
        assert str(atrasado) in salida
        assert "UJI-GER-2019-1" in salida
        # No se propaga solo: cada asistente tiene su receta y su calendario.
        assert "nada se propaga solo" in salida

    @pytest.mark.asyncio
    async def test_should_check_against_every_chatbot_of_the_organization(self):
        """Y no solo contra los de esta pasada: los que faltan son el problema."""
        esc = _Escenario([_chatbot()])

        await _ejecutar(esc, _args([uuid.uuid4()], dry_run=False))

        esc.divergencias.assert_awaited()


class TestElCaminoDeUnSoloChatbot:

    @pytest.mark.asyncio
    async def test_should_keep_working_with_a_single_chatbot(self):
        """Lo de siempre sigue siendo lo de siempre: un `--chatbot-id` y ya."""
        esc = _Escenario([_chatbot()])

        codigo = await _ejecutar(esc, _args([uuid.uuid4()]))

        assert codigo == 0
        assert esc.reconciliador.reconcile.await_count == 1

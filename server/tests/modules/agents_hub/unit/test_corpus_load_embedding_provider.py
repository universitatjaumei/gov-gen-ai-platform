"""FIX.4 — la carga del corpus embebe con el modelo configurado, no con el local a pelo.

`corpus/load.py` y `corpus/sync.py` construían `LocalEmbeddingService()` directamente. Eso ya
contradecía MOD.2 —que existe precisamente para que el servicio salga de la configuración y
no de un `import`—, y tiene dos consecuencias, ninguna buena:

- **Con el extra instalado**: el corpus queda embebido con BGE-M3 aunque el despliegue esté
  configurado con Google. La guarda de RAG.9 lo detecta... en la primera consulta de chat,
  o sea después de haber pagado la ingesta entera.
- **Sin el extra** (la instalación estándar desde D.4.0): la carga falla, porque `torch` y
  `sentence-transformers` son opcionales.

Lo que se arregla no es «que no falle»: es que la carga deje de ignorar la configuración.

Deploy: edge
"""
from __future__ import annotations

import argparse
import ast
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

MODULOS_DE_CARGA = (
    "server/app/modules/agents_hub/ingestion/corpus/load.py",
    "server/app/modules/agents_hub/ingestion/corpus/sync.py",
)


def _raiz_del_repo() -> Path:
    return Path(__file__).resolve().parents[5]


def _nombres_importados(ruta: Path) -> set[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    return {
        alias.name
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.ImportFrom)
        for alias in nodo.names
    }


class TestLasCLIsCarganElEntorno:
    """PIL.6: la CLI no pasa por FastAPI, así que nadie carga `server/.env` por ella.

    Sin esto, la carga aborta diciendo que falta `GOOGLE_CLOUD_PROJECT` **cuando está
    definida en el fichero que la aplicación sí lee**: un error a la vez cierto y engañoso,
    que manda a buscar el problema donde no está. Costó una vuelta entera descubrirlo.
    """

    def test_should_load_the_dotenv_the_application_reads(self):
        ruta = _raiz_del_repo() / "server/app/modules/agents_hub/ingestion/corpus/load.py"

        assert "from server.app.core import config" in ruta.read_text(encoding="utf-8"), (
            "la CLI no carga `server/.env`: quien la use vera 'falta GOOGLE_CLOUD_PROJECT' "
            "aunque la variable este puesta"
        )

    def test_should_load_it_before_resolving_the_embedding_service(self):
        """El orden importa: el servicio se construye leyendo el entorno.

        Comprobado sobre el fuente y no ejecutando, porque una comprobación de verdad
        dependería del `.env` de quien la corra —y ese fichero no existe en CI—.
        """
        fuente = (
            _raiz_del_repo() / "server/app/modules/agents_hub/ingestion/corpus/load.py"
        ).read_text(encoding="utf-8")

        assert fuente.index("from server.app.core import config") < fuente.index(
            "resolve_embedding_service"
        ), "el entorno se carga despues de resolver el servicio, que es tarde"


class TestLasCLIsNoCableanElServicioLocal:

    @pytest.mark.parametrize("modulo", MODULOS_DE_CARGA)
    def test_should_not_import_the_local_embedding_service(self, modulo):
        """El guardarraíl estructural: mientras el import esté, alguien lo volverá a usar.

        Se comprueba sobre el AST y no con una búsqueda de texto para no cazar la mención
        del nombre en un comentario o en esta misma explicación.
        """
        importados = _nombres_importados(_raiz_del_repo() / modulo)

        assert "LocalEmbeddingService" not in importados, (
            f"{modulo} sigue importando LocalEmbeddingService; el servicio se resuelve "
            "con resolve_embedding_service (MOD.2)"
        )

    @pytest.mark.parametrize("modulo", MODULOS_DE_CARGA)
    def test_should_import_the_resolver(self, modulo):
        importados = _nombres_importados(_raiz_del_repo() / modulo)

        assert "resolve_embedding_service" in importados, importados


class TestElOrdenDeCargaDeTorch:
    """En Windows, cargar torch después de abrir una conexión asyncpg mata el proceso.

    No es teoría: **la CLI moría con SIGSEGV** entre D.4.0 y FIX.4. El comentario de
    `load.py` decía que importar `MarkdownChunker` arriba forzaba el orden, y era verdad
    hasta que D.4.0 movió el import de `langchain_text_splitters` dentro del constructor
    del chunker —para que un despliegue sin modelos locales no pague la pila—. La precarga
    se quedó sin efecto y el comentario siguió afirmando que funcionaba.

    Por eso esto se comprueba y no se explica: un comentario no falla cuando deja de ser
    cierto.
    """

    @pytest.mark.parametrize("modulo", MODULOS_DE_CARGA)
    def test_should_preload_the_splitter_at_module_level(self, modulo):
        arbol = ast.parse((_raiz_del_repo() / modulo).read_text(encoding="utf-8"))

        precargados = {
            alias.name.split(".")[0]
            for nodo in arbol.body  # solo nivel de módulo: dentro de una función no sirve
            if isinstance(nodo, ast.Import)
            for alias in nodo.names
        }

        assert "langchain_text_splitters" in precargados, (
            f"{modulo} no precarga el splitter en el nivel de módulo. IngestionWatcher "
            "construye un chunker con la sesión ya abierta, y en Windows eso aborta el "
            "proceso con un access violation."
        )

    @pytest.mark.parametrize("modulo", MODULOS_DE_CARGA)
    def test_should_preload_before_touching_the_database(self, modulo):
        """La precarga tiene que ir ANTES del primer import del paquete de base de datos.

        Estar en el fichero no basta: lo que importa es el orden.
        """
        arbol = ast.parse((_raiz_del_repo() / modulo).read_text(encoding="utf-8"))

        linea_splitter = min(
            (
                nodo.lineno
                for nodo in ast.walk(arbol)
                if isinstance(nodo, ast.Import)
                for alias in nodo.names
                if alias.name.split(".")[0] == "langchain_text_splitters"
            ),
            default=None,
        )
        lineas_bd = [
            nodo.lineno
            for nodo in ast.walk(arbol)
            if isinstance(nodo, ast.ImportFrom)
            and (nodo.module or "").endswith("database.connection")
        ]

        assert linea_splitter is not None
        for linea in lineas_bd:
            assert linea_splitter < linea, (
                f"{modulo}: el splitter se precarga en la línea {linea_splitter}, después "
                f"del import de la conexión de BD en la {linea}"
            )


class TestLaCargaUsaElServicioResuelto:

    @pytest.mark.asyncio
    async def test_should_embed_with_the_service_resolved_from_configuration(self):
        """El caso que importa: con Google configurado, la carga embebe con Google.

        Se mira qué recibe `IngestionWatcher`, que es quien acaba llamando al servicio: es
        el punto donde la decisión se vuelve irreversible, porque el vector ya se escribe
        con esa procedencia.
        """
        from server.app.modules.agents_hub.ingestion.corpus import load

        servicio_configurado = MagicMock(name="GoogleEmbeddingService")
        chatbot_id = uuid.uuid4()

        session = AsyncMock()
        session.get = AsyncMock(return_value=MagicMock(organizacion_id=uuid.uuid4()))
        # DER.2: `_run` consulta los chatbots de la organización para el aviso de deriva.
        sin_hermanos = MagicMock()
        sin_hermanos.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=sin_hermanos)

        fabrica = MagicMock()
        fabrica.return_value.__aenter__ = AsyncMock(return_value=session)
        fabrica.return_value.__aexit__ = AsyncMock(return_value=False)

        fuente = MagicMock()
        fuente.list_entries = AsyncMock(return_value=[])

        informe = MagicMock()
        informe.detalle = []
        informe.motivos_omision = []
        informe.poda_omitida_por_no_censo = False
        reconciliador = MagicMock()
        reconciliador.reconcile = AsyncMock(return_value=informe)

        args = argparse.Namespace(
            dir=Path("corpus"), manifest=None, chatbot_ids=[chatbot_id], dry_run=True,
            census=False, prune=False, force_prune=False, prune_threshold=0.10,
            verbose=False,
        )

        with (
            patch.object(load, "LocalDirectorySource", return_value=fuente),
            patch.object(load, "assert_vocabulary", AsyncMock()),
            patch.object(load, "CorpusReconciler", return_value=reconciliador) as ctor_rec,
            patch(
                "server.app.modules.agents_hub.database.connection.create_async_engine",
                return_value=MagicMock(dispose=AsyncMock()),
            ),
            patch(
                "server.app.modules.agents_hub.database.connection.create_session_factory",
                return_value=fabrica,
            ),
            patch(
                "server.app.modules.agents_hub.services.embedding_resolver."
                "resolve_embedding_service",
                AsyncMock(return_value=servicio_configurado),
            ) as resolver,
            # La guarda de espacio vectorial tiene su propio test, justo debajo.
            patch(
                "server.app.modules.agents_hub.services.embedding_space."
                "assert_embedding_space_matches",
                AsyncMock(),
            ),
            patch(
                "server.app.modules.agents_hub.ingestion.divergence_detector."
                "detectar_divergencias",
                AsyncMock(return_value=[]),
            ),
            patch(
                "server.app.modules.agents_hub.ingestion.watcher.IngestionWatcher"
            ) as ctor_watcher,
        ):
            codigo = await load._run(args)

        assert codigo == 0
        resolver.assert_awaited()
        assert ctor_rec.called, "no se llegó a construir el reconciliador"
        # El watcher recibe el servicio resuelto, sea posicional o por nombre.
        recibido = (
            ctor_watcher.call_args.kwargs.get("embedding_service")
            or ctor_watcher.call_args.args[1]
        )
        assert recibido is servicio_configurado

    @pytest.mark.asyncio
    async def test_should_refuse_when_the_corpus_was_embedded_with_another_model(self):
        """La guarda de RAG.9 tiene que correr **antes de escribir**, no en el chat.

        Hasta FIX.4 solo corría al responder una pregunta. Una carga podía meter un segundo
        espacio vectorial en un corpus existente y nadie se enteraba hasta que alguien
        preguntaba — con la ingesta entera ya pagada y el corpus repartido entre dos
        espacios cuyo coseno no significa nada.
        """
        from server.app.modules.agents_hub.ingestion.corpus import load
        from server.app.modules.agents_hub.services.embedding_space import (
            EmbeddingSpaceMismatch,
        )

        session = AsyncMock()
        session.get = AsyncMock(return_value=MagicMock(organizacion_id=uuid.uuid4()))

        fabrica = MagicMock()
        fabrica.return_value.__aenter__ = AsyncMock(return_value=session)
        fabrica.return_value.__aexit__ = AsyncMock(return_value=False)

        fuente = MagicMock()
        fuente.list_entries = AsyncMock(return_value=[])

        reconciliador = MagicMock()
        reconciliador.reconcile = AsyncMock()

        args = argparse.Namespace(
            dir=Path("corpus"), manifest=None, chatbot_ids=[uuid.uuid4()], dry_run=False,
            census=False, prune=False, force_prune=False, prune_threshold=0.10,
            verbose=False,
        )

        with (
            patch.object(load, "LocalDirectorySource", return_value=fuente),
            patch.object(load, "assert_vocabulary", AsyncMock()),
            patch.object(load, "CorpusReconciler", return_value=reconciliador),
            patch(
                "server.app.modules.agents_hub.database.connection.create_async_engine",
                return_value=MagicMock(dispose=AsyncMock()),
            ),
            patch(
                "server.app.modules.agents_hub.database.connection.create_session_factory",
                return_value=fabrica,
            ),
            patch(
                "server.app.modules.agents_hub.services.embedding_resolver."
                "resolve_embedding_service",
                AsyncMock(return_value=MagicMock(model_name="google/text-embedding")),
            ),
            patch(
                "server.app.modules.agents_hub.services.embedding_space."
                "assert_embedding_space_matches",
                AsyncMock(side_effect=EmbeddingSpaceMismatch("BAAI/bge-m3 (1024)")),
            ) as guarda,
        ):
            codigo = await load._run(args)

        guarda.assert_awaited()
        assert codigo != 0, "una carga sobre otro espacio vectorial no puede salir con 0"
        reconciliador.reconcile.assert_not_awaited()
        session.commit.assert_not_awaited()

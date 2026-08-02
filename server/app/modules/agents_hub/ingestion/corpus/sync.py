"""CLI de sincronización con el sistema de publicación (SYNC.1). Deploy: edge.

Uso:
    uv run python -m server.app.modules.agents_hub.ingestion.corpus.sync \
        --chatbot-id <uuid> [--dry-run] [--prune] [--delta]

Hermana de `load.py`: misma reconciliación, otra fuente. `load` lee una carpeta local —el
mecanismo de mantenimiento mientras no exista el pipeline de publicación—; esta lee los dos
datasets del servicio MCP. Todo lo demás (emparejamiento, deltas, poda, salvaguarda de
proporción, job) es del reconciliador de ING.0.5 y no se duplica.

**No se engancha a ningún scheduler.** Es la misma decisión que en RAG.14: cuándo se
sincroniza es operativa, y automatizarla antes de haber visto el informe de una pasada real
es decidir a ciegas.

Configuración por entorno (`.env.example` y `scripts/generate_env.sh`):

    PUBLICATION_MCP_URL         extremo JSON-RPC del servicio
    PUBLICATION_DATASET_INDEX   código del dataset de índice (censo)
    PUBLICATION_DATASET_CONTENT código del dataset de contenido
    PUBLICATION_DATASET_TOKEN   token del dataset — secreto, nunca en logs
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid

# `langchain_text_splitters` arrastra torch, y en Windows cargarlo DESPUÉS de abrir una
# conexión asyncpg aborta el proceso. Mismo orden forzado que en `load.py`.
from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker  # noqa: F401

from server.app.modules.agents_hub.ingestion.corpus.manifest import (
    CorpusValidationError,
    assert_vocabulary,
)
from server.app.modules.agents_hub.ingestion.corpus.publication_client import (
    PublicationMcpClient,
    PublicationSyncError,
)
from server.app.modules.agents_hub.ingestion.corpus.publication_source import (
    PublicationMcpSource,
)
from server.app.modules.agents_hub.ingestion.corpus.reconciler import (
    UMBRAL_PODA_POR_DEFECTO,
    CorpusReconciler,
    PruneThresholdExceeded,
)

VARIABLES = (
    "PUBLICATION_MCP_URL",
    "PUBLICATION_DATASET_INDEX",
    "PUBLICATION_DATASET_CONTENT",
    "PUBLICATION_DATASET_TOKEN",
)


def _configuracion() -> dict[str, str]:
    valores = {nombre: os.environ.get(nombre, "").strip() for nombre in VARIABLES}
    if faltan := [nombre for nombre, valor in valores.items() if not valor]:
        raise PublicationSyncError(
            "Faltan variables de entorno para sincronizar: " + ", ".join(faltan)
        )
    return valores


async def _run(args: argparse.Namespace) -> int:
    from server.app.modules.agents_hub.database.config_models import HubChatbot
    from server.app.modules.agents_hub.database.connection import (
        create_async_engine,
        create_session_factory,
    )
    from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher
    from server.app.modules.agents_hub.services.config_provider import LocalConfigProvider
    from server.app.modules.agents_hub.services.embedding_service import (
        LocalEmbeddingService,
    )
    from server.app.modules.agents_hub.services.vocabulary_service import VocabularyService

    try:
        config = _configuracion()
    except PublicationSyncError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    fuente = PublicationMcpSource(
        PublicationMcpClient(
            url=config["PUBLICATION_MCP_URL"],
            token=config["PUBLICATION_DATASET_TOKEN"],
        ),
        index_dataset=config["PUBLICATION_DATASET_INDEX"],
        content_dataset=config["PUBLICATION_DATASET_CONTENT"],
        # `--delta` declara que el dataset de índice trae solo lo modificado en los últimos
        # N días. Entonces no es censo, y el reconciliador no poda: correcto, porque un
        # delta no distingue «retirada» de «no tocada».
        is_census_declared=not args.delta,
    )

    engine = create_async_engine()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            chatbot = await session.get(HubChatbot, args.chatbot_id)
            if chatbot is None:
                print(f"ERROR: no existe el chatbot {args.chatbot_id}", file=sys.stderr)
                return 1

            try:
                entradas = await fuente.list_entries()
            except (PublicationSyncError, CorpusValidationError) as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1
            print(f"{len(entradas)} entradas en el indice de publicacion")

            provider = LocalConfigProvider(session)
            vocabulario = VocabularyService(
                source=provider, organizacion_id=chatbot.organizacion_id
            )
            try:
                await assert_vocabulary(entradas, vocabulario)
            except CorpusValidationError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1

            reconciler = CorpusReconciler(
                session,
                IngestionWatcher(
                    session, LocalEmbeddingService(), chatbot_provider=provider
                ),
            )
            try:
                informe = await reconciler.reconcile(
                    fuente,
                    args.chatbot_id,
                    dry_run=args.dry_run,
                    prune=args.prune,
                    force_prune=args.force_prune,
                    prune_threshold=args.prune_threshold,
                )
            except PruneThresholdExceeded as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 2
            except PublicationSyncError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1

            if args.verbose:
                for linea in informe.detalle:
                    print(f"  {linea}")
            for motivo in informe.motivos_omision:
                print(f"  omitido: {motivo}")
            if informe.poda_omitida_por_no_censo:
                print("  aviso: --prune ignorado porque --delta no es un censo")

            if args.dry_run:
                print(f"[dry-run] {informe.render()} (nada escrito)")
            else:
                await session.commit()
                print(informe.render())
    finally:
        await engine.dispose()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sincroniza el corpus de un chatbot con el servicio de publicacion."
    )
    parser.add_argument("--chatbot-id", required=True, type=uuid.UUID, dest="chatbot_id")
    parser.add_argument("--dry-run", action="store_true", help="Plan sin escribir")
    parser.add_argument(
        "--delta",
        action="store_true",
        help="El indice trae solo lo modificado: no es censo y por tanto no habilita poda",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Marca como retirado lo que el censo no vio. Nunca borra",
    )
    parser.add_argument(
        "--force-prune", action="store_true", dest="force_prune",
        help="Confirma una poda por encima del umbral",
    )
    parser.add_argument(
        "--prune-threshold", type=float, default=UMBRAL_PODA_POR_DEFECTO,
        dest="prune_threshold",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Detalle por documento")
    args = parser.parse_args(argv)

    if args.prune and args.delta:
        print(
            "AVISO: --prune con --delta no retira nada. Es deliberado: un delta no puede "
            "distinguir «retirada» de «no tocada».",
            file=sys.stderr,
        )
    return asyncio.run(_run(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

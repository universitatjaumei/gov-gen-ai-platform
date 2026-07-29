"""CLI de carga y mantenimiento del corpus curado (ING.0.5). Deploy: edge.

Uso:
    uv run python -m server.app.modules.agents_hub.ingestion.corpus.load \
        --dir <carpeta de .md> --chatbot-id <uuid> [--dry-run]

**No es una carga inicial: es el mecanismo de mantenimiento del corpus** mientras no exista
el pipeline de publicación. La misma orden sobre la misma carpeta omite lo no cambiado,
actualiza metadatos sin re-trocear y re-ingiere solo lo modificado. Lo incremental no es un
modo: emerge del hash.

El censo sí es un modo, y es peligroso. `--prune` solo retira si la fuente declara corpus
completo (`--census`), y aborta si la poda pasa del umbral:

    --census            estas entradas son el corpus COMPLETO
    --prune             marca lo que el censo no vio (NUNCA borra)
    --force-prune       confirma una poda por encima del umbral
    --prune-threshold   proporción a partir de la cual hace falta confirmar (default 0,10)
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

# `langchain_text_splitters` arrastra torch, y en Windows cargarlo DESPUÉS de abrir una
# conexión asyncpg aborta el proceso con un access violation. Importar el chunker aquí
# arriba fuerza el orden correcto antes de que se cree el motor de BD.
from server.app.modules.agents_hub.ingestion.chunker import MarkdownChunker  # noqa: F401

from server.app.modules.agents_hub.ingestion.corpus.manifest import (
    CorpusValidationError,
    assert_vocabulary,
    load_manifest,
)
from server.app.modules.agents_hub.ingestion.corpus.reconciler import (
    UMBRAL_PODA_POR_DEFECTO,
    CorpusReconciler,
    PruneThresholdExceeded,
)
from server.app.modules.agents_hub.ingestion.corpus.source import LocalDirectorySource


async def _run(args: argparse.Namespace) -> int:
    from server.app.modules.agents_hub.database.config_models import HubChatbot
    from server.app.modules.agents_hub.database.connection import (
        create_async_engine,
        create_session_factory,
    )
    from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher
    from server.app.modules.agents_hub.services.config_provider import (
        LocalConfigProvider,
    )
    from server.app.modules.agents_hub.services.embedding_service import (
        LocalEmbeddingService,
    )
    from server.app.modules.agents_hub.services.vocabulary_service import (
        VocabularyService,
    )

    manifiesto = load_manifest(args.manifest) if args.manifest else None
    fuente = LocalDirectorySource(
        args.dir, manifest=manifiesto, is_census_declared=args.census
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
            except CorpusValidationError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1
            print(f"{len(entradas)} entradas leidas de {args.dir}")

            # Vocabulario: el error enumera TODOS los códigos malos, no el primero.
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
                    session,
                    LocalEmbeddingService(),
                    chatbot_provider=provider,
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

            if args.verbose:
                for linea in informe.detalle:
                    print(f"  {linea}")
            for motivo in informe.motivos_omision:
                print(f"  omitido: {motivo}")
            if informe.poda_omitida_por_no_censo:
                print(
                    "  aviso: --prune ignorado porque la fuente no declara censo "
                    "(anade --census si estas cargando el corpus completo)"
                )

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
        description="Carga y mantiene el corpus curado de un chatbot."
    )
    parser.add_argument("--dir", required=True, type=Path, help="Carpeta con los .md")
    parser.add_argument(
        "--manifest", type=Path, help="Manifiesto (opcional si hay front-matter)"
    )
    parser.add_argument(
        "--chatbot-id", required=True, type=uuid.UUID, dest="chatbot_id"
    )
    parser.add_argument("--dry-run", action="store_true", help="Plan sin escribir")
    parser.add_argument(
        "--census",
        action="store_true",
        help="Estas entradas son el corpus COMPLETO (requisito para --prune)",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Marca como retirado lo que el censo no vio. Nunca borra",
    )
    parser.add_argument(
        "--force-prune",
        action="store_true",
        dest="force_prune",
        help="Confirma una poda por encima del umbral",
    )
    parser.add_argument(
        "--prune-threshold",
        type=float,
        default=UMBRAL_PODA_POR_DEFECTO,
        dest="prune_threshold",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Detalle por fichero")
    args = parser.parse_args(argv)

    if args.prune and not args.census:
        print(
            "AVISO: --prune sin --census no retira nada. Es deliberado: una carga "
            "parcial no puede distinguir «retirada» de «no incluida».",
            file=sys.stderr,
        )
    return asyncio.run(_run(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

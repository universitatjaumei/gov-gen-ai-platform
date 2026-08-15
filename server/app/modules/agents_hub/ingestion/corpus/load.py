"""CLI de carga y mantenimiento del corpus curado (ING.0.5). Deploy: edge.

Uso:
    uv run python -m server.app.modules.agents_hub.ingestion.corpus.load \
        --dir <carpeta de .md> --chatbot-id <uuid> [--chatbot-id <uuid> ...] [--dry-run]

**`--chatbot-id` es repetible** (DER.1): el mismo corpus se carga en varios asistentes en una
sola pasada. Se lee, parsea y valida **una vez** —lo que garantiza que todos reciben
exactamente lo mismo, cosa que dos ejecuciones seguidas no garantizan si alguien toca un
fichero a mitad—; lo que se repite es la reconciliación, que es lo único que depende del
destino. Cada asistente embebe con **su** modelo, que es la libertad por la que se descartó
compartir el corpus entre chatbots (bloque COR).

Todos han de ser de la misma organización, y se comprueba antes de escribir nada.

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

# `langchain_text_splitters` arrastra torch cuando el extra [local-models] está instalado, y
# en Windows cargarlo DESPUÉS de abrir una conexión asyncpg aborta el proceso con un access
# violation. `IngestionWatcher` construye un chunker con la sesión ya abierta, así que el
# orden hay que forzarlo aquí.
#
# **Se importa el splitter y no el chunker**: hasta D.4.0 bastaba con importar
# `MarkdownChunker`, porque el módulo cargaba el splitter al importarse. D.4.0 movió ese
# import dentro del constructor —para que un despliegue sin modelos locales no pague la
# pila— y con ello dejó esta precarga sin efecto, sin que el comentario lo dijera: la CLI
# volvió a morir con SIGSEGV. Importar aquí lo que de verdad arrastra torch es lo que hace
# la garantía comprobable, y `test_corpus_load_embedding_provider.py` la fija.
import langchain_text_splitters  # noqa: F401

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


def progreso_por_consola(actual: int, total: int | None, mensaje: str) -> None:
    """Reporte de progreso para la carga masiva (RAG.12).

    Es el mismo `progress_callback` que consume el watcher para escribir la fila del job:
    una sola forma de contar el progreso, y no dos que se contradigan. `total` es None hasta
    que se trocea —antes no se sabe—, y ahí se muestra `?` en vez de inventar un cero.
    """
    print(f"  [{actual}/{total if total is not None else '?'}] {mensaje}", flush=True)


async def _run(args: argparse.Namespace) -> int:
    # La CLI no pasa por FastAPI, así que nadie ha cargado `server/.env`: sólo lo hace
    # `core.config`, al importarse. Sin esta línea la orden aborta diciendo que falta
    # `GOOGLE_CLOUD_PROJECT` **cuando está definida en el fichero que la aplicación sí lee**
    # —un error a la vez cierto y engañoso, que manda a buscar el problema donde no está—.
    from server.app.core import config  # noqa: F401
    from sqlalchemy import select

    from server.app.modules.agents_hub.database.config_models import HubChatbot
    from server.app.modules.agents_hub.database.connection import (
        create_async_engine,
        create_session_factory,
    )
    from server.app.modules.agents_hub.ingestion.watcher import IngestionWatcher
    from server.app.modules.agents_hub.services.config_provider import (
        LocalConfigProvider,
    )
    from server.app.modules.agents_hub.services.embedding_resolver import (
        resolve_embedding_service,
    )
    from server.app.modules.agents_hub.services.embedding_space import (
        EmbeddingSpaceMismatch,
        assert_embedding_space_matches,
    )
    from server.app.modules.agents_hub.services.vocabulary_service import (
        VocabularyService,
    )
    from server.app.modules.agents_hub.ingestion.divergence_detector import (
        detectar_divergencias,
        render_divergencias,
    )

    manifiesto = load_manifest(args.manifest) if args.manifest else None
    fuente = LocalDirectorySource(
        args.dir, manifest=manifiesto, is_census_declared=args.census
    )

    engine = create_async_engine()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            # ── Fase 1: comprobar. Nada de esto escribe. ──────────────────────────────
            #
            # DER.1: todas las comprobaciones van ANTES de la primera carga, y no una por
            # una justo antes de cada asistente. Si el segundo tiene el corpus en otro
            # espacio vectorial, descubrirlo con el primero ya cargado deja una pasada que
            # no se puede repetir limpia: hay que deshacer a mano.
            chatbots = {}
            for chatbot_id in args.chatbot_ids:
                chatbot = await session.get(HubChatbot, chatbot_id)
                if chatbot is None:
                    print(f"ERROR: no existe el chatbot {chatbot_id}", file=sys.stderr)
                    return 1
                chatbots[chatbot_id] = chatbot

            organizaciones = {c.organizacion_id for c in chatbots.values()}
            if len(organizaciones) > 1:
                print(
                    "ERROR: los chatbots indicados son de organizaciones distintas "
                    f"({', '.join(str(o) for o in sorted(map(str, organizaciones)))}). "
                    "Una misma carga no puede repartir corpus curado entre "
                    "administraciones: revisa los --chatbot-id.",
                    file=sys.stderr,
                )
                return 1
            organizacion_id = organizaciones.pop()

            try:
                entradas = await fuente.list_entries()
            except CorpusValidationError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1
            print(f"{len(entradas)} entradas leidas de {args.dir}")

            # Vocabulario: el error enumera TODOS los códigos malos, no el primero. Se
            # valida una sola vez porque el vocabulario es de la organización, que ya
            # sabemos que es una.
            provider = LocalConfigProvider(session)
            vocabulario = VocabularyService(
                source=provider, organizacion_id=organizacion_id
            )
            try:
                await assert_vocabulary(entradas, vocabulario)
            except CorpusValidationError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1

            # FIX.4: el servicio sale de la configuración vigente (MOD.2), no de un import.
            # Cablear aquí el local significaba embeber el corpus con BGE-M3 aunque el
            # despliegue estuviera configurado con Google —y descubrirlo en la primera
            # consulta de chat, cuando la guarda de RAG.9 comparase espacios vectoriales—.
            #
            # Se resuelve por chatbot: que cada asistente pueda elegir su modelo es
            # exactamente la libertad por la que se descartó compartir el corpus (COR).
            servicios = {}
            for chatbot_id in args.chatbot_ids:
                servicio = await resolve_embedding_service(session, chatbot_id)
                servicios[chatbot_id] = servicio
                print(f"embeddings de {chatbot_id}: {servicio.model_name}")
                try:
                    await assert_embedding_space_matches(session, chatbot_id, servicio)
                except EmbeddingSpaceMismatch as exc:
                    print(f"ERROR: {exc}", file=sys.stderr)
                    return 3

            # ── Fase 2: cargar, un asistente cada vez. ────────────────────────────────
            #
            # Se confirma por asistente y no al final: la reconciliación es incremental, así
            # que conservar lo que sí funcionó hace que repetir la pasada solo rehaga lo que
            # falta. Tirarlo todo por un fallo en el último obligaría a re-embeber corpus ya
            # embebido, que es la parte cara.
            primer_fallo = 0
            for chatbot_id in args.chatbot_ids:
                print(f"--- {chatbot_id} ---")
                reconciler = CorpusReconciler(
                    session,
                    IngestionWatcher(
                        session,
                        servicios[chatbot_id],
                        chatbot_provider=provider,
                    ),
                )
                try:
                    informe = await reconciler.reconcile(
                        fuente,
                        chatbot_id,
                        dry_run=args.dry_run,
                        prune=args.prune,
                        force_prune=args.force_prune,
                        prune_threshold=args.prune_threshold,
                    )
                except PruneThresholdExceeded as exc:
                    print(f"ERROR en {chatbot_id}: {exc}", file=sys.stderr)
                    primer_fallo = primer_fallo or 2
                    continue

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

            # DER.2: cargar en A no toca a B. Si B se quedó con la versión anterior de una
            # norma, este es el momento en que se puede decir —y el único en que alguien
            # está mirando—. Se compara contra TODOS los chatbots de la organización, no
            # solo contra los de esta pasada: los que faltan son precisamente el problema.
            #
            # No se propaga nada automáticamente: cada asistente tiene su receta de embedding
            # y su calendario, y propagar en silencio es cómo se reembebe un corpus sin que
            # nadie lo haya pedido.
            de_la_organizacion = list(
                (
                    await session.execute(
                        select(HubChatbot.id).where(
                            HubChatbot.organizacion_id == organizacion_id
                        )
                    )
                ).scalars().all()
            )
            divergencias = await detectar_divergencias(session, de_la_organizacion)
            if divergencias:
                print(render_divergencias(divergencias))
                print(
                    "  (recarga los chatbots atrasados con --chatbot-id; nada se propaga "
                    "solo)"
                )
    finally:
        await engine.dispose()
    return primer_fallo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Carga y mantiene el corpus curado de un chatbot."
    )
    parser.add_argument("--dir", required=True, type=Path, help="Carpeta con los .md")
    parser.add_argument(
        "--manifest", type=Path, help="Manifiesto (opcional si hay front-matter)"
    )
    parser.add_argument(
        "--chatbot-id",
        required=True,
        type=uuid.UUID,
        action="append",
        dest="chatbot_ids",
        metavar="UUID",
        help=(
            "Chatbot destino. Repetible: --chatbot-id A --chatbot-id B carga el mismo "
            "corpus en los dos en una sola pasada. Todos han de ser de la misma "
            "organizacion"
        ),
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

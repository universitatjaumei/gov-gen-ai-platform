"""Comando de detección de huecos de corpus (RAG.14). Deploy: edge.

    uv run python -m server.app.modules.agents_hub.ingestion.quality.detect_gaps \
        --chatbot-id <uuid> [--dry-run] [--dias 30] [--min-cluster 3]

**No se engancha al scheduler periódico de 9Q en este prompt**, y es deliberado: el
scheduler arranca hoy con los detectores vacíos, y decidir cada cuánto se revisan las
conversaciones de los usuarios es una decisión operativa —tiene coste de embeddings y llena
una cola que alguien tiene que atender—, no una consecuencia técnica de que el detector
exista.
"""
from __future__ import annotations

import argparse
import asyncio
import uuid


async def _main(args: argparse.Namespace) -> None:
    from server.app.modules.agents_hub.database.connection import (
        create_session_factory,
        get_engine,
    )
    from server.app.modules.agents_hub.ingestion.quality.gap_detector import (
        analizar_huecos,
        detectar_huecos,
        render_huecos,
    )
    from server.app.modules.agents_hub.services.embedding_resolver import (
        resolve_embedding_service,
    )

    chatbot_id = uuid.UUID(args.chatbot_id)
    async with create_session_factory(get_engine())() as session:
        servicio = await resolve_embedding_service(session, chatbot_id)
        huecos = await detectar_huecos(
            session,
            chatbot_id,
            servicio,
            dias=args.dias,
            min_cluster_size=args.min_cluster,
        )
        print(f"Chatbot {chatbot_id} -> {len(huecos)} huecos en {args.dias} dias")
        print(render_huecos(huecos))

        if args.dry_run:
            print("[dry-run] nada escrito")
            return

        vivos = await analizar_huecos(
            session,
            chatbot_id,
            servicio,
            dias=args.dias,
            min_cluster_size=args.min_cluster,
        )
        await session.commit()
        print(f"  -> {vivos} hallazgos en la cola de revision")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detecta huecos de corpus a partir de conversaciones que salieron mal."
    )
    parser.add_argument("--chatbot-id", required=True)
    parser.add_argument("--dias", type=int, default=30)
    parser.add_argument("--min-cluster", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    asyncio.run(_main(parser.parse_args()))


if __name__ == "__main__":
    main()

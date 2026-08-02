"""Comando de detección de revisiones vencidas (SYNC.2). Deploy: edge.

    uv run python -m server.app.modules.agents_hub.ingestion.quality.detect_stale \
        --chatbot-id <uuid> [--dry-run]

**No se engancha al scheduler periódico de 9Q**, igual que RAG.14 y SYNC.1. Cada cuánto se
revisa la caducidad es una decisión operativa —llena una cola que alguien tiene que
atender—, no una consecuencia técnica de que el detector exista.
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
    from server.app.modules.agents_hub.ingestion.quality.staleness_detector import (
        analizar_caducidad,
        detectar_caducados,
        render_caducados,
    )

    chatbot_id = uuid.UUID(args.chatbot_id)
    async with create_session_factory(get_engine())() as session:
        caducados = await detectar_caducados(session, chatbot_id)
        print(render_caducados(caducados))

        if args.dry_run:
            print("\n[dry-run] no se ha escrito ningun hallazgo.")
            return

        cuantos = await analizar_caducidad(session, chatbot_id)
        await session.commit()
        print(f"\n{cuantos} hallazgo(s) de revision vencida en la cola.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Detecta documentos cuya fecha de revision prevista ha vencido."
    )
    parser.add_argument("--chatbot-id", required=True, dest="chatbot_id")
    parser.add_argument(
        "--dry-run", action="store_true", help="Enumera sin escribir en la cola"
    )
    asyncio.run(_main(parser.parse_args(argv)))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

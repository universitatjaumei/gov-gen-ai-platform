"""Backfill language field for all existing HubDocumentChunks.

Run once after migration d4e5f6a7b8c9 to re-detect the language of existing
chunks that were ingested with the old default ("es").

Usage:
    python -m server.scripts.backfill_chunk_language
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from server.app.core.config import settings
from server.app.modules.agents_hub.agent.language_detector import detect_language
from server.app.modules.agents_hub.database.operational_models import HubDocumentChunk

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BATCH_SIZE = 200


async def backfill() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        result = await session.execute(select(HubDocumentChunk))
        chunks = result.scalars().all()

    logger.info("Found %d chunks to process", len(chunks))
    updated = 0

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        async with session_factory() as session:
            for chunk in batch:
                detected = detect_language(chunk.content)
                if chunk.language != detected:
                    chunk_db = await session.get(HubDocumentChunk, chunk.id)
                    if chunk_db:
                        chunk_db.language = detected
                        updated += 1
            await session.commit()
        logger.info("Processed %d / %d", min(i + BATCH_SIZE, len(chunks)), len(chunks))

    logger.info("Done — updated %d chunks", updated)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(backfill())

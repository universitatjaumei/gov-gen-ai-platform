"""
Migration to add diff-related columns to WebWatcherConfig and WebWatcherHistory.
Enables detailed content capture and diff visualization.
"""
import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from client_app.app.database.db import client_engine as engine
from sqlalchemy import text


async def migrate():
    print("Migrating WebWatcher tables: Adding diff-related columns...")

    async with engine.begin() as conn:
        # --- WebWatcherConfig ---
        result = await conn.execute(text("PRAGMA table_info(webwatcherconfig)"))
        existing_columns = {row[1] for row in result.fetchall()}

        if "last_content_text" not in existing_columns:
            print("Adding last_content_text column to webwatcherconfig")
            await conn.execute(text("ALTER TABLE webwatcherconfig ADD COLUMN last_content_text TEXT"))
        else:
            print("Column last_content_text already exists in webwatcherconfig.")

        if "last_content_html" not in existing_columns:
            print("Adding last_content_html column to webwatcherconfig")
            await conn.execute(text("ALTER TABLE webwatcherconfig ADD COLUMN last_content_html TEXT"))
        else:
            print("Column last_content_html already exists in webwatcherconfig.")

        if "capture_detailed_content" not in existing_columns:
            print("Adding capture_detailed_content column to webwatcherconfig")
            await conn.execute(text("ALTER TABLE webwatcherconfig ADD COLUMN capture_detailed_content BOOLEAN DEFAULT 0"))
        else:
            print("Column capture_detailed_content already exists in webwatcherconfig.")

        # --- WebWatcherHistory ---
        result = await conn.execute(text("PRAGMA table_info(webwatcherhistory)"))
        existing_columns = {row[1] for row in result.fetchall()}

        if "diff_text" not in existing_columns:
            print("Adding diff_text column to webwatcherhistory")
            await conn.execute(text("ALTER TABLE webwatcherhistory ADD COLUMN diff_text TEXT"))
        else:
            print("Column diff_text already exists in webwatcherhistory.")

        if "diff_html" not in existing_columns:
            print("Adding diff_html column to webwatcherhistory")
            await conn.execute(text("ALTER TABLE webwatcherhistory ADD COLUMN diff_html TEXT"))
        else:
            print("Column diff_html already exists in webwatcherhistory.")

    print("Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())

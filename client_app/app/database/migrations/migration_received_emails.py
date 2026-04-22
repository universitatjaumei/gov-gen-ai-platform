"""
Migration to create the received_emails table.
Stores processed emails from EmailScan and EmailWatcher for later analysis.
"""
import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from client_app.app.database.db import client_engine as engine
from sqlalchemy import text


async def migrate():
    print("Migrating: Creating received_emails table...")

    async with engine.begin() as conn:
        # Check if table already exists
        result = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='receivedemail'")
        )
        table_exists = result.fetchone() is not None

        if table_exists:
            print("Table receivedemail already exists. Skipping creation.")
        else:
            print("Creating receivedemail table...")
            await conn.execute(text("""
                CREATE TABLE receivedemail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id VARCHAR NOT NULL UNIQUE,
                    source VARCHAR NOT NULL,
                    sender VARCHAR NOT NULL,
                    subject VARCHAR NOT NULL,
                    date DATETIME NOT NULL,
                    body_plain TEXT DEFAULT '',
                    body_html TEXT,
                    attachments_info TEXT DEFAULT '[]',
                    is_processed BOOLEAN DEFAULT 0,
                    created_at DATETIME NOT NULL
                )
            """))
            print("Table receivedemail created successfully.")

            # Create index on message_id for faster lookups
            print("Creating index on message_id...")
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_receivedemail_message_id ON receivedemail (message_id)"
            ))

            # Create index on date for date range queries
            print("Creating index on date...")
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_receivedemail_date ON receivedemail (date)"
            ))

            # Create index on source for filtering by origin
            print("Creating index on source...")
            await conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_receivedemail_source ON receivedemail (source)"
            ))

    print("Migration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())

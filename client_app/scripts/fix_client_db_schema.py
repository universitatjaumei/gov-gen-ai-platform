
import sys
import os
import asyncio
from sqlmodel import text
from sqlmodel.ext.asyncio.session import AsyncSession

# Add root to path
sys.path.append(os.getcwd())

from client_app.app.database.db import client_engine

async def fix_client_schema():
    print("Checking CustomScript schema in client_local.db...")
    async with AsyncSession(client_engine) as session:
        try:
            # Check ui_contract
            try:
                await session.exec(text("SELECT ui_contract FROM customscript LIMIT 1"))
                print("Column 'ui_contract' already exists.")
            except Exception:
                print("Adding 'ui_contract'...")
                await session.exec(text("ALTER TABLE customscript ADD COLUMN ui_contract JSON"))
                print("Added.")

            # Check execution_mode
            try:
                await session.exec(text("SELECT execution_mode FROM customscript LIMIT 1"))
                print("Column 'execution_mode' already exists.")
            except Exception:
                print("Adding 'execution_mode'...")
                await session.exec(text("ALTER TABLE customscript ADD COLUMN execution_mode VARCHAR DEFAULT 'local'"))
                print("Added.")

            # Check visualization_config
            try:
                await session.exec(text("SELECT visualization_config FROM customscript LIMIT 1"))
                print("Column 'visualization_config' already exists.")
            except Exception:
                print("Adding 'visualization_config'...")
                await session.exec(text("ALTER TABLE customscript ADD COLUMN visualization_config JSON"))
                print("Added.")

            # Check script_path
            try:
                await session.exec(text("SELECT script_path FROM customscript LIMIT 1"))
                print("Column 'script_path' already exists.")
            except Exception:
                print("Adding 'script_path'...")
                await session.exec(text("ALTER TABLE customscript ADD COLUMN script_path VARCHAR"))
                print("Added.")

            # Check doc_path
            try:
                await session.exec(text("SELECT doc_path FROM customscript LIMIT 1"))
                print("Column 'doc_path' already exists.")
            except Exception:
                print("Adding 'doc_path'...")
                await session.exec(text("ALTER TABLE customscript ADD COLUMN doc_path VARCHAR"))
                print("Added.")

            # Check data_contract
            try:
                await session.exec(text("SELECT data_contract FROM customscript LIMIT 1"))
                print("Column 'data_contract' already exists.")
            except Exception:
                print("Adding 'data_contract'...")
                await session.exec(text("ALTER TABLE customscript ADD COLUMN data_contract JSON"))
                print("Added.")

            # === PROMPT 8 CORRECTION: Create script_library table ===
            try:
                await session.exec(text("SELECT id FROM script_library LIMIT 1"))
                print("Table 'script_library' already exists.")
            except Exception:
                print("Creating 'script_library' table...")
                await session.exec(text("""
                    CREATE TABLE script_library (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_module VARCHAR NOT NULL,
                        name VARCHAR NOT NULL,
                        description TEXT,
                        tags JSON,
                        script_path VARCHAR NOT NULL,
                        doc_path VARCHAR,
                        code_hash VARCHAR NOT NULL,
                        ui_contract JSON,
                        data_contract JSON,
                        execution_mode VARCHAR DEFAULT 'local',
                        visualization_config JSON,
                        source_automation_id INTEGER,
                        source_metadata JSON,
                        user_prompt TEXT,
                        status VARCHAR DEFAULT 'draft',
                        validation_errors TEXT,
                        execution_count INTEGER DEFAULT 0,
                        success_count INTEGER DEFAULT 0,
                        last_executed TIMESTAMP,
                        avg_execution_time_ms INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by VARCHAR,
                        is_favorite BOOLEAN DEFAULT 0
                    )
                """))
                print("Table created.")
                
                # Create indexes
                await session.exec(text("CREATE INDEX idx_script_library_source_module ON script_library(source_module)"))
                await session.exec(text("CREATE INDEX idx_script_library_name ON script_library(name)"))
                await session.exec(text("CREATE INDEX idx_script_library_status ON script_library(status)"))
                print("Indexes created.")

            await session.commit()
            print("Client DB schema update complete.")

        except Exception as e:
            print(f"Error updating schema: {e}")
            raise e

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_client_schema())

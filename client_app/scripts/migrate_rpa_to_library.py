
import asyncio
import sys
from pathlib import Path

# Adjust path to find modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.database.db import client_engine
from client_app.app.database.models import RpaPlaybook
from client_app.app.services.rpa_library_sync import rpa_sync_service

async def migrate_existing_rpa_playbooks():
    """
    Migra playbooks RPA existentes a ScriptLibrary
    - Lee todos los RpaPlaybook
    - Crea entradas en ScriptLibrary
    - Genera archivos JSON y README.md
    """
    print("Starting RPA Playbook Migration...")
    
    async with AsyncSession(client_engine) as session:
        # Obtener todos los playbooks
        result = await session.execute(select(RpaPlaybook))
        playbooks = result.scalars().all()
        
        count = 0
        for playbook in playbooks:
            print(f"Migrating Playbook: {playbook.name} (ID: {playbook.id})")
            try:
                # Sincronizar
                entry = await rpa_sync_service.sync_playbook_to_library(playbook)
                print(f" -> Synced to Library ID: {entry.id}")
                count += 1
            except Exception as e:
                print(f"Error migrating playbook {playbook.id}: {e}")
            
        print(f"Migration Complete. Migrated {count}/{len(playbooks)} playbooks.")

if __name__ == "__main__":
    asyncio.run(migrate_existing_rpa_playbooks())

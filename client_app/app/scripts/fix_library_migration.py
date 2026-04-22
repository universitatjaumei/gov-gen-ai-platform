
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parents[3]))

from client_app.app.database.db import client_engine
from client_app.app.database.models import ScriptLibrary, CustomScript, RpaPlaybook
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.services.script_library_service import script_library_service

async def migrate_data():
    print("Starting Migration: CustomScript/RpaPlaybook -> ScriptLibrary...")
    async with AsyncSession(client_engine) as session:
        # 1. Custom Scripts
        custom_scripts = (await session.execute(select(CustomScript))).scalars().all()
        print(f"Found {len(custom_scripts)} Custom Scripts.")
        
        migrated_cs = 0
        for cs in custom_scripts:
            # Check existence
            exists = (await session.execute(
                select(ScriptLibrary).where(
                    ScriptLibrary.source_module == 'custom',
                    ScriptLibrary.source_automation_id == cs.id
                )
            )).scalars().first()
            
            if not exists:
                print(f"Migrating Custom Script: {cs.name} (ID: {cs.id})")
                try:
                    # Use service to add
                    new_script = await script_library_service.add_script(
                        source_module='custom',
                        name=cs.name,
                        code=cs.code or "",
                        description=cs.description or "",
                        tags=cs.tags,
                        ui_contract=cs.ui_contract,
                        data_contract=cs.data_contract,
                        source_automation_id=cs.id,
                        source_metadata={'execution_mode': cs.execution_mode},
                        user_prompt=cs.user_prompt
                    )
                    # Update status manually after creation (add_script defaults to draft)
                    if cs.status and cs.status != 'draft':
                        new_script.status = cs.status
                        session.add(new_script)
                        await session.commit()
                        
                    migrated_cs += 1
                except Exception as e:
                    print(f"Error migrating {cs.name}: {e}")
            else:
                # Force update status if mismatched
                if cs.status and exists.status != cs.status:
                    print(f"Updating Status for {cs.name}: {exists.status} -> {cs.status}")
                    exists.status = cs.status
                    session.add(exists)
                    await session.commit()
                
        # 2. RPA Playbooks
        playbooks = (await session.execute(select(RpaPlaybook))).scalars().all()
        print(f"Found {len(playbooks)} RPA Playbooks.")
        
        migrated_rpa = 0
        for pb in playbooks:
             exists = (await session.execute(
                select(ScriptLibrary).where(
                    ScriptLibrary.source_module == 'rpa',
                    ScriptLibrary.source_automation_id == pb.id
                )
            )).scalars().first()
             
             if not exists:
                print(f"Migrating RPA Playbook: {pb.name}")
                try:
                    await script_library_service.add_script(
                        source_module='rpa',
                        name=pb.name,
                        code=f"# RPA Playbook: {pb.name}\n# Base URL: {pb.base_url}", # Placeholder code
                        description=pb.description or "RPA Automation",
                        source_automation_id=pb.id,
                        source_metadata={'base_url': pb.base_url},
                        user_prompt="Imported from RPA"
                    )
                    migrated_rpa += 1
                except Exception as e:
                    print(f"Error migrating RPA {pb.name}: {e}")

        print(f"Migration Complete. New Custom Scripts: {migrated_cs}, New RPA: {migrated_rpa}")

if __name__ == "__main__":
    try:
        asyncio.run(migrate_data())
    except Exception as e:
        print(f"Migration Failed: {e}")


import sys
import os
import asyncio
from pathlib import Path
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.ext.asyncio.session import AsyncSession
# from automatia_shared.core.path_manager import _storage_root # Skipping to avoid path hell in script

# Add root to path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'shared')) # Add shared lib

from client_app.app.database.db import client_engine
from client_app.app.database.models import CustomScript

async def migrate_to_hybrid():
    # Define Storage Root
    # Ideally logic should be centralized, but for migration script we define it explicitly or reuse
    storage_root = Path(os.environ.get("STORAGE_ROOT", os.path.join(os.getcwd(), "data", "storage")))
    scripts_dir = storage_root / "scripts" / "src"
    docs_dir = storage_root / "scripts" / "docs"
    
    scripts_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Migration Target: {storage_root}")

    async with AsyncSession(client_engine) as session:
        result = await session.execute(select(CustomScript))
        scripts = result.scalars().all()
        
        print(f"Found {len(scripts)} scripts to migrate.")
        
        for script in scripts:
            if script.script_path and os.path.exists(scripts_dir / script.script_path):
                print(f"Skipping {script.name} (already migrated)")
                continue

            # 1. Migrate Code
            sanitized_name = "".join(x for x in script.name if x.isalnum() or x in (' ', '_', '-')).replace(" ", "_").lower()
            filename_py = f"{script.id}_{sanitized_name}.py"
            file_path_py = scripts_dir / filename_py
            
            if script.code:
                with open(file_path_py, "w", encoding="utf-8") as f:
                    f.write(script.code)
                script.script_path = filename_py
                print(f"Migrated code -> {filename_py}")
            
            # 2. Migrate Description to Doc
            filename_md = f"{script.id}_{sanitized_name}.md"
            file_path_md = docs_dir / filename_md
            
            doc_content = f"# {script.name}\n\n"
            if script.description:
                doc_content += script.description + "\n\n"
            if script.user_prompt:
                doc_content += f"## Original Prompt\n{script.user_prompt}\n"
            
            with open(file_path_md, "w", encoding="utf-8") as f:
                f.write(doc_content)
            
            script.doc_path = filename_md
            print(f"Migrated doc -> {filename_md}")
            
            # 3. Init Data Contract (if missing)
            if not script.data_contract:
                # Basic inference from UI contract if available
                script.data_contract = {"schema_version": "1.0", "fields": script.ui_contract.get("inputs", [])}

            session.add(script)
        
        await session.commit()
        print("Migration complete.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(migrate_to_hybrid())

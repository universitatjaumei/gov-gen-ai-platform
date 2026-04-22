
"""
RPA Library Sync Service
Synchonizes RpaPlaybook (JSON) with ScriptLibrary (Unified Storage).
Handles contract generation and documentation for RPA scripts.
"""

from typing import Dict, Any, List, Optional
import json
from pathlib import Path
from datetime import datetime

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from client_app.app.database.db import client_engine
from client_app.app.database.models import RpaPlaybook, ScriptLibrary
from client_app.app.services.script_library_service import script_library_service

class RPALibrarySyncService:
    """Service to synchronize RPA Playbooks into the unified ScriptLibrary."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def sync_playbook_to_library(self, playbook: RpaPlaybook, session: Optional[AsyncSession] = None) -> Optional[ScriptLibrary]:
        """
        Syncs an RpaPlaybook to ScriptLibrary.
        """
        if session:
            return await self._sync_impl(session, playbook)
        
        async with AsyncSession(client_engine) as session:
            return await self._sync_impl(session, playbook)

    async def _sync_impl(self, session: AsyncSession, playbook: RpaPlaybook) -> Optional[ScriptLibrary]:
        # 1. Generate Content
        playbook_json = json.dumps(playbook.actions, indent=2)
        ui_contract = self._generate_ui_contract(playbook)
        data_contract = self._generate_data_contract(playbook)
        readme = self._generate_readme(playbook)

        stmt = select(ScriptLibrary).where(
            ScriptLibrary.source_module == 'rpa',
            ScriptLibrary.source_automation_id == playbook.id
        )
        result = await session.execute(stmt)
        existing = result.scalars().first()
            
        if existing:
            # Update (Passing session to keep transaction)
            await script_library_service.update_script_from_source(
                source_module='rpa',
                source_id=playbook.id,
                code=playbook_json,
                description=playbook.description,
                name=playbook.name,
                session=session
            )
            
            # Update contracts
            existing.ui_contract = ui_contract
            existing.data_contract = data_contract
            
            # Update doc if changed
            if existing.doc_path:
                try:
                    doc_full_path = Path("data/storage/scripts/docs") / existing.doc_path
                    doc_full_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(doc_full_path, 'w', encoding='utf-8') as f:
                        f.write(readme)
                except Exception as e:
                    print(f"Error updating RPA doc: {e}")

            session.add(existing)
            await session.commit()
            return existing
        
        else:
            # Create New
            new_entry = await script_library_service.add_script(
                source_module='rpa',
                name=playbook.name,
                code=playbook_json,
                description=playbook.description or "RPA Automation",
                tags=['rpa', 'playbook'],
                ui_contract=ui_contract,
                data_contract=data_contract,
                source_automation_id=playbook.id,
                source_metadata={'base_url': playbook.base_url}
            )
            
            # Overwrite the default doc with our full README
            if new_entry.doc_path:
                try:
                    doc_full_path = Path("data/storage/scripts/docs") / new_entry.doc_path
                    with open(doc_full_path, 'w', encoding='utf-8') as f:
                        f.write(readme)
                except: pass
            
            return new_entry

    def _generate_ui_contract(self, playbook: RpaPlaybook) -> Dict[str, Any]:
        """Generates UI Contract for RPA execution."""
        # RPA usually needs:
        # 1. Excel/CSV file (optional, for batch)
        # 2. Headless mode boolean
        return {
            "schema_version": "1.0",
            "inputs": [
                {
                    "name": "input_file",
                    "type": "FILE",
                    "label": "Archivo de Datos (Excel/CSV)",
                    "help": "Sube un archivo para procesar múltiples registros (Batch Mode).",
                    "required": False,
                    "constraints": {"extensions": [".xlsx", ".csv", ".xls"]}
                },
                {
                    "name": "headless",
                    "type": "BOOL",
                    "label": "Ejecución en segundo plano",
                    "default_value": False
                }
            ]
        }

    def _generate_data_contract(self, playbook: RpaPlaybook) -> Dict[str, Any]:
        """Generates Data Contract for Workflow linkage."""
        return {
            "input_schema": {
                "type": "object",
                "properties": {
                    "input_file": {"type": "string", "format": "binary"},
                    "headless": {"type": "boolean"}
                    # Future: Extract variables from playbook actions {{var}}
                }
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "processed_rows": {"type": "integer"},
                    "log_file": {"type": "string"},
                    "output_file": {"type": "string"}
                }
            }
        }

    def _generate_readme(self, playbook: RpaPlaybook) -> str:
        """Generates README.md for the playbook."""
        steps_md = ""
        if playbook.actions:
            for i, step in enumerate(playbook.actions, 1):
                action_type = step.get('action', 'unknown').upper()
                selector = step.get('selector', 'N/A')
                value = step.get('value', '')
                desc = f"{action_type} on `{selector}`"
                if value:
                    desc += f" with value `{value}`"
                steps_md += f"{i}. {desc}\n"
        else:
            steps_md = "_No active steps recorded._"

        return f"""# {playbook.name}

**Tipo**: RPA Web Automation
**URL Base**: {playbook.base_url or 'N/A'}
**ID Original**: {playbook.id}

## Descripción
{playbook.description or 'No description provided.'}

## Pasos del Playbook
{steps_md}

## Ejecución
Este robot puede ejecutarse en modo:
- **Individual**: Una sola ejecución.
- **Batch**: Procesando un archivo Excel fila por fila.

## Requisitos de Datos
- **Entrada (Opcional)**: Archivo Excel con columnas coincidentes con las variables del script.

---
*Generado automáticamente por Gov Gen AI RPA Sync*
"""

rpa_sync_service = RPALibrarySyncService()

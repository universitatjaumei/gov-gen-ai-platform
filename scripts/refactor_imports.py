#!/usr/bin/env python
"""
Script para ayudar en la refactorizacion de imports.

Uso:
    # Ver cambios sin aplicar (dry run)
    python scripts/refactor_imports.py

    # Aplicar cambios
    python scripts/refactor_imports.py --apply
"""
import re
from pathlib import Path

# Mapeo de imports: patron regex -> reemplazo
# Separados por contexto para aplicar correctamente segun la ubicacion del archivo

SHARED_REPLACEMENTS = {
    # Shared - Estos aplican a cualquier archivo
    r'from app\.core\.security import': 'from automatia_shared.core.security import',
    r'from app\.core\.reader import': 'from automatia_shared.core.reader import',
    r'from app\.core\.execution_manager import': 'from automatia_shared.core.execution_manager import',
    r'from app\.core\.i18n import': 'from automatia_shared.core.i18n import',
    r'from app\.core\.pdf_reader import': 'from automatia_shared.core.pdf_reader import',
}

SERVER_REPLACEMENTS = {
    # Server - Para archivos en server/
    r'from app\.database\.db import server_engine': 'from server.app.database.db import server_engine',
    r'from app\.database\.models import AIConfig': 'from server.app.database.models import AIConfig',
    r'from app\.database\.models import TokenLog': 'from server.app.database.models import TokenLog',
    r'from app\.database\.models import ExtractionServiceConfig': 'from server.app.database.models import ExtractionServiceConfig',
    r'from app\.database\.models import ModelPricing': 'from server.app.database.models import ModelPricing',
    r'from app\.database\.models import PartnerAccount': 'from server.app.database.models import PartnerAccount',
    r'from app\.database\.models import ClientAccount': 'from server.app.database.models import ClientAccount',
    r'from app\.database\.models import License': 'from server.app.database.models import License',
    r'from app\.services\.ai_brain import': 'from server.app.services.ai_brain import',
    r'from app\.services\.token_service import': 'from server.app.services.token_service import',
    r'from app\.services\.pricing_service import': 'from server.app.services.pricing_service import',
    r'from app\.services\.model_fetcher import': 'from server.app.services.model_fetcher import',
    r'from app\.services\.agent_service import': 'from server.app.services.agent_service import',
    r'from app\.modules\.brain\.': 'from server.app.modules.brain.',
}

CLIENT_REPLACEMENTS = {
    # Client - Para archivos en client_app/
    r'from app\.database\.db import client_engine': 'from client_app.app.database.db import client_engine',
    r'from app\.database\.models import RpaPlaybook': 'from client_app.app.database.models import RpaPlaybook',
    r'from app\.database\.models import ExtractionLog': 'from client_app.app.database.models import ExtractionLog',
    r'from app\.database\.models import ProviderAPIKey': 'from client_app.app.database.models import ProviderAPIKey',
    r'from app\.database\.models import ServerConnection': 'from client_app.app.database.models import ServerConnection',
    r'from app\.services\.extraction_service import': 'from client_app.app.services.extraction_service import',
    r'from app\.services\.sandbox_service import': 'from client_app.app.services.sandbox_service import',
    r'from app\.services\.api_key_service import': 'from client_app.app.services.api_key_service import',
    r'from app\.core\.state import': 'from client_app.app.core.state import',
    r'from app\.core\.rpa_executor import': 'from client_app.app.core.rpa_executor import',
    r'from app\.core\.exporters import': 'from client_app.app.core.exporters import',
    r'from app\.clients\.brain_client import': 'from client_app.app.clients.brain_client import',
    r'from app\.modules\.privacy\.': 'from client_app.app.modules.privacy.',
    r'from app\.modules\.security\.': 'from client_app.app.modules.security.',
    r'from app\.modules\.extraccion\.': 'from client_app.app.modules.extraccion.',
    r'from app\.ui\.': 'from client_app.app.ui.',
}


def get_replacements_for_path(filepath: Path) -> dict:
    """
    Determina que reemplazos aplicar segun la ubicacion del archivo.
    """
    filepath_str = str(filepath).replace('\\', '/')

    replacements = dict(SHARED_REPLACEMENTS)

    if '/server/' in filepath_str:
        replacements.update(SERVER_REPLACEMENTS)
    elif '/client_app/' in filepath_str:
        replacements.update(CLIENT_REPLACEMENTS)

    return replacements


def refactor_file(filepath: Path, dry_run: bool = True) -> bool:
    """
    Refactoriza imports en un archivo.

    Returns:
        True si hubo cambios, False si no
    """
    try:
        content = filepath.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # Archivo binario o encoding diferente, saltar
        return False

    original = content
    replacements = get_replacements_for_path(filepath)

    for old, new in replacements.items():
        content = re.sub(old, new, content)

    if content != original:
        prefix = '[DRY RUN] ' if dry_run else ''
        print(f"{prefix}Cambios en: {filepath}")

        if not dry_run:
            filepath.write_text(content, encoding='utf-8')

        return True

    return False


def main():
    import sys
    dry_run = "--apply" not in sys.argv

    if dry_run:
        print("=== MODO DRY RUN (usar --apply para aplicar cambios) ===\n")
    else:
        print("=== APLICANDO CAMBIOS ===\n")

    total_changes = 0

    # Buscar archivos Python en server/, client_app/ y shared/
    patterns = [
        "server/**/*.py",
        "client_app/**/*.py",
        "shared/**/*.py",
    ]

    root = Path(".")

    for pattern in patterns:
        for filepath in root.glob(pattern):
            # Saltar __pycache__ y .venv
            if '__pycache__' in str(filepath) or '.venv' in str(filepath):
                continue

            if refactor_file(filepath, dry_run=dry_run):
                total_changes += 1

    print(f"\n{'Encontrados' if dry_run else 'Aplicados'}: {total_changes} archivos con cambios")

    if dry_run and total_changes > 0:
        print("\nEjecuta con --apply para aplicar los cambios.")


if __name__ == "__main__":
    main()

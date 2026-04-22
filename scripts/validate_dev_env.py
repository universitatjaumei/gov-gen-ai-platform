import os
import sys
import json
import asyncio
from pathlib import Path

def print_res(task, status, detail=""):
    icon = "✅" if status else "❌"
    print(f"{icon} {task:<40} {'[OK]' if status else '[FALLO]'} {detail}")

async def validate():
    print("--- 🔍 VALIDACIÓN DE ENTORNO AUTOMATIA ---")
    root = Path(os.getcwd())
    errors = 0

    # 1. Check de Desacoplamiento (Regla Crítica)
    # Prohíbe 'import server' o 'from server' dentro de client_app
    forbidden_imports = False
    for py_file in (root / "client_app").rglob("*.py"):
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "from server." in content or "import server." in content:
                print_res(f"Arquitectura: {py_file.name}", False, "Importación prohibida de 'server' detectada.")
                forbidden_imports = True
                errors += 1
    if not forbidden_imports:
        print_res("Arquitectura: Desacoplamiento", True)

    # 2. Check de Internacionalización (i18n)
    i18n_path = root / "client_app" / "app" / "i18n" / "translations.json"
    if i18n_path.exists():
        try:
            with open(i18n_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not data:
                    print_res("i18n: translations.json", False, "El archivo está vacío.")
                    errors += 1
                else:
                    print_res("i18n: translations.json", True, f"{len(data)} claves cargadas.")
        except json.JSONDecodeError:
            print_res("i18n: translations.json", False, "JSON corrupto o mal formado.")
            errors += 1
    else:
        print_res("i18n: translations.json", False, "Archivo no encontrado.")
        errors += 1

    # 3. Check de Dependencias y Modelos
    try:
        from client_app.app.database.models import UserExtractionConfig
        from client_app.app.clients.brain_client import BrainAPIClient
        print_res("Core: Modelos y Clientes API", True)
    except ImportError as e:
        print_res("Core: Modelos y Clientes API", False, str(e))
        errors += 1

    # 4. Check de Directorios de Datos (Soberanía local)
    for folder in ["data/executions", "data/logs", "data/outputs"]:
        p = root / folder
        p.mkdir(parents=True, exist_ok=True)
        print_res(f"FS: Directorio {folder}", True)

    print("------------------------------------------")
    if errors > 0:
        print(f"⚠️  Se encontraron {errors} errores. No inicies el desarrollo.")
        sys.exit(1)
    else:
        print("🚀 Entorno listo para TDD.")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(validate())
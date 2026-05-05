"""
Exporta el contrato OpenAPI de la app FastAPI a openapi.json offline.

Uso:
    cd server && python export_openapi.py

No levanta Uvicorn ni requiere conexión real a base de datos.
El archivo generado es la fuente de verdad para Orval en el frontend.
"""

import json
import os
import sys
from pathlib import Path

# Variables de entorno mínimas antes de importar la app.
# JWT_SECRET_KEY es la única obligatoria (RuntimeError si falta al instanciar Settings).
# Las URLs de BD tienen default en db.py pero se sobreescriben para dejar claro
# que este script nunca conecta a ningún servidor real.
os.environ.setdefault("JWT_SECRET_KEY", "openapi-export-offline-key-min-32-chars!!")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql+psycopg2://x:x@localhost/x")

# app/main.py usa internamente `from server.app.*` — el root del proyecto debe
# estar en sys.path para que esos imports funcionen, igual que en los tests.
_PROJECT_ROOT = Path(__file__).parent.parent  # server/ → AI_agents_hub/
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from server.app.main import app  # noqa: E402

_HERE = Path(__file__).parent  # server/
_SERVER_OUT = _HERE / "openapi.json"
_FRONTEND_OUT = _HERE.parent / "frontend" / "openapi.json"


def main() -> None:
    print("Generando schema OpenAPI...", flush=True)
    schema = app.openapi()

    paths_count = len(schema.get("paths", {}))
    schemas_count = len(schema.get("components", {}).get("schemas", {}))

    payload = json.dumps(schema, indent=2, ensure_ascii=False)

    _SERVER_OUT.write_text(payload, encoding="utf-8")
    print(f"  [OK] {_SERVER_OUT}  ({paths_count} paths, {schemas_count} schemas)")

    if _FRONTEND_OUT.parent.exists():
        _FRONTEND_OUT.write_text(payload, encoding="utf-8")
        print(f"  [OK] {_FRONTEND_OUT}")
    else:
        print(
            f"  [WARN] Directorio frontend no encontrado: {_FRONTEND_OUT.parent}\n"
            "    Copia manualmente: cp server/openapi.json frontend/openapi.json",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()

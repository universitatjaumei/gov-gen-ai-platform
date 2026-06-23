"""Fixtures comunes de los tests del servidor MCP.

Asegura que los módulos planos del proyecto (config, api_client, resources,
server) sean importables sin instalar el paquete (mismo patrón que el
microservicio script_sandbox).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

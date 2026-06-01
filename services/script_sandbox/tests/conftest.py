"""Fixtures comunes para los tests del microservicio script-sandbox."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Aseguramos que el paquete `sandbox` (en la raíz del microservicio) sea importable
# sin necesidad de instalar el proyecto previamente.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


@pytest.fixture(scope="session")
def client() -> TestClient:
    from sandbox.main import app
    return TestClient(app)

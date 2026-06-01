"""Tests SBX.4 — verifican el hardening del servicio script-sandbox en docker-compose.

Parsean los ficheros YAML y el Dockerfile; no levantan contenedores.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# Raíz del monorepo (AI_agents_hub/)
_ROOT = Path(__file__).parent.parent.parent.parent


def _load_compose(filename: str) -> dict:
    path = _ROOT / filename
    assert path.exists(), f"No existe {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. docker-compose.yml (dev) — el sandbox está definido con hardening mínimo
# ---------------------------------------------------------------------------

def test_compose_dev_defines_sandbox_service() -> None:
    """El compose dev incluye script-sandbox con cap_drop, read_only, security_opt, user y red."""
    compose = _load_compose("docker-compose.yml")
    services = compose.get("services", {})

    assert "script-sandbox" in services, "Falta el servicio script-sandbox en docker-compose.yml"
    svc = services["script-sandbox"]

    assert svc.get("read_only") is True, "read_only debe ser true"

    cap_drop = svc.get("cap_drop", [])
    assert "ALL" in cap_drop, "cap_drop debe incluir ALL"

    security_opt = svc.get("security_opt", [])
    assert any("no-new-privileges" in o for o in security_opt), \
        "security_opt debe incluir no-new-privileges:true"

    user = str(svc.get("user", ""))
    assert "65534" in user, "user debe ser 65534 (nobody)"

    networks = compose.get("networks", {})
    assert "sandbox-net" in networks, "Falta la red sandbox-net en docker-compose.yml"

    svc_networks = svc.get("networks", [])
    svc_networks_list = (
        list(svc_networks.keys()) if isinstance(svc_networks, dict) else list(svc_networks)
    )
    assert "sandbox-net" in svc_networks_list, \
        "script-sandbox debe estar conectado a sandbox-net"


# ---------------------------------------------------------------------------
# 2. docker-compose.prod.yml — el sandbox NO expone puertos
# ---------------------------------------------------------------------------

def test_compose_prod_sandbox_has_no_ports() -> None:
    """En producción el sandbox no tiene sección ports (no accesible desde el host)."""
    compose = _load_compose("docker-compose.prod.yml")
    services = compose.get("services", {})

    assert "script-sandbox" in services, "Falta script-sandbox en docker-compose.prod.yml"
    svc = services["script-sandbox"]

    assert not svc.get("ports"), \
        "script-sandbox NO debe exponer ports en producción"


# ---------------------------------------------------------------------------
# 3. docker-compose.prod.yml — sandbox-net es internal: true
# ---------------------------------------------------------------------------

def test_compose_prod_sandbox_net_is_internal() -> None:
    """En producción sandbox-net tiene internal: true (sin egress a internet)."""
    compose = _load_compose("docker-compose.prod.yml")
    networks = compose.get("networks", {})

    assert "sandbox-net" in networks, "Falta la red sandbox-net en docker-compose.prod.yml"
    net = networks["sandbox-net"] or {}
    assert net.get("internal") is True, "sandbox-net debe tener internal: true en producción"


# ---------------------------------------------------------------------------
# 4. docker-compose.prod.yml — app conectada a sandbox-net
# ---------------------------------------------------------------------------

def test_compose_prod_app_connected_to_sandbox_net() -> None:
    """El servicio app en prod está conectado a sandbox-net para hablar con el sandbox."""
    compose = _load_compose("docker-compose.prod.yml")
    services = compose.get("services", {})

    assert "app" in services, "Falta el servicio app en docker-compose.prod.yml"
    app_svc = services["app"]

    app_networks = app_svc.get("networks", [])
    app_networks_list = (
        list(app_networks.keys()) if isinstance(app_networks, dict) else list(app_networks)
    )
    assert "sandbox-net" in app_networks_list, \
        "El servicio app debe estar conectado a sandbox-net en producción"


# ---------------------------------------------------------------------------
# 5. Dockerfile del sandbox — corre como usuario no-root 65534
# ---------------------------------------------------------------------------

def test_sandbox_dockerfile_runs_as_non_root_user() -> None:
    """El Dockerfile del sandbox tiene USER 65534 para evitar escalada de privilegios."""
    dockerfile = _ROOT / "services" / "script_sandbox" / "Dockerfile"
    assert dockerfile.exists(), f"No existe {dockerfile}"

    content = dockerfile.read_text(encoding="utf-8")
    user_lines = [line.strip() for line in content.splitlines() if line.strip().startswith("USER")]

    assert user_lines, "El Dockerfile no tiene instrucción USER"
    assert any("65534" in line for line in user_lines), \
        f"USER debe ser 65534, encontrado: {user_lines}"

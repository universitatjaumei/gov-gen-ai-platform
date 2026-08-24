"""SEC.9.1 — La biblioteca de automatizaciones exige identidad, y la saca del token.

**El agujero** (auditoría del 2026-08-24): `library_router` no tenía **ninguna** dependencia de
identidad. Los cuatro endpoints decidían la visibilidad con `X-Client-Id`, `X-Partner-Id` y
`X-Client-Groups`, que las pone quien llama: bastaba declarar el id del dueño para descargar el
código de la automatización de otra organización. `POST /push` publicaba un artefacto arbitrario
**y el servidor lo firmaba** con la clave privada de la plataforma, y `POST /sign_manifest` era un
oráculo de firma RSA abierto — se le pasaba un JSON y devolvía su firma.

Lo que se fija aquí es la frontera observable: sin credencial no se entra, la tenencia sale del
token y **nunca** de una cabecera, y firmar es cosa del superadministrador.

El último test no prueba comportamiento: comprueba que la guarda está declarada como dependencia
real del router. El inventario de módulos de PLAT.5 se validaba leyendo **docstrings**, y este
router declaraba «Módulo: plataforma» en el suyo mientras estaba completamente abierto — el check
pasaba en verde. Un docstring no autoriza nada.
"""
from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.app.core.auth.models import UserInfo
from server.app.routers.library_router import router as library_router

ORG_A = str(uuid.UUID("00000000-0000-0000-0000-0000000000a1"))
ORG_B = str(uuid.UUID("00000000-0000-0000-0000-0000000000b2"))


def _admin(*orgs: str) -> UserInfo:
    return UserInfo(
        user_id="admin-1", email="a@example.org", role="admin", organizacion_ids=orgs
    )


def _superadmin() -> UserInfo:
    return UserInfo(user_id="root", email="root@example.org", role="superadmin")


def _servicio(item=None, visibles: list | None = None):
    """Doble del `LibraryService` que registra con qué identidad se le preguntó."""
    servicio = MagicMock()
    servicio.get_by_id = AsyncMock(return_value=item)
    servicio.get_visible_automations = AsyncMock(return_value=visibles or [])
    servicio.save_master = AsyncMock(
        return_value=SimpleNamespace(id="a1", version=1)
    )
    return servicio


def _app(principal: UserInfo | None, servicio) -> "FastAPI":  # noqa: F821
    """App mínima con el router, el servicio doblado y (si se da) el principal.

    `principal=None` deja la dependencia de autenticación **real** para poder medir el 401;
    la sesión se dobla igual, porque si no la resolución de dependencias tocaría la BD antes
    de llegar a la comprobación de credencial.
    """
    from fastapi import FastAPI

    from server.app.api.deps import get_current_user, get_session, modulos_concedidos
    from server.app.routers.library_router import get_service

    app = FastAPI()

    async def _sesion():
        yield MagicMock()

    app.dependency_overrides[get_session] = _sesion
    app.dependency_overrides[get_service] = lambda: servicio
    # El módulo concedido se dobla aparte: lo que este fichero mide es la frontera de
    # identidad, no la de módulos (que tiene su propio test en PLAT.5).
    app.dependency_overrides[modulos_concedidos] = lambda: ["plataforma"]
    if principal is not None:
        app.dependency_overrides[get_current_user] = lambda: principal
    app.include_router(library_router, prefix="/api")
    return app


def _cliente(principal, servicio):
    from fastapi.testclient import TestClient

    return TestClient(_app(principal, servicio))


class TestSinCredencialNoSeEntra:

    def test_should_reject_manifest_without_authentication(self):
        resp = _cliente(None, _servicio()).get("/api/v1/library/manifest")
        assert resp.status_code == 401

    def test_should_reject_download_without_authentication(self):
        resp = _cliente(None, _servicio()).get("/api/v1/library/download/a1")
        assert resp.status_code == 401

    def test_should_reject_push_without_authentication(self):
        resp = _cliente(None, _servicio()).post("/api/v1/library/push", json={})
        assert resp.status_code == 401

    def test_should_reject_sign_manifest_without_authentication(self):
        resp = _cliente(None, _servicio()).post(
            "/api/v1/library/sign_manifest",
            json={"manifest_json": json.dumps({"id": "x"}), "partner_id": "p1"},
        )
        assert resp.status_code == 401


class TestLaTenenciaSaleDelToken:

    def test_should_ignore_client_supplied_tenant_headers(self):
        """La cabecera propone y el token dispone: pedir el catálogo de otra organización
        declarándolo en `X-Client-Id` tiene que dar exactamente lo mismo que no declararlo."""
        servicio = _servicio()
        cliente = _cliente(_admin(ORG_A), servicio)

        resp = cliente.get(
            "/api/v1/library/manifest",
            headers={
                "X-Client-Id": ORG_B,
                "X-Partner-Id": ORG_B,
                "X-Client-Groups": json.dumps(["grupo-ajeno"]),
            },
        )

        assert resp.status_code == 200
        kwargs = servicio.get_visible_automations.await_args.kwargs
        declarado = json.dumps(kwargs, default=str)
        assert ORG_B not in declarado
        assert "grupo-ajeno" not in declarado
        assert ORG_A in declarado

    def test_should_not_scope_the_catalogue_for_a_superadmin(self):
        servicio = _servicio()
        _cliente(_superadmin(), servicio).get("/api/v1/library/manifest")

        kwargs = servicio.get_visible_automations.await_args.kwargs
        assert kwargs.get("is_superadmin") is True

    def test_should_forbid_download_of_other_org_automation(self):
        """El artefacto es de ORG_B y el servicio no lo declara visible: 403, y sin que el
        `code_content` llegue a la respuesta."""
        ajeno = SimpleNamespace(id="a1", client_id=ORG_B, code_content="print('secreto')")
        servicio = _servicio(item=ajeno, visibles=[])

        resp = _cliente(_admin(ORG_A), servicio).get("/api/v1/library/download/a1")

        assert resp.status_code == 403
        assert "secreto" not in resp.text


class TestFirmarEsDelSuperadministrador:

    def test_should_forbid_push_for_non_superadmin(self):
        servicio = _servicio()
        resp = _cliente(_admin(ORG_A), servicio).post(
            "/api/v1/library/push",
            json={
                "id": "a1",
                "name": "Robada",
                "type": "script",
                "code_content": "print(1)",
            },
        )

        assert resp.status_code == 403
        servicio.save_master.assert_not_awaited()

    def test_should_forbid_sign_manifest_for_non_superadmin(self):
        resp = _cliente(_admin(ORG_A), _servicio()).post(
            "/api/v1/library/sign_manifest",
            json={"manifest_json": json.dumps({"id": "x"}), "partner_id": "p1"},
        )
        assert resp.status_code == 403


class TestLaGuardaEstaDeclarada:
    """El docstring no autoriza: la dependencia tiene que existir en el router."""

    def test_should_declare_real_dependencies_not_only_a_docstring(self):
        assert library_router.dependencies, (
            "library_router sin dependencies: la guarda vivía sólo en el docstring, "
            "que es lo que dejó pasar el agujero de SEC.9.1"
        )

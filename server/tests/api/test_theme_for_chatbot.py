"""Hallazgo #3 de MAN.2: el widget publico no consume ningun tema.

`GET /hub/themes/for-chatbot/{chatbot_id}` resuelve el tema aplicado a un chatbot (si lo
hay) para que el widget lo pinte. Dos cosas no son evidentes leyendo el codigo:

- **Solo devuelve `config`.** SEC.5 (`test_themes_security.py`) cerro `GET /{theme_id}`
  porque un tema lleva `organizacion_id` y sin guarda era un censo de organizaciones. Este
  endpoint no reabre ese hueco: nunca expone `theme_id`, `organizacion_id` ni `name`.
- **La guarda es la misma que abrir el chat** (`assert_chatbot_access`, SEC.2.1): quien no
  podria conversar con el chatbot tampoco ve de que color lo pintarian.

`POST /{theme_id}/apply/{chatbot_id}` completa el stub que dejaba `# TODO: actualizar
configuracion del chatbot en BD` sin persistir nada: ahora guarda `{"theme_id": ...}` en
`HubChatbot.theme_config`, la columna que no tenia lector ni escritor en ningun sitio.
"""
from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import perezoso evitado a proposito: `test_tenant_isolation.py` documenta que
# `hub_chatbots_router`/routers hermanos arrastran el chunker y pyarrow, cuya carga nativa
# revienta el proceso en Windows si ocurre a mitad de la sesion de pytest. `hub_themes_router`
# no tiene esa cadena de imports, pero se importa `server.app.main` primero de todas formas
# para fijar el mismo orden de carga que el resto de la suite.
import server.app.main  # noqa: F401
from server.app.api.deps import get_current_user
from server.app.core.auth.models import UserInfo
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.routers.hub_themes_router import THEMES_DIR, router

ORG_A = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
ORG_B = uuid.UUID("00000000-0000-0000-0000-0000000000b2")


def _app_con(principal: UserInfo, session):
    async def _sesion():
        yield session

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: principal
    app.dependency_overrides[get_async_session] = _sesion
    app.include_router(router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


def _sesion_que_devuelve(entidad=None):
    session = MagicMock()
    session.get = AsyncMock(return_value=entidad)
    session.commit = AsyncMock()
    return session


def _chatbot(
    access_mode="public_anon",
    organizacion_id=None,
    theme_config=None,
    allowed_roles=(),
    allowed_saml_groups=(),
):
    return SimpleNamespace(
        id=uuid.uuid4(),
        access_mode=access_mode,
        organizacion_id=organizacion_id or ORG_A,
        allowed_roles=allowed_roles,
        allowed_saml_groups=allowed_saml_groups,
        theme_config=theme_config if theme_config is not None else {},
    )


def _anonimo() -> UserInfo:
    return UserInfo(user_id="visitante", email="v@test.com", role="user")


@pytest.fixture
def tema_en_disco():
    """Un tema real en disco (colores/tipografia), igual que `tema_de_org_b` en
    test_themes_security.py. Se borra al terminar."""
    theme_id = str(uuid.uuid4())
    ruta = THEMES_DIR / f"{theme_id}.json"
    ruta.write_text(
        json.dumps(
            {
                "id": theme_id,
                "name": "Tema del chatbot",
                "organizacion_id": str(ORG_A),
                "chatbot_id": None,
                "is_default": False,
                "config": {"name": "chatbot-theme", "colors": {"primary": "#123456"}},
                "created_at": "2026-08-10T00:00:00+00:00",
                "updated_at": "2026-08-10T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    yield theme_id
    ruta.unlink(missing_ok=True)


class TestGetThemeForChatbot:
    def test_should_404_when_chatbot_does_not_exist(self):
        cliente = _app_con(_anonimo(), _sesion_que_devuelve(None))

        resp = cliente.get(f"/api/v1/hub/themes/for-chatbot/{uuid.uuid4()}")

        assert resp.status_code == 404

    def test_should_return_empty_config_when_no_theme_applied(self):
        chatbot = _chatbot(access_mode="public_anon", theme_config={})
        cliente = _app_con(_anonimo(), _sesion_que_devuelve(chatbot))

        resp = cliente.get(f"/api/v1/hub/themes/for-chatbot/{chatbot.id}")

        assert resp.status_code == 200
        assert resp.json() == {"config": {}}

    def test_should_resolve_the_applied_theme_config(self, tema_en_disco):
        chatbot = _chatbot(
            access_mode="public_anon", theme_config={"theme_id": tema_en_disco}
        )
        cliente = _app_con(_anonimo(), _sesion_que_devuelve(chatbot))

        resp = cliente.get(f"/api/v1/hub/themes/for-chatbot/{chatbot.id}")

        assert resp.status_code == 200
        assert resp.json() == {"config": {"name": "chatbot-theme", "colors": {"primary": "#123456"}}}

    def test_should_not_leak_theme_id_or_organizacion_id(self, tema_en_disco):
        """El disenio existe justo para no reabrir el censo de organizaciones de SEC.5."""
        chatbot = _chatbot(
            access_mode="public_anon", theme_config={"theme_id": tema_en_disco}
        )
        cliente = _app_con(_anonimo(), _sesion_que_devuelve(chatbot))

        resp = cliente.get(f"/api/v1/hub/themes/for-chatbot/{chatbot.id}")

        assert set(resp.json().keys()) == {"config"}

    def test_should_403_a_visitor_on_a_restricted_chatbot(self):
        chatbot = _chatbot(
            access_mode="restricted",
            organizacion_id=ORG_A,
            allowed_roles=("informer",),
        )
        # El visitante no pertenece a ORG_A ni tiene el rol permitido.
        cliente = _app_con(
            UserInfo(user_id="u", email="u@test.com", role="user", organizacion_ids=(str(ORG_B),)),
            _sesion_que_devuelve(chatbot),
        )

        resp = cliente.get(f"/api/v1/hub/themes/for-chatbot/{chatbot.id}")

        assert resp.status_code == 403

    def test_should_allow_a_superadmin_regardless_of_access_mode(self):
        chatbot = _chatbot(access_mode="restricted", organizacion_id=ORG_A)
        cliente = _app_con(
            UserInfo(user_id="root", email="root@test.com", role="superadmin"),
            _sesion_que_devuelve(chatbot),
        )

        resp = cliente.get(f"/api/v1/hub/themes/for-chatbot/{chatbot.id}")

        assert resp.status_code == 200


class TestApplyThemeToChatbot:
    def test_should_404_when_theme_does_not_exist(self):
        chatbot = _chatbot()
        cliente = _app_con(
            UserInfo(user_id="root", email="root@test.com", role="superadmin"),
            _sesion_que_devuelve(chatbot),
        )

        resp = cliente.post(f"/api/v1/hub/themes/{uuid.uuid4()}/apply/{chatbot.id}")

        assert resp.status_code == 404

    def test_should_404_when_chatbot_does_not_exist(self, tema_en_disco):
        cliente = _app_con(
            UserInfo(user_id="root", email="root@test.com", role="superadmin"),
            _sesion_que_devuelve(None),
        )

        resp = cliente.post(f"/api/v1/hub/themes/{tema_en_disco}/apply/{uuid.uuid4()}")

        assert resp.status_code == 404

    def test_should_persist_the_applied_theme_id_on_the_chatbot(self, tema_en_disco):
        chatbot = _chatbot(theme_config={})
        session = _sesion_que_devuelve(chatbot)
        cliente = _app_con(
            UserInfo(user_id="root", email="root@test.com", role="superadmin"), session
        )

        resp = cliente.post(f"/api/v1/hub/themes/{tema_en_disco}/apply/{chatbot.id}")

        assert resp.status_code == 200
        assert chatbot.theme_config == {"theme_id": tema_en_disco}
        session.commit.assert_awaited_once()

    def test_should_require_superadmin(self, tema_en_disco):
        chatbot = _chatbot()
        cliente = _app_con(
            UserInfo(user_id="a", email="a@test.com", role="admin"),
            _sesion_que_devuelve(chatbot),
        )

        resp = cliente.post(f"/api/v1/hub/themes/{tema_en_disco}/apply/{chatbot.id}")

        assert resp.status_code == 403

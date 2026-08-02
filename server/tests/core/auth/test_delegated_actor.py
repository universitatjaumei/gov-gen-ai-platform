"""Identidad delegada por cabecera firmada (Prompt SEC.2.1, Parte 2).

El Pipe de Open WebUI habla con el backend usando **un PAT de servicio**. Sin nada más, el
backend solo ve al dueño de ese PAT: la cuota por usuario de SEC.4 no podría existir y las
interacciones de cientos de personas quedarían atribuidas a una sola cuenta.

La alternativa —un PAT por persona— se descartó en la planificación: no escala a cientos de
usuarios ni sobrevive a las bajas.

**Las dos reglas que sostienen el diseño, y las dos tienen su test:**

1. **Sin el scope `chat:onbehalf`, la cabecera se ignora en silencio.** No es un error: el
   actor efectivo pasa a ser el dueño del PAT. Así un PAT robado que no lleve ese scope no
   sirve para suplantar a nadie, y el emisor decide caso por caso quién puede delegar.
2. **Las organizaciones salen del PAT, jamás de la cabecera.** Los grupos SAML sí vienen de
   la cabecera, porque eso lo sabe el IdP del cliente y el backend no. La diferencia es la
   que separa «el cliente aporta lo que sabe» de «el cliente se autoconcede permisos».
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt as pyjwt
import pytest
from fastapi import HTTPException

ORG_PAT = str(uuid.UUID("00000000-0000-0000-0000-0000000000a1"))
ORG_ROBADA = str(uuid.UUID("00000000-0000-0000-0000-0000000000b2"))
SECRETO = "secreto-de-actor-delegado-de-al-menos-32-chars"


@pytest.fixture(autouse=True)
def _entorno(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long")
    monkeypatch.setenv("DELEGATED_ACTOR_SECRET", SECRETO)


def _cabecera(
    *,
    sub: str = "persona-42",
    email: str = "persona@uji.es",
    groups: list[str] | None = None,
    aud: str = "govgenai-backend",
    exp_delta: timedelta = timedelta(seconds=120),
    secreto: str = SECRETO,
    extra: dict | None = None,
) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "email": email,
        "groups": groups or [],
        "aud": aud,
        "iat": ahora,
        "exp": ahora + exp_delta,
    }
    payload.update(extra or {})
    return pyjwt.encode(payload, secreto, algorithm="HS256")


def _peticion(cabecera: str | None, scopes: list[str] | None):
    """Doble de `Request`: solo se le piden las cabeceras y `state.pat_scopes`.

    `Headers` de Starlette y no un dict: las cabeceras HTTP son insensibles a mayúsculas y
    un dict no lo es, así que el doble mentiría justo sobre lo que el helper hace al leer.
    """
    from starlette.datastructures import Headers

    crudas = {"x-govgenai-actor": cabecera} if cabecera else {}
    return SimpleNamespace(
        headers=Headers(crudas), state=SimpleNamespace(pat_scopes=scopes)
    )


def _principal(role: str = "admin", orgs: tuple[str, ...] = (ORG_PAT,)):
    from server.app.core.auth.models import UserInfo

    return UserInfo(
        user_id="duenyo-del-pat",
        email="servicio@uji.es",
        role=role,
        organizacion_ids=orgs,
    )


class TestResolucionDelActor:

    def test_should_resolve_actor_from_signed_header_when_scope_present(self):
        from server.app.core.auth.delegated_actor import resolve_effective_actor
        from server.app.core.auth.pat.scopes import CHAT_ONBEHALF

        actor = resolve_effective_actor(
            _peticion(_cabecera(groups=["gerencia"]), [CHAT_ONBEHALF]), _principal()
        )

        assert actor.delegated is True
        assert actor.subject_id == "persona-42"
        assert actor.email == "persona@uji.es"
        assert actor.saml_groups == ("gerencia",)

    def test_should_ignore_actor_header_when_pat_lacks_onbehalf_scope(self):
        """Ni error ni delegación: el actor es el dueño del PAT, como si no viniera nada."""
        from server.app.core.auth.delegated_actor import resolve_effective_actor
        from server.app.core.auth.pat.scopes import CHAT_TEST

        actor = resolve_effective_actor(
            _peticion(_cabecera(), [CHAT_TEST]), _principal()
        )

        assert actor.delegated is False
        assert actor.email == "servicio@uji.es"

    def test_should_ignore_an_actor_header_on_a_human_session(self):
        """Sin PAT no hay delegación posible: `pat_scopes` es None en una sesión humana."""
        from server.app.core.auth.delegated_actor import resolve_effective_actor

        actor = resolve_effective_actor(_peticion(_cabecera(), None), _principal())

        assert actor.delegated is False
        assert actor.email == "servicio@uji.es"

    def test_should_401_on_invalid_signature(self):
        from server.app.core.auth.delegated_actor import resolve_effective_actor
        from server.app.core.auth.pat.scopes import CHAT_ONBEHALF

        with pytest.raises(HTTPException) as exc:
            resolve_effective_actor(
                _peticion(_cabecera(secreto="otro-secreto-cualquiera"), [CHAT_ONBEHALF]),
                _principal(),
            )
        assert exc.value.status_code == 401
        assert exc.value.detail["code"] == "ACTOR_TOKEN_INVALID"

    def test_should_401_on_expired_actor_token(self):
        from server.app.core.auth.delegated_actor import resolve_effective_actor
        from server.app.core.auth.pat.scopes import CHAT_ONBEHALF

        with pytest.raises(HTTPException) as exc:
            resolve_effective_actor(
                _peticion(_cabecera(exp_delta=timedelta(seconds=-10)), [CHAT_ONBEHALF]),
                _principal(),
            )
        assert exc.value.status_code == 401

    def test_should_401_on_wrong_audience(self):
        from server.app.core.auth.delegated_actor import resolve_effective_actor
        from server.app.core.auth.pat.scopes import CHAT_ONBEHALF

        with pytest.raises(HTTPException) as exc:
            resolve_effective_actor(
                _peticion(_cabecera(aud="otro-backend"), [CHAT_ONBEHALF]), _principal()
            )
        assert exc.value.status_code == 401

    def test_should_401_when_the_window_is_too_long(self):
        """La ventana corta es parte del contrato: una cabecera de un día es un PAT encubierto."""
        from server.app.core.auth.delegated_actor import resolve_effective_actor
        from server.app.core.auth.pat.scopes import CHAT_ONBEHALF

        with pytest.raises(HTTPException):
            resolve_effective_actor(
                _peticion(_cabecera(exp_delta=timedelta(hours=6)), [CHAT_ONBEHALF]),
                _principal(),
            )

    def test_should_inherit_organizacion_ids_from_pat_not_from_header(self):
        """El test que importa: la cabecera no concede organizaciones."""
        from server.app.core.auth.delegated_actor import resolve_effective_actor
        from server.app.core.auth.pat.scopes import CHAT_ONBEHALF

        actor = resolve_effective_actor(
            _peticion(
                _cabecera(extra={"orgs": [ORG_ROBADA], "role": "superadmin"}),
                [CHAT_ONBEHALF],
            ),
            _principal(orgs=(ORG_PAT,)),
        )

        assert actor.organizacion_ids == (ORG_PAT,)
        assert ORG_ROBADA not in actor.organizacion_ids
        assert actor.role != "superadmin"

    def test_should_use_session_user_as_actor_for_human_jwt(self):
        from server.app.core.auth.delegated_actor import resolve_effective_actor

        actor = resolve_effective_actor(_peticion(None, None), _principal(role="user"))

        assert actor.delegated is False
        assert actor.subject_id == "duenyo-del-pat"
        assert actor.organizacion_ids == (ORG_PAT,)

    def test_should_carry_the_saml_groups_of_a_human_session(self):
        """Un humano logueado por SAML lleva sus grupos en el token, no en una cabecera."""
        from server.app.core.auth.delegated_actor import resolve_effective_actor
        from server.app.core.auth.models import UserInfo

        humano = UserInfo(
            user_id="p-1",
            email="p@uji.es",
            role="user",
            organizacion_ids=(ORG_PAT,),
            saml_groups=("gerencia",),
        )
        actor = resolve_effective_actor(_peticion(None, None), humano)

        assert actor.saml_groups == ("gerencia",)

    def test_should_401_when_the_header_arrives_without_a_configured_secret(
        self, monkeypatch
    ):
        """Sin secreto no se puede verificar nada, y no verificar es aceptar cualquier firma."""
        from server.app.core.auth.delegated_actor import resolve_effective_actor
        from server.app.core.auth.pat.scopes import CHAT_ONBEHALF

        monkeypatch.delenv("DELEGATED_ACTOR_SECRET", raising=False)

        with pytest.raises(HTTPException) as exc:
            resolve_effective_actor(
                _peticion(_cabecera(), [CHAT_ONBEHALF]), _principal()
            )
        assert exc.value.status_code == 401


class TestElScope:

    def test_should_publish_the_onbehalf_scope_in_the_catalogue(self):
        from server.app.core.auth.pat.scopes import ALL_SCOPES, CHAT_ONBEHALF

        assert CHAT_ONBEHALF in ALL_SCOPES

    def test_should_cap_the_onbehalf_scope_to_admin_and_superadmin(self):
        """Suplantar es lo más que concede un PAT: no lo emite un rol cualquiera."""
        from server.app.core.auth.pat.scopes import (
            CHAT_ONBEHALF,
            allowed_scopes_for_role,
        )

        assert CHAT_ONBEHALF in allowed_scopes_for_role("superadmin")
        assert CHAT_ONBEHALF in allowed_scopes_for_role("admin")
        assert CHAT_ONBEHALF not in allowed_scopes_for_role("user")
        assert CHAT_ONBEHALF not in allowed_scopes_for_role("informer")

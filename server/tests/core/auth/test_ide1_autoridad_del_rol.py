"""IDE.1 — quién manda sobre el rol: la aplicación o el IdP.

`_provision_sso_user`, en la rama del usuario que ya existe, hacía `sso.role =
resolve_role(attributes)` **sin condición**. Es correcto si la autoridad de los permisos es el
IdP, y es una avería si la autoridad es la aplicación: cualquier rol asignado a mano dura hasta
el siguiente inicio de sesión. Por eso hoy no se pueden «dar usuarios con roles manualmente»
—no falta la pantalla, es que la pantalla no serviría—.

**Lo que decidió el usuario (2026-08-22)**, y que parte el problema en dos mitades que no se
mezclan:

- **El rol lo pone una persona, siempre.** «El superadmin, e incluso el admin, siempre se ha de
  hacer a mano. Serán pocos.» Así que con autoridad `app` el atributo de rol de la aserción **no
  se lee**, y `SAML_GROUP_ROLE_MAP` tampoco: quien llega nuevo entra con `SAML_DEFAULT_ROLE`.
- **Los módulos vendrán del grupo del IdP**, que en la UJI son los grandes colectivos
  (estudiante, PDI, PTGAS) y quizá el puesto. Eso es IDE.5 y no toca aquí: los grupos no se
  guardan, se leen de cada aserción, así que para ellos el IdP es la autoridad por construcción.

**Por qué ignorar el atributo y no confiar en él la primera vez.** `resolve_role` acepta
`superadmin` desde la aserción. Usarlo al crear la fila —que es lo que decía el prompt del
plan— significa que un IdP mal configurado acuña un superadministrador en el primer inicio de
sesión, **con la autoridad puesta en la aplicación**. El interruptor solo protegería lo ya
creado, que es la mitad inútil del problema. Desviación documentada frente al plan.

**Y se deja registro de lo ignorado.** Hoy nadie sabe qué atributos manda el IdP de la UJI —los
configura la Unidad de Desarrollo—, así que un aviso en el log cuando la aserción trae un rol
que no se está usando convierte esa incógnita en algo observable, sin tener que preguntar.
"""
from __future__ import annotations

import logging
import uuid

import pytest


def _uid() -> str:
    return uuid.uuid4().hex[:12]


async def _entrar(session, email: str, attributes: dict):
    from server.app.core.auth.saml.identity_service import SamlIdentityService

    return await SamlIdentityService(session).resolve_session(
        nameid=email, attributes=attributes
    )


async def _sso_user(session, email: str):
    from sqlalchemy import select

    from server.app.modules.agents_hub.database.config_models import HubSsoUser

    return (
        await session.execute(select(HubSsoUser).where(HubSsoUser.email == email))
    ).scalar_one()


# ───────────────────────── El ajuste existe y se valida ─────────────────────────


class TestElAjusteDeAutoridad:

    def test_should_default_to_the_application(self, saml_ctx, monkeypatch):
        """El defecto es lo que el usuario quiere hoy: el rol lo pone una persona."""
        monkeypatch.delenv("IDENTITY_ROLE_AUTHORITY", raising=False)
        from server.app.core.config import get_settings

        assert get_settings().identity_role_authority == "app"

    def test_should_accept_the_idp_as_authority(self, saml_ctx, monkeypatch):
        monkeypatch.setenv("IDENTITY_ROLE_AUTHORITY", "idp")
        from server.app.core.config import get_settings

        assert get_settings().identity_role_authority == "idp"

    def test_should_refuse_to_start_with_an_unknown_value(self, saml_ctx, monkeypatch):
        """No se interpreta un valor que no se entiende: adivinar aquí es adivinar quién
        reparte permisos. Y falla **siempre**, no solo en producción: un despliegue de
        desarrollo con la autoridad equivocada enseña un comportamiento que no es el real."""
        monkeypatch.setenv("IDENTITY_ROLE_AUTHORITY", "erp")
        from server.app.core.config import get_settings

        with pytest.raises(RuntimeError, match="IDENTITY_ROLE_AUTHORITY"):
            get_settings()


# ───────────────────────── Autoridad de la aplicación ─────────────────────────


class TestConAutoridadDeLaAplicacion:

    @pytest.mark.asyncio
    async def test_should_not_overwrite_a_role_set_by_hand(self, saml_ctx, monkeypatch, db):
        """**El test del bloque.** Sin esto, la pantalla de IDE.4 no serviría para nada."""
        monkeypatch.setenv("IDENTITY_ROLE_AUTHORITY", "app")
        email = f"promocionado-{_uid()}@uji.es"

        await _entrar(db.session, email, {"mail": [email]})
        fila = await _sso_user(db.session, email)
        fila.role = "admin"  # lo que haría una persona desde la pantalla
        await db.session.commit()

        info = await _entrar(db.session, email, {"mail": [email], "role": ["user"]})

        assert info.role == "admin"
        assert (await _sso_user(db.session, email)).role == "admin"

    @pytest.mark.asyncio
    async def test_should_create_a_new_user_with_the_configured_default(
        self, saml_ctx, monkeypatch, db
    ):
        """Y **no** con el rol de la aserción: `resolve_role` acepta `superadmin`, así que
        confiar en ella al crear deja que el IdP acuñe administradores."""
        monkeypatch.setenv("IDENTITY_ROLE_AUTHORITY", "app")
        email = f"nuevo-{_uid()}@uji.es"

        info = await _entrar(db.session, email, {"mail": [email], "role": ["admin"]})

        assert info.role == "user"
        assert (await _sso_user(db.session, email)).role == "user"

    @pytest.mark.asyncio
    async def test_should_not_let_the_idp_mint_a_superadmin(self, saml_ctx, monkeypatch, db):
        monkeypatch.setenv("IDENTITY_ROLE_AUTHORITY", "app")
        email = f"escalada-{_uid()}@uji.es"

        info = await _entrar(db.session, email, {"mail": [email], "role": ["superadmin"]})

        assert info.role == "user"

    @pytest.mark.asyncio
    async def test_should_ignore_the_group_role_map_too(self, saml_ctx, monkeypatch, db):
        """`SAML_GROUP_ROLE_MAP` es la otra vía por la que el IdP fija un rol. Ignorar una y
        no la otra dejaría el interruptor a medias."""
        monkeypatch.setenv("IDENTITY_ROLE_AUTHORITY", "app")
        monkeypatch.setenv("SAML_GROUP_ROLE_MAP", '{"gerencia": "admin"}')
        email = f"grupo-{_uid()}@uji.es"

        info = await _entrar(db.session, email, {"mail": [email], "groups": ["gerencia"]})

        assert info.role == "user"

    @pytest.mark.asyncio
    async def test_should_respect_the_configured_default_when_it_is_not_user(
        self, saml_ctx, monkeypatch, db
    ):
        """`SAML_DEFAULT_ROLE` es configuración del despliegue, o sea de la aplicación: sí
        manda. Lo que no manda es la aserción."""
        monkeypatch.setenv("IDENTITY_ROLE_AUTHORITY", "app")
        monkeypatch.setenv("SAML_DEFAULT_ROLE", "informer")
        email = f"defecto-{_uid()}@uji.es"

        info = await _entrar(db.session, email, {"mail": [email], "role": ["admin"]})

        assert info.role == "informer"

    @pytest.mark.asyncio
    async def test_should_log_the_role_it_is_ignoring(self, saml_ctx, monkeypatch, db, caplog):
        """Nadie sabe todavía qué manda el IdP de la UJI. Un aviso lo convierte en dato."""
        monkeypatch.setenv("IDENTITY_ROLE_AUTHORITY", "app")
        email = f"aviso-{_uid()}@uji.es"

        with caplog.at_level(logging.INFO):
            await _entrar(db.session, email, {"mail": [email], "role": ["admin"]})

        mensajes = " ".join(r.getMessage() for r in caplog.records)
        assert "IDENTITY_ROLE_AUTHORITY" in mensajes
        assert "admin" in mensajes

    @pytest.mark.asyncio
    async def test_should_not_log_anything_when_the_assertion_carries_no_role(
        self, saml_ctx, monkeypatch, db, caplog
    ):
        """Un aviso en cada inicio de sesión sin nada que avisar es ruido, y el ruido se
        acaba filtrando junto con lo que importa."""
        monkeypatch.setenv("IDENTITY_ROLE_AUTHORITY", "app")
        email = f"silencio-{_uid()}@uji.es"

        with caplog.at_level(logging.INFO):
            await _entrar(db.session, email, {"mail": [email]})

        mensajes = " ".join(r.getMessage() for r in caplog.records)
        assert "IDENTITY_ROLE_AUTHORITY" not in mensajes


# ───────────────────────── Autoridad del IdP (lo de hoy) ─────────────────────────


class TestConAutoridadDelIdP:

    @pytest.mark.asyncio
    async def test_should_refresh_the_role_from_the_assertion(self, saml_ctx, monkeypatch, db):
        """El comportamiento actual, intacto: es el modo del día que el ERP sea la fuente."""
        monkeypatch.setenv("IDENTITY_ROLE_AUTHORITY", "idp")
        email = f"idp-manda-{_uid()}@uji.es"

        await _entrar(db.session, email, {"mail": [email]})
        fila = await _sso_user(db.session, email)
        fila.role = "admin"
        await db.session.commit()

        info = await _entrar(db.session, email, {"mail": [email], "role": ["user"]})

        assert info.role == "user"

    @pytest.mark.asyncio
    async def test_should_create_with_the_resolved_role(self, saml_ctx, monkeypatch, db):
        monkeypatch.setenv("IDENTITY_ROLE_AUTHORITY", "idp")
        email = f"idp-nuevo-{_uid()}@uji.es"

        info = await _entrar(db.session, email, {"mail": [email], "role": ["admin"]})

        assert info.role == "admin"


# ───────────────────────── La identidad se refresca en los dos modos ─────────────────────────


class TestLaIdentidadSeRefrescaSiempre:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("autoridad", ["app", "idp"])
    async def test_should_refresh_name_and_last_login(
        self, saml_ctx, monkeypatch, db, autoridad: str
    ):
        """`display_name`, `external_id` y `last_login_at` son **identidad**, no permiso: los
        refresca el IdP en los dos modos. Confundirlos dejaría el nombre congelado al de la
        primera visita."""
        monkeypatch.setenv("IDENTITY_ROLE_AUTHORITY", autoridad)
        email = f"identidad-{autoridad}-{_uid()}@uji.es"

        await _entrar(db.session, email, {"mail": [email], "displayName": ["Nombre Viejo"]})
        primero = await _sso_user(db.session, email)
        primer_acceso = primero.last_login_at

        await _entrar(db.session, email, {"mail": [email], "displayName": ["Nombre Nuevo"]})
        fila = await _sso_user(db.session, email)

        assert fila.display_name == "Nombre Nuevo"
        assert fila.last_login_at is not None
        assert primer_acceso is not None
        assert fila.last_login_at >= primer_acceso

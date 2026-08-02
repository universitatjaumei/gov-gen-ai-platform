"""Modo de acceso por chatbot (Prompt SEC.2.1, Parte 1).

SEC.2 aísla **entre** organizaciones. Dentro de una, todos los chatbots quedaban igual de
accesibles: no había forma de decir «este es solo para personal» ni «este solo para
Gerencia». `access_mode` lo dice, y `assert_chatbot_access` es el **único** sitio donde se
resuelve — un endpoint que decida el acceso a mano vuelve a partir la regla en dos.

Lo que estos tests fijan, y que no es obvio al leer el helper:

- **`via` manda sobre la identidad.** Una API key de widget no es una identidad, así que no
  abre un chatbot `authenticated` ni aunque el actor que la acompañe fuera superadmin.
- **`restricted` con las dos listas vacías no es «cualquiera»**, es «nadie salvo el
  superadmin». La lectura contraria —«no hay restricciones declaradas, luego no restrinjo»—
  es la que convierte un descuido de configuración en un chatbot abierto.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

ORG_A = str(uuid.UUID("00000000-0000-0000-0000-0000000000a1"))
ORG_B = str(uuid.UUID("00000000-0000-0000-0000-0000000000b2"))


def _actor(
    role: str = "user",
    orgs: tuple[str, ...] = (ORG_A,),
    grupos: tuple[str, ...] = (),
):
    from server.app.core.auth.delegated_actor import EffectiveActor

    return EffectiveActor(
        subject_id="u-1",
        email="u@uji.es",
        role=role,
        organizacion_ids=orgs,
        saml_groups=grupos,
        delegated=False,
    )


def _chatbot(
    access_mode: str = "authenticated",
    roles: list[str] | None = None,
    grupos: list[str] | None = None,
    org: str = ORG_A,
):
    return SimpleNamespace(
        id=uuid.uuid4(),
        organizacion_id=uuid.UUID(org),
        access_mode=access_mode,
        allowed_roles=roles or [],
        allowed_saml_groups=grupos or [],
    )


class TestModoDeAcceso:

    def test_should_allow_anon_widget_only_when_public_anon(self):
        """Sin actor solo se conversa con un chatbot declarado público."""
        from server.app.core.auth.chatbot_access import assert_chatbot_access

        assert_chatbot_access(None, _chatbot("public_anon"), via="widget_api_key")

        with pytest.raises(HTTPException) as exc:
            assert_chatbot_access(None, _chatbot("authenticated"), via="widget_api_key")
        assert exc.value.status_code == 403

    def test_should_allow_public_anon_through_a_session_too(self):
        """Un chatbot abierto también se usa estando dentro; lo contrario sería absurdo."""
        from server.app.core.auth.chatbot_access import assert_chatbot_access

        assert_chatbot_access(_actor(), _chatbot("public_anon"), via="session")

    def test_should_403_widget_key_on_authenticated_chatbot(self):
        """La API key del widget identifica al *sitio*, no a la persona."""
        from server.app.core.auth.chatbot_access import assert_chatbot_access

        with pytest.raises(HTTPException) as exc:
            assert_chatbot_access(_actor(), _chatbot("authenticated"), via="widget_api_key")
        assert exc.value.status_code == 403
        assert exc.value.detail["code"] == "ACCESS_MODE_FORBIDDEN"

    def test_should_403_widget_key_even_for_a_superadmin(self):
        """El comodín es de identidad, y por este canal no llega ninguna."""
        from server.app.core.auth.chatbot_access import assert_chatbot_access

        with pytest.raises(HTTPException):
            assert_chatbot_access(
                _actor(role="superadmin", orgs=()),
                _chatbot("authenticated"),
                via="widget_api_key",
            )

    def test_should_403_authenticated_user_of_other_org(self):
        """Se apoya en SEC.2: el modo de acceso no sustituye a la frontera, la extiende."""
        from server.app.core.auth.chatbot_access import assert_chatbot_access

        with pytest.raises(HTTPException) as exc:
            assert_chatbot_access(
                _actor(orgs=(ORG_B,)), _chatbot("authenticated"), via="session"
            )
        assert exc.value.status_code == 403

    def test_should_403_authenticated_without_actor(self):
        from server.app.core.auth.chatbot_access import assert_chatbot_access

        with pytest.raises(HTTPException):
            assert_chatbot_access(None, _chatbot("authenticated"), via="session")

    def test_should_allow_restricted_when_role_in_allowed_roles(self):
        from server.app.core.auth.chatbot_access import assert_chatbot_access

        assert_chatbot_access(
            _actor(role="informer"),
            _chatbot("restricted", roles=["informer"]),
            via="session",
        )

    def test_should_allow_restricted_when_saml_group_matches(self):
        from server.app.core.auth.chatbot_access import assert_chatbot_access

        assert_chatbot_access(
            _actor(grupos=("gerencia", "pas")),
            _chatbot("restricted", grupos=["gerencia"]),
            via="session",
        )

    def test_should_403_restricted_when_no_role_or_group_matches(self):
        from server.app.core.auth.chatbot_access import assert_chatbot_access

        with pytest.raises(HTTPException) as exc:
            assert_chatbot_access(
                _actor(role="user", grupos=("pas",)),
                _chatbot("restricted", roles=["informer"], grupos=["gerencia"]),
                via="session",
            )
        assert exc.value.status_code == 403

    def test_should_403_restricted_when_lists_empty_and_not_superadmin(self):
        """Sin listas, `restricted` es «nadie», no «todos». Fail-closed."""
        from server.app.core.auth.chatbot_access import assert_chatbot_access

        with pytest.raises(HTTPException):
            assert_chatbot_access(_actor(role="admin"), _chatbot("restricted"), via="session")

    def test_should_403_restricted_for_a_member_of_another_org(self):
        """La pertenencia al grupo no salta la frontera de organización."""
        from server.app.core.auth.chatbot_access import assert_chatbot_access

        with pytest.raises(HTTPException):
            assert_chatbot_access(
                _actor(orgs=(ORG_B,), grupos=("gerencia",)),
                _chatbot("restricted", grupos=["gerencia"]),
                via="session",
            )

    def test_should_allow_superadmin_regardless_of_access_mode(self):
        from server.app.core.auth.chatbot_access import assert_chatbot_access

        superadmin = _actor(role="superadmin", orgs=())
        for modo in ("public_anon", "authenticated", "restricted"):
            assert_chatbot_access(superadmin, _chatbot(modo, org=ORG_B), via="session")

    def test_should_reject_an_unknown_access_mode(self):
        """Un modo que el helper no conoce no se interpreta: se cierra."""
        from server.app.core.auth.chatbot_access import assert_chatbot_access

        with pytest.raises(HTTPException):
            assert_chatbot_access(
                _actor(role="superadmin", orgs=()), _chatbot("barra_libre"), via="session"
            )


class TestElModeloYLaMigracion:

    def test_should_default_new_chatbots_to_authenticated(self):
        """El default del ORM. El de la tabla lo comprueba el test siguiente."""
        from server.app.modules.agents_hub.database.config_models import HubChatbot

        columna = HubChatbot.__table__.c.access_mode
        assert columna.default.arg == "authenticated"
        assert columna.nullable is False

    def test_should_default_existing_chatbots_to_authenticated_after_migration(self):
        """Lo que la migración le hace a una instalación que YA tiene chatbots.

        El `server_default` ejecutándose de verdad lo comprueba
        `tests/infra/test_migrations_fresh_install.py`, sobre una BD levantada con
        `alembic upgrade head`. Lo que allí no se puede ver es esto: una instalación limpia
        no tiene filas previas, así que un `UPDATE ... SET access_mode = 'public_anon'`
        pasaría desapercibido. Por eso este test lee el fichero.
        """
        codigo = _codigo_de_la_migracion(_fichero_de_migracion("access_mode"))
        subida = codigo.split("def downgrade")[0]

        assert 'server_default="authenticated"' in subida or \
               "server_default='authenticated'" in subida

        # `public_anon` solo puede aparecer enumerado en el CHECK. En cualquier otra línea
        # —un server_default, un UPDATE— significaría abrir chatbots existentes al público.
        colados = [
            linea
            for linea in subida.splitlines()
            if "public_anon" in linea and "access_mode IN" not in linea
        ]
        assert not colados, (
            "la migración no puede dejar ningún chatbot existente en modo anónimo: "
            f"{colados}"
        )
        assert "UPDATE hub_chatbots" not in subida.upper().replace(
            "UPDATE HUB_CHATBOTS", "UPDATE hub_chatbots"
        )

    def test_should_leave_the_vocabulary_of_modes_in_a_check_constraint(self):
        """Tres modos estables con consumidor en el código: esto sí es estructura.

        Es el criterio del proyecto para `CheckConstraint` frente a tabla de vocabulario
        (CLAUDE.md §5): añadir un modo exige de todos modos escribir el código que lo
        aplique en `assert_chatbot_access`.
        """
        from server.app.modules.agents_hub.database.config_models import HubChatbot

        checks = [
            str(c.sqltext)
            for c in HubChatbot.__table__.constraints
            if hasattr(c, "sqltext")
        ]
        assert any("access_mode" in c for c in checks)


class TestNadieDecideElAccesoAParte:
    """El grep de cierre del prompt, convertido en test.

    Hoy la única superficie de conversación es `hub_chat`. Cuando lleguen el adaptador
    compatible-OpenAI (OWUI.1) y el endpoint del widget (D.1), este test falla si alguno
    resuelve el acceso por su cuenta — que es exactamente como una regla única deja de
    serlo: no por una decisión, sino porque nadie se acordó.
    """

    SUPERFICIES_DE_CONVERSACION = (
        Path("app/api/v1/hub_chat.py"),
        # Se añaden aquí según se escriban; el test de abajo vigila que no se olvide.
        Path("app/api/v1/openai_compat.py"),
        Path("app/api/v1/widget_chat.py"),
    )

    def test_should_route_every_conversation_surface_through_the_helper(self):
        sin_guarda = [
            str(ruta)
            for ruta in self.SUPERFICIES_DE_CONVERSACION
            if ruta.is_file()
            and "assert_chatbot_access" not in ruta.read_text(encoding="utf-8")
        ]
        assert not sin_guarda, (
            f"estas superficies conversan con un chatbot sin pasar por "
            f"`assert_chatbot_access`: {sin_guarda}"
        )

    def test_should_not_let_a_conversation_surface_check_the_org_by_hand(self):
        """Media decisión es peor que ninguna: `assert_org_access` suelto aquí se olvida
        del modo de acceso, y el chatbot restringido queda abierto a su organización."""
        a_mano = [
            str(ruta)
            for ruta in self.SUPERFICIES_DE_CONVERSACION
            if ruta.is_file() and "assert_org_access" in ruta.read_text(encoding="utf-8")
        ]
        assert not a_mano, (
            f"estas superficies deciden la organización a mano en vez de delegar en "
            f"`assert_chatbot_access`: {a_mano}"
        )


def _codigo_de_la_migracion(fichero: Path) -> str:
    """El fichero sin su docstring: lo que se ejecuta, no lo que se explica.

    La explicación de una migración fail-closed nombra por fuerza el valor que NO usa, así
    que buscar la cadena a pelo daría un falso positivo justo en la migración bien escrita.
    """
    import ast

    arbol = ast.parse(fichero.read_text(encoding="utf-8"))
    if ast.get_docstring(arbol) is None:
        return fichero.read_text(encoding="utf-8")
    lineas = fichero.read_text(encoding="utf-8").splitlines(keepends=True)
    return "".join(lineas[arbol.body[0].end_lineno:])


def _fichero_de_migracion(marca: str) -> Path:
    versiones = Path("migrations/versions")
    candidatas = [
        f for f in versiones.glob("*.py") if marca in f.read_text(encoding="utf-8")
    ]
    assert candidatas, f"ninguna migración menciona '{marca}'"
    return max(candidatas, key=lambda f: f.stat().st_mtime)

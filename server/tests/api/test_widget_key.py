"""Tests SEC.8.5 — el widget deja de embeber un Bearer privilegiado.

El widget se incrusta con `data-token`, y ese token es un JWT de sesión o un PAT completo:
cualquiera que mire el HTML de la página lo lee. Como los endpoints lo resuelven como
`via="session"`, arrastra el rol y las organizaciones de su dueño y alcanza cualquier
endpoint protegido hasta que expire (JWT 60 min) o lo revoquen (PAT, indefinido).

SEC.2.1 ya había diseñado la salida —`assert_chatbot_access(..., via="widget_api_key")`
rechaza cualquier modo que no sea `public_anon`— pero no existía credencial que la usara:
`VIA_WIDGET` no tenía un solo llamante. Lo que falta es la credencial en sí, y tiene que
cumplir tres cosas: identificar un **sitio** y no a una persona, valer para **un** chatbot,
y guardarse con hash como cualquier otra credencial.
"""
from __future__ import annotations

import uuid

import pytest


class TestLaCredencialDeSitio:

    def test_should_store_only_the_hash(self):
        """El plano se enseña una vez al crearla y no se vuelve a guardar, igual que un PAT."""
        from server.app.core.auth.widget_key import generar_clave, hash_de_clave

        plano = generar_clave()
        assert len(plano) >= 32
        assert hash_de_clave(plano) != plano
        assert len(hash_de_clave(plano)) == 64  # sha256 hex

    def test_should_be_deterministic_for_lookup(self):
        from server.app.core.auth.widget_key import hash_de_clave

        assert hash_de_clave("abc") == hash_de_clave("abc")


class TestElWidgetNoAbreLoQueNoDebe:
    """La credencial identifica un sitio, así que no puede abrir un chatbot con sesión."""

    def _chatbot(self, access_mode: str):
        from types import SimpleNamespace

        return SimpleNamespace(
            id=uuid.uuid4(),
            access_mode=access_mode,
            organizacion_id=uuid.uuid4(),
            allowed_roles=(),
            allowed_saml_groups=(),
        )

    def test_should_open_a_public_anon_chatbot(self):
        from server.app.core.auth.chatbot_access import VIA_WIDGET, assert_chatbot_access

        assert_chatbot_access(None, self._chatbot("public_anon"), via=VIA_WIDGET)

    @pytest.mark.parametrize("modo", ["authenticated", "restricted"])
    def test_should_refuse_anything_that_is_not_public(self, modo):
        from fastapi import HTTPException

        from server.app.core.auth.chatbot_access import VIA_WIDGET, assert_chatbot_access

        with pytest.raises(HTTPException) as exc:
            assert_chatbot_access(None, self._chatbot(modo), via=VIA_WIDGET)
        assert exc.value.status_code == 403


class TestElBundleNoLlevaCredencialDeSesion:

    def test_widget_should_not_send_an_authorization_bearer(self):
        """El guardarraíl del cambio: mientras el widget mande `Authorization`, la
        credencial de sitio no sirve de nada porque el token sigue estando en el HTML."""
        from pathlib import Path

        raiz = Path(__file__).resolve().parents[3] / "frontend" / "src" / "widget"
        fuentes = list(raiz.rglob("*.ts")) + list(raiz.rglob("*.tsx"))
        assert fuentes, f"no se encontró el código del widget en {raiz}"

        ofensores = [
            f.name
            for f in fuentes
            if "Authorization" in f.read_text(encoding="utf-8")
        ]
        assert not ofensores, (
            f"el widget sigue enviando un Bearer de sesión en: {ofensores}"
        )

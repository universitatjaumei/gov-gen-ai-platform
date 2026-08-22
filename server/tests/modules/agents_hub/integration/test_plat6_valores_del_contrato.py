"""PLAT.6 — la lista de campos del tema sale del contrato, no del frontend.

Lo destapó la verificación en navegador, no los tests unitarios: en el nivel de plataforma de
una instalación recién levantada no hay tema propio ni nivel padre, así que la pantalla iteraba
un conjunto vacío y **no mostraba ni un campo**. No es un detalle estético: es justo el estado
en el que alguien entra por primera vez a poner los colores de su institución.

La salida no puede ser escribir la lista en el frontend —el prompt lo prohíbe y con razón: se
desincroniza del contrato en el primer campo nuevo—. Así que el contrato la publica: este
endpoint serializa `ThemeConfig` con sus valores por omisión, que es exactamente la lista de
campos que la pantalla debe ofrecer. Añadir un color a `ThemeColors` lo hace aparecer en la
pantalla sin tocar una línea de TypeScript.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from server.app.api.deps import get_current_user
from server.app.core.auth.models import UserInfo


def _cliente() -> AsyncClient:
    from server.app.routers.hub_themes_router import router

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: UserInfo(
        user_id="quien-pregunta", email="admin@uji.es", role="superadmin"
    )
    app.include_router(router, prefix="/api/v1")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestLosValoresPorOmisionDelContrato:

    @pytest.mark.asyncio
    async def test_should_publish_every_field_of_the_contract(self):
        async with _cliente() as cliente:
            respuesta = await cliente.get("/api/v1/hub/themes/defaults")

        assert respuesta.status_code == 200, respuesta.text
        config = respuesta.json()["config"]
        # Los cuatro grupos que la pantalla edita, cada uno con sus campos y sus valores.
        assert set(config) >= {"colors", "typography", "spacing", "branding"}
        assert config["colors"]["primary"].startswith("#")
        assert "fontFamily" in config["typography"]

    @pytest.mark.asyncio
    async def test_should_grow_on_its_own_when_the_contract_grows(self):
        """La propiedad que importa: la lista **es** el modelo, no una copia suya."""
        from server.app.routers.hub_themes_router import ThemeColors

        async with _cliente() as cliente:
            config = (await cliente.get("/api/v1/hub/themes/defaults")).json()["config"]

        assert set(config["colors"]) == set(ThemeColors.model_fields)

    @pytest.mark.asyncio
    async def test_should_not_invent_a_logo(self):
        """`branding` viaja con las claves presentes y en blanco: la pantalla necesita saber
        que el campo existe, y a la vez no puede creerse que ya hay un logotipo puesto."""
        async with _cliente() as cliente:
            config = (await cliente.get("/api/v1/hub/themes/defaults")).json()["config"]

        assert "logoUrl" in config["branding"]
        assert config["branding"]["logoUrl"] is None

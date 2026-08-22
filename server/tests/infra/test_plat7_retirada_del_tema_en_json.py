"""PLAT.7 — la columna que nadie leía y el guardarraíl que impide que vuelva.

`hub_organizaciones.theme_config` era una columna JSONB con un `<textarea>` a la vista
—«Configuración de tema (JSON)»— y **ningún lector**: la cascada resuelve desde `hub_themes`.
Dos sitios para lo mismo, y el visible era el que no hacía nada. Antes de PLAT.6 no se podía
retirar sin dejar hueco; ahora hay pantalla que lo sustituye.

Comprobado antes de borrar, como exige el prompt: las cinco organizaciones de la base de
desarrollo tenían `{}`. Ninguna llevaba configuración que alguien hubiera escrito creyendo que
servía.

El guardarraíl es contra la reaparición, no contra el borrado: una columna muerta que vuelve lo
hace por copiar y pegar un DTO, y nadie mira el modelo entero al revisarlo.
"""
from __future__ import annotations


class TestLaColumnaNoVuelve:

    def test_should_not_have_theme_config_on_the_organisation_model(self):
        from server.app.modules.agents_hub.database.config_models import HubOrganizacion

        columnas = {c.name for c in HubOrganizacion.__table__.columns}

        assert "theme_config" not in columnas, (
            "la identidad visual de una organización vive en `hub_themes` y se configura en "
            "/plataforma/identidad-visual (PLAT.6). Una segunda copia en JSONB no la lee nadie."
        )

    def test_should_not_expose_theme_config_in_the_organisation_dtos(self):
        from server.app.routers.hub_organizaciones_router import (
            OrganizacionCreate,
            OrganizacionRead,
            OrganizacionUpdate,
        )

        for dto in (OrganizacionRead, OrganizacionCreate, OrganizacionUpdate):
            assert "theme_config" not in dto.model_fields, dto.__name__

    def test_should_keep_it_on_the_chatbot_where_it_is_a_live_pointer(self):
        """En `HubChatbot` **sí** se lee: guarda `{"theme_id": ...}`, que es de donde el widget
        saca su tema. Retirar la de organizaciones no es retirar las dos."""
        from server.app.modules.agents_hub.database.config_models import HubChatbot

        assert "theme_config" in {c.name for c in HubChatbot.__table__.columns}

"""Tests SEC.8.6 — los temas viven en la base de datos, no en el disco del contenedor.

`hub_themes_router` guardaba cada tema como un `.json` bajo `data/themes`, una ruta
**relativa al directorio de trabajo**. El propio código lo decía: «Almacenamiento
simplificado (en producción usar BD)».

En Cloud Run eso no es un detalle de implementación: el contenedor es efímero y hay varias
instancias, así que un tema creado desde una instancia no existe para las demás y
desaparece al reciclarse. Y arrastra al widget: el arreglo del hallazgo #3 de MAN.2 guarda
en BD solo el puntero `{"theme_id": ...}` y resuelve el contenido leyendo ese fichero, de
modo que en producción el widget volvería a quedarse sin tema —con el puntero intacto, que
es lo que hace el fallo difícil de leer—.
"""
from __future__ import annotations

import uuid

import pytest


@pytest.fixture
async def organizacion(db_session):
    from server.app.modules.agents_hub.database.config_models import HubOrganizacion

    org = HubOrganizacion(id=uuid.uuid4(), name="Organización de prueba", partner_id="p1")
    db_session.add(org)
    await db_session.commit()
    return org


class TestElTemaSeGuardaEnLaBaseDeDatos:

    async def test_should_persist_a_theme_as_a_row(self, db_session, organizacion):
        from sqlalchemy import select

        from server.app.modules.agents_hub.database.config_models import HubTheme

        tema = HubTheme(
            id=uuid.uuid4(),
            name="Institucional",
            organizacion_id=organizacion.id,
            config={"name": "institucional", "version": "1.0.0", "colors": {"primary": "#036"}},
            created_by="admin-1",
        )
        db_session.add(tema)
        await db_session.commit()

        recuperado = (
            await db_session.execute(select(HubTheme).where(HubTheme.id == tema.id))
        ).scalar_one()

        assert recuperado.name == "Institucional"
        assert recuperado.config["colors"]["primary"] == "#036"
        assert recuperado.organizacion_id == organizacion.id

    async def test_should_allow_a_platform_theme_without_organization(self, db_session):
        """Un tema sin organización es de plataforma y lo hereda la cascada entera."""
        from server.app.modules.agents_hub.database.config_models import HubTheme

        tema = HubTheme(
            id=uuid.uuid4(),
            name="Plataforma",
            organizacion_id=None,
            config={"name": "plataforma", "version": "1.0.0"},
            created_by="root",
        )
        db_session.add(tema)
        await db_session.commit()

        assert tema.organizacion_id is None

    async def test_should_belong_to_the_config_base_so_it_syncs_to_edge(self):
        """Un tema es configuración institucional, no dato operacional del cliente: va
        en `HubConfigBase` para que la sincronización cloud→edge lo arrastre."""
        from server.app.modules.agents_hub.database.base import HubConfigBase
        from server.app.modules.agents_hub.database.config_models import HubTheme

        assert issubclass(HubTheme, HubConfigBase)


class TestElRouterNoTocaElDisco:

    def test_should_not_keep_a_local_themes_directory(self):
        """El guardarraíl del cambio: mientras exista el `THEMES_DIR` relativo, el tema
        sigue dependiendo del disco de la instancia aunque haya tabla.

        Se comprueba el **módulo cargado** y no el texto del fichero: la explicación de por
        qué se retiró el almacén de ficheros vive en los comentarios, y buscar la cadena
        obligaría a no poder contarla.
        """
        from server.app.routers import hub_themes_router as modulo

        assert not hasattr(modulo, "THEMES_DIR"), (
            "el router aún declara un directorio local de temas"
        )
        assert not hasattr(modulo, "_save_theme"), (
            "el router aún tiene el escritor a disco"
        )
        assert not hasattr(modulo, "_theme_path")

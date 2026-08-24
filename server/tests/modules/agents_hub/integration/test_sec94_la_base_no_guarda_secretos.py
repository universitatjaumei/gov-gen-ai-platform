"""SEC.9.4 — La base de datos guarda un puntero al secreto, nunca el secreto.

MT.2 dejó tres métodos para obtener la credencial de un proveedor, y uno de ellos —`clave`—
guardaba **la clave literal en la base de datos**, en texto plano y sin cifrar. No estaba expuesto
por HTTP (no hay router para esa tabla), así que el riesgo no era un endpoint: era un volcado, una
copia de seguridad, una réplica de lectura o el payload de la sincronización cloud→edge.

**Decisión del usuario (2026-08-24): se restringe el método en vez de cifrar.** Las dos opciones
protegen contra cosas distintas y conviene tenerlo escrito:

- *Cifrar en reposo* cubre leer la base sin pasar por la aplicación, pero no el compromiso de la
  aplicación: la app tiene que descifrar, así que la clave de cifrado vive en el entorno del mismo
  proceso — el secreto se mueve de «dentro de la BD» a «en el entorno del proceso que lee la BD»,
  que es donde ya estaba con los otros dos métodos. Y trae peso permanente: rotar obliga a
  recifrar, perder la clave es perder todas las credenciales, la copia sólo es restaurable con la
  clave, el edge la necesita también, y aparece un fallo nuevo —«no puedo descifrar»— que se
  manifiesta como una caída.
- *Restringir* deja en la base un **puntero**: el nombre de una variable de entorno, o nada (ADC).
  Volcados, copias, réplicas y la sincronización dejan de ser sensibles **por construcción**, y no
  hay clave que gestionar. Es lo que ya dicen las reglas del proyecto: secretos por variable de
  entorno, Secret Manager en producción.

Se puede hacer ahora sin migrar datos porque la tabla tiene **cero filas**. El coste es el
autoservicio del panel, y su recuperación está anotada en **MT.10** con un `SecretProvider` que
guarda el nombre del recurso y no el valor.

Lo que este prompt **no** toca, y queda anotado: `hub_providers.api_key`, que es la otra columna de
secreto en claro y **sí tiene datos**. Retirarla cambia la cadena de `model_factory` y el
formulario del proveedor, así que va aparte.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError

from server.app.modules.agents_hub.database.config_models import (
    HubOrganizacion,
    HubProvider,
    HubProviderCredential,
    MetodoDeCredencial,
)
from server.app.modules.agents_hub.services.credenciales_llm import resolver_credencial


def _uid() -> str:
    return uuid.uuid4().hex[:10]


async def _proveedor(session) -> HubProvider:
    fila = HubProvider(id=f"prov-{_uid()}", name="Proveedor", provider_type="google_genai")
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


async def _organizacion(session) -> HubOrganizacion:
    fila = HubOrganizacion(name=f"Onda {_uid()}", partner_id=f"p-{_uid()}")
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


class TestNoHayDondeGuardarUnSecreto:

    def test_should_not_offer_a_method_that_stores_the_key(self):
        valores = {m.value for m in MetodoDeCredencial}
        assert "clave" not in valores
        assert valores == {"variable_de_entorno", "entorno_de_ejecucion"}

    def test_should_not_have_a_column_for_the_secret(self):
        """La garantía más fuerte no es «no lo guardamos», es «no hay dónde»."""
        columnas = set(HubProviderCredential.__table__.columns.keys())
        assert "api_key" not in columnas
        assert "secret_env" in columnas

    @pytest.mark.asyncio
    async def test_should_reject_the_literal_key_method_in_the_database(self, db_session):
        """El `CheckConstraint` es el que impide que vuelva por un `INSERT` a mano."""
        proveedor = await _proveedor(db_session)
        db_session.add(
            HubProviderCredential(
                provider_id=proveedor.id, organizacion_id=None, metodo="clave"
            )
        )

        with pytest.raises((IntegrityError, DBAPIError)):
            await db_session.commit()
        await db_session.rollback()


class TestElFalloDiceQueFaltaYDeQuien:

    @pytest.mark.asyncio
    async def test_should_say_which_variable_is_missing_and_for_which_organisation(
        self, db_session, monkeypatch
    ):
        """Quien recibe el fallo tiene que poder arreglarlo sin adivinar: **qué** variable falta
        y **de qué organización** es la credencial que la pedía. Con varias organizaciones y una
        variable por cada una, «no está definida» a secas no dice cuál poner."""
        monkeypatch.delenv("GOOGLE_API_KEY_ONDA", raising=False)
        proveedor = await _proveedor(db_session)
        organizacion = await _organizacion(db_session)
        db_session.add(
            HubProviderCredential(
                provider_id=proveedor.id,
                organizacion_id=organizacion.id,
                metodo=MetodoDeCredencial.VARIABLE_DE_ENTORNO,
                secret_env="GOOGLE_API_KEY_ONDA",
            )
        )
        await db_session.commit()

        resuelta = await resolver_credencial(
            db_session, proveedor.id, organizacion_id=organizacion.id
        )

        assert resuelta is not None
        assert resuelta.api_key is None
        assert resuelta.falta is not None
        assert "GOOGLE_API_KEY_ONDA" in resuelta.falta
        assert str(organizacion.id) in resuelta.falta

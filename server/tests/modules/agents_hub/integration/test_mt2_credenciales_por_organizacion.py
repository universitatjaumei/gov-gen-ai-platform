"""MT.2 — proveedores y modelos dejan de ser globales.

Una sola credencial para todos significa, en el modelo Diputación→municipios, que el consumo de
un ayuntamiento se factura al contrato de otro y que sus prompts viajan por ese contrato. No es
incomodidad: es coste mal atribuido y protección de datos.

**Desviación documentada respecto al plan.** El plan decía «`organizacion_id` nullable en las dos
tablas». En `hub_llm_configs` eso funciona tal cual. En `hub_providers` no: su clave primaria es
el texto `google` / `vertex`, así que añadir una columna no permite que dos organizaciones tengan
cada una su Google — haría falta cambiar la clave primaria de una tabla con clave ajena y romper
`/providers/{provider_id}`. Y no hace falta: al mirar las cuatro filas reales resulta que
`hub_providers` **es un catálogo de tipos** (Google, Vertex, Ollama, OpenRouter) y **ninguna tiene
`api_key`**. Lo que tiene que separarse por organización es la credencial, no el catálogo.

Así que la credencial se va a su propia tabla, heredable por la cascada de MT.1, y declara **cómo**
se obtiene. Los tres métodos son los que ya están en uso hoy:

- `clave`: la clave literal, en la base de datos.
- `variable_de_entorno`: la base guarda **el nombre** de la variable, no el secreto. Es la que
  sirve al despliegue en GCP —Secret Manager monta una variable por organización— y la única que
  permite credenciales por organización sin meter secretos en la base.
- `entorno_de_ejecucion`: ADC de Vertex, sin clave. **Con un límite que conviene decir**: un
  proceso tiene una sola identidad ADC, así que esto sólo puede diferir por organización en modo
  `edge` —un despliegue por municipio—. En cloud-only es necesariamente de plataforma, y el test
  del final lo fija para que nadie espere otra cosa.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from server.app.core.ambito import Ambito, ambito_de
from server.app.modules.agents_hub.database.config_models import (
    HubLLMConfig,
    HubOrganizacion,
    HubProvider,
    HubProviderCredential,
    MetodoDeCredencial,
)
from server.app.modules.agents_hub.services.credenciales_llm import (
    CredencialDeProveedor,
    resolver_credencial,
)


def _uid() -> str:
    return uuid.uuid4().hex[:10]


async def _organizacion(session, nombre: str) -> HubOrganizacion:
    fila = HubOrganizacion(name=f"{nombre} {_uid()}", partner_id=f"p-{_uid()}")
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


async def _proveedor(session, *, tipo: str = "google_genai") -> HubProvider:
    fila = HubProvider(id=f"prov-{_uid()}", name="Proveedor", provider_type=tipo)
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


async def _credencial(session, proveedor, organizacion, **campos) -> HubProviderCredential:
    fila = HubProviderCredential(
        provider_id=proveedor.id,
        organizacion_id=organizacion.id if organizacion is not None else None,
        **campos,
    )
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


class TestLaCredencialEsDeQuienLaPaga:

    @pytest.mark.asyncio
    async def test_should_prefer_the_organisation_credential_over_the_platform_one(
        self, db_session
    ):
        proveedor = await _proveedor(db_session)
        una = await _organizacion(db_session, "Vila-real")
        await _credencial(
            db_session, proveedor, None,
            metodo=MetodoDeCredencial.CLAVE, api_key="la-de-plataforma",
        )
        await _credencial(
            db_session, proveedor, una,
            metodo=MetodoDeCredencial.CLAVE, api_key="la-de-vila-real",
        )

        resuelta = await resolver_credencial(db_session, proveedor.id, una.id)

        assert resuelta.api_key == "la-de-vila-real"

    @pytest.mark.asyncio
    async def test_should_fall_back_to_the_platform_credential(self, db_session):
        """Sin credencial propia, la de plataforma. **Es lo que hace segura la fase 1**: sin
        ninguna fila en la tabla nueva, el piloto se comporta exactamente como hoy."""
        proveedor = await _proveedor(db_session)
        una = await _organizacion(db_session, "Borriana")
        await _credencial(
            db_session, proveedor, None,
            metodo=MetodoDeCredencial.CLAVE, api_key="la-de-plataforma",
        )

        resuelta = await resolver_credencial(db_session, proveedor.id, una.id)

        assert resuelta.api_key == "la-de-plataforma"

    @pytest.mark.asyncio
    async def test_should_not_leak_an_api_key_across_organisations(self, db_session):
        """**El test que justifica el prompt.** Resolver para A no puede devolver la
        credencial de B, ni por un `ORDER BY` mal puesto ni por un `first()` sobre un listado
        sin filtrar. Lo que está en juego es el secreto de otro contrato."""
        proveedor = await _proveedor(db_session)
        una = await _organizacion(db_session, "Onda")
        otra = await _organizacion(db_session, "Nules")
        await _credencial(
            db_session, proveedor, otra,
            metodo=MetodoDeCredencial.CLAVE, api_key="secreto-de-nules",
        )

        resuelta = await resolver_credencial(db_session, proveedor.id, una.id)

        # Sin credencial propia ni de plataforma: no hay credencial. **No la del vecino.**
        assert resuelta is None or resuelta.api_key != "secreto-de-nules"

    @pytest.mark.asyncio
    async def test_should_keep_the_secret_out_of_the_database(self, db_session, monkeypatch):
        """El método que sirve al despliegue en GCP: la base guarda **el nombre** de la
        variable y el secreto vive en el entorno. Es lo que permite una credencial por
        organización sin que ningún secreto entre en la base de datos."""
        proveedor = await _proveedor(db_session)
        una = await _organizacion(db_session, "Almassora")
        monkeypatch.setenv("GOOGLE_API_KEY_ALMASSORA", "de-secret-manager")
        await _credencial(
            db_session, proveedor, una,
            metodo=MetodoDeCredencial.VARIABLE_DE_ENTORNO,
            secret_env="GOOGLE_API_KEY_ALMASSORA",
        )

        resuelta = await resolver_credencial(db_session, proveedor.id, una.id)

        assert resuelta.api_key == "de-secret-manager"
        assert resuelta.metodo is MetodoDeCredencial.VARIABLE_DE_ENTORNO

    @pytest.mark.asyncio
    async def test_should_say_which_variable_is_missing(self, db_session):
        """Una variable declarada y no puesta es un error de despliegue, y tiene que decir
        cuál: «falta la clave» manda a leer código, «falta GOOGLE_API_KEY_ONDA» se arregla."""
        proveedor = await _proveedor(db_session)
        una = await _organizacion(db_session, "Onda")
        await _credencial(
            db_session, proveedor, una,
            metodo=MetodoDeCredencial.VARIABLE_DE_ENTORNO,
            secret_env="NO_PUESTA_A_PROPOSITO",
        )

        resuelta = await resolver_credencial(db_session, proveedor.id, una.id)

        assert resuelta.api_key is None
        assert "NO_PUESTA_A_PROPOSITO" in (resuelta.falta or "")

    @pytest.mark.asyncio
    async def test_should_allow_a_provider_with_no_key_at_all(self, db_session):
        """Vertex no lleva clave: usa las credenciales del entorno de ejecución (ADC). Sin un
        método que lo diga, «sin clave» sería indistinguible de «mal configurado»."""
        proveedor = await _proveedor(db_session, tipo="google_vertexai")
        await _credencial(
            db_session, proveedor, None, metodo=MetodoDeCredencial.ENTORNO_DE_EJECUCION
        )

        resuelta = await resolver_credencial(db_session, proveedor.id, None)

        assert resuelta.metodo is MetodoDeCredencial.ENTORNO_DE_EJECUCION
        assert resuelta.api_key is None
        assert resuelta.falta is None, "ADC sin clave no es una carencia"

    @pytest.mark.asyncio
    async def test_should_override_the_base_url_per_organisation(self, db_session):
        """Un municipio con su propio Ollama en su propia red: el catálogo da la `base_url`
        por omisión y la credencial la puede cambiar, porque el «dónde» y el «con qué» son la
        misma decisión de contrato."""
        proveedor = await _proveedor(db_session, tipo="openai_compatible")
        una = await _organizacion(db_session, "Vinaròs")
        await _credencial(
            db_session, proveedor, una,
            metodo=MetodoDeCredencial.CLAVE, api_key="k", base_url="http://ollama.vinaros:11434/v1",
        )

        resuelta = await resolver_credencial(db_session, proveedor.id, una.id)

        assert resuelta.base_url == "http://ollama.vinaros:11434/v1"

    @pytest.mark.asyncio
    async def test_should_resolve_nothing_when_there_is_nothing(self, db_session):
        """Sin ninguna fila, `None`: es el estado de hoy, y el que hace que el piloto siga
        usando la cadena de siempre (clave del proveedor → variable de la config → variable
        por omisión) sin enterarse de que esta tabla existe."""
        proveedor = await _proveedor(db_session)

        assert await resolver_credencial(db_session, proveedor.id, None) is None


class TestUnaPorNivelYAmbito:

    @pytest.mark.asyncio
    async def test_should_let_two_organisations_have_their_own_default(self, db_session):
        """Hoy la unicidad de `is_default` es de hecho global, y `_relevar_default` degrada
        todas las del nivel: promover el nivel 1 de Onda dejaría a Vila-real sin el suyo."""
        proveedor = await _proveedor(db_session)
        una = await _organizacion(db_session, "Onda")
        otra = await _organizacion(db_session, "Vila-real")

        for organizacion in (una, otra):
            db_session.add(
                HubLLMConfig(
                    provider=proveedor.id,
                    model_name="gemini",
                    tier=1,
                    purpose="chat",
                    is_default=True,
                    organizacion_id=organizacion.id,
                )
            )
        await db_session.commit()

        filas = (
            await db_session.execute(
                select(HubLLMConfig).where(
                    HubLLMConfig.organizacion_id.in_([una.id, otra.id]),
                    HubLLMConfig.is_default.is_(True),
                )
            )
        ).scalars().all()

        assert len(filas) == 2

    @pytest.mark.asyncio
    async def test_should_not_demote_a_default_of_another_purpose(self, db_session):
        """**Fallo preexistente, encontrado leyendo `_relevar_default`.** Degradaba por nivel
        ignorando el propósito, y hoy conviven un chat nivel 1 y un embedding nivel 1 marcados
        por defecto: promover uno de chat desde la pantalla habría dejado la plataforma sin
        modelo de embeddings, y eso no se nota hasta la siguiente ingesta."""
        from server.app.routers.hub_llm_configs_router import _relevar_default

        proveedor = await _proveedor(db_session)
        embedding = HubLLMConfig(
            provider=proveedor.id,
            model_name="gemini-embedding-001",
            tier=1,
            purpose="embedding",
            is_default=True,
        )
        db_session.add(embedding)
        await db_session.commit()
        await db_session.refresh(embedding)

        await _relevar_default(db_session, tier=1, purpose="chat", organizacion_id=None)
        await db_session.commit()
        await db_session.refresh(embedding)

        assert embedding.is_default is True, "el defecto de embeddings no es del chat"

    @pytest.mark.asyncio
    async def test_should_not_demote_the_default_of_another_organisation(self, db_session):
        proveedor = await _proveedor(db_session)
        from server.app.routers.hub_llm_configs_router import _relevar_default

        otra = await _organizacion(db_session, "Nules")
        suya = HubLLMConfig(
            provider=proveedor.id,
            model_name="gemini",
            tier=1,
            purpose="chat",
            is_default=True,
            organizacion_id=otra.id,
        )
        db_session.add(suya)
        await db_session.commit()
        await db_session.refresh(suya)

        una = await _organizacion(db_session, "Onda")
        await _relevar_default(db_session, tier=1, purpose="chat", organizacion_id=una.id)
        await db_session.commit()
        await db_session.refresh(suya)

        assert suya.is_default is True


class TestElEsquemaDiceLaVerdad:

    def test_should_declare_the_new_scopes(self):
        """`hub_llm_configs` pasa a heredable —ya tiene la columna— y `hub_providers` **sigue
        siendo de plataforma**, porque es un catálogo de tipos: Google es Google en todos los
        municipios. El test de coherencia de MT.1 no dejaría declarar lo contrario."""
        assert ambito_de(HubLLMConfig).ambito is Ambito.HEREDABLE
        assert ambito_de(HubProvider).ambito is Ambito.PLATAFORMA
        assert ambito_de(HubProviderCredential).ambito is Ambito.HEREDABLE

    @pytest.mark.asyncio
    async def test_should_migrate_existing_rows_to_the_platform_level(self, db_session):
        """Las filas que ya existen quedan a nulo, que es «plataforma»: es la condición para
        que el piloto no note la migración."""
        proveedor = await _proveedor(db_session)
        antigua = HubLLMConfig(
            provider=proveedor.id, model_name="gemini", tier=1, purpose="chat"
        )
        db_session.add(antigua)
        await db_session.commit()
        await db_session.refresh(antigua)

        assert antigua.organizacion_id is None

    @pytest.mark.asyncio
    async def test_should_refuse_two_credentials_for_the_same_scope(self, db_session):
        """Dos credenciales del mismo proveedor para la misma organización serían dos
        respuestas a una pregunta con una sola: cuál gana lo decidiría el `ORDER BY`.

        **La restricción va con `NULLS NOT DISTINCT`**, que es lo que la hace valer también en
        el nivel de plataforma: en Postgres `NULL != NULL`, así que una única corriente
        dejaría meter dos filas de plataforma sin protestar — el caso más probable, porque es
        el único nivel que existe hoy.
        """
        from sqlalchemy.exc import IntegrityError

        proveedor = await _proveedor(db_session)
        await _credencial(
            db_session, proveedor, None, metodo=MetodoDeCredencial.CLAVE, api_key="una"
        )

        with pytest.raises(IntegrityError):
            await _credencial(
                db_session, proveedor, None, metodo=MetodoDeCredencial.CLAVE, api_key="otra"
            )
        await db_session.rollback()

    @pytest.mark.asyncio
    async def test_should_refuse_a_method_that_no_code_consumes(self, db_session):
        """`CheckConstraint` sobre el método, al contrario que el vocabulario del corpus
        (CLAUDE.md §5): son tres valores estables, cada uno con su rama en el código, y añadir
        un cuarto exige escribir la rama que lo consuma."""
        from sqlalchemy.exc import IntegrityError

        proveedor = await _proveedor(db_session)
        db_session.add(
            HubProviderCredential(
                provider_id=proveedor.id, organizacion_id=None, metodo="telepatia"
            )
        )
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()


class TestLoQueNoSePuedePrometer:

    @pytest.mark.asyncio
    async def test_should_admit_that_adc_cannot_differ_within_one_process(self, db_session):
        """Un proceso tiene **una sola** identidad ADC, así que «ADC por organización» sólo
        tiene sentido en modo `edge`, con un despliegue por municipio. Declararlo en una
        organización en modo cloud sería configuración que parece funcionar: se rechaza al
        resolver, con el motivo dicho.
        """
        proveedor = await _proveedor(db_session, tipo="google_vertexai")
        una = await _organizacion(db_session, "Alcora")
        await _credencial(
            db_session, proveedor, una, metodo=MetodoDeCredencial.ENTORNO_DE_EJECUCION
        )

        resuelta = await resolver_credencial(
            db_session, proveedor.id, una.id, modo_de_despliegue="cloud"
        )

        assert isinstance(resuelta, CredencialDeProveedor)
        assert "edge" in (resuelta.falta or "").lower()

    @pytest.mark.asyncio
    async def test_should_accept_adc_per_organisation_on_edge(self, db_session):
        proveedor = await _proveedor(db_session, tipo="google_vertexai")
        una = await _organizacion(db_session, "Alcora")
        await _credencial(
            db_session, proveedor, una, metodo=MetodoDeCredencial.ENTORNO_DE_EJECUCION
        )

        resuelta = await resolver_credencial(
            db_session, proveedor.id, una.id, modo_de_despliegue="edge"
        )

        assert resuelta.falta is None

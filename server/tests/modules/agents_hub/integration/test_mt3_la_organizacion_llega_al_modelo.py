"""MT.3 — quien pide un modelo dice para quién.

MT.2 puso la cascada en la base de datos y por sí sola no sirve de nada: `get_model_for_tier`
**no recibía la organización**, así que nadie le decía contra qué resolver y el nivel de
organización nunca se habría consultado. Ocho sitios lo llaman.

**El parámetro es obligatorio y no opcional con valor por omisión, y ésa es la decisión del
prompt.** Un opcional se olvida, y el fallo es silencioso: resuelve el modelo de la plataforma
cuando debía resolver el del municipio, la respuesta llega igual de bien escrita y el consumo se
carga al contrato equivocado. Nada falla, así que ningún test lo caza. Con un parámetro
obligatorio, un sitio que no sepa la respuesta **tiene que escribir que no la sabe**, y eso se ve
en una revisión.

De dónde la saca cada llamador está en el test que le corresponde: la ingesta del chatbot, el
rastreo del sitio, y los de Informes de quien pide —hasta que MT.4 le dé la dimensión al módulo—.
"""
from __future__ import annotations

import uuid

import pytest

from server.app.core.auth.models import UserInfo
from server.app.core.auth.tenancy import organizacion_unica_de
from server.app.modules.agents_hub.database.config_models import (
    HubLLMConfig,
    HubOrganizacion,
    HubProvider,
)
from server.app.modules.agents_hub.services.config_provider import LocalConfigProvider


def _uid() -> str:
    return uuid.uuid4().hex[:10]


async def _organizacion(session) -> HubOrganizacion:
    fila = HubOrganizacion(name=f"Org {_uid()}", partner_id=f"p-{_uid()}")
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


async def _proveedor(session) -> HubProvider:
    fila = HubProvider(id=f"prov-{_uid()}", name="P", provider_type="google_genai")
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


async def _modelo(session, proveedor, *, organizacion=None, nombre="gemini", tier=1):
    fila = HubLLMConfig(
        provider=proveedor.id,
        model_name=nombre,
        tier=tier,
        purpose="chat",
        is_default=True,
        organizacion_id=organizacion.id if organizacion is not None else None,
    )
    session.add(fila)
    await session.commit()
    await session.refresh(fila)
    return fila


class TestLaCascadaLlegaHastaElModelo:

    @pytest.mark.asyncio
    async def test_should_prefer_the_organisation_model_over_the_platform_one(self, db_session):
        proveedor = await _proveedor(db_session)
        una = await _organizacion(db_session)
        await _modelo(db_session, proveedor, nombre="de-plataforma")
        await _modelo(db_session, proveedor, organizacion=una, nombre="de-la-organizacion")

        config = await LocalConfigProvider(db_session).get_llm_config_for_tier(
            1, organizacion_id=una.id
        )

        assert config.model_name == "de-la-organizacion"

    @pytest.mark.asyncio
    async def test_should_fall_back_to_the_platform_model(self, db_session):
        """Sin modelo propio, el de plataforma. **Es lo que hace que el piloto no note MT.2**:
        sus siete filas están todas a nulo."""
        proveedor = await _proveedor(db_session)
        una = await _organizacion(db_session)
        await _modelo(db_session, proveedor, nombre="de-plataforma")

        config = await LocalConfigProvider(db_session).get_llm_config_for_tier(
            1, organizacion_id=una.id
        )

        assert config.model_name == "de-plataforma"

    @pytest.mark.asyncio
    async def test_should_not_use_the_model_of_another_organisation(self, db_session):
        """**El test que importa.** Resolver para A y devolver el modelo de B no es sólo un
        modelo equivocado: es el consumo cargado al contrato de otro municipio."""
        proveedor = await _proveedor(db_session)
        una = await _organizacion(db_session)
        otra = await _organizacion(db_session)
        await _modelo(db_session, proveedor, organizacion=otra, nombre="del-vecino")

        config = await LocalConfigProvider(db_session).get_llm_config_for_tier(
            1, organizacion_id=una.id
        )

        assert config is None, "sin modelo propio ni de plataforma, no hay modelo"

    @pytest.mark.asyncio
    async def test_should_keep_ignoring_models_that_are_not_for_chat(self, db_session):
        """Lo que ya protegía este método no se pierde al añadirle el eje: la configuración de
        embeddings del piloto está marcada por defecto en el nivel 1, y devolverla a quien pide
        un modelo para redactar reventaba mucho más lejos y acusando al proveedor."""
        proveedor = await _proveedor(db_session)
        una = await _organizacion(db_session)
        embedding = HubLLMConfig(
            provider=proveedor.id,
            model_name="gemini-embedding-001",
            tier=1,
            purpose="embedding",
            is_default=True,
            organizacion_id=una.id,
        )
        db_session.add(embedding)
        await db_session.commit()

        config = await LocalConfigProvider(db_session).get_llm_config_for_tier(
            1, organizacion_id=una.id
        )

        assert config is None


class TestQuienPideDiceParaQuien:

    def test_should_require_the_organisation_to_resolve_a_tier(self):
        """La firma lo exige. **No un opcional con valor por omisión**: un opcional se olvida y
        el fallo es silencioso —resuelve plataforma cuando debía resolver la organización—, así
        que no lo caza ningún test. Obligatorio, el sitio que no sepa la respuesta tiene que
        escribir que no la sabe."""
        import inspect

        from server.app.modules.agents_hub.services.model_factory import get_model_for_tier

        parametro = inspect.signature(get_model_for_tier).parameters["organizacion_id"]
        assert parametro.default is inspect.Parameter.empty, (
            "organizacion_id no puede tener valor por omisión: un opcional se olvida y "
            "resolver plataforma en vez de la organización no rompe nada visible"
        )

    def test_should_have_no_caller_left_on_the_old_signature(self):
        """Ningún llamador se queda con la resolución vieja, que es el riesgo del prompt: uno
        olvidado seguiría funcionando —resolviendo plataforma— y no lo delataría nada.

        Se recorre el **árbol sintáctico** y no las líneas: las llamadas están formateadas en
        varias líneas, y un `grep` por línea daría por incumplido lo que sí cumple y, lo que es
        peor, por cumplido lo que no en cuanto alguien reformateara. Además comprueba lo que de
        verdad importa —que el argumento va **nombrado**—: en una llamada de tres, el tercero
        posicional no le dice nada a quien lee el diff.
        """
        import ast
        from pathlib import Path

        raiz = Path(__file__).resolve().parents[4] / "app"
        pendientes: list[str] = []
        for fichero in raiz.rglob("*.py"):
            arbol = ast.parse(fichero.read_text(encoding="utf-8"))
            for nodo in ast.walk(arbol):
                if not isinstance(nodo, ast.Call):
                    continue
                nombre = getattr(nodo.func, "id", None) or getattr(nodo.func, "attr", None)
                if nombre != "get_model_for_tier":
                    continue
                if not any(k.arg == "organizacion_id" for k in nodo.keywords):
                    pendientes.append(f"{fichero.name}:{nodo.lineno}")

        assert pendientes == [], (
            "Estas llamadas no dicen para qué organización piden el modelo: " + ", ".join(pendientes)
        )


class TestDeDondeSaleLaOrganizacionDeCadaUno:

    def test_should_take_it_from_the_actor_when_they_belong_to_exactly_one(self):
        """Los llamadores de Informes la sacan de quien pide, que es lo único que hay hasta que
        MT.4 le dé la dimensión al módulo. **Sólo cuando pertenece a una**: con varias no hay
        forma de saber cuál es «la suya», y en un superadministrador la lista vacía significa
        «todas» — en los dos casos, plataforma, que es la respuesta honesta y además el
        comportamiento de hoy. Es el mismo criterio que REV.12 aplicó a la marca.
        """
        una = uuid.uuid4()

        de_una = UserInfo(
            user_id="1", email="a@uji.es", role="user", organizacion_ids=(str(una),)
        )
        assert organizacion_unica_de(de_una) == una

        de_varias = UserInfo(
            user_id="2",
            email="b@uji.es",
            role="admin",
            organizacion_ids=(str(una), str(uuid.uuid4())),
        )
        assert organizacion_unica_de(de_varias) is None

        superadmin = UserInfo(
            user_id="3", email="root@uji.es", role="superadmin", organizacion_ids=()
        )
        assert organizacion_unica_de(superadmin) is None

    def test_should_survive_a_claim_that_is_not_a_uuid(self):
        """Un claim mal poblado no puede reventar la resolución del modelo: sería un 500 en el
        chat por un dato de identidad, y el modo degradado correcto es «plataforma»."""
        roto = UserInfo(
            user_id="4", email="c@uji.es", role="user", organizacion_ids=("no-es-un-uuid",)
        )

        assert organizacion_unica_de(roto) is None

    @pytest.mark.asyncio
    async def test_should_take_it_from_the_chatbot_on_ingestion(self, db_session):
        """La ingesta la saca del chatbot, que sí la tiene NOT NULL. Es el único llamador que
        no necesita esperar a MT.4."""
        from server.app.modules.agents_hub.database.config_models import HubChatbot

        proveedor = await _proveedor(db_session)
        una = await _organizacion(db_session)
        modelo = await _modelo(db_session, proveedor)

        bot = HubChatbot(
            name=f"Bot {_uid()}",
            organizacion_id=una.id,
            llm_config_id=modelo.id,
            system_prompt="Eres útil.",
            sources=[],
        )
        db_session.add(bot)
        await db_session.commit()
        await db_session.refresh(bot)

        assert bot.organizacion_id == una.id

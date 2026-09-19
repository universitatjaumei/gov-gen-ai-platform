"""SEC.9.3 — El prompt de una actividad es de su organización, no de quien llegue antes.

**El agujero** (auditoría del 2026-08-24): MT.6 le dio a `hub_activity_prompts` su
`organizacion_id` y cambió la clave única a `(activity, organizacion_id)` con `NULLS NOT
DISTINCT`, de modo que pueden convivir la fila de plataforma y la de cada organización. El
**lector** (`config_provider`) respeta la cadena organización → plataforma → código. El
**escritor** no se enteró: `_fila()` buscaba `WHERE activity == ...` y se quedaba con la primera.

Consecuencia, con `_require_admin` de rol y sin `require_module`: cualquier administrador de
cualquier organización podía leer, **sobrescribir o borrar** el prompt de plataforma —el que
heredan todas—. Y como ese texto va al LLM, no es sólo un cambio de configuración ajena: es
inyección de prompt en las llamadas de las demás organizaciones.

De paso, MT.6 dejó la funcionalidad inalcanzable en la otra dirección: **no había forma por API de
crear un override *de organización***, porque el escritor nunca ponía la columna.

La organización objetivo se nombra como en REV.12 (`/hub/themes/resolved`): el cliente puede
declararla —es la del selector de la cabecera— y se comprueba con `assert_org_access`; si no la
declara, se usa la suya cuando tiene una sola. Nulo es el nivel de plataforma, y ése es del
superadministrador.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock


from server.app.core.auth.models import UserInfo

ORG_A = str(uuid.UUID("00000000-0000-0000-0000-0000000000a1"))
ORG_B = str(uuid.UUID("00000000-0000-0000-0000-0000000000b2"))

# Una actividad real del catálogo: inventarse una daría 422 y el test mediría eso.
def _una_actividad() -> str:
    from server.app.modules.redaccion.services.actividades_llm import ActividadLLM

    return str(next(iter(ActividadLLM)))


def _admin(*orgs: str) -> UserInfo:
    return UserInfo(
        user_id="00000000-0000-0000-0000-00000000dead",
        email="a@example.org",
        role="admin",
        organizacion_ids=orgs,
    )


def _superadmin() -> UserInfo:
    return UserInfo(
        user_id="00000000-0000-0000-0000-000000000001",
        email="root@example.org",
        role="superadmin",
    )


def _fila_de(org: str | None, texto: str):
    return SimpleNamespace(
        id=uuid.uuid4(),
        activity=_una_actividad(),
        organizacion_id=uuid.UUID(org) if org else None,
        template_text=texto,
        override_tier=2,
        version=1,
        updated_by=None,
        updated_at=None,
    )


def _sesion(fila=None):
    session = MagicMock()
    resultado = MagicMock()
    resultado.scalars.return_value.first.return_value = fila
    resultado.scalars.return_value.all.return_value = [fila] if fila else []
    session.execute = AsyncMock(return_value=resultado)
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()
    session.add = MagicMock()
    return session


def _cliente(principal: UserInfo, session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from server.app.api.deps import get_current_user, get_session, modulos_concedidos
    from server.app.routers.hub_activity_prompts_router import router

    async def _sesion_override():
        yield session

    app = FastAPI()
    app.dependency_overrides[get_current_user] = lambda: principal
    app.dependency_overrides[get_session] = _sesion_override
    app.dependency_overrides[modulos_concedidos] = lambda: ["plataforma"]
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def _sql_de(session) -> str:
    consulta = session.execute.await_args.args[0]
    return str(consulta.compile(compile_kwargs={"literal_binds": True}))


class TestElOverrideSeBuscaPorOrganizacion:

    def test_should_scope_the_lookup_to_the_actor_organisation(self):
        session = _sesion()
        resp = _cliente(_admin(ORG_A), session).get("/api/v1/hub/activity-prompts")

        assert resp.status_code == 200
        sql = _sql_de(session)
        assert uuid.UUID(ORG_A).hex in sql
        assert uuid.UUID(ORG_B).hex not in sql

    def test_should_not_take_the_prompt_of_another_organisation(self):
        """La fila que hay en la base es de ORG_B. Para un administrador de ORG_A el texto
        efectivo tiene que ser el del código, no el del vecino."""
        session = _sesion(fila=_fila_de(ORG_B, "TEXTO DEL VECINO"))
        resp = _cliente(_admin(ORG_A), session).get("/api/v1/hub/activity-prompts")

        assert resp.status_code == 200
        assert "TEXTO DEL VECINO" not in resp.text

    def test_should_accept_the_organisation_named_by_the_client(self):
        """Como en REV.12: la organización del selector de la cabecera viaja y se comprueba."""
        session = _sesion()
        resp = _cliente(_admin(ORG_A, ORG_B), session).get(
            f"/api/v1/hub/activity-prompts?organizacion_id={ORG_A}"
        )

        assert resp.status_code == 200
        assert uuid.UUID(ORG_A).hex in _sql_de(session)

    def test_should_forbid_naming_an_organisation_that_is_not_yours(self):
        session = _sesion()
        resp = _cliente(_admin(ORG_A), session).get(
            f"/api/v1/hub/activity-prompts?organizacion_id={ORG_B}"
        )

        assert resp.status_code == 403


class TestElNivelDePlataformaEsDelSuperadministrador:

    def test_should_write_the_override_of_the_actor_organisation(self):
        """Un administrador que guarda **crea la fila de su organización**, no toca la de
        plataforma. Antes esto era imposible por API: el escritor nunca ponía la columna."""
        session = _sesion()
        resp = _cliente(_admin(ORG_A), session).put(
            f"/api/v1/hub/activity-prompts/{_una_actividad()}",
            json={"override_tier": 2, "template_text": ""},
        )

        assert resp.status_code == 200
        creada = session.add.call_args.args[0]
        assert str(creada.organizacion_id) == ORG_A

    def test_should_forbid_overwriting_the_platform_prompt_from_an_org_admin(self):
        """La fila que existe es la de plataforma (`organizacion_id` nulo). Un administrador
        no la sobrescribe: si guarda, crea la suya y la de plataforma queda intacta."""
        de_plataforma = _fila_de(None, "EL DE TODAS")
        session = _sesion(fila=de_plataforma)

        resp = _cliente(_admin(ORG_A), session).put(
            f"/api/v1/hub/activity-prompts/{_una_actividad()}",
            json={"override_tier": 3, "template_text": ""},
        )

        assert resp.status_code == 200
        assert de_plataforma.template_text == "EL DE TODAS"
        assert de_plataforma.override_tier == 2
        creada = session.add.call_args.args[0]
        assert creada.organizacion_id is not None

    def test_should_forbid_deleting_another_organisations_override(self):
        """Borrar tiene que alcanzar sólo a la fila propia. La que hay es de ORG_B."""
        ajena = _fila_de(ORG_B, "TEXTO DEL VECINO")
        session = _sesion(fila=ajena)

        resp = _cliente(_admin(ORG_A), session).delete(
            f"/api/v1/hub/activity-prompts/{_una_actividad()}"
        )

        assert resp.status_code == 200
        session.delete.assert_not_awaited()

    def test_should_let_the_superadmin_manage_the_platform_level(self):
        session = _sesion()
        resp = _cliente(_superadmin(), session).put(
            f"/api/v1/hub/activity-prompts/{_una_actividad()}",
            json={"override_tier": 1, "template_text": ""},
        )

        assert resp.status_code == 200
        creada = session.add.call_args.args[0]
        assert creada.organizacion_id is None

    def test_should_ask_which_org_when_the_admin_manages_several(self):
        session = _sesion()
        resp = _cliente(_admin(ORG_A, ORG_B), session).put(
            f"/api/v1/hub/activity-prompts/{_una_actividad()}",
            json={"override_tier": 1, "template_text": ""},
        )

        assert resp.status_code == 400
        session.commit.assert_not_awaited()


class TestLaGuardaDeModulo:

    def test_should_require_the_platform_module_at_router_level(self):
        """El docstring declaraba «Módulo: plataforma» y no había ninguna dependencia. Es el
        mismo desajuste que PLAT.5 cerró en otros tres routers."""
        from server.app.routers.hub_activity_prompts_router import router

        assert router.dependencies, "sin require_module: la guarda vivía sólo en el docstring"

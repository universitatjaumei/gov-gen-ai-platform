"""Una plantilla de nivel plataforma la crea la plataforma, no un administrador de organización.

**El defecto (issue #90).** `approve_as_template` hacía:

    _require_admin = require_role("superadmin", "admin")
    ...
    if body.is_global and user.role != "admin":
        raise HTTPException(403, "Only admin can create global templates")

La dependencia deja pasar a **los dos** roles, y después esa línea bloquea a quien **no** sea
`"admin"` — o sea, precisamente al superadministrador. Tiene dos mitades y la segunda es la
grave:

- la que molesta: un **superadministrador no podía** crear una plantilla global;
- la que importa: un **administrador de organización sí podía**, y lo que creaba es
  `owner_kind="platform"` (nueve líneas más abajo, en el mismo endpoint), o sea **una fila de
  nivel plataforma que ven todas las demás organizaciones**.

Visto desde la frontera entre organizaciones eso no es una comodidad que falte: es un ámbito
inferior escribiendo por encima del suyo, saltándose las dos capas de `docs/MULTITENENCIA.md`.

**Por qué sobrevivió, que es la parte que se repite.** Había un test que **afirmaba el
defecto**: `test_non_admin_cannot_save_global_template`, con el docstring «Partner with
is_global=True → 403», usando un `_PARTNER` que es `role="superadmin"`. El vocabulario viejo
llamaba «partner» al superadministrador, así que el test se leía como «un no-admin no puede» y
en realidad decía «la plataforma no puede». Código y medida se daban la razón, como en el
issue #84.

Y el docstring del endpoint lo bendecía: «Solo admin/superadmin. `is_global` requiere admin».
Quien lo leyera no vería un fallo, vería una decisión — que es lo que hace que un defecto así
dure.

**Qué fija este fichero.** Las tres afirmaciones que el defecto invierte, más la del modelo: que
lo global es de la plataforma. La última es la que impide que el arreglo se pase de largo y le
quite al administrador de organización lo que sí le toca.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from server.app.api.deps import get_current_user, get_session
from server.app.core.auth.models import UserInfo
from server.app.main import app

_RUTA = "/api/v1/redaccion/llm-drafts/approve-as-template"

#: El rol de la plataforma. `core/auth/models.py` lo describe como «gestiona la plataforma
#: global», y `core/auth/modulos.py` lo dice sin rodeos: «El superadmin no necesita concesión.
#: Es el rol de la plataforma».
_SUPERADMIN = UserInfo(
    user_id="00000000-0000-0000-0000-0000000000f1",
    email="plataforma@test.com",
    role="superadmin",
)
#: Quien administra **su** organización. Su ámbito acaba ahí.
_ADMIN_DE_ORGANIZACION = UserInfo(
    user_id="00000000-0000-0000-0000-0000000000f2",
    email="admin@test.com",
    role="admin",
)

_BORRADOR = {
    "proposed_profile": "GENERIC_REPORT",
    "proposed_sections": [{"id": "s1", "title": "Intro", "order": 1, "block_ids": ["b1"]}],
    "proposed_blocks": [
        {"kind": "STATIC_TEXT", "id": "b1", "title": "Intro", "content": "Hola"}
    ],
    "proposed_inputs": {"required_slots": [], "optional_slots": []},
    "rationale": "Para el test",
    "model_used": "gpt-4o",
    "prompt_version": "v1",
}


def _sesion_simulada():
    sesion = MagicMock()
    sesion.add = MagicMock()
    sesion.flush = AsyncMock()
    sesion.commit = AsyncMock()
    sesion.get = AsyncMock(return_value=None)
    return sesion


def _como(quien: UserInfo):
    """Deja la sesión simulada accesible para inspeccionar lo que se guardó."""
    sesion = _sesion_simulada()

    async def _gen():
        yield sesion

    app.dependency_overrides[get_current_user] = lambda: quien
    app.dependency_overrides[get_session] = _gen
    return sesion


def _lo_guardado(sesion):
    """La plantilla que el endpoint añadió a la sesión."""
    from server.app.modules.redaccion.database.models import HubReportTemplate

    añadidos = [c.args[0] for c in sesion.add.call_args_list]
    plantillas = [o for o in añadidos if isinstance(o, HubReportTemplate)]
    assert plantillas, f"no se guardó ninguna plantilla; se añadió: {añadidos}"
    return plantillas[0]


@pytest.fixture
def cliente():
    """Sin gestor de contexto, como el resto de tests de este router.

    `with TestClient(app)` dispara el **ciclo de vida** de la aplicación, y al salir cierra el
    bucle de eventos junto con los motores de base de datos que abrió. En paralelo eso envenena
    al *worker*: los tests que corran después en él se caen en el `setup` con
    `Event loop is closed` y `asyncpg` intentando responder sobre un bucle cerrado.

    No se veía ejecutando este fichero solo —ahí el ciclo de vida abre y cierra sin que nadie
    más dependa de él— y salió con la suite entera. Es el mismo estado filtrado que CI busca
    con `-n0`.
    """
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _limpiar():
    yield
    app.dependency_overrides.clear()


class TestLoGlobalEsDeLaPlataforma:
    def test_el_superadministrador_puede_crear_una_plantilla_global(self, cliente) -> None:
        """El caso que devolvía 403. Rojo antes del arreglo."""
        sesion = _como(_SUPERADMIN)

        resp = cliente.post(
            _RUTA, json={"draft": _BORRADOR, "name": "De plataforma", "is_global": True}
        )

        assert resp.status_code == 200, (
            f"el rol de la plataforma no puede crear una plantilla de plataforma: "
            f"{resp.status_code} {resp.text[:200]}"
        )
        assert _lo_guardado(sesion).owner_kind == "platform"

    def test_un_admin_de_organizacion_no_puede_crear_una_plantilla_global(self, cliente) -> None:
        """La mitad grave: escribía una fila de nivel plataforma desde un ámbito inferior."""
        _como(_ADMIN_DE_ORGANIZACION)

        resp = cliente.post(
            _RUTA, json={"draft": _BORRADOR, "name": "Global indebida", "is_global": True}
        )

        assert resp.status_code == 403, (
            "un administrador de organización ha creado una plantilla de nivel plataforma, "
            f"que ven todas las organizaciones: {resp.status_code}"
        )

    def test_un_admin_de_organizacion_sigue_creando_las_suyas(self, cliente) -> None:
        """El camino bueno, que es lo que un arreglo pasado de largo rompería.

        Donde una comprobación puede bloquear hace falta el test de que **no** bloquea cuando no
        toca: si no, «lo global está protegido» y «al admin no le dejo nada» se parecen demasiado.
        """
        sesion = _como(_ADMIN_DE_ORGANIZACION)

        resp = cliente.post(
            _RUTA, json={"draft": _BORRADOR, "name": "De mi organización", "is_global": False}
        )

        assert resp.status_code == 200, f"{resp.status_code} {resp.text[:200]}"
        assert _lo_guardado(sesion).owner_kind == "admin"

    def test_lo_global_significa_nivel_plataforma(self) -> None:
        """La premisa, afirmada sobre el modelo y no sobre un fixture.

        `is_global` dejó de ser columna en MT.4 y pasó a ser un `hybrid_property` derivado de
        `owner_kind`. Si algún día eso cambia, el arreglo de arriba hay que revisarlo, y lo dice
        aquí en vez de repartirse por los tres tests de encima.
        """
        from server.app.modules.redaccion.database.models import HubReportTemplate

        assert "is_global" not in HubReportTemplate.__table__.columns, (
            "`is_global` ha vuelto a ser columna: entonces el nivel se guarda en dos sitios y "
            "pueden discrepar, que es lo que MT.4 vino a quitar"
        )
        assert hasattr(HubReportTemplate, "is_global"), (
            "ya no existe el `hybrid_property` `is_global`"
        )

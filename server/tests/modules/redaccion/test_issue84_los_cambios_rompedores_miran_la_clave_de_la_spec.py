"""La detección de cambios rompedores lee la clave que una spec guarda de verdad.

**El defecto.** `_required_slot_ids` hacía `spec_json.get("proposed_inputs", {})`, y
`proposed_inputs` es la clave del **borrador del modelo** (`contracts/drafts.py`). Una
`ReportTemplateSpec` guarda `input_contract` (`contracts/template.py`). Así que el `.get()` no
encontraba su clave, el valor por omisión `{}` hacía el resto, y `_compute_breaking_changes`
devolvía **siempre** la lista vacía: migrar un informe a una versión que añade un *slot*
obligatorio no avisaba de nada.

**Por qué no lo cazó el test que existía, que es la parte instructiva.**
`test_template_migration_service.py` tiene un
`test_migrate_returns_409_when_input_contract_breaking_change` que **pasaba**, porque su ayudante
`_spec()` construía la forma del borrador —`proposed_inputs`— en vez de la de una spec. El nombre
del test decía `input_contract` y el fixture escribía otra cosa: **el medidor estaba equivocado en
la misma dirección que el código**, así que los dos se daban la razón y ninguno tocaba la
realidad.

Es la razón por la que aquí no basta con arreglar el servicio y mirar que la suite siga verde. Lo
que hace falta es (1) un caso con la forma **real**, (2) el camino bueno, para que el arreglo no
se pase de largo inventando conflictos, y (3) una aserción sobre **los propios contratos**, que es
lo único que no puede derivar: si algún día `ReportTemplateSpec` renombra su campo, lo dice este
fichero y no catorce tests hablando de informes que no migran.

Las dos claves envuelven **el mismo tipo** (`InputContract`), o sea que confundirlas no da error
de tipos ni salta en revisión. De ahí que sobreviviera.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.app.modules.redaccion.database.models import (
    HubReportTemplateVersion,
    HubWorkspace,
)

_OWNER = uuid.UUID("00000000-0000-0000-0000-0000000000a1")
_WS_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-0000000000a1")
_TPL_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-0000000000a1")
_V1_ID = uuid.UUID("cccccccc-0000-0000-0000-0000000000a1")
_V2_ID = uuid.UUID("cccccccc-0000-0000-0000-0000000000a2")

_PLANTILLAS_DEMO = (
    Path(__file__).resolve().parents[3] / "app" / "data" / "plantillas_demo"
)


def _spec_de_verdad(required_slots: list[str]) -> dict:
    """Una `spec_json` con la forma que se guarda, no la del borrador.

    Las claves y la forma de los *slots* están copiadas de
    `app/data/plantillas_demo/informe_seguimiento_doctorado.json`, que es una spec real: un
    *slot* lleva `slot_id`, `kind` y `label`, y **no** lleva `required` —eso lo dice la lista en
    la que está—.
    """
    return {
        "blocks": [],
        "sections": [],
        "input_contract": {
            "required_slots": [
                {"slot_id": s, "kind": "markdown", "label": {"es": s}}
                for s in required_slots
            ],
            "optional_slots": [],
        },
        "ui_contract": {"manual_fields": []},
        "ai_block_policy": {},
        "review_policy": {},
        "export_policy": {},
    }


def _entorno(slots_v1: list[str], slots_v2: list[str]) -> tuple[MagicMock, MagicMock]:
    ws = MagicMock(spec=HubWorkspace)
    ws.id = _WS_ID
    ws.template_version_id = _V1_ID
    ws.owner_id = _OWNER
    ws.status = "draft"
    ws.inputs_json = {"datos": "informe.md"}
    ws.run_manifest_id = None
    ws.parent_workspace_id = None
    ws.archived_reason = None

    def _version(ver_id: uuid.UUID, num: int, slots: list[str]) -> MagicMock:
        v = MagicMock(spec=HubReportTemplateVersion)
        v.id = ver_id
        v.template_id = _TPL_ID
        v.version = num
        v.spec_json = _spec_de_verdad(slots)
        return v

    mapa = {
        ("HubWorkspace", _WS_ID): ws,
        ("HubReportTemplateVersion", _V1_ID): _version(_V1_ID, 1, slots_v1),
        ("HubReportTemplateVersion", _V2_ID): _version(_V2_ID, 2, slots_v2),
    }

    session = MagicMock()

    async def _get(cls, id_):
        return mapa.get((cls.__name__, id_))

    session.get = AsyncMock(side_effect=_get)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session, ws


class TestLaClaveEsLaDeLaSpec:
    def test_la_spec_y_el_borrador_no_declaran_la_misma_clave(self) -> None:
        """La premisa del defecto, afirmada sobre los contratos y no sobre un fixture.

        Si esto se pone rojo, el arreglo de `_required_slot_ids` hay que revisarlo: significa que
        alguno de los dos contratos cambió de nombre de campo.
        """
        from server.app.modules.redaccion.contracts.drafts import ReportTemplateDraft
        from server.app.modules.redaccion.contracts.template import ReportTemplateSpec

        assert "input_contract" in ReportTemplateSpec.model_fields, (
            "una `ReportTemplateSpec` ya no declara `input_contract`; el servicio de migración "
            "lee esa clave y hay que reapuntarlo"
        )
        assert "proposed_inputs" not in ReportTemplateSpec.model_fields, (
            "una spec ha empezado a declarar `proposed_inputs`, que era del borrador"
        )
        assert "proposed_inputs" in ReportTemplateDraft.model_fields, (
            "el borrador ya no declara `proposed_inputs`"
        )

    def test_las_plantillas_demo_usan_la_clave_de_la_spec(self) -> None:
        """Anclaje a datos reales: lo que hay en el catálogo versionado.

        Es la medición que destapó el defecto —cero `proposed_inputs`, dos `input_contract`— y
        aquí queda como aserción para que no se pueda volver a suponer lo contrario.
        """
        ficheros = sorted(_PLANTILLAS_DEMO.glob("*.json"))
        assert ficheros, f"no hay plantillas demo en {_PLANTILLAS_DEMO}"

        con_clave_de_spec, con_clave_de_borrador = [], []
        for fichero in ficheros:
            documento = json.loads(fichero.read_text(encoding="utf-8"))
            for entrada in documento["versiones"]:
                spec = entrada["spec_json"]
                (con_clave_de_spec if "input_contract" in spec else []).append(fichero.name)
                (con_clave_de_borrador if "proposed_inputs" in spec else []).append(fichero.name)

        assert con_clave_de_spec, (
            "ninguna versión de las plantillas demo guarda `input_contract`"
        )
        assert not con_clave_de_borrador, (
            f"estas plantillas guardan `proposed_inputs` en su spec: {con_clave_de_borrador}"
        )


class TestDeteccionDeCambiosRompedores:
    @pytest.mark.asyncio
    async def test_un_slot_obligatorio_nuevo_bloquea_la_migracion(self) -> None:
        """El caso que devolvía vacío siempre. Rojo antes del arreglo."""
        from server.app.modules.redaccion.services.template_migration_service import (
            CompatibilityConflictError,
            TemplateMigrationService,
        )

        session, _ = _entorno(slots_v1=["datos"], slots_v2=["datos", "anexo"])
        svc = TemplateMigrationService(session)

        with pytest.raises(CompatibilityConflictError) as excinfo:
            await svc.migrate_workspace(_WS_ID, _V2_ID, _OWNER)

        assert any(e["slot_id"] == "anexo" for e in excinfo.value.compatibility_errors), (
            "el slot obligatorio nuevo no aparece entre los conflictos: "
            f"{excinfo.value.compatibility_errors}"
        )

    @pytest.mark.asyncio
    async def test_no_inventa_conflictos_cuando_el_contrato_no_cambia(self) -> None:
        """El camino bueno, que es lo que un arreglo pasado de largo rompería.

        Donde una comprobación puede bloquear, hace falta un test de que **no** bloquea cuando no
        toca: si no, «detecta todo» y «detecta de más» se parecen demasiado.
        """
        from server.app.modules.redaccion.services.template_migration_service import (
            TemplateMigrationService,
        )

        session, _ = _entorno(slots_v1=["datos"], slots_v2=["datos"])
        svc = TemplateMigrationService(session)

        nuevo = await svc.migrate_workspace(_WS_ID, _V2_ID, _OWNER)
        assert nuevo.template_version_id == _V2_ID

    @pytest.mark.asyncio
    async def test_retirar_un_slot_obligatorio_no_es_rompedor(self) -> None:
        """Quitar un requisito no puede romper un workspace que ya lo cumplía."""
        from server.app.modules.redaccion.services.template_migration_service import (
            TemplateMigrationService,
        )

        session, _ = _entorno(slots_v1=["datos", "anexo"], slots_v2=["datos"])
        svc = TemplateMigrationService(session)

        nuevo = await svc.migrate_workspace(_WS_ID, _V2_ID, _OWNER)
        assert nuevo.template_version_id == _V2_ID

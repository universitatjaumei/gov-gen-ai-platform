"""VER.3 — lo que se aprueba tiene que poder volver a leerse.

Es la comprobación que faltaba en todo el camino: `approve-as-template` guardaba y devolvía
200, y **nadie leía después lo guardado**. Cuando se leyó por primera vez —al pedir el
contrato de UI de la plantilla recién aprobada— salió un 500, porque en `spec_json` estaba el
borrador y no la plantilla.

Este test recorre aprobar → leer contra base real, que es lo único que lo habría cazado.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.core.auth.models import UserInfo
from server.app.modules.redaccion.contracts.blocks import (
    AIAssistedTextBlock,
    DeterministicDataBlock,
    ReviewGateBlock,
)
from server.app.modules.redaccion.contracts.drafts import ReportTemplateDraft
from server.app.modules.redaccion.contracts.inputs import InputContract, InputSlot
from server.app.modules.redaccion.contracts.template import SectionContract
from server.app.routers.redaccion.hub_redaccion_router import get_template_ui_contract
from server.app.routers.redaccion.llm_drafts_router import (
    ApproveAsTemplateRequest,
    approve_as_template,
)

_USUARIO = UserInfo(user_id="1", email="fabra@uji.es", role="superadmin")


def _borrador() -> ReportTemplateDraft:
    return ReportTemplateDraft(
        proposed_profile="GENERIC_REPORT",
        proposed_sections=[
            SectionContract(id="s1", title="Datos", order=1, block_ids=["b_datos"]),
        ],
        proposed_blocks=[
            DeterministicDataBlock(
                id="b_datos", title="Importes", order=1, source_pipeline="excel"
            ),
            AIAssistedTextBlock(
                id="b_resumen", title="Resumen", order=2,
                ai_prompt_template_id="generic_report_v1", review_policy_id="required",
            ),
            ReviewGateBlock(id="b_gate", title="Revisión", order=3,
                            review_policy_id="required"),
        ],
        proposed_inputs=InputContract(
            required_slots=[
                InputSlot(slot_id="datos_excel", kind="excel",
                          label={"es": "Datos", "ca": "Dades", "en": "Data"}),
            ],
        ),
        rationale="",
        model_used="m",
        prompt_version="v",
    )


@pytest.mark.asyncio
async def test_should_serve_the_ui_contract_of_a_template_just_approved(db_url):
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            aprobada = await approve_as_template(
                body=ApproveAsTemplateRequest(
                    draft=_borrador(), name=f"Plantilla {uuid.uuid4().hex[:6]}",
                ),
                user=_USUARIO,
                session=session,
            )

            contrato = await get_template_ui_contract(
                version_id=aprobada.version_id, _user=_USUARIO, session=session,
            )

            assert [d.slot_id for d in contrato.dropzones] == ["datos_excel"]
            assert contrato.ai_review_panel_enabled is True
            assert [p.id for p in contrato.wizard_steps] == ["s1"]
    finally:
        await engine.dispose()

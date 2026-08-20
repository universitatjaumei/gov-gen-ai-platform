"""INF.1 — el contrato de UI dice qué fichero es obligatorio.

`UIFieldDescriptor` tenia `required` y `UIDropzoneDescriptor` no, asi que la pantalla sabia
que campo de texto era obligatorio y **no que fichero lo era**. Sin ese dato no podia validar
antes de lanzar, y el informe se ejecutaba sin datos: es el bloqueo A de las pruebas humanas
del 2026-08-20.

El segundo test es el que importa de verdad: las versiones de plantilla son **inmutables**, y
las que ya existen en la base se guardaron antes de que el campo existiera. Si el endpoint se
fiara del valor guardado, la plantilla del usuario seguiria diciendo `required=False` para un
slot que su `input_contract` declara obligatorio.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.core.auth.models import UserInfo
from server.app.modules.redaccion.database.models import (
    HubReportTemplate,
    HubReportTemplateVersion,
)
from server.app.routers.redaccion.hub_redaccion_router import get_template_ui_contract

_USUARIO = UserInfo(user_id="1", email="fabra@uji.es", role="superadmin")

def _spec_ya_guardada() -> dict:
    """Una spec como las que ya están en la base: con su slot obligatorio de markdown y
    **sin** `required` en el dropzone, porque el campo no existía cuando se guardaron.

    Se construye con los propios contratos y se le quita esa clave, en vez de escribirla a
    mano: un diccionario literal se desincroniza del modelo en cuanto alguien añade un campo
    obligatorio, y este test dejaría de probar lo que dice probar.
    """
    from server.app.modules.redaccion.contracts.inputs import InputSlot
    from server.app.modules.redaccion.contracts.template import (
        AIBlockPolicy,
        ExportPolicy,
        InputContract,
        ReportTemplateSpec,
        ReviewPolicy,
    )
    from server.app.modules.redaccion.contracts.ui import (
        ReportUIContract,
        UIDropzoneDescriptor,
    )

    etiqueta = {"es": "Informe resumen", "ca": "Informe resum", "en": "Summary"}
    spec = ReportTemplateSpec(
        sections=[],
        blocks=[],
        input_contract=InputContract(
            required_slots=[InputSlot(slot_id="datos", kind="markdown", label=etiqueta)],
            optional_slots=[],
        ),
        ui_contract=ReportUIContract(
            wizard_steps=[],
            dropzones=[
                UIDropzoneDescriptor(slot_id="datos", label=etiqueta, accept=[".md"])
            ],
            manual_fields=[],
            block_editor_enabled=True,
            ai_review_panel_enabled=True,
            preview_layout="markdown",
        ),
        ai_block_policy=AIBlockPolicy.ALLOWED,
        review_policy=ReviewPolicy.REQUIRED,
        export_policy=ExportPolicy.DOCX,
    )

    guardada = spec.model_dump(mode="json")
    del guardada["ui_contract"]["dropzones"][0]["required"]
    return guardada


def test_should_mark_a_required_slot_dropzone_as_required():
    """El constructor de specs marca el dropzone del slot obligatorio."""
    from server.app.modules.redaccion.contracts.template import InputContract, InputSlot
    from server.app.modules.redaccion.services.spec_builder import _contrato_de_ui

    class _Borrador:
        proposed_inputs = InputContract(
            required_slots=[
                InputSlot(slot_id="datos", kind="markdown", label={"es": "Informe resumen"})
            ],
            optional_slots=[
                InputSlot(slot_id="extra", kind="excel", label={"es": "Anexo"})
            ],
        )
        proposed_sections: list = []

    contrato = _contrato_de_ui(_Borrador(), hay_ia=False)
    por_slot = {dz.slot_id: dz.required for dz in contrato.dropzones}

    assert por_slot == {"datos": True, "extra": False}, (
        "sin esto la pantalla no distingue el fichero obligatorio del opcional"
    )


@pytest.mark.asyncio
async def test_should_derive_required_for_a_version_saved_before_the_field_existed(db_url):
    """Una versión ya guardada —sin el campo— sale con `required=True` derivado del contrato."""
    engine = create_async_engine(db_url)
    try:
        async with AsyncSession(engine) as session:
            plantilla = HubReportTemplate(
                name=f"Informe resumen {uuid.uuid4().hex[:6]}",
                report_profile="GENERIC_REPORT",
                owner_kind="platform",
                is_global=True,
            )
            session.add(plantilla)
            await session.flush()

            version = HubReportTemplateVersion(
                template_id=plantilla.id,
                version=1,
                spec_json=_spec_ya_guardada(),
                created_by=uuid.uuid4(),
            )
            session.add(version)
            # El id se captura **antes** del commit: `expire_on_commit` lo expira y leerlo
            # después dispara una recarga perezosa síncrona que revienta con `MissingGreenlet`.
            # Cuarta aparición del mismo patrón en este módulo, esta vez en un test.
            await session.flush()
            version_id = version.id
            await session.commit()

        # Sesión nueva a propósito: así se parece a producción, donde cada petición trae la suya.
        async with AsyncSession(engine) as session:
            contrato = await get_template_ui_contract(
                version_id=version_id, _user=_USUARIO, session=session
            )

            assert contrato.dropzones[0].required is True, (
                "la plantilla que el usuario ya tiene guardada seguiria dejando lanzar sin datos"
            )
    finally:
        await engine.dispose()

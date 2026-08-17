"""Endpoints LLM-drafts — 9R.4.3.

Deploy: edge
Expone generación, validación y aprobación de ReportTemplateDraft.
"""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user, get_session, require_role
from server.app.core.auth.models import UserInfo
from server.app.routers.redaccion._actor import (
    nombre_del_modelo,
    user_to_uuid as _user_to_uuid,
)
from server.app.modules.redaccion.contracts.drafts import (
    ReportTemplateDraft,
    ReportTemplateDraftValidationResult,
)
from server.app.modules.redaccion.database.models import (
    HubReportTemplate,
    HubReportTemplateVersion,
    HubWorkspace,
)
from server.app.modules.redaccion.database.repos import (
    ReportTemplateRepo,
    ReportTemplateVersionRepo,
    WorkspaceRepo,
)
from server.app.modules.agents_hub.services.model_factory import get_model_for_tier
from server.app.modules.redaccion.services.draft_validator import DraftValidator
from server.app.modules.redaccion.services.llm_spec_service import (
    LLMSpecService,
    PropuestaInvalidaError,
)
from server.app.modules.redaccion.services.spec_builder import spec_desde_borrador

router = APIRouter(prefix="/redaccion/llm-drafts", tags=["redaccion-llm-drafts"])

_require_admin = require_role("superadmin", "admin")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ProposeRequest(BaseModel):
    prompt_nl: str
    mode: Literal["admin_template", "user_workspace"] = "user_workspace"


class ApproveAsTemplateRequest(BaseModel):
    draft: ReportTemplateDraft
    name: str
    is_global: bool = False


class ApproveAsTemplateResponse(BaseModel):
    template_id: uuid.UUID
    version_id: uuid.UUID
    name: str
    is_global: bool


class ApproveAsWorkspaceRequest(BaseModel):
    draft: ReportTemplateDraft
    name: str


class ApproveAsWorkspaceResponse(BaseModel):
    workspace_id: uuid.UUID
    template_id: uuid.UUID
    template_version_id: uuid.UUID
    name: str
    status: str


# ---------------------------------------------------------------------------
# LLM service dependency — override in production via app.dependency_overrides
# ---------------------------------------------------------------------------

async def get_llm_spec_service(
    session: AsyncSession = Depends(get_session),
) -> LLMSpecService:
    """El servicio de propuesta de plantillas, con el modelo de la cascada (VER.2).

    Era un stub que devolvía 503 siempre, así que la puerta de entrada natural del módulo
    —describir el informe y que la plantilla se proponga sola— estaba cerrada aunque
    `LLMSpecService` llevara escrito y probado desde 9R.

    El 503 se conserva para el caso que de verdad lo merece —no hay modelo configurado— y
    **con el motivo dentro**: es la diferencia entre «esto no está montado» y «esto está
    roto», y sin ella hay que ir al log del servidor para distinguirlas.
    """
    from server.app.modules.agents_hub.services.config_provider import LocalConfigProvider

    try:
        modelo = await get_model_for_tier(1, LocalConfigProvider(session))
    except Exception as fallo:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail=f"No hay modelo de redacción disponible: {fallo}",
        ) from fallo

    return LLMSpecService(modelo, nombre_del_modelo(modelo))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/propose", response_model=ReportTemplateDraft, operation_id="proposeLlmDraft")
async def propose(
    body: ProposeRequest,
    user: UserInfo = Depends(get_current_user),
    service: LLMSpecService = Depends(get_llm_spec_service),
) -> ReportTemplateDraft:
    """Genera un ReportTemplateDraft a partir de texto natural. Sin persistir."""
    owner_kind: Literal["admin", "user"] = (
        "admin" if user.role in ("superadmin", "admin") else "user"
    )
    try:
        return await service.propose_template(body.prompt_nl, owner_kind)
    except PropuestaInvalidaError as fallo:
        # 422 y no 500: la propuesta la hizo el modelo, y quien pidió el informe necesita
        # saber que puede reformular, no ver un error del servidor.
        raise HTTPException(
            status_code=422,
            detail=f"La propuesta del modelo no encaja con el contrato de plantilla: {fallo}",
        ) from fallo


@router.post("/validate", response_model=ReportTemplateDraftValidationResult, operation_id="validateLlmDraft")
async def validate_draft(
    draft: ReportTemplateDraft,
    _: UserInfo = Depends(get_current_user),
) -> ReportTemplateDraftValidationResult:
    """Valida y normaliza un draft estructuralmente."""
    return DraftValidator().validate(draft)


@router.post("/approve-as-template", response_model=ApproveAsTemplateResponse, operation_id="approveAsTemplate")
async def approve_as_template(
    body: ApproveAsTemplateRequest,
    user: UserInfo = Depends(_require_admin),
    session: AsyncSession = Depends(get_session),
) -> ApproveAsTemplateResponse:
    """Persiste el draft como plantilla. Solo admin/superadmin. is_global requiere admin."""
    if body.is_global and user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can create global templates")

    result = DraftValidator().validate(body.draft)
    if not result.ok:
        raise HTTPException(
            status_code=422,
            detail=[
                {"loc": [e.field], "msg": e.message, "type": "value_error"}
                for e in result.errors
            ],
        )

    normalized = result.normalized_draft
    template_id = uuid.uuid4()
    version_id = uuid.uuid4()
    owner_uuid = _user_to_uuid(user.user_id)

    template = HubReportTemplate(
        id=template_id,
        name=body.name,
        report_profile=normalized.proposed_profile,
        owner_kind=user.role,
        owner_id=owner_uuid,
        is_global=body.is_global,
        current_version_id=version_id,
    )
    version = HubReportTemplateVersion(
        id=version_id,
        template_id=template_id,
        version=1,
        # La plantilla se guarda como plantilla, no como borrador: son formas distintas y
        # guardar el borrador dejaba la version inservible (VER.3).
        spec_json=spec_desde_borrador(normalized).model_dump(mode="json"),
        created_by=owner_uuid,
    )

    await ReportTemplateRepo(session).save(template)
    await ReportTemplateVersionRepo(session).save(version)
    await session.commit()

    return ApproveAsTemplateResponse(
        template_id=template_id,
        version_id=version_id,
        name=body.name,
        is_global=body.is_global,
    )


@router.post("/approve-as-workspace", response_model=ApproveAsWorkspaceResponse, operation_id="approveAsWorkspace")
async def approve_as_workspace(
    body: ApproveAsWorkspaceRequest,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApproveAsWorkspaceResponse:
    """Crea plantilla privada + workspace en estado draft. Cualquier usuario autenticado."""
    result = DraftValidator().validate(body.draft)
    if not result.ok:
        raise HTTPException(
            status_code=422,
            detail=[
                {"loc": [e.field], "msg": e.message, "type": "value_error"}
                for e in result.errors
            ],
        )

    normalized = result.normalized_draft
    template_id = uuid.uuid4()
    version_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    owner_uuid = _user_to_uuid(user.user_id)

    template = HubReportTemplate(
        id=template_id,
        name=body.name,
        report_profile=normalized.proposed_profile,
        owner_kind="user",
        owner_id=owner_uuid,
        is_global=False,
        current_version_id=version_id,
    )
    version = HubReportTemplateVersion(
        id=version_id,
        template_id=template_id,
        version=1,
        # La plantilla se guarda como plantilla, no como borrador: son formas distintas y
        # guardar el borrador dejaba la version inservible (VER.3).
        spec_json=spec_desde_borrador(normalized).model_dump(mode="json"),
        created_by=owner_uuid,
    )
    # 9R.10.2: arrancamos en `ingesting` para que la UI sepa que el workspace
    # está listo para subir inputs. Cuando el usuario invoca POST /run el
    # estado pasa a `drafting`.
    workspace = HubWorkspace(
        id=workspace_id,
        template_version_id=version_id,
        owner_id=owner_uuid,
        status="ingesting",
    )

    await ReportTemplateRepo(session).save(template)
    await ReportTemplateVersionRepo(session).save(version)
    await WorkspaceRepo(session).save(workspace)
    await session.commit()

    return ApproveAsWorkspaceResponse(
        workspace_id=workspace_id,
        template_id=template_id,
        template_version_id=version_id,
        name=body.name,
        status="ingesting",
    )

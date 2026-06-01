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
from server.app.modules.redaccion.services.draft_validator import DraftValidator
from server.app.modules.redaccion.services.llm_spec_service import LLMSpecService

router = APIRouter(prefix="/redaccion/llm-drafts", tags=["redaccion-llm-drafts"])

_require_admin_or_partner = require_role("admin", "partner")


def _user_to_uuid(user_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(user_id)
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_DNS, user_id)


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

async def get_llm_spec_service() -> LLMSpecService:
    """Stub: connect to model_factory in 9R.6.x. Override this dependency."""
    raise HTTPException(
        status_code=503,
        detail="LLM spec service not configured.",
    )


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
        "admin" if user.role in ("admin", "partner") else "user"
    )
    return await service.propose_template(body.prompt_nl, owner_kind)


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
    user: UserInfo = Depends(_require_admin_or_partner),
    session: AsyncSession = Depends(get_session),
) -> ApproveAsTemplateResponse:
    """Persiste el draft como plantilla. Solo admin/partner. is_global requiere admin."""
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
        spec_json=normalized.model_dump(mode="json"),
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
        spec_json=normalized.model_dump(mode="json"),
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

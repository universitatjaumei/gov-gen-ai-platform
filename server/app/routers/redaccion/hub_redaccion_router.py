"""Endpoints hub/redaccion — 9R.4.4 / 9R.7.2.

Deploy: edge
Template update notice, migración de workspaces, lectura de workspace/blocks/warnings.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import (
    get_current_user,
    get_session,
    require_role,
    require_scopes,
)
from server.app.core.auth.models import UserInfo
from server.app.modules.redaccion.contracts.template import ReportTemplateSpec
from server.app.modules.redaccion.contracts.ui import ReportUIContract
from server.app.modules.redaccion.database.models import (
    HubReportTemplate,
    HubReportTemplateVersion,
    HubWorkspace,
    HubWorkspaceBlock,
)
from server.app.modules.redaccion.database.repos import (
    ReportTemplateRepo,
    ReportTemplateVersionRepo,
    WorkspaceBlockRepo,
    WorkspaceRepo,
)
from server.app.modules.redaccion.services.template_migration_service import (
    CompatibilityConflictError,
    NewVersionNotice,
    TemplateMigrationService,
    WorkspaceNotFoundError,
    WorkspaceOwnershipError,
)

router = APIRouter(prefix="/hub/redaccion", tags=["hub-redaccion"])

# ---------------------------------------------------------------------------
# DTOs — workspace / blocks / warnings (9R.7.2)
# ---------------------------------------------------------------------------

class BlockStateOut(BaseModel):
    block_id: str
    kind: str
    status: str
    content: dict | None = None
    failure_kind: str | None = None
    last_error_message: str | None = None
    retry_attempts: int = 0
    updated_at: datetime


class WorkspaceOut(BaseModel):
    id: uuid.UUID
    template_version_id: uuid.UUID
    status: str
    blocks: list[BlockStateOut]
    created_at: datetime
    updated_at: datetime


class BlockPatchRequest(BaseModel):
    action: Literal["approve", "reject", "regenerate"]
    note: str | None = None


class ExtractionWarningOut(BaseModel):
    block_id: str | None = None
    message: str
    kind: str
    severity: str = "warning"


_KIND_TO_SEVERITY: dict[str, str] = {
    "type_mismatch": "error",
    "validation_failed": "error",
    "low_confidence": "warning",
    "missing_data": "warning",
}

_ACTION_TO_STATUS: dict[str, str] = {
    "approve": "approved",
    "reject": "rejected",
    "regenerate": "extracted",
}

# ---------------------------------------------------------------------------
# DTOs — templates / workspaces (9R.7.3)
# ---------------------------------------------------------------------------

class TemplateOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    report_profile: str
    owner_kind: str
    is_global: bool
    current_version_id: uuid.UUID | None = None
    created_at: datetime


class TemplateCreateIn(BaseModel):
    name: str
    description: str | None = None
    report_profile: str = "GENERIC_REPORT"
    owner_kind: str = "platform"
    spec_json: dict = Field(default_factory=dict)


class WorkspaceCreateIn(BaseModel):
    template_version_id: uuid.UUID


class WorkspaceCreatedOut(BaseModel):
    workspace_id: uuid.UUID


# ---------------------------------------------------------------------------
# DTOs — migrate (9R.4.4)
# ---------------------------------------------------------------------------

class MigrateRequest(BaseModel):
    target_version_id: uuid.UUID


class MigrateResponse(BaseModel):
    new_workspace_id: uuid.UUID


@router.get(
    "/templates",
    response_model=list[TemplateOut],
    operation_id="listTemplates",
)
async def list_templates(
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[TemplateOut]:
    """Lista plantillas globales + propias del usuario."""
    stmt = select(HubReportTemplate).where(
        or_(
            HubReportTemplate.is_global.is_(True),
            HubReportTemplate.owner_id == uuid.UUID(user.user_id),
        )
    )
    result = await session.execute(stmt)
    templates = list(result.scalars().all())
    return [
        TemplateOut(
            id=t.id,
            name=t.name,
            description=t.description,
            report_profile=t.report_profile,
            owner_kind=t.owner_kind,
            is_global=t.is_global,
            current_version_id=t.current_version_id,
            created_at=t.created_at,
        )
        for t in templates
    ]


@router.post(
    "/templates",
    response_model=TemplateOut,
    status_code=201,
    operation_id="createTemplate",
)
async def create_template(
    body: TemplateCreateIn,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TemplateOut:
    """Crea plantilla + versión 1. Solo admin/superadmin."""
    if user.role not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="Only admin can create templates")

    template = HubReportTemplate(
        name=body.name,
        description=body.description,
        report_profile=body.report_profile,
        owner_kind=body.owner_kind,
        owner_id=uuid.UUID(user.user_id),
        is_global=(body.owner_kind == "platform"),
    )
    template_repo = ReportTemplateRepo(session)
    template = await template_repo.save(template)

    version = HubReportTemplateVersion(
        template_id=template.id,
        version=1,
        spec_json=body.spec_json,
        created_by=uuid.UUID(user.user_id),
    )
    version_repo = ReportTemplateVersionRepo(session)
    version = await version_repo.save(version)

    await template_repo.update_status(template.id, version.id)
    await session.commit()
    await session.refresh(template)

    return TemplateOut(
        id=template.id,
        name=template.name,
        description=template.description,
        report_profile=template.report_profile,
        owner_kind=template.owner_kind,
        is_global=template.is_global,
        current_version_id=version.id,
        created_at=template.created_at,
    )


@router.post(
    "/workspaces",
    response_model=WorkspaceCreatedOut,
    status_code=201,
    operation_id="createWorkspace",
)
async def create_workspace_endpoint(
    body: WorkspaceCreateIn,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkspaceCreatedOut:
    """Crea workspace en estado draft para una versión de plantilla."""
    version = await ReportTemplateVersionRepo(session).get(body.template_version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Template version not found")

    workspace = HubWorkspace(
        template_version_id=body.template_version_id,
        owner_id=uuid.UUID(user.user_id),
        status="draft",
    )
    workspace = await WorkspaceRepo(session).save(workspace)
    await session.commit()
    await session.refresh(workspace)

    return WorkspaceCreatedOut(workspace_id=workspace.id)


@router.get(
    "/template-versions/{version_id}/ui-contract",
    response_model=ReportUIContract,
)
async def get_template_ui_contract(
    version_id: uuid.UUID,
    _user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ReportUIContract:
    """Devuelve el ReportUIContract de una versión de plantilla."""
    version = await ReportTemplateVersionRepo(session).get(version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Template version not found")
    spec = ReportTemplateSpec.model_validate(version.spec_json)
    return spec.ui_contract


@router.get(
    "/workspaces/{workspace_id}",
    response_model=WorkspaceOut,
    operation_id="getWorkspaceById",
)
async def get_workspace_by_id(
    workspace_id: uuid.UUID,
    _user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkspaceOut:
    """Devuelve el workspace con todos sus bloques."""
    workspace = await WorkspaceRepo(session).get(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    blocks = await WorkspaceBlockRepo(session).list(workspace_id)
    return WorkspaceOut(
        id=workspace.id,
        template_version_id=workspace.template_version_id,
        status=workspace.status,
        blocks=[
            BlockStateOut(
                block_id=b.block_id,
                kind=b.kind,
                status=b.status,
                content=b.content_json,
                failure_kind=b.failure_kind,
                last_error_message=b.last_error_message,
                retry_attempts=b.retry_attempts,
                updated_at=b.updated_at,
            )
            for b in blocks
        ],
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
    )


@router.patch(
    "/workspaces/{workspace_id}/blocks/{block_id}",
    response_model=BlockStateOut,
    operation_id="patchWorkspaceBlock",
)
async def patch_workspace_block(
    workspace_id: uuid.UUID,
    block_id: str,
    body: BlockPatchRequest,
    _user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BlockStateOut:
    """Aprueba, rechaza o solicita regeneración de un bloque."""
    stmt = select(HubWorkspaceBlock).where(
        and_(
            HubWorkspaceBlock.workspace_id == workspace_id,
            HubWorkspaceBlock.block_id == block_id,
        )
    )
    result = await session.execute(stmt)
    block = result.scalar_one_or_none()
    if block is None:
        raise HTTPException(status_code=404, detail="Block not found")

    block.status = _ACTION_TO_STATUS[body.action]
    await session.commit()
    await session.refresh(block)
    return BlockStateOut(
        block_id=block.block_id,
        kind=block.kind,
        status=block.status,
        content=block.content_json,
        failure_kind=block.failure_kind,
        last_error_message=block.last_error_message,
        retry_attempts=block.retry_attempts,
        updated_at=block.updated_at,
    )


@router.get(
    "/workspaces/{workspace_id}/warnings",
    response_model=list[ExtractionWarningOut],
    operation_id="getWorkspaceWarnings",
)
async def get_workspace_warnings(
    workspace_id: uuid.UUID,
    _user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ExtractionWarningOut]:
    """Lista de avisos de extracción del workspace."""
    workspace = await WorkspaceRepo(session).get(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return [
        ExtractionWarningOut(
            block_id=w.get("block_id"),
            message=w.get("message", ""),
            kind=w.get("kind", ""),
            severity=_KIND_TO_SEVERITY.get(w.get("kind", ""), "warning"),
        )
        for w in (workspace.warnings_json or [])
    ]


@router.get(
    "/workspaces/{workspace_id}/template-update-notice",
    response_model=NewVersionNotice,
    responses={204: {"description": "Workspace already at latest version"}},
)
async def template_update_notice(
    workspace_id: uuid.UUID,
    _user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NewVersionNotice | Response:
    """Devuelve aviso de nueva versión disponible, o 204 si ya está alineado."""
    service = TemplateMigrationService(session)
    try:
        notice = await service.detect_new_version(workspace_id)
    except WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if notice is None:
        return Response(status_code=204)
    return notice


@router.post(
    "/workspaces/{workspace_id}/migrate",
    response_model=MigrateResponse,
    status_code=201,
)
async def migrate_workspace(
    workspace_id: uuid.UUID,
    body: MigrateRequest,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MigrateResponse:
    """Crea workspace nuevo contra target_version_id, archiva el antiguo."""
    service = TemplateMigrationService(session)
    try:
        new_workspace = await service.migrate_workspace(
            workspace_id,
            body.target_version_id,
            uuid.UUID(user.user_id),
        )
    except WorkspaceNotFoundError:
        raise HTTPException(status_code=404, detail="Workspace not found")
    except WorkspaceOwnershipError:
        raise HTTPException(
            status_code=403,
            detail="Only the workspace owner can trigger migration",
        )
    except CompatibilityConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={"compatibility_errors": exc.compatibility_errors},
        )

    return MigrateResponse(new_workspace_id=new_workspace.id)


# ---------------------------------------------------------------------------
# DTOs — autoría de plantillas vía MCP (MCP.2)
# ---------------------------------------------------------------------------

class TemplateVersionOut(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    version: int
    spec: dict


class PublishVersionIn(BaseModel):
    spec_json: dict


class PublishVersionOut(BaseModel):
    template_id: uuid.UUID
    version: int
    version_id: uuid.UUID | None = None
    published: bool


# ---------------------------------------------------------------------------
# Endpoints — autoría de plantillas vía MCP (MCP.2)
# ---------------------------------------------------------------------------

@router.get("/template-schema", operation_id="getTemplateSchema")
async def get_template_schema(
    _user: UserInfo = Depends(require_scopes("redaccion:templates:read")),
) -> dict:
    """JSON Schema de ReportTemplateSpec.

    Alimenta el resource ``govgenai://redaccion/template-schema`` del servidor MCP:
    Claude redacta los drafts de plantilla directamente contra este contrato.
    """
    return ReportTemplateSpec.model_json_schema()


@router.get(
    "/template-versions/{version_id}",
    response_model=TemplateVersionOut,
    operation_id="getTemplateVersion",
)
async def get_template_version(
    version_id: uuid.UUID,
    _user: UserInfo = Depends(require_scopes("redaccion:templates:read")),
    session: AsyncSession = Depends(get_session),
) -> TemplateVersionOut:
    """Devuelve la spec completa de una versión de plantilla."""
    version = await ReportTemplateVersionRepo(session).get(version_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Template version not found")
    return TemplateVersionOut(
        id=version.id,
        template_id=version.template_id,
        version=version.version,
        spec=version.spec_json,
    )


@router.post(
    "/templates/{template_id}/versions",
    response_model=PublishVersionOut,
    status_code=201,
    operation_id="publishTemplateVersion",
)
async def publish_template_version(
    template_id: uuid.UUID,
    body: PublishVersionIn,
    dry_run: bool = False,
    user: UserInfo = Depends(require_role("superadmin", "admin")),
    _scope: UserInfo = Depends(require_scopes("redaccion:templates:write")),
    session: AsyncSession = Depends(get_session),
) -> PublishVersionOut:
    """Publica una nueva versión de plantilla (append-only).

    Nunca muta una versión existente: añade la siguiente. ``dry_run=True`` valida
    la spec contra ``ReportTemplateSpec`` y calcula la versión resultante SIN
    persistir.
    """
    template = await ReportTemplateRepo(session).get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        ReportTemplateSpec.model_validate(body.spec_json)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=json.loads(exc.json()))

    version_repo = ReportTemplateVersionRepo(session)
    existing = await version_repo.list(template_id)
    next_version = (existing[-1].version + 1) if existing else 1

    if dry_run:
        return PublishVersionOut(
            template_id=template_id, version=next_version, published=False
        )

    new_version_id = uuid.uuid4()
    new_version = HubReportTemplateVersion(
        id=new_version_id,
        template_id=template_id,
        version=next_version,
        spec_json=body.spec_json,
        created_by=uuid.UUID(user.user_id),
    )
    await version_repo.save(new_version)
    await ReportTemplateRepo(session).update_status(template_id, new_version_id)
    await session.commit()

    return PublishVersionOut(
        template_id=template_id,
        version=next_version,
        version_id=new_version_id,
        published=True,
    )

"""Router de auditoría de calidad de contenido web (9Q.8).

Deploy: edge.

Endpoints de cola de revisión de hallazgos, informe por sitio y descarga.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user
from server.app.core.auth.models import UserInfo
from server.app.modules.agents_hub.database.connection import get_async_session
from server.app.modules.agents_hub.ingestion.quality.contracts import (
    InvalidFindingTransitionError,
)
from server.app.modules.agents_hub.ingestion.quality.findings_repo import (
    ContentFindingRepo,
)
from server.app.modules.agents_hub.ingestion.quality.report_contracts import (
    ContentFindingView,
    WebQualityReport,
)

router = APIRouter(tags=["hub-content-quality"])

# ──────────────────────── Job de calidad inyectable ────────────────────────

_quality_job: Any = None


def set_quality_job(job: Any) -> None:
    global _quality_job
    _quality_job = job


def get_quality_job() -> Any:
    return _quality_job


# ──────────────────────── Dependencias ────────────────────────


def get_findings_repo(
    session: AsyncSession = Depends(get_async_session),
) -> ContentFindingRepo:
    return ContentFindingRepo(session)


def get_report_builder(
    session: AsyncSession = Depends(get_async_session),
) -> Any:
    from server.app.modules.agents_hub.ingestion.quality.report_builder import (
        WebQualityReportBuilder,
    )
    from server.app.modules.agents_hub.ingestion.quality.site_repo import (
        WebSiteRepo,
        ContentFindingRepo as _FR,
    )

    findings_repo = ContentFindingRepo(session)
    site_repo = WebSiteRepo(session)
    return WebQualityReportBuilder(findings_repo, site_repo)


def get_report_exporter() -> Any:
    from server.app.modules.agents_hub.ingestion.quality.report_exporter import (
        WebQualityReportExporter,
    )

    return WebQualityReportExporter()


async def _require_admin(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    if not (user.is_superadmin or user.is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
    return user


# ──────────────────────── Cola de revisión ────────────────────────


class _FindingOut(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    finding_type: str
    severity: str
    status: str
    confidence: float
    source_url: str | None
    detected_at: Any
    reviewed_at: Any = None

    model_config = {"from_attributes": True}


class _TransitionIn(BaseModel):
    new_status: str
    resolution_note: str | None = None


@router.get(
    "/hub/sites/{site_id}/findings",
    response_model=list[_FindingOut],
    operation_id="listSiteFindings",
)
async def list_site_findings(
    site_id: uuid.UUID,
    finding_status: str | None = Query(default=None, alias="status"),
    finding_type: str | None = Query(default=None, alias="type"),
    current_user: UserInfo = Depends(_require_admin),
    findings_repo: ContentFindingRepo = Depends(get_findings_repo),
):
    """Lista hallazgos de un sitio (cola de revisión).

    Deploy: edge.
    """
    return await findings_repo.list_by_site(
        site_id,
        status=finding_status,
        finding_type=finding_type,
    )


@router.patch(
    "/hub/sites/{site_id}/findings/{finding_id}",
    response_model=_FindingOut,
    operation_id="transitionFinding",
)
async def transition_finding(
    site_id: uuid.UUID,
    finding_id: uuid.UUID,
    body: _TransitionIn,
    current_user: UserInfo = Depends(_require_admin),
    findings_repo: ContentFindingRepo = Depends(get_findings_repo),
):
    """Transiciona el estado de un hallazgo (confirm/dismiss/resolve).

    Deploy: edge. Devuelve 422 si la transición no es válida.
    """
    try:
        updated = await findings_repo.transition(
            finding_id=finding_id,
            new_status=body.new_status,
            reviewed_by=uuid.UUID(current_user.user_id) if _is_uuid(current_user.user_id) else uuid.uuid4(),
            resolution_note=body.resolution_note,
        )
    except InvalidFindingTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return updated


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


# ──────────────────────── Informe ────────────────────────


@router.get(
    "/hub/sites/{site_id}/report",
    response_model=WebQualityReport,
    operation_id="getSiteQualityReport",
)
async def get_site_report(
    site_id: uuid.UUID,
    current_user: UserInfo = Depends(_require_admin),
    builder: Any = Depends(get_report_builder),
):
    """Genera y devuelve el informe de auditoría de calidad de un sitio.

    Deploy: edge.
    """
    return await builder.build(site_id)


@router.get(
    "/hub/sites/{site_id}/report/export",
    operation_id="exportSiteQualityReport",
)
async def export_site_report(
    site_id: uuid.UUID,
    report_format: str = Query(default="docx", alias="format"),
    current_user: UserInfo = Depends(_require_admin),
    builder: Any = Depends(get_report_builder),
    exporter: Any = Depends(get_report_exporter),
):
    """Descarga el informe como DOCX o PDF.

    Deploy: edge. Si LibreOffice no está disponible, PDF devuelve DOCX
    (Content-Type: application/vnd.openxmlformats…).
    """
    report = await builder.build(site_id)

    if report_format.lower() == "pdf":
        data = await exporter.to_pdf(report)
        media_type = "application/pdf"
        filename = f"informe_calidad_{site_id}.pdf"
    else:
        data = await exporter.to_docx(report)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"informe_calidad_{site_id}.docx"

    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ──────────────────────── Disparo de análisis ────────────────────────


@router.post(
    "/hub/sites/{site_id}/analyze",
    status_code=status.HTTP_202_ACCEPTED,
    operation_id="analyzeSite",
)
async def analyze_site(
    site_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: UserInfo = Depends(_require_admin),
    quality_job: Any = Depends(get_quality_job),
):
    """Dispara un análisis de calidad completo del sitio en background.

    Deploy: edge. Responde 202 Accepted inmediatamente.
    """
    if quality_job is not None:
        background_tasks.add_task(quality_job.run_for_site, site_id)
    return {"status": "queued", "site_id": str(site_id)}

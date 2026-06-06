"""Repositorio CRUD para HubContentFinding (9Q.1)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.operational_models import HubContentFinding
from server.app.modules.agents_hub.ingestion.quality.contracts import (
    ContentFinding,
    InvalidFindingTransitionError,
    _VALID_FINDING_TRANSITIONS,
)


class ContentFindingRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, finding: ContentFinding) -> HubContentFinding:
        stmt = select(HubContentFinding).where(
            HubContentFinding.site_id == finding.site_id,
            HubContentFinding.finding_type == finding.finding_type,
            HubContentFinding.page_id == finding.page_id,
            HubContentFinding.related_page_id == finding.related_page_id,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            orm = HubContentFinding(
                id=finding.id,
                site_id=finding.site_id,
                finding_type=finding.finding_type,
                severity=finding.severity,
                confidence=finding.confidence,
                page_id=finding.page_id,
                related_page_id=finding.related_page_id,
                source_url=finding.source_url,
                signal_json=finding.signal,
                status=finding.status,
                detected_at=finding.detected_at,
                reviewed_at=finding.reviewed_at,
                reviewed_by=finding.reviewed_by,
                resolution_note=finding.resolution_note,
            )
            self._session.add(orm)
            await self._session.flush()
            return orm

        existing.severity = finding.severity
        existing.confidence = finding.confidence
        existing.source_url = finding.source_url
        existing.signal_json = finding.signal
        existing.detected_at = finding.detected_at
        await self._session.flush()
        return existing

    async def list_by_site(
        self,
        site_id: uuid.UUID,
        status: Optional[str] = None,
        finding_type: Optional[str] = None,
    ) -> list[HubContentFinding]:
        stmt = select(HubContentFinding).where(HubContentFinding.site_id == site_id)
        if status is not None:
            stmt = stmt.where(HubContentFinding.status == status)
        if finding_type is not None:
            stmt = stmt.where(HubContentFinding.finding_type == finding_type)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get(self, finding_id: uuid.UUID) -> Optional[HubContentFinding]:
        return await self._session.get(HubContentFinding, finding_id)

    async def transition(
        self,
        finding_id: uuid.UUID,
        new_status: str,
        reviewed_by: uuid.UUID,
        resolution_note: Optional[str] = None,
    ) -> HubContentFinding:
        orm = await self._session.get(HubContentFinding, finding_id)
        allowed = _VALID_FINDING_TRANSITIONS.get(orm.status, set())
        if new_status not in allowed:
            raise InvalidFindingTransitionError(
                f"Cannot transition from '{orm.status}' to '{new_status}'"
            )
        orm.status = new_status
        orm.reviewed_by = reviewed_by
        orm.reviewed_at = datetime.now(timezone.utc)
        if resolution_note is not None:
            orm.resolution_note = resolution_note
        await self._session.flush()
        await self._session.refresh(orm)
        return orm

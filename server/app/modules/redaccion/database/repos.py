"""Repositorios para el módulo de redacción — 9R.1.4.

Solo infraestructura de acceso a datos. Sin lógica de negocio.
ReportTemplateVersionRepo no expone update: las versiones son append-only.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.redaccion.database.models import (
    HubReportTemplate,
    HubReportTemplateVersion,
    HubRunManifest,
    HubWorkspace,
    HubWorkspaceBlock,
)


class ReportTemplateRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, template_id: uuid.UUID) -> HubReportTemplate | None:
        return await self._session.get(HubReportTemplate, template_id)

    async def list(self, owner_id: uuid.UUID | None = None) -> list[HubReportTemplate]:
        stmt = select(HubReportTemplate)
        if owner_id is not None:
            stmt = stmt.where(HubReportTemplate.owner_id == owner_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def save(self, template: HubReportTemplate) -> HubReportTemplate:
        self._session.add(template)
        await self._session.flush()
        return template

    async def update_status(self, template_id: uuid.UUID, current_version_id: uuid.UUID) -> None:
        template = await self.get(template_id)
        if template:
            template.current_version_id = current_version_id
            await self._session.flush()


class ReportTemplateVersionRepo:
    """Append-only: no update method. Las versiones son inmutables."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, version_id: uuid.UUID) -> HubReportTemplateVersion | None:
        return await self._session.get(HubReportTemplateVersion, version_id)

    async def list(self, template_id: uuid.UUID) -> list[HubReportTemplateVersion]:
        stmt = (
            select(HubReportTemplateVersion)
            .where(HubReportTemplateVersion.template_id == template_id)
            .order_by(HubReportTemplateVersion.version)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def save(self, version: HubReportTemplateVersion) -> HubReportTemplateVersion:
        self._session.add(version)
        await self._session.flush()
        return version


class WorkspaceRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, workspace_id: uuid.UUID) -> HubWorkspace | None:
        return await self._session.get(HubWorkspace, workspace_id)

    async def list(self, owner_id: uuid.UUID | None = None) -> list[HubWorkspace]:
        stmt = select(HubWorkspace)
        if owner_id is not None:
            stmt = stmt.where(HubWorkspace.owner_id == owner_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def save(self, workspace: HubWorkspace) -> HubWorkspace:
        self._session.add(workspace)
        await self._session.flush()
        return workspace

    async def update_status(self, workspace_id: uuid.UUID, status: str) -> None:
        workspace = await self.get(workspace_id)
        if workspace:
            workspace.status = status
            await self._session.flush()


class WorkspaceBlockRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, block_id: uuid.UUID) -> HubWorkspaceBlock | None:
        return await self._session.get(HubWorkspaceBlock, block_id)

    async def list(self, workspace_id: uuid.UUID) -> list[HubWorkspaceBlock]:
        stmt = (
            select(HubWorkspaceBlock)
            .where(HubWorkspaceBlock.workspace_id == workspace_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def save(self, block: HubWorkspaceBlock) -> HubWorkspaceBlock:
        self._session.add(block)
        await self._session.flush()
        return block

    async def update_status(self, block_pk: uuid.UUID, status: str) -> None:
        block = await self.get(block_pk)
        if block:
            block.status = status
            await self._session.flush()


class RunManifestRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, manifest_id: uuid.UUID) -> HubRunManifest | None:
        return await self._session.get(HubRunManifest, manifest_id)

    async def list(self, workspace_id: uuid.UUID) -> list[HubRunManifest]:
        stmt = (
            select(HubRunManifest)
            .where(HubRunManifest.workspace_id == workspace_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def save(self, manifest: HubRunManifest) -> HubRunManifest:
        self._session.add(manifest)
        await self._session.flush()
        return manifest

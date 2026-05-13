"""LoadTemplateNode — carga y deserializa la spec de la versión de plantilla (9R.6.1)."""
from __future__ import annotations

from typing import Protocol
from uuid import UUID

from server.app.modules.redaccion.contracts.template import ReportTemplateSpec
from server.app.modules.redaccion.contracts.runtime import WorkspaceState


class TemplateVersionNotFoundError(Exception):
    def __init__(self, version_id: UUID) -> None:
        super().__init__(f"ReportTemplateVersion not found: {version_id}")
        self.version_id = version_id


class _VersionRepo(Protocol):
    async def get(self, version_id: UUID): ...


class LoadTemplateNode:
    """Carga la ReportTemplateSpec desde el repo y la inyecta en el estado."""

    def __init__(self, template_version_repo: _VersionRepo) -> None:
        self._repo = template_version_repo

    async def __call__(self, state: WorkspaceState) -> dict:
        orm = await self._repo.get(state.template_version_id)
        if orm is None:
            raise TemplateVersionNotFoundError(state.template_version_id)

        raw = orm.spec_json
        if isinstance(raw, str):
            import json
            raw = json.loads(raw)

        spec = ReportTemplateSpec.model_validate(raw)
        return {"spec": spec}

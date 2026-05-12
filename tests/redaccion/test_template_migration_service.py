"""9R.4.4 — TemplateMigrationService: política de anclaje y migración de workspaces.

RED → GREEN. Sin BD real; mocks para session.get / session.add / session.flush.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.app.modules.redaccion.database.models import (
    HubReportTemplate,
    HubReportTemplateVersion,
    HubWorkspace,
    HubWorkspaceBlock,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _spec(required_slots: list[str] | None = None) -> dict:
    slots = required_slots or []
    return {
        "proposed_profile": "GENERIC_REPORT",
        "proposed_sections": [],
        "proposed_blocks": [],
        "proposed_inputs": {
            "required_slots": [
                {"slot_id": s, "kind": "excel", "label": {"es": s}, "required": True}
                for s in slots
            ],
            "optional_slots": [],
        },
        "rationale": "test",
        "model_used": "gpt-4o",
        "prompt_version": "v1",
    }


def _workspace(
    ws_id: uuid.UUID,
    version_id: uuid.UUID,
    owner_id: uuid.UUID,
    *,
    status: str = "draft",
    inputs_json: dict | None = None,
    run_manifest_id: uuid.UUID | None = None,
) -> MagicMock:
    ws = MagicMock(spec=HubWorkspace)
    ws.id = ws_id
    ws.template_version_id = version_id
    ws.owner_id = owner_id
    ws.status = status
    ws.inputs_json = inputs_json if inputs_json is not None else {"file": "informe.xlsx"}
    ws.run_manifest_id = run_manifest_id
    ws.parent_workspace_id = None
    ws.archived_reason = None
    return ws


def _version(
    ver_id: uuid.UUID,
    template_id: uuid.UUID,
    version_num: int,
    spec: dict | None = None,
) -> MagicMock:
    v = MagicMock(spec=HubReportTemplateVersion)
    v.id = ver_id
    v.template_id = template_id
    v.version = version_num
    v.spec_json = spec if spec is not None else _spec()
    return v


def _template(tpl_id: uuid.UUID, current_version_id: uuid.UUID) -> MagicMock:
    t = MagicMock(spec=HubReportTemplate)
    t.id = tpl_id
    t.current_version_id = current_version_id
    return t


def _session(get_map: dict) -> MagicMock:
    s = MagicMock()

    async def _get(cls, id_):
        return get_map.get((cls.__name__, id_))

    s.get = AsyncMock(side_effect=_get)
    s.add = MagicMock()
    s.flush = AsyncMock()
    s.commit = AsyncMock()
    return s


# ── IDs ──────────────────────────────────────────────────────────────────────
_OWNER = uuid.UUID("00000000-0000-0000-0000-000000000001")
_OTHER = uuid.UUID("00000000-0000-0000-0000-000000000002")
_WS_ID = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
_TPL_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000001")
_V1_ID = uuid.UUID("cccccccc-0000-0000-0000-000000000001")
_V2_ID = uuid.UUID("cccccccc-0000-0000-0000-000000000002")


class TestDetectNewVersion:
    @pytest.mark.asyncio
    async def test_detect_new_version_returns_notice_when_template_has_newer_version(self):
        from server.app.modules.redaccion.services.template_migration_service import (
            NewVersionNotice,
            TemplateMigrationService,
        )
        ws = _workspace(_WS_ID, _V1_ID, _OWNER)
        v1 = _version(_V1_ID, _TPL_ID, 1)
        v2 = _version(_V2_ID, _TPL_ID, 2)
        tpl = _template(_TPL_ID, _V2_ID)  # template's current is v2

        session = _session({
            ("HubWorkspace", _WS_ID): ws,
            ("HubReportTemplateVersion", _V1_ID): v1,
            ("HubReportTemplate", _TPL_ID): tpl,
            ("HubReportTemplateVersion", _V2_ID): v2,
        })
        svc = TemplateMigrationService(session)
        notice = await svc.detect_new_version(_WS_ID)

        assert isinstance(notice, NewVersionNotice)
        assert notice.current_version_id == _V1_ID
        assert notice.latest_version_id == _V2_ID
        assert isinstance(notice.changes_summary, str)
        assert len(notice.changes_summary) > 0

    @pytest.mark.asyncio
    async def test_detect_new_version_returns_none_when_workspace_aligned_to_latest(self):
        from server.app.modules.redaccion.services.template_migration_service import (
            TemplateMigrationService,
        )
        ws = _workspace(_WS_ID, _V1_ID, _OWNER)
        v1 = _version(_V1_ID, _TPL_ID, 1)
        tpl = _template(_TPL_ID, _V1_ID)  # template's current is v1 — same as workspace

        session = _session({
            ("HubWorkspace", _WS_ID): ws,
            ("HubReportTemplateVersion", _V1_ID): v1,
            ("HubReportTemplate", _TPL_ID): tpl,
        })
        svc = TemplateMigrationService(session)
        result = await svc.detect_new_version(_WS_ID)

        assert result is None


class TestMigrateWorkspace:
    @pytest.mark.asyncio
    async def test_migrate_creates_new_workspace_against_target_version(self):
        from server.app.modules.redaccion.services.template_migration_service import (
            TemplateMigrationService,
        )
        ws = _workspace(_WS_ID, _V1_ID, _OWNER)
        v1 = _version(_V1_ID, _TPL_ID, 1)
        v2 = _version(_V2_ID, _TPL_ID, 2)

        session = _session({
            ("HubWorkspace", _WS_ID): ws,
            ("HubReportTemplateVersion", _V2_ID): v2,
            ("HubReportTemplateVersion", _V1_ID): v1,
        })
        svc = TemplateMigrationService(session)
        new_ws = await svc.migrate_workspace(_WS_ID, _V2_ID, _OWNER)

        assert new_ws.template_version_id == _V2_ID
        assert isinstance(new_ws, HubWorkspace)

    @pytest.mark.asyncio
    async def test_migrate_preserves_inputs_json_verbatim(self):
        from server.app.modules.redaccion.services.template_migration_service import (
            TemplateMigrationService,
        )
        original_inputs = {"file": "informe.xlsx", "year": 2026}
        ws = _workspace(_WS_ID, _V1_ID, _OWNER, inputs_json=original_inputs)
        v1 = _version(_V1_ID, _TPL_ID, 1)
        v2 = _version(_V2_ID, _TPL_ID, 2)

        session = _session({
            ("HubWorkspace", _WS_ID): ws,
            ("HubReportTemplateVersion", _V2_ID): v2,
            ("HubReportTemplateVersion", _V1_ID): v1,
        })
        svc = TemplateMigrationService(session)
        new_ws = await svc.migrate_workspace(_WS_ID, _V2_ID, _OWNER)

        assert new_ws.inputs_json == original_inputs

    @pytest.mark.asyncio
    async def test_migrate_does_not_copy_block_outputs_or_approvals(self):
        from server.app.modules.redaccion.services.template_migration_service import (
            TemplateMigrationService,
        )
        ws = _workspace(_WS_ID, _V1_ID, _OWNER)
        v1 = _version(_V1_ID, _TPL_ID, 1)
        v2 = _version(_V2_ID, _TPL_ID, 2)

        session = _session({
            ("HubWorkspace", _WS_ID): ws,
            ("HubReportTemplateVersion", _V2_ID): v2,
            ("HubReportTemplateVersion", _V1_ID): v1,
        })
        svc = TemplateMigrationService(session)
        await svc.migrate_workspace(_WS_ID, _V2_ID, _OWNER)

        added = [c.args[0] for c in session.add.call_args_list]
        assert not any(isinstance(obj, HubWorkspaceBlock) for obj in added), (
            "migrate_workspace must not copy HubWorkspaceBlock records"
        )

    @pytest.mark.asyncio
    async def test_migrate_archives_old_workspace_with_reason(self):
        from server.app.modules.redaccion.services.template_migration_service import (
            TemplateMigrationService,
        )
        ws = _workspace(_WS_ID, _V1_ID, _OWNER)
        v1 = _version(_V1_ID, _TPL_ID, 1)
        v2 = _version(_V2_ID, _TPL_ID, 2)

        session = _session({
            ("HubWorkspace", _WS_ID): ws,
            ("HubReportTemplateVersion", _V2_ID): v2,
            ("HubReportTemplateVersion", _V1_ID): v1,
        })
        svc = TemplateMigrationService(session)
        new_ws = await svc.migrate_workspace(_WS_ID, _V2_ID, _OWNER)

        assert ws.status == "archived"
        assert ws.archived_reason == f"migrated_to_{new_ws.id}"

    @pytest.mark.asyncio
    async def test_migrate_links_parent_workspace_id_in_new_workspace(self):
        from server.app.modules.redaccion.services.template_migration_service import (
            TemplateMigrationService,
        )
        ws = _workspace(_WS_ID, _V1_ID, _OWNER)
        v1 = _version(_V1_ID, _TPL_ID, 1)
        v2 = _version(_V2_ID, _TPL_ID, 2)

        session = _session({
            ("HubWorkspace", _WS_ID): ws,
            ("HubReportTemplateVersion", _V2_ID): v2,
            ("HubReportTemplateVersion", _V1_ID): v1,
        })
        svc = TemplateMigrationService(session)
        new_ws = await svc.migrate_workspace(_WS_ID, _V2_ID, _OWNER)

        assert new_ws.parent_workspace_id == _WS_ID

    @pytest.mark.asyncio
    async def test_migrate_returns_409_when_input_contract_breaking_change(self):
        from server.app.modules.redaccion.services.template_migration_service import (
            CompatibilityConflictError,
            TemplateMigrationService,
        )
        ws = _workspace(_WS_ID, _V1_ID, _OWNER)
        v1 = _version(_V1_ID, _TPL_ID, 1, spec=_spec(required_slots=["file"]))
        # v2 adds "additional_file" — breaking change
        v2 = _version(_V2_ID, _TPL_ID, 2, spec=_spec(required_slots=["file", "additional_file"]))

        session = _session({
            ("HubWorkspace", _WS_ID): ws,
            ("HubReportTemplateVersion", _V2_ID): v2,
            ("HubReportTemplateVersion", _V1_ID): v1,
        })
        svc = TemplateMigrationService(session)

        with pytest.raises(CompatibilityConflictError) as exc_info:
            await svc.migrate_workspace(_WS_ID, _V2_ID, _OWNER)

        errors = exc_info.value.compatibility_errors
        assert any(e["slot_id"] == "additional_file" for e in errors)

    @pytest.mark.asyncio
    async def test_migrate_requires_workspace_ownership(self):
        from server.app.modules.redaccion.services.template_migration_service import (
            TemplateMigrationService,
            WorkspaceOwnershipError,
        )
        ws = _workspace(_WS_ID, _V1_ID, _OWNER)
        v2 = _version(_V2_ID, _TPL_ID, 2)
        v1 = _version(_V1_ID, _TPL_ID, 1)

        session = _session({
            ("HubWorkspace", _WS_ID): ws,
            ("HubReportTemplateVersion", _V2_ID): v2,
            ("HubReportTemplateVersion", _V1_ID): v1,
        })
        svc = TemplateMigrationService(session)

        with pytest.raises(WorkspaceOwnershipError):
            await svc.migrate_workspace(_WS_ID, _V2_ID, _OTHER)

    @pytest.mark.asyncio
    async def test_migration_preserves_old_workspace_run_manifest(self):
        from server.app.modules.redaccion.services.template_migration_service import (
            TemplateMigrationService,
        )
        manifest_id = uuid.uuid4()
        ws = _workspace(_WS_ID, _V1_ID, _OWNER, run_manifest_id=manifest_id)
        v1 = _version(_V1_ID, _TPL_ID, 1)
        v2 = _version(_V2_ID, _TPL_ID, 2)

        session = _session({
            ("HubWorkspace", _WS_ID): ws,
            ("HubReportTemplateVersion", _V2_ID): v2,
            ("HubReportTemplateVersion", _V1_ID): v1,
        })
        svc = TemplateMigrationService(session)
        await svc.migrate_workspace(_WS_ID, _V2_ID, _OWNER)

        # Migration must not alter the old workspace's run_manifest_id
        assert ws.run_manifest_id == manifest_id

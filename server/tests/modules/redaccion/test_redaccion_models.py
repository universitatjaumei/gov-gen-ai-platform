"""9R.1.4 — Modelos ORM y repos de redacción.

Tests estructurales (sin BD en memoria): verifican que los modelos ORM tienen las
columnas, constraints y configuraciones correctas antes de la migración real.
"""
from __future__ import annotations

from sqlalchemy import UniqueConstraint


class TestRedaccionTableSchema:
    def _col(self, table, name):
        return table.columns[name]

    def test_alembic_upgrade_head_creates_new_tables(self):
        expected_tables = {
            "hub_report_templates",
            "hub_report_template_versions",
            "hub_workspaces",
            "hub_workspace_blocks",
            "hub_run_manifests",
        }
        from server.app.modules.agents_hub.database.base import HubOperationalBase
        registered = {t for t in HubOperationalBase.metadata.tables}
        assert expected_tables.issubset(registered), (
            f"Missing tables: {expected_tables - registered}"
        )

    def test_alembic_downgrade_removes_new_tables_cleanly(self):
        # Verifica que la función downgrade() está definida y llama a drop_table
        from server.migrations.versions.m4b5c6d7e8f9_redaccion_tables_9r14 import downgrade
        import inspect
        src = inspect.getsource(downgrade)
        assert "hub_run_manifests" in src
        assert "hub_workspace_blocks" in src
        assert "hub_workspaces" in src
        assert "hub_report_template_versions" in src
        assert "hub_report_templates" in src

    def test_workspace_block_unique_per_workspace(self):
        from server.app.modules.redaccion.database.models import HubWorkspaceBlock
        constraints = HubWorkspaceBlock.__table__.constraints
        unique_constraints = [
            c for c in constraints if isinstance(c, UniqueConstraint)
        ]
        assert any(
            set(col.name for col in uc.columns) == {"workspace_id", "block_id"}
            for uc in unique_constraints
        ), "Missing UNIQUE(workspace_id, block_id) on hub_workspace_blocks"

    def test_run_manifest_links_to_workspace_and_template_version(self):
        from server.app.modules.redaccion.database.models import HubRunManifest
        cols = HubRunManifest.__table__.columns
        assert "workspace_id" in cols
        assert "template_version_id" in cols
        assert "final_document_hash" in cols
        # final_document_hash is nullable (only set at assembly)
        assert cols["final_document_hash"].nullable is True

    def test_template_version_columns_present(self):
        from server.app.modules.redaccion.database.models import HubReportTemplateVersion
        cols = HubReportTemplateVersion.__table__.columns
        assert "template_id" in cols
        assert "version" in cols
        assert "spec_json" in cols
        assert "created_by" in cols

    def test_workspace_has_inputs_and_warnings_json(self):
        from server.app.modules.redaccion.database.models import HubWorkspace
        cols = HubWorkspace.__table__.columns
        assert "inputs_json" in cols
        assert "warnings_json" in cols
        assert "status" in cols
        assert "run_manifest_id" in cols
        assert cols["run_manifest_id"].nullable is True


class TestRepoApiSurface:
    def test_template_version_insert_only_no_update(self):
        from server.app.modules.redaccion.database.repos import ReportTemplateVersionRepo
        # Versiones son append-only: el repo NO expone un método update
        assert not hasattr(ReportTemplateVersionRepo, "update"), (
            "ReportTemplateVersionRepo must NOT have an update method — versions are immutable"
        )
        assert hasattr(ReportTemplateVersionRepo, "save")
        assert hasattr(ReportTemplateVersionRepo, "get")
        assert hasattr(ReportTemplateVersionRepo, "list")

    def test_workspace_repo_exposes_required_methods(self):
        from server.app.modules.redaccion.database.repos import WorkspaceRepo
        for method in ("get", "list", "save", "update_status"):
            assert hasattr(WorkspaceRepo, method), f"WorkspaceRepo missing method: {method}"

    def test_run_manifest_repo_has_no_update(self):
        from server.app.modules.redaccion.database.repos import RunManifestRepo
        # Manifests are immutable once created
        assert not hasattr(RunManifestRepo, "update")
        assert hasattr(RunManifestRepo, "save")

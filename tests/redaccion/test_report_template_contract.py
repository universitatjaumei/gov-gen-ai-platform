"""9R.1.1 — ReportTemplateContract + ReportTemplateVersion (Pydantic + OpenAPI).

Tests RED → GREEN. Sin routers; solo contratos Pydantic serializables por OpenAPI.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from server.app.modules.redaccion.contracts.template import (
    AIBlockPolicy,
    ExportPolicy,
    InputContract,
    ReportTemplateContract,
    ReportTemplateSpec,
    ReportTemplateVersion,
    ReportUIContract,
    ReviewPolicy,
    SectionContract,
    StaticTextBlock,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minimal_spec() -> ReportTemplateSpec:
    return ReportTemplateSpec(
        sections=[SectionContract(id="s1", title="Introducció", order=1)],
        blocks=[StaticTextBlock(id="b1", title="Intro")],
        input_contract=InputContract(),
        ui_contract=ReportUIContract(
            wizard_steps=[], dropzones=[], manual_fields=[],
            block_editor_enabled=False, ai_review_panel_enabled=False,
            preview_layout="markdown",
        ),
        ai_block_policy=AIBlockPolicy.REQUIRED_REVIEW,
        review_policy=ReviewPolicy.REQUIRED,
        export_policy=ExportPolicy.DOCX,
    )


def _minimal_contract(**overrides) -> ReportTemplateContract:
    defaults = dict(
        id=uuid4(),
        name="Informe genèric",
        report_profile="GENERIC_REPORT",
        owner_kind="platform",
        is_global=True,
        current_version_id=uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return ReportTemplateContract(**defaults)


def _minimal_version(**overrides) -> ReportTemplateVersion:
    defaults = dict(
        id=uuid4(),
        template_id=uuid4(),
        version=1,
        spec=_minimal_spec(),
        created_at=datetime.now(timezone.utc),
        created_by=uuid4(),
    )
    defaults.update(overrides)
    return ReportTemplateVersion(**defaults)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestReportTemplateContractOpenAPI:
    def test_report_template_contract_is_serializable_to_openapi(self):
        schema = ReportTemplateContract.model_json_schema()
        assert schema.get("title") == "ReportTemplateContract"
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "owner_kind" in schema["properties"]
        assert "is_global" in schema["properties"]

    def test_report_template_exports_stable_schema_names(self):
        # ReportTemplateVersion embeds ReportTemplateSpec and SectionContract — check those $defs
        version_schema = ReportTemplateVersion.model_json_schema()
        defs = version_schema.get("$defs", {})
        # Names must not contain auto-generated hash suffixes (e.g. "ReportTemplateSpec_abc123")
        for key in defs:
            assert "__" not in key, f"Unstable schema name: {key}"
            parts = key.split("_")
            assert not parts[-1].isdigit(), f"Unstable schema name with numeric suffix: {key}"
        # Core schemas present
        assert "ReportTemplateSpec" in defs
        assert "SectionContract" in defs


class TestReportTemplateContractValidation:
    def test_report_template_spec_rejects_unknown_owner_kind(self):
        with pytest.raises(ValidationError) as exc_info:
            _minimal_contract(owner_kind="admin")
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("owner_kind",) for e in errors)

    def test_only_admin_can_create_global_template_contract(self):
        # is_global=True with owner_kind != "platform" must be rejected
        with pytest.raises(ValidationError) as exc_info:
            _minimal_contract(owner_kind="organization", is_global=True)
        assert exc_info.value.error_count() >= 1

    def test_non_global_template_can_belong_to_organization(self):
        contract = _minimal_contract(owner_kind="organization", is_global=False, owner_id=uuid4())
        assert contract.owner_kind == "organization"
        assert not contract.is_global

    def test_optional_description_defaults_to_none(self):
        contract = _minimal_contract()
        assert contract.description is None

    def test_optional_owner_id_allowed_for_platform(self):
        contract = _minimal_contract(owner_kind="platform", owner_id=None)
        assert contract.owner_id is None


class TestReportTemplateVersion:
    def test_report_template_version_requires_template_id(self):
        with pytest.raises((ValidationError, TypeError)):
            ReportTemplateVersion(
                id=uuid4(),
                # template_id intentionally omitted
                version=1,
                spec=_minimal_spec(),
                created_at=datetime.now(timezone.utc),
                created_by=uuid4(),
            )

    def test_report_template_version_is_immutable_once_persisted(self):
        version = _minimal_version()
        with pytest.raises((ValidationError, TypeError)):
            version.version = 99  # frozen model must reject mutations

    def test_report_template_version_schema_is_serializable(self):
        schema = ReportTemplateVersion.model_json_schema()
        assert schema.get("title") == "ReportTemplateVersion"
        assert "template_id" in schema["properties"]
        assert "version" in schema["properties"]

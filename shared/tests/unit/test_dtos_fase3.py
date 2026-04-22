# shared/tests/unit/test_dtos_fase3.py
"""Tests for Phase 3 DTO updates - FlowSpec versioning fields."""
import pytest
from pydantic import ValidationError
from automatia_shared.dtos import FlowSpec, TaskSpec


def test_flowspec_version_semver_valid():
    """FlowSpec accepts valid semver version strings."""
    flow = FlowSpec(name="Test", version="1.2.3", status="DRAFT", steps=[])
    assert flow.version == "1.2.3"


def test_flowspec_version_semver_invalid():
    """FlowSpec rejects invalid version strings."""
    with pytest.raises(ValidationError):
        FlowSpec(name="Test", version="not-semver", status="DRAFT", steps=[])


def test_flowspec_status_enum_values():
    """FlowSpec accepts valid status values."""
    for status in ["DRAFT", "PUBLISHED", "DEPRECATED"]:
        flow = FlowSpec(name="Test", status=status, steps=[])
        assert flow.status == status


def test_flowspec_row_version_default():
    """FlowSpec has row_version defaulting to 0."""
    flow = FlowSpec(name="Test", steps=[])
    assert flow.row_version == 0


def test_flowspec_owner_scope_optional():
    """FlowSpec allows optional owner_scope."""
    flow = FlowSpec(name="Test", owner_scope="partner_123", steps=[])
    assert flow.owner_scope == "partner_123"

    flow_no_scope = FlowSpec(name="Test", steps=[])
    assert flow_no_scope.owner_scope is None


def test_flowspec_version_default():
    """FlowSpec defaults version to 0.1.0."""
    flow = FlowSpec(name="Test", steps=[])
    assert flow.version == "0.1.0"


def test_flowspec_status_default():
    """FlowSpec defaults status to DRAFT."""
    flow = FlowSpec(name="Test", steps=[])
    assert flow.status == "DRAFT"


def test_flowspec_version_various_valid_formats():
    """FlowSpec accepts various valid semver formats."""
    valid_versions = ["0.0.1", "1.0.0", "10.20.30", "999.999.999"]
    for v in valid_versions:
        flow = FlowSpec(name="Test", version=v, steps=[])
        assert flow.version == v

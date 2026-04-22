# client_app/tests/unit/test_models_fase3.py
"""Tests for Phase 3 model updates - versioning and metrics fields."""
import pytest
from app.database.models import FlowRegistry, TaskLog, ValidationHistory


def test_flowregistry_new_fields():
    """FlowRegistry includes version, status, row_version fields."""
    fr = FlowRegistry(name="Test", version="1.0.0", status="DRAFT", row_version=0)
    assert fr.version == "1.0.0"
    assert fr.status == "DRAFT"
    assert fr.row_version == 0


def test_flowregistry_defaults():
    """FlowRegistry has correct defaults for new fields."""
    fr = FlowRegistry(name="Test")
    assert fr.version == "0.1.0"
    assert fr.status == "DRAFT"
    assert fr.row_version == 0
    assert fr.owner_scope is None


def test_flowregistry_owner_scope():
    """FlowRegistry accepts owner_scope field."""
    fr = FlowRegistry(name="Test", owner_scope="partner_456")
    assert fr.owner_scope == "partner_456"


def test_tasklog_duration_field():
    """TaskLog includes duration_ms metric field."""
    tl = TaskLog(execution_id="exec_1", step_index=0, step_name="S1", duration_ms=1500)
    assert tl.duration_ms == 1500


def test_tasklog_policy_id_field():
    """TaskLog includes policy_id reference field."""
    tl = TaskLog(execution_id="exec_1", step_index=0, step_name="S1", policy_id=42)
    assert tl.policy_id == 42


def test_tasklog_peak_memory_field():
    """TaskLog includes peak_memory_mb metric field."""
    tl = TaskLog(execution_id="exec_1", step_index=0, step_name="S1", peak_memory_mb=256.5)
    assert tl.peak_memory_mb == 256.5


def test_tasklog_new_fields_defaults():
    """TaskLog new fields default to None."""
    tl = TaskLog(execution_id="exec_1", step_index=0, step_name="S1")
    assert tl.duration_ms is None
    assert tl.policy_id is None
    assert tl.peak_memory_mb is None


def test_validationhistory_retries_field():
    """ValidationHistory includes retries counter field."""
    vh = ValidationHistory(task_id="t1", user_action="retry", retries=2, who="user_123")
    assert vh.retries == 2
    assert vh.who == "user_123"


def test_validationhistory_fields_affected():
    """ValidationHistory includes fields_affected JSON field."""
    vh = ValidationHistory(
        task_id="t1",
        user_action="retry",
        fields_affected='["field_a", "field_b"]'
    )
    assert vh.fields_affected == '["field_a", "field_b"]'


def test_validationhistory_defaults():
    """ValidationHistory new fields have correct defaults."""
    vh = ValidationHistory(task_id="t1", user_action="approve")
    assert vh.who is None
    assert vh.retries == 0
    assert vh.fields_affected is None


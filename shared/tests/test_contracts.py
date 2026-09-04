"""
Contract tests for automatia-shared package.
These tests ensure that shared DTOs, enums, and utilities work correctly
and maintain their contracts for both server and client_app.
"""

import pytest
from datetime import datetime


class TestEnumsContract:
    """Tests for enum contracts."""

    def test_task_status_enum_values(self):
        """Verify TaskStatus enum has all required states."""
        from automatia_shared.enums import TaskStatus

        required_states = [
            "pending", "in_progress", "pending_validation",
            "user_approved", "user_rejected", "escalation_ready",
            "escalated", "completed", "failed"
        ]

        actual_values = [status.value for status in TaskStatus]

        for state in required_states:
            assert state in actual_values, f"TaskStatus missing required state: {state}"

    def test_license_status_enum_values(self):
        """Verify LicenseStatus enum has all required states."""
        from automatia_shared.enums import LicenseStatus

        required_states = ["active", "suspended", "expired", "pending"]
        actual_values = [status.value for status in LicenseStatus]

        for state in required_states:
            assert state in actual_values, f"LicenseStatus missing required state: {state}"

    def test_script_status_enum_values(self):
        """Verify ScriptStatus enum has all required states."""
        from automatia_shared.enums import ScriptStatus

        required_states = ["draft", "published", "deprecated", "rejected"]
        actual_values = [status.value for status in ScriptStatus]

        for state in required_states:
            assert state in actual_values, f"ScriptStatus missing required state: {state}"

    def test_enums_are_string_enums(self):
        """Verify enums inherit from str for JSON serialization."""
        from automatia_shared.enums import TaskStatus, LicenseStatus, ScriptStatus

        # String enums should be directly serializable
        assert TaskStatus.PENDING == "pending"
        assert LicenseStatus.ACTIVE == "active"
        assert ScriptStatus.DRAFT == "draft"


class TestDTOsContract:
    """Tests for DTO contracts."""

    def test_task_spec_serialization(self):
        """Verify TaskSpec can be created and serialized."""
        from automatia_shared.dtos import TaskSpec
        from automatia_shared.enums import StepType

        task = TaskSpec(
            name="Extract Invoice Data",
            type=StepType.EXTRACTION,
            script_id="script_123",
            config={"timeout": 300}
        )

        # Should be serializable to dict
        data = task.model_dump()
        assert data["name"] == "Extract Invoice Data"
        assert data["type"] == "extraction"
        assert data["script_id"] == "script_123"
        assert data["config"]["timeout"] == 300

    def test_flow_spec_serialization(self):
        """Verify FlowSpec can be created with steps."""
        from automatia_shared.dtos import FlowSpec, TaskSpec
        from automatia_shared.enums import TriggerType, StepType

        flow = FlowSpec(
            name="Invoice Processing Flow",
            description="Process incoming invoices",
            trigger_type=TriggerType.EMAIL,
            trigger_config={"sender_whitelist": ["invoices@example.com"]},
            steps=[
                TaskSpec(name="Extract", type=StepType.EXTRACTION, script_id="s1"),
                TaskSpec(name="Transform", type=StepType.ETL, script_id="s2"),
            ]
        )

        data = flow.model_dump()
        assert data["name"] == "Invoice Processing Flow"
        assert data["trigger_type"] == "email"
        assert len(data["steps"]) == 2
        assert data["steps"][0]["name"] == "Extract"

    # `test_field_definition_contract` vivía aquí. `FieldDefinition` era el especificador de
    # campos de la extracción asistida del NiceGUI —`expected_format`, `is_table`,
    # `example_value`— y **ya no existe en `automatia_shared.dtos`**, ni con otro nombre: el
    # `OutputField` de `contracts/ui_contract.py` tiene otra forma (`label`, `type`, `nullable`,
    # `constraints`) porque describe la salida de un átomo, no un campo a extraer de un PDF.
    #
    # Retirado en NIC.4 junto con el test de importación que lo pedía. Los dos llevaban en rojo
    # **sin que ningún check lo dijera**, porque CI corre con `working-directory: server` y nunca
    # ejecutó `shared/tests`. El paso que colectaba el árbol de la raíz —retirado en NIC.4 con ese
    # árbol— pasa a ejecutar este y el de `mcp_server`, que es lo que habría cazado esto: el
    # import está **dentro** de la función, así que un `--collect-only` lo habría dejado pasar.

    def test_license_info_computed_properties(self):
        """Verify LicenseInfo computed properties work."""
        from automatia_shared.dtos import LicenseInfo

        license_info = LicenseInfo(
            license_id="lic_001",
            client_id="client_001",
            partner_id="partner_001",
            quota_tokens=100000,
            consumed_tokens=75000,
            valid_until=datetime(2026, 12, 31),
            status="active"
        )

        assert license_info.remaining_tokens == 25000
        assert license_info.usage_percentage == 75.0


class TestValidatorsContract:
    """Tests for validator contracts."""

    def test_license_key_format_validation(self):
        """Verify license key format validation."""
        from automatia_shared.validators import validate_license_key_format

        # Valid format
        is_valid, error = validate_license_key_format("ABCD1-23456-EFGH7-89012")
        assert is_valid is True
        assert error is None

        # Invalid format
        is_valid, error = validate_license_key_format("invalid-key")
        assert is_valid is False
        assert error is not None

    def test_hash_license_key(self):
        """Verify license key hashing is deterministic."""
        from automatia_shared.validators import hash_license_key

        key = "TEST1-23456-ABCDE-67890"
        hash1 = hash_license_key(key)
        hash2 = hash_license_key(key)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64 hex chars

    def test_dni_format_validation(self):
        """Verify Spanish DNI validation."""
        from automatia_shared.validators import validate_dni_format

        # Valid DNI
        is_valid, error = validate_dni_format("12345678Z")
        assert is_valid is True

        # Valid NIE
        is_valid, error = validate_dni_format("X1234567L")
        assert is_valid is True

        # Invalid
        is_valid, error = validate_dni_format("invalid")
        assert is_valid is False

    def test_sanitize_filename(self):
        """Verify filename sanitization."""
        from automatia_shared.validators import sanitize_filename

        # Should remove path separators
        assert "/" not in sanitize_filename("path/to/file.pdf")
        assert "\\" not in sanitize_filename("path\\to\\file.pdf")

        # Should handle special characters
        result = sanitize_filename('file<>:"|?*.pdf')
        assert "<" not in result
        assert ">" not in result


class TestUtilsContract:
    """Tests for utility function contracts."""

    def test_generate_code_hash(self):
        """Verify code hashing is deterministic."""
        from automatia_shared.utils import generate_code_hash

        code = "def extract(): pass"
        hash1 = generate_code_hash(code)
        hash2 = generate_code_hash(code)

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_safe_json_loads(self):
        """Verify safe JSON parsing."""
        from automatia_shared.utils import safe_json_loads

        # Valid JSON
        result = safe_json_loads('{"key": "value"}')
        assert result == {"key": "value"}

        # Invalid JSON returns default
        result = safe_json_loads('invalid', default={})
        assert result == {}

    def test_extract_json_from_text(self):
        """Verify JSON extraction from markdown."""
        from automatia_shared.utils import extract_json_from_text

        text = '''
        Here is some text
        ```json
        {"field": "value"}
        ```
        More text
        '''
        result = extract_json_from_text(text)
        assert result == {"field": "value"}

    def test_estimate_tokens(self):
        """Verify token estimation."""
        from automatia_shared.utils import estimate_tokens

        text = "a" * 100  # 100 characters
        tokens = estimate_tokens(text)
        assert tokens == 25  # ~4 chars per token

    def test_format_currency_spanish(self):
        """Verify Spanish currency formatting."""
        from automatia_shared.utils import format_currency

        result = format_currency(1234.56, "EUR", "es")
        assert "1.234,56" in result
        assert "EUR" in result


class TestImportability:
    """Tests that all public APIs are importable."""

    def test_import_from_root(self):
        """Verify main exports from package root."""
        from automatia_shared import (
            TaskStatus,
            LicenseStatus,
            ScriptStatus,
            FlowSpec,
            TaskSpec,
        )

        assert TaskStatus is not None
        assert FlowSpec is not None

    def test_import_enums_module(self):
        """Verify all enums are importable."""
        from automatia_shared.enums import (
            TaskStatus,
            LicenseStatus,
            ScriptStatus,
            ExtractionPhase,
            TriggerType,
            StepType,
        )

        assert all([
            TaskStatus, LicenseStatus, ScriptStatus,
            ExtractionPhase, TriggerType, StepType
        ])

    def test_import_dtos_module(self):
        """Verify all DTOs are importable."""
        from automatia_shared.dtos import (
            TaskSpec,
            FlowSpec,
            ExtractionResult,
            ScriptAuditResult,
            LicenseInfo,
            BillingRecord,
        )

        assert all([
            TaskSpec, FlowSpec, ExtractionResult,
            ScriptAuditResult, LicenseInfo, BillingRecord
        ])

    def test_import_validators_module(self):
        """Verify all validators are importable."""
        from automatia_shared.validators import (
            validate_license_key_format,
            hash_license_key,
            validate_dni_format,
            validate_iban_format,
            validate_email_format,
            sanitize_filename,
            validate_script_imports,
        )

        assert all([
            validate_license_key_format, hash_license_key,
            validate_dni_format, validate_iban_format,
            validate_email_format, sanitize_filename,
            validate_script_imports
        ])

    def test_import_utils_module(self):
        """Verify all utils are importable."""
        from automatia_shared.utils import (
            generate_code_hash,
            normalize_whitespace,
            safe_json_loads,
            safe_json_dumps,
            truncate_text,
            extract_json_from_text,
            flatten_dict,
            estimate_tokens,
            format_currency,
            parse_iso_datetime,
        )

        assert all([
            generate_code_hash, normalize_whitespace,
            safe_json_loads, safe_json_dumps, truncate_text,
            extract_json_from_text, flatten_dict, estimate_tokens,
            format_currency, parse_iso_datetime
        ])

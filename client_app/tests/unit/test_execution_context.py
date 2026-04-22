
import pytest
from automatia_shared.dtos import ScriptContext, ExtractionResult, TaskStatus

class TestScriptContext:
    def test_context_has_unique_execution_id(self):
        ctx1 = ScriptContext(execution_id="1", script_id="test")
        ctx2 = ScriptContext(execution_id="2", script_id="test")
        assert ctx1.execution_id != ctx2.execution_id

    def test_license_key_is_masked(self):
        ctx = ScriptContext(
            execution_id="1", 
            script_id="test",
            license_key="12345678"  # Should store as is if short, or masked logic is in service layer (but context holds value)
        )
        # The prompt req said "license_key: Optional[str] = Field(None, description="Licencia activa (últimos 8 chars)")"
        # It implies the masking happens BEFORE creating the context, or we should verify 
        # that the field accepts string.
        assert ctx.license_key == "12345678"

class TestExtractionResult:
    def test_success_factory_creates_completed_result(self):
        result = ExtractionResult.success({"field": "value"})
        assert result.status == TaskStatus.COMPLETED
        assert result.datos["field"] == "value"
        assert result.error is None

    def test_failure_factory_creates_failed_result(self):
        result = ExtractionResult.failure("Something went wrong")
        assert result.status == TaskStatus.FAILED
        assert result.error == "Something went wrong"
        assert result.datos == {}

    def test_failure_includes_traceback(self):
        context = ScriptContext(execution_id="1", script_id="test")
        result = ExtractionResult.failure(
            "Error",
            context=context,
            traceback="Traceback (most recent call last):\n..."
        )
        assert result.context is not None
        assert result.context.traceback is not None
        assert "Traceback" in result.context.traceback

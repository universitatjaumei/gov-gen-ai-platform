import pytest
from app.services.sandbox_service import SandboxExecutionService
from automatia_shared.core.execution_manager import ExecutionPathManager

@pytest.fixture
def sandbox(tmp_path):
    """Sandbox configurado para tests de seguridad."""
    manager = ExecutionPathManager(app_name="test_sandbox")
    # Usar tmp_path como base para aislar ejecuciones
    manager.base_dir = tmp_path
    manager.executions_base = tmp_path / "executions"
    manager.executions_base.mkdir(parents=True, exist_ok=True)

    return SandboxExecutionService(manager)


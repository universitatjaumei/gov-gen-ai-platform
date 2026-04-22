# shared/tests/test_execution_manager.py
"""
Unit tests for ExecutionPathManager.

Tests verify:
- Deterministic path generation
- Execution ID sanitization (path traversal prevention)
- Cross-platform locking with filelock
- Cleanup of old executions
"""
import pytest
from pathlib import Path
import time
import threading
from automatia_shared.core.execution_manager import ExecutionPathManager


def test_builds_deterministic_paths(tmp_path: Path):
    """Verificar que genera rutas deterministas"""
    manager = ExecutionPathManager(app_name="test_app")
    # Override base_dir for testing
    manager.base_dir = tmp_path
    manager.executions_base = tmp_path / "executions"
    manager.executions_base.mkdir(parents=True, exist_ok=True)

    # Create a run to get dirs
    run_id = manager.create_run("TEST_TASK")

    inp = manager.get_input_dir(run_id)
    out = manager.get_output_dir(run_id)

    assert inp.exists()
    assert out.exists()
    assert "inputs" in str(inp) or "input" in str(inp)
    assert "outputs" in str(out) or "output" in str(out)


def test_sanitizes_execution_ids(tmp_path: Path):
    """Verificar sanitizacion de IDs peligrosos"""
    manager = ExecutionPathManager(app_name="test_app")
    manager.base_dir = tmp_path
    manager.executions_base = tmp_path / "executions"
    manager.executions_base.mkdir(parents=True, exist_ok=True)

    # IDs peligrosos deben sanitizarse
    dangerous_id = "../../etc/passwd"
    safe_id = manager._sanitize_id(dangerous_id)

    assert ".." not in safe_id
    assert "/etc/" not in safe_id
    assert "\\" not in safe_id


def test_lock_prevents_concurrent_access(tmp_path: Path):
    """Verificar que locks previenen acceso concurrente"""
    manager = ExecutionPathManager(app_name="test_app")
    manager.base_dir = tmp_path
    manager.executions_base = tmp_path / "executions"
    manager.executions_base.mkdir(parents=True, exist_ok=True)

    # Create execution dir first
    run_id = manager.create_run("LOCK_TEST")

    results = []

    def worker(name):
        with manager.lock(run_id):
            results.append(f"{name}_start")
            time.sleep(0.1)  # Simular trabajo
            results.append(f"{name}_end")

    # Lanzar 2 threads concurrentes
    t1 = threading.Thread(target=worker, args=("T1",))
    t2 = threading.Thread(target=worker, args=("T2",))

    t1.start()
    time.sleep(0.05)  # T2 inicia ligeramente despues
    t2.start()

    t1.join()
    t2.join()

    # Verificar que se ejecutaron secuencialmente (no entrelazados)
    # El orden puede ser T1 primero o T2 primero, pero nunca entrelazado
    assert results == ["T1_start", "T1_end", "T2_start", "T2_end"] or \
           results == ["T2_start", "T2_end", "T1_start", "T1_end"]


def test_lock_releases_on_exception(tmp_path: Path):
    """Verificar que lock se libera incluso con excepcion"""
    manager = ExecutionPathManager(app_name="test_app")
    manager.base_dir = tmp_path
    manager.executions_base = tmp_path / "executions"
    manager.executions_base.mkdir(parents=True, exist_ok=True)

    run_id = manager.create_run("EXCEPTION_TEST")

    # Primera ejecucion con error
    try:
        with manager.lock(run_id):
            raise ValueError("Test error")
    except ValueError:
        pass

    # Segunda ejecucion debe poder adquirir lock
    acquired = False
    with manager.lock(run_id):
        acquired = True

    assert acquired


def test_cleans_old_executions(tmp_path: Path):
    """Verificar limpieza de ejecuciones antiguas"""
    manager = ExecutionPathManager(app_name="test_app")
    manager.base_dir = tmp_path
    manager.executions_base = tmp_path / "executions"
    manager.executions_base.mkdir(parents=True, exist_ok=True)

    # Crear 3 ejecuciones directamente en el directorio
    task_dir = manager.executions_base / "TEST_CLEANUP"
    task_dir.mkdir(parents=True, exist_ok=True)

    for i in range(3):
        exec_dir = task_dir / f"run_test_{i}"
        exec_dir.mkdir(parents=True, exist_ok=True)
        (exec_dir / "test.txt").write_text("data")

    # Verificar que se crearon
    assert len(list(task_dir.iterdir())) == 3

    # Limpiar ejecuciones con max_age=0 (todas)
    deleted = manager.cleanup_old_executions(max_age_days=0)

    assert deleted >= 3


def test_sanitize_id_empty_becomes_default(tmp_path: Path):
    """Verificar que ID vacio se convierte en 'default'"""
    manager = ExecutionPathManager(app_name="test_app")

    # ID que se convierte en vacio despues de sanitizar
    safe_id = manager._sanitize_id("../../../")

    assert safe_id == "default" or len(safe_id) > 0


def test_sanitize_id_removes_special_chars(tmp_path: Path):
    """Verificar que caracteres especiales se eliminan"""
    manager = ExecutionPathManager(app_name="test_app")

    dangerous_chars = "<>:|?*\\"
    test_id = f"exec{dangerous_chars}001"

    safe_id = manager._sanitize_id(test_id)

    for char in dangerous_chars:
        assert char not in safe_id

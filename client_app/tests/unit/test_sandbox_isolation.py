import pytest
import shutil
from unittest.mock import MagicMock, patch
from pathlib import Path
from client_app.app.services.sandbox_service import SandboxExecutionService

@pytest.fixture
def mock_path_manager(tmp_path):
    pm = MagicMock()
    def get_path(exec_id):
        p = tmp_path / exec_id
        (p / "input").mkdir(parents=True, exist_ok=True)
        (p / "sandbox").mkdir(parents=True, exist_ok=True)
        (p / "output").mkdir(parents=True, exist_ok=True)
        return p
    pm.get_execution_path.side_effect = get_path
    return pm

@pytest.mark.asyncio
async def test_sandbox_blocks_open(mock_path_manager, tmp_path):
    """Verifica que open() está bloqueado dentro del proceso."""
    svc = SandboxExecutionService(mock_path_manager)
    exec_id = "test_block_open"
    
    # Crear archivo dummy para que el loop de ejecución tenga algo que procesar
    p = mock_path_manager.get_execution_path(exec_id)
    (p / "input" / "dummy.txt").write_text("data")

    # Script malicioso: intenta escribir fuera del jail usando ruta absoluta (Windows drive)
    code = """
def extraer_datos(filepath):
    with open('C:/hacked_outside.txt', 'w') as f:
        f.write('hacked')
    return {}
"""
    with patch('client_app.app.services.sandbox_service.validate_code_ast', return_value=True):
        result = await svc.execute_in_sandbox(code, [str(p / "input" / "dummy.txt")], exec_id)
    
    # Debe fallar y reportar error de permiso
    assert result["success"] is True
    item_result = result["data"][0]
    assert item_result["status"] == "error"
    assert "Blocked write to outside jail" in item_result["error"]

@pytest.mark.asyncio
async def test_sandbox_blocks_dangerous_imports(mock_path_manager):
    """Verifica que import os está bloqueado."""
    svc = SandboxExecutionService(mock_path_manager)
    exec_id = "test_block_import"
    
    p = mock_path_manager.get_execution_path(exec_id)
    (p / "input" / "dummy.txt").write_text("data")

    code = """
def extraer_datos(filepath):
    import smtplib
    return {'status': 'not_blocked'}
"""
    with patch('client_app.app.services.sandbox_service.validate_code_ast', return_value=True):
        result = await svc.execute_in_sandbox(code, [str(p / "input" / "dummy.txt")], exec_id)
    
    assert result["success"] is True
    item_result = result["data"][0]
    assert item_result["status"] == "error"
    assert "Blocked import: smtplib" in item_result["error"]

@pytest.mark.asyncio
async def test_sandbox_allows_allowed_imports(mock_path_manager):
    """Verifica que json y re están permitidos."""
    svc = SandboxExecutionService(mock_path_manager)
    exec_id = "test_allow_import"
    
    p = mock_path_manager.get_execution_path(exec_id)
    (p / "input" / "dummy.txt").write_text("data")

    code = """
import json
import re
def extraer_datos(filepath):
    return {"status": "ok"}
"""
    result = await svc.execute_in_sandbox(code, [str(p / "input" / "dummy.txt")], exec_id)
    
    assert result["success"] is True
    item_result = result["data"][0]
    assert item_result["status"] == "success"
    assert item_result["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_sandbox_allows_internal_service_import(mock_path_manager):
    """
    Verifica que el Sandbox permite importar el módulo de servicio interno.
    Esto es crítico para la compatibilidad con multiprocessing en Windows.
    """
    svc = SandboxExecutionService(mock_path_manager)
    exec_id = "test_internal_import"
    
    p = mock_path_manager.get_execution_path(exec_id)
    (p / "input" / "dummy.txt").write_text("data")

    # Intentar importar el propio servicio (que es lo que rompe en Windows)
    code = """
def extraer_datos(filepath):
    import client_app.app.services.sandbox_service as ss
    return {"status": "ok", "service_found": ss is not None}
"""
    with patch('client_app.app.services.sandbox_service.validate_code_ast', return_value=True):
        result = await svc.execute_in_sandbox(code, [str(p / "input" / "dummy.txt")], exec_id)
    
    assert result["success"] is True
    item_result = result["data"][0]
    assert item_result["status"] == "success", f"Failed with: {item_result.get('error')}"
    assert item_result["data"]["service_found"] is True


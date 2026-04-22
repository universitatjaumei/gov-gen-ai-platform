"""
Tests unitarios para AutomatismImportService.
Prompt 3.2 del sistema de exportacion/importacion de automatismos.

Valida la importacion de scripts, playbooks y workflows desde paquetes .automatia.
"""

import pytest
import zipfile
import json
import hashlib
from io import BytesIO
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from client_app.app.services.automatism_import_service import (
    AutomatismImportService,
    ConflictResolution,
    ImportResult,
    automatism_import_service
)
from client_app.app.services.import_validation_service import (
    ImportPermission,
    ValidationResult
)


# === FIXTURES ===

@pytest.fixture
def valid_manifest():
    """Manifiesto valido de prueba."""
    return {
        "version": "1.0",
        "name": "Test Package",
        "description": "Paquete de prueba",
        "export_date": datetime.now(timezone.utc).isoformat(),
        "source": {
            "license_id": "LIC-12345678",
            "client_id": "CLI-12345678",
            "partner_id": "PARTNER-ABC123",
            "machine_id": "WIN-TESTMACHINE"
        },
        "contents": {
            "scripts": ["test_script.py"],
            "playbooks": ["test_playbook.json"],
            "workflows": []
        },
        "file_hashes": {},
        "signature": {
            "type": "CLIENT",
            "algorithm": "HMAC-SHA256",
            "value": "dummy_signature",
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        "package_hash": "dummy_hash"
    }


@pytest.fixture
def script_code():
    """Codigo de script de prueba."""
    return """
import pandas as pd

def transform(df):
    '''Transforma el DataFrame.'''
    return df.dropna()
"""


@pytest.fixture
def script_metadata():
    """Metadatos de script de prueba."""
    return {
        "id": 1,
        "name": "test_script",
        "status": "draft",
        "description": "Script de prueba",
        "code_hash": "abc123",
        "input_type": "file",
        "output_type": "file",
        "tags": ["test"],
        "required_libraries": ["pandas"]
    }


@pytest.fixture
def playbook_actions():
    """Acciones de playbook de prueba."""
    return [
        {"type": "navigate", "url": "https://example.com"},
        {"type": "click", "selector": "#button"}
    ]


@pytest.fixture
def playbook_metadata():
    """Metadatos de playbook de prueba."""
    return {
        "id": 1,
        "name": "test_playbook",
        "description": "Playbook de prueba",
        "base_url": "https://example.com",
        "content_hash": "xyz789"
    }


@pytest.fixture
def valid_package_bytes(valid_manifest, script_code, script_metadata, playbook_actions, playbook_metadata):
    """Crea un paquete .automatia valido en memoria."""
    buffer = BytesIO()

    script_bytes = script_code.encode('utf-8')
    script_meta_bytes = json.dumps(script_metadata).encode('utf-8')
    playbook_bytes = json.dumps(playbook_actions).encode('utf-8')
    playbook_meta_bytes = json.dumps(playbook_metadata).encode('utf-8')

    valid_manifest["file_hashes"] = {
        "scripts/test_script.py": hashlib.sha256(script_bytes).hexdigest(),
        "metadata/scripts/test_script.json": hashlib.sha256(script_meta_bytes).hexdigest(),
        "playbooks/test_playbook.json": hashlib.sha256(playbook_bytes).hexdigest(),
        "metadata/playbooks/test_playbook.json": hashlib.sha256(playbook_meta_bytes).hexdigest()
    }

    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("scripts/test_script.py", script_bytes)
        zf.writestr("metadata/scripts/test_script.json", script_meta_bytes)
        zf.writestr("playbooks/test_playbook.json", playbook_bytes)
        zf.writestr("metadata/playbooks/test_playbook.json", playbook_meta_bytes)
        zf.writestr("manifest.json", json.dumps(valid_manifest, indent=2))

    return buffer.getvalue()


@pytest.fixture
def mock_validation_result(valid_manifest):
    """ValidationResult mock para tests."""
    return ValidationResult(
        is_valid=True,
        permission=ImportPermission.ALLOWED,
        errors=[],
        warnings=[],
        conflicts=[],
        manifest=valid_manifest,
        source_info=valid_manifest["source"]
    )


@pytest.fixture
def service():
    """Instancia del servicio."""
    return AutomatismImportService()


# === TESTS DE IMPORTACION DE SCRIPTS ===

@pytest.mark.asyncio
async def test_import_script_creates_record(service, valid_package_bytes, mock_validation_result):
    """Script importado se guarda en BD."""
    with patch.object(service, '_validate_package', new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = mock_validation_result

        with patch.object(service, '_save_script', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = 1  # ID del script creado

            with patch.object(service, '_save_playbook', new_callable=AsyncMock) as mock_save_pb:
                mock_save_pb.return_value = 1

                with patch.object(service, '_record_import', new_callable=AsyncMock):
                    result = await service.import_package(valid_package_bytes)

                    assert result.success is True
                    assert result.scripts_imported >= 1
                    mock_save.assert_called()


@pytest.mark.asyncio
async def test_import_script_preserves_code(service, valid_package_bytes, mock_validation_result, script_code):
    """El codigo se importa intacto."""
    saved_scripts = []

    async def capture_script(script_data):
        saved_scripts.append(script_data)
        return 1

    with patch.object(service, '_validate_package', new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = mock_validation_result

        with patch.object(service, '_save_script', new_callable=AsyncMock) as mock_save:
            mock_save.side_effect = capture_script

            with patch.object(service, '_save_playbook', new_callable=AsyncMock) as mock_save_pb:
                mock_save_pb.return_value = 1

                with patch.object(service, '_record_import', new_callable=AsyncMock):
                    await service.import_package(valid_package_bytes)

                    assert len(saved_scripts) > 0
                    # Verificar que el codigo se preserva
                    assert saved_scripts[0]['code'].strip() == script_code.strip()


@pytest.mark.asyncio
async def test_import_script_tracks_origin(service, valid_package_bytes, mock_validation_result):
    """Guarda origin_license_id y origin_package_id."""
    saved_scripts = []

    async def capture_script(script_data):
        saved_scripts.append(script_data)
        return 1

    with patch.object(service, '_validate_package', new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = mock_validation_result

        with patch.object(service, '_save_script', new_callable=AsyncMock) as mock_save:
            mock_save.side_effect = capture_script

            with patch.object(service, '_save_playbook', new_callable=AsyncMock) as mock_save_pb:
                mock_save_pb.return_value = 1

                with patch.object(service, '_record_import', new_callable=AsyncMock):
                    await service.import_package(valid_package_bytes)

                    assert len(saved_scripts) > 0
                    script = saved_scripts[0]
                    assert 'origin_license_id' in script
                    assert script['origin_license_id'] == "LIC-12345678"
                    assert 'origin_package_id' in script


# === TESTS DE IMPORTACION DE PLAYBOOKS ===

@pytest.mark.asyncio
async def test_import_playbook_creates_record(service, valid_package_bytes, mock_validation_result):
    """Playbook importado se guarda."""
    with patch.object(service, '_validate_package', new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = mock_validation_result

        with patch.object(service, '_save_script', new_callable=AsyncMock) as mock_save_script:
            mock_save_script.return_value = 1

            with patch.object(service, '_save_playbook', new_callable=AsyncMock) as mock_save_pb:
                mock_save_pb.return_value = 1

                with patch.object(service, '_record_import', new_callable=AsyncMock):
                    result = await service.import_package(valid_package_bytes)

                    assert result.success is True
                    assert result.playbooks_imported >= 1
                    mock_save_pb.assert_called()


# === TESTS DE IMPORTACION DE WORKFLOWS ===

@pytest.mark.asyncio
async def test_import_workflow_creates_flow(service, mock_validation_result):
    """Workflow se importa como FlowRegistry."""
    # Crear paquete con workflow
    workflow_spec = {
        "name": "Test Workflow",
        "description": "Workflow de prueba",
        "version": "1.0.0",
        "status": "DRAFT",
        "trigger_type": "manual",
        "trigger_config": {},
        "steps": [{"type": "extraction", "config": {}}],
        "is_active": True
    }

    manifest = mock_validation_result.manifest.copy()
    manifest["contents"]["workflows"] = ["test_workflow.json"]
    manifest["contents"]["scripts"] = []
    manifest["contents"]["playbooks"] = []

    workflow_bytes = json.dumps(workflow_spec).encode('utf-8')
    manifest["file_hashes"]["workflows/test_workflow.json"] = hashlib.sha256(workflow_bytes).hexdigest()

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zf:
        zf.writestr("workflows/test_workflow.json", workflow_bytes)
        zf.writestr("manifest.json", json.dumps(manifest))

    mock_validation_result.manifest = manifest

    with patch.object(service, '_validate_package', new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = mock_validation_result

        with patch.object(service, '_save_workflow', new_callable=AsyncMock) as mock_save_wf:
            mock_save_wf.return_value = 1

            with patch.object(service, '_record_import', new_callable=AsyncMock):
                result = await service.import_package(buffer.getvalue())

                assert result.success is True
                assert result.workflows_imported >= 1
                mock_save_wf.assert_called()


# === TESTS DE MANEJO DE CONFLICTOS ===

@pytest.mark.asyncio
async def test_import_handles_rename_conflict(service, valid_package_bytes, mock_validation_result):
    """Renombra si hay conflicto con resolucion RENAME."""
    # Agregar conflicto
    mock_validation_result.conflicts = [
        {"name": "test_script", "type": "script", "local_id": 99, "action": "rename"}
    ]

    saved_scripts = []

    async def capture_script(script_data):
        saved_scripts.append(script_data)
        return 1

    conflict_resolutions = {"test_script": ConflictResolution.RENAME}

    with patch.object(service, '_validate_package', new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = mock_validation_result

        with patch.object(service, '_save_script', new_callable=AsyncMock) as mock_save:
            mock_save.side_effect = capture_script

            with patch.object(service, '_save_playbook', new_callable=AsyncMock) as mock_save_pb:
                mock_save_pb.return_value = 1

                with patch.object(service, '_record_import', new_callable=AsyncMock):
                    result = await service.import_package(
                        valid_package_bytes,
                        conflict_resolutions=conflict_resolutions
                    )

                    assert result.success is True
                    # El script debe haberse renombrado
                    if saved_scripts:
                        assert saved_scripts[0]['name'] != "test_script" or "_imported" in saved_scripts[0]['name']


@pytest.mark.asyncio
async def test_import_handles_overwrite_conflict(service, valid_package_bytes, mock_validation_result):
    """Sobrescribe si se indica con resolucion OVERWRITE."""
    mock_validation_result.conflicts = [
        {"name": "test_script", "type": "script", "local_id": 99, "action": "rename"}
    ]

    conflict_resolutions = {"test_script": ConflictResolution.OVERWRITE}

    with patch.object(service, '_validate_package', new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = mock_validation_result

        with patch.object(service, '_update_script', new_callable=AsyncMock) as mock_update:
            mock_update.return_value = 99

            with patch.object(service, '_save_playbook', new_callable=AsyncMock) as mock_save_pb:
                mock_save_pb.return_value = 1

                with patch.object(service, '_record_import', new_callable=AsyncMock):
                    result = await service.import_package(
                        valid_package_bytes,
                        conflict_resolutions=conflict_resolutions
                    )

                    assert result.success is True
                    mock_update.assert_called()


@pytest.mark.asyncio
async def test_import_handles_skip_conflict(service, valid_package_bytes, mock_validation_result):
    """Omite si se indica con resolucion SKIP."""
    mock_validation_result.conflicts = [
        {"name": "test_script", "type": "script", "local_id": 99, "action": "rename"}
    ]

    conflict_resolutions = {"test_script": ConflictResolution.SKIP}

    with patch.object(service, '_validate_package', new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = mock_validation_result

        with patch.object(service, '_save_script', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = 1

            with patch.object(service, '_save_playbook', new_callable=AsyncMock) as mock_save_pb:
                mock_save_pb.return_value = 1

                with patch.object(service, '_record_import', new_callable=AsyncMock):
                    result = await service.import_package(
                        valid_package_bytes,
                        conflict_resolutions=conflict_resolutions
                    )

                    assert result.success is True
                    assert result.skipped >= 1


# === TESTS DE ESTADO DE SCRIPTS IMPORTADOS ===

@pytest.mark.asyncio
async def test_imported_draft_stays_draft(service, valid_package_bytes, mock_validation_result):
    """Script DRAFT importado queda como DRAFT."""
    saved_scripts = []

    async def capture_script(script_data):
        saved_scripts.append(script_data)
        return 1

    with patch.object(service, '_validate_package', new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = mock_validation_result

        with patch.object(service, '_save_script', new_callable=AsyncMock) as mock_save:
            mock_save.side_effect = capture_script

            with patch.object(service, '_save_playbook', new_callable=AsyncMock) as mock_save_pb:
                mock_save_pb.return_value = 1

                with patch.object(service, '_record_import', new_callable=AsyncMock):
                    await service.import_package(valid_package_bytes)

                    assert len(saved_scripts) > 0
                    # Script importado debe ser draft
                    assert saved_scripts[0]['status'] == 'draft'


@pytest.mark.asyncio
async def test_imported_from_partner_is_published(service, valid_package_bytes, mock_validation_result):
    """Con firma partner, script puede ser PUBLISHED."""
    # Cambiar firma a PARTNER
    mock_validation_result.manifest["signature"]["type"] = "PARTNER"

    saved_scripts = []

    async def capture_script(script_data):
        saved_scripts.append(script_data)
        return 1

    with patch.object(service, '_validate_package', new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = mock_validation_result

        with patch.object(service, '_save_script', new_callable=AsyncMock) as mock_save:
            mock_save.side_effect = capture_script

            with patch.object(service, '_save_playbook', new_callable=AsyncMock) as mock_save_pb:
                mock_save_pb.return_value = 1

                with patch.object(service, '_record_import', new_callable=AsyncMock):
                    await service.import_package(valid_package_bytes)

                    assert len(saved_scripts) > 0
                    # Con firma partner, puede ser published
                    assert saved_scripts[0]['status'] == 'published'


# === TESTS DE PERMISOS ===

@pytest.mark.asyncio
async def test_import_denied_raises_error(service, valid_package_bytes, mock_validation_result):
    """Importacion denegada lanza error."""
    mock_validation_result.permission = ImportPermission.DENIED

    with patch.object(service, '_validate_package', new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = mock_validation_result

        with pytest.raises(PermissionError):
            await service.import_package(valid_package_bytes)


@pytest.mark.asyncio
async def test_import_requires_partner_without_token_raises(service, valid_package_bytes, mock_validation_result):
    """Importacion que requiere partner sin token lanza error."""
    mock_validation_result.permission = ImportPermission.REQUIRES_PARTNER

    with patch.object(service, '_validate_package', new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = mock_validation_result

        with pytest.raises(PermissionError):
            await service.import_package(valid_package_bytes)


@pytest.mark.asyncio
async def test_import_requires_partner_with_token_succeeds(service, valid_package_bytes, mock_validation_result):
    """Importacion que requiere partner con token valido funciona."""
    mock_validation_result.permission = ImportPermission.REQUIRES_PARTNER

    with patch.object(service, '_validate_package', new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = mock_validation_result

        with patch.object(service, '_verify_partner_token', new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = True

            with patch.object(service, '_save_script', new_callable=AsyncMock) as mock_save:
                mock_save.return_value = 1

                with patch.object(service, '_save_playbook', new_callable=AsyncMock) as mock_save_pb:
                    mock_save_pb.return_value = 1

                    with patch.object(service, '_record_import', new_callable=AsyncMock):
                        result = await service.import_package(
                            valid_package_bytes,
                            partner_approval_token="valid_token"
                        )

                        assert result.success is True


# === TESTS DE VALIDACION ===

@pytest.mark.asyncio
async def test_import_invalid_package_raises(service):
    """Paquete invalido lanza error."""
    invalid_validation = ValidationResult(
        is_valid=False,
        permission=ImportPermission.DENIED,
        errors=["Paquete corrupto"],
        warnings=[],
        conflicts=[],
        manifest=None,
        source_info=None
    )

    with patch.object(service, '_validate_package', new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = invalid_validation

        with pytest.raises(ValueError) as exc_info:
            await service.import_package(b"invalid")

        assert "invalido" in str(exc_info.value).lower() or "corrupto" in str(exc_info.value).lower()


# === TESTS DE ESTRUCTURA ===

@pytest.mark.asyncio
async def test_import_result_structure(service, valid_package_bytes, mock_validation_result):
    """ImportResult tiene la estructura correcta."""
    with patch.object(service, '_validate_package', new_callable=AsyncMock) as mock_validate:
        mock_validate.return_value = mock_validation_result

        with patch.object(service, '_save_script', new_callable=AsyncMock) as mock_save:
            mock_save.return_value = 1

            with patch.object(service, '_save_playbook', new_callable=AsyncMock) as mock_save_pb:
                mock_save_pb.return_value = 1

                with patch.object(service, '_record_import', new_callable=AsyncMock):
                    result = await service.import_package(valid_package_bytes)

                    assert isinstance(result, ImportResult)
                    assert hasattr(result, 'success')
                    assert hasattr(result, 'scripts_imported')
                    assert hasattr(result, 'playbooks_imported')
                    assert hasattr(result, 'workflows_imported')
                    assert hasattr(result, 'skipped')


@pytest.mark.asyncio
async def test_singleton_exists():
    """El singleton del servicio existe."""
    assert automatism_import_service is not None
    assert isinstance(automatism_import_service, AutomatismImportService)

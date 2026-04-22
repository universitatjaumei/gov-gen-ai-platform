"""
Tests para el servicio de exportación de automatismos.
Prompt 2.1 del sistema de exportación/importación de automatismos.

Verifican:
- Exportación de scripts individuales y múltiples
- Exportación de playbooks
- Exportación mixta (scripts + playbooks)
- Estructura correcta del ZIP
- Presencia y firma del manifiesto
"""

import pytest
import zipfile
import json
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from client_app.app.services.automatism_export_service import (
    AutomatismExportService,
    automatism_export_service
)


# === FIXTURES ===

@pytest.fixture
def mock_script():
    """Crea un mock de CustomScript con todos los atributos requeridos."""
    script = MagicMock(spec=[
        'id', 'name', 'code', 'code_hash', 'status', 'description',
        'input_type', 'output_type', 'tags', 'required_libraries'
    ])
    script.id = 1
    script.name = "transformar_datos"
    script.code = """def transform(df):
    return df.dropna()
"""
    script.code_hash = "abc123hash"
    script.status = "published"
    script.description = "Elimina filas con valores nulos"
    script.input_type = "file"
    script.output_type = "file"
    script.tags = ["etl", "limpieza"]
    script.required_libraries = ["pandas"]
    return script


@pytest.fixture
def mock_script_2():
    """Crea un segundo mock de CustomScript."""
    script = MagicMock(spec=[
        'id', 'name', 'code', 'code_hash', 'status', 'description',
        'input_type', 'output_type', 'tags', 'required_libraries'
    ])
    script.id = 2
    script.name = "validar_email"
    script.code = """import re

def validate_email(email):
    pattern = r'^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$'
    return bool(re.match(pattern, email))
"""
    script.code_hash = "def456hash"
    script.status = "draft"
    script.description = "Valida formato de email"
    script.input_type = "text"
    script.output_type = "text"
    script.tags = ["validacion"]
    script.required_libraries = []
    return script


@pytest.fixture
def mock_playbook():
    """Crea un mock de RpaPlaybook con todos los atributos requeridos."""
    playbook = MagicMock(spec=['id', 'name', 'description', 'actions', 'base_url'])
    playbook.id = 1
    playbook.name = "login_portal"
    playbook.description = "Automatiza login en portal web"
    playbook.base_url = "https://example.com"
    playbook.actions = json.dumps([
        {"action": "goto", "url": "https://example.com/login"},
        {"action": "fill", "selector": "#username", "value": "{{username}}"},
        {"action": "fill", "selector": "#password", "value": "{{password}}"},
        {"action": "click", "selector": "#submit"}
    ])
    return playbook


@pytest.fixture
def mock_source_info():
    """Información de origen para el paquete."""
    return {
        "license_id": "LIC-001-ABC",
        "client_id": "CLI-001",
        "partner_id": "PARTNER-001",
        "machine_id": "MACHINE-XYZ",
        "license_key": "secret-license-key-123"
    }


@pytest.fixture
def export_service():
    """Crea instancia del servicio de exportación con mocks."""
    service = AutomatismExportService()
    return service


# === TESTS DE EXPORTACIÓN DE SCRIPTS ===

@pytest.mark.asyncio
async def test_export_single_script(export_service, mock_script, mock_source_info):
    """Exportar un script genera ZIP válido."""
    # Arrange
    with patch.object(export_service, '_load_scripts', new_callable=AsyncMock) as mock_load:
        with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
            mock_load.return_value = [mock_script]
            mock_info.return_value = mock_source_info

            # Act
            result = await export_service.export_package(
                name="Mi Paquete",
                script_ids=[1],
                description="Paquete de prueba"
            )

            # Assert
            assert isinstance(result, bytes)
            assert len(result) > 0

            # Verificar que es un ZIP válido
            buffer = BytesIO(result)
            with zipfile.ZipFile(buffer, 'r') as zf:
                names = zf.namelist()
                assert f"scripts/{mock_script.name}.py" in names


@pytest.mark.asyncio
async def test_export_multiple_scripts(export_service, mock_script, mock_script_2, mock_source_info):
    """Exportar varios scripts los incluye a todos en el ZIP."""
    # Arrange
    with patch.object(export_service, '_load_scripts', new_callable=AsyncMock) as mock_load:
        with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
            mock_load.return_value = [mock_script, mock_script_2]
            mock_info.return_value = mock_source_info

            # Act
            result = await export_service.export_package(
                name="Paquete Multi-Script",
                script_ids=[1, 2]
            )

            # Assert
            buffer = BytesIO(result)
            with zipfile.ZipFile(buffer, 'r') as zf:
                names = zf.namelist()
                assert f"scripts/{mock_script.name}.py" in names
                assert f"scripts/{mock_script_2.name}.py" in names
                # También deben existir los metadatos
                assert f"metadata/scripts/{mock_script.name}.json" in names
                assert f"metadata/scripts/{mock_script_2.name}.json" in names


@pytest.mark.asyncio
async def test_export_playbook(export_service, mock_playbook, mock_source_info):
    """Exportar playbook lo incluye en el ZIP."""
    # Arrange
    with patch.object(export_service, '_load_playbooks', new_callable=AsyncMock) as mock_load:
        with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
            with patch.object(export_service, '_load_scripts', new_callable=AsyncMock) as mock_scripts:
                mock_load.return_value = [mock_playbook]
                mock_scripts.return_value = []
                mock_info.return_value = mock_source_info

                # Act
                result = await export_service.export_package(
                    name="Paquete Playbook",
                    playbook_ids=[1]
                )

                # Assert
                buffer = BytesIO(result)
                with zipfile.ZipFile(buffer, 'r') as zf:
                    names = zf.namelist()
                    assert f"playbooks/{mock_playbook.name}.json" in names
                    assert f"metadata/playbooks/{mock_playbook.name}.json" in names


@pytest.mark.asyncio
async def test_export_mixed(export_service, mock_script, mock_playbook, mock_source_info):
    """Exportar scripts + playbooks juntos los incluye a ambos."""
    # Arrange
    with patch.object(export_service, '_load_scripts', new_callable=AsyncMock) as mock_load_scripts:
        with patch.object(export_service, '_load_playbooks', new_callable=AsyncMock) as mock_load_pb:
            with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
                mock_load_scripts.return_value = [mock_script]
                mock_load_pb.return_value = [mock_playbook]
                mock_info.return_value = mock_source_info

                # Act
                result = await export_service.export_package(
                    name="Paquete Mixto",
                    script_ids=[1],
                    playbook_ids=[1],
                    description="Scripts y playbooks juntos"
                )

                # Assert
                buffer = BytesIO(result)
                with zipfile.ZipFile(buffer, 'r') as zf:
                    names = zf.namelist()
                    # Scripts
                    assert f"scripts/{mock_script.name}.py" in names
                    assert f"metadata/scripts/{mock_script.name}.json" in names
                    # Playbooks
                    assert f"playbooks/{mock_playbook.name}.json" in names
                    assert f"metadata/playbooks/{mock_playbook.name}.json" in names


# === TESTS DE ESTRUCTURA DEL ZIP ===

@pytest.mark.asyncio
async def test_exported_zip_has_manifest(export_service, mock_script, mock_source_info):
    """El ZIP contiene manifest.json."""
    # Arrange
    with patch.object(export_service, '_load_scripts', new_callable=AsyncMock) as mock_load:
        with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
            mock_load.return_value = [mock_script]
            mock_info.return_value = mock_source_info

            # Act
            result = await export_service.export_package(
                name="Test Manifest",
                script_ids=[1]
            )

            # Assert
            buffer = BytesIO(result)
            with zipfile.ZipFile(buffer, 'r') as zf:
                assert 'manifest.json' in zf.namelist()

                # Verificar que el manifest es JSON válido
                manifest_content = zf.read('manifest.json').decode('utf-8')
                manifest = json.loads(manifest_content)
                assert 'version' in manifest
                assert 'name' in manifest
                assert manifest['name'] == "Test Manifest"


@pytest.mark.asyncio
async def test_exported_zip_has_correct_structure(export_service, mock_script, mock_playbook, mock_source_info):
    """Estructura de carpetas correcta: scripts/, playbooks/, metadata/."""
    # Arrange
    with patch.object(export_service, '_load_scripts', new_callable=AsyncMock) as mock_load_scripts:
        with patch.object(export_service, '_load_playbooks', new_callable=AsyncMock) as mock_load_pb:
            with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
                mock_load_scripts.return_value = [mock_script]
                mock_load_pb.return_value = [mock_playbook]
                mock_info.return_value = mock_source_info

                # Act
                result = await export_service.export_package(
                    name="Test Estructura",
                    script_ids=[1],
                    playbook_ids=[1]
                )

                # Assert
                buffer = BytesIO(result)
                with zipfile.ZipFile(buffer, 'r') as zf:
                    names = zf.namelist()

                    # Verificar estructura de carpetas
                    scripts_folder = any(n.startswith('scripts/') for n in names)
                    playbooks_folder = any(n.startswith('playbooks/') for n in names)
                    metadata_folder = any(n.startswith('metadata/') for n in names)

                    assert scripts_folder, "Falta carpeta scripts/"
                    assert playbooks_folder, "Falta carpeta playbooks/"
                    assert metadata_folder, "Falta carpeta metadata/"


# === TESTS DE FIRMA ===

@pytest.mark.asyncio
async def test_export_signs_manifest(export_service, mock_script, mock_source_info):
    """El manifest está firmado con los datos del cliente."""
    # Arrange
    with patch.object(export_service, '_load_scripts', new_callable=AsyncMock) as mock_load:
        with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
            mock_load.return_value = [mock_script]
            mock_info.return_value = mock_source_info

            # Act
            result = await export_service.export_package(
                name="Test Firma",
                script_ids=[1]
            )

            # Assert
            buffer = BytesIO(result)
            with zipfile.ZipFile(buffer, 'r') as zf:
                manifest_content = zf.read('manifest.json').decode('utf-8')
                manifest = json.loads(manifest_content)

                # Verificar que tiene firma
                assert 'signature' in manifest
                assert manifest['signature'] is not None

                # Verificar estructura de la firma
                signature = manifest['signature']
                assert signature['type'] == 'CLIENT'
                assert signature['algorithm'] == 'HMAC-SHA256'
                assert 'value' in signature
                assert 'timestamp' in signature

                # Verificar que tiene package_hash
                assert 'package_hash' in manifest
                assert manifest['package_hash'] is not None


# === TESTS DE CONTENIDO ===

@pytest.mark.asyncio
async def test_script_code_preserved(export_service, mock_script, mock_source_info):
    """El código del script se preserva intacto."""
    # Arrange
    with patch.object(export_service, '_load_scripts', new_callable=AsyncMock) as mock_load:
        with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
            mock_load.return_value = [mock_script]
            mock_info.return_value = mock_source_info

            # Act
            result = await export_service.export_package(
                name="Test Codigo",
                script_ids=[1]
            )

            # Assert
            buffer = BytesIO(result)
            with zipfile.ZipFile(buffer, 'r') as zf:
                code_content = zf.read(f"scripts/{mock_script.name}.py").decode('utf-8')
                assert code_content == mock_script.code


@pytest.mark.asyncio
async def test_playbook_actions_preserved(export_service, mock_playbook, mock_source_info):
    """Las acciones del playbook se preservan intactas."""
    # Arrange
    with patch.object(export_service, '_load_playbooks', new_callable=AsyncMock) as mock_load:
        with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
            with patch.object(export_service, '_load_scripts', new_callable=AsyncMock) as mock_scripts:
                mock_load.return_value = [mock_playbook]
                mock_scripts.return_value = []
                mock_info.return_value = mock_source_info

                # Act
                result = await export_service.export_package(
                    name="Test Playbook",
                    playbook_ids=[1]
                )

                # Assert
                buffer = BytesIO(result)
                with zipfile.ZipFile(buffer, 'r') as zf:
                    pb_content = zf.read(f"playbooks/{mock_playbook.name}.json").decode('utf-8')
                    assert pb_content == mock_playbook.actions


@pytest.mark.asyncio
async def test_manifest_source_info(export_service, mock_script, mock_source_info):
    """El manifest incluye información de origen correcta."""
    # Arrange
    with patch.object(export_service, '_load_scripts', new_callable=AsyncMock) as mock_load:
        with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
            mock_load.return_value = [mock_script]
            mock_info.return_value = mock_source_info

            # Act
            result = await export_service.export_package(
                name="Test Source Info",
                script_ids=[1]
            )

            # Assert
            buffer = BytesIO(result)
            with zipfile.ZipFile(buffer, 'r') as zf:
                manifest_content = zf.read('manifest.json').decode('utf-8')
                manifest = json.loads(manifest_content)

                assert manifest['source']['license_id'] == mock_source_info['license_id']
                assert manifest['source']['client_id'] == mock_source_info['client_id']
                assert manifest['source']['partner_id'] == mock_source_info['partner_id']
                assert manifest['source']['machine_id'] == mock_source_info['machine_id']


# === TESTS DE METADATOS ===

@pytest.mark.asyncio
async def test_script_metadata_complete(export_service, mock_script, mock_source_info):
    """Los metadatos del script incluyen toda la información necesaria."""
    # Arrange
    with patch.object(export_service, '_load_scripts', new_callable=AsyncMock) as mock_load:
        with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
            mock_load.return_value = [mock_script]
            mock_info.return_value = mock_source_info

            # Act
            result = await export_service.export_package(
                name="Test Metadata",
                script_ids=[1]
            )

            # Assert
            buffer = BytesIO(result)
            with zipfile.ZipFile(buffer, 'r') as zf:
                meta_content = zf.read(f"metadata/scripts/{mock_script.name}.json").decode('utf-8')
                metadata = json.loads(meta_content)

                assert metadata['id'] == mock_script.id
                assert metadata['name'] == mock_script.name
                assert metadata['status'] == mock_script.status
                assert metadata['code_hash'] == mock_script.code_hash
                assert metadata['description'] == mock_script.description


# === TESTS DE OUTPUT ===

@pytest.mark.asyncio
async def test_export_to_file(export_service, mock_script, mock_source_info, tmp_path):
    """Exportar a archivo guarda el ZIP correctamente."""
    # Arrange
    output_file = tmp_path / "test_package.automatia"

    with patch.object(export_service, '_load_scripts', new_callable=AsyncMock) as mock_load:
        with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
            mock_load.return_value = [mock_script]
            mock_info.return_value = mock_source_info

            # Act
            result = await export_service.export_package(
                name="Test File Export",
                script_ids=[1],
                output_path=str(output_file)
            )

            # Assert
            assert result == str(output_file)
            assert output_file.exists()

            # Verificar que el archivo es un ZIP válido
            with zipfile.ZipFile(output_file, 'r') as zf:
                assert 'manifest.json' in zf.namelist()


# === TEST DEL SINGLETON ===

def test_singleton_exists():
    """Verifica que existe el singleton del servicio."""
    assert automatism_export_service is not None
    assert isinstance(automatism_export_service, AutomatismExportService)

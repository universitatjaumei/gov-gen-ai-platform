"""
Tests para la exportación de workflows completos con dependencias.
Prompt 2.2 del sistema de exportación/importación de automatismos.

Verifican:
- Exportación de la definición del workflow
- Inclusión de scripts referenciados como dependencias
- Inclusión de playbooks referenciados como dependencias
- Resolución recursiva de dependencias
- Manifest con lista de dependencias
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
def mock_flow():
    """Crea un mock de FlowRegistry con pasos que referencian scripts y playbooks."""
    flow = MagicMock(spec=[
        'id', 'name', 'description', 'version', 'status', 'trigger_type',
        'trigger_config', 'steps', 'is_active', 'owner_scope'
    ])
    flow.id = 1
    flow.name = "proceso_facturas"
    flow.description = "Procesa facturas desde email"
    flow.version = "1.0.0"
    flow.status = "PUBLISHED"
    flow.trigger_type = "manual"
    flow.trigger_config = "{}"
    flow.is_active = True
    flow.owner_scope = None
    # Steps como JSON string (como se almacena en BD)
    flow.steps = json.dumps([
        {
            "name": "Extraer datos",
            "type": "extraction",
            "config": {"config_id": 1}
        },
        {
            "name": "Transformar con script",
            "type": "custom_script",
            "config": {"script_id": 1, "input_mapping": {}}
        },
        {
            "name": "Automatizar portal",
            "type": "rpa",
            "config": {"playbook_id": 1}
        }
    ])
    return flow


@pytest.fixture
def mock_flow_multiple_scripts():
    """Crea un mock de FlowRegistry con multiples scripts."""
    flow = MagicMock(spec=[
        'id', 'name', 'description', 'version', 'status', 'trigger_type',
        'trigger_config', 'steps', 'is_active', 'owner_scope'
    ])
    flow.id = 2
    flow.name = "etl_completo"
    flow.description = "Pipeline ETL con multiples transformaciones"
    flow.version = "2.0.0"
    flow.status = "PUBLISHED"
    flow.trigger_type = "schedule"
    flow.trigger_config = '{"cron": "0 8 * * *"}'
    flow.is_active = True
    flow.owner_scope = None
    flow.steps = json.dumps([
        {
            "name": "Validar datos",
            "type": "custom_script",
            "config": {"script_id": 1}
        },
        {
            "name": "Transformar datos",
            "type": "custom_script",
            "config": {"script_id": 2}
        },
        {
            "name": "Exportar resultado",
            "type": "custom_script",
            "config": {"script_id": 3}
        }
    ])
    return flow


@pytest.fixture
def mock_flow_no_deps():
    """Crea un mock de FlowRegistry sin dependencias de scripts/playbooks."""
    flow = MagicMock(spec=[
        'id', 'name', 'description', 'version', 'status', 'trigger_type',
        'trigger_config', 'steps', 'is_active', 'owner_scope'
    ])
    flow.id = 3
    flow.name = "notificacion_simple"
    flow.description = "Envia notificacion por email"
    flow.version = "1.0.0"
    flow.status = "DRAFT"
    flow.trigger_type = "manual"
    flow.trigger_config = "{}"
    flow.is_active = True
    flow.owner_scope = None
    flow.steps = json.dumps([
        {
            "name": "Enviar email",
            "type": "email_send",
            "config": {"to": "test@example.com", "subject": "Test"}
        }
    ])
    return flow


@pytest.fixture
def mock_script():
    """Crea un mock de CustomScript."""
    script = MagicMock(spec=[
        'id', 'name', 'code', 'code_hash', 'status', 'description',
        'input_type', 'output_type', 'tags', 'required_libraries'
    ])
    script.id = 1
    script.name = "transformar_factura"
    script.code = """def transform(df):
    return df.dropna()
"""
    script.code_hash = "abc123hash"
    script.status = "published"
    script.description = "Transforma datos de factura"
    script.input_type = "file"
    script.output_type = "dataframe"
    script.tags = ["etl", "factura"]
    script.required_libraries = ["pandas"]
    return script


@pytest.fixture
def mock_script_2():
    """Segundo script mock."""
    script = MagicMock(spec=[
        'id', 'name', 'code', 'code_hash', 'status', 'description',
        'input_type', 'output_type', 'tags', 'required_libraries'
    ])
    script.id = 2
    script.name = "validar_datos"
    script.code = """def validate(df):
    return df[df['total'] > 0]
"""
    script.code_hash = "def456hash"
    script.status = "published"
    script.description = "Valida datos"
    script.input_type = "dataframe"
    script.output_type = "dataframe"
    script.tags = ["validacion"]
    script.required_libraries = ["pandas"]
    return script


@pytest.fixture
def mock_script_3():
    """Tercer script mock."""
    script = MagicMock(spec=[
        'id', 'name', 'code', 'code_hash', 'status', 'description',
        'input_type', 'output_type', 'tags', 'required_libraries'
    ])
    script.id = 3
    script.name = "exportar_csv"
    script.code = """def export(df, path):
    df.to_csv(path)
"""
    script.code_hash = "ghi789hash"
    script.status = "published"
    script.description = "Exporta a CSV"
    script.input_type = "dataframe"
    script.output_type = "file"
    script.tags = ["export"]
    script.required_libraries = ["pandas"]
    return script


@pytest.fixture
def mock_playbook():
    """Crea un mock de RpaPlaybook."""
    playbook = MagicMock(spec=['id', 'name', 'description', 'actions', 'base_url'])
    playbook.id = 1
    playbook.name = "login_erp"
    playbook.description = "Login al sistema ERP"
    playbook.base_url = "https://erp.example.com"
    playbook.actions = json.dumps([
        {"action": "goto", "url": "https://erp.example.com/login"},
        {"action": "fill", "selector": "#user", "value": "{{user}}"},
        {"action": "click", "selector": "#submit"}
    ])
    return playbook


@pytest.fixture
def mock_source_info():
    """Informacion de origen para el paquete."""
    return {
        "license_id": "LIC-001-ABC",
        "client_id": "CLI-001",
        "partner_id": "PARTNER-001",
        "machine_id": "MACHINE-XYZ",
        "license_key": "secret-license-key-123"
    }


@pytest.fixture
def export_service():
    """Crea instancia del servicio de exportacion."""
    return AutomatismExportService()


# === TESTS DE EXPORTACION DE WORKFLOW ===

@pytest.mark.asyncio
async def test_export_workflow_includes_definition(
    export_service, mock_flow, mock_script, mock_playbook, mock_source_info
):
    """El JSON del workflow se incluye en el paquete."""
    with patch.object(export_service, '_load_flow', new_callable=AsyncMock) as mock_load_flow:
        with patch.object(export_service, '_load_script', new_callable=AsyncMock) as mock_load_script:
            with patch.object(export_service, '_load_playbook', new_callable=AsyncMock) as mock_load_pb:
                with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
                    mock_load_flow.return_value = mock_flow
                    mock_load_script.return_value = mock_script
                    mock_load_pb.return_value = mock_playbook
                    mock_info.return_value = mock_source_info

                    result = await export_service.export_workflow(
                        flow_id=1,
                        name="Paquete Workflow"
                    )

                    buffer = BytesIO(result)
                    with zipfile.ZipFile(buffer, 'r') as zf:
                        names = zf.namelist()
                        # Debe existir el archivo del workflow
                        workflow_files = [n for n in names if n.startswith('workflows/')]
                        assert len(workflow_files) == 1
                        assert f"workflows/{mock_flow.name}.json" in names


@pytest.mark.asyncio
async def test_export_workflow_includes_script_dependencies(
    export_service, mock_flow, mock_script, mock_playbook, mock_source_info
):
    """Scripts referenciados en los pasos se incluyen automaticamente."""
    with patch.object(export_service, '_load_flow', new_callable=AsyncMock) as mock_load_flow:
        with patch.object(export_service, '_load_script', new_callable=AsyncMock) as mock_load_script:
            with patch.object(export_service, '_load_playbook', new_callable=AsyncMock) as mock_load_pb:
                with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
                    mock_load_flow.return_value = mock_flow
                    mock_load_script.return_value = mock_script
                    mock_load_pb.return_value = mock_playbook
                    mock_info.return_value = mock_source_info

                    result = await export_service.export_workflow(
                        flow_id=1,
                        include_dependencies=True
                    )

                    buffer = BytesIO(result)
                    with zipfile.ZipFile(buffer, 'r') as zf:
                        names = zf.namelist()
                        # Script dependiente debe estar incluido
                        assert f"scripts/{mock_script.name}.py" in names
                        assert f"metadata/scripts/{mock_script.name}.json" in names


@pytest.mark.asyncio
async def test_export_workflow_includes_playbook_dependencies(
    export_service, mock_flow, mock_script, mock_playbook, mock_source_info
):
    """Playbooks referenciados en los pasos se incluyen automaticamente."""
    with patch.object(export_service, '_load_flow', new_callable=AsyncMock) as mock_load_flow:
        with patch.object(export_service, '_load_script', new_callable=AsyncMock) as mock_load_script:
            with patch.object(export_service, '_load_playbook', new_callable=AsyncMock) as mock_load_pb:
                with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
                    mock_load_flow.return_value = mock_flow
                    mock_load_script.return_value = mock_script
                    mock_load_pb.return_value = mock_playbook
                    mock_info.return_value = mock_source_info

                    result = await export_service.export_workflow(
                        flow_id=1,
                        include_dependencies=True
                    )

                    buffer = BytesIO(result)
                    with zipfile.ZipFile(buffer, 'r') as zf:
                        names = zf.namelist()
                        # Playbook dependiente debe estar incluido
                        assert f"playbooks/{mock_playbook.name}.json" in names
                        assert f"metadata/playbooks/{mock_playbook.name}.json" in names


@pytest.mark.asyncio
async def test_export_workflow_multiple_scripts(
    export_service, mock_flow_multiple_scripts,
    mock_script, mock_script_2, mock_script_3, mock_source_info
):
    """Multiples scripts referenciados se incluyen todos."""
    scripts_by_id = {1: mock_script, 2: mock_script_2, 3: mock_script_3}

    async def load_script_by_id(script_id):
        return scripts_by_id.get(script_id)

    with patch.object(export_service, '_load_flow', new_callable=AsyncMock) as mock_load_flow:
        with patch.object(export_service, '_load_script', new_callable=AsyncMock) as mock_load_script:
            with patch.object(export_service, '_load_playbook', new_callable=AsyncMock) as mock_load_pb:
                with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
                    mock_load_flow.return_value = mock_flow_multiple_scripts
                    mock_load_script.side_effect = load_script_by_id
                    mock_load_pb.return_value = None
                    mock_info.return_value = mock_source_info

                    result = await export_service.export_workflow(
                        flow_id=2,
                        include_dependencies=True
                    )

                    buffer = BytesIO(result)
                    with zipfile.ZipFile(buffer, 'r') as zf:
                        names = zf.namelist()
                        # Todos los scripts deben estar incluidos
                        assert f"scripts/{mock_script.name}.py" in names
                        assert f"scripts/{mock_script_2.name}.py" in names
                        assert f"scripts/{mock_script_3.name}.py" in names


@pytest.mark.asyncio
async def test_export_workflow_without_dependencies(
    export_service, mock_flow, mock_source_info
):
    """Exportar workflow sin incluir dependencias solo exporta la definicion."""
    with patch.object(export_service, '_load_flow', new_callable=AsyncMock) as mock_load_flow:
        with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
            mock_load_flow.return_value = mock_flow
            mock_info.return_value = mock_source_info

            result = await export_service.export_workflow(
                flow_id=1,
                include_dependencies=False
            )

            buffer = BytesIO(result)
            with zipfile.ZipFile(buffer, 'r') as zf:
                names = zf.namelist()
                # Solo workflow y manifest
                assert f"workflows/{mock_flow.name}.json" in names
                assert 'manifest.json' in names
                # Sin scripts ni playbooks
                script_files = [n for n in names if n.startswith('scripts/')]
                playbook_files = [n for n in names if n.startswith('playbooks/')]
                assert len(script_files) == 0
                assert len(playbook_files) == 0


@pytest.mark.asyncio
async def test_workflow_manifest_has_dependencies(
    export_service, mock_flow, mock_script, mock_playbook, mock_source_info
):
    """El manifest lista las dependencias del workflow."""
    with patch.object(export_service, '_load_flow', new_callable=AsyncMock) as mock_load_flow:
        with patch.object(export_service, '_load_script', new_callable=AsyncMock) as mock_load_script:
            with patch.object(export_service, '_load_playbook', new_callable=AsyncMock) as mock_load_pb:
                with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
                    mock_load_flow.return_value = mock_flow
                    mock_load_script.return_value = mock_script
                    mock_load_pb.return_value = mock_playbook
                    mock_info.return_value = mock_source_info

                    result = await export_service.export_workflow(
                        flow_id=1,
                        include_dependencies=True
                    )

                    buffer = BytesIO(result)
                    with zipfile.ZipFile(buffer, 'r') as zf:
                        manifest_content = zf.read('manifest.json').decode('utf-8')
                        manifest = json.loads(manifest_content)

                        # Debe tener seccion de dependencias
                        assert 'dependencies' in manifest
                        deps = manifest['dependencies']
                        assert 'scripts' in deps
                        assert 'playbooks' in deps


# === TESTS DE CONTENIDO DEL WORKFLOW ===

@pytest.mark.asyncio
async def test_workflow_definition_preserved(
    export_service, mock_flow, mock_script, mock_playbook, mock_source_info
):
    """La definicion del workflow se preserva correctamente."""
    with patch.object(export_service, '_load_flow', new_callable=AsyncMock) as mock_load_flow:
        with patch.object(export_service, '_load_script', new_callable=AsyncMock) as mock_load_script:
            with patch.object(export_service, '_load_playbook', new_callable=AsyncMock) as mock_load_pb:
                with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
                    mock_load_flow.return_value = mock_flow
                    mock_load_script.return_value = mock_script
                    mock_load_pb.return_value = mock_playbook
                    mock_info.return_value = mock_source_info

                    result = await export_service.export_workflow(flow_id=1)

                    buffer = BytesIO(result)
                    with zipfile.ZipFile(buffer, 'r') as zf:
                        workflow_content = zf.read(f"workflows/{mock_flow.name}.json").decode('utf-8')
                        workflow = json.loads(workflow_content)

                        # Verificar campos del workflow
                        assert workflow['name'] == mock_flow.name
                        assert workflow['description'] == mock_flow.description
                        assert workflow['version'] == mock_flow.version
                        assert len(workflow['steps']) == 3


@pytest.mark.asyncio
async def test_workflow_uses_default_name(
    export_service, mock_flow, mock_script, mock_playbook, mock_source_info
):
    """Si no se especifica nombre, usa el nombre del workflow."""
    with patch.object(export_service, '_load_flow', new_callable=AsyncMock) as mock_load_flow:
        with patch.object(export_service, '_load_script', new_callable=AsyncMock) as mock_load_script:
            with patch.object(export_service, '_load_playbook', new_callable=AsyncMock) as mock_load_pb:
                with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
                    mock_load_flow.return_value = mock_flow
                    mock_load_script.return_value = mock_script
                    mock_load_pb.return_value = mock_playbook
                    mock_info.return_value = mock_source_info

                    result = await export_service.export_workflow(flow_id=1)

                    buffer = BytesIO(result)
                    with zipfile.ZipFile(buffer, 'r') as zf:
                        manifest_content = zf.read('manifest.json').decode('utf-8')
                        manifest = json.loads(manifest_content)
                        # Nombre del paquete debe ser el nombre del workflow
                        assert manifest['name'] == mock_flow.name


@pytest.mark.asyncio
async def test_workflow_no_deps_exports_correctly(
    export_service, mock_flow_no_deps, mock_source_info
):
    """Workflow sin scripts/playbooks se exporta correctamente."""
    with patch.object(export_service, '_load_flow', new_callable=AsyncMock) as mock_load_flow:
        with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
            mock_load_flow.return_value = mock_flow_no_deps
            mock_info.return_value = mock_source_info

            result = await export_service.export_workflow(
                flow_id=3,
                include_dependencies=True
            )

            buffer = BytesIO(result)
            with zipfile.ZipFile(buffer, 'r') as zf:
                names = zf.namelist()
                # Debe tener workflow y manifest
                assert f"workflows/{mock_flow_no_deps.name}.json" in names
                assert 'manifest.json' in names


# === TESTS DE OUTPUT ===

@pytest.mark.asyncio
async def test_export_workflow_to_file(
    export_service, mock_flow, mock_script, mock_playbook, mock_source_info, tmp_path
):
    """Exportar workflow a archivo funciona correctamente."""
    output_file = tmp_path / "workflow_package.automatia"

    with patch.object(export_service, '_load_flow', new_callable=AsyncMock) as mock_load_flow:
        with patch.object(export_service, '_load_script', new_callable=AsyncMock) as mock_load_script:
            with patch.object(export_service, '_load_playbook', new_callable=AsyncMock) as mock_load_pb:
                with patch.object(export_service, '_get_source_info', new_callable=AsyncMock) as mock_info:
                    mock_load_flow.return_value = mock_flow
                    mock_load_script.return_value = mock_script
                    mock_load_pb.return_value = mock_playbook
                    mock_info.return_value = mock_source_info

                    result = await export_service.export_workflow(
                        flow_id=1,
                        output_path=str(output_file)
                    )

                    assert result == str(output_file)
                    assert output_file.exists()

                    with zipfile.ZipFile(output_file, 'r') as zf:
                        assert 'manifest.json' in zf.namelist()

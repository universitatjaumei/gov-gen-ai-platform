"""
Tests TDD para el AssetFinishingService.
Prompt #2: Servicio de "Sellado Atomico" (Capa Client)

El AssetFinishingService coordina la "promocion" de un recurso desde un estado
de "borrador" a un "atomo completo" de la biblioteca, asignandole:
- UIContract: contrato de datos inferido del codigo fuente
- README.md: documentacion tecnica generada automaticamente
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path


@pytest.mark.asyncio
async def test_seal_resource_updates_db_and_docs():
    """
    Test principal: verificar que seal_resource actualiza el contrato
    y genera la documentacion.
    """
    # Import dentro del test para evitar problemas de importacion circular
    from client_app.app.services.asset_finishing_service import AssetFinishingService
    from client_app.app.database.models import ScriptLibrary

    # 1. Setup: Crear un mock de un script en DB (estado inicial vacio)
    mock_script = MagicMock(spec=ScriptLibrary)
    mock_script.id = 123
    mock_script.name = "Robot de Prueba"
    mock_script.description = "Un script de prueba"
    mock_script.source_module = "custom"
    mock_script.script_path = "scripts/test_script.py"
    mock_script.ui_contract = {}
    mock_script.doc_path = None
    mock_script.status = "draft"
    mock_script.code = "cliente = '{{nombre}}'"  # Codigo con variable

    # Mocks de dependencias
    mock_db_session = MagicMock()
    mock_db_session.get.return_value = mock_script

    service = AssetFinishingService(session=mock_db_session)

    # 2. Ejecucion del sellado
    with patch('client_app.app.services.asset_finishing_service.doc_generator') as mock_doc_gen:
        mock_doc_gen.save_readme.return_value = Path("/data/storage/docs/123.md")

        updated_script = await service.seal_resource(script_id=123)

        # 3. Validaciones
        # Se infirió el contrato?
        assert updated_script.ui_contract is not None
        assert 'inputs' in updated_script.ui_contract
        assert len(updated_script.ui_contract['inputs']) == 1
        assert updated_script.ui_contract['inputs'][0]['name'] == "nombre"

        # Se llamo a la generacion de doc?
        mock_doc_gen.save_readme.assert_called_once()

        # Se actualizo doc_path?
        assert updated_script.doc_path is not None

        # Se guardo en DB?
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()


@pytest.mark.asyncio
async def test_seal_resource_with_empty_code():
    """
    Test de robustez: codigo vacio genera contrato vacio sin fallar.
    """
    from client_app.app.services.asset_finishing_service import AssetFinishingService
    from client_app.app.database.models import ScriptLibrary

    mock_script = MagicMock(spec=ScriptLibrary)
    mock_script.id = 456
    mock_script.name = "Script Vacio"
    mock_script.description = "Sin variables"
    mock_script.source_module = "custom"
    mock_script.script_path = "scripts/empty.py"
    mock_script.ui_contract = {}
    mock_script.doc_path = None
    mock_script.status = "draft"
    mock_script.code = "print('hola')"  # Sin variables {{}}

    mock_db_session = MagicMock()
    mock_db_session.get.return_value = mock_script

    service = AssetFinishingService(session=mock_db_session)

    with patch('client_app.app.services.asset_finishing_service.doc_generator') as mock_doc_gen:
        mock_doc_gen.save_readme.return_value = Path("/data/storage/docs/456.md")

        updated_script = await service.seal_resource(script_id=456)

        # Contrato vacio pero valido
        assert updated_script.ui_contract is not None
        assert 'inputs' in updated_script.ui_contract
        assert len(updated_script.ui_contract['inputs']) == 0


@pytest.mark.asyncio
async def test_seal_resource_idempotent():
    """
    Test de idempotencia: sellar dos veces actualiza el contrato existente.
    """
    from client_app.app.services.asset_finishing_service import AssetFinishingService
    from client_app.app.database.models import ScriptLibrary

    mock_script = MagicMock(spec=ScriptLibrary)
    mock_script.id = 789
    mock_script.name = "Script con Contrato"
    mock_script.description = "Ya tiene contrato"
    mock_script.source_module = "custom"
    mock_script.script_path = "scripts/existing.py"
    # Ya tiene un contrato anterior
    mock_script.ui_contract = {
        'inputs': [{'name': 'old_var', 'type': 'str'}]
    }
    mock_script.doc_path = "/old/path.md"
    mock_script.status = "validated"
    mock_script.code = "x = '{{new_var}}'"  # Nueva variable

    mock_db_session = MagicMock()
    mock_db_session.get.return_value = mock_script

    service = AssetFinishingService(session=mock_db_session)

    with patch('client_app.app.services.asset_finishing_service.doc_generator') as mock_doc_gen:
        mock_doc_gen.save_readme.return_value = Path("/data/storage/docs/789.md")

        updated_script = await service.seal_resource(script_id=789)

        # El contrato debe actualizarse con las nuevas variables
        assert 'inputs' in updated_script.ui_contract
        input_names = [i['name'] for i in updated_script.ui_contract['inputs']]
        assert 'new_var' in input_names
        # old_var ya no deberia estar (se reemplaza)
        assert 'old_var' not in input_names


@pytest.mark.asyncio
async def test_seal_resource_script_not_found():
    """
    Test de error: script no encontrado lanza excepcion.
    """
    from client_app.app.services.asset_finishing_service import AssetFinishingService

    mock_db_session = MagicMock()
    mock_db_session.get.return_value = None  # No existe

    service = AssetFinishingService(session=mock_db_session)

    with pytest.raises(ValueError, match="Script.*no encontrado"):
        await service.seal_resource(script_id=999)


@pytest.mark.asyncio
async def test_seal_resource_reads_code_from_file():
    """
    Test: si el script no tiene codigo en memoria, lo lee del archivo.
    """
    from client_app.app.services.asset_finishing_service import AssetFinishingService
    from client_app.app.database.models import ScriptLibrary

    mock_script = MagicMock(spec=ScriptLibrary)
    mock_script.id = 101
    mock_script.name = "Script desde Archivo"
    mock_script.description = "Codigo en disco"
    mock_script.source_module = "custom"
    mock_script.script_path = "scripts/from_file.py"
    mock_script.ui_contract = {}
    mock_script.doc_path = None
    mock_script.status = "draft"
    mock_script.code = None  # No tiene codigo en memoria

    mock_db_session = MagicMock()
    mock_db_session.get.return_value = mock_script

    service = AssetFinishingService(session=mock_db_session)

    # Mock de lectura de archivo
    file_content = "data = '{{campo_archivo}}'"

    with patch('client_app.app.services.asset_finishing_service.doc_generator') as mock_doc_gen, \
         patch('pathlib.Path.read_text', return_value=file_content), \
         patch('pathlib.Path.exists', return_value=True):

        mock_doc_gen.save_readme.return_value = Path("/data/storage/docs/101.md")

        updated_script = await service.seal_resource(script_id=101)

        # Debe haber inferido del archivo
        assert 'inputs' in updated_script.ui_contract
        input_names = [i['name'] for i in updated_script.ui_contract['inputs']]
        assert 'campo_archivo' in input_names


@pytest.mark.asyncio
async def test_seal_resource_with_precalculated_contract():
    """
    Test: acepta contrato pre-calculado (para Factory/Extraction).
    """
    from client_app.app.services.asset_finishing_service import AssetFinishingService
    from client_app.app.database.models import ScriptLibrary

    mock_script = MagicMock(spec=ScriptLibrary)
    mock_script.id = 202
    mock_script.name = "Extractor Factory"
    mock_script.description = "Generado por Factory"
    mock_script.source_module = "extraction"
    mock_script.script_path = "scripts/factory.py"
    mock_script.ui_contract = {}
    mock_script.doc_path = None
    mock_script.status = "draft"
    mock_script.code = "# Script generado sin {{variables}}"

    mock_db_session = MagicMock()
    mock_db_session.get.return_value = mock_script

    service = AssetFinishingService(session=mock_db_session)

    # Contrato pre-calculado (de Factory)
    precalculated_contract = {
        'inputs': [
            {'name': 'input_document', 'type': 'file', 'label': 'Documento PDF'}
        ],
        'outputs': [
            {'name': 'fecha_factura', 'type': 'date'},
            {'name': 'importe_total', 'type': 'float'}
        ]
    }

    with patch('client_app.app.services.asset_finishing_service.doc_generator') as mock_doc_gen:
        mock_doc_gen.save_readme.return_value = Path("/data/storage/docs/202.md")

        updated_script = await service.seal_resource(
            script_id=202,
            precalculated_contract=precalculated_contract
        )

        # Debe usar el contrato pre-calculado
        assert updated_script.ui_contract == precalculated_contract

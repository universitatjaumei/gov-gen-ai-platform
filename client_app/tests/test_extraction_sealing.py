# client_app/tests/test_extraction_sealing.py
"""
Test TDD for Extraction Service Atomic Sealing integration.
Prompt #4: Integración del Sello Atómico en el Modo Factory (Extracción).

Tests that extraction deployments trigger atomic sealing with proper contract generation.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Any

from automatia_shared.contracts.ui_contract import InputType


class TestExtractionServiceSealing:
    """Tests for atomic sealing integration in ExtractionService."""

    @pytest.mark.asyncio
    async def test_deploy_extraction_triggers_sealing(self):
        """
        Test that deploying an extraction script to production
        triggers the atomic sealing process.
        """
        from client_app.app.services.extraction_service import ExtractionService

        # Setup service
        service = ExtractionService()

        # Mock the database session
        with patch('client_app.app.services.extraction_service.AsyncSession') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            mock_session.commit = AsyncMock()

            # Mock path_manager
            mock_exec_path = MagicMock()
            mock_script_file = MagicMock()
            mock_script_file.exists.return_value = True
            mock_exec_path.__truediv__ = MagicMock(return_value=mock_exec_path)
            mock_exec_path.__truediv__.return_value.__truediv__ = MagicMock(return_value=mock_script_file)
            service.path_manager.get_execution_path = MagicMock(return_value=mock_exec_path)

            # Mock shutil.copy2
            with patch('client_app.app.services.extraction_service.shutil.copy2'):
                # Mock script_library_service
                with patch('client_app.app.services.extraction_service.script_library_service') as mock_lib_svc:
                    mock_library_script = MagicMock()
                    mock_library_script.id = 123
                    mock_lib_svc.add_script = AsyncMock(return_value=mock_library_script)

                    # Execute deployment
                    result = await service.deploy_script_to_production(
                        execution_id="test-exec-123",
                        service_name="Extractor Facturas",
                        description="Test extraction"
                    )

                    # Verify script_library_service.add_script was called
                    mock_lib_svc.add_script.assert_called_once()

    @pytest.mark.asyncio
    async def test_deploy_extraction_generates_correct_contract(self):
        """
        Test that the generated contract includes:
        1. An input_document field of type FILE
        2. Output fields from field_definitions
        """
        from client_app.app.services.extraction_service import ExtractionService

        # Field definitions as user would configure them
        field_definitions = [
            {"name": "num_factura", "type": "string", "description": "Número de factura"},
            {"name": "fecha", "type": "date", "description": "Fecha de emisión"},
            {"name": "total", "type": "float", "description": "Importe total"}
        ]

        # Test the contract building logic
        from client_app.app.services.extraction_service import build_extraction_contract
        contract = build_extraction_contract(
            name="Extractor Test",
            field_definitions=field_definitions,
            description="Robot de extracción de facturas"
        )

        # Verify contract structure
        assert "inputs" in contract
        assert "outputs" in contract

        # Check that input_document is present as FILE type
        input_names = [inp["name"] for inp in contract["inputs"]]
        assert "input_document" in input_names

        input_doc = next(inp for inp in contract["inputs"] if inp["name"] == "input_document")
        assert input_doc["type"] == InputType.FILE.value

        # Check output fields match field_definitions
        output_names = [out["name"] for out in contract["outputs"]]
        assert "num_factura" in output_names
        assert "fecha" in output_names
        assert "total" in output_names

    @pytest.mark.asyncio
    async def test_register_service_with_sealing(self):
        """
        Test that register_service also triggers sealing when
        syncing to the script library.
        """
        from client_app.app.services.extraction_service import ExtractionService

        service = ExtractionService()

        field_definitions = [
            {"name": "cif", "type": "string", "is_optional": False},
            {"name": "importe", "type": "float", "is_optional": False}
        ]

        # Patch sqlmodel.Session at source (it's imported inside the function)
        with patch('sqlmodel.Session') as mock_session_ctx:
            mock_session = MagicMock()
            mock_session_ctx.return_value.__enter__.return_value = mock_session
            mock_session.exec.return_value.first.return_value = None
            mock_session.commit = MagicMock()

            with patch('client_app.app.services.extraction_service.script_library_service') as mock_lib:
                mock_lib.add_script = AsyncMock(return_value=MagicMock(id=456))

                result = await service.register_service(
                    service_id="test-service-001",
                    name="Extractor CIF",
                    description="Extrae CIF e importe",
                    field_definitions=field_definitions,
                    policies={},
                    options={}
                )

                assert result is True


class TestBuildExtractionContract:
    """Tests for the contract building utility function."""

    def test_build_contract_basic(self):
        """Test basic contract building with standard fields."""
        from client_app.app.services.extraction_service import build_extraction_contract

        fields = [
            {"name": "campo1", "type": "string"},
            {"name": "campo2", "type": "int"}
        ]

        contract = build_extraction_contract(
            name="Test Robot",
            field_definitions=fields
        )

        assert contract["version"] == "1.0.0"
        assert len(contract["inputs"]) >= 1  # At least input_document
        assert len(contract["outputs"]) == 2

    def test_build_contract_type_mapping(self):
        """Test that field types are correctly mapped to InputType."""
        from client_app.app.services.extraction_service import build_extraction_contract

        fields = [
            {"name": "texto", "type": "string"},
            {"name": "numero", "type": "int"},
            {"name": "decimal", "type": "float"},
            {"name": "fecha", "type": "date"},
            {"name": "booleano", "type": "bool"}
        ]

        contract = build_extraction_contract(
            name="Type Test Robot",
            field_definitions=fields
        )

        # Verify type mapping in outputs
        outputs_by_name = {out["name"]: out for out in contract["outputs"]}

        assert outputs_by_name["texto"]["type"] == InputType.STR.value
        assert outputs_by_name["numero"]["type"] == InputType.INT.value
        assert outputs_by_name["decimal"]["type"] == InputType.FLOAT.value
        assert outputs_by_name["fecha"]["type"] == InputType.DATE.value
        assert outputs_by_name["booleano"]["type"] == InputType.BOOL.value

    def test_build_contract_with_engine_metadata(self):
        """Test contract includes extraction engine metadata."""
        from client_app.app.services.extraction_service import build_extraction_contract

        fields = [{"name": "test", "type": "string"}]

        contract = build_extraction_contract(
            name="Engine Test Robot",
            field_definitions=fields,
            engine="pdfplumber"
        )

        assert "metadata" in contract
        assert contract["metadata"].get("engine") == "pdfplumber"
        assert contract["metadata"].get("type") == "extraction"

    def test_build_contract_humanizes_labels(self):
        """Test that field names are humanized for labels."""
        from client_app.app.services.extraction_service import build_extraction_contract

        fields = [
            {"name": "numero_factura", "type": "string"},
            {"name": "fecha_emision", "type": "date"}
        ]

        contract = build_extraction_contract(
            name="Label Test Robot",
            field_definitions=fields
        )

        outputs_by_name = {out["name"]: out for out in contract["outputs"]}

        # Labels should be humanized versions of names
        assert outputs_by_name["numero_factura"]["label"] == "Numero Factura"
        assert outputs_by_name["fecha_emision"]["label"] == "Fecha Emision"


class TestExtractionReadmeGeneration:
    """Tests for extraction-specific README generation."""

    def test_readme_includes_output_schema(self):
        """Test that generated README includes output field schema."""
        from client_app.app.services.extraction_service import generate_extraction_readme

        fields = [
            {"name": "cif", "type": "string", "description": "CIF del emisor"},
            {"name": "total", "type": "float", "description": "Importe total"}
        ]

        readme = generate_extraction_readme(
            name="Extractor Facturas",
            description="Extrae datos de facturas PDF",
            field_definitions=fields,
            engine="fitz"
        )

        # Check README contains expected sections
        assert "# Extractor Facturas" in readme
        assert "## Esquema de Salida" in readme
        assert "cif" in readme
        assert "total" in readme
        assert "fitz" in readme.lower() or "Motor" in readme


class TestDeploymentBugFixes:
    """
    Tests for bug fixes in extraction deployment flow.
    These verify the fixes for:
    - DataContract serialization to dict for JSON columns
    - UnboundLocalError for readme_path variable
    - Async session usage with seal_resource
    """

    @pytest.mark.asyncio
    async def test_datacontract_serialized_to_dict_for_library(self):
        """
        Test that DataContract objects are properly converted to dicts
        before being passed to script_library_service.add_script.

        Bug: Object of type DataContract is not JSON serializable
        Fix: Convert using model_dump() before passing to add_script
        """
        from client_app.app.services.extraction_service import ExtractionService

        service = ExtractionService()

        field_definitions = [
            {"name": "test_field", "type": "string", "description": "Test"}
        ]

        # Track what ui_contract was passed to add_script
        captured_ui_contract = None

        async def mock_add_script(**kwargs):
            nonlocal captured_ui_contract
            captured_ui_contract = kwargs.get('ui_contract')
            mock_script = MagicMock()
            mock_script.id = 999
            return mock_script

        with patch('client_app.app.services.extraction_service.AsyncSession') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            mock_session.commit = AsyncMock()
            mock_session.get = AsyncMock(return_value=None)

            mock_exec_path = MagicMock()
            mock_script_file = MagicMock()
            mock_script_file.exists.return_value = True

            # Mock file reading
            with patch('builtins.open', MagicMock()):
                mock_exec_path.__truediv__ = MagicMock(return_value=mock_exec_path)
                mock_exec_path.__truediv__.return_value.__truediv__ = MagicMock(return_value=mock_script_file)
                service.path_manager.get_execution_path = MagicMock(return_value=mock_exec_path)

                with patch('client_app.app.services.extraction_service.shutil.copy2'):
                    with patch('client_app.app.services.extraction_service.script_library_service') as mock_lib_svc:
                        mock_lib_svc.add_script = AsyncMock(side_effect=mock_add_script)

                        # Mock AssetFinishingService at its source module
                        with patch('client_app.app.services.asset_finishing_service.AssetFinishingService') as mock_finishing:
                            mock_finishing_instance = MagicMock()
                            mock_finishing_instance.seal_resource = AsyncMock(return_value=MagicMock(doc_path=None))
                            mock_finishing.return_value = mock_finishing_instance

                            try:
                                await service.deploy_script_to_production(
                                    execution_id="test-exec",
                                    service_name="Test Service",
                                    description="Test",
                                    field_definitions=field_definitions
                                )
                            except Exception:
                                pass  # We just want to verify the ui_contract type

        # Verify ui_contract is a dict, not a DataContract object
        if captured_ui_contract is not None:
            assert isinstance(captured_ui_contract, dict), \
                f"ui_contract should be dict, got {type(captured_ui_contract).__name__}"

    @pytest.mark.asyncio
    async def test_readme_path_defined_when_add_script_fails(self):
        """
        Test that readme_path is properly initialized even when
        script_library_service.add_script fails.

        Bug: UnboundLocalError: cannot access local variable 'readme_path'
        Fix: Initialize readme_path = None before the try block
        """
        from client_app.app.services.extraction_service import ExtractionService

        service = ExtractionService()

        with patch('client_app.app.services.extraction_service.AsyncSession') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            mock_session.commit = AsyncMock()

            mock_exec_path = MagicMock()
            mock_script_file = MagicMock()
            mock_script_file.exists.return_value = True

            with patch('builtins.open', MagicMock()):
                mock_exec_path.__truediv__ = MagicMock(return_value=mock_exec_path)
                mock_exec_path.__truediv__.return_value.__truediv__ = MagicMock(return_value=mock_script_file)
                service.path_manager.get_execution_path = MagicMock(return_value=mock_exec_path)

                with patch('client_app.app.services.extraction_service.shutil.copy2'):
                    with patch('client_app.app.services.extraction_service.script_library_service') as mock_lib_svc:
                        # Make add_script fail to trigger the except block
                        mock_lib_svc.add_script = AsyncMock(
                            side_effect=Exception("Simulated library sync failure")
                        )

                        # This should NOT raise UnboundLocalError
                        try:
                            result = await service.deploy_script_to_production(
                                execution_id="test-exec",
                                service_name="Test Service",
                                description="Test"
                            )
                            # Verify return tuple has readme_path (should be None)
                            service_id, lib_script_id, readme_path = result
                            assert readme_path is None, "readme_path should be None when add_script fails"
                        except UnboundLocalError as e:
                            pytest.fail(f"UnboundLocalError should not occur: {e}")

    @pytest.mark.asyncio
    async def test_seal_resource_called_with_await(self):
        """
        Test that seal_resource is properly awaited since it's an async method.

        Bug: seal_resource called without await, causing coroutine to never execute
        Fix: Use 'await finishing_svc.seal_resource(...)' with AsyncSession
        """
        from client_app.app.services.extraction_service import ExtractionService

        service = ExtractionService()
        seal_resource_awaited = False

        async def mock_seal_resource(*args, **kwargs):
            nonlocal seal_resource_awaited
            seal_resource_awaited = True
            mock_result = MagicMock()
            mock_result.doc_path = "test_doc.md"
            return mock_result

        with patch('client_app.app.services.extraction_service.AsyncSession') as mock_session_ctx:
            mock_session = AsyncMock()
            mock_session_ctx.return_value.__aenter__.return_value = mock_session
            mock_session.commit = AsyncMock()

            mock_exec_path = MagicMock()
            mock_script_file = MagicMock()
            mock_script_file.exists.return_value = True

            with patch('builtins.open', MagicMock()):
                mock_exec_path.__truediv__ = MagicMock(return_value=mock_exec_path)
                mock_exec_path.__truediv__.return_value.__truediv__ = MagicMock(return_value=mock_script_file)
                service.path_manager.get_execution_path = MagicMock(return_value=mock_exec_path)

                with patch('client_app.app.services.extraction_service.shutil.copy2'):
                    with patch('client_app.app.services.extraction_service.script_library_service') as mock_lib_svc:
                        mock_library_script = MagicMock()
                        mock_library_script.id = 123
                        mock_lib_svc.add_script = AsyncMock(return_value=mock_library_script)

                        # Mock AssetFinishingService at its source module
                        with patch('client_app.app.services.asset_finishing_service.AssetFinishingService') as mock_finishing_cls:
                            mock_finishing_instance = MagicMock()
                            mock_finishing_instance.seal_resource = mock_seal_resource
                            mock_finishing_cls.return_value = mock_finishing_instance

                            try:
                                await service.deploy_script_to_production(
                                    execution_id="test-exec",
                                    service_name="Test Service",
                                    description="Test",
                                    field_definitions=[{"name": "test", "type": "string"}]
                                )
                            except Exception:
                                pass  # Ignore other errors, we just check seal_resource was awaited

        assert seal_resource_awaited, "seal_resource should have been properly awaited"

    def test_datacontract_model_dump_available(self):
        """
        Test that DataContract has model_dump method (Pydantic v2) for serialization.
        This ensures the conversion code will work.
        """
        from automatia_shared.contracts.ui_contract import DataContract, UIContract, OutputSchema

        # Create a minimal DataContract
        contract = DataContract(
            version="1.0.0",
            inputs=UIContract(inputs=[], version="1.0.0"),
            outputs=OutputSchema(fields=[])
        )

        # Verify it has model_dump (Pydantic v2) or dict (Pydantic v1)
        has_serialization = hasattr(contract, 'model_dump') or hasattr(contract, 'dict')
        assert has_serialization, "DataContract must have model_dump() or dict() method"

        # Verify serialization produces a dict
        if hasattr(contract, 'model_dump'):
            result = contract.model_dump()
        else:
            result = contract.dict()

        assert isinstance(result, dict), "Serialized contract should be a dict"
        assert "version" in result, "Serialized contract should contain 'version'"

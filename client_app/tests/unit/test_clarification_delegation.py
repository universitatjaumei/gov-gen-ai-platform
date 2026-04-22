
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from client_app.app.services.clarification_service import ClarificationService

@pytest.fixture
def clarification_service():
    """Returns a fresh ClarificationService instance for each test."""
    return ClarificationService()

@pytest.mark.asyncio
async def test_delegate_custom_script(clarification_service):
    """Verify delegation to ScriptGeneratorService for custom_script."""
    enriched_input = {
        "user_prompt": "Create a python script",
        "output_type": "file",
        "_clarifications": {"q1": "answer1"}
    }
    context = {"examples": [], "files": ["example.py"]}
    
    # Mock ScriptGeneratorService
    mock_script_gen = AsyncMock()
    mock_script_gen.generate_script.return_value = {"success": True, "code": "print('hello')"}
    
    # Inject mock
    with patch.object(clarification_service, "script_generator", mock_script_gen, create=True):
        # We need to manually set the attribute because the method uses getattr(self, "script_generator", None)
        # However, patch.object on instance attribute might be tricky if it doesn't exist.
        # Let's set it directly.
        clarification_service.script_generator = mock_script_gen
        
        result = await clarification_service._delegate_generation("custom_script", enriched_input, context)
        
        assert result["success"] is True
        assert result["code"] == "print('hello')"
        
        mock_script_gen.generate_script.assert_called_once()
        call_kwargs = mock_script_gen.generate_script.call_args.kwargs
        assert call_kwargs["user_prompt"] == "Create a python script"
        assert call_kwargs["output_type"] == "file"
        assert call_kwargs["clarifications"] == {"q1": "answer1"}
        # Check if context was passed (it might be summarized string)
        assert "context" in call_kwargs

@pytest.mark.asyncio
async def test_delegate_extraction(clarification_service):
    """Verify delegation to ExtractionService for extraction."""
    enriched_input = {
        "user_prompt": "Extract invoices",
        "files": ["invoice.pdf"],
        "_clarifications": {"q1": "yes"}
    }
    context = {}
    
    # Mock ExtractionService
    mock_extract_svc = AsyncMock()
    mock_extract_svc.process_files_generic.return_value = {"status": "ok", "data": {}}
    
    # Inject mock
    clarification_service.extraction_service = mock_extract_svc
    
    result = await clarification_service._delegate_generation("extraction", enriched_input, context)
    
    assert result["status"] == "ok"
    
    mock_extract_svc.process_files_generic.assert_called_once()
    call_kwargs = mock_extract_svc.process_files_generic.call_args.kwargs
    assert call_kwargs["file_paths"] == ["invoice.pdf"]
    assert call_kwargs["recognize_all"] is True

@pytest.mark.asyncio
async def test_delegate_etl(clarification_service):
    """Verify delegation to ETLScriptFactory logic."""
    enriched_input = {
        "user_prompt": "Transform CSV",
        "source_file": "data.csv",
        "_clarifications": {"delimiter": ";"}
    }
    context = {}
    
    # Correctly patch the classes where they are DEFINED, since clarification_service 
    # uses local imports and doesn't expose them at module level.
    
    with patch("client_app.app.modules.factory.etl_factory.ETLScriptFactory") as MockFactory, \
         patch("client_app.app.services.etl_service.ETLService") as MockETLService, \
         patch("sqlmodel.ext.asyncio.session.AsyncSession") as MockSession, \
         patch("client_app.app.database.db.client_engine") as MockEngine:
         
        # Setup Mocks
        mock_factory_instance = MockFactory.return_value
        mock_factory_instance.generate_transformation_script = AsyncMock(return_value={"script": "import pandas..."})
        
        mock_etl_service_instance = MockETLService.return_value
        mock_etl_service_instance._detect_format.return_value = "csv"
        
        # Create a specific mock for the dataframe
        mock_df = MagicMock()
        mock_df.head.return_value = "dataframe_sample"
        
        mock_etl_service_instance._read_source_file = AsyncMock(return_value=mock_df)
        mock_etl_service_instance._get_brain_client = AsyncMock(return_value=("mock_client", "mock_key"))
        
        # Async session context manager
        mock_session_instance = MockSession.return_value
        mock_session_instance.__aenter__.return_value = mock_session_instance
        
        # We need to ensure that the LOCAL imports in delegation service pick up these mocks.
        # Since 'from ... import ...' inside a function usually loads the module, 
        # patching sys.modules or the source module should work.
        # However, `patch` wraps the target. If `_delegate_etl` does 
        # `from client_app.app.modules.factory.etl_factory import ETLScriptFactory`
        # then patching `client_app.app.modules.factory.etl_factory.ETLScriptFactory` works 
        # IF the import happens AFTER the patch is active (which it does, inside the function).
        
        result = await clarification_service._delegate_generation("etl", enriched_input, context)
        
        assert result["script"] == "import pandas..."
        
        # Verify calls
        mock_etl_service_instance._read_source_file.assert_called_once()
        mock_factory_instance.generate_transformation_script.assert_called_once()
        call_kwargs = mock_factory_instance.generate_transformation_script.call_args.kwargs
        assert "dataframe_sample" in str(call_kwargs["source_sample"]) # mocking head return string for simplicity check
        assert "delimiter: ;" in call_kwargs["user_instructions"]

@pytest.mark.asyncio
async def test_delegate_rpa_with_logs(clarification_service):
    """Verify RPA delegation calls analyze_recording when logs are present."""
    enriched_input = {
        "recording_logs": [{"type": "click"}],
        "context": {"url": "https://example.com"}
    }
    
    # Mock state.rpa
    with patch("client_app.app.core.state.app_state") as mock_state:
        # We patch app_state because 'state' is an alias to it in the module
        # But wait, the service imports 'state' from client_app.app.core.state.
        # So we should patch where it is IMPORTED or the module itself.
        
        mock_state.rpa.analyze_recording = AsyncMock(return_value=[{"action": "click", "selector": "#btn"}])
        
        # We need to ensure the import inside the method picks up this mock.
        # Patching 'client_app.app.core.state.state' is key.
        with patch("client_app.app.core.state.state", mock_state):
             result = await clarification_service._delegate_generation("rpa", enriched_input, {})
    
             assert result["status"] == "success"
             assert result["playbook"][0]["selector"] == "#btn"
             assert result["module_type"] == "rpa"
             
             mock_state.rpa.analyze_recording.assert_called_once()
             args = mock_state.rpa.analyze_recording.call_args.kwargs
             assert args["recording_logs"] == [{"type": "click"}]

@pytest.mark.asyncio
async def test_delegate_rpa_missing_logs(clarification_service):
    """Verify RPA delegation returns pending_input when logs are missing."""
    enriched_input = {
        "user_prompt": "Do automation",
        "_clarifications": {}
    }
    
    # No need to mock state logic deep since it should return early
    result = await clarification_service._delegate_generation("rpa", enriched_input, {})
    
    assert result["status"] == "pending_input"
    assert result["required_input"] == "recording_logs"
    assert "grabación" in result["message"]

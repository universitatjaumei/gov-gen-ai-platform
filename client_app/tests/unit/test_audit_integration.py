import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from client_app.app.services.extraction_service import ExtractionService
from client_app.app.modules.runtime.workflow_engine import execute_etl_transform
from automatia_shared.dtos import TaskSpec

@pytest.fixture
def mock_brain():
    brain = AsyncMock()
    # Mock some basic brain responses
    brain.extract_data.return_value = ({"field1": "val1"}, {"detected": 1})
    return brain

@pytest.fixture
def mock_audit_service():
    """Mocks enterprise_audit_service methods on the real singleton instance."""
    from client_app.app.services.enterprise_audit_service import enterprise_audit_service
    
    with patch.object(enterprise_audit_service, 'log_event', new_callable=AsyncMock) as mock_log, \
         patch.object(enterprise_audit_service, 'log_pii_operation', new_callable=AsyncMock) as mock_pii:
        
        # We return a dummy object that has references to both mocks for convenience in assertions
        mock_container = MagicMock()
        mock_container.log_event = mock_log
        mock_container.log_pii_operation = mock_pii
        yield mock_container

@pytest.mark.asyncio
async def test_extraction_service_audit_integration(mock_brain, mock_audit_service):
    """Verifica que ExtractionService dispare eventos de auditoría."""
    service = ExtractionService(brain=mock_brain, logger=MagicMock())
    
    # Mock AnonymizationContext to avoid spaCy/NER issues in tests
    mock_anon = MagicMock()
    mock_anon.anonymize.side_effect = lambda x: x
    mock_anon.deanonymize.side_effect = lambda x: x
    mock_anon.get_stats.return_value = {"detected": 0}
    mock_anon.fake_to_real = {}

    # Minimal mock for dependencies
    async def mock_io_bound(f, *args, **kwargs):
        res = f(*args, **kwargs)
        if asyncio.iscoroutine(res):
            return await res
        return res

    with patch('client_app.app.services.extraction_service.extraer_texto_dual', AsyncMock(return_value=("text1", "text2", False))), \
         patch('client_app.app.services.extraction_service.AnonymizationContext', return_value=mock_anon), \
         patch('client_app.app.services.extraction_service.run.io_bound', side_effect=mock_io_bound):
            
        result = await service.process_files_generic(
            file_paths=["test.pdf"],
            target_fields=["field1"]
        )
        
        # log_event should be called at least twice 
        # 1. process_files_generic -> "extraction"
        # 2. extract_with_ai -> "anonymization"
        
        actions = [call.kwargs.get('action_type') for call in mock_audit_service.log_event.call_args_list]
        
        assert "extraction" in actions
        assert "anonymization" in actions
        
        # log_pii_operation should be called once inside extract_with_ai
        assert mock_audit_service.log_pii_operation.called

@pytest.mark.asyncio
async def test_workflow_engine_audit_integration(mock_audit_service):
    """Verifica que los ejecutores de workflow disparen eventos de auditoría."""
    task = TaskSpec(
        name="Test ETL",
        type="etl_transform",
        config={
            "script": "def transform(df): return df",
            "target_format": "csv"
        }
    )
    context = {
        "source_file": "test.csv",
        "previous_output": None
    }
    
    # Mock pandas to avoid real IO
    with patch('pandas.read_csv', return_value=MagicMock()):
        await execute_etl_transform(task, context)
        
        assert mock_audit_service.log_event.called
        # Check that it was called with the right action type
        found = False
        for call in mock_audit_service.log_event.call_args_list:
            if call.kwargs.get('action_type') == "etl_transform":
                found = True
                break
        assert found, f"Action type 'etl_transform' not found in calls: {mock_audit_service.log_event.call_args_list}"

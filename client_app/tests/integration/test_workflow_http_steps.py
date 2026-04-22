import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from client_app.app.modules.runtime.workflow_engine import WorkflowEngine, StepRegistry
from automatia_shared.dtos import TaskSpec
from automatia_shared.enums import StepType

@pytest.mark.asyncio
async def test_api_fetch_step():
    """Test API Fetch step implementation"""
    # Create engine with mock session
    mock_session = AsyncMock()
    engine = WorkflowEngine(session=mock_session)
    
    # Define task
    task = TaskSpec(
        name="Fetch User",
        type=StepType.API_FETCH,
        config={
            "url": "https://api.example.com/users/1",
            "method": "GET",
            "headers": {"Authorization": "Bearer token"},
            "output_var": "user_data"
        }
    )
    
    context = {}
    
    # Mock httpx.AsyncClient
    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "name": "Test User"}
        mock_response.text = '{"id": 1, "name": "Test User"}'
        
        mock_client.request.return_value = mock_response
        
        try:
            result = await engine._execute_task(task, context)
            
            # Assertions (Success case)
            assert result == {"id": 1, "name": "Test User"}
            assert context["user_data"] == result
            
            mock_client.request.assert_awaited_once_with(
                method="GET",
                url="https://api.example.com/users/1",
                headers={"Authorization": "Bearer token"},
                json=None,
                params=None,
                timeout=30.0
            ) 
            
        except NotImplementedError:
            pytest.fail("API_FETCH step not implemented")

@pytest.mark.asyncio
async def test_webhook_step():
    """Test Webhook step implementation"""
    mock_session = AsyncMock()
    engine = WorkflowEngine(session=mock_session)
    
    task = TaskSpec(
        name="Send Webhook",
        type=StepType.WEBHOOK,
        config={
            "url": "https://webhook.site/123",
            "payload": {"event": "done"},
            "headers": {"X-Custom": "123"}
        }
    )
    
    context = {}
    
    with patch("httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.post.return_value = mock_response # Ensure 'post' returns the mock response
        
        try:
            await engine._execute_task(task, context)
            
            mock_client.post.assert_awaited_once_with(
                url="https://webhook.site/123",
                headers={"X-Custom": "123"},
                json={"event": "done"},
                timeout=10.0
            )
        except NotImplementedError:
             pytest.fail("WEBHOOK step not implemented")

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from client_app.app.services.workflow_scheduler_service import WorkflowScheduler
from types import SimpleNamespace

@pytest.fixture
def scheduler_service():
    service = WorkflowScheduler()
    # Mock the internal scheduler to avoid actual timing issues in unit tests
    service._scheduler = MagicMock(spec=AsyncIOScheduler)
    return service

@pytest.mark.asyncio
async def test_add_interval_job(scheduler_service):
    """Verify that adding an interval job calls APScheduler correctly."""
    flow_id = 1
    config = {"minutes": 5}
    
    scheduler_service.add_flow_job(flow_id, "interval", config)
    
    scheduler_service._scheduler.add_job.assert_called_once()
    args, kwargs = scheduler_service._scheduler.add_job.call_args
    assert kwargs['id'] == f"flow_{flow_id}"
    # Verify it's an IntervalTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    assert isinstance(kwargs['trigger'], IntervalTrigger)

@pytest.mark.asyncio
async def test_remove_job(scheduler_service):
    """Verify that removing a job calls APScheduler correctly."""
    flow_id = 1
    scheduler_service.remove_flow_job(flow_id)
    
    scheduler_service._scheduler.remove_job.assert_called_once_with(f"flow_{flow_id}")

@pytest.mark.asyncio
async def test_sync_with_db(scheduler_service):
    """Verify that sync_with_db loads active scheduled flows."""
    mock_flows = [
        SimpleNamespace(id=1, trigger_type="interval", trigger_config='{"minutes": 10}', is_active=True),
        SimpleNamespace(id=2, trigger_type="manual", trigger_config='{}', is_active=True)
    ]
    
    with patch("client_app.app.services.workflow_scheduler_service.AsyncSession") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        
        # Mocking FlowRegistryService
        with patch("client_app.app.services.workflow_scheduler_service.FlowRegistryService") as mock_reg_cls:
            mock_reg = AsyncMock()
            mock_reg.list_flows.return_value = mock_flows
            mock_reg_cls.return_value = mock_reg
            
            await scheduler_service.sync_with_db()
            
            # Should have added job for flow 1 but not flow 2
            assert scheduler_service._scheduler.add_job.call_count == 1

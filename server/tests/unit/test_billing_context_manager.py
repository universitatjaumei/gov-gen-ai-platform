import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from server.app.modules.brain.billing_engine import BillingEngine

@pytest.mark.asyncio
async def test_billing_engine_context_manager_commit():
    """Verify that the context manager commits and closes on success."""
    # We need to mock AsyncSession and server_engine
    with patch("server.app.modules.brain.billing_engine.AsyncSession") as mock_session_cls:
        mock_session = mock_session_cls.return_value
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        async with BillingEngine() as engine:
            assert engine._session == mock_session
            # No exception raised
            
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()
        mock_session.rollback.assert_not_called()

@pytest.mark.asyncio
async def test_billing_engine_context_manager_rollback():
    """Verify that the context manager rolls back and closes on exception."""
    with patch("server.app.modules.brain.billing_engine.AsyncSession") as mock_session_cls:
        mock_session = mock_session_cls.return_value
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        try:
            async with BillingEngine() as engine:
                raise ValueError("Simulated error")
        except ValueError:
            pass
            
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()
        mock_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_billing_engine_session_is_none_after_exit():
    """Verify that the session reference is cleared."""
    with patch("server.app.modules.brain.billing_engine.AsyncSession") as mock_session_cls:
        mock_session = mock_session_cls.return_value
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        engine = BillingEngine()
        async with engine:
            assert engine._session is not None
        
        assert engine._session is None

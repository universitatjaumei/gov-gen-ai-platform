
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from server.app.ui.partner_layout import PartnerLayout, PartnerContext

@pytest.mark.asyncio
async def test_from_session_returns_dev_id_when_no_session():
    """
    Debe devolver un ID de desarrollo si no hay sesión activa y estamos en modo dev.
    """
    # Mocks
    mock_db_session = AsyncMock()
    
    # Mocking nicegui app.storage.user
    with patch("server.app.ui.partner_layout.app") as mock_app:
        # Case 1: Empty storage (No login)
        mock_app.storage.user.get.return_value = None
        
        # We need to mock from_dev_mode to return a context, 
        # because the logic we want to implement in from_session will likely call from_dev_mode 
        # with the dev ID if no token is found.
        # However, strictly testing the BYPASS means testing that it *decides* to use the dev ID.
        
        # Let's mock PartnerContext.from_dev_mode to verified it is called with "dev-partner-0000"
        with patch.object(PartnerContext, 'from_dev_mode', new_callable=AsyncMock) as mock_from_dev:
            mock_from_dev.return_value = PartnerContext(
                partner_id="dev-partner-0000", 
                partner_name="Dev Partner", 
                role="ADMIN"
            )
            
            # Call SUT
            ctx = await PartnerContext.from_session(token="invalid_or_none", db_session=mock_db_session)
            
            # Verify
            assert ctx is not None
            assert ctx.partner_id == "dev-partner-0000"
            
            # Verify it tried to load the dev partner
            mock_from_dev.assert_called_once()
            args, _ = mock_from_dev.call_args
            assert args[0] == "dev-partner-0000"

@pytest.mark.asyncio
async def test_from_session_uses_real_id_if_present():
    """
    Si hay partner_id en storage user (simulando cookie), debe usar ese.
    """
    mock_db_session = AsyncMock()
    
    with patch("server.app.ui.partner_layout.app") as mock_app:
        # Case 2: Session exists
        mock_app.storage.user.get.return_value = "partner_123"
        
        with patch.object(PartnerContext, 'from_dev_mode', new_callable=AsyncMock) as mock_from_dev:
             mock_from_dev.return_value = PartnerContext(partner_id="partner_123", partner_name="Real Partner")
             
             ctx = await PartnerContext.from_session(token="dummy", db_session=mock_db_session)
             
             assert ctx.partner_id == "partner_123"
             # Should be called with the real ID
             assert mock_from_dev.call_args[0][0] == "partner_123"

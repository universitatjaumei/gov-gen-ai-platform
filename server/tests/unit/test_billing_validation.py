import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from server.app.modules.automation.billing_engine import BillingEngine
from server.app.database.models import License, ClientAccount, PartnerAccount

@pytest.mark.asyncio
async def test_validate_access_success():
    """Test standard success path."""
    engine = BillingEngine()
    
    with patch("server.app.modules.automation.billing_engine.AsyncSession") as mock_session_cls:
        mock_session = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session
        
        # Mock Data
        from datetime import datetime, timedelta
        future = datetime.utcnow() + timedelta(days=365)
        mock_license = License(license_id="lic_1", client_id="cli_1", status="active", quota_tokens=1000, consumed_tokens=0, valid_until=future)
        mock_client = ClientAccount(client_id="cli_1", partner_id="part_1", name="Test Client", license_key="xyz")
        mock_partner = PartnerAccount(partner_id="part_1", name="Test Partner", email="x@x.com", credits_balance=1000)
        
        # Configure Get returns in order: License -> Client -> Partner
        # Note: BillingEngine.validate_access likely does multiple gets.
        # We need to ensure the order matches implementation or use side_effect
        
        async def get_side_effect(model, key):
            if model == License: return mock_license
            if model == ClientAccount: return mock_client
            if model == PartnerAccount: return mock_partner
            return None
            
        mock_session.get.side_effect = get_side_effect
        
        # Test
        result = await engine.validate_access("lic_1", estimated_cost=10)
        assert result is True

@pytest.mark.asyncio
async def test_validate_access_no_license():
    """Test failure when license does not exist."""
    engine = BillingEngine()
    with patch("server.app.modules.automation.billing_engine.AsyncSession") as mock_session_cls:
        mock_session = mock_session_cls.return_value.__aenter__.return_value = AsyncMock()
        mock_session.get.return_value = None # License None
        
        with pytest.raises(Exception) as exc:
             await engine.validate_access("invalid_lic")
        assert "No active license found" in str(exc.value)

@pytest.mark.asyncio
async def test_validate_access_license_invalid():
    """Test failure when license is expired/consumed."""
    engine = BillingEngine()
    with patch("server.app.modules.automation.billing_engine.AsyncSession") as mock_session_cls:
        mock_session = mock_session_cls.return_value.__aenter__.return_value = AsyncMock()
        
        # Locked/Expired License
        from datetime import datetime
        past = datetime(2020, 1, 1)
        bad_license = License(license_id="lic_bad", client_id="cli_1", status="expired", quota_tokens=100, consumed_tokens=100, valid_until=past)
        mock_session.get.return_value = bad_license
        
        with pytest.raises(Exception) as exc:
             await engine.validate_access("lic_bad")
        assert "License is not active or expired" in str(exc.value)

@pytest.mark.asyncio
async def test_validate_access_partner_credit_limit():
    """Test failure when partner has insufficient credits."""
    engine = BillingEngine()
    with patch("server.app.modules.automation.billing_engine.AsyncSession") as mock_session_cls:
        mock_session = mock_session_cls.return_value.__aenter__.return_value = AsyncMock()
        
        from datetime import datetime, timedelta
        future = datetime.utcnow() + timedelta(days=365)
        mock_license = License(license_id="lic_1", client_id="cli_1", status="active", quota_tokens=1000, consumed_tokens=0, valid_until=future)
        mock_client = ClientAccount(client_id="cli_1", partner_id="part_1", name="Test Client", license_key="xyz")
        # Partner has 0 credits
        mock_partner = PartnerAccount(partner_id="part_1", name="Test Partner", email="x@x.com", credits_balance=0)
        
        async def get_side_effect(model, key):
            if model == License: return mock_license
            if model == ClientAccount: return mock_client
            if model == PartnerAccount: return mock_partner
            return None
        mock_session.get.side_effect = get_side_effect
        
        with pytest.raises(Exception) as exc:
             await engine.validate_access("lic_1", estimated_cost=50)
             
        # Verification of exact user wording not strictly required in Unit Backend test 
        # but the error code/class should be distinct. 
        # The plan says to raise PartnerCreditError.
        # We'll check the message part or type.
        assert "Partner credit limit exceeded" in str(exc.value)

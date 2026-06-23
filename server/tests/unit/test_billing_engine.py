import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from server.app.modules.automation.billing_engine import BillingEngine
from server.app.database.models import License, ClientAccount, PartnerAccount

# --- Helpers ---
class FakeResult:
    def __init__(self, item):
        self.item = item
    def scalar_one(self):
        return self.item

class FakeAsyncSession:
    def __init__(self, results_sequence):
        self.results_iter = iter(results_sequence)
        self.committed = False
        self.added = []
        # Mapping for .get() method: {(ModelClass, pk): instance}
        self.get_mapping = {}

    async def execute(self, *args, **kwargs):
        return next(self.results_iter)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True
    
    async def get(self, model_class, primary_key):
        """Simulate session.get(Model, pk) behavior"""
        return self.get_mapping.get((model_class, primary_key))

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

# --- Tests ---

@pytest.mark.asyncio
async def test_billing_engine_records_consumption():
    """Verificar registro de consumo de tokens"""
    engine = BillingEngine()
    
    # Datos de prueba
    mock_license = License(
        license_id="lic_001",
        client_id="client_001",
        quota_tokens=100000,
        consumed_tokens=1000,
        valid_until=datetime.now(),
        status="ACTIVE"
    )
    
    mock_client = ClientAccount(
        client_id="client_001",
        partner_id="partner_001",
        name="Test Client",
        license_key="hash"
    )

    mock_partner = PartnerAccount(
        partner_id="partner_001",
        name="Test Partner",
        email="test@partner.com",
        credits_balance=10000
    )
    
    # Configurar fake session con mapping para .get()
    fake_session = FakeAsyncSession([])
    fake_session.get_mapping = {
        (License, "lic_001"): mock_license,
        (ClientAccount, "client_001"): mock_client,
        (PartnerAccount, "partner_001"): mock_partner
    }

    # El patch debe devolver siempre esta instancia (o factory)
    # create_autospec=True puede ser util, pero aqui return_value sirve
    with patch("server.app.modules.automation.billing_engine.AsyncSession", return_value=fake_session):
        await engine.record_consumption(
            license_id="lic_001",
            tokens_used=500,
            operation="text_generation"
        )
        
        # Verify changes
        assert mock_license.consumed_tokens == 1500
        assert mock_partner.credits_balance == 9500
        assert fake_session.committed is True

@pytest.mark.asyncio
async def test_billing_engine_updates_partner_balance():
    """Verificar que se descuentan créditos del Partner"""
    engine = BillingEngine()
    
    mock_partner = PartnerAccount(
        partner_id="partner_001",
        name="Test Partner",
         email="test@partner.com",
        credits_balance=10000
    )
    
    fake_session = FakeAsyncSession([
        FakeResult(mock_partner)
    ])

    with patch("server.app.modules.automation.billing_engine.AsyncSession", return_value=fake_session):
        await engine.deduct_partner_credits(
            partner_id="partner_001",
            amount=500
        )
        
        assert mock_partner.credits_balance == 9500
        assert fake_session.committed is True

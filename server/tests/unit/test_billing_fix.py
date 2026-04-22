import pytest
from unittest.mock import AsyncMock, patch
from server.app.modules.brain.billing_engine import BillingEngine
from server.app.database.models import License, ClientAccount, PartnerAccount

@pytest.mark.asyncio
async def test_record_consumption_fix_no_greenlet_error():
    """
    Test que verifica que record_consumption se ejecuta sin errores de Greenlet
    y actualiza correctamente los balances.
    """
    engine = BillingEngine()
    
    # IDs de prueba
    lic_id = "test-lic-123"
    cli_id = "test-cli-456"
    part_id = "test-part-789"
    tokens_to_use = 100
    
    # Mocks de los objetos de base de datos
    mock_license = License(
        license_id=lic_id,
        client_id=cli_id,
        quota_tokens=1000,
        consumed_tokens=100,
        valid_until=AsyncMock(), # No importa para este test
        status="ACTIVE"
    )
    
    mock_client = ClientAccount(
        client_id=cli_id,
        partner_id=part_id,
        name="Test Client",
        license_key="key"
    )
    
    mock_partner = PartnerAccount(
        partner_id=part_id,
        name="Test Partner",
        email="partner@test.com",
        credits_balance=5000
    )

    # Configuramos el mock de AsyncSession
    mock_session = AsyncMock()
    mock_session.get.side_effect = [mock_license, mock_client, mock_partner]
    
    # El mock de la clase AsyncSession debe devolver el mock_session cuando se usa como context manager
    with patch("server.app.modules.brain.billing_engine.AsyncSession") as mock_session_class:
        mock_session_class.return_value.__aenter__.return_value = mock_session
        
        # Ejecutamos la función
        await engine.record_consumption(license_id=lic_id, tokens_used=tokens_to_use)
        
        # Verificaciones
        # 1. Se llamaron a los gets esperados
        assert mock_session.get.call_count == 3
        
        # 2. Los datos se actualizaron correctamente
        assert mock_license.consumed_tokens == 200
        assert mock_partner.credits_balance == 4900
        
        # 3. Se añadieron los objetos a la sesión y se hizo commit
        assert mock_session.add.call_count == 2
        mock_session.commit.assert_awaited_once()

@pytest.mark.asyncio
async def test_record_consumption_log_cleanliness(capsys):
    """
    Verifica que el log impreso no contenga caracteres problemáticos.
    """
    engine = BillingEngine()
    
    lic_id = "lic-log-test"
    mock_license = License(license_id=lic_id, client_id="cli", consumed_tokens=0, quota_tokens=1000, valid_until=AsyncMock())
    mock_client = ClientAccount(client_id="cli", partner_id="part", license_key="k", name="n")
    mock_partner = PartnerAccount(partner_id="part", credits_balance=1000, name="n", email="e")
    
    mock_session = AsyncMock()
    mock_session.get.side_effect = [mock_license, mock_client, mock_partner]
    
    with patch("server.app.modules.brain.billing_engine.AsyncSession") as mock_session_class:
        mock_session_class.return_value.__aenter__.return_value = mock_session
        await engine.record_consumption(license_id=lic_id, tokens_used=50)
        
        captured = capsys.readouterr()
        # Verificamos que contenga la info esperada y no caracteres raros (aunque el print ya era bastante limpio)
        assert "[Billing] Facturacion: 50 tokens" in captured.out
        assert f"Lic: {lic_id}" in captured.out
        # Nos aseguramos que no haya emojis u otros que fallarían en CP1252
        # (Este test pasará si el print usa caracteres estándar)
        assert all(ord(c) < 128 for c in captured.out.strip())

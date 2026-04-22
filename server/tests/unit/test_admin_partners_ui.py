import pytest
from server.app.database.models import PartnerAccount

def test_partner_creation_structure():
    """Verifica que el modelo Partner acepta los datos del formulario UI"""
    p = PartnerAccount(
        partner_id="new_partner",
        name="Consultora TIC SL",
        email="admin@tic.com",
        credits_balance=500000,
        is_active=True
    )
    assert p.partner_id == "new_partner"
    assert p.credits_balance == 500000
    assert p.is_active is True
    assert p.name == "Consultora TIC SL"

def test_partner_credit_adjustment():
    """Verifica lógica de ajuste de créditos"""
    p = PartnerAccount(
        partner_id="test_partner",
        name="Test Partner",
        credits_balance=1000
    )
    
    # Add credits
    p.credits_balance += 5000
    assert p.credits_balance == 6000
    
    # Set absolute value
    p.credits_balance = 10000
    assert p.credits_balance == 10000

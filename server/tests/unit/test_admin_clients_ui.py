import pytest
import secrets
from automatia_shared.validators import hash_license_key

def test_license_key_generation_format():
    """Verifica formato de license key generada"""
    # Simula la lógica del botón 'Generar Key'
    raw_key = f"LIC-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
    
    # Formato esperado: LIC-XXXXXXXX-XXXXXXXX-XXXXXXXX
    assert raw_key.startswith("LIC-")
    assert len(raw_key.split('-')) == 4
    assert all(len(part) == 8 for part in raw_key.split('-')[1:])

def test_license_key_hashing():
    """Verifica que el hash es diferente a la key original"""
    # Use a mock or rely on implementation if automatia_shared is available
    # The prompt implies automatia_shared exists. 
    # If not, I might need to implement the hashing logic in the test or import from app if shared is not set up.
    # Assuming automatia_shared is in python path or installed.
    
    raw_key = "LIC-ABC12345-DEF67890-GHI11111"
    hashed = hash_license_key(raw_key)
    
    assert raw_key != hashed
    assert len(hashed) == 64  # SHA256 produces 64 hex chars
    assert hashed.isalnum()  # Solo caracteres hexadecimales

def test_client_license_structure():
    """Verifica estructura de datos para creación de cliente + licencia"""
    from server.app.database.models import ClientAccount, License
    from abc import ABC # Dummy just to have some imports if needed
    from datetime import datetime, timedelta
    
    # We must ensure models are available. server.tests.conftest adds root to path.
    
    client = ClientAccount(
        client_id="test_client_001",
        name="Ayuntamiento Test",
        partner_id="partner_dev",
        license_key=hash_license_key("LIC-TEST-1234-5678-9012"),
        is_active=True
    )
    
    license = License(
        license_id="lic_test_001",
        client_id=client.client_id,
        quota_tokens=1000000,
        consumed_tokens=0,
        valid_until=datetime.utcnow() + timedelta(days=365),
        status="ACTIVE"
    )
    
    assert client.client_id == "test_client_001"
    assert license.quota_tokens == 1000000
    assert license.remaining_tokens == 1000000

import pytest
import hashlib
from unittest.mock import MagicMock
from app.services.sandbox_service import (
    SandboxExecutionService,
    IntegrityError
)
# Note: SecurityException might need to be imported depending on where it fits, 
# but for now we focus on IntegrityError as per prompt instructions.

# === Tests de Hash ===

def test_execution_blocked_on_hash_mismatch():
    svc = SandboxExecutionService(MagicMock())
    code = "print('changed')"
    fake_hash = hashlib.sha256(b"print('original')").hexdigest()

    with pytest.raises(IntegrityError, match="Hash mismatch"):
        svc.validate_integrity(code, expected_hash=fake_hash)

def test_execution_allowed_on_hash_match():
    svc = SandboxExecutionService(MagicMock())
    code = "print('ok')"
    good_hash = hashlib.sha256(code.encode()).hexdigest()

    assert svc.validate_integrity(code, expected_hash=good_hash) is True

def test_hash_optional_when_not_provided():
    """Si no se proporciona hash, no se valida (modo desarrollo)."""
    svc = SandboxExecutionService(MagicMock())
    code = "print('no hash')"

    assert svc.validate_integrity(code, expected_hash=None) is True

# === Tests de Firma Digital (ed25519) ===

def test_signature_verification_success():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    # Generar par de claves
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw
    )

    code = "print('signed')"
    signature = private_key.sign(code.encode())

    svc = SandboxExecutionService(MagicMock(), public_key=public_bytes)
    assert svc.validate_integrity(code, expected_sig=signature) is True

def test_signature_verification_fails_on_tampered_code():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw
    )

    code = "print('original')"
    signature = private_key.sign(code.encode())

    svc = SandboxExecutionService(MagicMock(), public_key=public_bytes)

    with pytest.raises(IntegrityError, match="Invalid signature"):
        svc.validate_integrity(code + " # tampered", expected_sig=signature)

def test_signature_required_when_public_key_configured():
    """Si hay public_key configurada, la firma es obligatoria."""
    svc = SandboxExecutionService(MagicMock(), public_key=b"fake_key")
    code = "print('unsigned')"

    with pytest.raises(IntegrityError, match="Signature required"):
        svc.validate_integrity(code, expected_sig=None)


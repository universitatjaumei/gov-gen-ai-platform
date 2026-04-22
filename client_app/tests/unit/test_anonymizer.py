# client_app/tests/unit/test_anonymizer.py
import pytest
from pathlib import Path
from app.modules.privacy.anonymizer import AnonymizationContext


def test_anonymize_dni_and_email_roundtrip():
    """Verificar anonimizacion reversible de DNI y email"""
    ctx = AnonymizationContext()
    original = "DNI: 12345678Z, Email: test@example.com"
    anonym = ctx.anonymize(original)

    # Verificar que datos sensibles NO estan en texto anonimizado
    assert "12345678Z" not in anonym
    assert "test@example.com" not in anonym

    # Verificar reversibilidad
    restored = ctx.deanonymize(anonym)
    assert "12345678Z" in restored
    assert "test@example.com" in restored


def test_persistence_encrypted(tmp_path: Path):
    """Verificar que el mapa se persiste cifrado"""
    from app.modules.security.encryption_service import EncryptionService

    # Usar la misma instancia de EncryptionService para cifrar y descifrar
    enc_service = EncryptionService()

    ctx = AnonymizationContext(encryption_service=enc_service)
    ctx.anonymize("DNI: 12345678Z")

    map_path = tmp_path / "anon_map.json.enc"
    ctx.save_state(map_path)

    assert map_path.exists()

    # Verificar que NO es JSON plano (esta cifrado)
    content = map_path.read_bytes()
    assert not content.startswith(b'{')  # No es JSON sin cifrar

    # Verificar que se puede cargar (usando el mismo encryption_service)
    ctx2 = AnonymizationContext(encryption_service=enc_service)
    ctx2.load_state(map_path)
    assert len(ctx2.fake_to_real) > 0


def test_collision_handling():
    """Verificar que colisiones de fakes se manejan correctamente"""
    ctx = AnonymizationContext()

    # Forzar colision inyectando un fake manualmente
    fake_dni = "12345678A"
    ctx.fake_to_real[fake_dni] = "99999999Z"

    # Anonimizar un DNI nuevo que podria generar el mismo fake
    result = ctx.anonymize("DNI Real: 88888888B")

    # Verificar que no se pierde la asociacion original
    assert ctx.fake_to_real[fake_dni] == "99999999Z"

    # Y que el nuevo DNI tiene su propio fake (diferente)
    assert "88888888B" in ctx.fake_to_real.values()


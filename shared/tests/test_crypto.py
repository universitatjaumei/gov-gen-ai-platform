"""
Tests unitarios para las utilidades criptográficas RSA.

Valida el correcto funcionamiento de firma y verificación de payloads,
así como el manejo de errores y casos límite.
"""

import json
import pytest
from automatia_shared.crypto_utils import (
    RSASigner,
    rsa_signer,
    InvalidKeyError,
    SignatureVerificationError,
)


class TestRSASigner:
    """Suite de tests para la clase RSASigner."""

    @pytest.fixture
    def key_pair(self) -> tuple[bytes, bytes]:
        """Genera un par de claves RSA para los tests."""
        return RSASigner.generate_key_pair(key_size=2048)

    @pytest.fixture
    def signer(self) -> RSASigner:
        """Instancia de RSASigner para tests."""
        return RSASigner()

    def test_sign_and_verify_simple_payload(self, signer: RSASigner, key_pair: tuple[bytes, bytes]):
        """Firma y verifica un payload simple exitosamente."""
        private_key, public_key = key_pair
        payload = "Hello, AutomatIA!"

        signature = signer.sign_payload(payload, private_key)

        assert signature is not None
        assert len(signature) > 0
        assert signer.verify_signature(payload, signature, public_key) is True

    def test_sign_and_verify_json_manifest(self, signer: RSASigner, key_pair: tuple[bytes, bytes]):
        """Firma y verifica un manifiesto JSON completo."""
        private_key, public_key = key_pair

        manifest = {
            "id": "script-001",
            "name": "Extracción Facturas",
            "version": "1.0.0",
            "type": "extraction",
            "code_content": "def extract(doc): return {'total': 100}",
            "metadata": {
                "author": "Partner ABC",
                "created_at": "2026-02-06T10:00:00Z"
            }
        }

        # Usar serialización canónica para consistencia
        payload = RSASigner.canonicalize_json(manifest)
        signature = signer.sign_payload(payload, private_key)

        assert signer.verify_signature(payload, signature, public_key) is True

    def test_verify_detects_tampered_payload(self, signer: RSASigner, key_pair: tuple[bytes, bytes]):
        """La verificación falla si el payload ha sido modificado."""
        private_key, public_key = key_pair

        original_payload = '{"amount": 1000}'
        signature = signer.sign_payload(original_payload, private_key)

        # Intentar verificar con payload alterado
        tampered_payload = '{"amount": 9999}'

        assert signer.verify_signature(tampered_payload, signature, public_key) is False

    def test_verify_detects_corrupted_signature(self, signer: RSASigner, key_pair: tuple[bytes, bytes]):
        """La verificación falla si la firma está corrupta."""
        private_key, public_key = key_pair

        payload = "test payload"
        signature = signer.sign_payload(payload, private_key)

        # Corromper la firma (modificar un carácter)
        corrupted_signature = signature[:-1] + ('A' if signature[-1] != 'A' else 'B')

        # Puede retornar False o lanzar ValueError dependiendo de si el base64 es válido
        try:
            result = signer.verify_signature(payload, corrupted_signature, public_key)
            assert result is False
        except ValueError:
            pass  # También es aceptable si la firma base64 queda inválida

    def test_verify_fails_with_wrong_public_key(self, signer: RSASigner, key_pair: tuple[bytes, bytes]):
        """La verificación falla si se usa una clave pública diferente."""
        private_key, public_key = key_pair

        # Generar otro par de claves (atacante)
        _, attacker_public_key = RSASigner.generate_key_pair(key_size=2048)

        payload = "sensitive data"
        signature = signer.sign_payload(payload, private_key)

        # Verificar con clave pública del atacante debe fallar
        assert signer.verify_signature(payload, signature, attacker_public_key) is False

    def test_sign_empty_payload_raises_error(self, signer: RSASigner, key_pair: tuple[bytes, bytes]):
        """Firmar un payload vacío lanza ValueError."""
        private_key, _ = key_pair

        with pytest.raises(ValueError, match="vacío"):
            signer.sign_payload("", private_key)

    def test_sign_invalid_private_key_raises_error(self, signer: RSASigner):
        """Firmar con clave privada inválida lanza InvalidKeyError."""
        invalid_key = b"not a valid key"

        with pytest.raises(InvalidKeyError):
            signer.sign_payload("test", invalid_key)

    def test_verify_invalid_public_key_raises_error(self, signer: RSASigner):
        """Verificar con clave pública inválida lanza InvalidKeyError."""
        invalid_key = b"not a valid key"

        with pytest.raises(InvalidKeyError):
            signer.verify_signature("test", "c2lnbmF0dXJl", invalid_key)

    def test_verify_invalid_base64_signature_raises_error(self, signer: RSASigner, key_pair: tuple[bytes, bytes]):
        """Verificar con firma base64 inválida lanza ValueError."""
        _, public_key = key_pair

        with pytest.raises(ValueError, match="malformada"):
            signer.verify_signature("test", "not!valid!base64!!!", public_key)

    def test_verify_empty_inputs_returns_false(self, signer: RSASigner, key_pair: tuple[bytes, bytes]):
        """Verificar con inputs vacíos retorna False sin lanzar excepción."""
        _, public_key = key_pair

        assert signer.verify_signature("", "signature", public_key) is False
        assert signer.verify_signature("payload", "", public_key) is False


class TestCanonicalizeJson:
    """Tests para la serialización JSON canónica."""

    def test_canonicalize_sorts_keys(self):
        """Las claves se ordenan alfabéticamente."""
        data = {"zebra": 1, "apple": 2, "mango": 3}
        result = RSASigner.canonicalize_json(data)

        assert result == '{"apple":2,"mango":3,"zebra":1}'

    def test_canonicalize_nested_objects(self):
        """Los objetos anidados también se ordenan."""
        data = {
            "outer": {
                "z_inner": 1,
                "a_inner": 2
            },
            "alpha": "first"
        }
        result = RSASigner.canonicalize_json(data)

        parsed = json.loads(result)
        assert list(parsed.keys()) == ["alpha", "outer"]
        assert list(parsed["outer"].keys()) == ["a_inner", "z_inner"]

    def test_canonicalize_no_extra_whitespace(self):
        """No hay espacios extra en la salida."""
        data = {"key": "value", "number": 123}
        result = RSASigner.canonicalize_json(data)

        assert " " not in result
        assert "\n" not in result

    def test_canonicalize_deterministic(self):
        """La misma entrada siempre produce la misma salida."""
        data = {"id": "123", "name": "test", "values": [1, 2, 3]}

        results = [RSASigner.canonicalize_json(data) for _ in range(100)]

        assert len(set(results)) == 1  # Todas las salidas son idénticas

    def test_canonicalize_handles_unicode(self):
        """Maneja correctamente caracteres Unicode."""
        data = {"mensaje": "¡Hola, España! 日本語"}
        result = RSASigner.canonicalize_json(data)

        assert "España" in result
        assert "日本語" in result


class TestGenerateKeyPair:
    """Tests para la generación de pares de claves."""

    def test_generate_returns_valid_pem_format(self):
        """Las claves generadas están en formato PEM válido."""
        private_key, public_key = RSASigner.generate_key_pair()

        assert private_key.startswith(b"-----BEGIN PRIVATE KEY-----")
        assert private_key.endswith(b"-----END PRIVATE KEY-----\n")
        assert public_key.startswith(b"-----BEGIN PUBLIC KEY-----")
        assert public_key.endswith(b"-----END PUBLIC KEY-----\n")

    def test_generate_different_sizes(self):
        """Se pueden generar claves de diferentes tamaños."""
        private_2048, _ = RSASigner.generate_key_pair(key_size=2048)
        private_4096, _ = RSASigner.generate_key_pair(key_size=4096)

        # La clave de 4096 bits debe ser más larga
        assert len(private_4096) > len(private_2048)

    def test_generated_keys_work_together(self):
        """Las claves generadas funcionan correctamente para firma/verificación."""
        private_key, public_key = RSASigner.generate_key_pair()
        signer = RSASigner()

        payload = "test message for signature verification"
        signature = signer.sign_payload(payload, private_key)

        assert signer.verify_signature(payload, signature, public_key) is True


class TestSingletonInstance:
    """Tests para la instancia singleton rsa_signer."""

    def test_singleton_is_rsa_signer_instance(self):
        """La instancia singleton es del tipo correcto."""
        assert isinstance(rsa_signer, RSASigner)

    def test_singleton_works_correctly(self):
        """La instancia singleton funciona correctamente."""
        private_key, public_key = RSASigner.generate_key_pair()

        payload = "singleton test"
        signature = rsa_signer.sign_payload(payload, private_key)

        assert rsa_signer.verify_signature(payload, signature, public_key) is True


class TestIntegrationScenario:
    """Test de integración: escenario completo de firma de manifiesto."""

    def test_full_manifest_signing_workflow(self):
        """
        Escenario completo: Partner firma un manifiesto, Cliente lo verifica.

        Simula el flujo real donde:
        1. El Partner (servidor) genera un manifiesto de automatización
        2. Lo firma con su clave privada
        3. El Cliente descarga el manifiesto + firma
        4. El Cliente verifica la autenticidad con la clave pública del Partner
        """
        # Setup: Partner tiene su par de claves
        partner_private_key, partner_public_key = RSASigner.generate_key_pair(key_size=2048)

        # 1. Partner crea un manifiesto de automatización
        manifest = {
            "id": "automation-2026-001",
            "name": "Proceso de Facturación Automática",
            "type": "workflow",
            "version": "2.1.0",
            "code_content": """
def process_invoice(data):
    validated = validate_fields(data)
    enriched = enrich_with_api(validated)
    return save_to_erp(enriched)
""",
            "steps": [
                {"name": "validate", "type": "extraction"},
                {"name": "enrich", "type": "api_call"},
                {"name": "save", "type": "database"}
            ],
            "metadata": {
                "author": "Partner Consulting SL",
                "created_at": "2026-02-06T12:00:00Z",
                "client_scope": "enterprise"
            }
        }

        # 2. Partner serializa de forma canónica y firma
        canonical_manifest = RSASigner.canonicalize_json(manifest)
        signature = rsa_signer.sign_payload(canonical_manifest, partner_private_key)

        # 3. Simular transmisión al cliente (manifest + signature)
        transmitted_data = {
            "manifest": manifest,
            "signature": signature
        }

        # 4. Cliente recibe y verifica
        received_manifest = transmitted_data["manifest"]
        received_signature = transmitted_data["signature"]

        # Cliente reconstruye el payload canónico
        client_canonical = RSASigner.canonicalize_json(received_manifest)

        # Cliente verifica con la clave pública del Partner (pre-configurada)
        is_authentic = rsa_signer.verify_signature(
            client_canonical,
            received_signature,
            partner_public_key
        )

        assert is_authentic is True, "El manifiesto debería ser auténtico"

        # 5. Simular ataque: modificación del manifiesto en tránsito
        tampered_manifest = received_manifest.copy()
        tampered_manifest["code_content"] = "def malicious(): os.system('rm -rf /')"

        tampered_canonical = RSASigner.canonicalize_json(tampered_manifest)

        is_tampered_authentic = rsa_signer.verify_signature(
            tampered_canonical,
            received_signature,
            partner_public_key
        )

        assert is_tampered_authentic is False, "El manifiesto alterado NO debería pasar verificación"

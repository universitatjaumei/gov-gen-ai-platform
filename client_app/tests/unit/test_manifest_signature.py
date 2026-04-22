"""
Tests para el servicio de firma de manifiesto.
Prompt 1.3 del sistema de exportación/importación de automatismos.

TDD: Estos tests se escriben ANTES de implementar el servicio.

La firma se aplica SOLO al manifest.json, no a cada archivo individual.
Dos tipos de firma:
- HMAC-SHA256 para cliente (usando license_key + machine_id)
- RSA para partner (requiere servidor Brain)
"""
import pytest
import json
import hashlib
import hmac
from datetime import datetime
from unittest.mock import patch

from client_app.app.services.manifest_signature_service import (
    ManifestSignatureService,
    manifest_signature_service
)


@pytest.fixture
def signature_service():
    """Instancia del servicio de firma."""
    return ManifestSignatureService()


@pytest.fixture
def sample_manifest():
    """Manifiesto de ejemplo para tests."""
    return json.dumps({
        "version": "1.0",
        "name": "test-package",
        "export_date": "2024-01-15T10:30:00Z",
        "source": {
            "license_id": "LIC-001",
            "client_id": "CLI-001",
            "partner_id": "PARTNER-001"
        },
        "contents": {
            "scripts": ["script1.py", "script2.py"],
            "playbooks": []
        },
        "file_hashes": {
            "scripts/script1.py": "abc123",
            "scripts/script2.py": "def456"
        }
    }, sort_keys=True)


@pytest.fixture
def client_credentials():
    """Credenciales de cliente de ejemplo."""
    return {
        "license_key": "LIC-KEY-ABC123-XYZ789",
        "machine_id": "MACHINE-001-ABCDEF"
    }


class TestDeriveClientKey:
    """Tests para derivación de clave HMAC del cliente."""

    def test_derive_client_key(self, signature_service, client_credentials):
        """Clave derivada de license_key + machine_id es determinista."""
        key1 = signature_service.derive_client_key(
            client_credentials["license_key"],
            client_credentials["machine_id"]
        )
        key2 = signature_service.derive_client_key(
            client_credentials["license_key"],
            client_credentials["machine_id"]
        )

        # Mismas credenciales = misma clave
        assert key1 == key2
        # La clave es bytes de 32 bytes (SHA256)
        assert isinstance(key1, bytes)
        assert len(key1) == 32

    def test_derive_client_key_different_credentials(self, signature_service):
        """Credenciales diferentes producen claves diferentes."""
        key1 = signature_service.derive_client_key("LICENSE-A", "MACHINE-1")
        key2 = signature_service.derive_client_key("LICENSE-B", "MACHINE-1")
        key3 = signature_service.derive_client_key("LICENSE-A", "MACHINE-2")

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_derive_client_key_format(self, signature_service, client_credentials):
        """La clave se deriva usando SHA256 de 'license_key:machine_id'."""
        expected_combined = f"{client_credentials['license_key']}:{client_credentials['machine_id']}"
        expected_key = hashlib.sha256(expected_combined.encode()).digest()

        actual_key = signature_service.derive_client_key(
            client_credentials["license_key"],
            client_credentials["machine_id"]
        )

        assert actual_key == expected_key


class TestSignManifestClient:
    """Tests para firma de manifiesto como cliente (HMAC)."""

    def test_sign_manifest_client_hmac(self, signature_service, sample_manifest, client_credentials):
        """Firma con HMAC usando credenciales cliente."""
        signature = signature_service.sign_as_client(
            sample_manifest,
            client_credentials["license_key"],
            client_credentials["machine_id"]
        )

        # Verificar estructura de la firma
        assert isinstance(signature, dict)
        assert signature["type"] == "CLIENT"
        assert signature["algorithm"] == "HMAC-SHA256"
        assert "value" in signature
        assert "timestamp" in signature

        # El valor de la firma es hexadecimal
        assert len(signature["value"]) == 64  # SHA256 hex
        int(signature["value"], 16)  # No debe lanzar excepción

    def test_signature_includes_timestamp(self, signature_service, sample_manifest, client_credentials):
        """La firma incluye timestamp ISO."""
        signature = signature_service.sign_as_client(
            sample_manifest,
            client_credentials["license_key"],
            client_credentials["machine_id"]
        )

        # El timestamp debe ser ISO format válido
        timestamp = signature["timestamp"]
        assert timestamp is not None

        # Debe poder parsearse como datetime
        parsed = datetime.fromisoformat(timestamp)
        assert parsed is not None

    def test_sign_manifest_is_deterministic_with_same_timestamp(
        self, signature_service, sample_manifest, client_credentials
    ):
        """La firma es determinista si el timestamp es el mismo."""
        fixed_timestamp = "2024-01-15T12:00:00"

        with patch.object(
            signature_service, '_get_timestamp', return_value=fixed_timestamp
        ):
            sig1 = signature_service.sign_as_client(
                sample_manifest,
                client_credentials["license_key"],
                client_credentials["machine_id"]
            )
            sig2 = signature_service.sign_as_client(
                sample_manifest,
                client_credentials["license_key"],
                client_credentials["machine_id"]
            )

        assert sig1["value"] == sig2["value"]
        assert sig1["timestamp"] == sig2["timestamp"]

    def test_sign_manifest_different_content_different_signature(
        self, signature_service, client_credentials
    ):
        """Contenido diferente produce firma diferente."""
        manifest1 = json.dumps({"name": "package1"})
        manifest2 = json.dumps({"name": "package2"})

        fixed_timestamp = "2024-01-15T12:00:00"

        with patch.object(
            signature_service, '_get_timestamp', return_value=fixed_timestamp
        ):
            sig1 = signature_service.sign_as_client(
                manifest1,
                client_credentials["license_key"],
                client_credentials["machine_id"]
            )
            sig2 = signature_service.sign_as_client(
                manifest2,
                client_credentials["license_key"],
                client_credentials["machine_id"]
            )

        assert sig1["value"] != sig2["value"]


class TestVerifyClientSignature:
    """Tests para verificación de firma de cliente."""

    def test_verify_signature_valid(self, signature_service, sample_manifest, client_credentials):
        """Verificación exitosa de firma válida."""
        # Firmar
        signature = signature_service.sign_as_client(
            sample_manifest,
            client_credentials["license_key"],
            client_credentials["machine_id"]
        )

        # Verificar
        is_valid = signature_service.verify_client_signature(
            sample_manifest,
            signature,
            client_credentials["license_key"],
            client_credentials["machine_id"]
        )

        assert is_valid is True

    def test_verify_signature_tampered(self, signature_service, sample_manifest, client_credentials):
        """Detecta manifest modificado."""
        # Firmar manifest original
        signature = signature_service.sign_as_client(
            sample_manifest,
            client_credentials["license_key"],
            client_credentials["machine_id"]
        )

        # Modificar el manifest
        tampered_manifest = sample_manifest.replace("test-package", "hacked-package")

        # Verificar con manifest modificado debe fallar
        is_valid = signature_service.verify_client_signature(
            tampered_manifest,
            signature,
            client_credentials["license_key"],
            client_credentials["machine_id"]
        )

        assert is_valid is False

    def test_verify_signature_wrong_credentials(
        self, signature_service, sample_manifest, client_credentials
    ):
        """Firma no válida con credenciales incorrectas."""
        # Firmar con credenciales correctas
        signature = signature_service.sign_as_client(
            sample_manifest,
            client_credentials["license_key"],
            client_credentials["machine_id"]
        )

        # Verificar con credenciales incorrectas
        is_valid = signature_service.verify_client_signature(
            sample_manifest,
            signature,
            "WRONG-LICENSE-KEY",
            client_credentials["machine_id"]
        )

        assert is_valid is False

    def test_verify_signature_tampered_signature_value(
        self, signature_service, sample_manifest, client_credentials
    ):
        """Detecta firma manipulada."""
        signature = signature_service.sign_as_client(
            sample_manifest,
            client_credentials["license_key"],
            client_credentials["machine_id"]
        )

        # Manipular el valor de la firma
        signature["value"] = "a" * 64  # Firma falsa

        is_valid = signature_service.verify_client_signature(
            sample_manifest,
            signature,
            client_credentials["license_key"],
            client_credentials["machine_id"]
        )

        assert is_valid is False

    def test_verify_signature_tampered_timestamp(
        self, signature_service, sample_manifest, client_credentials
    ):
        """Detecta timestamp manipulado."""
        signature = signature_service.sign_as_client(
            sample_manifest,
            client_credentials["license_key"],
            client_credentials["machine_id"]
        )

        # Manipular el timestamp
        signature["timestamp"] = "2099-12-31T23:59:59"

        is_valid = signature_service.verify_client_signature(
            sample_manifest,
            signature,
            client_credentials["license_key"],
            client_credentials["machine_id"]
        )

        assert is_valid is False


class TestSignManifestPartner:
    """Tests para firma de manifiesto como partner (RSA)."""

    @pytest.mark.asyncio
    async def test_sign_manifest_partner_rsa_not_implemented(self, signature_service, sample_manifest):
        """Firma RSA de partner requiere servidor Brain."""
        with pytest.raises(NotImplementedError) as exc_info:
            await signature_service.sign_as_partner(sample_manifest, "PARTNER-001")

        assert "Requiere Brain en servidor" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_verify_partner_signature_not_implemented(self, signature_service, sample_manifest):
        """Verificación RSA de partner requiere servidor Brain."""
        fake_signature = {
            "type": "PARTNER",
            "algorithm": "RSA-SHA256",
            "value": "fake_signature",
            "timestamp": "2024-01-15T12:00:00"
        }

        with pytest.raises(NotImplementedError) as exc_info:
            await signature_service.verify_partner_signature(
                sample_manifest, fake_signature, "PARTNER-001"
            )

        assert "Requiere Brain en servidor" in str(exc_info.value)


class TestSingleton:
    """Tests para el singleton del servicio."""

    def test_singleton_exists(self):
        """El singleton manifest_signature_service existe."""
        assert manifest_signature_service is not None
        assert isinstance(manifest_signature_service, ManifestSignatureService)

    def test_singleton_is_functional(self, sample_manifest, client_credentials):
        """El singleton es funcional."""
        signature = manifest_signature_service.sign_as_client(
            sample_manifest,
            client_credentials["license_key"],
            client_credentials["machine_id"]
        )

        assert signature["type"] == "CLIENT"
        assert "value" in signature

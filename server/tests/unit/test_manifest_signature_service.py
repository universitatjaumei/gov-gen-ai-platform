"""
Tests unitarios para ManifestSignatureService.

Valida la firma de manifiestos, manejo de errores y logging de auditoría.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from server.app.services.manifest_signature_service import (
    ManifestSignatureService,
    manifest_signature_service,
    SignatureConfigError,
)
from automatia_shared.crypto_utils import RSASigner


class TestManifestSignatureService:
    """Suite de tests para ManifestSignatureService."""

    @pytest.fixture
    def key_pair(self) -> tuple[bytes, bytes]:
        """Genera un par de claves RSA para los tests."""
        return RSASigner.generate_key_pair(key_size=2048)

    @pytest.fixture
    def sample_manifest(self) -> dict:
        """Manifiesto de ejemplo para tests."""
        return {
            "id": "script-test-001",
            "name": "Script de Prueba",
            "type": "extraction",
            "code_content": "def extract(doc): return {'field': 'value'}",
            "version": 1,
            "partner_id": "partner-abc",
            "client_id": None,
            "is_system_template": False,
            "is_workflow": False,
        }

    def test_service_without_key_returns_none(self, sample_manifest):
        """Sin clave configurada, sign_manifest retorna None."""
        with patch.dict(os.environ, {}, clear=True):
            # Eliminar la variable si existe
            os.environ.pop("AUTOMATIA_SIGNING_KEY", None)
            service = ManifestSignatureService()

            assert service.is_configured is False
            signature = service.sign_manifest(sample_manifest)
            assert signature is None

    def test_service_with_valid_key_signs_manifest(self, key_pair, sample_manifest):
        """Con clave válida, sign_manifest retorna firma Base64."""
        private_key, public_key = key_pair

        with patch.dict(os.environ, {"AUTOMATIA_SIGNING_KEY": private_key.decode()}):
            service = ManifestSignatureService()

            assert service.is_configured is True
            signature = service.sign_manifest(sample_manifest)

            assert signature is not None
            assert len(signature) > 0
            assert isinstance(signature, str)

    def test_signature_is_verifiable(self, key_pair, sample_manifest):
        """La firma generada puede ser verificada con la clave pública."""
        private_key, public_key = key_pair

        with patch.dict(os.environ, {"AUTOMATIA_SIGNING_KEY": private_key.decode()}):
            service = ManifestSignatureService()
            signature = service.sign_manifest(sample_manifest)

            # Verificar con RSASigner
            signer = RSASigner()
            signable_data = service.get_signable_fields(sample_manifest)
            canonical = RSASigner.canonicalize_json(signable_data)

            is_valid = signer.verify_signature(canonical, signature, public_key)
            assert is_valid is True

    def test_signature_detects_tampering(self, key_pair, sample_manifest):
        """La firma detecta modificaciones en el manifiesto."""
        private_key, public_key = key_pair

        with patch.dict(os.environ, {"AUTOMATIA_SIGNING_KEY": private_key.decode()}):
            service = ManifestSignatureService()
            signature = service.sign_manifest(sample_manifest)

            # Modificar el manifiesto después de firmar
            tampered_manifest = sample_manifest.copy()
            tampered_manifest["code_content"] = "def malicious(): pass"

            # Verificar con datos alterados
            signer = RSASigner()
            signable_data = service.get_signable_fields(tampered_manifest)
            canonical = RSASigner.canonicalize_json(signable_data)

            is_valid = signer.verify_signature(canonical, signature, public_key)
            assert is_valid is False

    def test_sign_empty_manifest_raises_error(self, key_pair):
        """Firmar manifiesto vacío lanza ValueError."""
        private_key, _ = key_pair

        with patch.dict(os.environ, {"AUTOMATIA_SIGNING_KEY": private_key.decode()}):
            service = ManifestSignatureService()

            with pytest.raises(ValueError, match="vacío"):
                service.sign_manifest({})

    def test_sign_with_invalid_key_raises_error(self, sample_manifest):
        """Firmar con clave inválida lanza SignatureConfigError."""
        with patch.dict(os.environ, {"AUTOMATIA_SIGNING_KEY": "not-a-valid-key"}):
            service = ManifestSignatureService()

            # La clave se carga pero es inválida
            assert service.is_configured is True

            with pytest.raises(SignatureConfigError):
                service.sign_manifest(sample_manifest)

    def test_all_signatures_are_valid(self, key_pair, sample_manifest):
        """
        Todas las firmas generadas son válidas y verificables.

        Nota: PSS padding es probabilístico (usa salt aleatorio), por lo que
        cada firma será diferente. Esto es correcto y más seguro que PKCS#1 v1.5.
        Lo importante es que todas las firmas sean verificables.
        """
        private_key, public_key = key_pair

        with patch.dict(os.environ, {"AUTOMATIA_SIGNING_KEY": private_key.decode()}):
            service = ManifestSignatureService()
            signer = RSASigner()

            # Firmar múltiples veces
            signatures = [service.sign_manifest(sample_manifest) for _ in range(5)]

            # Todas las firmas deben ser válidas (aunque diferentes)
            signable_data = service.get_signable_fields(sample_manifest)
            canonical = RSASigner.canonicalize_json(signable_data)

            for signature in signatures:
                assert signer.verify_signature(canonical, signature, public_key) is True

    def test_get_signable_fields_extracts_correct_keys(self, sample_manifest):
        """get_signable_fields extrae solo los campos relevantes."""
        service = ManifestSignatureService()

        full_data = {
            **sample_manifest,
            "metadata_json": {"author": "test"},
            "updated_at": "2026-02-06T12:00:00Z",
            "signature": "old-signature",
            "access_groups": ["group1"],
        }

        signable = service.get_signable_fields(full_data)

        # Debe incluir campos importantes
        assert "id" in signable
        assert "name" in signable
        assert "code_content" in signable
        assert "version" in signable

        # No debe incluir metadatos volátiles
        assert "metadata_json" not in signable
        assert "updated_at" not in signable
        assert "signature" not in signable
        assert "access_groups" not in signable


class TestSignatureWithNewlineHandling:
    """Tests para manejo de saltos de línea en la clave."""

    def test_handles_escaped_newlines(self):
        """Maneja correctamente saltos de línea escapados (\\n literal)."""
        private_key, _ = RSASigner.generate_key_pair()

        # Simular cómo se vería en una variable de entorno con \\n literal
        escaped_key = private_key.decode().replace("\n", "\\n")

        with patch.dict(os.environ, {"AUTOMATIA_SIGNING_KEY": escaped_key}):
            service = ManifestSignatureService()

            assert service.is_configured is True
            # Si la clave se procesó correctamente, debería poder firmar
            signature = service.sign_manifest({"id": "test", "name": "test"})
            assert signature is not None


class TestSingletonInstance:
    """Tests para la instancia singleton."""

    def test_singleton_exists(self):
        """La instancia singleton está disponible."""
        assert manifest_signature_service is not None
        assert isinstance(manifest_signature_service, ManifestSignatureService)


class TestAuditLogging:
    """Tests para verificar que se generan logs de auditoría."""

    def test_successful_signature_logs_info(self, caplog):
        """Una firma exitosa genera log INFO."""
        private_key, _ = RSASigner.generate_key_pair()

        with patch.dict(os.environ, {"AUTOMATIA_SIGNING_KEY": private_key.decode()}):
            import logging
            caplog.set_level(logging.INFO, logger="automatia.security.signatures")

            service = ManifestSignatureService()
            service.sign_manifest({
                "id": "test-123",
                "name": "Test Script",
                "type": "extraction"
            })

            # Verificar que se registró el evento
            assert any("firmado" in record.message.lower() for record in caplog.records)
            assert any("test-123" in record.message for record in caplog.records)

    def test_failed_signature_logs_error(self, caplog):
        """Un error de firma genera log ERROR."""
        with patch.dict(os.environ, {"AUTOMATIA_SIGNING_KEY": "invalid-key"}):
            import logging
            caplog.set_level(logging.ERROR, logger="automatia.security.signatures")

            service = ManifestSignatureService()

            with pytest.raises(SignatureConfigError):
                service.sign_manifest({"id": "test", "name": "test"})

            # Verificar que se registró el error
            assert any("error" in record.message.lower() for record in caplog.records)

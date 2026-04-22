"""
Tests de integración para verificación de firmas criptográficas.

Valida que el cliente detecta y rechaza correctamente:
1. Manifiestos sin firma
2. Manifiestos con firma corrupta
3. Manifiestos alterados después de firmados
4. Manifiestos firmados con clave incorrecta

Estos tests simulan ataques de integridad en el flujo de descarga.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from automatia_shared.dtos import AutomationBlueprintDTO
from automatia_shared.crypto_utils import RSASigner
from client_app.app.services.sync_manager import SyncManager, SignatureVerificationError


class TestSignatureVerificationIntegration:
    """Tests de integración para verificación de firmas."""

    @pytest.fixture
    def key_pair(self) -> tuple[bytes, bytes]:
        """Par de claves RSA del Partner legítimo."""
        return RSASigner.generate_key_pair(key_size=2048)

    @pytest.fixture
    def attacker_key_pair(self) -> tuple[bytes, bytes]:
        """Par de claves RSA de un atacante."""
        return RSASigner.generate_key_pair(key_size=2048)

    @pytest.fixture
    def sample_dto(self) -> AutomationBlueprintDTO:
        """DTO de ejemplo para tests."""
        return AutomationBlueprintDTO(
            id="script-integration-001",
            name="Script de Integración",
            type="pdf_extractor",
            code_content="def extract(doc):\n    return {'field': doc.get('value')}",
            version=1,
            updated_at=datetime.now(timezone.utc),
            partner_id="partner-test",
            client_id=None,
            is_system_template=False,
            signature=None,
            access_groups=[],
            is_workflow=False,
            metadata={}
        )

    def _sign_dto(self, dto: AutomationBlueprintDTO, private_key: bytes) -> str:
        """Firma un DTO con la clave privada proporcionada."""
        signer = RSASigner()

        signable_data = {
            "id": dto.id,
            "name": dto.name,
            "type": dto.type,
            "code_content": dto.code_content,
            "version": dto.version,
            "is_workflow": dto.is_workflow,
            "partner_id": dto.partner_id,
            "client_id": dto.client_id,
            "is_system_template": dto.is_system_template
        }

        canonical = RSASigner.canonicalize_json(signable_data)
        return signer.sign_payload(canonical, private_key)

    @pytest.mark.asyncio
    async def test_valid_signature_passes_verification(self, key_pair, sample_dto):
        """Un manifiesto correctamente firmado pasa la verificación."""
        private_key, public_key = key_pair

        # Firmar el DTO
        sample_dto.signature = self._sign_dto(sample_dto, private_key)

        # Crear SyncManager con la clave pública
        mock_session = AsyncMock()
        sync_manager = SyncManager(mock_session, partner_public_key=public_key)

        # Verificar - no debe lanzar excepción
        result = await sync_manager.verify_signature(sample_dto, raise_on_failure=True)

        assert result is True

    @pytest.mark.asyncio
    async def test_missing_signature_raises_error(self, key_pair, sample_dto):
        """Un manifiesto sin firma lanza SignatureVerificationError."""
        _, public_key = key_pair

        # DTO sin firma
        sample_dto.signature = None

        mock_session = AsyncMock()
        sync_manager = SyncManager(mock_session, partner_public_key=public_key)

        with pytest.raises(SignatureVerificationError, match="no tiene firma"):
            await sync_manager.verify_signature(sample_dto, raise_on_failure=True)

    @pytest.mark.asyncio
    async def test_corrupted_signature_raises_error(self, key_pair, sample_dto):
        """Una firma corrupta lanza SignatureVerificationError."""
        private_key, public_key = key_pair

        # Firmar correctamente y luego corromper
        sample_dto.signature = self._sign_dto(sample_dto, private_key)

        # Corromper la firma (modificar algunos caracteres)
        corrupted = sample_dto.signature[:-10] + "CORRUPTED!"
        sample_dto.signature = corrupted

        mock_session = AsyncMock()
        sync_manager = SyncManager(mock_session, partner_public_key=public_key)

        # Puede fallar por firma inválida o malformada
        with pytest.raises(SignatureVerificationError):
            await sync_manager.verify_signature(sample_dto, raise_on_failure=True)

    @pytest.mark.asyncio
    async def test_tampered_content_detected(self, key_pair, sample_dto):
        """
        ATAQUE: Contenido alterado después de firmar es detectado.

        Simula un ataque man-in-the-middle donde el contenido
        del script se modifica durante la transmisión.
        """
        private_key, public_key = key_pair

        # 1. Firmar el contenido original
        sample_dto.signature = self._sign_dto(sample_dto, private_key)

        # 2. ATAQUE: Modificar el código después de firmado
        sample_dto.code_content = """
def extract(doc):
    # CÓDIGO MALICIOSO INYECTADO
    import os
    os.system('rm -rf /')  # Borrar sistema
    return {'hacked': True}
"""

        mock_session = AsyncMock()
        sync_manager = SyncManager(mock_session, partner_public_key=public_key)

        # 3. La verificación debe detectar la alteración
        with pytest.raises(SignatureVerificationError, match="inválida"):
            await sync_manager.verify_signature(sample_dto, raise_on_failure=True)

    @pytest.mark.asyncio
    async def test_wrong_signer_detected(self, key_pair, attacker_key_pair, sample_dto):
        """
        ATAQUE: Firma con clave de atacante es rechazada.

        Simula un atacante que firma el contenido con su propia clave.
        El cliente debe rechazarlo porque la clave pública no coincide.
        """
        attacker_private, _ = attacker_key_pair
        _, legitimate_public = key_pair

        # ATAQUE: Firmar con la clave del atacante
        sample_dto.signature = self._sign_dto(sample_dto, attacker_private)

        # El cliente usa la clave pública LEGÍTIMA
        mock_session = AsyncMock()
        sync_manager = SyncManager(mock_session, partner_public_key=legitimate_public)

        # Debe detectar que la firma no corresponde al Partner legítimo
        with pytest.raises(SignatureVerificationError, match="inválida"):
            await sync_manager.verify_signature(sample_dto, raise_on_failure=True)

    @pytest.mark.asyncio
    async def test_save_local_blocks_invalid_signature(self, key_pair, sample_dto):
        """
        save_local() bloquea la persistencia si la firma es inválida.

        Verifica el flujo completo: descarga → verificación → bloqueo.
        """
        private_key, public_key = key_pair

        # Firmar y luego alterar
        sample_dto.signature = self._sign_dto(sample_dto, private_key)
        sample_dto.name = "NOMBRE ALTERADO POR ATACANTE"

        mock_session = AsyncMock()
        sync_manager = SyncManager(mock_session, partner_public_key=public_key)

        # save_local debe rechazar el DTO
        with pytest.raises(SignatureVerificationError):
            await sync_manager.save_local(sample_dto)

        # La base de datos NO debe haber sido llamada
        mock_session.add.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_public_key_configured_raises_error(self, sample_dto):
        """Sin clave pública configurada, se lanza error de verificación."""
        # Simular que no hay ServerConnection con clave pública
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session.exec = AsyncMock(return_value=mock_result)

        # SyncManager sin clave pública inyectada
        sync_manager = SyncManager(mock_session, partner_public_key=None)

        sample_dto.signature = "some_signature"

        with pytest.raises(SignatureVerificationError, match="clave pública.*no configurada"):
            await sync_manager.verify_signature(sample_dto, raise_on_failure=True)

    @pytest.mark.asyncio
    async def test_skip_verification_allows_unsigned(self, sample_dto):
        """
        skip_verification=True permite guardar sin verificar (modo desarrollo).
        """
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)  # No existe localmente

        sync_manager = SyncManager(mock_session, partner_public_key=None)

        sample_dto.signature = None

        # Con skip_verification=True, no debe fallar
        await sync_manager.save_local(sample_dto, skip_verification=True)

        # Se debe haber intentado guardar
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()


class TestSignatureVerificationEdgeCases:
    """Tests para casos límite de verificación."""

    @pytest.fixture
    def key_pair(self) -> tuple[bytes, bytes]:
        return RSASigner.generate_key_pair(key_size=2048)

    @pytest.mark.asyncio
    async def test_empty_code_content_verifies(self, key_pair):
        """Un script con código vacío pero firmado correctamente se verifica."""
        private_key, public_key = key_pair

        dto = AutomationBlueprintDTO(
            id="empty-script",
            name="Script Vacío",
            type="pdf_extractor",
            code_content="",  # Vacío pero válido
            version=1,
            updated_at=datetime.now(timezone.utc),
            signature=None
        )

        # Firmar
        signer = RSASigner()
        signable = {"id": dto.id, "name": dto.name, "type": dto.type,
                    "code_content": dto.code_content, "version": dto.version,
                    "is_workflow": False, "partner_id": None, "client_id": None,
                    "is_system_template": False}
        dto.signature = signer.sign_payload(
            RSASigner.canonicalize_json(signable), private_key
        )

        mock_session = AsyncMock()
        sync_manager = SyncManager(mock_session, partner_public_key=public_key)

        result = await sync_manager.verify_signature(dto, raise_on_failure=True)
        assert result is True

    @pytest.mark.asyncio
    async def test_unicode_content_verifies(self, key_pair):
        """Contenido con caracteres Unicode se verifica correctamente."""
        private_key, public_key = key_pair

        dto = AutomationBlueprintDTO(
            id="unicode-script",
            name="Script con Ñ y émojis 🎉",
            type="pdf_extractor",
            code_content="def extract():\n    return {'país': 'España', 'emoji': '🚀'}",
            version=1,
            updated_at=datetime.now(timezone.utc),
            signature=None
        )

        # Firmar
        signer = RSASigner()
        signable = {"id": dto.id, "name": dto.name, "type": dto.type,
                    "code_content": dto.code_content, "version": dto.version,
                    "is_workflow": False, "partner_id": None, "client_id": None,
                    "is_system_template": False}
        dto.signature = signer.sign_payload(
            RSASigner.canonicalize_json(signable), private_key
        )

        mock_session = AsyncMock()
        sync_manager = SyncManager(mock_session, partner_public_key=public_key)

        result = await sync_manager.verify_signature(dto, raise_on_failure=True)
        assert result is True

    @pytest.mark.asyncio
    async def test_malformed_base64_signature_raises_error(self, key_pair):
        """Una firma con Base64 inválido lanza error."""
        _, public_key = key_pair

        dto = AutomationBlueprintDTO(
            id="bad-b64",
            name="Test",
            type="pdf_extractor",
            code_content="pass",
            version=1,
            updated_at=datetime.now(timezone.utc),
            signature="!!!NOT_VALID_BASE64!!!"
        )

        mock_session = AsyncMock()
        sync_manager = SyncManager(mock_session, partner_public_key=public_key)

        with pytest.raises(SignatureVerificationError, match="malformada"):
            await sync_manager.verify_signature(dto, raise_on_failure=True)

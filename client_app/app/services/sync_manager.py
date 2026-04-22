from typing import List, Optional, Dict, Any
import hashlib
import logging
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from datetime import datetime, timezone

from client_app.app.database.models import LocalAutomation, ServerConnection
from automatia_shared.dtos import AutomationBlueprintDTO
from automatia_shared.crypto_utils import RSASigner, InvalidKeyError

logger = logging.getLogger(__name__)


class SignatureVerificationError(Exception):
    """
    Excepción de seguridad lanzada cuando la verificación de firma falla.

    Indica que el contenido descargado puede haber sido alterado o
    que no proviene de una fuente autorizada.
    """
    pass


class SyncManager:
    """
    Gestor de sincronización local con verificación criptográfica.

    Se encarga de persistir, actualizar y verificar la integridad de los automatismos
    (blueprints) descargados desde el servidor Brain.

    La verificación de firmas RSA garantiza que el contenido:
    1. No ha sido alterado en tránsito
    2. Proviene realmente del Partner/Servidor autorizado
    """

    # Campos que se incluyen en la firma (deben coincidir con el servidor)
    SIGNABLE_FIELDS = {
        "id", "name", "type", "code_content", "version",
        "is_workflow", "partner_id", "client_id", "is_system_template"
    }

    def __init__(self, session: AsyncSession, partner_public_key: Optional[bytes] = None):
        """
        Inicializa el gestor de sincronización.

        Args:
            session: Sesión de base de datos asíncrona.
            partner_public_key: Clave pública RSA del Partner en formato PEM (bytes).
                               Si no se proporciona, se intentará cargar desde ServerConnection.
        """
        self.session = session
        self._partner_public_key = partner_public_key
        self._signer = RSASigner()

    async def _get_partner_public_key(self) -> Optional[bytes]:
        """
        Obtiene la clave pública del Partner desde la configuración.

        Returns:
            bytes: Clave pública PEM o None si no está configurada.
        """
        if self._partner_public_key:
            return self._partner_public_key

        # Cargar desde ServerConnection activa
        result = await self.session.exec(
            select(ServerConnection).where(ServerConnection.is_active == True)
        )
        conn = result.first()

        if conn and conn.partner_public_key:
            self._partner_public_key = conn.partner_public_key.encode('utf-8')
            return self._partner_public_key

        return None

    def _get_signable_data(self, dto: AutomationBlueprintDTO) -> Dict[str, Any]:
        """
        Extrae los campos firmables de un DTO para verificación.

        Args:
            dto: DTO de automatización.

        Returns:
            Dict con solo los campos que fueron firmados por el servidor.
        """
        data = dto.model_dump() if hasattr(dto, 'model_dump') else dto.dict()
        return {k: v for k, v in data.items() if k in self.SIGNABLE_FIELDS}

    async def verify_signature(
        self,
        dto: AutomationBlueprintDTO,
        raise_on_failure: bool = True
    ) -> bool:
        """
        Verifica la firma criptográfica de un blueprint descargado.

        Args:
            dto: DTO de automatización con firma.
            raise_on_failure: Si True, lanza SignatureVerificationError en fallo.

        Returns:
            bool: True si la firma es válida.

        Raises:
            SignatureVerificationError: Si la firma es inválida y raise_on_failure=True.
        """
        # Si no hay firma, depende de la política
        if not dto.signature:
            logger.warning(f"Blueprint '{dto.id}' sin firma - posible modo desarrollo")
            if raise_on_failure:
                raise SignatureVerificationError(
                    f"El blueprint '{dto.id}' no tiene firma criptográfica. "
                    "No se puede verificar su autenticidad."
                )
            return False

        # Obtener clave pública
        public_key = await self._get_partner_public_key()

        if not public_key:
            logger.warning("No hay clave pública del Partner configurada")
            if raise_on_failure:
                raise SignatureVerificationError(
                    "No se puede verificar la firma: clave pública del Partner no configurada. "
                    "Configure la clave en Ajustes > Conexión al Servidor."
                )
            return False

        # Extraer datos firmables y serializar canónicamente
        signable_data = self._get_signable_data(dto)
        canonical_payload = RSASigner.canonicalize_json(signable_data)

        try:
            is_valid = self._signer.verify_signature(
                payload=canonical_payload,
                signature_b64=dto.signature,
                public_key_pem=public_key
            )
        except InvalidKeyError as e:
            logger.error(f"Clave pública inválida: {e}")
            if raise_on_failure:
                raise SignatureVerificationError(
                    f"La clave pública del Partner es inválida: {e}"
                ) from e
            return False
        except ValueError as e:
            logger.error(f"Firma malformada: {e}")
            if raise_on_failure:
                raise SignatureVerificationError(
                    f"La firma del blueprint '{dto.id}' está malformada: {e}"
                ) from e
            return False

        if not is_valid:
            logger.error(
                f"[SECURITY] Firma inválida para blueprint '{dto.id}'. "
                "El contenido puede haber sido alterado."
            )
            if raise_on_failure:
                raise SignatureVerificationError(
                    f"ALERTA DE SEGURIDAD: La firma del blueprint '{dto.id}' es inválida. "
                    "El contenido puede haber sido alterado en tránsito o no proviene "
                    "del servidor autorizado. La instalación ha sido bloqueada."
                )
            return False

        logger.info(f"Firma verificada correctamente para blueprint '{dto.id}'")
        return True

    def calculate_hash(self, content: str) -> str:
        """Calcula el hash SHA256 del contenido para control de versiones local."""
        return hashlib.sha256(content.encode()).hexdigest()

    async def save_local(
        self,
        dto: AutomationBlueprintDTO,
        skip_verification: bool = False
    ) -> LocalAutomation:
        """
        Guarda o actualiza una automatización sincronizada en la base de datos local.

        IMPORTANTE: Antes de persistir, verifica la firma criptográfica del servidor
        para garantizar la integridad y autenticidad del contenido.

        Args:
            dto: Objeto de transferencia de datos con la información del automatismo.
            skip_verification: Si True, omite la verificación de firma (solo desarrollo).

        Returns:
            Instancia de LocalAutomation persistida.

        Raises:
            SignatureVerificationError: Si la firma es inválida o está ausente.
        """
        # 1. Verificar firma criptográfica (OBLIGATORIO en producción)
        if not skip_verification:
            await self.verify_signature(dto, raise_on_failure=True)

        now = datetime.now(timezone.utc)
        current = await self.session.get(LocalAutomation, dto.id)

        if current:
            # Update
            current.name = dto.name
            current.code_content = dto.code_content
            current.version = dto.version
            current.updated_at = now
            current.signature = dto.signature
            current.type = dto.type
            current.local_status = "synced"
            current.last_synced_at = now

            self.session.add(current)
            await self.session.commit()
            await self.session.refresh(current)
            logger.info(f"Blueprint '{dto.id}' actualizado localmente (v{dto.version})")
            return current
        else:
            # Create
            new_item = LocalAutomation(
                id=dto.id,
                name=dto.name,
                type=dto.type,
                code_content=dto.code_content,
                version=dto.version,
                updated_at=now,
                signature=dto.signature,
                is_system=dto.is_system_template,
                local_status="synced",
                last_synced_at=now
            )
            self.session.add(new_item)
            await self.session.commit()
            await self.session.refresh(new_item)
            logger.info(f"Blueprint '{dto.id}' guardado localmente (v{dto.version})")
            return new_item

    async def get_local_item(self, item_id: str) -> Optional[LocalAutomation]:
        """Recupera una automatización local por su identificador único."""
        return await self.session.get(LocalAutomation, item_id)

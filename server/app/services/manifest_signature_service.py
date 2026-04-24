"""
Servicio de Firma de Manifiestos para AutomatIA Server.

Proporciona firmas RSA para los manifiestos de automatizaciones (scripts y workflows)
que se distribuyen a través de la biblioteca central. Garantiza la integridad y
autenticidad de los activos antes de su distribución a los clientes.
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from automatia_shared.crypto_utils import RSASigner, InvalidKeyError

# Configurar logger específico para auditoría de firmas
logger = logging.getLogger("automatia.security.signatures")


class SignatureConfigError(Exception):
    """Error de configuración del servicio de firmas (clave no disponible, etc.)."""

    pass


class ManifestSignatureService:
    """
    Servicio para firmar manifiestos de automatizaciones con RSA.

    La clave privada del Partner/Sistema se obtiene de la variable de entorno
    AUTOMATIA_SIGNING_KEY. En producción, esta clave debe ser gestionada
    de forma segura (AWS KMS, HashiCorp Vault, etc.).

    Uso:
        service = ManifestSignatureService()
        signature = service.sign_manifest(manifest_dict)
    """

    # Variable de entorno para la clave privada PEM
    SIGNING_KEY_ENV = "AUTOMATIA_SIGNING_KEY"

    def __init__(self):
        """Inicializa el servicio."""
        self._signer = RSASigner()
        self._private_key: Optional[bytes] = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Garantiza que la clave esté cargada antes de su uso."""
        if not self._initialized:
            self._load_signing_key()
            self._initialized = True

    def _load_signing_key(self) -> None:
        """
        Carga la clave privada desde la variable de entorno.

        La clave debe estar en formato PEM. Los saltos de línea pueden estar
        codificados como '\\n' literal en la variable de entorno.
        """
        key_data = os.environ.get(self.SIGNING_KEY_ENV)

        if key_data:
            # Normalizar saltos de línea (algunos sistemas usan \\n literal)
            key_data = key_data.replace("\\n", "\n")
            self._private_key = key_data.encode("utf-8")
            logger.info("Clave de firma cargada desde variable de entorno")
        else:
            logger.warning(
                f"Variable de entorno {self.SIGNING_KEY_ENV} no configurada. "
                "El servicio de firmas funcionará en modo degradado (sin firmar)."
            )

    @property
    def is_configured(self) -> bool:
        """Indica si el servicio tiene una clave de firma configurada."""
        self._ensure_initialized()
        return self._private_key is not None

    def sign_manifest(self, manifest_dict: Dict[str, Any]) -> Optional[str]:
        """
        Firma un diccionario de manifiesto y retorna la firma Base64.

        El manifiesto se serializa de forma canónica (sort_keys=True, sin espacios)
        antes de firmar para garantizar consistencia.

        Args:
            manifest_dict: Diccionario con los datos del manifiesto a firmar.
                          Debe contener al menos 'id' y 'code_content'.

        Returns:
            str: Firma RSA en formato Base64, o None si el servicio no está configurado.

        Raises:
            SignatureConfigError: Si la clave privada está corrupta o es inválida.
            ValueError: Si el manifiesto está vacío o es inválido.
        """
        if not manifest_dict:
            raise ValueError("El manifiesto no puede estar vacío")

        self._ensure_initialized()

        if not self.is_configured:
            logger.warning(
                f"Intento de firma sin clave configurada. "
                f"Manifest ID: {manifest_dict.get('id', 'unknown')}"
            )
            return None

        try:
            # Serialización canónica para firma consistente
            canonical_payload = RSASigner.canonicalize_json(manifest_dict)

            # Firmar
            signature = self._signer.sign_payload(canonical_payload, self._private_key)

            # Log de auditoría
            self._log_signature_event(
                manifest_id=manifest_dict.get("id", "unknown"),
                manifest_name=manifest_dict.get("name", "unknown"),
                manifest_type=manifest_dict.get("type", "unknown"),
                partner_id=manifest_dict.get("partner_id"),
                success=True,
            )

            return signature

        except InvalidKeyError as e:
            logger.error(f"Clave privada inválida: {e}")
            self._log_signature_event(
                manifest_id=manifest_dict.get("id", "unknown"),
                manifest_name=manifest_dict.get("name", "unknown"),
                manifest_type=manifest_dict.get("type", "unknown"),
                partner_id=manifest_dict.get("partner_id"),
                success=False,
                error=str(e),
            )
            raise SignatureConfigError(f"Clave de firma inválida: {e}") from e

        except Exception as e:
            logger.error(f"Error inesperado al firmar manifiesto: {e}")
            self._log_signature_event(
                manifest_id=manifest_dict.get("id", "unknown"),
                manifest_name=manifest_dict.get("name", "unknown"),
                manifest_type=manifest_dict.get("type", "unknown"),
                partner_id=manifest_dict.get("partner_id"),
                success=False,
                error=str(e),
            )
            raise

    def _log_signature_event(
        self,
        manifest_id: str,
        manifest_name: str,
        manifest_type: str,
        partner_id: Optional[str],
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """
        Registra un evento de firma en el log de auditoría.

        Formato estructurado para facilitar análisis y alertas en sistemas
        de monitoreo (ELK, CloudWatch, etc.).
        """
        event = {
            "event_type": "MANIFEST_SIGNATURE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "manifest_id": manifest_id,
            "manifest_name": manifest_name,
            "manifest_type": manifest_type,
            "partner_id": partner_id or "system",
            "status": "SUCCESS" if success else "FAILED",
        }

        if error:
            event["error"] = error

        if success:
            logger.info(
                f"[AUDIT] Manifiesto firmado: {manifest_name} (ID: {manifest_id}) "
                f"por Partner: {partner_id or 'system'}"
            )
        else:
            logger.error(
                f"[AUDIT] Error al firmar manifiesto: {manifest_name} (ID: {manifest_id}) "
                f"- Error: {error}"
            )

    def get_signable_fields(self, full_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrae los campos relevantes para la firma de un diccionario completo.

        Solo se firman los campos que definen el contenido y comportamiento
        del automatismo, excluyendo metadatos volátiles como timestamps.

        Args:
            full_data: Diccionario completo con todos los datos del item.

        Returns:
            Dict con solo los campos que deben ser firmados.
        """
        signable_keys = {
            "id",
            "name",
            "type",
            "code_content",
            "version",
            "is_workflow",
            "partner_id",
            "client_id",
            "is_system_template",
        }

        return {k: v for k, v in full_data.items() if k in signable_keys}


# Instancia singleton para uso en la aplicación
manifest_signature_service = ManifestSignatureService()


__all__ = [
    "ManifestSignatureService",
    "manifest_signature_service",
    "SignatureConfigError",
]

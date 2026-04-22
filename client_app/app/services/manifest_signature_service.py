"""
Servicio de firma de manifiesto para paquetes de automatismos.
Prompt 1.3 del sistema de exportación/importación de automatismos.

La firma se aplica SOLO al manifest.json, no a cada archivo individual.
El manifiesto contiene los hashes de todos los archivos del paquete.

Dos tipos de firma:
- HMAC-SHA256 para cliente (usando license_key + machine_id)
- RSA para partner (requiere servidor Brain)
"""

import hashlib
import hmac
from datetime import datetime
from typing import Dict


class ManifestSignatureService:
    """
    Servicio para firmar y verificar manifiestos de paquetes.

    Firma de cliente (HMAC):
    - Usa clave derivada de license_key + machine_id
    - Permite verificación sin conexión al servidor
    - Adecuada para exportar/importar dentro de la misma licencia

    Firma de partner (RSA):
    - Requiere comunicación con servidor Brain
    - Usa clave privada del partner almacenada en servidor
    - Necesaria para transferencias entre diferentes licencias
    """

    def derive_client_key(self, license_key: str, machine_id: str) -> bytes:
        """
        Deriva clave HMAC de credenciales del cliente.

        La clave se genera usando SHA256 de 'license_key:machine_id'.
        Esto garantiza que:
        - La clave es única por combinación de licencia y máquina
        - Es determinista (mismas credenciales = misma clave)
        - Tiene longitud adecuada para HMAC-SHA256 (32 bytes)

        Args:
            license_key: Clave de licencia del cliente
            machine_id: ID único de la máquina

        Returns:
            bytes: Clave de 32 bytes para usar con HMAC-SHA256
        """
        combined = f"{license_key}:{machine_id}"
        return hashlib.sha256(combined.encode()).digest()

    def _get_timestamp(self) -> str:
        """
        Obtiene timestamp actual en formato ISO.

        Método separado para facilitar testing con mocks.

        Returns:
            str: Timestamp ISO sin microsegundos
        """
        return datetime.utcnow().replace(microsecond=0).isoformat()

    def sign_as_client(
        self,
        manifest_json: str,
        license_key: str,
        machine_id: str
    ) -> Dict[str, str]:
        """
        Firma el manifiesto como cliente usando HMAC-SHA256.

        El proceso de firma:
        1. Deriva clave HMAC de las credenciales del cliente
        2. Genera timestamp actual
        3. Concatena manifest_json + '|' + timestamp
        4. Calcula HMAC-SHA256 del contenido concatenado

        La firma incluye el timestamp para:
        - Prevenir ataques de replay
        - Registrar momento de la firma
        - Permitir validación de antigüedad del paquete

        Args:
            manifest_json: JSON string del manifiesto a firmar
            license_key: Clave de licencia del cliente
            machine_id: ID único de la máquina

        Returns:
            dict: Datos de la firma con estructura:
                {
                    "type": "CLIENT",
                    "algorithm": "HMAC-SHA256",
                    "value": "<firma hexadecimal>",
                    "timestamp": "<ISO timestamp>"
                }
        """
        key = self.derive_client_key(license_key, machine_id)
        timestamp = self._get_timestamp()

        # Concatenar manifest con timestamp para incluir en firma
        data_to_sign = f"{manifest_json}|{timestamp}"
        signature = hmac.new(key, data_to_sign.encode(), hashlib.sha256).hexdigest()

        return {
            "type": "CLIENT",
            "algorithm": "HMAC-SHA256",
            "value": signature,
            "timestamp": timestamp
        }

    def verify_client_signature(
        self,
        manifest_json: str,
        signature_data: Dict[str, str],
        license_key: str,
        machine_id: str
    ) -> bool:
        """
        Verifica firma de cliente.

        El proceso de verificación:
        1. Deriva la misma clave HMAC de las credenciales
        2. Reconstruye el contenido firmado (manifest + timestamp)
        3. Calcula HMAC-SHA256 esperado
        4. Compara con el valor de firma proporcionado

        Usa hmac.compare_digest para comparación segura contra
        ataques de timing.

        Args:
            manifest_json: JSON string del manifiesto a verificar
            signature_data: Datos de la firma (del método sign_as_client)
            license_key: Clave de licencia del cliente
            machine_id: ID único de la máquina

        Returns:
            bool: True si la firma es válida, False en caso contrario
        """
        key = self.derive_client_key(license_key, machine_id)

        # Reconstruir el contenido que fue firmado
        timestamp = signature_data.get("timestamp", "")
        data_to_verify = f"{manifest_json}|{timestamp}"

        # Calcular firma esperada
        expected = hmac.new(key, data_to_verify.encode(), hashlib.sha256).hexdigest()

        # Comparación segura contra timing attacks
        return hmac.compare_digest(expected, signature_data.get("value", ""))

    async def sign_as_partner(
        self,
        manifest_json: str,
        partner_id: str
    ) -> Dict[str, str]:
        """
        Firma el manifiesto como partner usando RSA via Brain Server.

        El servidor Brain custodia la clave privada del partner y genera la firma.
        """
        if not manifest_json:
            raise ValueError("Manifest JSON cannot be empty")

        try:
            from client_app.app.clients.brain_client import BrainAPIClient
            from client_app.app.database.models import ServerConnection
            from client_app.app.database.db import client_engine
            from sqlmodel.ext.asyncio.session import AsyncSession
            from sqlmodel import select

            async with AsyncSession(client_engine) as session:
                result = await session.exec(
                    select(ServerConnection).where(ServerConnection.is_active == True)
                )
                connection = result.first()
                brain_url = connection.brain_url if connection else "http://localhost:8000"
                license_key = connection.license_key if connection else "TRIAL-KEY"

            client = BrainAPIClient(base_url=brain_url)
            
            response = await client.post_generic(
                "/api/v1/library/sign_manifest",
                json_data={
                    "manifest_json": manifest_json,
                    "partner_id": partner_id
                },
                license_key=license_key
            )
            
            if "signature" not in response:
                raise ValueError("Server response missing signature")
                
            return {
                "type": "PARTNER",
                "value": response["signature"],
                "algorithm": response.get("algorithm", "RSA-SHA256"),
                "key_id": response.get("key_id", "default"),
                "timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            logger.error(f"Error signing as partner: {e}")
            raise ValueError(f"Failed to sign manifest: {e}")

    async def verify_partner_signature(
        self,
        manifest_json: str,
        signature_data: Dict[str, str],
        partner_id: str
    ) -> bool:
        """
        Verifica firma de partner consultando al servidor Brain.

        Requiere comunicación con servidor Brain para verificar la firma RSA.
        """
        if not manifest_json or not signature_data:
            return False

        try:
            from client_app.app.clients.brain_client import BrainAPIClient
            from client_app.app.database.models import ServerConnection
            from client_app.app.database.db import client_engine
            from sqlmodel.ext.asyncio.session import AsyncSession
            from sqlmodel import select

            async with AsyncSession(client_engine) as session:
                result = await session.exec(
                    select(ServerConnection).where(ServerConnection.is_active == True)
                )
                connection = result.first()
                brain_url = connection.brain_url if connection else "http://localhost:8000"
                license_key = connection.license_key if connection else "TRIAL-KEY"

            client = BrainAPIClient(base_url=brain_url)
            
            response = await client.post_generic(
                "/api/v1/library/verify_manifest",
                json_data={
                    "manifest_json": manifest_json,
                    "signature": signature_data.get("value") or signature_data.get("signature"),
                    "partner_id": partner_id,
                    "algorithm": signature_data.get("algorithm", "RSA-SHA256"),
                    "key_id": signature_data.get("key_id", "default")
                },
                license_key=license_key
            )
            
            return response.get("valid", False)
            
        except Exception as e:
            logger.error(f"Error verifying partner signature: {e}")
            return False


# Singleton del servicio
manifest_signature_service = ManifestSignatureService()

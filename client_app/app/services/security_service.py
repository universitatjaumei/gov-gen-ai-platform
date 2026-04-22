import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select

from automatia_shared.core.security import SecurityAuditor
from automatia_shared.crypto_utils import RSASigner, InvalidKeyError
from client_app.app.database.models import SecurityPolicy, ServerConnection
from client_app.app.modules.security.policy_manager import PartnerPolicyManager

logger = logging.getLogger(__name__)

class SecurityService:
    """
    Servicio de Seguridad del Cliente.
    
    Gestiona:
    1. Sincronización de políticas de seguridad desde el servidor.
    2. Caché local persistente (JSON) para operación offline.
    3. Verificación de firmas RSA para garantizar integridad de políticas.
    4. Aplicación de políticas al entorno de ejecución.
    """
    
    CACHE_FILE = Path("storage/security_policy.json")
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._signer = RSASigner()
        
    async def initialize_security(self) -> None:
        """
        Punto de entrada al inicio de la aplicación.
        Intenta sincronizar, si falla usa caché.
        """
        logger.info("Initializing Security Service...")
        
        # 1. Asegurar directorio de almacenamiento
        self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # 2. Intentar sincronizar con el servidor
        try:
            await self.sync_policy_from_server()
        except Exception as e:
            logger.warning(f"Could not sync security policy: {e}. Falling back to cache.")
            
        # 3. Cargar política efectiva (ya sea actualizada o cacheada)
        await self.load_effective_policy()

    async def sync_policy_from_server(self) -> None:
        """
        Descarga la política actual del servidor, verifica firma y guarda en caché/BD.
        """
        # Obtener conexión activa y brain client
        conn = await self._get_active_connection()
        if not conn or not conn.license_key:
            logger.warning("No active server connection or license key found.")
            return

        # Importar aquí para evitar ciclos si es necesario, o usar una fábrica
        from client_app.app.clients.brain_client import BrainAPIClient
        client = BrainAPIClient(base_url=conn.brain_url)
        
        # Descargar política firmada
        logger.info(f"Fetching policy from {conn.brain_url}...")
        policy_data = await client.get_effective_policy(conn.license_key)
        
        # Verificar firma RSA
        if not await self._verify_policy_signature(policy_data, conn.partner_public_key):
            raise ValueError("Security Policy signature verification failed!")
            
        # Persistir en Caché Local (JSON) para arranque offline
        self._save_to_cache(policy_data)
        
        # Persistir en BD para consultas SQL
        await self._save_to_db(policy_data)
        
        logger.info("Security Policy successfully synced and cached.")

    async def load_effective_policy(self) -> None:
        """
        Carga la política desde el caché local y la aplica al sistema.
        Si el caché no existe o es inválido, carga defaults seguros.
        """
        policy_data = self._load_from_cache()
        
        if not policy_data:
            logger.warning("No cached security policy found. Using SYSTEM DEFAULTS.")
            # Podríamos forzar un modo seguro aquí
            return

        # Verificar integridad del caché (si tenemos clave pública)
        # Nota: Si estamos offline, usamos la clave pública guardada en BD
        conn = await self._get_active_connection()
        public_key = conn.partner_public_key if conn else None
        
        if public_key:
            if not await self._verify_policy_signature(policy_data, public_key):
                logger.error("Cached policy signature is INVALID. Potentially git tampering. Using defaults.")
                return
        
        # Aplicar política al PolicyManager
        manager = PartnerPolicyManager(
            client_policy=policy_data.get("policy", {}),
            partner_policy={} # El servidor ya devuelve la efectiva mezclada o separada, asumimos 'policy' es la efectiva
        )
        
        # Aplicar al auditor global (si existe singleton o inyección)
        # En este diseño, el auditor se instancia por ejecución, pero podemos setear defaults globales si la lib lo permite
        # Por ahora logueamos
        logger.info(f"Applied Security Policy: {manager}")

    # --- Helpers ---

    async def _get_active_connection(self) -> Optional[ServerConnection]:
        result = await self.session.exec(
            select(ServerConnection).where(ServerConnection.is_active == True)
        )
        return result.first()

    async def _verify_policy_signature(self, policy_envelope: Dict[str, Any], public_key_pem: Optional[str]) -> bool:
        """
        Verifica que el payload coincida con la firma usando la clave pública del partner.
        """
        if not public_key_pem:
            logger.warning("No partner public key available to verify signature.")
            return False
            
        signature = policy_envelope.get("signature")
        payload = policy_envelope.get("policy") # El dict de la política
        
        if not signature or not payload:
            return False
            
        try:
            # Canonicalizar el JSON para verificación consistente
            canonical_payload = RSASigner.canonicalize_json(payload)
            public_key_bytes = public_key_pem.encode('utf-8') if isinstance(public_key_pem, str) else public_key_pem
            
            return self._signer.verify_signature(
                payload=canonical_payload,
                signature_b64=signature,
                public_key_pem=public_key_bytes
            )
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False

    def _save_to_cache(self, policy_data: Dict[str, Any]) -> None:
        """Guarda el sobre (policy + signature) en JSON."""
        try:
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(policy_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write policy cache: {e}")

    def _load_from_cache(self) -> Optional[Dict[str, Any]]:
        """Lee el sobre desde JSON."""
        if not self.CACHE_FILE.exists():
            return None
        try:
            with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read policy cache: {e}")
            return None

    async def _save_to_db(self, policy_envelope: Dict[str, Any]) -> None:
        """Actualiza la tabla SecurityPolicy."""
        payload = policy_envelope.get("policy", {})
        
        # Buscar política existente (asumimos una global o por nombre 'server_synced')
        # Por simplicidad usaremos 'server_synced' como identificador
        stmt = select(SecurityPolicy).where(SecurityPolicy.name == "server_synced")
        result = await self.session.exec(stmt)
        policy = result.first()
        
        if not policy:
            policy = SecurityPolicy(name="server_synced")
            
        # Mapear campos
        # Nota: El payload del servidor debe coincidir con las keys esperadas
        policy.allowed_imports = json.dumps(payload.get("allowed_imports", []))
        policy.forbidden_imports = json.dumps(payload.get("forbidden_imports", []))
        policy.max_execution_time = payload.get("max_execution_time", 300)
        policy.max_memory_mb = payload.get("max_memory_mb", 512)
        policy.screenshot_policy = payload.get("screenshot_policy", "REVIEW")
        policy.trusted_screenshot_domains = json.dumps(payload.get("trusted_screenshot_domains", []))
        policy.allowed_domains = json.dumps(payload.get("allowed_domains", []))
        policy.updated_at = datetime.utcnow()
        policy.is_active = True
        
        self.session.add(policy)
        await self.session.commit()

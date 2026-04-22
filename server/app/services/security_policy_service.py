"""
Servicio de gestión de políticas de seguridad.
Implementa la lógica de cascada: CLIENT > PARTNER > SYSTEM
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.database.models import (
    ServerSecurityPolicy as SecurityPolicy, ClientAccount, PartnerAccount
)


class SecurityPolicyService:
    """
    Gestor de políticas de seguridad y cumplimiento normativo.

    Implementa un sistema de resolución en cascada donde el nivel más 
    específico sobreescribe al general:
    1. CLIENT - Restricciones específicas para un cliente final.
    2. PARTNER - Políticas aplicadas a toda la base instalada de un Partner.
    3. SYSTEM - Configuración "Hardened" por defecto del sistema.
    """

    # Valores por defecto del sistema
    SYSTEM_DEFAULTS = {
        "allowed_domains": '["*"]',
        "allowed_libraries": '["pandas", "json", "re", "math", "datetime", "openpyxl", "xlrd", "numpy"]',
        "forbidden_libraries": '["os", "sys", "subprocess", "requests", "socket", "shutil", "ctypes"]',
        "max_execution_time": 300,
        "max_memory_mb": 512,
    }

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_system_policy(self) -> SecurityPolicy:
        """
        Obtiene la política global del sistema (SYSTEM).
        
        Si no existe, la inicializa automáticamente con los valores predefinidos 
        de alta seguridad (Hardened Defaults).

        Returns:
            SecurityPolicy: La instancia de la política global.
        """
        stmt = select(SecurityPolicy).where(
            SecurityPolicy.scope == "SYSTEM",
            SecurityPolicy.is_active == True
        )
        result = await self.db.exec(stmt)
        policy = result.first()

        if not policy:
            # Crear política SYSTEM por defecto
            policy = SecurityPolicy(
                scope="SYSTEM",
                partner_id=None,
                client_id=None,
                allowed_domains=self.SYSTEM_DEFAULTS["allowed_domains"],
                allowed_libraries=self.SYSTEM_DEFAULTS["allowed_libraries"],
                forbidden_libraries=self.SYSTEM_DEFAULTS["forbidden_libraries"],
                max_execution_time=self.SYSTEM_DEFAULTS["max_execution_time"],
                max_memory_mb=self.SYSTEM_DEFAULTS["max_memory_mb"],
                is_active=True
            )
            self.db.add(policy)
            await self.db.commit()
            await self.db.refresh(policy)

        return policy

    async def get_partner_policy(self, partner_id: str) -> Optional[SecurityPolicy]:
        """
        Obtiene la política específica de un partner (si existe).
        """
        stmt = select(SecurityPolicy).where(
            SecurityPolicy.scope == "PARTNER",
            SecurityPolicy.partner_id == partner_id,
            SecurityPolicy.is_active == True
        )
        result = await self.db.exec(stmt)
        return result.first()

    async def get_client_policy(self, client_id: str) -> Optional[SecurityPolicy]:
        """
        Obtiene la política específica de un cliente (si existe).
        """
        stmt = select(SecurityPolicy).where(
            SecurityPolicy.scope == "CLIENT",
            SecurityPolicy.client_id == client_id,
            SecurityPolicy.is_active == True
        )
        result = await self.db.exec(stmt)
        return result.first()

    async def get_effective_policy(self, client_id: str) -> Dict[str, Any]:
        """
        Calcula la política de seguridad efectiva aplicando la jerarquía de cascada.
        
        Prioridad descendente: Política de Cliente -> Política de Partner -> Sistema.

        Args:
            client_id: Identificador del cliente para el cual resolver la política.

        Returns:
            Dict[str, Any]: Diccionario con parámetros de seguridad y nivel de aplicación.
        """
        # Intentar obtener política del cliente
        client_policy = await self.get_client_policy(client_id)
        if client_policy:
            return self._policy_to_dict(client_policy, "CLIENT")

        # Obtener el partner del cliente
        client = await self.db.get(ClientAccount, client_id)
        if client and client.partner_id:
            # Intentar obtener política del partner
            partner_policy = await self.get_partner_policy(client.partner_id)
            if partner_policy:
                return self._policy_to_dict(partner_policy, "PARTNER")

        # Fallback a política del sistema
        system_policy = await self.get_system_policy()
        return self._policy_to_dict(system_policy, "SYSTEM")

    async def get_effective_policy_for_partner(self, partner_id: str) -> Dict[str, Any]:
        """
        Obtiene la política efectiva para un partner (sin cliente específico).
        Orden: PARTNER > SYSTEM
        """
        partner_policy = await self.get_partner_policy(partner_id)
        if partner_policy:
            return self._policy_to_dict(partner_policy, "PARTNER")

        system_policy = await self.get_system_policy()
        return self._policy_to_dict(system_policy, "SYSTEM")

    def _policy_to_dict(self, policy: SecurityPolicy, applied_level: str) -> Dict[str, Any]:
        """Convierte una política a diccionario con metadatos."""
        return {
            "id": policy.id,
            "scope": policy.scope,
            "applied_level": applied_level,
            "partner_id": policy.partner_id,
            "client_id": policy.client_id,
            "allowed_domains": self._parse_json(policy.allowed_domains),
            "allowed_libraries": self._parse_json(policy.allowed_libraries),
            "forbidden_libraries": self._parse_json(policy.forbidden_libraries),
            "max_execution_time": policy.max_execution_time,
            "max_memory_mb": policy.max_memory_mb,
            "screenshot_policy": getattr(policy, "screenshot_policy", "REVIEW"),
            "trusted_screenshot_domains": self._parse_json(getattr(policy, "trusted_screenshot_domains", "[]")),
            "is_active": policy.is_active,
            "created_at": policy.created_at.isoformat() if policy.created_at else None,
            "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
        }

    def _parse_json(self, value: str) -> List[str]:
        """Parse JSON string to list safely."""
        try:
            return json.loads(value) if value else []
        except (json.JSONDecodeError, TypeError):
            return []

    async def save_system_policy(self, allowed_domains: List[str], allowed_libraries: List[str], forbidden_libraries: List[str], max_execution_time: int, max_memory_mb: int, screenshot_policy: str = "REVIEW", trusted_screenshot_domains: List[str] = []) -> SecurityPolicy:
        """
        Actualiza los parámetros globales de seguridad del sistema.

        Args:
            allowed_domains: Lista blanca de dominios para navegación.
            allowed_libraries: Librerías Python permitidas en scripts.
            forbidden_libraries: Librerías Python estrictamente prohibidas.
            max_execution_time: Tiempo máximo de ejecución en segundos.
            max_memory_mb: Límite de memoria RAM permitida.
            screenshot_policy: Política de capturas de pantalla (REVIEW/AUTO).
            trusted_screenshot_domains: Dominios donde AUTO-screenshot está permitido.

        Returns:
            SecurityPolicy: Instancia actualizada.
        """
        policy = await self.get_system_policy()

        policy.allowed_domains = json.dumps(allowed_domains)
        policy.allowed_libraries = json.dumps(allowed_libraries)
        policy.forbidden_libraries = json.dumps(forbidden_libraries)
        policy.max_execution_time = max_execution_time
        policy.max_memory_mb = max_memory_mb
        policy.screenshot_policy = screenshot_policy
        policy.trusted_screenshot_domains = json.dumps(trusted_screenshot_domains)
        policy.updated_at = datetime.utcnow()

        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def save_partner_policy(
        self,
        partner_id: str,
        allowed_domains: List[str],
        allowed_libraries: List[str],
        forbidden_libraries: List[str],
        max_execution_time: int,
        max_memory_mb: int,
        screenshot_policy: str = "REVIEW",
        trusted_screenshot_domains: List[str] = []
    ) -> SecurityPolicy:
        """
        Crea o actualiza la política de un partner.
        """
        policy = await self.get_partner_policy(partner_id)

        if not policy:
            policy = SecurityPolicy(
                scope="PARTNER",
                partner_id=partner_id,
                client_id=None
            )

        policy.allowed_domains = json.dumps(allowed_domains)
        policy.allowed_libraries = json.dumps(allowed_libraries)
        policy.forbidden_libraries = json.dumps(forbidden_libraries)
        policy.max_execution_time = max_execution_time
        policy.max_memory_mb = max_memory_mb
        policy.screenshot_policy = screenshot_policy
        policy.trusted_screenshot_domains = json.dumps(trusted_screenshot_domains)
        policy.updated_at = datetime.utcnow()
        policy.is_active = True

        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def save_client_policy(
        self,
        client_id: str,
        partner_id: str,
        allowed_domains: List[str],
        allowed_libraries: List[str],
        forbidden_libraries: List[str],
        max_execution_time: int,
        max_memory_mb: int,
        screenshot_policy: str = "REVIEW",
        trusted_screenshot_domains: List[str] = []
    ) -> SecurityPolicy:
        """
        Crea o actualiza la política de un cliente.
        """
        policy = await self.get_client_policy(client_id)

        if not policy:
            policy = SecurityPolicy(
                scope="CLIENT",
                partner_id=partner_id,
                client_id=client_id
            )

        policy.allowed_domains = json.dumps(allowed_domains)
        policy.allowed_libraries = json.dumps(allowed_libraries)
        policy.forbidden_libraries = json.dumps(forbidden_libraries)
        policy.max_execution_time = max_execution_time
        policy.max_memory_mb = max_memory_mb
        policy.screenshot_policy = screenshot_policy
        policy.trusted_screenshot_domains = json.dumps(trusted_screenshot_domains)
        policy.updated_at = datetime.utcnow()
        policy.is_active = True

        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def delete_policy(self, policy_id: int) -> bool:
        """
        Elimina una política (soft delete via is_active=False).
        No permite eliminar la política SYSTEM.
        """
        policy = await self.db.get(SecurityPolicy, policy_id)
        if not policy:
            return False

        if policy.scope == "SYSTEM":
            return False  # No se puede eliminar la política del sistema

        policy.is_active = False
        policy.updated_at = datetime.utcnow()
        self.db.add(policy)
        await self.db.commit()
        return True

    async def get_all_partner_policies(self) -> List[Dict[str, Any]]:
        """
        Obtiene todas las políticas de partners activas.
        Para uso en el panel de admin.
        """
        stmt = select(SecurityPolicy).where(
            SecurityPolicy.scope == "PARTNER",
            SecurityPolicy.is_active == True
        )
        result = await self.db.exec(stmt)
        policies = result.all()

        output = []
        for p in policies:
            partner = await self.db.get(PartnerAccount, p.partner_id)
            output.append({
                **self._policy_to_dict(p, "PARTNER"),
                "partner_name": partner.name if partner else "Unknown"
            })
        return output

    async def get_partner_client_policies(self, partner_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene todas las políticas de clientes de un partner.
        """
        stmt = select(SecurityPolicy).where(
            SecurityPolicy.scope == "CLIENT",
            SecurityPolicy.partner_id == partner_id,
            SecurityPolicy.is_active == True
        )
        result = await self.db.exec(stmt)
        policies = result.all()

        output = []
        for p in policies:
            client = await self.db.get(ClientAccount, p.client_id)
            output.append({
                **self._policy_to_dict(p, "CLIENT"),
                "client_name": client.name if client else "Unknown"
            })
        return output

    async def get_clients_with_policy_status(self, partner_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene todos los clientes de un partner con info de su política.
        Indica si tienen política propia o heredada.
        """
        # Obtener todos los clientes del partner
        stmt = select(ClientAccount).where(
            ClientAccount.partner_id == partner_id,
            ClientAccount.is_active == True
        )
        result = await self.db.exec(stmt)
        clients = result.all()

        # Verificar política del partner
        partner_policy = await self.get_partner_policy(partner_id)

        output = []
        for client in clients:
            client_policy = await self.get_client_policy(client.client_id)

            if client_policy:
                policy_level = "CLIENT"
                policy_id = client_policy.id
            elif partner_policy:
                policy_level = "PARTNER"
                policy_id = partner_policy.id
            else:
                policy_level = "SYSTEM"
                system_policy = await self.get_system_policy()
                policy_id = system_policy.id

            output.append({
                "client_id": client.client_id,
                "client_name": client.name,
                "has_custom_policy": client_policy is not None,
                "policy_level": policy_level,
                "policy_id": policy_id
            })

        return output

"""
Servicio de gestión de clientes (ClientAccounts) dentro de un Partner.

Implementa operaciones CRUD multi-inquilino (multi-tenant) donde todas las
solicitudes están aisladas por el `partner_id` del contexto.
"""

import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from server.app.database.models import ClientAccount, License
from automatia_shared.validators import hash_license_key


class PartnerClientService:
    """
    Controlador de operaciones para clientes finales de un Partner.

    Gestiona la creación de cuentas de cliente, la generación de sus claves
    de licencia y la visualización de estadísticas de consumo. Garantiza que
    un Partner solo pueda ver y modificar sus propios clientes.
    """

    def __init__(self, db_session: AsyncSession, partner_id: str):
        self.db = db_session
        self.partner_id = partner_id

    async def list_clients(self, include_inactive: bool = False) -> List[ClientAccount]:
        """
        Lista todos los clientes vinculados al Partner actual.

        Args:
            include_inactive: Si es True, incluye clientes con `is_active=False`.

        Returns:
            List[ClientAccount]: Lista de modelos de cliente encontrados.
        """
        stmt = select(ClientAccount).where(ClientAccount.partner_id == self.partner_id)
        if not include_inactive:
            stmt = stmt.where(ClientAccount.is_active)

        stmt = stmt.order_by(ClientAccount.created_at.desc())
        result = await self.db.exec(stmt)
        return result.all()

    async def get_client(self, client_id: str) -> Optional[ClientAccount]:
        """Obtener cliente por ID (solo si pertenece al partner)."""
        stmt = select(ClientAccount).where(
            ClientAccount.client_id == client_id,
            ClientAccount.partner_id == self.partner_id,
        )
        result = await self.db.exec(stmt)
        return result.first()

    async def create_client(
        self, client_id: str, name: str, license_key_raw: str, nif: Optional[str] = None
    ) -> ClientAccount:
        """
        Crea un nuevo cliente asignándolo explícitamente al Partner del servicio.

        Realiza el hashing de la clave de licencia antes de persistirla en la base de datos
        para garantizar la seguridad del secreto.

        Args:
            client_id: Identificador único deseado para el cliente.
            name: Nombre o razón social.
            license_key_raw: Clave de licencia pública (sin hashear) enviada al cliente.
            nif: Identificador fiscal (opcional).

        Returns:
            ClientAccount: La instancia del cliente creado.
        """
        hashed_key = hash_license_key(license_key_raw)

        client = ClientAccount(
            client_id=client_id,
            partner_id=self.partner_id,
            name=name,
            nif=nif,
            license_key=hashed_key,
            is_active=True,
        )

        self.db.add(client)
        await self.db.commit()
        await self.db.refresh(client)
        return client

    def _extract_partner_number(self, partner_id: str) -> str:
        """Extrae o genera un numero de 3 digitos para el partner."""
        import re

        # 1. Patrones conocidos
        patterns = [
            r"partner_(\d+)",  # partner_001
            r"ID_P_(\d+)",  # ID_P_005
            r"^(\d+)$",  # 042
        ]

        for p in patterns:
            match = re.search(p, partner_id)
            if match:
                num = match.group(1)
                # Tomar ultimos 3 digitos si es mas largo, o padding zero
                return f"{int(num):03d}"[-3:]

        # 2. Fallback determinista (hash)
        # abs(hash) % 1000 -> 000..999
        h = abs(hash(partner_id)) % 1000
        return f"{h:03d}"

    async def create_client_with_license(
        self,
        name: str,
        nif: Optional[str] = None,
        quota_tokens: int = 100000,
        valid_until: Optional[datetime] = None,
    ) -> Tuple[ClientAccount, License, str]:
        """
        Orquesta la creación de una cuenta de cliente junto con su licencia inicial.

        Calcula automáticamente IDs únicos basados en la jerarquía del partner,
        genera una clave aleatoria segura y establece las cuotas de consumo.

        Args:
            name: Nombre del cliente.
            nif: NIF/CIF (opcional).
            quota_tokens: Cantidad de tokens asignados de base.
            valid_until: Fecha de expiración (opcional, por defecto permanente).

        Returns:
            Tuple[ClientAccount, License, str]: (Cliente, Licencia, Clave pública).
        """

        # 1. Generate ID
        # Format: ID_C_{partner_num}_{seq}
        partner_num = self._extract_partner_number(self.partner_id)
        seq = 1
        while True:
            client_id = f"ID_C_{partner_num}_{seq:03d}"
            # Check ID availability globally (PK check)
            exists = await self.db.get(ClientAccount, client_id)
            if not exists:
                break
            seq += 1

        # 2. Generate Key
        license_key_raw = f"LIC-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"

        # 3. Create Client
        client = await self.create_client(client_id, name, license_key_raw, nif)

        # 4. Handle Validity
        if valid_until is None:
            # Permanent license (far future)
            valid_until = datetime(2099, 12, 31)

        # 5. Create License
        # Format: L_{client_id_suffix}
        # Example: ID_C_001_001 -> L_C_001_001
        # Example: client_partner_dev -> L_client_partner_dev

        if client_id.startswith("ID_"):
            license_id_suffix = client_id[3:]  # Strip "ID_"
        else:
            license_id_suffix = client_id

        formatted_license_id = f"L_{license_id_suffix}"

        license = License(
            license_id=formatted_license_id,
            client_id=client_id,
            quota_tokens=quota_tokens,
            consumed_tokens=0,
            valid_until=valid_until,
            status="ACTIVE",
        )
        self.db.add(license)
        await self.db.commit()
        await self.db.refresh(license)

        return client, license, license_key_raw

    async def update_client(self, client_id: str, **kwargs) -> Optional[ClientAccount]:
        """Actualizar cliente (solo si pertenece al partner)."""
        client = await self.get_client(client_id)
        if not client:
            return None

        for key, value in kwargs.items():
            if hasattr(client, key) and key not in ("client_id", "partner_id"):
                setattr(client, key, value)

        self.db.add(client)
        await self.db.commit()
        await self.db.refresh(client)
        return client

    async def deactivate_client(self, client_id: str) -> bool:
        """
        Desactiva un cliente y suspende automáticamente todas sus licencias activas.

        Utilizado para interrumpir el servicio por impago o rescisión de contrato
        sin eliminar físicamente los datos (Soft Delete).

        Args:
            client_id: ID del cliente a desactivar.

        Returns:
            bool: True si la operación se completó correctamente.
        """
        client = await self.get_client(client_id)
        if not client:
            return False

        client.is_active = False
        self.db.add(client)

        # Suspend licenses
        from automatia_shared.enums import LicenseStatus

        stmt = select(License).where(License.client_id == client_id)
        result = await self.db.exec(stmt)
        for lic in result.all():
            lic.status = LicenseStatus.SUSPENDED.value
            self.db.add(lic)

        await self.db.commit()
        return True

    async def reactivate_client(self, client_id: str) -> bool:
        """Reactivar cliente."""
        client = await self.get_client(client_id)
        if not client:
            return False

        client.is_active = True
        self.db.add(client)
        await self.db.commit()
        return True

    async def search_clients(self, query: str) -> List[ClientAccount]:
        """Buscar clientes por nombre."""
        stmt = select(ClientAccount).where(
            ClientAccount.partner_id == self.partner_id,
            ClientAccount.name.ilike(f"%{query}%"),
        )
        result = await self.db.exec(stmt)
        return result.all()

    async def regenerate_license_key(self, client_id: str) -> Tuple[str, str]:
        """Regenerar license key para un cliente."""
        client = await self.get_client(client_id)
        if not client:
            raise ValueError("Cliente no encontrado o no pertenece a este partner")

        # Generar nueva key
        new_key = f"LIC-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
        new_hash = hash_license_key(new_key)

        client.license_key = new_hash
        self.db.add(client)
        await self.db.commit()

        return new_key, new_hash

    async def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Obtener estadisticas basicas de un cliente."""
        client = await self.get_client(client_id)
        if not client:
            return None

        stmt = (
            select(License)
            .where(License.client_id == client_id)
            .where(License.status == "active")
        )
        result = await self.db.exec(stmt)
        license = result.first()

        if not license:
            return {"quota_tokens": 0, "consumed_tokens": 0, "usage_percent": 0.0}

        percent = 0.0
        if license.quota_tokens > 0:
            percent = (license.consumed_tokens / license.quota_tokens) * 100

        return {
            "quota_tokens": license.quota_tokens,
            "consumed_tokens": license.consumed_tokens,
            "usage_percent": round(percent, 2),
        }

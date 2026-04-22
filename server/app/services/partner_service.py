"""
Servicio de gestión de PartnerAccounts (Cuentas de Socio).

Maneja el ciclo de vida de los socios de la plataforma, incluyendo la creación 
con generación automática de identificadores estandarizados y la gestión de 
sus balances de créditos globales.
"""
import re
from typing import Optional, List
from sqlmodel import select, col
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.models import PartnerAccount

class PartnerService:
    """
    Servicio para la administración de cuentas de Partner en el sistema.

    Proporciona métodos para registrar nuevos partners, listar los existentes 
    y gestionar la jerarquía superior de la plataforma.
    """
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def _generate_next_partner_id(self) -> str:
        """
        Calcula el siguiente identificador disponible en formato 'ID_P_XXX'.
        
        Analiza todos los IDs existentes con el prefijo 'ID_P_', extrae la 
        secuencia numérica máxima y devuelve el valor incrementado con 
        formateo de tres dígitos.

        Returns:
            str: Nuevo ID de partner generado (ej: 'ID_P_005').
        """
        # Buscar IDs que coincidan con el patron ID_P_
        stmt = select(PartnerAccount.partner_id).where(
            col(PartnerAccount.partner_id).like("ID_P_%")
        )
        result = await self.db.exec(stmt)
        existing_ids = result.all()
        
        max_seq = 0
        pattern = re.compile(r"ID_P_(\d+)")
        
        for pid in existing_ids:
            match = pattern.match(pid)
            if match:
                seq = int(match.group(1))
                if seq > max_seq:
                    max_seq = seq
                    
        # Check also legacy partner_XXX if we want continuity (optional)
        # For now, we stick to ID_P_XXX sequence starting from max found there.
        # If no ID_P_XXX exists, we start at 001.
        
        next_seq = max_seq + 1
        return f"ID_P_{next_seq:03d}"

    async def create_partner(self, name: str, email: Optional[str] = None, credits_balance: int = 0) -> PartnerAccount:
        """
        Registra un nuevo Partner en la plataforma.
        
        Asigna automáticamente un ID estandarizado y establece el balance inicial 
        de créditos para el consumo de servicios de IA por parte de sus clientes.

        Args:
            name: Nombre comercial del Partner.
            email: Correo electrónico de contacto/facturación.
            credits_balance: Balance inicial de tokens asignados por contrato.

        Returns:
            PartnerAccount: Instancia del partner creado y persistido.
        """
        new_id = await self._generate_next_partner_id()
        
        # Double check collision (unlikely with max+1 logic but good for concurrency safety in strictly serialized envs)
        # In high concurrency, DB unique constraint handles it, but here we can just loop if needed.
        # Simple implementation for now.
        
        partner = PartnerAccount(
            partner_id=new_id,
            name=name,
            email=email,
            credits_balance=credits_balance,
            is_active=True
        )
        self.db.add(partner)
        await self.db.commit()
        await self.db.refresh(partner)
        return partner

    async def get_partner(self, partner_id: str) -> Optional[PartnerAccount]:
        return await self.db.get(PartnerAccount, partner_id)

    async def list_partners(self) -> List[PartnerAccount]:
        stmt = select(PartnerAccount).order_by(PartnerAccount.created_at.desc())
        result = await self.db.exec(stmt)
        return result.all()

"""
Motor de facturación y control de consumo.

Este módulo orquesta el registro de uso de tokens y la actualización de 
balances financieros para Partners y Clientes. Actúa como el árbitro de 
acceso a los recursos de IA del servidor.
"""
from datetime import datetime
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.db import server_engine
from server.app.database.models import License, ClientAccount, PartnerAccount

class LicenseError(Exception):
    """Error relacionado con la validez de la licencia."""
    pass

class PartnerCreditError(Exception):
    """Error relacionado con los créditos del Partner."""
    pass

class BillingEngine:
    """
    Motor de facturación centralizado de AutomatIA.

    Responsabilidades:
    - Registrar consumo de tokens por cliente y licencia.
    - Descontar créditos del balance global del Partner.
    - Realizar comprobaciones previas (Pre-Flight Checks) para asegurar solvencia.
    """

    def __init__(self):
        self._session = None

    async def __aenter__(self):
        """Permite usar el motor como context manager para transacciones largas."""
        self._session = AsyncSession(server_engine)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cierra la transacción y la sesión al salir del contexto."""
        if self._session:
            if exc_type:
                await self._session.rollback()
            else:
                await self._session.commit()
            await self._session.close()
            self._session = None
    
    async def validate_access(self, license_id: str, estimated_cost: float = 0.0) -> bool:
        """
        Valida si una ejecución está permitida antes de consumir recursos.
        
        Realiza una verificación en cascada:
        1. Validez temporal y de estado de la Licencia.
        2. Existencia del Cliente propietario.
        3. Solvencia del Partner (balance de créditos >= coste estimado).

        Args:
            license_id: UUID de la licencia que solicita acceso.
            estimated_cost: Coste previsto de la operación (opcional).

        Returns:
            bool: True si el acceso está garantizado.

        Raises:
            LicenseError: Si la licencia es inválida o inexistente.
            PartnerCreditError: Si el partner carece de saldo suficiente.
        """
        async with AsyncSession(server_engine) as session:
            # 1. Validar Licencia
            license = await session.get(License, license_id)
            if not license:
                raise LicenseError("No active license found (Invalid ID)")
            
            if not license.is_valid():
                raise LicenseError(f"License is not active or expired (Status: {license.status})")
            
            # 2. Obtener Cliente y Partner
            client = await session.get(ClientAccount, license.client_id)
            if not client:
                 raise LicenseError("License orphaned (No Client found)")
                 
            partner = await session.get(PartnerAccount, client.partner_id)
            if not partner:
                 raise LicenseError("Client orphan (No Partner assigned)")
            
            # 3. Validar Crédito Global (Partner)
            # Permitimos pasar si balance >= estimated_cost
            # Si estimated_cost es 0, solo validamos que tenga > 0 o is_active
            if partner.credits_balance <= 0 or partner.credits_balance < estimated_cost:
                 raise PartnerCreditError(f"Partner credit limit exceeded (Balance: {partner.credits_balance})")
                 
            return True

    async def record_consumption(self, license_id: str, tokens_used: int, operation: str = "text_generation"):
        """
        Registra el consumo de tokens y actualiza balances de forma atómica.
        
        Aumenta el contador de la licencia y descuenta el equivalente en créditos 
        del Partner asociado. Utiliza cargas explícitas para evitar errores de 
        contexto asíncrono (MissingGreenlet).

        Args:
            license_id: ID de la licencia que realizó el consumo.
            tokens_used: Número total de tokens (input + output).
            operation: Etiqueta descriptiva del tipo de tarea realizada.
        """
        async with AsyncSession(server_engine) as session:
            # 1. Cargar licencia explícitamente
            license = await session.get(License, license_id)
            if not license:
                print(f"[Billing] Error: Licencia {license_id} no encontrada.")
                return
            
            license.consumed_tokens += tokens_used
            session.add(license)
            
            # 2. Obtener cliente de forma independiente usando la FK
            client = await session.get(ClientAccount, license.client_id)
            
            # 3. Descontar créditos del Partner usando la FK del cliente
            pid = "?"
            if client and client.partner_id:
                pid = client.partner_id
                partner = await session.get(PartnerAccount, client.partner_id)
                if partner:
                    partner.credits_balance -= tokens_used
                    session.add(partner)
            
            await session.commit()
            
            # Log limpio de caracteres especiales para Windows (ASCII)
            print(f"[Billing] Facturacion: {tokens_used} tokens | Lic: {license_id} | Partner: {pid}")
    
    async def deduct_partner_credits(self, partner_id: str, amount: int):
        """
        Descuenta créditos del balance del Partner.
        
        Args:
            partner_id: ID del partner
            amount: Cantidad a descontar (positivo)
        """
        async with AsyncSession(server_engine) as session:
            result = await session.execute(
                select(PartnerAccount).where(PartnerAccount.partner_id == partner_id)
            )
            partner = result.scalar_one()
            partner.credits_balance -= amount
            session.add(partner)
            await session.commit()

# Singleton Instance
billing_engine = BillingEngine()

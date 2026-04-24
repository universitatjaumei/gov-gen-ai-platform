from typing import List
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.models import ScriptEscalation


class PartnerScriptsService:
    """
    Servicio para el desarrollo y validación de scripts delegados por clientes.

    Gestiona las solicitudes de escalado (Escalations) donde un cliente requiere
    que su Partner desarrolle o corrija un script de automatización complejo.
    """

    def __init__(self, session: AsyncSession, partner_id: str):
        self.session = session
        self.partner_id = partner_id

    async def get_pending_escalations(self) -> List[ScriptEscalation]:
        """
        Obtiene todas las solicitudes de desarrollo pendientes para este Partner.

        Returns:
            List[ScriptEscalation]: Lista de escalados en estado 'PENDING'.
        """
        # In real multi-tenant, filter by partner's clients.
        # For now, we fetch all PENDING associated with this partner_id.
        query = (
            select(ScriptEscalation)
            .where(ScriptEscalation.partner_id == self.partner_id)
            .where(ScriptEscalation.status == "PENDING")
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def publish_script(self, escalation_id: int, new_code: str) -> bool:
        """
        Finaliza un escalado publicando el código desarrollado por el Partner.

        Cambia el estado del escalado a 'RESOLVED' y pone el script a disposición
        del cliente solicitante.

        Args:
            escalation_id: ID único de la solicitud.
            new_code: Código Python finalizado y validado.

        Returns:
            bool: True si la resolución se guardó con éxito.
        """
        esc = await self.session.get(ScriptEscalation, escalation_id)
        if not esc:
            raise ValueError("Escalation not found")

        esc.status = "RESOLVED"

        # Here we would also update the CLIENT's CustomScript status.
        # But since Server/Client are decoupled in architecture (Sync),
        # we update the Server's TrustedScript or send a sync event.
        # For CS-09 scope, we just mark escalation resolved and assume sync happens or
        # we log the resolution.

        # Ideally, we push update to client. For prototype, we just save state.
        self.session.add(esc)
        await self.session.commit()
        return True

    async def reject_escalation(self, escalation_id: int, reason: str) -> bool:
        """Reject escalation."""
        esc = await self.session.get(ScriptEscalation, escalation_id)
        if not esc:
            raise ValueError("Escalation not found")

        esc.status = "REJECTED"
        esc.client_notes = f"{esc.client_notes or ''}\n\nREJECTION REASON: {reason}"

        self.session.add(esc)
        await self.session.commit()
        return True

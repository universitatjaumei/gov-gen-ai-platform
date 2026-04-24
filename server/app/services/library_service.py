from typing import List, Optional, Dict, Any
from sqlmodel import select, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.models import AutomationLibrary


class LibraryService:
    """
    Servicio de gestión para el catálogo central de automatizaciones (AutomationLibrary).

    Permite administrar la visibilidad de los recursos según la jerarquía de
    acceso (Global, Partner, Organización) y gestionar la persistencia de
    átomos y workflows en el servidor.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_visible_automations(
        self,
        client_id: Optional[str] = None,
        partner_id: Optional[str] = None,
        client_groups: List[str] = None,
        is_superadmin: bool = False,
    ) -> List[AutomationLibrary]:
        """
        Recupera las automatizaciones visibles para el solicitante según su contexto.

        Aplica reglas de filtrado multinivel:
        1. Superadmins: Ven todo el catálogo.
        2. Clientes: Ven sus propios recursos y los compartidos por su Partner o el Sistema.

        Args:
            client_id: ID del cliente que solicita.
            partner_id: ID del partner del cliente.
            client_groups: Grupos de acceso a los que pertenece el cliente.
            is_superadmin: Flag de privilegios elevados.

        Returns:
            List[AutomationLibrary]: Lista de automatizaciones autorizadas.
        """
        if is_superadmin:
            statement = select(AutomationLibrary)
            results = await self.session.exec(statement)
            return results.all()

        client_groups = client_groups or []

        # Base query: Get everything that *might* be visible
        # 1. Owned by client
        # 2. Owned by partner
        # 3. System templates
        conditions = []

        if client_id:
            conditions.append(AutomationLibrary.client_id == client_id)

        if partner_id:
            conditions.append(AutomationLibrary.partner_id == partner_id)

        conditions.append(AutomationLibrary.is_system_template)

        statement = select(AutomationLibrary).where(or_(*conditions))

        results = await self.session.exec(statement)
        candidates = results.all()

        # Python-side filtering for access_groups (JSON logic)
        visible_items = []
        for item in candidates:
            # 1. Always show own items and system templates
            if item.client_id == client_id or item.is_system_template:
                visible_items.append(item)
                continue

            # 2. Partner items: check access groups
            if item.partner_id == partner_id:
                if not item.access_groups:  # No restriction
                    visible_items.append(item)
                else:
                    # Check intersection
                    # item.access_groups is a JSON-decoded list (thanks to SQLModel/Pydantic)
                    if any(group in item.access_groups for group in client_groups):
                        visible_items.append(item)

        return visible_items

    async def get_by_id(self, item_id: str) -> Optional[AutomationLibrary]:
        return await self.session.get(AutomationLibrary, item_id)

    async def save_master(self, data: Dict[str, Any]) -> AutomationLibrary:
        """
        Saves a master automation (Partner/System) with signature.
        """
        # Ensure it's treated as an update or insert
        # Here assuming simple create for MVP or ID check
        item_id = data.get("id")
        if item_id:
            existing = await self.session.get(AutomationLibrary, item_id)
            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
                self.session.add(existing)
                await self.session.commit()
                await self.session.refresh(existing)
                return existing

        new_item = AutomationLibrary(**data)
        self.session.add(new_item)
        await self.session.commit()
        await self.session.refresh(new_item)
        return new_item

    async def delete_automation(
        self, item_id: str, partner_id: str, is_superadmin: bool = False
    ) -> bool:
        """
        Deletes an automation.
        Partners can only delete their own.
        Superadmins can delete any.
        """
        item = await self.session.get(AutomationLibrary, item_id)
        if not item:
            return False

        # Security check: must be owned by partner OR be superadmin
        if not is_superadmin and item.partner_id != partner_id:
            return False

        await self.session.delete(item)
        await self.session.commit()
        return True

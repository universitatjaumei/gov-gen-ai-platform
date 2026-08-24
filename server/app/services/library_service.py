from typing import Any, Dict, List, Optional, Sequence
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
        client_ids: Sequence[str] | None = None,
        client_groups: Sequence[str] | None = None,
        is_superadmin: bool = False,
    ) -> List[AutomationLibrary]:
        """
        Recupera las automatizaciones visibles para el solicitante según su contexto.

        1. Superadministrador: ve el catálogo entero.
        2. Cualquier otro: lo de **sus** organizaciones y las plantillas de sistema.

        **SEC.9.1 — `client_ids` en plural, y sin `partner_id`.** Antes recibía un `client_id` y
        un `partner_id` que el router sacaba de cabeceras HTTP, o sea del propio llamante. Ahora
        vienen del token, donde la tenencia es una tupla de organizaciones y **no hay dimensión
        de *partner***: ROL.1 la retiró del principal. Así que la rama que hacía visibles los
        artefactos de un partner —y con ella el cruce de `access_groups`— desaparece.

        Es un **estrechamiento deliberado**: nadie ve menos de lo suyo, y lo que se pierde es una
        vía de compartición cuyo control lo ponía quien pedía. Compartir configuración entre
        organizaciones es justo lo que diseñan MT.17–MT.21 (`capacidades`/`requiere`), y ahí el
        criterio lo pone la plataforma, no una cabecera.

        Args:
            client_ids: organizaciones del principal (claim del token).
            client_groups: grupos que el IdP declara para el principal.
            is_superadmin: privilegios elevados (ve todo).

        Returns:
            List[AutomationLibrary]: Lista de automatizaciones autorizadas.
        """
        if is_superadmin:
            statement = select(AutomationLibrary)
            results = await self.session.exec(statement)
            return results.all()

        propias = [str(c) for c in (client_ids or [])]

        conditions = []
        if propias:
            conditions.append(AutomationLibrary.client_id.in_(propias))
        conditions.append(AutomationLibrary.is_system_template)

        statement = select(AutomationLibrary).where(or_(*conditions))

        results = await self.session.exec(statement)
        candidates = results.all()

        return [
            item
            for item in candidates
            if (item.client_id is not None and str(item.client_id) in propias)
            or item.is_system_template
        ]

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

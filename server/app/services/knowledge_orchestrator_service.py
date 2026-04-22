"""
Servicio del Orquestador de Conocimiento (Lado Servidor).

Implementa la lógica del Orquestador Multinivel para IA. Construye prompts 
de sistema dinámicos inyectando inventarios de 4 niveles de visibilidad: 
LOCAL, ORGANIZACIÓN, PARTNER y GLOBAL.
"""

import json
from enum import IntEnum
from typing import List, Dict, Any, Optional
from sqlalchemy import or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.database.db import server_engine
from server.app.database.models import AutomationLibrary, SystemPrompt
from automatia_shared.enums import AutomationType


class ResourceLevel(IntEnum):
    LOCAL = 1
    ORGANIZATION = 2
    PARTNER = 3
    GLOBAL = 4


class KnowledgeOrchestratorService:
    """
    Orquestador de prompts y contexto híbrido de AutomatIA.
    
    Centraliza la búsqueda de recursos de automatización (Átomos/Workflows) a 
    lo largo de la jerarquía de la plataforma para permitir que el Asistente 
    de IA conozca qué herramientas tiene disponibles según el cliente y partner.
    """
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def search_remote_inventory(self, query: str, client_id: str, partner_id: str, max_results: int = 15) -> List[Dict[str, Any]]:
        """
        Busca en el catálogo remoto (ORG, PARTNER, GLOBAL) recursos compatibles.
        
        Asegura que los resultados respeten las políticas de aislamiento de datos 
        del Partner y el Cliente.

        Args:
            query: Texto de búsqueda (o 'all').
            client_id: Identificador del cliente final.
            partner_id: Identificador del partner propietario.
            max_results: Límite de elementos a retornar.

        Returns:
            List[Dict]: Lista de recursos formateados con su nivel de acceso.
        """
        async with AsyncSession(server_engine) as session:
            # Construir filtros de seguridad y multinivel
            # 1. Recursos de la organización (client_id coincide)
            # 2. Recursos del partner (partner_id coincide y is_system_template=False)
            # 3. Recursos globales (is_system_template=True)
            
            stmt = select(AutomationLibrary).where(
                or_(
                    AutomationLibrary.client_id == client_id,
                    AutomationLibrary.partner_id == partner_id,
                    AutomationLibrary.is_system_template == True
                )
            )
            
            # Filtro por texto si hay query
            if query and query.lower() != "all":
                q = f"%{query.lower()}%"
                stmt = stmt.where(
                    or_(
                        AutomationLibrary.name.ilike(q),
                        AutomationLibrary.id.ilike(q)
                    )
                )
            
            result = await session.execute(stmt)
            automations = result.scalars().all()
            
            items = []
            for auto in automations:
                # Determinar nivel
                if auto.is_system_template:
                    level = ResourceLevel.GLOBAL
                elif auto.client_id == client_id:
                    level = ResourceLevel.ORGANIZATION
                elif auto.partner_id == partner_id:
                    level = ResourceLevel.PARTNER
                else:
                    continue # No debería pasar por el filtro OR
                
                # Metadata del contrato (asumimos que está en metadata_json)
                ui_contract = auto.metadata_json.get("ui_contract", {}) if auto.metadata_json else {}
                description = auto.metadata_json.get("description", "") if auto.metadata_json else ""
                
                items.append({
                    "id": auto.id,
                    "level": level.name,
                    "name": auto.name,
                    "description": description,
                    "ui_contract": ui_contract
                })
            
            # Ordenar por nivel (prioridad)
            items.sort(key=lambda x: ResourceLevel[x["level"]].value)
            
            return items[:max_results]

    def format_inventory_block(self, local_inventory: List[Dict], remote_inventory: List[Dict]) -> str:
        """
        Genera el bloque de texto estructurado para el System Prompt.
        
        Combina el inventario local (del cliente local) y el remoto (del servidor) 
        en una lista formateada para que el LLM la interprete como herramientas.

        Args:
            local_inventory: Recursos presentes en la instancia local.
            remote_inventory: Recursos recuperados de la base de datos central.

        Returns:
            str: Texto formateado con IDs, nombres y descripciones.
        """
        combined = []
        
        # Añadir LOCAL
        for item in local_inventory:
            combined.append(self._format_item(item, "LOCAL"))
            
        # Añadir REMOTOS
        for item in remote_inventory:
            combined.append(self._format_item(item, item["level"]))
            
        if not combined:
            return "(No se encontraron recursos relevantes en el catálogo)"
            
        return "\n".join(combined)

    def _format_item(self, item: Dict, level: str) -> str:
        # Extraer inputs del contrato
        ui_contract = item.get("ui_contract", {})
        inputs = ui_contract.get("inputs", [])
        inputs_summary = [i.get("label", i.get("id")) for i in inputs]
        
        return (
            f"- ID: {item['id']} | NIVEL: {level}\n"
            f"  Nombre: {item['name']}\n"
            f"  Descripción: {item.get('description', '')}\n"
            f"  Entradas: {', '.join(inputs_summary) if inputs_summary else 'Ninguna'}\n"
        )

    async def get_system_prompt(self, name: str) -> Optional[str]:
        """Recupera el contenido del system prompt de la BD."""
        async with AsyncSession(server_engine) as session:
            stmt = select(SystemPrompt).where(SystemPrompt.name == name, SystemPrompt.is_active == True)
            result = await session.execute(stmt)
            prompt = result.scalars().first()
            return prompt.content if prompt else None

    async def build_hybrid_system_prompt(self, user_query: str, local_inventory: List[Dict], client_id: str, partner_id: str, prompt_name: str = "flow_orchestrator") -> str:
        """
        Construye el prompt final inyectando el inventario combinado de 4 niveles.
        
        Es el método principal utilizado por el Copilot para entender el 
        contexto actual del usuario y proponer soluciones.

        Args:
            user_query: Intención del usuario o contexto de búsqueda.
            local_inventory: Recursos locales.
            client_id: Contexto del cliente.
            partner_id: Contexto del partner.
            prompt_name: Nombre de la plantilla de prompt en la BD.

        Returns:
            str: Prompt de sistema completo y listo para el LLM.
        """
        # 1. Buscar inventario remoto
        remote_items = await self.search_remote_inventory(user_query, client_id, partner_id)
        
        # 2. Formatear bloque de inventario
        inventory_block = self.format_inventory_block(local_inventory, remote_items)
        
        # 3. Obtener el SystemPrompt
        base_prompt = await self.get_system_prompt(prompt_name)
        if not base_prompt:
            # Fallback a un prompt genérico si no existe en BD
            base_prompt = "Actúa como un arquitecto de automatización. INVENTARIO: {inventory_block}"
            
        # 4. Inyectar contexto
        # Nota: Usamos replace en lugar de .format() para evitar errores con llaves en el prompt
        return base_prompt.replace("{inventory_block}", inventory_block)


# Global instance
knowledge_orchestrator = KnowledgeOrchestratorService()

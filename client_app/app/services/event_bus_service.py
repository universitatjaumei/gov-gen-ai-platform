import asyncio
import logging
from typing import Dict, List, Any
from client_app.app.database.models import TriggerSubscription, FlowRegistry
from client_app.app.database.db import get_session
from sqlmodel import select

logger = logging.getLogger(__name__)

class EventBusService:
    """
    Bus de eventos centralizado.
    Recibe eventos de Watchers y dispara los flujos suscritos.
    """
    
    async def emit_trigger_event(self, trigger_id: int, payload: Dict[str, Any]):
        """
        Llamado por los watchers cuando detectan algo.
        Solo ejecuta flujos que tengan is_active=True.
        """
        logger.info(f"Event received from Trigger {trigger_id}")

        # 1. Buscar suscriptores con flujos activos
        async with get_session() as session:
            statement = select(TriggerSubscription, FlowRegistry).join(
                FlowRegistry, TriggerSubscription.flow_id == FlowRegistry.id
            ).where(
                TriggerSubscription.trigger_id == trigger_id,
                TriggerSubscription.is_active == True,
                FlowRegistry.is_active == True  # Only execute active flows
            )
            result = await session.exec(statement)
            subscriptions = [(sub, flow) for sub, flow in result.all()]

        if not subscriptions:
            logger.warning(f"Trigger {trigger_id} fired but no active subscriptions/flows found.")
            return

        logger.info(f"Found {len(subscriptions)} active subscribed flows.")

        # 2. Ejecutar flujos en paralelo
        tasks = [self._execute_flow(sub.flow_id, payload) for sub, flow in subscriptions]
        await asyncio.gather(*tasks, return_exceptions=True)
            
    async def _execute_flow(self, flow_id: int, payload: Dict[str, Any]):
        """
        Inicia la ejecución del flujo inyectando el payload.
        """
        try:
            from client_app.app.services.flow_registry_service import flow_registry_service
            from client_app.app.modules.runtime.workflow_engine import WorkflowEngine
            
            logger.info(f"Triggering Flow {flow_id} with payload keys: {list(payload.keys())}")
            
            # The service needs a session to pass to engine, or engine creates one?
            # WorkflowEngine takes session in init.
            # Using get_session matches the pattern.
            async with get_session() as session:
                # 1. Get Flow Spec
                # We need to bind the session to the service instance manually or use service's own session management?
                # flow_registry_service uses self.session if provided, or creates new if not. 
                # But here we are inside a context manager for session.
                # It's cleaner to instantiate service with session or use a service method that accepts session?
                # flow_registry_service singleton usually doesn't hold session. 
                # Wait, flow_registry_service.__init__ takes session=None.
                # If I use global 'flow_registry_service', its session is None.
                # So I should create a new service instance or set session?
                # Better: create new instance or use the global one but manage session inside it?
                # Actually, flow_registry_service methods (like get_flow) use self.session. 
                # If self.session is None, get_flow crashes?
                # Looking at flow_registry_service.py: 
                # async def get_flow(self, flow_id): return await self.session.get(...)
                # So self.session MUST be set if using instance methods that use self.session.
                # But 'update_flow_metadata' handles creating session if None.
                # 'get_flow' DOES NOT handle it.
                # So the global 'flow_registry_service' instance is tricky if session is not injected.
                # 
                # However, in 'flow_registry_service.py':
                # flow_registry_service = FlowRegistryService()
                # It is instantiated without session.
                # So any call to get_flow on that global instance will fail if session not set?
                # Let's check 'get_flow' again in Step 108.
                # Line 68: return await self.session.get(FlowRegistry, flow_id)
                # Yes, it will fail if self.session is None.
                # So 'flow_registry_service' as singleton expects manual session injection or maybe it's used differently?
                # 
                # Actually, most services in this app seem to follow a pattern where they might be instantiated per request 
                # OR the methods create their own session.
                # 'create_flow', 'update_flow' etc. use self.session.
                # But 'update_flow_metadata' uses 'async with AsyncSession(...) if not self.session'.
                # This suggests inconsistency or a specific usage pattern.
                # 
                # For EventBus, since we are in background task (async), I should probably instantiate the service 
                # with my local session.
                
                registry_service = flow_registry_service.__class__(session) 
                # Or just construct: FlowRegistryService(session)
                
                # But wait, I need to import the class FlowRegistryService, not just the instance.
                # The instance exports the class? No. 
                # I should import the class.
                pass
            
            # Re-importing class to be safe
            from client_app.app.services.flow_registry_service import FlowRegistryService
            
            async with get_session() as session:
                registry_service = FlowRegistryService(session)
                flow_spec = await registry_service.get_flow_spec(flow_id)
                
                if not flow_spec:
                    logger.error(f"Flow {flow_id} not found or failed to load spec.")
                    return

                # 2. Prepare Context
                # We inject the payload as 'trigger' variable
                context = {
                    "trigger": payload,
                    "trigger_id": payload.get("meta", {}).get("trigger_id")
                }
                
                # 3. Execute Flow
                engine = WorkflowEngine(session)
                result = await engine.execute_flow(flow_spec, context)
                
                logger.info(f"Flow {flow_id} execution finished with status: {result.get('status')}")
            
        except Exception as e:
            logger.error(f"Error executing flow {flow_id}: {e}", exc_info=True)

event_bus_service = EventBusService()

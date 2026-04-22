import asyncio
from typing import Dict, Set, Optional, List, Any
from datetime import datetime
import logging

from client_app.app.database.models import TriggerConfig, TriggerStatus, TriggerSubscription
from client_app.app.database.db import get_session
from sqlmodel import select

logger = logging.getLogger(__name__)

class TriggerLifecycleManager:
    """
    Gestiona el ciclo de vida de los triggers y sus watchers asociados.
    Implementa el patrón de suscripción y lazy activation.
    """
    
    def __init__(self):
        self._active_watchers: Dict[int, Any] = {} # trigger_id -> watcher_instance
        self._subscriptions: Dict[int, Set[int]] = {} # trigger_id -> {flow_ids}
        
    async def initialize(self):
        """Restores state from DB on app startup."""
        async with get_session() as session:
            # Recover active subscriptions from DB
            statement = select(TriggerSubscription).where(TriggerSubscription.is_active == True)
            results = await session.exec(statement)
            subscriptions = results.all()
            
            for sub in subscriptions:
                if sub.trigger_id not in self._subscriptions:
                    self._subscriptions[sub.trigger_id] = set()
                self._subscriptions[sub.trigger_id].add(sub.flow_id)

            # Start watchers for active subscriptions
            for trigger_id in self._subscriptions.keys():
                trigger = await session.get(TriggerConfig, trigger_id)
                if trigger:
                     await self._start_physical_watcher(trigger)

    async def subscribe(self, trigger: TriggerConfig, flow_id: int):
        """
        Suscribe un flujo a un trigger. 
        Si es el primer suscriptor, arranca el watcher físico.
        """
        logger.info(f"Flow {flow_id} subscribing to Trigger {trigger.id}")
        
        if trigger.id not in self._subscriptions:
            self._subscriptions[trigger.id] = set()
            
        self._subscriptions[trigger.id].add(flow_id)
        
        if trigger.id not in self._active_watchers:
            await self._start_physical_watcher(trigger)
            
    async def unsubscribe(self, trigger_id: int, flow_id: int):
        """
        Desuscribe un flujo via ID.
        Si no quedan suscriptores, detiene el watcher.
        """
        logger.info(f"Flow {flow_id} unsubscribing from Trigger {trigger_id}")
        
        if trigger_id in self._subscriptions:
            self._subscriptions[trigger_id].discard(flow_id)
            
            if not self._subscriptions[trigger_id]:
                await self._stop_physical_watcher(trigger_id)
                del self._subscriptions[trigger_id]

    async def get_trigger_status(self, trigger_id: int) -> TriggerStatus:
        if trigger_id in self._active_watchers:
            return TriggerStatus.ACTIVE
        # TODO: Check DB if configured but not active?
        return TriggerStatus.CONFIGURED

    async def _start_physical_watcher(self, trigger: TriggerConfig):
        """
        Instancia y arranca el watcher específico según el tipo.
        """
        logger.info(f"Starting physical watcher for Trigger {trigger.id} ({trigger.type})")
        
        try:
            if trigger.type == "folder_watcher":
                from client_app.app.services.folder_watcher_service import folder_watcher_service
                success, msg = await folder_watcher_service.start_trigger(trigger)
                if not success:
                     logger.error(f"Failed to start folder watcher {trigger.id}: {msg}")
                     # Should we mark it as ERROR in DB?
                     # Yes, ideally.
                     return
                     
            elif trigger.type == "mail_watcher":
                 from client_app.app.services.mail_watcher_service import mail_watcher_service
                 success, msg = await mail_watcher_service.start_trigger(trigger)
                 if not success:
                     logger.error(f"Failed to start mail watcher {trigger.id}: {msg}")
                     return

            elif trigger.type == "web_watcher":
                 from client_app.app.services.web_watcher_service import web_watcher_service
                 success, msg = await web_watcher_service.start_trigger(trigger)
                 if not success:
                     logger.error(f"Failed to start web watcher {trigger.id}: {msg}")
                     return

            elif trigger.type == "scheduler":
                 from client_app.app.services.scheduler_service import scheduler_service
                 success, msg = await scheduler_service.start_trigger(trigger)
                 if not success:
                     logger.error(f"Failed to start scheduler trigger {trigger.id}: {msg}")
                     return
            
            else:
                 logger.warning(f"Unknown trigger type: {trigger.type}")
                 # If unknown, we should probably not mark it as active
                 return

            # If we reached here, the watcher was conceptually started (or it's a placeholder)
            self._active_watchers[trigger.id] = True 
            
            # Update DB status
            async with get_session() as session:
                db_trigger = await session.get(TriggerConfig, trigger.id)
                if db_trigger:
                    db_trigger.status = TriggerStatus.ACTIVE
                    db_trigger.is_active = True
                    # Only commit if we actually started something or confirm it's active?
                    # Yes, we assume success if we passed guard clauses.
                    session.add(db_trigger)
                    await session.commit()
                    
        except Exception as e:
            logger.error(f"Failed to start watcher {trigger.id}: {e}")
            # Update DB status to ERROR

    async def _stop_physical_watcher(self, trigger_id: int):
        """Detiene y limpia el watcher."""
        logger.info(f"Stopping physical watcher for Trigger {trigger_id}")
        
        async with get_session() as session:
            trigger = await session.get(TriggerConfig, trigger_id)
            if not trigger:
                 logger.warning(f"Trigger {trigger_id} not found for stopping.")
                 return

            if trigger.type == "folder_watcher":
                from client_app.app.services.folder_watcher_service import folder_watcher_service
                await folder_watcher_service.stop_watcher(trigger_id)
            
            elif trigger.type == "mail_watcher":
                 from client_app.app.services.mail_watcher_service import mail_watcher_service
                 await mail_watcher_service.stop_watcher(trigger_id)

            elif trigger.type == "web_watcher":
                 from client_app.app.services.web_watcher_service import web_watcher_service
                 await web_watcher_service.stop_watcher(trigger_id=trigger_id)

            elif trigger.type == "scheduler":
                 from client_app.app.services.scheduler_service import scheduler_service
                 await scheduler_service.stop_watcher(trigger_id)

        if trigger_id in self._active_watchers:
            del self._active_watchers[trigger_id]

    async def set_trigger_active(self, trigger_id: int, active: bool) -> bool:
        """
        Activa o desactiva un trigger manualmente desde la UI.
        Actualiza la BD y el estado del watcher físico.
        """
        async with get_session() as session:
            trigger = await session.get(TriggerConfig, trigger_id)
            if not trigger:
                return False
            
            trigger.is_active = active
            trigger.status = TriggerStatus.ACTIVE if active else TriggerStatus.PAUSED
            session.add(trigger)
            await session.commit()
            await session.refresh(trigger)
            
            if active:
                # Iniciar watcher físico
                # Usamos logica similar a _start_physical_watcher pero necesitamos llamar a la version publica?
                # start_trigger en services devuelve success/msg
                
                if trigger.type == "folder_watcher":
                    from client_app.app.services.folder_watcher_service import folder_watcher_service
                    await folder_watcher_service.start_trigger(trigger)
                elif trigger.type == "mail_watcher":
                    from client_app.app.services.mail_watcher_service import mail_watcher_service
                    await mail_watcher_service.start_trigger(trigger)
                elif trigger.type == "web_watcher":
                    from client_app.app.services.web_watcher_service import web_watcher_service
                    await web_watcher_service.start_trigger(trigger)
                elif trigger.type == "scheduler":
                    from client_app.app.services.scheduler_service import scheduler_service
                    await scheduler_service.start_trigger(trigger)
                
                self._active_watchers[trigger.id] = True
            
            else:
                await self._stop_physical_watcher(trigger_id)
                
            return True

trigger_lifecycle_manager = TriggerLifecycleManager()

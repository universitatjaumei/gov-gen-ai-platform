"""
Workflow Scheduler Service.
Handles background execution of workflows based on interval or cron expressions.
"""

import asyncio
import json
from datetime import datetime
from typing import Optional, Dict

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.database.db import client_engine
from client_app.app.services.flow_registry_service import FlowRegistryService
from client_app.app.database.models import FlowRegistry

class WorkflowScheduler:
    """
    Manages scheduled workflow tasks using APScheduler.
    """
    _instance: Optional["WorkflowScheduler"] = None
    _scheduler: Optional[AsyncIOScheduler] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._scheduler is None:
            self._scheduler = AsyncIOScheduler()

    async def start(self):
        """Starts the scheduler if not already running."""
        if not self._scheduler.running:
            self._scheduler.start()
            print("[WorkflowScheduler] Scheduler started")
            await self.sync_with_db()

    async def stop(self):
        """Stops the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            print("[WorkflowScheduler] Scheduler stopped")

    async def sync_with_db(self):
        """
        Loads all active scheduled flows from the database and registers them.
        """
        print("[WorkflowScheduler] Syncing with database...")
        async with AsyncSession(client_engine) as session:
            reg = FlowRegistryService(session)
            flows = await reg.list_flows()
            
            # Clear existing workflow jobs before re-syncing to avoid duplicates
            for job in self._scheduler.get_jobs():
                if job.id.startswith("flow_"):
                    self._scheduler.remove_job(job.id)

            for flow in flows:
                if flow.is_active and flow.trigger_type in ["interval", "cron", "schedule"]:
                    await self.schedule_flow(flow)

    async def schedule_flow(self, flow):
        """
        Schedules a flow using its database object properties.
        """
        if not flow.is_active or flow.trigger_type == 'manual':
            self.remove_flow_job(flow.id)
            return

        try:
            config = json.loads(flow.trigger_config) if isinstance(flow.trigger_config, str) else flow.trigger_config
            self.add_flow_job(flow.id, flow.trigger_type, config)
        except Exception as e:
            print(f"[WorkflowScheduler] Error scheduling flow {flow.id}: {e}")

    def add_flow_job(self, flow_id: int, trigger_type: str, config: dict):
        """
        Adds or updates a flow job in the scheduler.
        """
        job_id = f"flow_{flow_id}"
        
        # Remove existing if any
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        trigger = None
        if trigger_type == "interval":
            # Support hours, minutes, seconds from config
            trigger = IntervalTrigger(
                hours=config.get("hours", 0),
                minutes=config.get("minutes", 0),
                seconds=config.get("seconds", 0)
            )
        elif trigger_type == "cron" or trigger_type == "schedule":
            cron_expr = config.get("cron")
            if cron_expr:
                trigger = CronTrigger.from_crontab(cron_expr)
        
        if trigger:
            self._scheduler.add_job(
                self._run_workflow_wrapper,
                trigger=trigger,
                args=[flow_id],
                id=job_id,
                name=f"Workflow Flow {flow_id}",
                replace_existing=True
            )
            print(f"[WorkflowScheduler] Job {job_id} scheduled ({trigger_type})")
        else:
            print(f"[WorkflowScheduler] Warning: Invalid trigger configuration for flow {flow_id}")

    def remove_flow_job(self, flow_id: int):
        """Removes a flow job from the scheduler."""
        job_id = f"flow_{flow_id}"
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            print(f"[WorkflowScheduler] Job {job_id} removed")

    def _run_workflow_wrapper(self, flow_id: int):
        """Wrapper to launch the async execution from a thread/scheduler context."""
        asyncio.create_task(self._execute_workflow(flow_id))

    async def _execute_workflow(self, flow_id: int):
        """
        Actual execution logic: re-fetches flow and runs it via WorkflowEngine.
        """
        from client_app.app.modules.runtime.workflow_engine import WorkflowEngine
        
        print(f"[WorkflowScheduler] Executing flow {flow_id}...")
        try:
            async with AsyncSession(client_engine) as session:
                reg = FlowRegistryService(session)
                flow = await reg.get_flow(flow_id)
                
                if not flow or not flow.is_active:
                    print(f"[WorkflowScheduler] Flow {flow_id} no longer active or exists. Removing job.")
                    self.remove_flow_job(flow_id)
                    return

                engine = WorkflowEngine(session)
                context = {"trigger": "scheduler", "timestamp": datetime.now().isoformat()}
                
                result = await engine.execute_flow(flow, context=context)
                print(f"[WorkflowScheduler] Flow {flow_id} finished with status: {result.get('status')}")
                
        except Exception as e:
            print(f"[WorkflowScheduler] Critical error executing flow {flow_id}: {e}")

# Global singleton
workflow_scheduler = WorkflowScheduler()

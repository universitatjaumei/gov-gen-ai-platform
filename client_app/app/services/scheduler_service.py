"""
SchedulerService - Programación de Ejecuciones de Flujos

Servicio para programar ejecuciones automáticas de flujos usando APScheduler.
Almacena las tareas programadas en SQLite local para persistencia.

Funcionalidades:
- Programar ejecuciones únicas (run_date)
- Programar ejecuciones recurrentes (interval, cron)
- Gestionar tareas programadas (listar, cancelar, pausar)
- Integración con el motor de ejecución de flujos
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED

from client_app.app.services.enterprise_audit_service import enterprise_audit_service
from automatia_shared.core.audit_models import RiskLevel
from client_app.app.database.models import TriggerConfig
from shared.automatia_shared.dtos import TriggerPayloadMeta, SchedulerPayload
import uuid

# Define SchedulerPayload if not imported
# (Assumed imported from dtos)


class ScheduleType(str, Enum):
    """Tipos de programación."""
    ONCE = "once"           # Ejecución única
    INTERVAL = "interval"   # Cada X minutos/horas/días
    CRON = "cron"           # Expresión cron
    DAILY = "daily"         # Diariamente a hora fija
    WEEKLY = "weekly"       # Semanalmente


@dataclass
class ScheduleConfig:
    """Configuración de una programación."""
    schedule_type: ScheduleType
    flow_id: int
    flow_name: str = ""

    # Para ONCE
    run_date: Optional[datetime] = None

    # Para INTERVAL
    interval_minutes: Optional[int] = None
    interval_hours: Optional[int] = None
    interval_days: Optional[int] = None

    # Para CRON
    cron_expression: Optional[str] = None

    # Para DAILY/WEEKLY
    hour: int = 9
    minute: int = 0
    day_of_week: Optional[str] = None  # "mon,wed,fri" para WEEKLY

    # Metadata
    enabled: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schedule_type": self.schedule_type.value,
            "flow_id": self.flow_id,
            "flow_name": self.flow_name,
            "run_date": self.run_date.isoformat() if self.run_date else None,
            "interval_minutes": self.interval_minutes,
            "interval_hours": self.interval_hours,
            "interval_days": self.interval_days,
            "cron_expression": self.cron_expression,
            "hour": self.hour,
            "minute": self.minute,
            "day_of_week": self.day_of_week,
            "enabled": self.enabled,
            "description": self.description,
        }


@dataclass
class ScheduledJob:
    """Información de una tarea programada."""
    job_id: str
    flow_id: int
    flow_name: str
    schedule_type: ScheduleType
    next_run: Optional[datetime]
    last_run: Optional[datetime] = None
    is_paused: bool = False
    run_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "flow_id": self.flow_id,
            "flow_name": self.flow_name,
            "schedule_type": self.schedule_type.value,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "is_paused": self.is_paused,
            "run_count": self.run_count,
        }


class SchedulerService:
    """
    Servicio de programación de ejecuciones de flujos.

    Usa APScheduler con SQLite para persistencia de tareas.
    """

    # Ruta de la base de datos de tareas
    DB_PATH = Path("data/scheduler.db")

    def __init__(self):
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._workflow_engine = None
        self._is_running = False
        self._audit_enabled = True

        # Callbacks para notificaciones
        self._job_callbacks: List[Callable] = []

        # Contador de ejecuciones por job
        self._run_counts: Dict[str, int] = {}

    def set_workflow_engine(self, engine) -> None:
        """Inyecta la dependencia del motor de flujos."""
        self._workflow_engine = engine

    async def start(self) -> None:
        """Inicia el scheduler."""
        if self._is_running:
            return

        # Crear directorio si no existe
        self.DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Configurar jobstore con SQLite
        jobstores = {
            "default": SQLAlchemyJobStore(url=f"sqlite:///{self.DB_PATH}")
        }

        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            timezone="Europe/Madrid"  # Ajustar según configuración
        )

        # Registrar listeners de eventos
        self._scheduler.add_listener(
            self._on_job_executed,
            EVENT_JOB_EXECUTED
        )
        self._scheduler.add_listener(
            self._on_job_error,
            EVENT_JOB_ERROR
        )
        self._scheduler.add_listener(
            self._on_job_missed,
            EVENT_JOB_MISSED
        )

        self._scheduler.start()
        self._is_running = True

        # Auditoría
        if self._audit_enabled:
            await enterprise_audit_service.log_event(
                action_type="SCHEDULER_STARTED",
                module="scheduler_service",
                source_description="APScheduler",
                risk_level=RiskLevel.LOW.value,
                additional_context={"db_path": str(self.DB_PATH)}
            )

    async def stop(self) -> None:
        """Detiene el scheduler."""
        if self._scheduler and self._is_running:
            self._scheduler.shutdown(wait=False)
            self._is_running = False

            if self._audit_enabled:
                await enterprise_audit_service.log_event(
                    action_type="SCHEDULER_STOPPED",
                    module="scheduler_service",
                    risk_level=RiskLevel.LOW.value
                )

    def _on_job_executed(self, event):
        """Callback cuando un job se ejecuta correctamente."""
        job_id = event.job_id
        self._run_counts[job_id] = self._run_counts.get(job_id, 0) + 1
        asyncio.create_task(self._notify_job_event(job_id, "executed"))

    def _on_job_error(self, event):
        """Callback cuando un job falla."""
        asyncio.create_task(self._notify_job_event(event.job_id, "error", str(event.exception)))

    def _on_job_missed(self, event):
        """Callback cuando un job se pierde (sistema apagado)."""
        asyncio.create_task(self._notify_job_event(event.job_id, "missed"))

    async def _notify_job_event(self, job_id: str, event_type: str, error: str = None):
        """Notifica eventos de jobs a los suscriptores."""
        for callback in self._job_callbacks[:]:
            try:
                await callback(job_id, event_type, error)
            except:
                self._job_callbacks.remove(callback)

    def register_job_callback(self, callback: Callable) -> None:
        """Registra callback para eventos de jobs."""
        if callback not in self._job_callbacks:
            self._job_callbacks.append(callback)

    def unregister_job_callback(self, callback: Callable) -> None:
        """Elimina callback de eventos."""
        if callback in self._job_callbacks:
            self._job_callbacks.remove(callback)

    async def _execute_flow(self, flow_id: int, job_id: str):
        """Ejecuta un flujo (llamado por el scheduler)."""
        if not self._workflow_engine:
            print(f"[SchedulerService] No hay workflow engine configurado")
            return

        try:
            # Auditoría de inicio
            if self._audit_enabled:
                await enterprise_audit_service.log_event(
                    action_type="SCHEDULED_FLOW_STARTED",
                    module="scheduler_service",
                    source_description=f"Job: {job_id}",
                    risk_level=RiskLevel.LOW.value,
                    additional_context={"flow_id": flow_id, "job_id": job_id}
                )

            # Ejecutar flujo
            await self._workflow_engine.execute_flow(flow_id, trigger="scheduler")

        except Exception as e:
            print(f"[SchedulerService] Error ejecutando flujo {flow_id}: {e}")
            if self._audit_enabled:
                await enterprise_audit_service.log_event(
                    action_type="SCHEDULED_FLOW_ERROR",
                    module="scheduler_service",
                    source_description=f"Job: {job_id}",
                    risk_level=RiskLevel.HIGH.value,
                    additional_context={"flow_id": flow_id, "job_id": job_id, "error": str(e)}
                )

    async def schedule_flow(self, config: ScheduleConfig) -> str:
        """
        Programa la ejecución de un flujo.

        Args:
            config: Configuración de la programación

        Returns:
            job_id de la tarea creada
        """
        if not self._scheduler or not self._is_running:
            await self.start()

        job_id = f"flow_{config.flow_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Crear trigger según tipo
        trigger = None

        if config.schedule_type == ScheduleType.ONCE:
            if not config.run_date:
                raise ValueError("run_date requerido para schedule_type=ONCE")
            trigger = DateTrigger(run_date=config.run_date)

        elif config.schedule_type == ScheduleType.INTERVAL:
            kwargs = {}
            if config.interval_minutes:
                kwargs["minutes"] = config.interval_minutes
            if config.interval_hours:
                kwargs["hours"] = config.interval_hours
            if config.interval_days:
                kwargs["days"] = config.interval_days
            if not kwargs:
                raise ValueError("Se requiere al menos un intervalo")
            trigger = IntervalTrigger(**kwargs)

        elif config.schedule_type == ScheduleType.CRON:
            if not config.cron_expression:
                raise ValueError("cron_expression requerido para schedule_type=CRON")
            # Parsear expresión cron (minuto hora día mes día_semana)
            parts = config.cron_expression.split()
            if len(parts) != 5:
                raise ValueError("Expresión cron debe tener 5 partes")
            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4]
            )

        elif config.schedule_type == ScheduleType.DAILY:
            trigger = CronTrigger(hour=config.hour, minute=config.minute)

        elif config.schedule_type == ScheduleType.WEEKLY:
            if not config.day_of_week:
                raise ValueError("day_of_week requerido para schedule_type=WEEKLY")
            trigger = CronTrigger(
                hour=config.hour,
                minute=config.minute,
                day_of_week=config.day_of_week
            )

        # Añadir job
        self._scheduler.add_job(
            self._execute_flow,
            trigger=trigger,
            args=[config.flow_id, job_id],
            id=job_id,
            name=f"Flow: {config.flow_name or config.flow_id}",
            replace_existing=True
        )

        # Auditoría
        if self._audit_enabled:
            await enterprise_audit_service.log_event(
                action_type="FLOW_SCHEDULED",
                module="scheduler_service",
                source_description=f"Flow: {config.flow_name or config.flow_id}",
                target_description=f"Schedule: {config.schedule_type.value}",
                risk_level=RiskLevel.LOW.value,
                additional_context={
                    "job_id": job_id,
                    "flow_id": config.flow_id,
                    "schedule_type": config.schedule_type.value,
                }
            )

        return job_id

    async def cancel_schedule(self, job_id: str) -> bool:
        """
        Cancela una tarea programada.

        Args:
            job_id: ID de la tarea a cancelar

        Returns:
            True si se canceló correctamente
        """
        if not self._scheduler:
            return False

        try:
            self._scheduler.remove_job(job_id)

            if self._audit_enabled:
                await enterprise_audit_service.log_event(
                    action_type="FLOW_SCHEDULE_CANCELLED",
                    module="scheduler_service",
                    source_description=f"Job: {job_id}",
                    risk_level=RiskLevel.LOW.value,
                    additional_context={"job_id": job_id}
                )

            return True
        except Exception as e:
            print(f"[SchedulerService] Error cancelando job {job_id}: {e}")
            return False

    async def pause_schedule(self, job_id: str) -> bool:
        """Pausa una tarea programada."""
        if not self._scheduler:
            return False
        try:
            self._scheduler.pause_job(job_id)
            return True
        except:
            return False

    async def resume_schedule(self, job_id: str) -> bool:
        """Reanuda una tarea pausada."""
        if not self._scheduler:
            return False
        try:
            self._scheduler.resume_job(job_id)
            return True
        except:
            return False

    async def get_scheduled_jobs(self) -> List[ScheduledJob]:
        """
        Obtiene todas las tareas programadas.

        Returns:
            Lista de ScheduledJob
        """
        if not self._scheduler:
            return []

        jobs = []
        for job in self._scheduler.get_jobs():
            # Extraer flow_id del job_id o args
            flow_id = 0
            if job.args and len(job.args) >= 1:
                flow_id = job.args[0]

            # Determinar tipo de schedule
            schedule_type = ScheduleType.ONCE
            if isinstance(job.trigger, IntervalTrigger):
                schedule_type = ScheduleType.INTERVAL
            elif isinstance(job.trigger, CronTrigger):
                schedule_type = ScheduleType.CRON

            jobs.append(ScheduledJob(
                job_id=job.id,
                flow_id=flow_id,
                flow_name=job.name.replace("Flow: ", ""),
                schedule_type=schedule_type,
                next_run=job.next_run_time,
                is_paused=job.next_run_time is None,
                run_count=self._run_counts.get(job.id, 0)
            ))

        return jobs

    async def get_next_run(self, flow_id: int) -> Optional[datetime]:
        """
        Obtiene la próxima ejecución programada de un flujo.

        Args:
            flow_id: ID del flujo

        Returns:
            Datetime de próxima ejecución o None
        """
        if not self._scheduler:
            return None

        for job in self._scheduler.get_jobs():
            if job.args and len(job.args) >= 1 and job.args[0] == flow_id:
                return job.next_run_time

        return None

    async def get_schedules_for_flow(self, flow_id: int) -> List[ScheduledJob]:
        """
        Obtiene todas las programaciones de un flujo específico.

        Args:
            flow_id: ID del flujo

        Returns:
            Lista de ScheduledJob para ese flujo
        """
        all_jobs = await self.get_scheduled_jobs()
        return [j for j in all_jobs if j.flow_id == flow_id]

    @property
    def is_running(self) -> bool:
        """Indica si el scheduler está activo."""
        return self._is_running


    async def _emit_scheduled_event(self, trigger_id: int, job_id: str):
        """
        Callback ejecutado por APScheduler para emitir un evento al bus.
        """
        try:
             from client_app.app.services.event_bus_service import event_bus_service
             
             execution_id = uuid.uuid4().hex
             meta = TriggerPayloadMeta(
                 trigger_id=trigger_id,
                 trigger_type="scheduler",
                 timestamp=datetime.utcnow(),
                 execution_id=execution_id
             )
             
             payload = SchedulerPayload(
                 meta=meta,
                 data={
                     "job_id": job_id,
                     "scheduled_time": datetime.utcnow().isoformat()
                 }
             )
             
             await event_bus_service.emit_trigger_event(
                 trigger_id=trigger_id, 
                 payload=payload.model_dump()
             )
             
             # Auditoría ligera
             if self._audit_enabled:
                pass # TODO: Add audit log if needed
             
        except Exception as e:
            print(f"[SchedulerService] Error emitting event for trigger {trigger_id}: {e}")

    async def start_trigger(self, trigger: TriggerConfig) -> tuple[bool, str]:
        """
        Inicia o actualiza un job programado basado en TriggerConfig.
        """
        if not self._scheduler or not self._is_running:
             await self.start()
             
        try:
            config = trigger.configuration
            job_id = f"trigger_{trigger.id}"
            
            # Construir trigger de APScheduler
            aps_trigger = None
            schedule_type = config.get("schedule_type")
            
            if schedule_type == "once":
                run_date = config.get("run_date")
                if not run_date:
                    return False, "run_date required for ONCE schedule"
                # Parse date if string? Assuming simplified format or isoformat handling?
                # DateTrigger accepts datetime, or string (if timezone aware?)
                # We should ensure run_date is datetime object if possible or string
                if isinstance(run_date, str):
                    run_date = datetime.fromisoformat(run_date)
                aps_trigger = DateTrigger(run_date=run_date)
                
            elif schedule_type == "interval":
                kwargs = {}
                if "interval_minutes" in config: kwargs["minutes"] = int(config["interval_minutes"])
                if "interval_hours" in config: kwargs["hours"] = int(config["interval_hours"])
                if "interval_days" in config: kwargs["days"] = int(config["interval_days"])
                
                if not kwargs:
                    return False, "Interval required"
                aps_trigger = IntervalTrigger(**kwargs)
                
            elif schedule_type == "cron":
                cron_expr = config.get("cron_expression")
                if not cron_expr:
                    return False, "Cron expression required"
                parts = cron_expr.split()
                if len(parts) != 5:
                    return False, "Invalid cron expression (5 parts required)"
                aps_trigger = CronTrigger(
                    minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4]
                )
                
            elif schedule_type == "daily":
                aps_trigger = CronTrigger(hour=config.get("hour", 9), minute=config.get("minute", 0))
                
            elif schedule_type == "weekly":
                day = config.get("day_of_week")
                if not day:
                    return False, "Day of week required"
                aps_trigger = CronTrigger(
                    hour=config.get("hour", 9), minute=config.get("minute", 0), day_of_week=day
                )
            
            else:
                return False, f"Unknown schedule type: {schedule_type}"
            
            # Añadir job
            self._scheduler.add_job(
                self._emit_scheduled_event,
                trigger=aps_trigger,
                args=[trigger.id, job_id],
                id=job_id,
                name=f"Trigger {trigger.id} ({schedule_type})",
                replace_existing=True
            )
            
            print(f"[SchedulerService] Trigger {trigger.id} scheduled/updated.")
            return True, "Scheduled"
            
        except Exception as e:
            return False, f"Failed to schedule trigger {trigger.id}: {e}"

    async def stop_watcher(self, trigger_id: int) -> bool:
        """Detiene (elimina) el job asociado al trigger."""
        job_id = f"trigger_{trigger_id}"
        return await self.cancel_schedule(job_id)

# Singleton
scheduler_service = SchedulerService()

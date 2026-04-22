"""
Servicio FolderWatcher - Gestión de Configuración y Ciclo de Vida

Administra las configuraciones de FolderWatcher, su ciclo de vida y el monitoreo de estado.
Proporciona la interfaz entre la UI y el módulo central de FolderWatcher.
"""
import asyncio
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime
from pathlib import Path
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.database.db import client_engine
from client_app.app.database.models import (
    TriggerConfig,
    FlowRegistry,
    ServerConnection,
    LocalCredentials
)
from client_app.app.modules.watchers.folder_watcher import FolderWatcher
from client_app.app.modules.output.email_sender import EmailSender
from client_app.app.core.hardware_fingerprint import get_machine_fingerprint
from client_app.app.modules.security.encryption_service import EncryptionService
from client_app.app.services.enterprise_audit_service import enterprise_audit_service
from automatia_shared.core.audit_models import RiskLevel


class FolderWatcherService:
    """
    Servicio para la gestión de instancias de FolderWatcher.
    Maneja el CRUD de configuraciones, la gestión del ciclo de vida (inicio/parada)
    y el monitoreo de salud de las rutas vigiladas.
    """

    def __init__(self):
        # Runtime state (not persisted)
        self._running_watchers: Dict[int, FolderWatcher] = {}  # config_id -> FolderWatcher
        self._watcher_tasks: Dict[int, asyncio.Task] = {}  # config_id -> Task
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Workflow engine reference (injected) - DEPRECATED for Watchers, reused for other services maybe
        self._workflow_engine = None

        # SSE: Callback system for real-time notifications
        self._status_callbacks: List[Callable] = []

    def set_workflow_engine(self, engine) -> None:
        """Inyecta la dependencia del motor de flujos de trabajo."""
        self._workflow_engine = engine

    # === SSE CALLBACKS ===

    def register_status_callback(self, callback: Callable) -> None:
        """Registra un callback para notificaciones de cambio de estado (SSE)."""
        if callback not in self._status_callbacks:
            self._status_callbacks.append(callback)

    def unregister_status_callback(self, callback: Callable) -> None:
        """Elimina el registro de un callback de estado."""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)

    async def _notify_status_change(self) -> None:
        """Notifica el cambio de estado global a todos los suscriptores SSE registrados."""
        if not self._status_callbacks:
            return

        try:
            status = await self.get_status()
            for callback in self._status_callbacks[:]:
                try:
                    await callback(status)
                except Exception:
                    self.unregister_status_callback(callback)
        except Exception as e:
            print(f"[FolderWatcherService] Error notifying status: {e}")

    # === CRUD OPERATIONS ===

    async def create_config(self, data: Dict[str, Any]) -> int:
        """
        Crea una nueva configuración usando TriggerConfig (V2).
        """
        import os
        watch_path = data.get("watch_path")
        if not watch_path or not os.path.isdir(watch_path):
             raise ValueError(f"La ruta especificada no existe o no es un directorio: {watch_path}")

        async with AsyncSession(client_engine) as session:
            # Create V2 TriggerConfig
            config = TriggerConfig(
                name=data["name"],
                description=data.get("description"),
                type="folder_watcher",
                status="CONFIGURED",
                is_active=False,
                configuration={
                    "watch_path": data["watch_path"],
                    "recursive": data.get("recursive", False),
                    "stabilization_seconds": data.get("stabilization_seconds", 2.0),
                    "auto_start": data.get("auto_start", False)
                },
                file_extensions=data.get("file_patterns", "*").split(',')
            )
            session.add(config)
            await session.commit()
            await session.refresh(config)

            print(f"[FolderWatcherService] TriggerConfig created: {config.name} (ID: {config.id})")
            return config.id

    async def get_config(self, config_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene configuración de TriggerConfig."""
        async with AsyncSession(client_engine) as session:
            trigger = await session.get(TriggerConfig, config_id)
            if not trigger or trigger.type != "folder_watcher":
                return None

            conf = trigger.configuration
            return {
                "id": trigger.id,
                "name": trigger.name,
                "description": trigger.description,
                "watch_path": conf.get("watch_path"),
                "file_patterns": ",".join(trigger.file_extensions or ["*"]),
                "recursive": conf.get("recursive", False),
                "stabilization_seconds": conf.get("stabilization_seconds", 2.0),
                "is_active": trigger.is_active,
                "auto_start": conf.get("auto_start", False),
                "is_paused": trigger.status == "PAUSED",
                "trigger_count": 0,
                "last_triggered_at": trigger.last_triggered,
                "last_error": trigger.last_error,
                "created_at": trigger.created_at,
            }

    async def list_configs(self) -> List[Dict[str, Any]]:
        """Lista todas las configuraciones de folder_watcher desde TriggerConfig."""
        async with AsyncSession(client_engine) as session:
            stmt = select(TriggerConfig).where(TriggerConfig.type == "folder_watcher")
            result = await session.exec(stmt)
            triggers = result.all()

            configs = []
            for t in triggers:
                conf = t.configuration or {}
                configs.append({
                    "id": t.id,
                    "name": t.name,
                    "watch_path": conf.get("watch_path", ""),
                    "file_patterns": ",".join(t.file_extensions or ["*"]),
                    "is_active": t.is_active,
                    "auto_start": conf.get("auto_start", False),
                    "is_paused": t.status == "PAUSED",
                    "trigger_count": 0,
                    "last_triggered_at": t.last_triggered,
                    "last_error": t.last_error,
                })

            return configs

    async def update_config(self, config_id: int, data: Dict[str, Any]) -> bool:
        """Actualiza configuración de TriggerConfig."""
        import os
        if "watch_path" in data:
            watch_path = data["watch_path"]
            if not watch_path or not os.path.isdir(watch_path):
                raise ValueError(f"La ruta especificada no existe o no es un directorio: {watch_path}")

        if config_id in self._running_watchers:
            return False  # Must stop first

        async with AsyncSession(client_engine) as session:
            trigger = await session.get(TriggerConfig, config_id)
            if not trigger or trigger.type != "folder_watcher":
                return False

            conf = trigger.configuration.copy() if trigger.configuration else {}
            if "name" in data: trigger.name = data["name"]
            if "watch_path" in data: conf["watch_path"] = data["watch_path"]
            if "recursive" in data: conf["recursive"] = data["recursive"]
            if "stabilization_seconds" in data: conf["stabilization_seconds"] = data["stabilization_seconds"]
            if "auto_start" in data: conf["auto_start"] = data["auto_start"]
            if "file_patterns" in data: trigger.file_extensions = data["file_patterns"].split(',')

            trigger.configuration = conf
            trigger.updated_at = datetime.utcnow()
            session.add(trigger)
            await session.commit()
            return True

    async def delete_config(self, config_id: int) -> bool:
        """Elimina configuración de TriggerConfig."""
        if config_id in self._running_watchers:
            await self.stop_watcher(config_id)

        async with AsyncSession(client_engine) as session:
            trigger = await session.get(TriggerConfig, config_id)
            if not trigger or trigger.type != "folder_watcher":
                return False

            await session.delete(trigger)
            await session.commit()
            return True

    # === LIFECYCLE MANAGEMENT ===

    async def start_trigger(self, trigger: TriggerConfig) -> tuple[bool, str]:
        """
        Inicia un FolderWatcher basado en TriggerConfig (Nueva Arquitectura).
        """
        # Check if already running
        if trigger.id in self._running_watchers:
             return True, "Watcher is already running"
             
        # Config extraction
        config_data = trigger.configuration
        watch_path_str = config_data.get("watch_path")
        
        if not watch_path_str:
            return False, "Watch path not configured"
            
        watch_path = Path(watch_path_str)
        if not watch_path.exists():
            return False, f"Path does not exist: {watch_path}"
            
        try:
            # Create Watcher
            patterns = trigger.file_extensions or ["*"]
            
            watcher = FolderWatcher(
                 watch_directory=watch_path,
                 trigger_id=trigger.id,
                 file_patterns=patterns,
                 stabilization_time=config_data.get("stabilization_seconds", 2.0),
                 recursive=config_data.get("recursive", False)
            )
            
            task = asyncio.create_task(watcher.start_monitoring())
            
            self._running_watchers[trigger.id] = watcher
            self._watcher_tasks[trigger.id] = task
            
            print(f"[FolderWatcherService] Started watcher for trigger {trigger.id}")
            await self._notify_status_change()
            return True, "Started"
            
        except Exception as e:
            print(f"[FolderWatcherService] Failed to start trigger {trigger.id}: {e}")
            return False, str(e)

    async def stop_watcher(self, config_id: int) -> tuple[bool, str]:
        """
        Detiene un watcher en ejecución de forma segura.
        Cancela la tarea de asyncio. DB updates are handled by TriggerLifecycleManager.
        """
        if config_id not in self._running_watchers:
            return False, "Watcher is not running"

        try:
            watcher = self._running_watchers[config_id]
            task = self._watcher_tasks.get(config_id)

            # Stop watcher internal loop
            watcher.stop()

            # Cancel asyncio task
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            # Cleanup state
            del self._running_watchers[config_id]
            if config_id in self._watcher_tasks:
                del self._watcher_tasks[config_id]

            print(f"[FolderWatcherService] Stopped watcher: {config_id}")
            await self._notify_status_change()
            return True, "Watcher stopped successfully"

        except Exception as e:
            print(f"[FolderWatcherService] Error stopping watcher {config_id}: {e}")
            return False, f"Error stopping: {e}"

    async def stop_all(self) -> int:
        """Detiene todos los watchers que se encuentren activos en el sistema."""
        count = 0
        # Iterate copy of keys since dictionary changes during iteration
        for cid in list(self._running_watchers.keys()):
            success, _ = await self.stop_watcher(cid)
            if success:
                count += 1
        return count

    async def start_all_autostart(self) -> int:
        """Inicia automáticamente todos los folder_watchers marcados con auto_start."""
        count = 0
        triggers_to_start = []

        async with AsyncSession(client_engine) as session:
            stmt = select(TriggerConfig).where(
                TriggerConfig.type == "folder_watcher"
            )
            result = await session.exec(stmt)
            for trigger in result.all():
                conf = trigger.configuration or {}
                if conf.get("auto_start", False) and trigger.id not in self._running_watchers:
                    triggers_to_start.append(trigger)

        for trigger in triggers_to_start:
            success, _ = await self.start_trigger(trigger)
            if success:
                count += 1

        return count

    async def start_heartbeat(self):
        """
        Inicia la tarea periódica de 'latido' (heartbeat).
        Verifica la salud de las rutas cada 60 segundos y gestiona alertas de desconexión.
        """
        if self._heartbeat_task and not self._heartbeat_task.done():
            return # Already running

        async def _heartbeat_loop():
            while True:
                try:
                    await asyncio.sleep(60)
                    active_count = len(self._running_watchers)
                    if active_count > 0:
                        print(f"[FolderWatcherService] Heartbeat: {active_count} active watchers")
                        await self.check_all_paths_health()
                    else:
                        # Even if no active watchers, still verify connectivity for paused monitors
                        await self.verify_connectivity()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"[FolderWatcherService] Heartbeat error: {e}")
                    await asyncio.sleep(60) # Wait before retry

        self._heartbeat_task = asyncio.create_task(_heartbeat_loop())
        print("[FolderWatcherService] Heartbeat started")

    async def verify_connectivity(self):
        """
        Verifica la conectividad de todas las rutas monitorizadas (activas y pausadas).
        Actualiza el estado visual en la base de datos sin alterar el ciclo de vida de los watchers.
        """
        import os

        async with AsyncSession(client_engine) as session:
            stmt = select(TriggerConfig).where(TriggerConfig.type == "folder_watcher")
            result = await session.exec(stmt)
            all_triggers = result.all()

            if not all_triggers:
                return

            for trigger in all_triggers:
                conf = trigger.configuration or {}
                watch_path = conf.get("watch_path", "")
                path_exists = os.path.isdir(watch_path) if watch_path else False

                if not path_exists and (not trigger.last_error or "Ruta no accesible" not in (trigger.last_error or "")):
                    error_msg = f"Ruta no accesible: '{watch_path}'"
                    trigger.last_error = error_msg
                    print(f"[FolderWatcherService] Connectivity issue detected: {error_msg}")
                elif path_exists and trigger.last_error and "Ruta no accesible" in trigger.last_error:
                    trigger.last_error = None

                trigger.updated_at = datetime.utcnow()
                session.add(trigger)

            await session.commit()

    async def check_all_paths_health(self):
        """
        Verifica la integridad física de las rutas monitorizadas que están activas.
        Si una ruta deja de estar disponible (ej. desconexión de red):
        1. Detiene el watcher en memoria.
        2. Registra el error en la base de datos.
        3. Envía una alerta por email a los administradores y partners.
        """
        import os

        async with AsyncSession(client_engine) as session:
            # 1. Obtener triggers activos de tipo folder_watcher
            stmt = select(TriggerConfig).where(
                TriggerConfig.type == "folder_watcher",
                TriggerConfig.is_active == True
            )
            result = await session.exec(stmt)
            active_triggers = result.all()

            if not active_triggers:
                return

            # 2. Obtener contactos (ServerConnection)
            server_stmt = select(ServerConnection)
            server_result = await session.exec(server_stmt)
            server_conn = server_result.first()

            # 3. Obtener credenciales SMTP
            smtp_stmt = select(LocalCredentials).where(LocalCredentials.service_type == "SMTP")
            smtp_result = await session.exec(smtp_stmt)
            smtp_creds_record = smtp_result.first()

            for trigger in active_triggers:
                conf = trigger.configuration or {}
                watch_path = conf.get("watch_path", "")

                if not watch_path or not os.path.isdir(watch_path):
                    error_msg = f"Error: La ruta '{watch_path}' no existe en el disco"
                    print(f"[FolderWatcherService] ALERT: {error_msg}")

                    # Detener watcher en memoria
                    if trigger.id in self._running_watchers:
                        watcher = self._running_watchers.pop(trigger.id)
                        watcher.stop()

                    # Actualizar DB
                    trigger.is_active = False
                    trigger.last_error = error_msg
                    trigger.updated_at = datetime.utcnow()
                    session.add(trigger)

                    # Enviar Alerta por Email
                    if server_conn and smtp_creds_record:
                        try:
                            try:
                                encryption_service = EncryptionService()
                                creds_data = encryption_service.decrypt(smtp_creds_record.encrypted_data)
                            except Exception as decrypt_error:
                                security_error_msg = f"Error de seguridad: No se pudieron descifrar las credenciales SMTP - {type(decrypt_error).__name__}"
                                print(f"[FolderWatcherService] SECURITY ERROR: {security_error_msg}")

                                await enterprise_audit_service.log_event(
                                    action_type="SECURITY_DECRYPTION_FAILURE",
                                    module="folder_watcher_service",
                                    source_description=f"Trigger: {trigger.name} (ID: {trigger.id})",
                                    target_description="SMTP credentials decryption",
                                    risk_level=RiskLevel.CRITICAL.value,
                                    additional_context={
                                        "error_type": type(decrypt_error).__name__,
                                        "trigger_id": trigger.id,
                                        "action": "health_check_alert"
                                    },
                                    security_flags={"decryption_failed": True, "monitoring_stopped": True}
                                )

                                if trigger.id in self._running_watchers:
                                    watcher = self._running_watchers.pop(trigger.id)
                                    watcher.stop()
                                    trigger.is_active = False
                                    trigger.last_error = security_error_msg
                                    session.add(trigger)

                                continue

                            sender = EmailSender(creds_data)
                            machine_id = get_machine_fingerprint()
                            client_name = server_conn.client_email.split('@')[0] if server_conn.client_email else "Cliente Gov Gen AI"

                            to_addrs = []
                            if server_conn.client_email: to_addrs.append(server_conn.client_email)
                            if server_conn.partner_email: to_addrs.append(server_conn.partner_email)

                            if to_addrs:
                                subject = f"[ALERTA] Monitor de Carpeta Desconectado - {client_name}"
                                body = f"""
                                <h2>Alerta de Infraestructura - Gov Gen AI</h2>
                                <p>Se ha detectado que una carpeta monitorizada ya no es accesible.</p>
                                <ul>
                                    <li><b>Nombre:</b> {trigger.name}</li>
                                    <li><b>Ruta:</b> {watch_path}</li>
                                    <li><b>Máquina (ID):</b> {machine_id}</li>
                                    <li><b>Fecha:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</li>
                                </ul>
                                <p>Por favor, verifique la conexión del disco o la disponibilidad de la ruta de red.</p>
                                """
                                sender.send(
                                    from_addr=creds_data.get("username", "alerts@automatia.es"),
                                    to_addrs=to_addrs,
                                    subject=subject,
                                    body=body,
                                    html=True
                                )
                                print(f"[FolderWatcherService] Alert email sent to {to_addrs}")
                        except Exception as ee:
                            print(f"[FolderWatcherService] Error sending alert email: {ee}")

            await session.commit()

    async def stop_heartbeat(self):
        """Detiene de forma segura la tarea de fondo del heartbeat."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            print("[FolderWatcherService] Heartbeat stopped")

    async def get_status(self) -> Dict[str, Any]:
        """
        Retorna un resumen del estado global del servicio de monitoreo.
        Incluye el número de watchers activos y sus identificadores.
        """
        return {
            "active_watchers": len(self._running_watchers),
            "running_config_ids": list(self._running_watchers.keys()),
            "last_heartbeat": datetime.utcnow()
        }

# Singleton instance
folder_watcher_service = FolderWatcherService()

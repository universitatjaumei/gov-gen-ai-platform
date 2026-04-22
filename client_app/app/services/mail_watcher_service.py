"""
Servicio MailWatcher - Gestión de Configuración y Estado del Monitor de Email

Administra la configuración del EmailWatcher, las credenciales y el estado de ejecución.
Proporciona la interfaz entre la UI y el módulo central de monitoreo de correo.
"""
import json
import asyncio
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime
from pathlib import Path
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.database.db import client_engine
from client_app.app.database.models import LocalCredentials, FlowRegistry, TaskLog, MailWatcherState, TriggerConfig
from client_app.app.modules.watchers.email_watcher import EmailWatcher
from shared.automatia_shared.core.execution_manager import ExecutionPathManager


from client_app.app.services.connection_logger_service import log_connection_event, log_connection_error, log_email_trigger

class MailWatcherService:
    # ... existing methods ...

    async def start_watcher(self, config: dict, auto_start: bool = False):
        # ... logic ...
        await log_connection_event('email', f"IMAP: {config.get('folder')}", 'connect', 'success', 'Monitor de email iniciado')
        # ...

    async def stop_watcher(self):
        # ... logic ...
        await log_connection_event('email', f"IMAP", 'disconnect', 'success', 'Monitor deteniddo')
        # ...

    async def _poll_imap(self):
        # ... try ...
        await log_connection_error('email', 'IMAP Polling', str(e))
        # ...
    """
    Servicio encargado de gestionar el proceso de fondo MailWatcher.
    Maneja la persistencia de configuraciones, el ciclo de vida del monitor
    y la integración con el motor de flujos de trabajo.
    """
    
    CONFIG_SERVICE_NAME = "mail_watcher_config"
    
    def __init__(self):
        # Legacy Single Instance
        self.watcher: Optional[EmailWatcher] = None
        self.is_running: bool = False
        self.background_task: Optional[asyncio.Task] = None # Renamed from watcher_task in legacy
        self.watcher_task: Optional[asyncio.Task] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # New Multi-Instance Support
        self._running_watchers: Dict[int, EmailWatcher] = {} # trigger_id -> EmailWatcher
        self._watcher_tasks: Dict[int, asyncio.Task] = {}   # trigger_id -> Task
        
        self.path_manager = ExecutionPathManager()
        
        # SSE: Callback system for real-time notifications
        self.status_callbacks: List[Callable] = []
    
    def register_status_callback(self, callback: Callable) -> None:
        """Registra un callback para recibir notificaciones de cambio de estado vía SSE."""
        if callback not in self.status_callbacks:
            self.status_callbacks.append(callback)
    
    def unregister_status_callback(self, callback: Callable) -> None:
        """Elimina la suscripción de un callback de estado."""
        if callback in self.status_callbacks:
            self.status_callbacks.remove(callback)
    
    async def _notify_status_change(self) -> None:
        """Notifica el estado actualizado a todos los clientes SSE conectados."""
        if not self.status_callbacks:
            return
        
        try:
            status = await self.get_status()
            for callback in self.status_callbacks[:]:  # Copia para evitar modificaciones durante la iteración
                try:
                    await callback(status)
                except Exception:
                    # El cliente probablemente se desconectó, eliminar el callback
                    self.unregister_status_callback(callback)
        except Exception as e:
            print(f"[MailWatcherService] Error notifying status change: {e}")
    
    async def save_config(self, config: Dict[str, Any]) -> None:
        """
        Persiste la configuración global del MailWatcher en la base de datos.
        
        Args:
            config: Diccionario con credential_id, carpeta IMAP, intervalo de chequeo,
                    filtros de remitente y filtros de contenido (asunto, adjuntos).
        """
        async with AsyncSession(client_engine) as session:
            # Check if config exists
            stmt = select(LocalCredentials).where(
                LocalCredentials.service_name == self.CONFIG_SERVICE_NAME
            )
            result = await session.exec(stmt)
            existing = result.first()
            
            # Store as plain JSON (not encrypted, just config)
            config_json = json.dumps(config)
            
            if existing:
                existing.encrypted_data = config_json
                existing.updated_at = datetime.utcnow()
                session.add(existing)
            else:
                cred = LocalCredentials(
                    service_name=self.CONFIG_SERVICE_NAME,
                    encrypted_data=config_json
                )
                session.add(cred)
            
            await session.commit()
            print(f"[MailWatcherService] Configuration saved")
    
    async def load_config(self) -> Optional[Dict[str, Any]]:
        """Carga la configuración del MailWatcher desde la base de datos local."""
        async with AsyncSession(client_engine) as session:
            stmt = select(LocalCredentials).where(
                LocalCredentials.service_name == self.CONFIG_SERVICE_NAME
            )
            result = await session.exec(stmt)
            config_record = result.first()
            
            if config_record:
                return json.loads(config_record.encrypted_data)
            
            return None
    
    async def save_credential(
        self,
        name: str,
        server: str,
        port: int,
        username: str,
        password: str,
        use_ssl: bool = True,
        service_type: str = "IMAP"
    ) -> int:
        """
        Guarda credenciales de servidor de correo de forma cifrada en la base de datos.
        
        Args:
            name: Nombre identificativo de la credencial.
            server: Dirección del servidor (host).
            port: Puerto de conexión.
            username: Nombre de usuario/email.
            password: Contraseña del servicio.
            use_ssl: Indica si se debe usar conexión cifrada (SSL/TLS).
            service_type: Tipo de servicio ('IMAP' o 'SMTP').
        
        Returns:
            ID de la credencial creada.
        """
        from client_app.app.modules.security.encryption_service import EncryptionService
        
        async with AsyncSession(client_engine) as session:
            # Encrypt credentials
            cred_data = {
                "server": server,
                "port": port,
                "user": username,
                "password": password,
                "use_ssl": use_ssl
            }
            
            encryption = EncryptionService()
            encrypted_data = encryption.encrypt(cred_data)
            
            cred = LocalCredentials(
                service_name=f"{service_type.lower()}_{name}",
                service_type=service_type,
                encrypted_data=encrypted_data
            )
            session.add(cred)
            await session.commit()
            await session.refresh(cred)
            
            print(f"[MailWatcherService] {service_type} credential saved: {name}")
            return cred.id
    
    async def get_credential(self, credential_id: int) -> Optional[Dict[str, Any]]:
        """Recupera y descifra los datos de una credencial por su ID."""
        # Evitar warning de SQLAlchemy "fully NULL primary key identity"
        if credential_id is None:
            return None

        from client_app.app.modules.security.encryption_service import EncryptionService

        async with AsyncSession(client_engine) as session:
            cred = await session.get(LocalCredentials, credential_id)
            if cred:
                encryption = EncryptionService()
                return encryption.decrypt(cred.encrypted_data)
            return None
    
    async def list_credentials(self, service_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lista las credenciales registradas, con posibilidad de filtrar por tipo de servicio.
        """
        async with AsyncSession(client_engine) as session:
            stmt = select(LocalCredentials)
            if service_type:
                stmt = stmt.where(LocalCredentials.service_type == service_type)
            
            result = await session.exec(stmt)
            credentials = result.all()
            
            return [
                {
                    "id": cred.id,
                    "name": cred.service_name.replace("imap_", "").replace("smtp_", ""),
                    "service_type": cred.service_type,
                    "created_at": cred.created_at
                }
                for cred in credentials
            ]

    async def update_credential(
        self,
        credential_id: int,
        name: Optional[str] = None,
        server: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_ssl: Optional[bool] = None,
        service_type: Optional[str] = None
    ) -> bool:
        """
        Actualiza una credencial existente, re-cifrando los datos si es necesario.
        
        Args:
            credential_id: ID de la credencial a modificar.
            name: Nuevo nombre (opcional).
            server: Nuevo servidor (opcional).
            port: Nuevo puerto (opcional).
            username: Nuevo usuario (opcional).
            password: Nueva contraseña (opcional).
            use_ssl: Nueva configuración SSL (opcional).
            service_type: Nuevo tipo de servicio (opcional).
        
        Returns:
            True si la actualización fue exitosa.
        """
        from client_app.app.modules.security.encryption_service import EncryptionService
        
        async with AsyncSession(client_engine) as session:
            # Get existing credential
            cred = await session.get(LocalCredentials, credential_id)
            if not cred:
                return False
            
            # Decrypt current credentials
            encryption = EncryptionService()
            current_data = encryption.decrypt(cred.encrypted_data)
            
            # Update with new values (if provided)
            if server is not None:
                current_data["server"] = server
            if port is not None:
                current_data["port"] = port
            if username is not None:
                current_data["user"] = username
            if password is not None:
                current_data["password"] = password
            if use_ssl is not None:
                current_data["use_ssl"] = use_ssl
            
            # Re-encrypt with updated data
            encrypted_data = encryption.encrypt(current_data)
            
            # Update the record
            cred.encrypted_data = encrypted_data
            if name:
                cred.service_name = f"{service_type.lower() if service_type else cred.service_type.lower()}_{name}"
            if service_type:
                cred.service_type = service_type
            
            await session.commit()
            return True

    async def delete_credential(self, credential_id: int) -> bool:
        """Elimina una credencial de la base de datos por su ID."""
        async with AsyncSession(client_engine) as session:
            cred = await session.get(LocalCredentials, credential_id)
            if not cred:
                return False
            
            await session.delete(cred)
            await session.commit()
            return True

    # --- COMPATIBILITY ALIASES ---
    async def save_imap_credential(self, *args, **kwargs):
        """Deprecated alias for save_credential(..., service_type='IMAP')"""
        return await self.save_credential(*args, **kwargs, service_type="IMAP")

    async def get_imap_credential(self, *args, **kwargs):
        """Deprecated alias for get_credential"""
        return await self.get_credential(*args, **kwargs)

    async def list_imap_credentials(self):
        """Deprecated alias for list_credentials(service_type='IMAP')"""
        return await self.list_credentials(service_type="IMAP")
    
    async def test_imap_connection(self, credential_id: int) -> tuple[bool, str]:
        """
        Prueba la conexión IMAP con las credenciales indicadas.
        Utiliza un hilo secundario para evitar bloquear el bucle de eventos de asyncio.
        
        Returns:
            Tupla (éxito, mensaje_de_log).
        """
        try:
            cred_data = await self.get_imap_credential(credential_id)
            if not cred_data:
                return False, "Credential not found"
            
            # Create temporary watcher just for testing
            from imapclient import IMAPClient
            
            server = cred_data.get("server")
            user = cred_data.get("user")
            password = cred_data.get("password")
            
            # Test connection (blocking operation)
            def _test_sync():
                client = IMAPClient(server, use_uid=True)
                client.login(user, password)
                client.logout()
            
            await asyncio.to_thread(_test_sync)
            
            return True, f"Successfully connected to {server}"
            
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
            
    async def test_smtp_connection(self, credential_id: int) -> tuple[bool, str]:
        """
        Prueba la conexión SMTP (servidor de salida) con las credenciales indicadas.
        Soporta conexiones directas SSL (puerto 465) y STARTTLS (puerto 587).
        
        Returns:
            Tupla (éxito, mensaje_de_log).
        """
        try:
            cred_data = await self.get_credential(credential_id)
            if not cred_data:
                return False, "Credential not found"
            
            import smtplib
            import ssl
            
            server = cred_data.get("server")
            port = cred_data.get("port", 587)
            user = cred_data.get("user")
            password = cred_data.get("password")
            use_ssl = cred_data.get("use_ssl", True)
            
            def _test_sync():
                if use_ssl and port == 465:
                    context = ssl.create_default_context()
                    with smtplib.SMTP_SSL(server, port, context=context) as client:
                        client.login(user, password)
                else:
                    with smtplib.SMTP(server, port) as client:
                        if use_ssl:
                            client.starttls()
                        client.login(user, password)
            
            await asyncio.to_thread(_test_sync)
            return True, f"Successfully connected to SMTP {server}"
            
        except Exception as e:
            return False, f"SMTP Connection failed: {str(e)}"

    async def test_connection(self, credential_id: int) -> tuple[bool, str]:
        """
        Prueba la conexión basándose en el tipo de servicio de la credencial (IMAP o SMTP).
        """
        async with AsyncSession(client_engine) as session:
            cred = await session.get(LocalCredentials, credential_id)
            if not cred:
                return False, "Credential not found"
            
            if cred.service_type == "IMAP":
                return await self.test_imap_connection(credential_id)
            elif cred.service_type == "SMTP":
                return await self.test_smtp_connection(credential_id)
            else:
                return False, f"Unsupported service type: {cred.service_type}"
    
    async def _update_state(self, **kwargs) -> None:
        """Actualiza el estado del monitor en la base de datos y notifica a los suscriptores SSE."""
        async with AsyncSession(client_engine) as session:
            state = await session.get(MailWatcherState, 1)
            if not state:
                state = MailWatcherState(id=1)
            
            for key, value in kwargs.items():
                setattr(state, key, value)
            
            state.updated_at = datetime.utcnow()
            session.add(state)
            await session.commit()
        
        # SSE: Notify clients of state change
        await self._notify_status_change()
    
    async def _heartbeat_updater(self) -> None:
        """Tarea de fondo que actualiza el 'latido' de actividad cada 30 segundos."""
        while self.is_running:
            try:
                await self._update_state(last_heartbeat=datetime.utcnow())
                await asyncio.sleep(30)
            except Exception as e:
                print(f"[MailWatcherService] Heartbeat error: {e}")
                await asyncio.sleep(30)
    
    async def start_watcher(self, config: Dict[str, Any], auto_start: bool = False) -> tuple[bool, str]:
        """
        Inicia la tarea de fondo del EmailWatcher.
        Valida credenciales y configuración del flujo antes de arrancar.
        
        Args:
            config: Diccionario de configuración.
            auto_start: Si es True, el monitor se iniciará automáticamente al arrancar la app.
        
        Returns:
            Tupla (éxito, mensaje).
        """
        if self.is_running:
            return False, "Watcher is already running"
        
        try:
            # Get credentials
            credential_id = config.get("credential_id")
            cred_data = await self.get_imap_credential(credential_id)
            if not cred_data:
                return False, "IMAP credentials not found"
            
            # Get workflow
            flow_id = config.get("flow_id")
            async with AsyncSession(client_engine) as session:
                flow = await session.get(FlowRegistry, flow_id)
                if not flow:
                    return False, f"Workflow {flow_id} not found"
            
            # Get base directory (execution_dir)
            # Get base directory (execution_dir)
            # Use PathManager for consistency
            base_dir = self.path_manager.executions_base
            base_dir.mkdir(parents=True, exist_ok=True)
            
            # Create EmailWatcher instance
            # Note: workflow_engine needs to be injected
            from client_app.app.core.state import state
            
            self.watcher = EmailWatcher(
                credentials=cred_data,
                path_manager=self.path_manager,
                workflow_engine=state.workflow_engine,  # Assuming this exists in state
                flow_id=str(flow_id),
                whitelist_senders=config.get("whitelist_senders", []),
                subject_filter=config.get("subject_filter"),
                folder=config.get("folder", "INBOX"),
                check_interval=config.get("check_interval", 60)
            )
            
            # Start background tasks
            self.watcher_task = asyncio.create_task(self._run_watcher_loop())
            self.heartbeat_task = asyncio.create_task(self._heartbeat_updater())
            self.is_running = True
            
            # Update state
            await self._update_state(
                is_enabled=True,
                is_running=True,
                auto_start=auto_start,
                error_count=0,
                last_error=None
            )
            
            # SSE notification already called by _update_state
            
            print(f"[MailWatcherService] Watcher started (auto_start={auto_start})")
            return True, "MailWatcher started successfully"
            
        except Exception as e:
            return False, f"Failed to start watcher: {str(e)}"
    
    async def _run_watcher_loop(self) -> None:
        """Bucle principal de ejecución del monitor con recuperación automática de errores."""
        consecutive_errors = 0
        max_errors = 5
        
        try:
            await self.watcher.connect()
            
            while self.is_running:
                try:
                    emails = await self.watcher.fetch_new_emails()
                    
                    for email in emails:
                        await self.watcher.process_email(email)
                    
                    # Reset error count on success
                    if consecutive_errors > 0:
                        consecutive_errors = 0
                        await self._update_state(error_count=0, last_error=None)
                    
                    await asyncio.sleep(self.watcher.check_interval)
                    
                except Exception as e:
                    consecutive_errors += 1
                    error_msg = f"Error in watcher loop: {str(e)}"
                    print(f"[MailWatcherService] {error_msg} (attempt {consecutive_errors}/{max_errors})")
                    
                    await self._update_state(
                        error_count=consecutive_errors,
                        last_error=error_msg
                    )
                    
                    if consecutive_errors >= max_errors:
                        print(f"[MailWatcherService] Max errors reached, stopping watcher")
                        self.is_running = False
                        await self._update_state(is_enabled=False, is_running=False)
                        break
                    
                    # Exponential backoff: 2^n seconds, max 5 minutes
                    wait_time = min(2 ** consecutive_errors, 300)
                    print(f"[MailWatcherService] Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
        
        except Exception as e:
            error_msg = f"Fatal error in watcher: {str(e)}"
            print(f"[MailWatcherService] {error_msg}")
            await self._update_state(is_enabled=False, is_running=False, last_error=error_msg)
            self.is_running = False
        finally:
            if self.watcher:
                await self.watcher.disconnect()
    
    async def start_trigger(self, trigger: TriggerConfig) -> tuple[bool, str]:
        """
        Inicia un watcher específico para un TriggerConfig.
        """
        if trigger.id in self._running_watchers:
            return True, "Watcher already running"
            
        try:
            config = trigger.configuration
            credential_id = config.get("credential_id")
            
            # Resolve credentials (using encryption service via helper)
            cred_data = await self.get_imap_credential(credential_id)
            if not cred_data:
                return False, f"Credentials not found for trigger {trigger.id}"

            watcher = EmailWatcher(
                credentials=cred_data,
                path_manager=self.path_manager,
                trigger_id=trigger.id,
                whitelist_senders=config.get("whitelist_senders", []),
                subject_filter=config.get("subject_filter"),
                folder=config.get("folder", "INBOX"),
                check_interval=config.get("check_interval", 60)
            )

            self._running_watchers[trigger.id] = watcher
            task = asyncio.create_task(self._run_trigger_loop(trigger.id, watcher))
            self._watcher_tasks[trigger.id] = task
            
            return True, "Started"
            
        except Exception as e:
            return False, f"Failed to start trigger {trigger.id}: {e}"

    async def _run_trigger_loop(self, trigger_id: int, watcher: EmailWatcher):
        """
        Loop para un watcher específico.
        """
        consecutive_errors = 0
        try:
            await watcher.connect()
            while trigger_id in self._running_watchers:
                try:
                    emails = await watcher.fetch_new_emails()
                    for email in emails:
                        await watcher.process_email(email)
                    
                    consecutive_errors = 0
                    await asyncio.sleep(watcher.check_interval)
                    
                except Exception as e:
                    consecutive_errors += 1
                    print(f"[MailWatcherService] Error in trigger {trigger_id}: {e}")
                    wait_time = min(2 ** consecutive_errors, 300)
                    await asyncio.sleep(wait_time)
        except Exception as e:
            print(f"[MailWatcherService] Fatal error in trigger {trigger_id}: {e}")
        finally:
            await watcher.disconnect()
            if trigger_id in self._running_watchers:
                del self._running_watchers[trigger_id]
                # We should notify LifecycleManager or update DB status ideally.
                # But LifecycleManager monitors status or assumes it runs unless stopped?
                # For now, simplistic handling.

    async def stop_watcher(self, trigger_id: Optional[int] = None) -> tuple[bool, str]:
        """
        Detiene un watcher. 
        Si trigger_id es None, detiene el watcher Legacy.
        Si trigger_id es int, detiene el watcher específico.
        """
        if trigger_id is not None:
            # Stop specific trigger watcher
            if trigger_id not in self._running_watchers:
                return False, "Watcher not found"
            
            # Remove from dict to signal loop termination
            watcher = self._running_watchers.pop(trigger_id, None) 
            task = self._watcher_tasks.pop(trigger_id, None)
            
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            if watcher:
                await watcher.disconnect()
                
            return True, "Stopped"
            
        else:
            # Stop Legacy Watcher
            if not self.is_running:
                return False, "Watcher is not running"
            
            try:
                self.is_running = False
                
                # Cancel tasks
                if self.watcher_task:
                    self.watcher_task.cancel()
                    try:
                        await self.watcher_task
                    except asyncio.CancelledError:
                        pass
                
                if self.heartbeat_task:
                    self.heartbeat_task.cancel()
                    try:
                        await self.heartbeat_task
                    except asyncio.CancelledError:
                        pass
                
                self.watcher = None
                self.watcher_task = None
                self.heartbeat_task = None
                
                # Update state
                await self._update_state(
                    is_enabled=False,
                    is_running=False
                )
                
                print("[MailWatcherService] Legacy Watcher stopped")
                return True, "MailWatcher stopped successfully"
                
            except Exception as e:
                return False, f"Failed to stop watcher: {str(e)}"

    # --- CRUD METHODS FOR TRIGGER CONFIG (V2) ---
    async def create_config(self, data: Dict[str, Any]) -> int:
        """Crea una nueva configuración de Email Trigger."""
        async with AsyncSession(client_engine) as session:
            trigger = TriggerConfig(
                name=data.get("name", "Email Monitor"),
                description=data.get("description"),
                type="email_watcher",
                status="CONFIGURED",
                is_active=False,
                configuration={
                    "credential_id": data.get("credential_id"),
                    "folder": data.get("folder", "INBOX"),
                    "check_interval": data.get("check_interval", 60),
                    "subject_filter": data.get("subject_filter"),
                    "whitelist_senders": data.get("whitelist_senders", []),
                    "process_attachments": data.get("process_attachments", False),
                    "allowed_extensions": data.get("allowed_extensions", [])
                }
            )
            session.add(trigger)
            await session.commit()
            await session.refresh(trigger)
            
            print(f"[MailWatcherService] TriggerConfig created: {trigger.name} (ID: {trigger.id})")
            return trigger.id

    async def get_config(self, config_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene configuración de Email Trigger."""
        async with AsyncSession(client_engine) as session:
            trigger = await session.get(TriggerConfig, config_id)
            if not trigger or trigger.type != "email_watcher":
                return None
            
            c = trigger.configuration
            return {
                "id": trigger.id,
                "name": trigger.name,
                "description": trigger.description,
                "credential_id": c.get("credential_id"),
                "folder": c.get("folder"),
                "check_interval": c.get("check_interval"),
                "subject_filter": c.get("subject_filter"),
                "whitelist_senders": c.get("whitelist_senders"),
                "process_attachments": c.get("process_attachments"),
                "allowed_extensions": c.get("allowed_extensions"),
                "is_active": trigger.is_active,
                "last_triggered_at": trigger.last_triggered,
                "created_at": trigger.created_at,
                "updated_at": trigger.updated_at
            }

    async def list_configs(self) -> List[Dict[str, Any]]:
        """Lista configuraciones de Email Trigger."""
        async with AsyncSession(client_engine) as session:
            stmt = select(TriggerConfig).where(TriggerConfig.type == "email_watcher")
            result = await session.exec(stmt)
            triggers = result.all()
            
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "folder": t.configuration.get("folder"),
                    "credential_id": t.configuration.get("credential_id"),
                    "check_interval": t.configuration.get("check_interval"),
                    "is_active": t.is_active,
                    "last_triggered_at": t.last_triggered
                }
                for t in triggers
            ]

    async def update_config(self, config_id: int, data: Dict[str, Any]) -> bool:
        """Actualiza configuración de Email Trigger."""
        if config_id in self._running_watchers:
            return False # Must stop first

        async with AsyncSession(client_engine) as session:
            trigger = await session.get(TriggerConfig, config_id)
            if not trigger or trigger.type != "email_watcher":
                return False

            conf = trigger.configuration.copy()
            if "name" in data: trigger.name = data["name"]
            if "description" in data: trigger.description = data["description"]
            
            for key in ["credential_id", "folder", "check_interval", "subject_filter", "whitelist_senders", "process_attachments", "allowed_extensions"]:
                if key in data:
                    conf[key] = data[key]
            
            trigger.configuration = conf
            trigger.updated_at = datetime.utcnow()
            session.add(trigger)
            await session.commit()
            return True

    async def delete_config(self, config_id: int) -> bool:
        """Elimina configuración de Email Trigger."""
        await self.stop_watcher(trigger_id=config_id)
        
        async with AsyncSession(client_engine) as session:
            trigger = await session.get(TriggerConfig, config_id)
            if not trigger or trigger.type != "email_watcher":
                return False
            
            await session.delete(trigger)
            await session.commit()
            return True

# Singleton instance
mail_watcher_service = MailWatcherService()

"""
Servicio WebWatcher - Monitoreo de URLs con detección de cambios.
Gestiona el ciclo de vida de los observadores (watchers), su configuración e historial de cambios.
Proporciona la interfaz principal entre la UI y el módulo de bajo nivel web_watcher.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict, List, Any, Callable, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from playwright.async_api import async_playwright

from client_app.app.database.db import client_engine
from client_app.app.database.models import (
    WebWatcherHistory,
    FlowRegistry,
    TriggerConfig
)
from client_app.app.modules.watchers.web_watcher import (
    check_url_changes,
    validate_selector,
    generate_text_diff,
    generate_html_diff
)
from shared.automatia_shared.dtos import TriggerPayloadMeta, WebWatcherPayload
import uuid


from client_app.app.services.connection_logger_service import log_connection_event, log_connection_error


@asynccontextmanager
async def get_browser_page():
    """Context manager para obtener una página de Playwright."""
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    try:
        yield page
    finally:
        await page.close()
        await browser.close()
        await playwright.stop()

class WebWatcherService:
    """
    Servicio encargado de orquestar el monitoreo de páginas web para detectar cambios visuales
    o de contenido mediante selectores CSS.
    Implementa el patrón Singleton y soporta notificaciones en tiempo real vía SSE.
    """
    # ... existing methods ...
    """
    Service for managing WebWatcher configurations and watchers.
    
    Responsibilities:
    - Configuration CRUD
    - Watcher lifecycle (start/stop)
    - Change history retrieval
    - Manual checks
    """
    
    def __init__(self):
        """Inicializa el servicio y el almacenamiento de tareas activas."""
        self.watchers: Dict[int, asyncio.Task] = {}  # config_id -> task (Legacy)
        self._trigger_tasks: Dict[int, asyncio.Task] = {} # trigger_id -> task (New)
        self.screenshot_base_dir = Path("data/screenshots/web_watcher")
        self._status_callbacks: List[Callable] = [] # list of callbacks for status changes
        # SSE: Callback system for real-time notifications
        self.status_callbacks: List[Callable] = []
    
    def register_status_callback(self, callback: Callable) -> None:
        """
        Registra un callback para notificar cambios de estado (vía SSE).
        """
        if callback not in self.status_callbacks:
            self.status_callbacks.append(callback)
    
    def unregister_status_callback(self, callback: Callable) -> None:
        """
        Elimina un callback de estado previamente registrado.
        """
        if callback in self.status_callbacks:
            self.status_callbacks.remove(callback)
    
    async def _notify_status_change(self, config_id: int) -> None:
        """
        Notifica a todos los callbacks registrados sobre el cambio de estado de un watcher.
        """
        if not self.status_callbacks:
            return
        
        try:
            # Get current status
            config = await self.load_config(config_id)
            if not config:
                return
            
            status_data = {
                "config_id": config_id,
                "url": config["url"],
                "is_active": config["is_active"],
                "last_checked_at": config["last_checked_at"]
            }
            
            for callback in self.status_callbacks[:]:
                try:
                    await callback(status_data)
                except Exception:
                    # Client disconnected or error, remove callback
                    self.unregister_status_callback(callback)
        except Exception as e:
            print(f"[WebWatcherService] Error notifying status change: {e}")
    
    async def create_config(self, config: Dict[str, Any]) -> int:
        """
        Crea una nueva configuración usando TriggerConfig (V2).
        """
        async with AsyncSession(client_engine) as session:
            trigger = TriggerConfig(
                name=config.get("name", "Web Watcher"),
                description=config.get("description"),
                type="web_watcher",
                status="CONFIGURED",
                is_active=False,
                configuration={
                    "url": config["url"],
                    "selector": config.get("selector", "body"),
                    "selector_type": config.get("selector_type", "css"),
                    "watch_mode": config.get("watch_mode", "selector"),
                    "check_interval": config.get("check_interval", 60),
                    "notify_on_change": config.get("notify_on_change", True),
                    "capture_screenshot": config.get("capture_screenshot", True),
                    "capture_detailed_content": config.get("capture_detailed_content", False),
                    "send_email_on_change": config.get("send_email_on_change", False),
                    "smtp_credential_id": config.get("smtp_credential_id"),
                    "notification_email": config.get("notification_email")
                }
            )
            session.add(trigger)
            await session.commit()
            await session.refresh(trigger)

            print(f"[WebWatcherService] TriggerConfig created: {trigger.name} (ID: {trigger.id})")
            return trigger.id

    # Alias for UI compatibility - Removed since create_config is now the main one
    # async def save_config(self, config: Dict[str, Any]) -> int: -> Use create_config
    
    async def update_config(self, config_id: int, config: Dict[str, Any]) -> bool:
        """Actualiza una configuración existente (V1 o V2).

        """
        async with AsyncSession(client_engine) as session:
            trigger = await session.get(TriggerConfig, config_id)
            if not trigger or trigger.type != "web_watcher":
                return False

            conf = trigger.configuration.copy() if trigger.configuration else {}
            if "name" in config: trigger.name = config["name"]
            for key in ["url", "selector", "selector_type", "watch_mode", "check_interval", "notify_on_change", "capture_screenshot", "capture_detailed_content", "send_email_on_change", "smtp_credential_id", "notification_email"]:
                if key in config:
                    conf[key] = config[key]
            trigger.configuration = conf
            trigger.updated_at = datetime.utcnow()
            session.add(trigger)
            await session.commit()
            return True
    
    async def load_config(self, config_id: int) -> Optional[Dict[str, Any]]:
        """Carga los detalles de una configuración de TriggerConfig."""
        async with AsyncSession(client_engine) as session:
            trigger = await session.get(TriggerConfig, config_id)
            if not trigger or trigger.type != "web_watcher":
                return None

            c = trigger.configuration or {}
            return {
                "id": trigger.id,
                "name": trigger.name,
                "url": c.get("url"),
                "selector": c.get("selector"),
                "selector_type": c.get("selector_type"),
                "watch_mode": c.get("watch_mode"),
                "check_interval": c.get("check_interval"),
                "last_hash": c.get("last_hash"),
                "last_content_text": c.get("last_content_text"),
                "last_content_html": c.get("last_content_html"),
                "last_checked_at": trigger.last_triggered,
                "notify_on_change": c.get("notify_on_change"),
                "capture_screenshot": c.get("capture_screenshot"),
                "capture_detailed_content": c.get("capture_detailed_content", False),
                "send_email_on_change": c.get("send_email_on_change"),
                "smtp_credential_id": c.get("smtp_credential_id"),
                "notification_email": c.get("notification_email"),
                "is_active": trigger.is_active,
                "created_at": trigger.created_at,
                "updated_at": trigger.updated_at,
            }
    
    async def list_configs(self) -> List[Dict[str, Any]]:
        """List all web_watcher configurations from TriggerConfig."""
        async with AsyncSession(client_engine) as session:
            stmt = select(TriggerConfig).where(TriggerConfig.type == "web_watcher")
            result = await session.exec(stmt)
            triggers = result.all()

            configs = []
            for t in triggers:
                c = t.configuration or {}
                configs.append({
                    "id": t.id,
                    "name": t.name,
                    "url": c.get("url"),
                    "selector": c.get("selector"),
                    "selector_type": c.get("selector_type"),
                    "watch_mode": c.get("watch_mode"),
                    "check_interval": c.get("check_interval"),
                    "is_active": t.is_active,
                    "last_checked_at": t.last_triggered,
                    "send_email_on_change": c.get("send_email_on_change"),
                    "smtp_credential_id": c.get("smtp_credential_id"),
                    "notification_email": c.get("notification_email"),
                })

            return configs
    
    async def delete_config(self, config_id: int) -> bool:
        """Delete configuration (stops watcher if active)."""
        # Stop watcher if running
        await self.stop_watcher(config_id=config_id)
        await self.stop_watcher(trigger_id=config_id)

        async with AsyncSession(client_engine) as session:
            trigger = await session.get(TriggerConfig, config_id)
            if not trigger or trigger.type != "web_watcher":
                return False

            await session.delete(trigger)
            await session.commit()
            return True

    async def start_watcher(self, config_id: int) -> Tuple[bool, str]:
        """
        Inicia el monitoreo en segundo plano de una URL basada en su configuración.

        Args:
            config_id: ID de la configuración del observador.

        Returns:
            Tupla (éxito: bool, mensaje: str).
        """
        if config_id in self.watchers or config_id in self._trigger_tasks:
            return False, "Watcher already running"

        try:
            config = await self.load_config(config_id)
            if not config:
                return False, f"Configuration {config_id} not found"

            # Update state in TriggerConfig
            async with AsyncSession(client_engine) as session:
                trigger_config = await session.get(TriggerConfig, config_id)
                if trigger_config:
                    trigger_config.is_active = True
                    session.add(trigger_config)
                    await session.commit()

            # SSE: Notify clients of status change
            await self._notify_status_change(config_id)

            # Start background task
            self.watchers[config_id] = asyncio.create_task(
                self._watcher_loop(config_id)
            )

            print(f"[WebWatcherService] Watcher started: {config['url']}")
            return True, f"Watcher started for {config['url']}"

        except Exception as e:
            return False, f"Failed to start watcher: {str(e)}"
    
    async def stop_watcher(self, config_id: int) -> bool:
        """
        Detiene la tarea de monitoreo en segundo plano.
        """
        if config_id not in self.watchers:
            return False, "Watcher not running"
        
        try:
            # Cancel task
            self.watchers[config_id].cancel()
            try:
                await self.watchers[config_id]
            except asyncio.CancelledError:
                pass
            
            del self.watchers[config_id]

            # Update state in TriggerConfig
            async with AsyncSession(client_engine) as session:
                trigger_config = await session.get(TriggerConfig, config_id)
                if trigger_config:
                    trigger_config.is_active = False
                    session.add(trigger_config)
                    await session.commit()

            # SSE: Notify clients of status change
            await self._notify_status_change(config_id)
            
            print(f"[WebWatcherService] Watcher stopped: {config_id}")
            return True
            
        except Exception as e:
            return False, f"Failed to stop watcher: {str(e)}"
    
    async def manual_check(self, config_id: int) -> Tuple[bool, str, bool]:
        """
        Realiza una comprobación manual inmediata de cambios en la URL.

        Returns:
            Tupla (éxito: bool, mensaje: str, hubo_cambio: bool).
        """
        try:
            config = await self.load_config(config_id)
            if not config:
                return False, "Configuration not found", False

            capture_detailed = config.get("capture_detailed_content", False)

            async with get_browser_page() as page:
                # Check for changes
                screenshot_dir = self.screenshot_base_dir / str(config_id)

                result = await check_url_changes(
                    page=page,
                    url=config["url"],
                    selector=config["selector"],
                    selector_type=config["selector_type"],
                    last_hash=config["last_hash"],
                    capture_screenshot=config["capture_screenshot"],
                    screenshot_dir=screenshot_dir,
                    watch_mode=config.get("watch_mode", "selector"),
                    capture_content=capture_detailed
                )

                # Generate diff if detailed content is enabled and there's a change
                diff_text = None
                diff_html = None

                if result.changed and capture_detailed and result.content_text:
                    old_text = config.get("last_content_text") or ""
                    diff_text = generate_text_diff(old_text, result.content_text)
                    diff_html = generate_html_diff(old_text, result.content_text)

                # Update last_hash, last_checked_at, and content if detailed mode
                async with AsyncSession(client_engine) as session:
                    trigger = await session.get(TriggerConfig, config_id)
                    if trigger:
                        conf = trigger.configuration.copy() if trigger.configuration else {}
                        conf["last_hash"] = result.new_hash
                        trigger.last_triggered = datetime.utcnow()

                        # Store content for next diff comparison
                        if capture_detailed and result.content_text:
                            conf["last_content_text"] = result.content_text
                            conf["last_content_html"] = result.content_html

                        trigger.configuration = conf
                        session.add(trigger)
                        await session.commit()

                # If changed, log to history
                if result.changed:
                    await self._log_change(
                        config_id=config_id,
                        url=config["url"],
                        old_hash=config["last_hash"],
                        new_hash=result.new_hash,
                        screenshot_path=result.screenshot_path,
                        diff_text=diff_text,
                        diff_html=diff_html
                    )

                    # Trigger workflow if configured
                    if config["trigger_workflow"] and config["workflow_id"]:
                        await self._trigger_workflow(config_id, config["workflow_id"])

                    return True, "Change detected!", True
                else:
                    return True, "No changes detected", False

        except Exception as e:
            return False, f"Check failed: {str(e)}", False
    
    async def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Valida una configuración de monitoreo (prueba el selector contra la URL real).

        Returns:
            Tupla (es_valido: bool, mensaje: str).
        """
        try:
            async with get_browser_page() as page:
                valid, message = await validate_selector(
                    page=page,
                    url=config["url"],
                    selector=config.get("selector", "body"),
                    selector_type=config.get("selector_type", "css")
                )
                return valid, message

        except Exception as e:
            return False, f"Validation failed: {str(e)}"
    
    async def get_change_history(
        self,
        config_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Recupera el historial de cambios detectados para un observador específico.
        """
        async with AsyncSession(client_engine) as session:
            stmt = (
                select(WebWatcherHistory)
                .where(WebWatcherHistory.config_id == config_id)
                .order_by(WebWatcherHistory.change_detected_at.desc())
                .limit(limit)
            )
            result = await session.exec(stmt)
            history = result.all()
            
            return [
                {
                    "id": h.id,
                    "url": h.url,
                    "change_detected_at": h.change_detected_at,
                    "old_hash": h.old_hash,
                    "new_hash": h.new_hash,
                    "screenshot_path": h.screenshot_path,
                    "diff_text": h.diff_text,
                    "diff_html": h.diff_html,
                    "workflow_triggered": h.workflow_triggered,
                    "workflow_execution_id": h.workflow_execution_id
                }
                for h in history
            ]
    
    async def _watcher_loop(self, config_id: int):
        """Background task for periodic checking."""
        while True:
            try:
                config = await self.load_config(config_id)
                if not config or not config["is_active"]:
                    break
                
                # Perform check
                success, message, changed = await self.manual_check(config_id)
                
                if not success:
                    print(f"[WebWatcherService] Check failed for {config_id}: {message}")
                
                # Wait for next check
                await asyncio.sleep(config["check_interval"] * 60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[WebWatcherService] Error in watcher loop: {e}")
                await asyncio.sleep(60)  # Wait before retry
    
    async def _log_change(
        self,
        config_id: int,
        url: str,
        old_hash: Optional[str],
        new_hash: str,
        screenshot_path: Optional[str],
        diff_text: Optional[str] = None,
        diff_html: Optional[str] = None
    ) -> None:
        """Registra un cambio detectado en la base de datos de historial."""
        async with AsyncSession(client_engine) as session:
            history = WebWatcherHistory(
                config_id=config_id,
                url=url,
                old_hash=old_hash,
                new_hash=new_hash,
                screenshot_path=screenshot_path,
                diff_text=diff_text,
                diff_html=diff_html
            )
            session.add(history)
            await session.commit()

            print(f"[WebWatcherService] Change logged for {url}")

        # Enviar notificación por email si está configurado
        config = await self.load_config(config_id)
        if config and config.get("send_email_on_change"):
            await self._send_email_notification(config, url, diff_html)

    async def _send_email_notification(self, config: Dict[str, Any], url: str, diff_html: Optional[str] = None) -> bool:
        """
        Envía notificación por email cuando se detecta un cambio.

        Args:
            config: Configuración del watcher con smtp_credential_id y notification_email
            url: URL donde se detectó el cambio
            diff_html: HTML formateado con los cambios detectados (opcional)

        Returns:
            True si el email se envió correctamente
        """
        smtp_credential_id = config.get("smtp_credential_id")
        notification_email = config.get("notification_email")

        if not smtp_credential_id or not notification_email:
            print(f"[WebWatcherService] Email notification skipped: missing SMTP config")
            return False

        try:
            from client_app.app.services.mail_watcher_service import mail_watcher_service
            from client_app.app.modules.output.email_sender import EmailSender

            # Obtener credenciales SMTP
            cred_data = await mail_watcher_service.get_credential(smtp_credential_id)
            if not cred_data:
                print(f"[WebWatcherService] SMTP credential {smtp_credential_id} not found")
                return False

            # Preparar credenciales para EmailSender
            smtp_credentials = {
                "server": cred_data.get("server"),
                "port": cred_data.get("port", 587),
                "username": cred_data.get("user"),
                "password": cred_data.get("password")
            }

            # Crear y enviar email
            email_sender = EmailSender(smtp_credentials)

            # Información del monitor
            monitor_name = config.get('name') or 'Monitor sin nombre'
            watch_mode = config.get('watch_mode', 'selector')
            selector = config.get('selector', 'body')
            detection_time = datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')

            # Determinar descripción del modo de vigilancia
            if watch_mode == 'full_page':
                watch_description = "Vigilancia de página completa (Smart Digest)"
                element_info = "Se analizó el contenido principal de la página"
            else:
                selector_type = config.get('selector_type', 'css').upper()
                watch_description = f"Vigilancia de elemento específico ({selector_type})"
                element_info = f"Selector: {selector}"

            subject = f"[Gov Gen AI] Cambio detectado: {monitor_name}"

            # Crear email en formato HTML profesional
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ background: #f8f9fa; padding: 30px; border: 1px solid #e9ecef; }}
        .info-box {{ background: white; border-radius: 8px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        .label {{ font-size: 11px; color: #6c757d; text-transform: uppercase; font-weight: 600; margin-bottom: 4px; }}
        .value {{ font-size: 14px; color: #212529; word-break: break-all; }}
        .url {{ font-family: monospace; font-size: 13px; background: #e9ecef; padding: 8px 12px; border-radius: 4px; display: block; margin-top: 8px; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500; }}
        .badge-info {{ background: #e3f2fd; color: #1565c0; }}
        .footer {{ text-align: center; padding: 20px; color: #6c757d; font-size: 12px; }}
        .divider {{ height: 1px; background: #e9ecef; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Cambio detectado</h1>
        </div>
        <div class="content">
            <div class="info-box">
                <div class="label">Monitor</div>
                <div class="value" style="font-size: 18px; font-weight: 600; color: #667eea;">{monitor_name}</div>
            </div>

            <div class="info-box">
                <div class="label">URL vigilada</div>
                <code class="url">{url}</code>
            </div>

            <div class="info-box">
                <div style="display: flex; gap: 30px;">
                    <div style="flex: 1;">
                        <div class="label">Modo de vigilancia</div>
                        <div class="value"><span class="badge badge-info">{watch_description}</span></div>
                    </div>
                </div>
                <div class="divider"></div>
                <div class="label">Elemento analizado</div>
                <div class="value" style="font-family: monospace;">{element_info}</div>
            </div>

            <div class="info-box">
                <div class="label">Fecha y hora de detección</div>
                <div class="value">{detection_time} UTC</div>
            </div>
            {f'''
            <div class="info-box">
                <div class="label">Cambios detectados</div>
                <div style="background: #fafafa; border-radius: 4px; padding: 12px; margin-top: 8px; max-height: 400px; overflow-y: auto;">
                    {diff_html}
                </div>
            </div>
            ''' if diff_html else ''}
        </div>
        <div class="footer">
            Este mensaje fue generado automáticamente por Gov Gen AI Web Watcher.<br>
            No responda a este correo.
        </div>
    </div>
</body>
</html>
"""

            message_id = email_sender.send(
                from_addr=smtp_credentials["username"],
                to_addrs=[notification_email],
                subject=subject,
                body=html_body,
                html=True
            )

            print(f"[WebWatcherService] Email notification sent: {message_id}")
            return True

        except Exception as e:
            print(f"[WebWatcherService] Failed to send email notification: {e}")
            return False
    
    async def _trigger_workflow(self, config_id: int, workflow_id: int) -> bool:
        """
        Dispara la ejecución de un flujo de trabajo cuando se detecta un cambio.
        """
        try:
            from client_app.app.core.state import state
            
            # Get workflow
            async with AsyncSession(client_engine) as session:
                workflow = await session.get(FlowRegistry, workflow_id)
                if not workflow:
                    print(f"[WebWatcherService] Workflow {workflow_id} not found")
                    return False
            
            # Trigger workflow (assuming workflow_engine exists in state)
            if hasattr(state, 'workflow_engine'):
                execution_id = await state.workflow_engine.execute(
                    workflow_id=workflow_id,
                    context={"source": "web_watcher", "config_id": config_id}
                )
                
                # Update history with execution_id
                async with AsyncSession(client_engine) as session:
                    stmt = (
                        select(WebWatcherHistory)
                        .where(WebWatcherHistory.config_id == config_id)
                        .order_by(WebWatcherHistory.change_detected_at.desc())
                        .limit(1)
                    )
                    result = await session.exec(stmt)
                    history = result.first()
                    
                    if history:
                        history.workflow_triggered = True
                        history.workflow_execution_id = str(execution_id)
                        session.add(history)
                        await session.commit()
                
                print(f"[WebWatcherService] Workflow {workflow_id} triggered: {execution_id}")
                return True
            else:
                print("[WebWatcherService] WorkflowEngine not available in state")
                return False
                
        except Exception as e:
            print(f"[WebWatcherService] Failed to trigger workflow: {e}")
            return False



    async def start_trigger(self, trigger: TriggerConfig) -> Tuple[bool, str]:
        """
        Inicia un watcher específico para un TriggerConfig (Nueva Arquitectura).
        """
        if trigger.id in self._trigger_tasks:
            return True, "Watcher already running"

        try:
            # Start background task
            self._trigger_tasks[trigger.id] = asyncio.create_task(
                self._run_trigger_loop(trigger)
            )
            
            print(f"[WebWatcherService] Trigger Watcher started: {trigger.configuration.get('url')}")
            return True, "Started"
            
        except Exception as e:
            return False, f"Failed to start trigger {trigger.id}: {e}"

    async def _run_trigger_loop(self, trigger: TriggerConfig):
        """
        Loop para un trigger específico.
        """
        config = trigger.configuration
        trigger_id = trigger.id

        url = config.get("url")
        selector = config.get("selector", "body")
        selector_type = config.get("selector_type", "css")
        watch_mode = config.get("watch_mode", "selector")
        check_interval = config.get("check_interval", 60)  # minutes
        capture_detailed = config.get("capture_detailed_content", False)

        # State for diff comparison
        last_hash = config.get("last_hash")
        last_content_text = config.get("last_content_text")

        from client_app.app.services.event_bus_service import event_bus_service

        print(f"[WebWatcherService] Starting loop for trigger {trigger_id} ({url})")

        while trigger_id in self._trigger_tasks:
            try:
                # Get Browser Page
                async with get_browser_page() as page:
                    screenshot_dir = self.screenshot_base_dir / str(trigger_id)

                    result = await check_url_changes(
                        page=page,
                        url=url,
                        selector=selector,
                        selector_type=selector_type,
                        last_hash=last_hash,
                        capture_screenshot=True,
                        screenshot_dir=screenshot_dir,
                        watch_mode=watch_mode,
                        capture_content=capture_detailed
                    )

                    if result.changed:
                        print(f"[WebWatcherService] Change detected for trigger {trigger_id}")

                        # Generate diff if detailed content is enabled
                        diff_text = None
                        diff_html = None

                        if capture_detailed and result.content_text:
                            old_text = last_content_text or ""
                            diff_text = generate_text_diff(old_text, result.content_text)
                            diff_html = generate_html_diff(old_text, result.content_text)

                        # Emit Event
                        execution_id = uuid.uuid4().hex

                        meta = TriggerPayloadMeta(
                            trigger_id=trigger_id,
                            trigger_type="web_watcher",
                            timestamp=datetime.utcnow(),
                            execution_id=execution_id
                        )

                        payload = WebWatcherPayload(
                            meta=meta,
                            data={
                                "url": url,
                                "old_hash": last_hash,
                                "new_hash": result.new_hash,
                                "screenshot_path": result.screenshot_path,
                                "change_detected_at": datetime.utcnow().isoformat(),
                                "diff_text": diff_text,
                                "diff_html": diff_html,
                                "new_content_html": result.content_html
                            }
                        )

                        await event_bus_service.emit_trigger_event(
                            trigger_id=trigger_id,
                            payload=payload.model_dump()
                        )

                        # Update content for next comparison
                        if capture_detailed and result.content_text:
                            last_content_text = result.content_text

                            # Persist to TriggerConfig
                            async with AsyncSession(client_engine) as session:
                                tr = await session.get(TriggerConfig, trigger_id)
                                if tr:
                                    new_conf = tr.configuration.copy()
                                    new_conf["last_hash"] = result.new_hash
                                    new_conf["last_content_text"] = result.content_text
                                    new_conf["last_content_html"] = result.content_html
                                    tr.configuration = new_conf
                                    tr.last_triggered = datetime.utcnow()
                                    session.add(tr)
                                    await session.commit()

                    # Update local state
                    last_hash = result.new_hash

                # Wait for next check
                await asyncio.sleep(check_interval * 60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[WebWatcherService] Error in trigger loop {trigger_id}: {e}")
                await asyncio.sleep(60)  # Backoff

    async def stop_watcher(self, config_id: Optional[int] = None, trigger_id: Optional[int] = None) -> bool:
        """
        Detiene un watcher.
        Soporta tanto legacy (config_id) como nuevo (trigger_id).
        """
        # Stop Trigger Watcher
        if trigger_id is not None:
            if trigger_id in self._trigger_tasks:
                task = self._trigger_tasks[trigger_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self._trigger_tasks[trigger_id]
                return True
            return False

        # Stop Watcher by config_id (supports both V1 and V2)
        if config_id is not None:
            try:
                # Cancel task if running
                if config_id in self.watchers:
                    self.watchers[config_id].cancel()
                    try:
                        await self.watchers[config_id]
                    except asyncio.CancelledError:
                        pass
                    del self.watchers[config_id]

                # Update state in TriggerConfig
                async with AsyncSession(client_engine) as session:
                    trigger_config = await session.get(TriggerConfig, config_id)
                    if trigger_config:
                        trigger_config.is_active = False
                        session.add(trigger_config)
                        await session.commit()

                # SSE: Notify clients of status change
                await self._notify_status_change(config_id)

                print(f"[WebWatcherService] Watcher stopped: {config_id}")
                return True

            except Exception as e:
                return False, f"Failed to stop watcher: {str(e)}"
        
        return False

# Global instance
web_watcher_service = WebWatcherService()

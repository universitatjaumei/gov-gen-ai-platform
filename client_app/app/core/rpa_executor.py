import os
import json
import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from playwright.async_api import async_playwright
import pandas as pd
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.database.models import RpaPlaybook
from client_app.app.database.db import client_engine
from automatia_shared.core.execution_manager import ExecutionPathManager

# Script JS para inyectar y grabar eventos (Mismo que en logic.py)
RECORDER_SCRIPT = """
(function() {
    window.recorded_actions = [];
    window.recording_paused = False;
    
    function getSemanticInfo(el) {
        if (!(el instanceof Element)) return {};
        
        var info = {
            tagName: el.tagName.toLowerCase(),
            id: el.id || '',
            className: el.className || '',
            innerText: (el.innerText || '').trim().substring(0, 50),
            placeholder: el.getAttribute('placeholder') || '',
            ariaLabel: el.getAttribute('aria-label') || '',
            name: el.getAttribute('name') || '',
            inputType: el.getAttribute('type') || '',
            role: el.getAttribute('role') || '',
            dataTestId: el.getAttribute('data-testid') || el.getAttribute('data-test-id') || ''
        };

        // Try to find associated label
        if (el.id) {
            var label = document.querySelector('label[for="' + el.id + '"]');
            if (label) info.associatedLabel = label.innerText.trim();
        }
        
        // If no explicit label, check parent label (for nested inputs)
        if (!info.associatedLabel) {
            var parentLabel = el.closest('label');
            if (parentLabel) {
                 var clone = parentLabel.cloneNode(true);
                 var input = clone.querySelector('input, select, textarea');
                 if (input) input.remove();
                 info.associatedLabel = clone.innerText.trim();
            }
        }
        
        // Check for preceding sibling label
        if (!info.associatedLabel) {
            var sibling = el.previousElementSibling;
            if (sibling && sibling.tagName === 'LABEL') {
                info.associatedLabel = sibling.innerText.trim();
            }
        }

        return info;
    }

    function getCssSelector(el) {
        if (!(el instanceof Element)) return;
        var path = [];
        while (el.nodeType === Node.ELEMENT_NODE) {
            var selector = el.nodeName.toLowerCase();
            if (el.id) {
                selector += '#' + el.id;
                path.unshift(selector);
                break;
            } else {
                var sib = el, nth = 1;
                while (sib = sib.previousElementSibling) {
                    if (sib.nodeName.toLowerCase() == selector)
                        nth++;
                }
                if (nth != 1)
                    selector += ":nth-of-type("+nth+")";
            }
            path.unshift(selector);
            el = el.parentNode;
        }
        return path.join(" > ");
    }

    function recordEvent(type, target, value) {
        if (window.recording_paused) return; // PAUSE CHECK
        
        var semantic = getSemanticInfo(target);
        var action = {
            type: type,
            selector: getCssSelector(target),
            semantic: semantic,
            timestamp: Date.now(),
            value: value || ''
        };
        var last = window.recorded_actions[window.recorded_actions.length - 1];
        if (last && last.type === type && last.selector === action.selector && (action.timestamp - last.timestamp) < 500) {
            return;
        }
        window.recorded_actions.push(action);
        console.log("Action Recorded:", action);
    }

    document.addEventListener('click', function(e) {
        if (e.target && e.target.closest) {
             var clickable = e.target.closest('a, button, input[type="submit"], input[type="button"]');
             if (clickable) {
                 recordEvent('click', clickable, null);
             } else {
                 recordEvent('click', e.target, null);
             }
        }
    }, true);

    document.addEventListener('change', function(e) {
        recordEvent('change', e.target, e.target.value);
    }, true);
    
    document.addEventListener('submit', function(e) {
        recordEvent('submit', e.target, null);
    }, true);

    console.log("[OK] Smart Recorder Injected & Running");
})();
"""

class PlaybookBrokenException(Exception):
    def __init__(self, details):
        self.details = details
        super().__init__(f"Playbook roto en paso {details.get('step_index')}: {details.get('message')}")

class SessionExpiredException(Exception):
    def __init__(self, details):
        self.details = details
        super().__init__("Sesión caducada detectada")

# --- BRAIN CLIENT (Centralizado) ---


@dataclass
class AgentResult:
    """Resultado de la ejecución de un agente autónomo."""
    success: bool
    output: str
    error: Optional[str] = None
    action_log: Optional[str] = None


class BrowserAgentWrapper:
    """
    Envoltorio para agentes autónomos vinculados a RPA.

    Permite ejecutar misiones autónomas usando el navegador Playwright,
    delegando la inteligencia al servidor Brain via API.
    """

    def __init__(self, brain_client=None, license_key: str = "TRIAL-KEY"):
        """
        Inicializa el wrapper del agente.

        Args:
            brain_client: Cliente Brain (BrainAPIClient o LocalBrainClient)
            license_key: Clave de licencia para autenticación
        """
        self._brain_client = brain_client
        self._license_key = license_key

    async def _get_brain_client(self):
        """Obtiene el cliente Brain activo."""
        if self._brain_client:
            return self._brain_client, self._license_key

        # Lazy import to avoid circular dependencies
        from client_app.app.clients.brain_client import BrainAPIClient
        from client_app.app.database.models import ServerConnection
        from client_app.app.database.db import client_engine

        # Resolve URL from DB
        async with AsyncSession(client_engine) as session:
            stmt = select(ServerConnection).where(ServerConnection.is_active == True)
            res = await session.exec(stmt)
            conn = res.first()
            url = conn.brain_url if (conn and conn.brain_url) else "http://localhost:8080"
            key = conn.license_key if (conn and conn.license_key) else self._license_key
            return BrainAPIClient(base_url=url), key

    async def run_agent_task(self, context, task_instruction: str) -> AgentResult:
        """
        Ejecuta una misión autónoma sobre el contexto de navegación actual.

        Args:
            context: El contexto de Playwright donde el agente debe actuar.
            task_instruction: Descripción en lenguaje natural de la tarea.

        Returns:
            AgentResult: Objeto con el estado de éxito, salida y logs de acción.
        """
        print(f"[BrowserAgent] Iniciando tarea: '{task_instruction}'")

        action_history = []
        max_steps = 20

        try:
            client, license_key = await self._get_brain_client()

            # Get current page from context
            pages = context.pages
            if not pages:
                page = await context.new_page()
            else:
                page = pages[0]

            for step in range(max_steps):
                # 1. Capture page state
                try:
                    screenshot_bytes = await page.screenshot()
                    import base64
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                except Exception:
                    screenshot_b64 = ""

                page_state = {
                    "url": page.url,
                    "title": await page.title() if page else "",
                    "screenshot_base64": screenshot_b64,
                    "html_snippet": ""  # Could add truncated HTML if needed
                }

                # 2. Get next action from Brain
                result = await client.run_agent_step(
                    task_instruction=task_instruction,
                    page_state=page_state,
                    action_history=action_history,
                    license_key=license_key
                )

                action = result.get("action", "error")
                reasoning = result.get("reasoning", "")
                is_complete = result.get("is_complete", False)

                print(f"[BrowserAgent] Step {step+1}: {action} - {reasoning[:50]}...")

                # 3. Check if complete
                if is_complete or action == "done":
                    return AgentResult(
                        success=True,
                        output=reasoning,
                        action_log=str(action_history)
                    )

                if action == "error":
                    return AgentResult(
                        success=False,
                        output="",
                        error=reasoning,
                        action_log=str(action_history)
                    )

                # 4. Execute action
                action_result = {"success": False, "error": "Unknown action"}
                try:
                    selector = result.get("selector", "")
                    value = result.get("value", "")

                    if action == "click":
                        await page.click(selector, timeout=10000)
                        action_result = {"success": True}
                    elif action == "fill":
                        await page.fill(selector, value, timeout=10000)
                        action_result = {"success": True}
                    elif action == "navigate":
                        await page.goto(value, timeout=30000)
                        action_result = {"success": True}
                    elif action == "wait":
                        await page.wait_for_timeout(int(value) if value else 1000)
                        action_result = {"success": True}
                    elif action == "visual_click":
                        # Use visual safety net
                        coords = await client.get_element_coordinates(
                            screenshot_bytes, selector,
                            page.viewport_size or {"width": 1280, "height": 800},
                            license_key=license_key
                        )
                        if coords:
                            await page.mouse.click(coords[0], coords[1])
                            action_result = {"success": True}
                        else:
                            action_result = {"success": False, "error": "Element not found visually"}
                    else:
                        action_result = {"success": False, "error": f"Unknown action: {action}"}

                except Exception as e:
                    action_result = {"success": False, "error": str(e)}

                # 5. Record action in history
                action_history.append({
                    "step": step,
                    "action": action,
                    "selector": result.get("selector", ""),
                    "value": result.get("value", ""),
                    "result": action_result,
                    "timestamp": datetime.now().isoformat()
                })

                # Small delay between actions
                await asyncio.sleep(0.5)

            # Max steps reached
            return AgentResult(
                success=False,
                output="",
                error=f"Max steps ({max_steps}) reached without completing task",
                action_log=str(action_history)
            )

        except Exception as e:
            err_msg = f"Agent error: {str(e)}"
            print(f"[BrowserAgent] {err_msg}")
            return AgentResult(
                success=False,
                output="",
                error=err_msg,
                action_log=str(action_history) if action_history else None
            )

class RPAExecutor:
    """
    Ejecutor de automatización (Body) que delega la inteligencia al Brain.
    Integra ExecutionPathManager para gestión centralizada de archivos.
    """
    def __init__(self, brain_service: Optional[Any] = None, db_session=None):
        # NOTE: 'brain_service' arg is legacy/local injection. We now use dynamic resolution.
        self._local_brain_ref = brain_service
        self.paths = ExecutionPathManager()

        
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self._recording_active = False
        self.master_playbook: List[Dict[str, Any]] = []

        # State
        self.current_execution_id: str = None
        self._download_dir: str = None  # Directorio para guardar descargas
        
        print(f"[RPAExecutor] Inicializado. Path Manager vinculado.")

    async def _get_active_license_key(self) -> Optional[str]:
        """Retrieves active license key from local db."""
        from client_app.app.database.models import ServerConnection
        from client_app.app.core.state import state
        
        async with AsyncSession(client_engine) as session:
            stmt = select(ServerConnection).where(ServerConnection.is_active == True)
            res = await session.exec(stmt)
            conn = res.first()
            return conn.license_key if conn else None

    async def _get_brain_client(self):
        """
        Returns (client, license_key).
        Always resolves to BrainAPIClient (Split or Monolith).
        """
        from client_app.app.clients.brain_client import BrainAPIClient
        from client_app.app.database.models import ServerConnection
        
        # 1. Resolve License Key
        key = await self._get_active_license_key()
        
        # [FIX] Handle Seed Mismatch
        if not key or key in ["demo_key_123", "dev_key"]:
            key = "DEV_LICENSE_KEY_12345"

        # 2. Resolve URL from DB
        async with AsyncSession(client_engine) as session:
            conn = await session.get(ServerConnection, "default")
            url = conn.brain_url if (conn and conn.brain_url) else "http://localhost:8080"
            return BrainAPIClient(base_url=url), key


    def set_execution_context(self, task_id: str = None, task_type: str = 'GENERIC'):
        """Define o crea el contexto de ejecución actual (carpetas)."""
        if task_id:
            # Assume it exists or manager handles it transparently (it does dir creation on init usually or we trust it exists)
            # Actually manager.create_execution_context handles creation idempotently
            # But create_execution_context generally creates a NEW ID if not provided.
            # If we rely on an external ID, we might need a way to ensure dirs exist.
            # For now execution_manager doesn't have 'ensure_output_dir(id)'.
            # We will use create_execution_context with workflow_id trick if needed, or just assume standard ID format.
            # Simple approach: If task_id provided, we assume we can just set it.
            # But integration requested: "Si no se pasa task_id, genera uno nuevo... Guarda el ID".
            
            # To ensure folders exist for a passed ID check manager (it needs an ensure method effectively)
            # We'll re-use create logic essentially or just set it.
            self.current_execution_id = task_id
            # Ensure dirs exist manually just in case
            self.paths.get_input_dir(task_id).mkdir(parents=True, exist_ok=True)
            self.paths.get_output_dir(task_id).mkdir(parents=True, exist_ok=True)
        else:
            self.current_execution_id = self.paths.create_execution_context(task_type=task_type)
        
        print(f"[RPAExecutor] [DIR] Contexto de ejecución activo: {self.current_execution_id}")

    def _log(self, message: str, callback=None):
        print(message)
        if callback: callback(message)

    def _is_login_url(self, url: str) -> bool:
        """Detecta si la URL actual parece una página de login."""
        if not url: return False
        keywords = ['login', 'signin', 'auth', 'acceso', 'identificacion', 'sso']
        url_lower = url.lower()
        return any(k in url_lower for k in keywords)

    async def list_stored_playbooks(self) -> List[Dict]:
        """Lista playbooks desde la DB."""
        async with AsyncSession(client_engine) as session:
            statement = select(RpaPlaybook).order_by(RpaPlaybook.name)
            results = await session.exec(statement)
            playbooks = results.all()
            
            return [
                {
                    "filename": f"{p.name}.json", # Fake filename for compatibility
                    "friendly_name": p.name,
                    "url": p.base_url,
                    "id": p.id
                }
                for p in playbooks
            ]

    async def save_master_playbook(self, name: str, base_url: str) -> str:
        """Guarda playbook en DB."""
        if not self.master_playbook:
            return ""

        async with AsyncSession(client_engine) as session:
            # Check if exists to update
            statement = select(RpaPlaybook).where(RpaPlaybook.name == name)
            results = await session.exec(statement)
            existing = results.first()
            
            if existing:
                existing.actions = self.master_playbook
                existing.base_url = base_url
                existing.last_run = datetime.utcnow()
                session.add(existing)
                print(f"[RPAExecutor] [UPDATE] Playbook '{name}' actualizado en DB.")
            else:
                new_pb = RpaPlaybook(
                    name=name,
                    base_url=base_url,
                    actions=self.master_playbook,
                    description="Grabado con RPAExecutor"
                )
                session.add(new_pb)
                print(f"[RPAExecutor] [SAVE] Playbook '{name}' creado en DB.")
                
            await session.commit()
            return name

    async def load_master_playbook(self, name_or_id: str) -> Dict:
        """Carga desde DB."""
        name_clean = str(name_or_id).replace(".json", "")
        
        async with AsyncSession(client_engine) as session:
            if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
                 statement = select(RpaPlaybook).where(RpaPlaybook.id == int(name_or_id))
            else:
                 statement = select(RpaPlaybook).where(RpaPlaybook.name == name_clean)
            
            results = await session.exec(statement)
            pb = results.first()
            
            if pb:
                self.master_playbook = pb.actions
                print(f"[RPAExecutor] [LOAD] Playbook '{pb.name}' cargado ({len(pb.actions)} pasos).")
                return {
                    "name": pb.name,
                    "base_url": pb.base_url,
                    "actions": pb.actions
                }
            else:
                print(f"[RPAExecutor] [WARN] Playbook '{name_clean}' no encontrado en DB.")
                return {}

    async def analyze_recording(self, recording_logs: list, context_dict: dict = None, config: dict = None, log_callback=None) -> list:
        """Delegación al Brain Service."""
        msg = "[RPAExecutor] [BRAIN] Solicitando análisis al Brain..."
        self._log(msg, log_callback)
        
        client, license_key = await self._get_brain_client()
        playbook = await client.analyze_recording(recording_logs, context_dict, license_key=license_key)
        
        if playbook:
            self.master_playbook = playbook
        return playbook

    async def refine_playbook(
        self, 
        current_playbook: list, 
        recording_logs: list, 
        error_logs: str, 
        user_feedback_history: list, 
        context_data: dict,
        config: dict = None,
        log_callback=None
    ) -> list:
        """Delegación al Brain Service para refinamiento."""
        self._log("[RPAExecutor] 🔧 Solicitando refinamiento al Brain...", log_callback)
        
        client, license_key = await self._get_brain_client()
        return await client.refine_playbook(
            current_playbook,
            recording_logs,
            error_logs,
            user_feedback_history,
            context_data,
            license_key=license_key
        )

    # --- BROWSER / SESSION MANAGEMENT ---

    def _get_session_path(self, url: str) -> Optional[str]:
        if not url: return None
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace("www.", "").replace(".", "_")
            if not domain: return None
            # Use PathManager session dir
            return str(self.paths.get_session_dir() / f"session_{domain}.json")
        except: return None

    async def save_session_state(self, url: str):
        if not self.context or not url: return
        path = self._get_session_path(url)
        if path:
            try:
                await self.context.storage_state(path=path)
                print(f"[RPAExecutor] [SESSION] Sesión guardada: {path}")
            except Exception as e:
                print(f"[RPAExecutor] [WARN] Error guardando sesión: {e}")

    async def run_agent_interactive(self, instruction: str) -> dict:
        """Delega una tarea al Agente Autónomo usando el contexto actual."""
        if not self.context:
            return {"success": False, "error": "No hay navegador activo (contexto nulo)"}
            
        print(f"[RPAExecutor] [AGENT] Delegando al Agente: {instruction}")
        
        # Pausar listener de grabación si es posible (enviando evento al navegador)
        # Esto evita que el agente 'se grabe a sí mismo' generando ruido de clicks
        try:
            if self.page:
                await self.page.evaluate("if(window.recorded_actions) window.recording_paused = true;")
        except: pass

        try:
            agent_wrapper = BrowserAgentWrapper()
            result = await agent_wrapper.run_agent_task(self.context, instruction)
            
            return {
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "action_log": result.action_log
            }
        finally:
            # Reactivar grabación
            try:
                 if self.page:
                    await self.page.evaluate("if(window.recorded_actions) window.recording_paused = false;")
            except: pass

    async def start_recording_session(self, url: str, _excel_file=None, _attachments_path: str = None, log_callback=None):
        msg = f"[RPAExecutor] 🎥 Iniciando sesión de grabación: {url}"
        self._log(msg, log_callback)
        
        # Init Context if not set
        if not self.current_execution_id:
            self.set_execution_context(task_type="RECORDING")

        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=False,
                args=["--window-size=1280,800", "--disable-infobars"]
            )
            
            storage_path = self._get_session_path(url)
            state_options = {}
            if storage_path and os.path.exists(storage_path):
                 self._log(f"[RPAExecutor] [SESSION] Recuperando sesión: {storage_path}", log_callback)
                 state_options["storage_state"] = storage_path
            
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                accept_downloads=True,
                **state_options
            )
            await self.context.add_init_script(RECORDER_SCRIPT)

            self.page = await self.context.new_page()

            # Configurar directorio de descargas y manejador
            download_dir = self.paths.get_output_dir(self.current_execution_id)
            os.makedirs(download_dir, exist_ok=True)

            async def handle_download(download):
                """Guarda las descargas en el directorio de salida."""
                suggested_filename = download.suggested_filename
                save_path = os.path.join(download_dir, suggested_filename)
                try:
                    await download.save_as(save_path)
                    self._log(f"[RPAExecutor] [DOWNLOAD] Archivo guardado: {save_path}", log_callback)
                except Exception as e:
                    self._log(f"[RPAExecutor] [DOWNLOAD] Error guardando {suggested_filename}: {e}", log_callback)

            self.page.on("download", handle_download)

            if url:
                await self.page.goto(url)

            self._recording_active = True
            
        except Exception as e:
            self._log(f"[RPAExecutor] [ERROR] Error inicio grabación: {e}", log_callback)
            await self.stop_recording_and_get_logs(log_callback)
            raise e

    async def stop_recording_and_get_logs(self, log_callback=None):
        self._log("[RPAExecutor] [STOP] Deteniendo grabación...", log_callback)
        logs = []
        if self.page:
             try:
                 await self.save_session_state(self.page.url)
             except: pass

        try:
            if self.page and not self.page.is_closed():
                logs = await self.page.evaluate("() => window.recorded_actions")
        except Exception as e:
            print(f"[RPAExecutor] [WARN] Error logs: {e}")
        
        try:
            if self.context: await self.context.close()
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except: pass
            
        self._recording_active = False
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        
        if logs:
            self.master_playbook = logs
        return logs

    async def run_playbook_batch(self, playbook: list, excel_path: str = None, explicit_rows: list = None, start_row: int = 0, log_callback=None, on_ask_user=None) -> str:
        """Ejecución por lotes."""
        self._log(f"[RPAExecutor] [START] Batch Run. Start: {start_row}", log_callback)
        
        # Ensure Context
        if not self.current_execution_id:
            self.set_execution_context(task_type="BATCH")

        # Setup Results
        results_filename = f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        results_path = self.paths.get_output_dir(self.current_execution_id) / results_filename
        
        df = pd.DataFrame()
        is_excel_mode = False
        
        if explicit_rows:
            df = pd.DataFrame(explicit_rows)
        elif excel_path and os.path.exists(excel_path):
            is_excel_mode = True
            df = pd.read_excel(excel_path)
            if "Estado_Robot" not in df.columns: df["Estado_Robot"] = ""
        else:
            df = pd.DataFrame([{}])

        # Get base URL
        base_url = next((s.get("value") for s in playbook if s.get("action") == "navigate"), "")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=False, 
            args=["--window-size=1280,800", "--disable-infobars"]
        )
        
        storage_path = self._get_session_path(base_url)
        state_options = {"storage_state": storage_path} if storage_path and os.path.exists(storage_path) else {}

        # Configurar directorio de descargas para esta ejecución
        self._download_dir = self.paths.get_output_dir(self.current_execution_id)
        os.makedirs(self._download_dir, exist_ok=True)

        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            accept_downloads=True,
            **state_options
        )

        consecutive_errors = 0
        last_error_step = -1
        
        # ACTIVE PLAYERBOOK (Mutable for learning)
        active_playbook = list(playbook)
        
        try:
            total = len(df)
            for i in range(total):
                if i < start_row: continue
                
                # Check status if excel
                if is_excel_mode and str(df.at[i, "Estado_Robot"]) == "OK": continue

                # Prepare Data
                row_data = df.iloc[i].to_dict()
                row_data = {k: ("" if pd.isna(v) else v) for k,v in row_data.items()}

                self._log(f"--- Fila {i+1}/{total} ---", log_callback)
                try:
                    # Pass active_playbook instead of original
                    success, error_msg, failed_idx, _, updated_pb = await self.execute_playbook(
                        active_playbook, 
                        row_data, 
                        log_callback=log_callback, 
                        on_ask_user=on_ask_user
                    )
                    
                    # --- LEARNING MOMENT ---
                    if updated_pb and updated_pb != active_playbook:
                        print(f"[RunBatch] [BRAIN] Aprendizaje aplicado: Actualizando playbook maestro para filas restantes.")
                        active_playbook = updated_pb
                    
                    if success:
                        consecutive_errors = 0
                        if is_excel_mode: df.at[i, "Estado_Robot"] = "OK"
                    else:
                        if error_msg == "SESSION_EXPIRED":
                            raise SessionExpiredException({"message": "Redirección a Login durante lote"})

                        self._log(f"[ERROR] Fallo: {error_msg}", log_callback)
                        if is_excel_mode: df.at[i, "Estado_Robot"] = error_msg
                        
                        # 3 Strikes Rule
                        if failed_idx != -1:
                            if failed_idx == last_error_step: consecutive_errors += 1
                            else:
                                consecutive_errors = 1
                                last_error_step = failed_idx
                            
                            if consecutive_errors >= 3:
                                raise PlaybookBrokenException({"step_index": failed_idx, "message": "Fallo sistémico (3 strikes)"})
                        else:
                            consecutive_errors = 0

                except Exception as e:
                     error_msg = f"CRITICAL: {e}"
                     self._log(f"[ERROR] {error_msg}", log_callback)
                     if is_excel_mode: df.at[i, "Estado_Robot"] = str(e)
                     
                     if isinstance(e, (PlaybookBrokenException, SessionExpiredException)): 
                         raise e

                # Save after each row
                if is_excel_mode:
                    try: df.to_excel(results_path, index=False)
                    except: pass

            if base_url: await self.save_session_state(base_url)
                
        finally:
            if self.context: await self.context.close()
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
            
        return str(results_path) if results_path.exists() else ""

    async def execute_playbook(self, playbook: list, data_row: dict, log_callback=None, on_ask_user=None) -> Tuple[bool, str, int, Optional[dict], Optional[list]]:
        """
        Ejecuta un playbook unitario con soporte de "Sala de Emergencias".
        Si on_ask_user está definido, pausará en error para pedir ayuda.
        Retorna: (Success, ErrorMsg, FailedIndex, ErrorDetails, UpdatedPlaybook)
        """
        if not self.browser:
             # Just in case called alone for test
             self.playwright = await async_playwright().start()
             self.browser = await self.playwright.chromium.launch(headless=False)
             self.context = await self.browser.new_context()

        # Re-use context
        page = await self.context.new_page()

        # Configurar manejador de descargas si hay directorio configurado
        if self._download_dir:
            download_dir = self._download_dir

            async def handle_download(download):
                """Guarda las descargas en el directorio de salida."""
                suggested_filename = download.suggested_filename
                save_path = os.path.join(download_dir, suggested_filename)
                try:
                    await download.save_as(save_path)
                    self._log(f"[RPAExecutor] [DOWNLOAD] Archivo guardado: {save_path}", log_callback)
                except Exception as e:
                    self._log(f"[RPAExecutor] [DOWNLOAD] Error guardando {suggested_filename}: {e}", log_callback)

            page.on("download", handle_download)

        # Local copy to allow runtime patching
        current_playbook = list(playbook)
        
        try:
            index = 0
            while index < len(current_playbook):
                step = current_playbook[index]
                
                action = step.get("action")
                selector = step.get("selector")
                val_tmpl = step.get("value")
                
                # 1. Portero: Check Login
                try:
                    if self._is_login_url(page.url) and action != "navigate":
                         # Fallo inmediato de sesión (esto podría tratarse como error recuperable si soportáramos relogin manual)
                         return False, "SESSION_EXPIRED", index, {"url": page.url}, current_playbook
                except: pass

                # 2. Resolve Vars
                final_selector = self._substitute(selector, data_row)
                final_value = self._substitute(val_tmpl, data_row)
                
                # 3. Path Resolution for Attachments
                try:
                    if action in ["setInputFiles", "upload"] or (action == "fill" and "input[type='file']" in str(final_selector).lower()):
                         if final_value and self.current_execution_id:
                             input_dir = self.paths.get_input_dir(self.current_execution_id)
                             if os.path.basename(final_value) == final_value:
                                 path_check = input_dir / final_value
                                 if path_check.exists():
                                     final_value = str(path_check)
                                 else:
                                     raise FileNotFoundError(f"Adjunto no encontrado: {final_value}")
                except Exception as e:
                     # Capturar error de fichero aquí para que entre en el loop de retry
                     pass # Dejar que falle abajo o lanzar? Mejor lanzar para catch block.
                
                msg = f"   [{index+1}] {action} -> {final_selector} ({final_value})"
                print(msg) 
                if log_callback: log_callback(msg)

                # 4. Action Execution (Atomic Try/Catch for Retry Loop)
                step_success = False
                while not step_success:
                    try:
                        if action == "navigate":
                            await page.goto(final_value, timeout=60000)
                            try: 
                                if self._is_login_url(page.url):
                                    raise SessionExpiredException({"url": page.url})
                            except SessionExpiredException as se: raise se
                            except: pass
                            
                        elif action == "click":
                            await page.click(final_selector, timeout=30000)
                            
                        elif action == "fill":
                            await page.fill(final_selector, str(final_value), timeout=30000)
                            
                        elif action == "wait":
                            if final_selector:
                                await page.wait_for_selector(final_selector, state="visible", timeout=30000)
                            else:
                                await page.wait_for_timeout(int(final_value) if final_value else 1000)
                                
                        elif action == "select":
                            try: await page.select_option(final_selector, label=str(final_value))
                            except: await page.select_option(final_selector, value=str(final_value))
                            
                        elif action == "setInputFiles":
                            await page.set_input_files(final_selector, final_value)
                            
                        elif action == "ai_agent":
                            # Autonomous Delegation
                            instruction = final_value or step.get("value") or ""
                            print(f"[RunPlaybook] [AGENT] Invoking Agent: {instruction}")
                            
                            # Re-use logic for cleaner code
                            # We can instantiate wrapper here or use self.run_agent_interactive if we want to reuse pause logic
                            # But self.run_agent_interactive assumes interactive pause which is fine.
                            # However, we are in playback mode, not recording. So pausing recording is not needed, but harmless.
                            
                            agent_wrapper = BrowserAgentWrapper()
                            # execute_playbook context is self.context usually
                            # Note: execute_playbook creates "page = await self.context.new_page()" if called isolated
                            # But usually self.context is set.
                            # Agent needs CONTEXT, not PAGE (browser-use limitation/design)
                            
                            res = await agent_wrapper.run_agent_task(self.context, instruction)
                            
                            if not res.success:
                                raise Exception(f"Agent Failed: {res.error}")
                            
                            # If successful, logic continues
                            print(f"[RunPlaybook] [OK] Agent Output: {res.output[:100]}...")
                        
                        step_success = True  # Exit retry loop
                        
                    except Exception as e:
                        # --- VISUAL SAFETY NET ---
                        recovered_visually = False
                        if action in ["click", "fill"] and not isinstance(e, SessionExpiredException):
                            print(f"[WARN] Selector falló. Intentando recuperación visual para: '{step.get('description', '')}'")
                            try:
                                # 1. Screenshot in memory
                                png_bytes = await page.screenshot()
                                
                                # 2. Viewport
                                viewport = page.viewport_size or {"width": 1280, "height": 800}
                                
                                # 3. Ask Brain
                                description = step.get("description") or f"Elemento para {action}: {final_selector}"
                                
                                client, license_key = await self._get_brain_client()
                                coords = await client.get_element_coordinates(png_bytes, description, viewport, license_key=license_key)
                                
                                if coords:
                                    vx, vy = coords
                                    # Ensure inside viewport (Safety)
                                    if 0 <= vx <= viewport["width"] and 0 <= vy <= viewport["height"]:
                                        print(f"[VisualSafetyNet] [TARGET] Recuperado! Clicando en ({vx}, {vy})")
                                        await page.mouse.click(vx, vy)
                                        
                                        if action == "fill":
                                            # Focus obtained by click, now type
                                            await page.keyboard.type(str(final_value))
                                            
                                        step_success = True # Marked as success
                                        recovered_visually = True
                                        # break/continue handled by 'while not step_success' check
                                    else:
                                        print(f"[VisualSafetyNet] [ERROR] Coordenadas fuera de rango: {coords}")
                                else:
                                    print("[VisualSafetyNet] [NOTFOUND] Elemento no identificado visualmente.")
                                    
                            except Exception as vis_e:
                                print(f"[VisualSafetyNet] [CRASH] Error en recuperación visual: {vis_e}")

                        if recovered_visually:
                            continue # Loop will check step_success=True and exit

                        # --- EMERGENCY ROOM LOGIC (Fallback) ---
                        if isinstance(e, SessionExpiredException): raise e # No recovering login yet
                        
                        error_msg = str(e).splitlines()[0]
                        print(f"[ERROR] Error en paso {index+1}: {error_msg}")
                        
                        if on_ask_user:
                            # 1. Screenshot error
                            timestamp = datetime.now().strftime("%H%M%S")
                            shot_path = self.paths.get_output_dir(self.current_execution_id) / f"error_step_{index}_{timestamp}.png"
                            try: await page.screenshot(path=str(shot_path))
                            except: shot_path = None
                            
                            print(f"[RPAExecutor] [EMERGENCY] Invocando Sala de Emergencias...")
                            
                            # 2. Ask User
                            try:
                                decision, new_playbook = await on_ask_user(error_msg, str(shot_path) if shot_path else "", step_index=index)
                                
                                if decision == "RETRY":
                                    print("[RPAExecutor] [UPDATE] Reintentando con playbook parcheado...")
                                    current_playbook = new_playbook

                                    # Verificar límites (Defensive Fix)
                                    if index >= len(current_playbook):
                                        print("[WARN] El playbook se ha acortado y el índice actual ya no existe. Saltando al siguiente.")
                                        step_success = True 
                                        break

                                    # Update current step vars from new playbook if changed
                                    step = current_playbook[index]
                                    action = step.get("action")
                                    selector = step.get("selector")
                                    val_tmpl = step.get("value")
                                    # Re-resolve (important!)
                                    final_selector = self._substitute(selector, data_row)
                                    final_value = self._substitute(val_tmpl, data_row)
                                    # Continue loop to try again
                                    continue
                                    
                                elif decision == "SKIP":
                                    print("[RPAExecutor] [SKIP] Saltando paso...")
                                    step_success = True
                                    break
                                    
                                elif decision == "STOP":
                                    print("[RPAExecutor] [STOP] Parada de emergencia solicitada.")
                                    raise e
                                    
                            except Exception as intervention_err:
                                print(f"Error en intervención: {intervention_err}")
                                raise e # Fail if intervention fails
                        else:
                            # No user handler -> Fail standard
                            raise e
                
                # End of While (Retry) -> Next Step
                index += 1

            return True, "OK", -1, None, current_playbook
            
        except Exception as e:
            error_details = {"message": str(e), "step_index": index, "step": step}
            return False, str(e), index, error_details, current_playbook
        finally:
            # Only close if NOT keeping open for debug? For batch we close.
            if page and not page.is_closed(): await page.close()

    def _substitute(self, text, data):
        if not isinstance(text, str): return text
        for k, v in data.items():
            pattern = r"\{\{\s*" + re.escape(str(k)) + r"\s*\}\}"
            text = re.sub(pattern, str(v), text)
        return text

    def extract_variables_from_playbook(self, playbook: list) -> list:
        vars_set = set()
        for step in playbook:
            for field in ["selector", "value", "url"]:
                val = str(step.get(field, ""))
                found = re.findall(r"\{\{\s*([^}]+)\s*\}\}", val)
                vars_set.update(found)
        return list(vars_set)

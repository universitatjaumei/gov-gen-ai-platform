import uuid
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.enums import StepType
import httpx
from client_app.app.database.models import TaskLog
from client_app.app.services.custom_script_service import custom_script_service
from client_app.app.services.sandbox_service import sandbox_service
import pandas as pd
from pathlib import Path
import os
from client_app.app.modules.output.email_sender import EmailSender
from client_app.app.modules.output.email_sender import EmailSender
from client_app.app.services.mail_watcher_service import mail_watcher_service
from client_app.app.services.screenshot_guard import screenshot_guard, ScreenshotGuardAction
from client_app.app.core.audit import audit_operation
import json
import logging
# Brain client resolved dynamically to support both monolith and split modes
brain_client = None  # Will be resolved at runtime via _get_workflow_brain_client()


async def _get_workflow_brain_client():
    """
    Resuelve y retorna el cliente de cerebro (Brain) para el workflow engine.
    Siempre usa BrainAPIClient para mantener consistencia arquitectura (monolito o split).

    Returns:
        BrainAPIClient con la URL resuelta dinámicamente.
    """
    from client_app.app.clients import BrainAPIClient
    from client_app.app.database.models import ServerConnection
    from client_app.app.database.db import client_engine
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlmodel import select

    # Resolve URL from DB (active connection or default)
    async with AsyncSession(client_engine) as session:
        stmt = select(ServerConnection).where(ServerConnection.is_active == True)
        res = await session.exec(stmt)
        conn = res.first()
        url = conn.brain_url if (conn and conn.brain_url) else "http://localhost:8080"
        return BrainAPIClient(base_url=url)

def is_interactive_session() -> bool:
    """Determina si hay un usuario interactivo (UI abierta)."""
    # Implementar según arquitectura (ej: verificar si hay websocket activo)
    # Por ahora hardcodear a False si no se detecta explícitamente UI
    try:
        from nicegui import ui
        # Check if there are active clients connected
        # NiceGUI internal API might differ, assume no interactivity in engine unless notified
        return False 
    except:
        return False

async def create_dashboard_notification(
    title: str,
    message: str,
    notification_type: str = "warning",
    action_url: Optional[str] = None
):
    """Crea una notificación visible en el dashboard."""
    # Placeholder for notification system
    print(f"[NOTIFICATION] {title}: {message} ({action_url})")

def is_safe_path(path: Path | str, base_dir: Path | str) -> bool:
    """Valida que path esté dentro de base_dir."""
    try:
        p = Path(path).resolve()
        b = Path(base_dir).resolve()
        return p.is_relative_to(b)
    except Exception:
        return False

class StepRegistry:
    """Registry de ejecutores por tipo de step."""
    _executors: Dict[str, Callable] = {}

    @classmethod
    def register(cls, step_type: str):
        def decorator(func):
            cls._executors[step_type] = func
            return func
        return decorator

    @classmethod
    def get(cls, step_type: str) -> Optional[Callable]:
        return cls._executors.get(step_type)


def _resolve_variables(text: Any, context: Dict[str, Any]) -> Any:
    """
    Reemplaza expresiones {{variable}} por valores del contexto.
    Soporta {{prev}} como alias de previous_output.
    """
    if not isinstance(text, str):
        return text

    import re

    def replace(match):
        var_name = match.group(1).strip()
        if var_name == "prev":
            var_name = "previous_output"
        
        val = context.get(var_name)
        if val is None:
            # Intentar búsqueda profunda en dicts si var_name tiene puntos
            if "." in var_name:
                parts = var_name.split(".")
                curr = context
                for p in parts:
                    if isinstance(curr, dict):
                        curr = curr.get(p)
                    else:
                        return match.group(0)
                return str(curr) if curr is not None else match.group(0)
            return match.group(0)
        return str(val)

    return re.sub(r"\{\{([^}]+)\}\}", replace, text)


class WorkflowEngine:
    def __init__(self, session):
        self.session = session
        self._current_execution_id = None

    async def _handle_screenshot_for_healing(
        self,
        screenshot_bytes: bytes,
        url: str,
        task_id: int,
        step_index: int
    ) -> dict:
        """
        Maneja el envío de captura para auto-healing.

        En sesión interactiva: muestra diálogo.
        En background: suspende y notifica.
        """
        action = await screenshot_guard.check_policy(url)

        # BLOCK: no se puede hacer auto-healing visual
        if action == ScreenshotGuardAction.BLOCK:
            return {
                "suspended": False,
                "blocked": True,
                "reason": "screenshot_policy_block"
            }

        # ALLOW: proceder directamente
        if action == ScreenshotGuardAction.ALLOW:
            client = await _get_workflow_brain_client()
            if hasattr(client, 'send_visual_request'):
                response = await client.send_visual_request(
                    image_bytes=screenshot_bytes,
                    prompt="Analiza el error y sugiere corrección de selector",
                    context={"url": url}
                )
            else:
                # Fallback: use call_llm if send_visual_request not available
                response = {"suggestion": "Visual analysis not available in this mode"}
            return {
                "suspended": False,
                "blocked": False,
                "brain_response": response
            }

        # REQUIRE_REVIEW
        if is_interactive_session():
            # Usuario presente: mostrar diálogo
            approved = await request_screenshot_approval(screenshot_bytes, url)
            if not approved:
                return {"suspended": False, "cancelled": True}

            client = await _get_workflow_brain_client()
            if hasattr(client, 'send_visual_request'):
                response = await client.send_visual_request(
                    image_bytes=screenshot_bytes,
                    prompt="Analiza el error y sugiere corrección",
                    context={"url": url}
                )
            else:
                response = {"suggestion": "Visual analysis not available in this mode"}
            return {"suspended": False, "brain_response": response}

        # Background: suspender y notificar
        review_id = await self._save_pending_screenshot_review(
            screenshot_bytes=screenshot_bytes,
            url=url,
            task_id=task_id,
            step_index=step_index,
            reason="auto_healing"
        )

        await create_dashboard_notification(
            title="Auto-healing requiere revisión",
            message=f"El workflow necesita analizar una captura de {url}. Revise y apruebe para continuar.",
            notification_type="warning",
            action_url=f"/pending-reviews/{review_id}"
        )

        return {
            "suspended": True,
            "pending_review_id": review_id,
            "reason": "awaiting_user_approval"
        }

    async def _save_pending_screenshot_review(
        self,
        screenshot_bytes: bytes,
        url: str,
        task_id: int,
        step_index: int,
        reason: str
    ) -> int:
        """Guarda la captura y crea registro de revisión pendiente."""
        
        # Guardar imagen
        screenshots_dir = Path("data/pending_screenshots")
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid.uuid4().hex}.png"
        filepath = screenshots_dir / filename
        filepath.write_bytes(screenshot_bytes)

        # Crear registro
        # IMPORTANTE: Usar self.session si es compatible con SQLModel, o crear nueva sesión si self.session es sincrono/otro tipo
        # En execution_flow, self.session seems to be async session (await self.session.commit())
        
        review = PendingScreenshotReview(
            execution_id=self._current_execution_id or "unknown",
            task_id=task_id,
            step_index=step_index,
            screenshot_path=str(filepath),
            source_url=url,
            reason=reason
        )
        self.session.add(review)
        await self.session.commit()
        await self.session.refresh(review)
        return review.id

    async def execute_flow(
        self,
        flow: FlowSpec,
        context: Dict[str, Any],
        stop_on_error: bool = True,
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes a linear flow of tasks.
        """
        if not execution_id:
            execution_id = f"exec_{uuid.uuid4().hex[:12]}"
            
        self._current_execution_id = execution_id
        results = []
        previous_output = None
        final_status = "completed"

        for idx, step in enumerate(flow.steps):
            # Prepare context
            step_context = {
                **context, 
                "previous_output": previous_output,
                "execution_id": execution_id
            }
            
            # Create TaskLog
            log = TaskLog(
                execution_id=execution_id,
                step_index=idx,
                step_name=step.name,
                status="pending",
                started_at=datetime.utcnow()
            )
            self.session.add(log)
            await self.session.commit()
            await self.session.refresh(log)

            start_time = time.perf_counter()
            retries = step.config.get("retries", 0)
            
            # Execution Loop (with retries)
            for attempt in range(retries + 1):
                try:
                    # Execute task
                    output = await self._execute_task(step, step_context)
                    
                    # Success
                    previous_output = output
                    log.status = "completed"
                    log.result_summary = "Success"
                    break # Break retry loop
                
                except Exception as e:
                    # Failure
                    if attempt < retries:
                        continue # Retry
                    
                    log.status = "failed"
                    log.error_message = str(e)
                    
                    if stop_on_error:
                        final_status = "failed"
            
            # Record metrics
            log.duration_ms = int((time.perf_counter() - start_time) * 1000)
            log.completed_at = datetime.utcnow()
            self.session.add(log)
            await self.session.commit()
            
            results.append({"step": step.name, "status": log.status})
            
            if log.status == "failed" and stop_on_error:
                break
        
        return {
            "execution_id": execution_id,
            "status": final_status,
            "results": results
        }

    async def _execute_task(self, task: TaskSpec, context: Dict[str, Any]) -> Any:
        """Executes a single task using the registered executor."""
        # 1. Resolve Executor
        executor = StepRegistry.get(task.type)
        if not executor:
            self.logger.error(f"Executor not found for: {task.type}")
            raise ValueError(f"No executor found for task type: {task.type}")

        # 2. Prepare and Coerce Inputs
        # We might want to apply type coercion here if the task specifies input contracts
        from client_app.app.services.type_compatibility_service import type_compatibility_service
        
        # Determine current input value (usually previous_output)
        current_input = context.get("previous_output")
        
        # 3. Execution based on async/sync nature
        if asyncio.iscoroutinefunction(executor):
            return await executor(task, context)
        else:
            return executor(task, context)


@StepRegistry.register("etl_transform")
@audit_operation(action_type="etl_transform", module="workflow_engine")
async def execute_etl_transform(task: TaskSpec, context: Dict[str, Any]) -> Any:
    """
    Executes an ETL transformation script.
    Input: 'source_file' path or 'previous_output' (DataFrame or path).
    Output: Transformed DataFrame or path (if output_path provided).
    """
    import pandas as pd
    from pathlib import Path
    
    # 1. Resolve Input
    source_path = context.get('source_file')
    df = None

    # Try using previous output as source path if string
    prev = context.get('previous_output')
    if not source_path and isinstance(prev, str) and Path(prev).exists():
        source_path = prev

    # If we have a DataFrame in previous output, use it
    if isinstance(prev, pd.DataFrame):
        df = prev.copy()

    # If we have a dict, try to convert to DataFrame (e.g., from api_fetch)
    if df is None and isinstance(prev, dict):
        # Try common JSON structures: {data: [...]}, {records: [...]}, {rows: [...]}, {result: {...}}
        data_list = None
        for key in ['data', 'records', 'rows', 'items', 'results', 'result']:
            if key in prev:
                candidate = prev[key]
                if isinstance(candidate, list) and candidate and isinstance(candidate[0], dict):
                    data_list = candidate
                    break
                elif isinstance(candidate, dict):
                    # Nested structure like CKAN: result.records
                    for subkey in ['records', 'data', 'rows']:
                        if subkey in candidate and isinstance(candidate[subkey], list):
                            data_list = candidate[subkey]
                            break
                    if data_list:
                        break

        if data_list:
            df = pd.DataFrame(data_list)
        elif isinstance(prev, dict) and all(not isinstance(v, (dict, list)) for v in prev.values()):
            # Flat dict = single record
            df = pd.DataFrame([prev])

    # If we have a list of dicts, convert to DataFrame
    if df is None and isinstance(prev, list) and prev and isinstance(prev[0], dict):
        df = pd.DataFrame(prev)

    # If still no DF, try reading from file
    if df is None:
        if not source_path:
            raise ValueError("No source input (file or DataFrame) found for ETL transform")
            
        path = Path(source_path)
        ext = path.suffix.lower()
        
        try:
            if ext == '.csv':
                df = pd.read_csv(path)
            elif ext in ['.xlsx', '.xls']:
                df = pd.read_excel(path)
            elif ext == '.json':
                df = pd.read_json(path)
            elif ext == '.parquet':
                df = pd.read_parquet(path)
            elif ext == '.xml':
                df = pd.read_xml(path)
            else:
                # Default fallback
                df = pd.read_csv(path)
        except Exception as e:
            raise ValueError(f"Failed to read source file {source_path}: {str(e)}")

    # 2. Get Script (supports both embedded script and script_id reference)
    script = task.config.get("script")

    if not script:
        # Try to load from ScriptLibrary
        # Support both "script_id" and "config_id" for compatibility with flow designer
        script_id = task.config.get("script_id") or task.config.get("config_id")
        if script_id:
            from client_app.app.services.script_library_service import script_library_service

            # Load script from library
            library_script = await script_library_service.get_script(int(script_id))
            if not library_script:
                raise ValueError(f"Script {script_id} not found in library")

            # Verify seal if exists (security for Partner)
            try:
                await script_library_service.verify_asset_seal(int(script_id))
            except ValueError as e:
                # If verification fails, script was altered
                raise RuntimeError(f"Security check failed: {e}")

            # Get code from library entry
            if hasattr(library_script, 'code') and library_script.code:
                script = library_script.code
            elif hasattr(library_script, 'script_path') and library_script.script_path:
                script_path = Path(library_script.script_path)
                if script_path.exists():
                    script = script_path.read_text(encoding='utf-8')
                else:
                    raise ValueError(f"Script file not found: {script_path}")
            else:
                raise ValueError(f"No code found for script {script_id}")

    if not script:
        raise ValueError("No script or script_id found in task config")

    # Safe(r) execution namespace
    namespace = {'pd': pd, 'df': df}
    try:
        exec(script, namespace)
    except Exception as e:
        raise RuntimeError(f"Script execution failed: {str(e)}")
    
    transform_func = namespace.get('transform')
    if not transform_func:
        raise ValueError("Script must define 'transform(df)' function")
        
    try:
        result_df = transform_func(df)
    except Exception as e:
        raise RuntimeError(f"Transformation function failed: {str(e)}")
    
    # 3. Handle Output
    output_path = context.get('output_path')
    if output_path:
        target_format = task.config.get("target_format", "csv")
        try:
            if target_format == 'csv':
                result_df.to_csv(output_path, index=False)
            elif target_format == 'json':
                result_df.to_json(output_path, orient='records', indent=2)
            elif target_format == 'excel':
                result_df.to_excel(output_path, index=False)
            elif target_format == 'parquet':
                result_df.to_parquet(output_path, index=False)
            elif target_format == 'xml':
                result_df.to_xml(output_path, index=False)
            else:
                result_df.to_csv(output_path, index=False)
            return output_path
        except Exception as e:
            raise RuntimeError(f"Failed to write output to {output_path}: {str(e)}")
    
    return result_df


@StepRegistry.register("custom_script")
@audit_operation(action_type="custom_script", module="workflow_engine")
async def execute_custom_script(task: TaskSpec, context: Dict[str, Any]) -> Any:
    """
    Executes a Custom Script ID.
    Config: { "script_id": int, "input_mapping": Dict }
    """
    script_id = task.config.get("script_id")
    if not script_id:
        raise ValueError("script_id is required for custom_script step")
        
    # 1. Fetch Script
    script = await custom_script_service.get_script(script_id)
    if not script:
        raise ValueError(f"Script {script_id} not found")
        
    # 2. Resolve Inputs
    input_mapping = task.config.get("input_mapping", {})
    # Simple resolution: if value starts with {{, resolve from context? 
    # For now, simplistic mapping:
    # We assume context has file paths. Script Service expects 'input_files' list.
    
    # We look for a file to pass.
    # If mapping has 'file' key, use that context key.
    # Default to use 'previous_output' if it's a file path.
    
    input_files = []
    
    # Logic to find input file
    file_key = input_mapping.get("file")
    if file_key:
        val = context.get(file_key)
        if val and isinstance(val, str):
            input_files.append(val)
    else:
        # Fallback
        prev = context.get("previous_output")
        if isinstance(prev, str) and (prev.endswith('.csv') or prev.endswith('.xlsx')):
            input_files.append(prev)
            
    if not input_files and script.input_type != 'none':
         # If script needs input but we have none, maybe warning?
         # Or rely on sandbox execution failing if code requires it.
         pass

    # 3. Log Start
    exec_record = await custom_script_service.log_execution_start(script_id, input_files)
    
    # 4. Execute
    try:
        result = await sandbox_service.execute(
            code=script.code,
            input_files=input_files,
            timeout=300 # 5 min limit for workflow steps
        )
        
        status = "success" if result.get("success") else "error"
        
        # 5. Log End
        await custom_script_service.log_execution_end(
            execution_id=exec_record.id,
            status=status,
            output_files=result.get("output_files", []),
            error_message=result.get("error"),
            output_preview=result.get("preview")
        )
        
        if status == "error":
            raise RuntimeError(f"Custom Script failed: {result.get('error')}")
            
        # Return output
        # If output files exist, return the first one as 'output' for next step
        # Or return the whole result dict
        outputs = result.get("output_files", [])
        if outputs:
            return outputs[0] # Path to file
        return result
        
    except Exception as e:
        # Log failure if not already logged
        await custom_script_service.log_execution_end(
            execution_id=exec_record.id,
            status="error",
            error_message=str(e)
        )
        raise e

@StepRegistry.register("email_send")
@audit_operation(action_type="export", module="workflow_engine")
async def execute_email_send(task: TaskSpec, context: Dict[str, Any]) -> Any:
    """
    Ejecuta un paso de envío de email (EMAIL_SEND).
    Soporta resolución de variables {{}} en destinatarios, asunto y cuerpo.
    Acepta adjuntos desde archivos explícitos o variables de contexto.
    """
    config = task.config
    credential_id = config.get("credential_id")
    if not credential_id:
        raise ValueError("EMAIL_SEND requiere 'credential_id'")
        
    # 1. Obtener Credenciales
    creds = await mail_watcher_service.get_credential(credential_id)
    if not creds:
        raise ValueError(f"Credencial SMTP {credential_id} no encontrada")
        
    # 2. Resolver Variables en campos de texto
    to_field = config.get("to", [])
    if isinstance(to_field, str):
        to_addrs = [addr.strip() for addr in _resolve_variables(to_field, context).split(",") if addr.strip()]
    else:
        to_addrs = [_resolve_variables(addr, context) for addr in to_field]
        
    if not to_addrs:
        raise ValueError("EMAIL_SEND requiere al menos un destinatario en 'to'")

    subject = _resolve_variables(config.get("subject", "Gov Gen AI Notification"), context)
    body = _resolve_variables(config.get("body", ""), context)
    is_html = config.get("is_html", config.get("html", False)) # Compatibilidad con ambos nombres
    
    # CC / BCC
    cc = config.get("cc")
    if cc and isinstance(cc, str):
        cc = [addr.strip() for addr in _resolve_variables(cc, context).split(",") if addr.strip()]
    
    bcc = config.get("bcc")
    if bcc and isinstance(bcc, str):
        bcc = [addr.strip() for addr in _resolve_variables(bcc, context).split(",") if addr.strip()]

    # 3. Resolver Adjuntos
    attachments = []
    
    # Adjuntar previous_output automáticamente si se solicita
    if config.get("attach_previous_output"):
        prev = context.get("previous_output")
        if prev and isinstance(prev, str) and Path(prev).exists():
            attachments.append(Path(prev))
    
    # Adjuntos explícitos desde configuración (puede ser una lista de rutas o una variable)
    extra_attachments = config.get("attachments")
    if extra_attachments:
        # Si es un string literal {{var}}, resolvemos y esperamos una lista de Paths o un Path
        if isinstance(extra_attachments, str) and extra_attachments.startswith("{{") and extra_attachments.endswith("}}"):
            var_name = extra_attachments[2:-2].strip()
            resolved_val = context.get(var_name)
            if resolved_val:
                if isinstance(resolved_val, list):
                    for item in resolved_val:
                        if isinstance(item, (str, Path)) and Path(item).exists():
                            attachments.append(Path(item))
                elif isinstance(resolved_val, (str, Path)) and Path(resolved_val).exists():
                    attachments.append(Path(resolved_val))
        elif isinstance(extra_attachments, list):
            for item in extra_attachments:
                # Resolver variable en la ruta si existe
                item_path = _resolve_variables(item, context)
                if Path(item_path).exists():
                    attachments.append(Path(item_path))

    # 4. Enviar (Blocking operation in thread)
    from client_app.app.modules.security.encryption_service import EncryptionService
    encryption = EncryptionService()
    
    # Preparar dict para EmailSender
    smtp_config = {
        "server": creds['server'],
        "port": creds['port'],
        "username": creds['user'],
        "password": creds['password']
    }
    
    sender = EmailSender(smtp_config, encryption)
    
    # Usar to_thread para no bloquear el loop de eventos
    message_id = await asyncio.to_thread(
        sender.send_with_file_attachments,
        from_addr=creds['user'],
        to_addrs=to_addrs,
        subject=subject,
        body=body,
        file_paths=attachments,
        html=is_html
    )
    
    return {
        "success": True,
        "message_id": message_id,
        "recipients": to_addrs,
        "subject": subject,
        "attachment_count": len(attachments)
    }
    
@StepRegistry.register("rpa_execute")
@audit_operation(action_type="rpa_execute", module="workflow_engine")
async def execute_rpa_step(task: TaskSpec, context: Dict[str, Any]) -> Any:
    """
    Executes an RPA Playbook.
    Config: {
        "playbook_id": int,
        "playbook_name": str,
        "input_mapping": Dict[str, Any]
    }
    """
    # Lazy Import to avoid circular deps
    from client_app.app.core.rpa_executor import RPAExecutor

    # 1. Resolve Brain client dynamically (supports monolith and split modes)
    brain = await _get_workflow_brain_client()
    if not brain:
        raise RuntimeError("RPA Step requires initialized Brain Service")

    # 2. Config Resolution
    playbook_id = task.config.get("playbook_id")
    playbook_name = task.config.get("playbook_name")
    
    if not playbook_id and not playbook_name:
        raise ValueError("RPA Step requires 'playbook_id' or 'playbook_name'")
        
    # 3. Instantiate Executor
    # We create a fresh executor for this step. 
    # Ideally we'd manage a pool/singleton but RPA is stateful (browser) so new instance is safer.
    executor = RPAExecutor(brain_service=brain)
    
    # Set execution context if we want logs/screenshots to go to specific folder
    exec_id = context.get("execution_id")
    if exec_id:
        executor.current_execution_id = exec_id
        # Ensure paths are set up (executor uses PathManager internally)
        # But we might need to manually ensure directories if executor doesn't do it on set context from ID
        # executor.set_execution_context(exec_id) # This handles dir creation!
        executor.set_execution_context(exec_id)
        
    try:
        # 4. Load Playbook
        identifier = playbook_id if playbook_id else playbook_name
        pb_data = await executor.load_master_playbook(identifier)
        
        if not pb_data or "actions" not in pb_data:
            raise ValueError(f"Playbook '{identifier}' not found or empty")
            
        # 5. Data Mapping
        # We merge context into a flat dictionary for substitution {{var}}
        # Priority: input_mapping > context
        run_data = context.copy()
        
        input_mapping = task.config.get("input_mapping", {})
        for target_var, source_val in input_mapping.items():
            # If source_val is a key in context, use its value
            # If not, use source_val as literal
            if isinstance(source_val, str) and source_val in context:
                run_data[target_var] = context[source_val]
            else:
                run_data[target_var] = source_val
        
        # 6. Execute
        # execute_playbook returns: (Success, ErrorMsg, FailedIndex, ErrorDetails, UpdatedPlaybook)
        success, error_msg, failed_idx, err_details, _ = await executor.execute_playbook(
            playbook=pb_data["actions"],
            data_row=run_data
            # No interactive user callback for headless workflow execution by default
            # unless we implement a websocket notifier mechanism.
        )
        
        if not success:
            raise RuntimeError(f"RPA Failed at step {failed_idx}: {error_msg}")
            
        return "RPA_SUCCESS"
        
    finally:
        # Cleanup browser if left open
        if executor.browser:
            await executor.browser.close()
        if executor.playwright:
            await executor.playwright.stop()


@StepRegistry.register("api_fetch")
@audit_operation(action_type="query", module="workflow_engine")
async def execute_api_fetch(task: TaskSpec, context: Dict[str, Any]) -> Any:
    """
    Execute HTTP API request.
    ...
    """
    from client_app.app.services.api_connection_service import api_connection_service
    log = logging.getLogger(__name__)

    url = task.config.get("url")
    method = task.config.get("method", "GET").upper()
    headers = task.config.get("headers", {})
    json_body = task.config.get("json_body")
    params = task.config.get("params")
    output_key = task.config.get("output_var")
    config_id = task.config.get("config_id")

    log.info(f"[WorkflowEngine] execute_api_fetch: url={url}, config_id={config_id}, task_config={task.config}")

    # Resolve from DB if config_id is provided and url is missing
    if not url and config_id:
        log.info(f"[WorkflowEngine] Resolving config from DB for id={config_id}")
        db_config = await api_connection_service.get_config(int(config_id))
        if db_config:
            url = db_config.url
            method = db_config.method.upper()
            log.info(f"[WorkflowEngine] Resolved URL: {url}")
            
            # Resolve headers
            if db_config.headers:
                try:
                    db_headers = json.loads(db_config.headers) if isinstance(db_config.headers, str) else db_config.headers
                    # Merge: manual config takes precedence over saved config
                    final_headers = db_headers.copy()
                    final_headers.update(headers)
                    headers = final_headers
                except:
                    pass
            
            # Resolve body if not provided manually
            if json_body is None and db_config.body:
                try:
                    json_body = json.loads(db_config.body) if isinstance(db_config.body, str) else db_config.body
                except:
                    pass
        else:
            log.warning(f"[WorkflowEngine] Config {config_id} not found in database")

    if not url:
        raise ValueError("API Fetch step requires 'url' (none found in task config or linked config_id)")

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            json=json_body,
            params=params,
            timeout=task.config.get("timeout", 30.0)
        )
        
        # Check status
        # If ignore_errors is set in config? Defaults to raise
        if not task.config.get("ignore_errors"):
            response.raise_for_status()
            
        # Parse response
        try:
            data = response.json()
        except:
            data = response.text
            
        if output_key:
            context[output_key] = data
            
        return data


@StepRegistry.register("webhook")
async def execute_webhook(task: TaskSpec, context: Dict[str, Any]) -> Any:
    """
    Send a Webhook (Fire-and-forget style or simple POST).
    Config:
        url: str
        payload: dict
        headers: dict
    """
    url = task.config.get("url")
    payload = task.config.get("payload")
    headers = task.config.get("headers", {})

    if not url:
        raise ValueError("Webhook step requires 'url'")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url=url,
            json=payload,
            headers=headers,
            timeout=task.config.get("timeout", 10.0)
        )

        response.raise_for_status()
        return {"status": response.status_code, "body": response.text}


@StepRegistry.register("report_generate")
@audit_operation(action_type="export", module="workflow_engine")
async def execute_report_generate(task: TaskSpec, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Genera un informe PDF usando una plantilla.

    Config:
        template_id: int (ID de ReportTemplate, obligatorio)
        title_source: str (literal:Titulo o var:nombre_variable)
        data_source: str (var:variable_datos, default: previous_output)
        output_filename: str (nombre del archivo, soporta {{date}})
        output_var: str (nombre de la variable de salida)
        run_analysis: bool (usar IA para analisis, default: False)
        analysis_instructions: str (instrucciones para IA)
        styles_override: dict (sobrescribir estilos de la plantilla)

    Returns:
        {
            "report_file": str (path al archivo generado),
            "report_path": str (path absoluto),
            "format": str ("pdf")
        }
    """
    from client_app.app.modules.factory.report_factory import ReportFactory
    from client_app.app.database.models import ReportTemplate, ReportHistory
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlmodel import select
    from client_app.app.database.db import client_engine
    import json

    # 1. Obtener plantilla
    template_id = task.config.get("template_id")
    if not template_id:
        raise ValueError("template_id es obligatorio para report_generate")

    async with AsyncSession(client_engine) as session:
        result = await session.exec(
            select(ReportTemplate).where(ReportTemplate.id == template_id)
        )
        template = result.first()

    if not template:
        raise ValueError(f"Plantilla con id={template_id} no encontrada")

    # 2. Resolver datos de origen
    data_source = task.config.get("data_source", "previous_output")
    report_data = None

    if data_source.startswith("var:"):
        var_name = data_source[4:]
        report_data = context.get(var_name)
    else:
        report_data = context.get(data_source)

    # Si no hay datos explícitos, usar previous_output
    if report_data is None:
        report_data = context.get("previous_output")

    # 3. Construir contexto del reporte
    report_context = {}

    # Resolver título
    title_source = task.config.get("title_source", "")
    if title_source.startswith("literal:"):
        report_context["title"] = title_source[8:]
    elif title_source.startswith("var:"):
        var_name = title_source[4:]
        report_context["title"] = context.get(var_name, "Informe")
    else:
        report_context["title"] = title_source or "Informe Generado"

    # Fecha
    report_context["date"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Datos de tabla (si es DataFrame o dict/list)
    if isinstance(report_data, pd.DataFrame):
        report_context["table_data"] = report_data
    elif isinstance(report_data, dict):
        # Intentar convertir a DataFrame si tiene estructura tabular
        if "data" in report_data and isinstance(report_data["data"], list):
            report_context["table_data"] = pd.DataFrame(report_data["data"])
        elif isinstance(report_data.get("items"), list):
            report_context["table_data"] = pd.DataFrame(report_data["items"])
        else:
            # Usar como resumen
            report_context["summary"] = json.dumps(report_data, indent=2, ensure_ascii=False)
    elif isinstance(report_data, list):
        report_context["table_data"] = pd.DataFrame(report_data)
    elif isinstance(report_data, str) and Path(report_data).exists():
        # Es un archivo, intentar leerlo
        file_path = Path(report_data)
        ext = file_path.suffix.lower()
        if ext == ".csv":
            report_context["table_data"] = pd.read_csv(file_path)
        elif ext in [".xlsx", ".xls"]:
            report_context["table_data"] = pd.read_excel(file_path)
        elif ext == ".json":
            report_context["table_data"] = pd.read_json(file_path)

    # Estilos (mezclar default de plantilla con override)
    default_styles = {}
    if template.default_styles:
        try:
            default_styles = json.loads(template.default_styles)
        except:
            pass

    styles_override = task.config.get("styles_override", {})
    report_context["styles"] = {**default_styles, **styles_override}

    # 4. Resolver path de salida
    output_filename = task.config.get("output_filename", "informe_{{date}}.pdf")
    # Reemplazar variables en nombre de archivo
    output_filename = output_filename.replace("{{date}}", datetime.now().strftime("%Y%m%d_%H%M%S"))
    execution_id = context.get("execution_id", "local")
    output_filename = output_filename.replace("{{execution_id}}", execution_id)

    # Directorio de salida
    output_dir = Path("data/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_filename

    # 5. Generar PDF
    # Determinar backend según tipo de plantilla
    if template.template_type == "html":
        factory = ReportFactory(backend="html")
        template_name = template.template_source
    else:
        factory = ReportFactory(backend="reportlab")
        template_name = None

    # Opciones de página (tamaño y orientación)
    page_options = {
        'page_size': task.config.get('page_size', 'A4'),
        'orientation': task.config.get('orientation', 'portrait')
    }

    result_path = factory.generate_pdf(
        context=report_context,
        output_path=str(output_path),
        template_name=template_name,
        page_options=page_options
    )

    # 6. Registrar en historial
    async with AsyncSession(client_engine) as session:
        history = ReportHistory(
            report_name=report_context.get("title", "Informe"),
            pdf_path=result_path,
            template_used=template.name,
            status="success"
        )
        session.add(history)
        await session.commit()

    # 7. Retornar resultado
    return {
        "report_file": result_path,
        "report_path": str(Path(result_path).absolute()),
        "format": "pdf"
    }


# ============================================================================
# EJECUTORES DE ENTRADA (INPUTS)
# ============================================================================

@StepRegistry.register("folder_scan")
@audit_operation(action_type="query", module="workflow_engine")
async def execute_folder_scan(task: TaskSpec, context: Dict[str, Any]) -> Any:
    """
    Escanea una carpeta y lista archivos según patrón.

    Config esperada:
        scan_path: str (ruta a escanear, soporta {{variables}})
        file_pattern: str (patrón glob, ej: "*.pdf", default: "*")
        recursive: bool (incluir subdirectorios, default: False)
        max_files: int (límite de archivos, default: 100)
        include_directories: bool (incluir carpetas, default: False)

    Output:
        Dict con lista de archivos encontrados y metadata
    """
    from client_app.app.services.file_system_service import file_system_service

    # 1. Resolver variables en path
    scan_path = task.config.get('scan_path', '')
    scan_path = _resolve_variables(scan_path, context)

    if not scan_path:
        raise ValueError("scan_path is required for FOLDER_SCAN")

    # 2. Obtener configuración
    file_pattern = task.config.get('file_pattern', '*')
    recursive = task.config.get('recursive', False)
    max_files = task.config.get('max_files', 100)
    include_directories = task.config.get('include_directories', False)

    # 3. Ejecutar escaneo
    result = await file_system_service.scan_folder(
        path=scan_path,
        pattern=file_pattern,
        recursive=recursive,
        max_files=max_files,
        include_directories=include_directories
    )

    if not result.success:
        raise RuntimeError(f"Folder scan failed: {result.error}")

    # 4. Retornar resultado estructurado
    return result.to_dict()


@StepRegistry.register("email_scan")
@audit_operation(action_type="query", module="workflow_engine")
async def execute_email_scan(task: TaskSpec, context: Dict[str, Any]) -> Any:
    """
    Busca emails por criterio y descarga adjuntos.

    Config esperada:
        credential_id: int (ID de credencial IMAP)
        subject_contains: str (filtro de asunto, opcional)
        from_address: str (filtro de remitente, opcional)
        since_date: str (fecha ISO, opcional)
        folder: str (carpeta IMAP, default: "INBOX")
        has_attachments: bool (solo con adjuntos, default: False)
        max_emails: int (límite, default: 50)
        download_attachments: bool (descargar adjuntos, default: True)

    Output:
        Dict con lista de emails y adjuntos
    """
    from client_app.app.services.email_scan_service import (
        email_scan_service,
        EmailSearchCriteria
    )

    # 1. Validar credencial
    credential_id = task.config.get('credential_id')
    if not credential_id:
        raise ValueError("credential_id is required for EMAIL_SCAN")

    # 2. Construir criterios de búsqueda
    since_date = None
    if task.config.get('since_date'):
        since_date = datetime.fromisoformat(task.config['since_date'])

    before_date = None
    if task.config.get('before_date'):
        before_date = datetime.fromisoformat(task.config['before_date'])

    criteria = EmailSearchCriteria(
        subject_contains=task.config.get('subject_contains'),
        from_address=task.config.get('from_address'),
        to_address=task.config.get('to_address'),
        since_date=since_date,
        before_date=before_date,
        folder=task.config.get('folder', 'INBOX'),
        has_attachments=task.config.get('has_attachments', False),
        max_emails=task.config.get('max_emails', 50),
        mark_as_read=task.config.get('mark_as_read', False)
    )

    # 3. Ejecutar escaneo
    download_attachments = task.config.get('download_attachments', True)

    result = await email_scan_service.scan_emails(
        credential_id=credential_id,
        criteria=criteria,
        download_attachments=download_attachments
    )

    if not result.success:
        raise RuntimeError(f"Email scan failed: {result.error}")

    # 4. Retornar resultado
    return result.to_dict()


@StepRegistry.register("sql_query")
@audit_operation(action_type="query", module="workflow_engine")
async def execute_sql_query(task: TaskSpec, context: Dict[str, Any]) -> Any:
    """
    Ejecuta una consulta SQL SELECT.

    Config esperada:
        connection_id: int (ID del átomo CONNECTION subtipo DATABASE)
        query: str (consulta SQL)
        parameters: dict (parámetros nombrados)
        max_rows: int (límite de filas, default 1000)
        timeout_seconds: int (timeout, default 30)

    Output:
        Dict con rows, row_count, columns, execution_time_ms
    """
    from client_app.app.services.database_connection_service import database_connection_service

    # 1. Obtener configuración
    connection_id = task.config.get('connection_id')
    query = task.config.get('query')
    parameters = task.config.get('parameters', {})
    max_rows = task.config.get('max_rows', 1000)
    timeout = task.config.get('timeout_seconds', 30)

    if not connection_id:
        raise ValueError("connection_id is required for SQL_QUERY")
    if not query:
        raise ValueError("query is required for SQL_QUERY")

    # 2. Validar que es SELECT (seguridad)
    query_upper = query.strip().upper()
    if not query_upper.startswith('SELECT'):
        raise ValueError("SQL_QUERY only supports SELECT statements")

    # Detectar statements peligrosos
    dangerous = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'TRUNCATE', 'ALTER', 'CREATE']
    for keyword in dangerous:
        if keyword in query_upper:
            raise ValueError(f"SQL_QUERY cannot contain {keyword} statements")

    # 3. Resolver variables en query
    for var_name, var_value in context.items():
        if isinstance(var_value, (str, int, float)):
            query = query.replace(f'{{{{{var_name}}}}}', str(var_value))

    # 4. Ejecutar query
    start_time = time.perf_counter()

    result = await database_connection_service.execute_query(
        connection_id=connection_id,
        query=query,
        parameters=parameters,
        max_rows=max_rows,
        timeout=timeout
    )

    execution_time = int((time.perf_counter() - start_time) * 1000)

    return {
        'rows': result['rows'],
        'row_count': len(result['rows']),
        'columns': result['columns'],
        'execution_time_ms': execution_time
    }


# ============================================================================
# EJECUTORES DE PROCESAMIENTO (PROCESSORS)
# ============================================================================

@StepRegistry.register("extraction")
@audit_operation(action_type="extraction", module="workflow_engine")
async def execute_extraction_ia(task: TaskSpec, context: Dict[str, Any]) -> Any:
    """
    Ejecuta una extracción de datos usando IA.

    Config esperada:
        script_id: int (ID en ScriptLibrary) O
        automation_id: int (ID en UserExtractionConfig)

    Input:
        previous_output: str (path a PDF/imagen)

    Output:
        Dict con datos extraídos según el schema configurado
    """
    from client_app.app.services.extraction_service import extraction_service
    from client_app.app.services.script_library_service import script_library_service

    # 1. Resolver archivo de entrada
    input_file = context.get('previous_output')
    if isinstance(input_file, dict):
        # Puede venir como dict con file_path
        input_file = input_file.get('file_path') or input_file.get('files', [None])[0]

    if not input_file:
        input_file = task.config.get('input_file')

    if not input_file or not Path(input_file).exists():
        raise ValueError(f"No input file found for extraction: {input_file}")

    # 2. Cargar configuración de extracción
    # Support both "script_id" and "config_id" for compatibility with flow designer
    script_id = task.config.get('script_id') or task.config.get('config_id')
    automation_id = task.config.get('automation_id')

    extraction_schema = {}
    user_prompt = task.config.get('user_prompt', '')

    if script_id:
        # Cargar desde ScriptLibrary
        lib_script = await script_library_service.get_script(int(script_id))
        if not lib_script:
            raise ValueError(f"Extraction script {script_id} not found")

        # Extraer schema del data_contract
        if hasattr(lib_script, 'data_contract') and lib_script.data_contract:
            extraction_schema = lib_script.data_contract.get('output_schema', {})

    elif automation_id:
        # Usar UserExtractionConfig directamente
        extraction_schema = task.config.get('schema', {})
    else:
        raise ValueError("No script_id or automation_id provided")

    # 3. Ejecutar extracción
    result = await extraction_service.extract_from_file(
        file_path=input_file,
        schema=extraction_schema,
        user_prompt=user_prompt
    )

    return result


@StepRegistry.register("pdf_tools")
@audit_operation(action_type="transform", module="workflow_engine")
async def execute_pdf_tools(task: TaskSpec, context: Dict[str, Any]) -> Any:
    """
    Ejecuta operaciones sobre PDFs (merge, split, optimize).

    Config esperada:
        operation: str ('merge', 'split', 'optimize')

        Para merge:
            input_files: List[str] O usar previous_output
            output_name: str

        Para split:
            split_mode: str ('ranges', 'pages', 'all')
            ranges: List[{start, end}] | pages: List[int]

        Para optimize:
            optimization_level: int (1-4)

    Output:
        str | List[str] (path(s) a archivo(s) generado(s))
    """
    from client_app.app.services.pdf_tools_service import pdf_tools_service

    operation = task.config.get('operation')
    if not operation:
        raise ValueError("operation is required for PDF_TOOLS")

    # Resolver archivos de entrada
    input_files = task.config.get('input_files', [])
    prev = context.get('previous_output')

    if not input_files:
        if isinstance(prev, list):
            input_files = [f for f in prev if isinstance(f, str) and Path(f).exists()]
        elif isinstance(prev, str) and Path(prev).exists():
            input_files = [prev]
        elif isinstance(prev, dict):
            # Puede ser ScanResult o similar
            files = prev.get('files', [])
            if files:
                input_files = [f.get('path') or f for f in files if isinstance(f, (str, dict))]

    if not input_files:
        raise ValueError("No input files found for PDF_TOOLS")

    # Asegurar que son strings
    input_files = [str(f) for f in input_files if f]

    # Ejecutar operación
    if operation == 'merge':
        output_name = task.config.get('output_name', 'merged.pdf')
        result = await pdf_tools_service.merge(
            input_files=input_files,
            output_name=output_name,
            optimize=task.config.get('optimize', True)
        )
        return result  # Path al PDF combinado

    elif operation == 'split':
        split_mode = task.config.get('split_mode', 'all')
        if split_mode == 'ranges':
            ranges = task.config.get('ranges', [])
            result = await pdf_tools_service.split_by_ranges(
                input_file=input_files[0],
                ranges=ranges
            )
        elif split_mode == 'pages':
            pages = task.config.get('pages', [])
            result = await pdf_tools_service.split_by_pages(
                input_file=input_files[0],
                pages=pages
            )
        else:  # 'all'
            result = await pdf_tools_service.split_all(
                input_file=input_files[0]
            )
        return result  # Lista de paths

    elif operation == 'optimize':
        level = task.config.get('optimization_level', 3)
        result = await pdf_tools_service.optimize(
            input_file=input_files[0],
            level=level
        )
        return result  # Path al PDF optimizado

    else:
        raise ValueError(f"Unknown PDF operation: {operation}")


@StepRegistry.register("graphics")
@audit_operation(action_type="transform", module="workflow_engine")
async def execute_graphics(task: TaskSpec, context: Dict[str, Any]) -> Any:
    """
    Genera visualizaciones (gráficos).

    Config esperada (Modo Determinista):
        mode: 'assisted'
        chart_config: ChartConfiguration serializado

    Config esperada (Modo IA):
        mode: 'ai'
        user_prompt: str

    Input:
        previous_output: DataFrame o path a archivo de datos

    Output:
        str (path a imagen PNG generada)
    """
    from client_app.app.services.deterministic_graphics_service import DeterministicGraphicsService
    from client_app.app.services.script_library_service import script_library_service

    # 1. Resolver datos de entrada
    df = None
    prev = context.get('previous_output')

    if isinstance(prev, pd.DataFrame):
        df = prev
    elif isinstance(prev, dict) and 'rows' in prev:
        # SQL result or similar
        df = pd.DataFrame(prev['rows'])
    elif isinstance(prev, str) and Path(prev).exists():
        # Intentar cargar archivo
        ext = Path(prev).suffix.lower()
        if ext == '.csv':
            df = pd.read_csv(prev)
        elif ext in ['.xlsx', '.xls']:
            df = pd.read_excel(prev)
        elif ext == '.json':
            df = pd.read_json(prev)
        elif ext == '.parquet':
            df = pd.read_parquet(prev)

    if df is None:
        raise ValueError("No valid DataFrame input found for GRAPHICS")

    # 2. Determinar modo
    mode = task.config.get('mode', 'assisted')
    # Support both "script_id" and "config_id" for compatibility with flow designer
    script_id = task.config.get('script_id') or task.config.get('config_id')
    chart_config = {}

    # Si hay script_id, cargar configuración desde ScriptLibrary
    if script_id:
        lib_script = await script_library_service.get_script(int(script_id))
        if lib_script and hasattr(lib_script, 'source_metadata') and lib_script.source_metadata:
            chart_config = lib_script.source_metadata.get('chart_config', {})
            mode = 'assisted'
    else:
        chart_config = task.config.get('chart_config', {})

    # 3. Generar visualización
    output_dir = Path("data/graphics")
    output_dir.mkdir(parents=True, exist_ok=True)

    exec_id = context.get('execution_id', uuid.uuid4().hex[:8])
    filename = f"chart_{exec_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    output_path = output_dir / filename

    if mode == 'assisted' and chart_config:
        # Modo determinista
        from client_app.app.models.chart_configuration import ChartConfiguration
        config = ChartConfiguration(**chart_config)

        service = DeterministicGraphicsService()
        result_bytes = await service.generate_chart(df, config)

        output_path.write_bytes(result_bytes)
    else:
        # Modo IA - usar GraphicsFactory
        from client_app.app.modules.factory.graphics_factory import GraphicsFactory
        factory = GraphicsFactory()

        user_prompt = task.config.get('user_prompt', 'Generate a relevant chart')
        metadata = factory.analyze_dataframe(df)
        script = await factory.generate_script(metadata, user_prompt)
        result_bytes = await factory.execute_script(script, df)

        output_path.write_bytes(result_bytes)

    return str(output_path)


# ============================================================================
# EJECUTORES DE SALIDA (OUTPUTS)
# ============================================================================

@StepRegistry.register("archive_file")
@audit_operation(action_type="export", module="workflow_engine")
async def execute_archive_file(task: TaskSpec, context: Dict[str, Any]) -> Any:
    """
    Archiva (copia/mueve) archivos a una ruta destino.

    Config esperada:
        source_path: str (archivo origen, soporta {{variables}} o usa previous_output)
        destination_path: str (carpeta/archivo destino, soporta {{variables}})
        operation: str ('copy' o 'move', default: 'copy')
        create_dirs: bool (crear directorios si no existen, default: True)
        overwrite: bool (sobreescribir si existe, default: False)

    Output:
        Dict con ruta final del archivo
    """
    from client_app.app.services.file_system_service import (
        file_system_service,
        FileOperation
    )

    # 1. Resolver archivo fuente
    source_path = task.config.get('source_path')

    # Si no hay source_path explícito, usar previous_output
    if not source_path:
        prev = context.get('previous_output')
        if isinstance(prev, str) and Path(prev).exists():
            source_path = prev
        elif isinstance(prev, dict):
            source_path = prev.get('file_path') or prev.get('report_file') or prev.get('report_path')
        elif isinstance(prev, list) and prev:
            # Tomar el primer archivo
            source_path = prev[0] if isinstance(prev[0], str) else prev[0].get('path')

    if not source_path:
        raise ValueError("No source file found for ARCHIVE_FILE")

    source_path = _resolve_variables(source_path, context)

    # 2. Resolver destino
    destination_path = task.config.get('destination_path', '')
    destination_path = _resolve_variables(destination_path, context)

    # Soportar variables de fecha/tiempo en destino
    now = datetime.now()
    destination_path = destination_path.replace('{{date}}', now.strftime('%Y%m%d'))
    destination_path = destination_path.replace('{{time}}', now.strftime('%H%M%S'))
    destination_path = destination_path.replace('{{datetime}}', now.strftime('%Y%m%d_%H%M%S'))

    if not destination_path:
        raise ValueError("destination_path is required for ARCHIVE_FILE")

    # 3. Extraer prefijo y sufijo (Reglas Mágicas)
    prefix = task.config.get('prefix', '')
    suffix = task.config.get('suffix', '')
    
    # Soportar variables de fecha/tiempo nativas también en prefijos/sufijos
    prefix = _resolve_variables(prefix, context)
    prefix = prefix.replace('{{date}}', now.strftime('%Y%m%d'))
    prefix = prefix.replace('{{time}}', now.strftime('%H%M%S'))
    prefix = prefix.replace('{{datetime}}', now.strftime('%Y%m%d_%H%M%S'))

    suffix = _resolve_variables(suffix, context)
    suffix = suffix.replace('{{date}}', now.strftime('%Y%m%d'))
    suffix = suffix.replace('{{time}}', now.strftime('%H%M%S'))
    suffix = suffix.replace('{{datetime}}', now.strftime('%Y%m%d_%H%M%S'))

    # 4. Operación
    operation_str = task.config.get('operation', 'copy').lower()
    operation = FileOperation.COPY if operation_str == 'copy' else FileOperation.MOVE

    # 5. Ejecutar archivado
    result = await file_system_service.archive_file(
        source_path=source_path,
        destination_path=destination_path,
        operation=operation,
        create_dirs=task.config.get('create_dirs', True),
        overwrite=task.config.get('overwrite', False),
        prefix=prefix,
        suffix=suffix
    )

    if not result.success:
        raise RuntimeError(f"Archive operation failed: {result.error}")

    return result.to_dict()


@StepRegistry.register("llm_process")
@audit_operation(action_type="transform", module="workflow_engine")
async def execute_llm_process(task: TaskSpec, context: Dict[str, Any]) -> Any:
    """
    Procesa texto con un LLM usando anonimización PII.

    Config esperada:
        instruction: str (prompt principal, soporta {{variables}})
        system_prompt: str (contexto del sistema, opcional)
        output_format: str ('text', 'json', 'markdown', default: 'text')
        temperature: float (0.0-1.0, default: 0.7)
        max_tokens: int (default: 1024)

    Input:
        previous_output: str (texto a procesar) O
        input_text: str en config

    Output:
        str o Dict según output_format
    """
    from client_app.app.modules.privacy.anonymizer import AnonymizationContext

    # 1. Obtener configuración
    instruction = task.config.get('instruction', '')
    system_prompt = task.config.get('system_prompt', '')
    output_format = task.config.get('output_format', 'text')
    temperature = task.config.get('temperature', 0.7)
    max_tokens = task.config.get('max_tokens', 1024)

    if not instruction:
        raise ValueError("instruction is required for LLM_PROCESS")

    # 2. Resolver variables en instruction y system_prompt
    instruction = _resolve_variables(instruction, context)
    system_prompt = _resolve_variables(system_prompt, context)

    # 3. Obtener texto de entrada
    input_text = task.config.get('input_text')
    if not input_text:
        prev = context.get('previous_output')
        if isinstance(prev, str):
            input_text = prev
        elif isinstance(prev, dict):
            # Intentar extraer texto de estructuras comunes
            input_text = prev.get('text') or prev.get('content') or prev.get('body') or str(prev)
        elif isinstance(prev, list):
            # Concatenar si es lista de strings
            input_text = '\n'.join(str(item) for item in prev)
        else:
            input_text = str(prev) if prev else ''

    if not input_text:
        raise ValueError("No input text found for LLM_PROCESS")

    # Resolver variables en input_text también
    input_text = _resolve_variables(input_text, context)

    # 4. Anonimizar texto de entrada (proteger PII)
    anon_ctx = AnonymizationContext()
    anonymized_input = anon_ctx.anonymize(input_text)
    pii_count = sum(anon_ctx.stats.values())

    # 5. Construir prompt final con contexto de sistema si existe
    if system_prompt:
        full_prompt = f"[CONTEXTO DEL SISTEMA]\n{system_prompt}\n\n[INSTRUCCIÓN]\n{instruction}\n\n[TEXTO A PROCESAR]\n{anonymized_input}"
    else:
        full_prompt = f"{instruction}\n\n---\n{anonymized_input}"

    # 6. Llamar al Brain LLM (Tier 1 - extraccion_pdf para texto rápido)
    brain = await _get_workflow_brain_client()

    try:
        # Usar service_id para obtener el prompt del servidor y role para el tier
        response = await brain.call_llm(
            prompt=full_prompt,
            role="extraccion_pdf",  # Tier 1 - rápido y económico para texto
            service_id="sys_llm_process",
            temperature=temperature
        )

        # call_llm devuelve string directamente
        llm_output = response if isinstance(response, str) else str(response)

    except Exception as e:
        raise RuntimeError(f"LLM call failed: {str(e)}")

    # 7. Rehydratar respuesta (restaurar datos PII)
    rehydrated_output = anon_ctx.deanonymize(llm_output)

    # 8. Formatear salida según output_format
    if output_format == 'json':
        import json
        try:
            # Intentar parsear como JSON
            result = json.loads(rehydrated_output)
        except json.JSONDecodeError:
            # Si falla, devolver como dict con el texto
            result = {'response': rehydrated_output, 'format': 'text'}
    else:
        result = rehydrated_output

    # Añadir metadata
    return {
        'output': result,
        'format': output_format,
        'pii_protected': pii_count,
        'input_length': len(input_text),
        'output_length': len(str(result))
    }


@StepRegistry.register("sql_insert")
@audit_operation(action_type="export", module="workflow_engine")
async def execute_sql_insert(task: TaskSpec, context: Dict[str, Any]) -> Any:
    """
    Inserta o actualiza datos en una tabla SQL.

    Config esperada:
        connection_id: int (ID de credencial de BD)
        table_name: str (nombre de la tabla)
        column_mapping: Dict[str, str] (mapeo columna → expresión/variable)
        mode: str ('insert', 'upsert', 'update', default: 'insert')
        primary_key: str (columna PK para upsert/update)
        batch_size: int (tamaño de lote, default: 100)

    Input:
        previous_output: List[Dict] o DataFrame con datos a insertar

    Output:
        Dict con success, rows_affected, mode
    """
    from client_app.app.services.database_connection_service import database_connection_service

    # 1. Validar configuración
    connection_id = task.config.get('connection_id')
    table_name = task.config.get('table_name')

    if not connection_id:
        raise ValueError("connection_id is required for SQL_INSERT")
    if not table_name:
        raise ValueError("table_name is required for SQL_INSERT")

    # 2. Resolver datos de entrada
    data = None
    prev = context.get('previous_output')

    if isinstance(prev, pd.DataFrame):
        data = prev.to_dict('records')
    elif isinstance(prev, list):
        data = prev
    elif isinstance(prev, dict) and 'rows' in prev:
        data = prev['rows']

    if not data:
        raise ValueError("No data found to insert")

    # 3. Aplicar column_mapping si existe
    column_mapping = task.config.get('column_mapping', {})
    if column_mapping:
        mapped_data = []
        for row in data:
            mapped_row = {}
            for col, expr in column_mapping.items():
                if expr.startswith('{{') and expr.endswith('}}'):
                    # Es una variable del contexto
                    var_name = expr[2:-2].strip()
                    if var_name in row:
                        mapped_row[col] = row[var_name]
                    else:
                        mapped_row[col] = context.get(var_name)
                else:
                    # Es un valor literal o nombre de columna del row
                    mapped_row[col] = row.get(expr, expr)
            mapped_data.append(mapped_row)
        data = mapped_data

    # 4. Ejecutar inserción
    mode = task.config.get('mode', 'insert')
    batch_size = task.config.get('batch_size', 100)
    primary_key = task.config.get('primary_key')

    rows_affected = await database_connection_service.bulk_insert(
        connection_id=connection_id,
        table_name=table_name,
        data=data,
        mode=mode,
        primary_key=primary_key,
        batch_size=batch_size
    )

    return {
        'success': True,
        'rows_affected': rows_affected,
        'mode': mode,
        'table': table_name
    }



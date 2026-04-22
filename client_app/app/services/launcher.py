from typing import Optional, Dict, Any
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.database.models import LocalAutomation
from automatia_shared.enums import AutomationType
from datetime import datetime

class LauncherService:
    """
    Servicio encargado de disparar y gestionar la ejecución de automatizaciones sincronizadas.
    Actúa como despachador central para diferentes tipos de tareas (scripts, RPA, flujos).
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def launch(self, automation_id: str) -> Dict[str, Any]:
        """
        Inicia la ejecución de una automatización por su ID.
        Identifica el tipo de tarea y delega la ejecución al motor correspondiente.

        Args:
            automation_id: Identificador único de la automatización local.

        Returns:
            Diccionario con el resumen del resultado de la ejecución.
        """
        item = await self.session.get(LocalAutomation, automation_id)
        if not item:
            return {"success": False, "error": "Automation not found"}

        # Prepare result structure
        result = {
            "automation_id": item.id,
            "name": item.name,
            "type": item.type,
            "success": True,
            "timestamp": datetime.utcnow().isoformat()
        }

        if item.type == AutomationType.CUSTOM_SCRIPT:
            from client_app.app.services.sandbox_service import SandboxExecutionService
            from automatia_shared.core.execution_manager import ExecutionPathManager
            
            sandbox = SandboxExecutionService(ExecutionPathManager())
            # Use code_content from synced automation
            exec_result = await sandbox.execute_script(item.code_content, {})
            
            result["success"] = exec_result.get("success", False)
            result["message"] = exec_result.get("output", "") or exec_result.get("error", "")
            
        elif item.type == AutomationType.WORKFLOW:
            # For workflows, code_content is usually the JSON definition
            from client_app.app.services.workflow_execution_service import workflow_execution_service
            # The workflow engine might need the ID or the content
            exec_result = await workflow_execution_service.execute_workflow(item.id)
            
            result["success"] = exec_result.get("success", False)
            result["message"] = f"Workflow executed. Status: {exec_result.get('status')}"
            
        elif item.type == AutomationType.RPA_WEB:
            # RPA integration placeholder (requires browser context)
            result["message"] = "RPA execution engine integration pending."
        else:
            result["message"] = f"Generic execution for {item.type} not implemented."

        return result

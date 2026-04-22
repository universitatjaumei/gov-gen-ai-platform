import traceback
from typing import Dict, Any
from automatia_shared.dtos import TaskSpec
from client_app.app.modules.runtime.workflow_engine import WorkflowEngine
from client_app.app.database.db import client_engine
from sqlmodel.ext.asyncio.session import AsyncSession

class StepTesterService:
    async def run_step(self, step: TaskSpec, test_input: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta un paso individual con input de prueba.
        
        Args:
            step: La especificación del paso a probar.
            test_input: Diccionario con datos de entrada simulados (ej: {'previous_output': ...}).
            
        Returns:
            Dict con keys 'success' (bool), 'output' (Any) o 'error' (str).
        """
        try:
            async with AsyncSession(client_engine) as session:
                engine = WorkflowEngine(session)
                
                # Contexto de prueba. 
                # Combinamos test_input con flags para indicar que es modo prueba.
                context = {'test_mode': True, **test_input}
                
                # Ejecutar la tarea usando el método protegido del motor
                output = await engine._execute_task(step, context)
                
                return {
                    'success': True,
                    'output': output,
                    'context_updated': context
                }
        
        except Exception as e:
            # Capturar traceback para debugging
            tb = traceback.format_exc()
            return {
                'success': False,
                'error': str(e),
                'traceback': tb
            }

step_tester_service = StepTesterService()

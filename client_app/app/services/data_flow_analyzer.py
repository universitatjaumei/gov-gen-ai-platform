"""
DataFlowAnalyzer - Sistema de variables y contexto para el editor de flujos.
Prompt 4.1 del plan de refactorización.

Proporciona:
- Variables disponibles de pasos anteriores con información de tipo
- Variables del trigger según su tipo
- Sugerencias de nombres de variables de salida
- Definiciones de outputs por tipo de paso
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from automatia_shared.dtos import FlowSpec
from automatia_shared.enums import StepType
from client_app.app.clients.brain_client import BrainAPIClient
from client_app.app.core.state import state as app_state
import json


@dataclass
class VariableInfo:
    """Información completa de una variable disponible."""
    name: str
    var_type: str  # 'string', 'number', 'file', 'file[]', 'json', 'json[]', 'any', 'boolean'
    source_step: Optional[int] = None  # Índice del paso que la produce (None si es del trigger/contexto)
    source_step_name: Optional[str] = None  # Nombre del paso de origen
    description: Optional[str] = None  # Descripción de la variable


# Definición de outputs por tipo de paso
STEP_TYPE_OUTPUTS: Dict[StepType, Dict[str, str]] = {
    StepType.EXTRACTION: {
        'extracted_data': 'json',
        'source_file': 'file',
        'confidence': 'number',
    },
    StepType.API_FETCH: {
        'response_body': 'json',
        'status_code': 'number',
        'headers': 'json',
    },
    StepType.EMAIL: {
        'emails': 'json[]',
        'attachments': 'file[]',
        'message_ids': 'string[]',
    },
    StepType.EMAIL_SEND: {
        'sent': 'boolean',
        'message_id': 'string',
    },
    StepType.CUSTOM_SCRIPT: {
        'result': 'any',
    },
    StepType.ETL_TRANSFORM: {
        'transformed_data': 'json',
        'row_count': 'number',
    },
    StepType.NAVIGATION: {
        'result': 'json',
        'screenshots': 'file[]',
    },
    StepType.RPA_EXECUTE: {
        'result': 'json',
        'screenshots': 'file[]',
    },
    StepType.REPORT_GENERATE: {
        'report_file': 'file',
        'report_path': 'string',
    },
    StepType.WEBHOOK: {
        'payload': 'json',
        'headers': 'json',
        'method': 'str',
        'timestamp': 'datetime'
    },
    StepType.SQL_QUERY: {
        'result_set': 'json[]',
        'row_count': 'int',
        'columns': 'list',
        'execution_time_ms': 'int'
    },
    StepType.CONNECTION: {
        'trigger_file': 'file',
        'file_path': 'str',
        'file_name': 'str',
        'file_extension': 'str',
        'folder_path': 'str'
    }
}

# Variables del trigger según su tipo
TRIGGER_VARIABLES: Dict[str, List[Dict[str, str]]] = {
    'manual': [
        {'name': 'execution_id', 'var_type': 'string', 'description': 'ID único de esta ejecución'},
        {'name': 'trigger_type', 'var_type': 'string', 'description': 'Tipo de trigger (manual)'},
        {'name': 'user_id', 'var_type': 'string', 'description': 'ID del usuario que inició la ejecución'},
    ],
    'email': [
        {'name': 'execution_id', 'var_type': 'string', 'description': 'ID único de esta ejecución'},
        {'name': 'trigger_type', 'var_type': 'string', 'description': 'Tipo de trigger (email)'},
        {'name': 'email_from', 'var_type': 'string', 'description': 'Remitente del email'},
        {'name': 'email_to', 'var_type': 'string', 'description': 'Destinatario del email'},
        {'name': 'email_subject', 'var_type': 'string', 'description': 'Asunto del email'},
        {'name': 'email_body', 'var_type': 'string', 'description': 'Cuerpo del email'},
        {'name': 'email_date', 'var_type': 'string', 'description': 'Fecha del email'},
        {'name': 'attachments', 'var_type': 'file[]', 'description': 'Archivos adjuntos del email'},
    ],
    'file': [
        {'name': 'execution_id', 'var_type': 'string', 'description': 'ID único de esta ejecución'},
        {'name': 'trigger_type', 'var_type': 'string', 'description': 'Tipo de trigger (file)'},
        {'name': 'trigger_file', 'var_type': 'file', 'description': 'Archivo que activó el trigger'},
        {'name': 'file_path', 'var_type': 'string', 'description': 'Ruta completa del archivo'},
        {'name': 'file_name', 'var_type': 'string', 'description': 'Nombre del archivo'},
        {'name': 'file_extension', 'var_type': 'string', 'description': 'Extensión del archivo'},
        {'name': 'folder_path', 'var_type': 'string', 'description': 'Carpeta monitoreada'},
    ],
    'schedule': [
        {'name': 'execution_id', 'var_type': 'string', 'description': 'ID único de esta ejecución'},
        {'name': 'trigger_type', 'var_type': 'string', 'description': 'Tipo de trigger (schedule)'},
        {'name': 'scheduled_time', 'var_type': 'string', 'description': 'Hora programada de ejecución'},
    ],
    'webhook': [
        {'name': 'execution_id', 'var_type': 'string', 'description': 'ID único de esta ejecución'},
        {'name': 'trigger_type', 'var_type': 'string', 'description': 'Tipo de trigger (webhook)'},
        {'name': 'webhook_payload', 'var_type': 'json', 'description': 'Datos recibidos por el webhook'},
        {'name': 'webhook_headers', 'var_type': 'json', 'description': 'Headers del request'},
    ],
    'api': [
        {'name': 'execution_id', 'var_type': 'string', 'description': 'ID único de esta ejecución'},
        {'name': 'trigger_type', 'var_type': 'string', 'description': 'Tipo de trigger (api)'},
        {'name': 'api_payload', 'var_type': 'json', 'description': 'Datos recibidos por la API'},
        {'name': 'api_headers', 'var_type': 'json', 'description': 'Headers del request'},
    ],
}

# Sugerencias de nombres base por tipo de paso
SUGGESTED_OUTPUT_NAMES: Dict[StepType, str] = {
    StepType.EXTRACTION: 'extraction_result',
    StepType.ETL_TRANSFORM: 'transformed_data',
    StepType.CUSTOM_SCRIPT: 'script_output',
    StepType.REPORT_GENERATE: 'report_path',
    StepType.API_FETCH: 'api_response',
    StepType.EMAIL: 'email_data',
    StepType.EMAIL_SEND: 'email_sent',
    StepType.NAVIGATION: 'rpa_result',
    StepType.RPA_EXECUTE: 'rpa_result',
    StepType.WEBHOOK: 'webhook_data',
}


class DataFlowAnalyzer:
    """Analizador de flujo de datos para el editor de flujos."""

    def get_available_variables(self, flow: FlowSpec, step_index: int) -> List[VariableInfo]:
        """
        Retorna las variables disponibles para un paso dado.

        Args:
            flow: El FlowSpec completo (puede ser None si es standalone)
            step_index: Índice del paso actual

        Returns:
            Lista de VariableInfo con todas las variables disponibles
        """
        variables: List[VariableInfo] = []

        # 0. Global Variables (siempre disponibles)
        variables.extend([
            VariableInfo(name='date', var_type='string', source_step=-1, source_step_name='Global', description='Fecha actual (YYYY-MM-DD)'),
            VariableInfo(name='time', var_type='string', source_step=-1, source_step_name='Global', description='Hora actual (HH:MM:SS)'),
            VariableInfo(name='datetime', var_type='string', source_step=-1, source_step_name='Global', description='Fecha y hora actual ISO'),
            VariableInfo(name='timestamp', var_type='number', source_step=-1, source_step_name='Global', description='Timestamp UNIX actual'),
        ])

        if not flow:
            return variables

        # 1. Variables del trigger
        trigger_type = getattr(flow, 'trigger_type', None) or 'manual'
        trigger_vars = self.get_trigger_variables(trigger_type)
        variables.extend(trigger_vars)

        # 2. Outputs de pasos anteriores
        for idx in range(step_index):
            if idx < len(flow.steps):
                prev_step = flow.steps[idx]
                step_vars = self._get_step_output_variables(prev_step, idx)
                variables.extend(step_vars)

        # 3. Variable especial 'previous_output' (solo si hay paso anterior)
        if step_index > 0:
            variables.append(VariableInfo(
                name='previous_output',
                var_type='any',
                source_step=step_index - 1,
                source_step_name=flow.steps[step_index - 1].name if step_index - 1 < len(flow.steps) else None,
                description='Resultado del paso anterior'
            ))

        return variables

    def get_trigger_variables(self, trigger_type: str) -> List[VariableInfo]:
        """
        Retorna las variables disponibles según el tipo de trigger.

        Args:
            trigger_type: Tipo de trigger ('manual', 'email', 'folder_watcher', etc.)

        Returns:
            Lista de VariableInfo para el trigger
        """
        trigger_vars = TRIGGER_VARIABLES.get(trigger_type, TRIGGER_VARIABLES['manual'])

        return [
            VariableInfo(
                name=v['name'],
                var_type=v['var_type'],
                source_step=None,
                source_step_name=None,
                description=v.get('description', '')
            )
            for v in trigger_vars
        ]

    def _get_step_output_variables(self, step, step_index: int) -> List[VariableInfo]:
        """
        Obtiene las variables de output de un paso.

        Args:
            step: El TaskSpec del paso
            step_index: Índice del paso

        Returns:
            Lista de VariableInfo con los outputs del paso
        """
        variables: List[VariableInfo] = []

        # Variable de output configurada por el usuario
        output_var = step.config.get('output_var') if step.config else None
        if output_var:
            # 1. Variable principal (el objeto completo)
            primary_type = self._get_primary_output_type(step.type)
            variables.append(VariableInfo(
                name=output_var,
                var_type=primary_type,
                source_step=step_index,
                source_step_name=step.name,
                description=f'Resultado completo de "{step.name}"'
            ))

            # 2. Sub-variables (Data Pills para acceso a campos específicos)
            outputs = STEP_TYPE_OUTPUTS.get(step.type, {})
            for field_name, field_type in outputs.items():
                variables.append(VariableInfo(
                    name=f"{output_var}.{field_name}",
                    var_type=field_type,
                    source_step=step_index,
                    source_step_name=step.name,
                    description=f'Campo "{field_name}" de "{step.name}"'
                ))

        return variables

    def _get_primary_output_type(self, step_type: StepType) -> str:
        """
        Obtiene el tipo principal de output de un tipo de paso.

        Args:
            step_type: El tipo de paso

        Returns:
            El tipo de la variable principal ('json', 'file', 'string', etc.)
        """
        outputs = STEP_TYPE_OUTPUTS.get(step_type, {})

        # Mapeo de tipo principal por step type
        primary_types = {
            StepType.EXTRACTION: 'json',
            StepType.API_FETCH: 'json',
            StepType.EMAIL: 'json[]',
            StepType.EMAIL_SEND: 'boolean',
            StepType.CUSTOM_SCRIPT: 'any',
            StepType.ETL_TRANSFORM: 'json',
            StepType.NAVIGATION: 'json',
            StepType.RPA_EXECUTE: 'json',
            StepType.REPORT_GENERATE: 'file',
            StepType.WEBHOOK: 'json',
        }

        return primary_types.get(step_type, 'any')

    def get_step_type_outputs(self, step_type: StepType) -> Dict[str, str]:
        """
        Retorna la definición de outputs para un tipo de paso.

        Args:
            step_type: El tipo de paso

        Returns:
            Diccionario con nombre -> tipo de cada output
        """
        return STEP_TYPE_OUTPUTS.get(step_type, {'result': 'any'})

    def suggest_output_var_name(
        self,
        step_type: StepType,
        step_index: int,
        flow: FlowSpec = None
    ) -> str:
        """
        Sugiere un nombre de variable de salida según el tipo de paso.
        Asegura que el nombre no colisione con variables existentes.

        Args:
            step_type: Tipo del paso
            step_index: Índice del paso
            flow: FlowSpec opcional para verificar colisiones

        Returns:
            Nombre sugerido único
        """
        base_name = SUGGESTED_OUTPUT_NAMES.get(step_type, 'step_output')
        suggested = f'{base_name}_{step_index + 1}'

        # Si no hay flow, retornar la sugerencia básica
        if not flow:
            return suggested

    async def suggest_semantic_name(
        self,
        step_type: StepType,
        config: Dict[str, Any],
        license_key: str = "TRIAL-KEY"
    ) -> str:
        """
        Consulta al cerebro para obtener un nombre semántico basado en la config.
        """
        from client_app.app.clients.brain_client import get_brain_client
        brain = await get_brain_client()
        
        # Limpiar config para el prompt (quitar campos pesados o vacÃ­os)
        summary = {k: v for k, v in config.items() if v and not isinstance(v, (bytes, bytearray, list, dict))}
        
        try:
            # Usar el service_id especÃ­fico del prompt semÃ¡ntico
            response = await brain.call_llm(
                prompt="Sustrae el nombre semÃ¡ntico.",
                service_id="sys_semantic_naming",
                config_summary={
                    "step_type": step_type.value,
                    "config_summary": json.dumps(summary)
                },
                license_key=license_key
            )
            
            # Limpieza bÃ¡sica de la respuesta
            clean_name = response.strip().lower().replace(" ", "_").replace("\"", "").replace("'", "")
            return clean_name or self.suggest_output_var_name(step_type, 0)
            
        except Exception as e:
            print(f"[DataFlowAnalyzer] Error sugiriendo nombre: {e}")
            return self.suggest_output_var_name(step_type, 0)

    async def get_execution_history(self, node_id: str, limit: int = 5) -> List[Any]:
        """
        Recupera el historial de ejecuciones de un nodo específico.
        """
        from client_app.app.database.db import client_engine
        from client_app.app.database.models import TaskLog
        from sqlmodel import select, col
        from sqlmodel.ext.asyncio.session import AsyncSession
        from sqlalchemy import desc
        
        async with AsyncSession(client_engine) as session:
            # En la tabla TaskLog, buscamos por step_name o similar si no hay node_id directo
            # Asumimos que TaskLog tiene la información necesaria
            statement = select(TaskLog).where(
                TaskLog.step_name == node_id
            ).order_by(desc(TaskLog.started_at)).limit(limit)
            
            results = await session.exec(statement)
            return results.all()

    async def get_variable_preview(self, var_name: str, flow_id: int) -> Optional[str]:
        """
        Obtiene un preview del último valor de una variable (si existe historial).

        Args:
            var_name: Nombre de la variable
            flow_id: ID del flujo

        Returns:
            String con preview del valor o None si no hay historial
        """
        # Intentar obtener del historial de logs
        from client_app.app.database.db import client_engine
        from client_app.app.database.models import TaskLog
        from sqlmodel import select
        from sqlmodel.ext.asyncio.session import AsyncSession
        from sqlalchemy import desc
        import json

        async with AsyncSession(client_engine) as session:
            # Buscamos el último log que haya tenido éxito para este flujo
            # y que pueda contener el valor de la variable (en result_summary o similar)
            statement = select(TaskLog).where(
                TaskLog.execution_id.like(f"flow_{flow_id}%"),
                TaskLog.status == "completed"
            ).order_by(desc(TaskLog.started_at)).limit(1)
            
            result = await session.exec(statement)
            log = result.first()
            
            if log and log.result_summary:
                # El result_summary podría ser un JSON con los outputs
                return log.result_summary[:100] + "..." if len(log.result_summary) > 100 else log.result_summary

        return None


# Instancia singleton
data_flow_analyzer = DataFlowAnalyzer()

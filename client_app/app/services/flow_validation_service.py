from typing import Dict, List, Literal, Optional, Any
from dataclasses import dataclass
import json
from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.enums import StepType


@dataclass
class StepValidationError:
    """Representa un error de validación en un campo específico de un paso."""
    step_index: int
    field_name: str
    message: str
    severity: Literal["error", "warning"] = "error"


class FlowValidationService:
    """Servicio para validar reglas de negocio en flujos antes de guardar"""
    
    def validate_flow(self, flow: FlowSpec) -> List[str]:
        """
        Valida el flujo completo. Retorna lista de errores.
        """
        errors = []
        
        if not flow.name or not flow.name.strip():
            errors.append("El flujo debe tener un nombre.")
            
        if not flow.steps:
            errors.append("El flujo debe tener al menos un paso.")
            
        for i, step in enumerate(flow.steps):
            step_error = self.validate_step(step)
            if step_error:
                errors.append(f"Paso {i+1} ({step.name}): {step_error}")
                
        return errors

    def validate_step(self, step: TaskSpec) -> Optional[str]:
        """
        Valida la configuración de un paso individual.
        Retorna mensaje de error o None si es válido.
        """
        config = step.config or {}
        
        if step.type == StepType.EXTRACTION:
            if not config.get('config_id'):
                return "requiere seleccionar una configuración de extracción."
                
        elif step.type == StepType.NAVIGATION or step.type == StepType.RPA_EXECUTE:
            if not config.get('playbook_id'):
                return "requiere seleccionar un playbook RPA."
                
        elif step.type == StepType.CUSTOM_SCRIPT:
            if not config.get('script_id'):
                return "requiere seleccionar un script."
        
        elif step.type == StepType.ETL_TRANSFORM:
            if not config.get('script_id'):
                return "requiere seleccionar un script ETL."
                
        elif step.type == StepType.REPORT_GENERATE:
            if not config.get('template_id'):
                return "requiere seleccionar una plantilla de informe."
                
        elif step.type == StepType.EMAIL:
            mode = config.get('mode', 'input')
            if mode == 'input' and not config.get('credential_id'):
                 # Note: Currently EMAIL Step might imply IMAP defaults or specific creds. 
                 # If the UI adds credential selector for input, this is valid.
                 # If prompts didn't specify, we only enforce if 'credential_id' is expected.
                 # Based on FE-04 prompt: "EMAIL (IMAP): Requiere credential_id cuando mode='input'"
                 return "requiere seleccionar credenciales IMAP."
                 
        elif step.type == StepType.EMAIL_SEND:
            if not config.get('to'):
                return "requiere destinatarios."
            if not config.get('credential_id'):
                return "requiere seleccionar credencial SMTP."
                
        elif step.type == StepType.API_FETCH:
            # Requires either URL (manual) or endpoint_id (pre-configured)
            if not config.get('url') and not config.get('endpoint_id'):
                return "requiere una URL o endpoint."
                
        return None

    def validate_step_detailed(self, step: TaskSpec, step_index: int = 0) -> List[StepValidationError]:
        """
        Valida un paso individual y retorna lista de errores detallados.
        Cada error indica el campo específico que tiene problemas.

        Args:
            step: El TaskSpec a validar
            step_index: Índice del paso en el flujo (para el error)

        Returns:
            Lista de StepValidationError (vacía si el paso es válido)
        """
        errors: List[StepValidationError] = []
        config = step.config or {}

        if step.type == StepType.API_FETCH:
            if not config.get('url') and not config.get('endpoint_id'):
                errors.append(StepValidationError(
                    step_index=step_index,
                    field_name="url",
                    message="La URL es obligatoria",
                    severity="error"
                ))

        elif step.type == StepType.EMAIL_SEND:
            if not config.get('to'):
                errors.append(StepValidationError(
                    step_index=step_index,
                    field_name="to",
                    message="El destinatario es obligatorio",
                    severity="error"
                ))
            if not config.get('subject'):
                errors.append(StepValidationError(
                    step_index=step_index,
                    field_name="subject",
                    message="El asunto es obligatorio",
                    severity="error"
                ))
            if not config.get('credential_id'):
                errors.append(StepValidationError(
                    step_index=step_index,
                    field_name="credential_id",
                    message="Debe seleccionar una cuenta SMTP",
                    severity="error"
                ))

        elif step.type == StepType.EXTRACTION:
            if not config.get('config_id'):
                errors.append(StepValidationError(
                    step_index=step_index,
                    field_name="config_id",
                    message="Debe seleccionar una configuración de extracción",
                    severity="error"
                ))

        elif step.type == StepType.CUSTOM_SCRIPT:
            if not config.get('script_id'):
                errors.append(StepValidationError(
                    step_index=step_index,
                    field_name="script_id",
                    message="Debe seleccionar un script",
                    severity="error"
                ))

        elif step.type == StepType.NAVIGATION or step.type == StepType.RPA_EXECUTE:
            if not config.get('playbook_id'):
                errors.append(StepValidationError(
                    step_index=step_index,
                    field_name="playbook_id",
                    message="Debe seleccionar un playbook RPA",
                    severity="error"
                ))

        elif step.type == StepType.ETL_TRANSFORM:
            if not config.get('script_id'):
                errors.append(StepValidationError(
                    step_index=step_index,
                    field_name="script_id",
                    message="Debe seleccionar un script ETL",
                    severity="error"
                ))

        elif step.type == StepType.REPORT_GENERATE:
            if not config.get('template_id'):
                errors.append(StepValidationError(
                    step_index=step_index,
                    field_name="template_id",
                    message="Debe seleccionar una plantilla de informe",
                    severity="error"
                ))

        elif step.type == StepType.EMAIL:
            mode = config.get('mode', 'input')
            if mode == 'input' and not config.get('credential_id'):
                errors.append(StepValidationError(
                    step_index=step_index,
                    field_name="credential_id",
                    message="Debe seleccionar credenciales IMAP",
                    severity="error"
                ))

        return errors

    def validate_all_steps(self, flow: FlowSpec) -> Dict[int, List[StepValidationError]]:
        """
        Valida todos los pasos de un flujo y retorna un resumen de errores.

        Args:
            flow: El FlowSpec a validar

        Returns:
            Diccionario donde las claves son índices de pasos y los valores
            son listas de errores para ese paso. Solo incluye pasos con errores.
        """
        errors_by_step: Dict[int, List[StepValidationError]] = {}

        if not flow.steps:
            return errors_by_step

        for index, step in enumerate(flow.steps):
            step_errors = self.validate_step_detailed(step, step_index=index)
            if step_errors:
                errors_by_step[index] = step_errors

        return errors_by_step

    # =========================================================================
    # ATOM EXISTENCE VALIDATION (NEW)
    # =========================================================================

    async def validate_flow_atoms(self, flow_id: int) -> Dict[str, Any]:
        """
        Validates that all atoms referenced in a flow exist.

        Args:
            flow_id: ID of the flow to validate

        Returns:
            {
                'valid': bool,
                'missing_atoms': [...],
                'warnings': [],
                'error': str (only if flow not found)
            }
        """
        from sqlmodel.ext.asyncio.session import AsyncSession
        from client_app.app.database.db import client_engine
        from client_app.app.database.models import FlowRegistry, ScriptLibrary
        from client_app.app.services.script_library_service import script_library_service

        async with AsyncSession(client_engine) as session:
            flow = await session.get(FlowRegistry, flow_id)
            if not flow:
                return {'valid': False, 'error': 'Flow not found', 'missing_atoms': [], 'warnings': []}

            steps = json.loads(flow.steps) if flow.steps else []
            missing_atoms = []
            warnings = []

            for step in steps:
                step_config = step.get('config', {})
                script_id = step_config.get('script_id')
                automation_id = step_config.get('automation_id')
                playbook_id = step_config.get('playbook_id')
                template_id = step_config.get('template_id')

                # Check script_id references
                if script_id:
                    atom = await script_library_service.get_script(int(script_id))
                    if not atom:
                        missing_atoms.append({
                            'step_name': step.get('name', 'Unknown'),
                            'step_id': step.get('id'),
                            'script_id': script_id,
                            'type': step.get('type', 'unknown'),
                            'reference_type': 'script_id'
                        })
                    elif hasattr(atom, 'status') and atom.status == 'draft':
                        warnings.append({
                            'step_name': step.get('name'),
                            'step_id': step.get('id'),
                            'message': f"Atom '{atom.name}' is in draft status",
                            'severity': 'warning'
                        })

                # Check automation_id references (UserExtractionConfig)
                if automation_id:
                    from client_app.app.database.models import UserExtractionConfig
                    config = await session.get(UserExtractionConfig, int(automation_id))
                    if not config:
                        missing_atoms.append({
                            'step_name': step.get('name', 'Unknown'),
                            'step_id': step.get('id'),
                            'automation_id': automation_id,
                            'type': step.get('type', 'extraction'),
                            'reference_type': 'automation_id'
                        })

                # Check playbook_id references (RpaPlaybook)
                if playbook_id:
                    from client_app.app.database.models import RpaPlaybook
                    playbook = await session.get(RpaPlaybook, int(playbook_id))
                    if not playbook:
                        missing_atoms.append({
                            'step_name': step.get('name', 'Unknown'),
                            'step_id': step.get('id'),
                            'playbook_id': playbook_id,
                            'type': 'rpa_execute',
                            'reference_type': 'playbook_id'
                        })

                # Check template_id references (ReportTemplate)
                if template_id:
                    from client_app.app.database.models import ReportTemplate
                    template = await session.get(ReportTemplate, int(template_id))
                    if not template:
                        missing_atoms.append({
                            'step_name': step.get('name', 'Unknown'),
                            'step_id': step.get('id'),
                            'template_id': template_id,
                            'type': 'report_generate',
                            'reference_type': 'template_id'
                        })

            return {
                'valid': len(missing_atoms) == 0,
                'missing_atoms': missing_atoms,
                'warnings': warnings,
                'total_steps': len(steps)
            }

    async def get_atom_usage_report(self, script_id: int) -> Dict[str, Any]:
        """
        Generates usage report of an atom in flows.
        Useful before deleting an atom.

        Args:
            script_id: ID of the script/atom to check

        Returns:
            {
                'used_in_flows': [...],
                'total_usages': int,
                'can_delete': bool
            }
        """
        from sqlmodel import select
        from sqlmodel.ext.asyncio.session import AsyncSession
        from client_app.app.database.db import client_engine
        from client_app.app.database.models import FlowRegistry

        usages = []

        async with AsyncSession(client_engine) as session:
            stmt = select(FlowRegistry)
            result = await session.exec(stmt)
            flows = result.all()

            for flow in flows:
                steps = json.loads(flow.steps) if flow.steps else []

                for step in steps:
                    step_config = step.get('config', {})
                    if step_config.get('script_id') == script_id:
                        usages.append({
                            'flow_id': flow.id,
                            'flow_name': flow.name,
                            'step_name': step.get('name', 'Unknown'),
                            'step_type': step.get('type', 'unknown')
                        })

        return {
            'used_in_flows': usages,
            'total_usages': len(usages),
            'can_delete': len(usages) == 0
        }

    async def validate_flow_before_execution(self, flow_id: int) -> Dict[str, Any]:
        """
        Complete validation before executing a flow.
        Combines atom validation with other checks.

        Args:
            flow_id: ID of the flow to validate

        Returns:
            {
                'can_execute': bool,
                'atoms_valid': bool,
                'missing_atoms': [...],
                'warnings': [...],
                'errors': [...]
            }
        """
        atom_validation = await self.validate_flow_atoms(flow_id)

        errors = []
        if atom_validation.get('error'):
            errors.append(atom_validation['error'])

        for missing in atom_validation.get('missing_atoms', []):
            ref_id = missing.get('script_id') or missing.get('automation_id') or missing.get('playbook_id') or missing.get('template_id')
            errors.append(
                f"Missing {missing['reference_type']}: {ref_id} in step '{missing['step_name']}'"
            )

        return {
            'can_execute': len(errors) == 0,
            'atoms_valid': atom_validation.get('valid', False),
            'missing_atoms': atom_validation.get('missing_atoms', []),
            'warnings': atom_validation.get('warnings', []),
            'errors': errors,
            'total_steps': atom_validation.get('total_steps', 0)
        }

    async def get_flow_dependencies(self, flow_id: int) -> Dict[str, Any]:
        """
        Gets all external dependencies of a flow.

        Returns:
            {
                'scripts': [...],
                'playbooks': [...],
                'templates': [...],
                'credentials': [...],
                'total_dependencies': int
            }
        """
        from sqlmodel import select
        from sqlmodel.ext.asyncio.session import AsyncSession
        from client_app.app.database.db import client_engine
        from client_app.app.database.models import FlowRegistry, ScriptLibrary

        async with AsyncSession(client_engine) as session:
            flow = await session.get(FlowRegistry, flow_id)
            if not flow:
                return {'error': 'Flow not found'}

            steps = json.loads(flow.steps) if flow.steps else []

            script_ids = set()
            playbook_ids = set()
            template_ids = set()
            credential_ids = set()

            for step in steps:
                config = step.get('config', {})
                if config.get('script_id'):
                    script_ids.add(int(config['script_id']))
                if config.get('playbook_id'):
                    playbook_ids.add(int(config['playbook_id']))
                if config.get('template_id'):
                    template_ids.add(int(config['template_id']))
                if config.get('credential_id'):
                    credential_ids.add(int(config['credential_id']))
                if config.get('connection_id'):
                    credential_ids.add(int(config['connection_id']))

            # Fetch details
            scripts = []
            for sid in script_ids:
                script = await session.get(ScriptLibrary, sid)
                if script:
                    scripts.append({
                        'id': script.id,
                        'name': script.name,
                        'module': script.source_module,
                        'status': script.status
                    })

            playbooks = []
            for pid in playbook_ids:
                from client_app.app.database.models import RpaPlaybook
                pb = await session.get(RpaPlaybook, pid)
                if pb:
                    playbooks.append({'id': pb.id, 'name': pb.name})

            templates = []
            for tid in template_ids:
                from client_app.app.database.models import ReportTemplate
                tpl = await session.get(ReportTemplate, tid)
                if tpl:
                    templates.append({'id': tpl.id, 'name': tpl.name})

            credentials = []
            for cid in credential_ids:
                from client_app.app.database.models import EmailCredential
                cred = await session.get(EmailCredential, cid)
                if cred:
                    credentials.append({
                        'id': cred.id,
                        'name': cred.account_name,
                        'type': cred.service_type
                    })

            return {
                'scripts': scripts,
                'playbooks': playbooks,
                'templates': templates,
                'credentials': credentials,
                'total_dependencies': len(scripts) + len(playbooks) + len(templates) + len(credentials)
            }


flow_validation_service = FlowValidationService()

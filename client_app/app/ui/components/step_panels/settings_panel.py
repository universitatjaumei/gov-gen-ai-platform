"""
Settings Panel - Renders the configuration form for a step.
Extracted from StepConfigurator for reusability in Unified Creation Wizard.
"""
from typing import Callable, Optional
from nicegui import ui
from automatia_shared.dtos import TaskSpec, FlowSpec
from automatia_shared.enums import StepType
from client_app.app.ui.components.step_forms.extraction_form import render_extraction_form
from client_app.app.ui.components.step_forms.api_fetch_form import render_api_fetch_form
from client_app.app.ui.components.step_forms.email_send_form import render_email_send_form
from client_app.app.ui.components.step_forms.generic_form import render_generic_form
from client_app.app.services.resource_listing_service import resource_listing_service


async def render_settings_panel(
    step: TaskSpec,
    flow: Optional[FlowSpec] = None,
    on_change: Optional[Callable] = None
):
    """
    Renderiza el panel de configuración del paso.
    
    Args:
        step: El TaskSpec del paso a configurar
        flow: El flujo completo (opcional, para contexto)
        on_change: Callback opcional cuando cambia la configuración
    """
    ui.label('Ajustes del Paso').classes('text-lg font-bold mb-4')

    if step.type == StepType.EXTRACTION:
        await render_extraction_form(step, flow=flow, on_change=on_change)
        
    elif step.type == StepType.API_FETCH:
        render_api_fetch_form(step, on_change=on_change)
        
    elif step.type == StepType.EMAIL_SEND:
        await render_email_send_form(step, flow=flow, on_change=on_change)
        
    elif step.type == StepType.REPORT:
        from client_app.app.ui.components.step_forms.report_generate_form import ReportGenerateForm
        from client_app.app.ui.pill_logic import PillProvider
        
        # Obtener variables disponibles
        available_variables = {}
        if flow and step in flow.steps:
            step_index = flow.steps.index(step)
            provider = PillProvider(flow)
            pills = provider.get_available_pills(step_index)
            
            for pill in pills:
                group = pill.source_step_name or "Global"
                if group not in available_variables:
                    available_variables[group] = {}
                if isinstance(available_variables[group], dict):
                    available_variables[group][pill.label] = pill.reference
        
        form = ReportGenerateForm(
            step=step,
            available_variables=available_variables,
            on_config_change=on_change
        )
        await form.render()

    elif step.type in [StepType.NAVIGATION, StepType.RPA_EXECUTE]:
        # Simple Select logic for RPA playbooks
        playbooks = await resource_listing_service.list_rpa_playbooks()
        opts = {p['id']: p['name'] for p in playbooks} if playbooks else {}
        
        def handle_playbook_change(e):
            step.config['playbook_id'] = int(e.value)
            if on_change:
                on_change()
        
        ui.select(
            options=opts, 
            label='RPA Playbook',
            value=step.config.get('playbook_id'),
            on_change=handle_playbook_change
        ).classes('w-full')
        
    else:
        # Fallback Generic
        render_generic_form(step, config_schema=None, on_change=on_change)

"""
Variables Panel - Renders data flow analysis (available inputs and output configuration).
Extracted from StepConfigurator for reusability in Unified Creation Wizard.
"""
from typing import Optional
from nicegui import ui
from automatia_shared.dtos import TaskSpec, FlowSpec
from automatia_shared.enums import StepType
from client_app.app.config.atom_catalog import get_atom_metadata
from automatia_shared.contracts.ui_contract import InputType


def render_variables_panel(step: TaskSpec, flow: FlowSpec):
    """
    Renderiza variables disponibles y configuración de salida.
    
    Args:
        step: El TaskSpec del paso
        flow: El FlowSpec completo para obtener variables previas
    """
    try:
        if step in flow.steps:
            step_index = flow.steps.index(step)
            # Import provider to get pills directly
            from client_app.app.ui.pill_logic import PillProvider
            provider = PillProvider(flow)
            pills = provider.get_available_pills(step_index)
            
            ui.label('Variables Disponibles (Data Pills)').classes('text-lg font-bold mb-4')
            
            # --- FILE DETECTION (Prompt 8) ---
            meta = get_atom_metadata(step.type)
            schema = meta.config_schema or {}
            properties = schema.get('properties', {})
            
            has_file_input = False
            # Check schema
            for prop_name, prop_def in properties.items():
                if prop_def.get('type') in ('file', 'files', InputType.FILE, InputType.FILES):
                    has_file_input = True
                    break
            
            # Hardcoded check for specific steps until contracts are fully implemented
            if step.type in (StepType.EXTRACTION, StepType.ANONYMIZATION):
                has_file_input = True
                
            if has_file_input:
                with ui.card().classes('w-full bg-amber-50 border border-amber-200 p-3 mb-4 shadow-none'):
                    with ui.row().classes('items-center gap-2 mb-1'):
                        ui.icon('cloud_upload', color='amber-8', size='sm')
                        ui.label('Este paso requiere archivos').classes('text-sm font-bold text-amber-900')
                    ui.markdown('Sugerencia: Usa el **Sandbox Central** para subir archivos temporales y probar este paso.').classes('text-xs text-amber-800')

            with ui.column().classes('w-full gap-4'):
                # Available Inputs
                ui.label('Entradas Disponibles').classes('font-bold text-sm text-gray-400 uppercase tracking-wider')
                if pills:
                    with ui.row().classes('flex-wrap gap-2'):
                        for pill in pills:
                            with ui.button(on_click=lambda p=pill: ui.notify(f"Copiado: {p.reference}")).props('rounded outline dense size=sm').classes('px-2 py-1 bg-blue-50 hover:bg-blue-100 border-blue-200'):
                                with ui.row().classes('items-center gap-1'):
                                    ui.icon('database', size='xs', color='blue')
                                    ui.label(pill.label).classes('text-xs font-medium text-slate-700')
                            ui.tooltip(f"Clic para copiar {pill.reference}")
                else:
                    ui.label('No hay datos previos disponibles').classes('text-sm text-gray-500 italic pb-4')
                
                ui.separator()
                
                # Output Config
                ui.label('Configuración de Salida').classes('font-bold text-sm text-gray-400 uppercase tracking-wider')
                from client_app.app.services.data_flow_analyzer import data_flow_analyzer
                suggested_name = data_flow_analyzer.suggest_output_var_name(step.type, step_index)
                current_output = step.config.get('output_var', '')
                
                def update_output_var(e):
                    step.config['output_var'] = e.value
                
                ui.input(
                    'Nombre de la Variable de Salida', 
                    value=current_output,
                    placeholder=suggested_name,
                    on_change=update_output_var
                ).props('dense outlined').classes('w-full text-sm')
                
                ui.label('Esta variable estará disponible para los siguientes pasos del flujo.').classes('text-xs text-gray-500 italic')
    except Exception as e:
        ui.label(f"Data Flow Error: {str(e)}").classes('text-red-400 text-xs')

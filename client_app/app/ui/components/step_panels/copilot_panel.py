"""
Copilot Panel - Renders AI assistant suggestions and contextual help.
Extracted from StepConfigurator for reusability in Unified Creation Wizard.
"""
from nicegui import ui
from automatia_shared.dtos import TaskSpec, FlowSpec


def render_copilot_panel(step: TaskSpec, flow: FlowSpec):
    """
    Renderiza el panel del asistente de IA (Copiloto).
    
    Args:
        step: El TaskSpec del paso
        flow: El FlowSpec completo para contexto
    """
    ui.label('Asistente de IA (Copiloto)').classes('text-lg font-bold mb-4')
    
    # Prompt 4: Display compatibility warnings from LayoutState
    from client_app.app.ui.layout_state import LayoutState
    layout_state = LayoutState()
    
    if layout_state.suggestions:
        with ui.column().classes('w-full gap-2 mb-4'):
            ui.label('Alertas de Compatibilidad').classes('text-xs font-bold text-red-500 uppercase')
            
            for suggestion in layout_state.suggestions:
                severity_color = {
                    'warning': 'orange-500',
                    'error': 'red-500',
                    'info': 'blue-500'
                }.get(suggestion.get('severity', 'info'), 'blue-500')
                
                with ui.card().classes(f'w-full p-3 border-l-4 border-{severity_color} bg-white shadow-sm'):
                    with ui.row().classes('items-center gap-2 mb-1'):
                        icon = 'warning' if suggestion.get('severity') == 'warning' else 'info'
                        ui.icon(icon, color=severity_color.replace('-500', '-8'), size='xs')
                        ui.label(f"{suggestion.get('source_step', '')} → {suggestion.get('target_step', '')}").classes('text-sm font-bold text-slate-800')
                    
                    ui.label(suggestion.get('message', '')).classes('text-xs text-gray-600')
                    
                    # Show bridge prompt if available
                    if suggestion.get('bridge_prompt'):
                        with ui.expansion('Ver Prompt de Puente', icon='code').classes('mt-2'):
                            ui.markdown(f"```\n{suggestion['bridge_prompt']}\n```").classes('text-xs')
            
            ui.separator().classes('my-4')
    
    with ui.column().classes('w-full gap-4'):
        # Search Area or suggestions
        ui.label('¿En qué puedo ayudarte con este paso?').classes('text-sm text-gray-600')
        
        # Suggested Actions (Premium feel)
        with ui.column().classes('w-full gap-2 mt-2'):
            ui.label('Sugerencias Contextuales').classes('text-xs font-bold text-gray-400 uppercase')
            
            with ui.card().classes('w-full p-3 border-l-4 border-blue-500 bg-white shadow-sm hover:shadow-md transition-all cursor-pointer'):
                with ui.row().classes('items-center gap-2 mb-1'):
                    ui.icon('auto_fix_high', color='blue', size='xs')
                    ui.label('Conectar variable de salida').classes('text-sm font-bold text-slate-800')
                ui.label('Puedo ayudarte a vincular el resultado de este paso con la siguiente acción.').classes('text-xs text-gray-600')
                ui.button('Analizar Conexiones', icon='insights').props('flat dense size=sm color=primary').classes('mt-2')

            with ui.card().classes('w-full p-3 border-l-4 border-amber-400 bg-white shadow-sm hover:shadow-md transition-all cursor-pointer'):
                with ui.row().classes('items-center gap-2 mb-1'):
                    ui.icon('help_outline', color='amber-8', size='xs')
                    ui.label('Documentación Rápida').classes('text-sm font-bold text-slate-800')
                ui.label('Explica qué hace este paso en lenguaje natural para tu equipo.').classes('text-xs text-gray-600')
                ui.button('Autogenerar Doc', icon='history_edu').props('flat dense size=sm color=amber-8').classes('mt-2')

        ui.separator().classes('my-4')
        
        # Context-aware chat placeholder
        ui.label('Chat del Copiloto').classes('text-xs font-bold text-gray-400 uppercase')
        with ui.column().classes('w-full bg-slate-50 p-4 rounded-lg border border-dashed border-slate-300 min-h-[100px] items-center justify-center'):
            ui.icon('chat_bubble_outline', size='lg', color='slate-300')
            ui.label('Escribe una consulta técnica sobre esta acción...').classes('text-xs text-slate-400 italic text-center')

        # Simple simulated chat input at bottom
        with ui.row().classes('w-full items-center gap-2 mt-auto pb-4'):
            ui.input(placeholder='Pregunta sobre esta acción...').classes('flex-1').props('outlined dense')
            ui.button(icon='send').props('flat round color=primary')

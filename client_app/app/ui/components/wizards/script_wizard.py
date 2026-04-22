
from nicegui import ui, app
import uuid
from typing import Callable, Optional, Dict, Any
from pathlib import Path
from client_app.app.ui.ui_utils import ui_emit

async def render_script_wizard(
    on_save: Callable[[str], None], 
    context: Optional[str] = None,
    is_flow_context: bool = False
):
    """
    Wizard simplificado para crear Script Personalizado.
    
    Prompt #7: Enhanced with smart redirection and seal feedback.
    
    Args:
        on_save: Callback to execute after save (receives script_id)
        context: Optional context information
        is_flow_context: True if wizard is opened from flow editor drawer
    """
    script_name = ui.input("Nombre del Script").classes('w-full')
    
    if context:
        ui.label(f"Contexto Detectado: {context}").classes('text-xs text-blue-500 mb-2')
    
    prompt_area = ui.textarea(label="Describe qué debe hacer el script").classes('w-full')
    
    # Real AI Generation
    async def generate_with_ai():
        if not prompt_area.value:
            ui.notify("Por favor, describe qué debe hacer el script.", type='warning')
            return

        ui.notify("Generando código con IA...", type='info')
        
        try:
            from client_app.app.services.script_generator_service import script_generator_service
            
            # Use standard generation which enforces JSON structure
            result = await script_generator_service.generate_script(
                user_prompt=prompt_area.value,
                output_type="file"
            )
            
            if result.get("success"):
                code = result.get("code", "")
                if code:
                    code_editor.value = code
                    ui.notify("Código generado exitosamente", type='positive')
                else:
                    ui.notify("La IA no devolvió código válido.", type='warning')
            else:
                ui.notify(f"Error: {result.get('error')}", type='negative')
                
        except Exception as e:
            ui.notify(f"Error invocando IA: {str(e)}", type='negative')

    ui.button("Generar con IA (Beta)", icon='auto_awesome', on_click=generate_with_ai).props('flat color=secondary')

    code_editor = ui.codemirror(value="# Python Code will appear here", language='python').classes('h-48 border')

    async def save_and_redirect():
        """
        Prompt #7: Smart save with seal feedback and context-aware redirection.
        """
        if not script_name.value:
            ui.notify('Nombre requerido', type='warning')
            return
        
        # Show sealing spinner
        with ui.dialog() as seal_dialog, ui.card().classes('p-6 min-w-[400px]'):
            with ui.column().classes('w-full items-center gap-4'):
                ui.spinner(size='lg', color='blue')
                ui.label('Generando documentación técnica...').classes('text-lg font-semibold text-slate-700')
                ui.label('Aplicando Sello Atómico').classes('text-sm text-slate-500')
        
        seal_dialog.open()
        
        try:
            # Mock creation logic (in real implementation, call AssetFinishingService)
            new_id = str(uuid.uuid4())
            
            # Simulate seal process
            await ui.run_javascript('new Promise(resolve => setTimeout(resolve, 1500))', timeout=2.0)
            
            # Mock seal metadata (in real implementation, get from AssetFinishingService)
            seal_metadata = {
                'script_id': new_id,
                'script_name': script_name.value,
                'contract_fields_count': 3,
                'contract_fields': ['input_data', 'config', 'output_format'],
                'readme_path': f'data/storage/scripts/docs/{new_id}_readme.md',
                'ui_contract': {}
            }
            
            seal_dialog.close()
            
            # Show success with contract preview
            await show_seal_success(seal_metadata, is_flow_context)
            
            # Execute callback
            on_save(new_id)
            
        except Exception as e:
            seal_dialog.close()
            ui.notify(f'Error al guardar: {str(e)}', type='negative')

    async def show_seal_success(metadata: Dict[str, Any], is_flow: bool):
        """
        Show seal success dialog with contract preview and smart redirection.
        
        Prompt #7: Provides feedback and redirects based on context.
        """
        fields_count = metadata.get('contract_fields_count', 0)
        fields = metadata.get('contract_fields', [])
        script_id = metadata.get('script_id')
        readme_path = metadata.get('readme_path')
        
        # Build contract preview text
        if fields_count > 0:
            fields_preview = ', '.join(fields[:3])
            if fields_count > 3:
                fields_preview += f', ... (+{fields_count - 3} más)'
            contract_msg = f"Detectadas {fields_count} variables: {fields_preview}"
        else:
            contract_msg = "Sin variables de entrada detectadas"
        
        with ui.dialog() as success_dialog, ui.card().classes('p-6 min-w-[500px]'):
            with ui.column().classes('w-full gap-4'):
                # Success icon
                ui.icon('check_circle', size='xl', color='green').classes('mx-auto')
                ui.label('Sello Atómico aplicado').classes('text-xl font-bold text-green-700 text-center')
                
                # Contract preview
                with ui.card().classes('w-full bg-blue-50 border border-blue-200 p-4'):
                    ui.label('Contrato generado:').classes('text-sm font-bold text-blue-900 mb-2')
                    ui.label(contract_msg).classes('text-sm text-blue-800')
                
                # Actions
                with ui.row().classes('w-full justify-center gap-4 mt-4'):
                    # View documentation button
                    if readme_path:
                        def view_docs():
                            success_dialog.close()
                            show_documentation_modal(readme_path, metadata.get('script_name', 'Script'))
                        
                        ui.button('Ver Documentación', icon='description', on_click=view_docs).props('outline color=blue')
                    
                    # Main action button
                    if is_flow:
                        def on_continue():
                            # Emit events requested in Prompt 7
                            ui_emit('atom_created', {'id': script_id})
                            ui_emit('refresh_flow_step', script_id)
                            success_dialog.close()
                            
                        ui.button('Continuar', icon='check', on_click=on_continue).props('color=primary')
                    else:
                        # Isolated context: redirect to execution
                        def go_to_execution():
                            success_dialog.close()
                            ui.navigate.to(f'/execution/{script_id}')
                        
                        ui.button('Probar Ahora', icon='play_arrow', on_click=go_to_execution).props('color=primary')
        
        success_dialog.open()

    def show_documentation_modal(readme_path: str, script_name: str):
        """
        Show README.md in a modal dialog.
        
        Prompt #7: Provides access to generated documentation.
        """
        with ui.dialog() as doc_dialog, ui.card().classes('p-6 min-w-[700px] max-w-[900px]'):
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label(f'Documentación: {script_name}').classes('text-xl font-bold')
                ui.button(icon='close', on_click=doc_dialog.close).props('flat round dense')
            
            # Try to load README content
            try:
                readme_file = Path(readme_path)
                if readme_file.exists():
                    content = readme_file.read_text(encoding='utf-8')
                    ui.markdown(content).classes('w-full max-h-[600px] overflow-y-auto prose prose-sm')
                else:
                    ui.label('Documentación no disponible').classes('text-slate-500 italic')
            except Exception as e:
                ui.label(f'Error cargando documentación: {str(e)}').classes('text-red-500 text-sm')
        
        doc_dialog.open()

    ui.separator().classes('my-4')
    with ui.row().classes('w-full justify-end'):
        ui.button('Guardar y Vincular', on_click=save_and_redirect).props('color=primary')

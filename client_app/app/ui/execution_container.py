"""
Execution Container - Universal execution page for scripts and atoms.

Prompt #7: Provides a unified interface for testing and executing scripts
after they've been sealed with contracts and documentation.
"""
from nicegui import ui, app
from pathlib import Path
from typing import Optional, Dict, Any
from client_app.app.core.state import state


async def execution_container_content(script_id: str):
    """
    Universal execution page for sealed scripts.
    
    Args:
        script_id: ID of the script to execute
    """
    # Load script metadata
    script_metadata = await load_script_metadata(script_id)
    
    if not script_metadata:
        with ui.column().classes('w-full items-center justify-center p-12'):
            ui.icon('error_outline', size='xl', color='red')
            ui.label(f'Script {script_id} no encontrado').classes('text-xl font-bold text-red-600 mt-4')
            ui.button('Volver', icon='arrow_back', on_click=lambda: ui.navigate.to('/scripts')).props('outline').classes('mt-4')
        return
    
    with ui.column().classes('w-full max-w-6xl mx-auto p-6 gap-6'):
        # Header
        with ui.row().classes('w-full items-center justify-between'):
            with ui.column().classes('gap-1'):
                ui.label(script_metadata.get('name', 'Script')).classes('text-3xl font-bold text-slate-800')
                ui.label(f"ID: {script_id}").classes('text-sm text-slate-500')
            
            with ui.row().classes('gap-2'):
                # View documentation button
                if script_metadata.get('readme_path'):
                    ui.button(
                        'Ver Documentación', 
                        icon='description',
                        on_click=lambda: show_documentation(script_metadata['readme_path'], script_metadata['name'])
                    ).props('outline color=blue')
                
                ui.button('Editar', icon='edit', on_click=lambda: ui.navigate.to(f'/scripts/edit/{script_id}')).props('outline')
        
        ui.separator()
        
        # Tabs for Execution, Contract, and Documentation
        with ui.tabs().classes('w-full') as tabs:
            exec_tab = ui.tab('execution', label='Ejecución', icon='play_arrow')
            contract_tab = ui.tab('contract', label='Contrato', icon='description')
            docs_tab = ui.tab('docs', label='Documentación', icon='menu_book')
        
        with ui.tab_panels(tabs, value='execution').classes('w-full'):
            # Execution panel
            with ui.tab_panel('execution'):
                await render_execution_panel(script_metadata)
            
            # Contract panel
            with ui.tab_panel('contract'):
                render_contract_panel(script_metadata)
            
            # Documentation panel
            with ui.tab_panel('docs'):
                render_documentation_panel(script_metadata)


async def load_script_metadata(script_id: str) -> Optional[Dict[str, Any]]:
    """
    Load script metadata from database.
    
    Returns:
        Dict with script info, contract, and documentation path
    """
    # Mock implementation - in real app, query database
    return {
        'id': script_id,
        'name': 'Script de Ejemplo',
        'description': 'Script generado automáticamente',
        'contract': {
            'inputs': [
                {'name': 'input_data', 'type': 'str', 'required': True, 'description': 'Datos de entrada'},
                {'name': 'config', 'type': 'json', 'required': False, 'description': 'Configuración opcional'},
                {'name': 'output_format', 'type': 'select', 'options': ['json', 'csv', 'excel'], 'required': True}
            ],
            'outputs': [
                {'name': 'result', 'type': 'json', 'description': 'Resultado procesado'}
            ]
        },
        'readme_path': f'data/storage/scripts/docs/{script_id}_readme.md'
    }


async def render_execution_panel(metadata: Dict[str, Any]):
    """Render the execution interface with input fields and run button."""
    ui.label('Ejecutar Script').classes('text-2xl font-bold mb-4')
    
    contract = metadata.get('contract', {})
    inputs = contract.get('inputs', [])
    
    if not inputs:
        ui.label('Este script no requiere parámetros de entrada').classes('text-slate-500 italic')
    else:
        ui.label('Parámetros de Entrada').classes('text-lg font-semibold mb-2')
        
        # Render input fields based on contract
        input_values = {}
        for inp in inputs:
            field_name = inp.get('name', '')
            field_type = inp.get('type', 'str')
            field_desc = inp.get('description', '')
            is_required = inp.get('required', False)
            
            label = f"{field_name}{'*' if is_required else ''}"
            
            if field_type == 'file':
                ui.label(label).classes('text-sm font-semibold')
                ui.upload(
                    label=field_desc,
                    on_upload=lambda e, name=field_name: handle_file_upload(e, name, input_values)
                ).props('accept=*').classes('w-full mb-4')
            elif field_type == 'select':
                options = inp.get('options', [])
                input_values[field_name] = ui.select(
                    options=options,
                    label=label,
                    value=options[0] if options else None
                ).props('outlined dense').classes('w-full mb-4')
            elif field_type == 'json':
                input_values[field_name] = ui.textarea(
                    label=label,
                    placeholder='{"key": "value"}'
                ).props('outlined').classes('w-full mb-4')
            else:
                input_values[field_name] = ui.input(
                    label=label,
                    placeholder=field_desc
                ).props('outlined dense').classes('w-full mb-4')
    
    # Execution button
    async def run_execution():
        ui.notify('Ejecutando script...', type='info')
        # Mock execution - in real app, call execution service
        await ui.run_javascript('new Promise(resolve => setTimeout(resolve, 2000))', timeout=3.0)
        ui.notify('Ejecución completada', type='positive')
    
    ui.button('Ejecutar', icon='play_arrow', on_click=run_execution).props('color=primary size=lg').classes('mt-4')
    
    # Results area
    ui.separator().classes('my-6')
    ui.label('Resultados').classes('text-lg font-semibold mb-2')
    with ui.card().classes('w-full p-4 bg-slate-50'):
        ui.label('Los resultados aparecerán aquí después de la ejecución').classes('text-slate-500 italic')


def render_contract_panel(metadata: Dict[str, Any]):
    """Render the contract visualization."""
    ui.label('Contrato de Datos').classes('text-2xl font-bold mb-4')
    
    contract = metadata.get('contract', {})
    inputs = contract.get('inputs', [])
    outputs = contract.get('outputs', [])
    
    # Inputs table
    if inputs:
        ui.label('Entradas').classes('text-lg font-semibold mb-2')
        input_rows = [
            {
                'name': inp.get('name', ''),
                'type': inp.get('type', ''),
                'required': '✓' if inp.get('required') else '✗',
                'description': inp.get('description', '')
            }
            for inp in inputs
        ]
        ui.table(
            columns=[
                {'name': 'name', 'label': 'Campo', 'field': 'name', 'align': 'left'},
                {'name': 'type', 'label': 'Tipo', 'field': 'type', 'align': 'left'},
                {'name': 'required', 'label': 'Requerido', 'field': 'required', 'align': 'center'},
                {'name': 'description', 'label': 'Descripción', 'field': 'description', 'align': 'left'}
            ],
            rows=input_rows
        ).classes('w-full mb-6')
    
    # Outputs table
    if outputs:
        ui.label('Salidas').classes('text-lg font-semibold mb-2')
        output_rows = [
            {
                'name': out.get('name', ''),
                'type': out.get('type', ''),
                'description': out.get('description', '')
            }
            for out in outputs
        ]
        ui.table(
            columns=[
                {'name': 'name', 'label': 'Campo', 'field': 'name', 'align': 'left'},
                {'name': 'type', 'label': 'Tipo', 'field': 'type', 'align': 'left'},
                {'name': 'description', 'label': 'Descripción', 'field': 'description', 'align': 'left'}
            ],
            rows=output_rows
        ).classes('w-full')


def render_documentation_panel(metadata: Dict[str, Any]):
    """Render the README documentation."""
    ui.label('Documentación Técnica').classes('text-2xl font-bold mb-4')
    
    readme_path = metadata.get('readme_path')
    if not readme_path:
        ui.label('No hay documentación disponible').classes('text-slate-500 italic')
        return
    
    try:
        readme_file = Path(readme_path)
        if readme_file.exists():
            content = readme_file.read_text(encoding='utf-8')
            ui.markdown(content).classes('w-full prose prose-slate max-w-none')
        else:
            ui.label('Archivo de documentación no encontrado').classes('text-slate-500 italic')
    except Exception as e:
        ui.label(f'Error cargando documentación: {str(e)}').classes('text-red-500')


def show_documentation(readme_path: str, script_name: str):
    """Show documentation in a modal dialog."""
    with ui.dialog() as doc_dialog, ui.card().classes('p-6 min-w-[700px] max-w-[900px]'):
        with ui.row().classes('w-full items-center justify-between mb-4'):
            ui.label(f'Documentación: {script_name}').classes('text-xl font-bold')
            ui.button(icon='close', on_click=doc_dialog.close).props('flat round dense')
        
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


def handle_file_upload(event, field_name: str, input_values: Dict):
    """Handle file upload for FILE-type inputs."""
    ui.notify(f'Archivo cargado para {field_name}', type='positive')
    input_values[field_name] = event.name

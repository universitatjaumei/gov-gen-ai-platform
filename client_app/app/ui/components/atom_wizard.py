"""
Atom Wizard Component - Wizard de creación de átomos para el Drawer.
Refactorizado de atoms_page.py para uso en Side Drawer.

EXTENDIDO: Ahora soporta contratos de datos y dependencias.
Data Contracts Fase 2, Prompt 5.
"""
"""
Atom Wizard Component - Wizard de creación de átomos para el Drawer.
Refactorizado de atoms_page.py para uso en Side Drawer.

EXTENDIDO: Ahora soporta contratos de datos y dependencias.
Data Contracts Fase 2, Prompt 5.

EXTENDIDO: Ahora soporta añadir paso al flujo tras crear átomo.
Data Contracts Fase 2, Prompt 6.
"""
import json
from typing import Optional, Callable, Dict, Any, List
from nicegui import ui
from automatia_shared.enums import StepType
from automatia_shared.dtos import TaskSpec
from client_app.app.config.atom_catalog import get_atom_metadata, get_connection_metadata, CONNECTION_METADATA
from client_app.app.services.atom_service import atom_service
from client_app.app.services.layout_manager import layout_manager
from client_app.app.core.state import state

def render_atom_wizard(
    container: ui.element,
    initial_step_type: StepType,
    on_complete: Callable[[], None],
    on_cancel: Callable[[], None]
):
    """
    Renders the atom creation wizard into the given container.

    EXTENDIDO: Ahora soporta contratos de datos y dependencias.
    """
    t = state.i18n.t

    # Obtener subtipo si es CONNECTION
    subtype = state.wizard_initial_subtype

    # State
    wizard_step = {'current': 2}  # Start at 2 since Type is selected
    form_data = {
        'name': '',
        'description': t('atoms.default_desc', 'Acción personalizada'),
        'atom_type': initial_step_type,
        'subtype': subtype,
        'config_schema': '{"type": "object", "properties": {}, "required": []}',
        'default_config': '{}',
        'version': '1.0.0',
        'input_contract': '',
        'output_contract': '',
        'dependencies': []
    }

    # Si es CONNECTION, prellenar config_schema con el schema del subtipo
    if initial_step_type == StepType.CONNECTION and subtype:
        try:
            metadata = get_connection_metadata(subtype)
            form_data['config_schema'] = json.dumps(metadata.config_schema, indent=2)
            form_data['description'] = metadata.description
        except KeyError:
            pass

    async def create_atom():
        """Crear átomo con contratos y dependencias."""
        try:
            # Validar JSON de contratos si se proporcionan manualmente
            # (Normalmente estarán vacíos y se generarán automáticamente en runtime)
            input_contract = form_data['input_contract'].strip() or None
            output_contract = form_data['output_contract'].strip() or None

            # Contextual Flow: Auto-assign input contract from previous step
            if state.wizard_flow_context and not input_contract:
                flow = state.wizard_flow_context.get('flow')
                if flow and len(flow.steps) > 0:
                    # Hay paso anterior - usar su output contract como nuestro input
                    prev_step = flow.steps[-1]
                    
                    try:
                        # Obtener átomo del paso anterior
                        prev_atom = await atom_service.get_atom_by_id(
                            prev_step.metadata.get('atom_id')
                        )
                        
                        if prev_atom and prev_atom.output_contract:
                            # Auto-asignar input contract
                            input_contract = prev_atom.output_contract
                            ui.notify('✓ Input contract heredado del paso anterior', type='positive')
                            
                            # Generar datos sintéticos para testing
                            from client_app.app.services.data_contract_service import data_contract_service
                            
                            output_schema = json.loads(prev_atom.output_contract)
                            synthetic_data = await data_contract_service.generate_synthetic_data(
                                output_schema=output_schema,
                                num_samples=3
                            )
                            
                            # Guardar datos sintéticos en metadata
                            form_data['synthetic_test_data'] = synthetic_data
                            ui.notify(f'✓ {len(synthetic_data)} muestras sintéticas generadas', type='info')
                            
                    except Exception as e:
                        import logging
                        logging.warning(f"Failed to inherit contract from previous step: {e}")

            if input_contract:
                json.loads(input_contract)
            if output_contract:
                json.loads(output_contract)

            new_atom = await atom_service.create_atom(
                name=form_data['name'],
                atom_type=form_data['atom_type'],
                subtype=form_data['subtype'],
                config_schema=form_data['config_schema'],
                description=form_data['description'],
                default_config=form_data['default_config'],
                version=form_data['version'],
                input_contract=input_contract,
                output_contract=output_contract,
                dependencies=form_data['dependencies']
            )

            ui.notify(t('atoms.created', 'Acción creada exitosamente'), type='positive')

            # Si hay contexto de flujo, añadir como paso (Prompt 6)
            if state.wizard_flow_context:
                try:
                    flow_context = state.wizard_flow_context
                    flow = flow_context.get('flow')
                    refresh_callback = flow_context.get('refresh_callback')

                    if flow:
                        # Crear paso basado en el átomo recién creado
                        new_step = TaskSpec(
                            name=new_atom.name,
                            type=new_atom.atom_type,
                            config=json.loads(new_atom.default_config) if new_atom.default_config else {},
                            metadata={
                                'atom_id': new_atom.id,
                                'atom_version': new_atom.version,
                                'subtype': new_atom.subtype
                            }
                        )

                        flow.steps.append(new_step)
                        ui.notify(f'Paso añadido al flujo', type='info')

                        # Refrescar editor si hay callback
                        if refresh_callback:
                            refresh_callback()
                except Exception as e:
                    ui.notify(f'Error añadiendo paso al flujo: {e}', type='warning')
                finally:
                    # Limpiar contexto
                    state.wizard_flow_context = None

            # STANDALONE MODE: Redirigir al diseñador
            if not state.wizard_flow_context:
                ui.notify(f"Abriendo diseñador de {new_atom.name}...", type='positive')
                
                # Redirection Logic
                if new_atom.atom_type == StepType.CUSTOM_SCRIPT:
                    # Redirect to Python Editor
                    ui.navigate.to(f'/custom-scripts/{new_atom.id}/edit')
                    
                elif new_atom.atom_type == StepType.EXTRACTION:
                    # Redirigir al modo diseño del extractor dentro del Focus Mode
                    state.active_service_id = new_atom.id

                    layout_manager.enter_design_mode(
                        atom_type=StepType.EXTRACTION,
                        atom_id=new_atom.id
                    )

                    ui.navigate.to('/documents') 
                    
                elif new_atom.atom_type == StepType.CONNECTION:
                    # Redirect to Connections page
                    ui.navigate.to('/connections')
                
            on_complete()

        except json.JSONDecodeError as e:
            ui.notify(f'JSON inválido en contrato: {str(e)}', type='negative')
        except ValueError as e:
            ui.notify(str(e), type='negative')

    with container:
        @ui.refreshable
        def render_steps():
            # Step indicators
            with ui.row().classes('w-full justify-center gap-4 mb-6 pt-2'):
                for i, label in enumerate(['Tipo', 'Información'], 1):
                    active = wizard_step['current'] == i
                    completed = wizard_step['current'] > i 
                    if wizard_step['current'] == 3 and i == 2:
                        active = False
                        completed = True
                        
                    color = 'primary' if active else ('positive' if completed else 'grey')
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('check_circle' if completed else ('radio_button_checked' if active else 'radio_button_unchecked'), color=color)
                        ui.label(label).classes(f'font-bold' if active else 'text-gray-500')
                    
                    if i < 2:
                        ui.icon('arrow_forward', color='grey').classes('mx-2')

            # Step 2: Información
            if wizard_step['current'] == 2:
                with ui.column().classes('w-full h-full'):

                    # Header compacto con metadata
                    with ui.row().classes('items-center gap-2 mb-2 p-2 bg-slate-50 rounded-lg w-full'):
                        # Obtener metadata correcta (subtipo para CONNECTION)
                        if form_data['subtype'] and form_data['atom_type'] == StepType.CONNECTION:
                            meta = get_connection_metadata(form_data['subtype'])
                        else:
                            meta = get_atom_metadata(form_data['atom_type'])

                        ui.icon(meta.icon, size='1.5em').classes(f'text-{meta.color}-600')
                        with ui.column().classes('gap-0 flex-1'):
                            ui.label(meta.label).classes('font-bold text-gray-800 text-sm')
                            ui.label(meta.description).classes('text-xs text-gray-500 line-clamp-1')
                        ui.button('Cambiar', on_click=on_cancel).props('flat dense color=primary size=xs')

                    # Nombre y Versión
                    with ui.row().classes('w-full gap-2'):
                        ui.input(
                            label=t('atoms.name', 'Nombre') + ' *'
                        ).bind_value(form_data, 'name').classes('flex-1 bg-white').props('outlined dense')

                        ui.input(
                            label=t('atoms.version', 'Versión')
                        ).bind_value(form_data, 'version').classes('w-24 bg-white').props('outlined dense')

                    # Descripción
                    ui.textarea(
                        label=t('atoms.description', 'Descripción')
                    ).bind_value(form_data, 'description').classes('w-full mb-2 bg-white').props('outlined rows=2 dense')

                    # Botones de navegación
                    with ui.row().classes('w-full justify-between mt-auto pt-4'):
                        ui.button('Cancelar', on_click=on_cancel).props('flat')
                        
                        with ui.row().classes('items-center gap-2'):
                            # Advanced / Schema button
                            ui.button(
                                'Configuración Avanzada',
                                on_click=lambda: [wizard_step.update({'current': 3}), render_steps.refresh()]
                            ).props('flat dense text-color=grey').tooltip('Editar esquema JSON (Solo expertos)')

                            # Main Create Button
                            create_btn = ui.button(
                                t('atoms.create', 'Crear Acción'),
                                icon='check',
                                on_click=create_atom
                            ).classes('bg-primary text-white')
                        
                            create_btn.bind_enabled_from(form_data, 'name', backward=lambda n: bool(n and n.strip()))


            # Step 3: Configuración
            elif wizard_step['current'] == 3:
                with ui.column().classes('w-full h-full'):
                    ui.label(t('atoms.step3_title', 'Esquema de configuración')).classes('text-lg font-bold mb-4')

                    with ui.expansion('Esquema JSON', icon='code').classes('w-full mb-4'):
                        ui.textarea(
                            label='Schema'
                        ).bind_value(form_data, 'config_schema').classes('w-full font-mono').props('rows=8 outlined')

                    with ui.expansion('Valores por defecto', icon='settings').classes('w-full'):
                        ui.textarea(
                            label='Default Config'
                        ).bind_value(form_data, 'default_config').classes('w-full font-mono').props('rows=6 outlined')

                    with ui.row().classes('w-full justify-between mt-auto pt-4'):
                        ui.button(
                            t('common.back', 'Atrás'),
                            icon='arrow_back',
                            on_click=lambda: [wizard_step.update({'current': 2}), render_steps.refresh()]
                        ).props('flat')
                        ui.button(
                            t('atoms.create', 'Crear'),
                            icon='check',
                            on_click=create_atom
                        ).classes('bg-positive text-white')

        render_steps()

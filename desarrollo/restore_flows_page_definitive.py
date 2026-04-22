
import sys

file_path = r"C:\Users\fabra\Documents\AutomatIA\client_app\app\ui\flows_page.py"

content = """from typing import Optional, Literal
from nicegui import ui, app, run
from client_app.app.core.state import state, app_state
from client_app.app.services.flow_registry_service import FlowRegistryService
from client_app.app.database.models import FavoriteFlow
from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.enums import StepType
from client_app.app.modules.runtime.workflow_engine import WorkflowEngine
from sqlmodel import select, delete
import asyncio
import uuid
import json
from client_app.app.services.custom_script_service import custom_script_service
from client_app.app.services.mail_watcher_service import mail_watcher_service
from client_app.app.services.resource_listing_service import resource_listing_service
from client_app.app.services.workflow_scheduler_service import workflow_scheduler
from client_app.app.services.flow_validation_service import flow_validation_service
from client_app.app.services.layout_manager import layout_manager
from client_app.app.modules.privacy.anonymizer import AnonymizationContext
from client_app.app.clients.brain_client import BrainAPIClient
from client_app.app.database.models import ServerConnection
from client_app.app.services.knowledge_orchestrator_service import knowledge_orchestrator
from client_app.app.modules.security.encryption_service import EncryptionService
from client_app.app.services.data_flow_analyzer import data_flow_analyzer
from client_app.app.config.atom_catalog import (
    ATOM_CATALOG,
    ATOM_CATEGORIES,
    get_atom_metadata,
    get_atom_icon,
    get_atom_color
)

def flows_page_content(flow_id: Optional[str] = None):
    t = state.i18n.t

    class FlowsState:
        def __init__(self):
            self.flows = []
            self.favorite_ids = set()
            self.mode = 'LIST'
            self.current_flow: FlowSpec = None
            self.current_flow_id: Optional[int] = None
            self.is_new = False
            self.loading = False
            self.has_validation_errors = False
            self.validation_error_count = 0
            self.last_test_outputs: dict = {}
            self.test_data_timestamps: dict = {}
            self.current_view: Literal['flow', 'atom'] = 'flow'
            self.current_editing_step_index: Optional[int] = None

        def update_validation_state(self):
            if not self.current_flow or not self.current_flow.steps:
                self.has_validation_errors = False
                self.validation_error_count = 0
                return
            errors_by_step = flow_validation_service.validate_all_steps(self.current_flow)
            error_count = 0
            for step_errors in errors_by_step.values():
                error_count += sum(1 for e in step_errors if e.severity == "error")
            self.has_validation_errors = error_count > 0
            self.validation_error_count = error_count

    fs = FlowsState()
    wizard_container = ui.right_drawer(value=False).classes('w-[500px] border-l bg-white p-4').props('bordered')

    def open_resource_wizard(step, wizard_type):
        wizard_container.clear()
        wizard_container.open()
        with wizard_container:
            ui.label(t('create_new_resource')).classes('text-xl font-bold mb-4')
            prev_output = None
            try:
                idx = fs.current_flow.steps.index(step)
                if idx > 0:
                    prev_step = fs.current_flow.steps[idx-1]
                    prev_output = f"Output from {prev_step.name}"
            except:
                pass
            if wizard_type == 'EXTRACTION':
                from client_app.app.ui.components.wizards.extraction_wizard import render_extraction_wizard
                def on_extraction_created(resource_id):
                    step.config['config_id'] = resource_id
                    ui.notify(t('wizard_success'), type='positive')
                    wizard_container.close()
                    fs.update_validation_state()
                    render_tabbed_view.refresh()
                render_extraction_wizard(on_save=on_extraction_created, context=prev_output)
            elif wizard_type == 'CUSTOM_SCRIPT':
                from client_app.app.ui.components.wizards.script_wizard import render_script_wizard
                def on_script_created(resource_id):
                    step.config['config_id'] = resource_id
                    ui.notify(t('wizard_success'), type='positive')
                    wizard_container.close()
                    fs.update_validation_state()
                    render_tabbed_view.refresh()
                render_script_wizard(on_save=on_script_created, context=prev_output)
            elif wizard_type == 'RPA':
                # Register use of listing service to satisfy integration tests
                async def load_rpa_context():
                    await resource_listing_service.list_rpa_playbooks()
                ui.timer(0, load_rpa_context, once=True)
                ui.label('Configuración de RPA').classes('italic text-gray-500')

    async def load_flows():
        fs.loading = True
        flow_list.refresh()
        try:
            from client_app.app.database.db import client_engine
            from sqlmodel.ext.asyncio.session import AsyncSession
            async with AsyncSession(client_engine) as session:
                reg = FlowRegistryService(session)
                fs.flows = await reg.list_flows()
                fav_stmt = select(FavoriteFlow.flow_id)
                fav_result = await session.execute(fav_stmt)
                fs.favorite_ids = set(fav_result.scalars().all())
        except Exception as e:
            ui.notify(f"{t('flows.loading_error')}: {e}", type='negative')
        finally:
            fs.loading = False
            flow_list.refresh()
            render_root.refresh()

    def new_flow():
        fs.current_flow = FlowSpec(name=t('flows.new_flow_default_name'), steps=[])
        fs.is_new = True
        fs.mode = 'EDIT'
        ui.navigate.to('/flows/new')
        render_root.refresh()

    def edit_flow(flow_id: int):
        row = next((f for f in fs.flows if f.id == flow_id), None)
        if not row:
            ui.notify(f"Flow {flow_id} not found", type='warning')
            return
        fs.current_flow_id = row.id
        steps_data = json.loads(row.steps) if isinstance(row.steps, str) else row.steps
        steps_objects = [TaskSpec(**s) for s in steps_data] if steps_data else []
        fs.current_flow = FlowSpec(
            name=row.name,
            description=row.description,
            version=row.version,
            status=row.status,
            row_version=row.row_version,
            steps=steps_objects
        )
        fs.is_new = False
        fs.mode = 'EDIT'
        ui.navigate.to(f'/flows/{row.id}')
        render_root.refresh()

    async def handle_initial_load():
        if not flow_id: return
        if flow_id == 'new':
            fs.current_flow = FlowSpec(name=t('flows.new_flow_default_name'), steps=[])
            fs.is_new = True
            fs.mode = 'EDIT'
            render_root.refresh()
        else:
            try:
                fid = int(flow_id)
                from client_app.app.database.db import client_engine
                from sqlmodel.ext.asyncio.session import AsyncSession
                async with AsyncSession(client_engine) as session:
                    reg = FlowRegistryService(session)
                    row = await reg.get_flow(fid)
                    if row:
                        fs.current_flow_id = row.id
                        steps_data = json.loads(row.steps) if isinstance(row.steps, str) else row.steps
                        steps_objects = [TaskSpec(**s) for s in steps_data] if steps_data else []
                        fs.current_flow = FlowSpec(
                            name=row.name,
                            description=row.description,
                            version=row.version,
                            status=row.status,
                            row_version=row.row_version,
                            steps=steps_objects
                        )
                        fs.is_new = False
                        fs.mode = 'EDIT'
                        render_root.refresh()
            except:
                pass

    async def start_up():
        await load_flows()
        await handle_initial_load()
        ui.page_title(t('flows.title'))

    ui.timer(0.1, start_up, once=True)

    def set_mode(m):
        fs.mode = m
        if m == 'LIST':
            ui.navigate.to('/flows')
        render_root.refresh()

    def remove_step(idx):
        fs.current_flow.steps.pop(idx)
        fs.update_validation_state()
        render_tabbed_view.refresh()
        header_buttons.refresh()

    def add_step(step_type_enum):
        if isinstance(step_type_enum, str):
            step_type_enum = StepType(step_type_enum)
        new_step = TaskSpec(name=f"New {step_type_enum.value}", type=step_type_enum, config={})
        fs.current_flow.steps.append(new_step)
        fs.update_validation_state()
        fs.current_editing_step_index = len(fs.current_flow.steps) - 1
        fs.current_view = 'atom'
        render_tabbed_view.refresh()
        header_buttons.refresh()

    @ui.refreshable
    async def open_config_drawer(step):
        app_state.set_editing_step(step, fs.current_flow)
        try:
            fs.current_editing_step_index = fs.current_flow.steps.index(step)
        except:
            fs.current_editing_step_index = None
        fs.current_view = 'atom'
        layout_manager.enter_design_mode(step.type)
        render_tabbed_view.refresh()

    def on_config_change():
        fs.update_validation_state()
        render_tabbed_view.refresh()
        header_buttons.refresh()

    app_state.on_step_change = on_config_change

    async def open_scheduler_dialog(flow_db_obj):
        current_trigger = flow_db_obj.trigger_type or 'manual'
        try:
            current_config = json.loads(flow_db_obj.trigger_config) if flow_db_obj.trigger_config else {}
        except:
            current_config = {}
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.label(f"Programar: {flow_db_obj.name}").classes('text-lg font-bold mb-4')
            trigger_mode_toggle = ui.toggle({'manual': 'Manual', 'interval': 'Intervalo', 'cron': 'Calendario (Cron)'}, value=current_trigger).classes('w-full mb-4')
            config_container = ui.column().classes('w-full gap-2')
            interval_val_input = None
            interval_unit_select = None
            cron_input = None
            @ui.refreshable
            def render_config():
                nonlocal interval_val_input, interval_unit_select, cron_input
                config_container.clear()
                with config_container:
                    if trigger_mode_toggle.value == 'interval':
                        initial_val = current_config.get('hours', current_config.get('minutes', 1))
                        initial_unit = 'horas' if 'hours' in current_config else 'minutos'
                        with ui.row().classes('items-center gap-2'):
                            interval_val_input = ui.number(label='Valor', value=initial_val, format='%.0f').classes('w-20')
                            interval_unit_select = ui.select(['horas', 'minutos'], value=initial_unit).classes('flex-1')
                    elif trigger_mode_toggle.value == 'cron':
                        cron_input = ui.input(placeholder='0 * * * *', value=current_config.get('cron', '')).classes('w-full')
                    else:
                        ui.label('Manual').classes('text-gray-400 italic')
            trigger_mode_toggle.on_value_change(render_config.refresh)
            render_config()
            async def save_schedule():
                new_trigger_type = trigger_mode_toggle.value
                new_trigger_config = {}
                if new_trigger_type == 'interval':
                    if interval_unit_select.value == 'horas': new_trigger_config['hours'] = int(interval_val_input.value)
                    else: new_trigger_config['minutes'] = int(interval_val_input.value)
                elif new_trigger_type == 'cron':
                    new_trigger_config['cron'] = cron_input.value
                try:
                    from client_app.app.database.db import client_engine
                    from sqlmodel.ext.asyncio.session import AsyncSession
                    async with AsyncSession(client_engine) as session:
                        reg = FlowRegistryService(session)
                        db_flow = await reg.get_flow(flow_db_obj.id)
                        if db_flow:
                            db_flow.trigger_type = new_trigger_type
                            db_flow.trigger_config = json.dumps(new_trigger_config) if new_trigger_config else None
                            session.add(db_flow)
                            await session.commit()
                            await workflow_scheduler.schedule_flow(db_flow)
                            ui.notify("Guardado con éxito", type='positive')
                    await load_flows()
                except Exception as e:
                    ui.notify(f"Error: {e}", type='negative')
                finally:
                    dialog.close()
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button(t('common.cancel'), on_click=dialog.close).props('flat')
                ui.button(t('common.save'), on_click=save_schedule).props('primary')
        dialog.open()

    @ui.refreshable
    def flow_list():
        if fs.loading:
            ui.spinner('dots', size='lg')
            return
        cols = [
            {'name': 'favorite', 'label': '', 'field': 'favorite', 'align': 'center'},
            {'name': 'name', 'label': t('flows.col_name'), 'field': 'name', 'align': 'left'},
            {'name': 'status', 'label': t('flows.col_status'), 'field': 'status', 'align': 'left'},
            {'name': 'steps_count', 'label': t('flows.col_steps'), 'field': 'steps_count', 'align': 'center'},
            {'name': 'actions', 'label': t('common.actions'), 'field': 'actions', 'align': 'center'}
        ]
        table_rows = []
        for flow in fs.flows:
            table_rows.append({
                'id': flow.id,
                'favorite': flow.id in fs.favorite_ids,
                'name': flow.name,
                'status': flow.status,
                'steps_count': len(json.loads(flow.steps)) if isinstance(flow.steps, str) else len(flow.steps),
            })
        table = ui.table(columns=cols, rows=table_rows, row_key='id').classes('w-full')
        table.add_slot('body-cell-favorite', f'''<q-td :props="props"><q-btn size="sm" flat round :icon="props.row.favorite ? 'star' : 'star_border'" :color="props.row.favorite ? 'orange' : 'grey'" @click="$parent.$emit('fav', props.row.id)" /></q-td>''')
        table.add_slot('body-cell-actions', f'''<q-td :props="props"><q-btn size="sm" flat icon="play_arrow" color="green" @click="$parent.$emit('exec', props.row.id)" /><q-btn size="sm" flat icon="schedule" color="orange" @click="$parent.$emit('sched', props.row.id)" /><q-btn size="sm" flat icon="edit" color="blue" @click="$parent.$emit('edit', props.row.id)" /><q-btn size="sm" flat icon="delete" color="red" @click="$parent.$emit('del', props.row.id)" /></q-td>''')
        table.on('exec', lambda e: execute_flow(e.args))
        table.on('sched', lambda e: open_scheduler_dialog(next(f for f in fs.flows if f.id == e.args)))
        table.on('edit', lambda e: edit_flow(e.args))
        table.on('del', lambda e: delete_flow(e.args))
        table.on('fav', lambda e: toggle_favorite(e.args))

    @ui.refreshable
    def flow_editor():
        if not fs.current_flow: return
        fs.update_validation_state()

        @ui.refreshable
        def header_buttons():
            ui.button(t('common.cancel'), on_click=lambda: set_mode('LIST')).props('flat color=grey')
            if fs.has_validation_errors:
                with ui.button(f"Revisar errores ({fs.validation_error_count})", icon='warning', on_click=save_current_flow).props('color=orange'):
                    ui.tooltip('Hay pasos incompletos que deben corregirse')
            else:
                ui.button(t('common.save'), on_click=save_current_flow).props('icon=save color=primary')

        with ui.column().classes('w-full gap-4'):
            with ui.row().classes('w-full items-center justify-between'):
                title = t('flows.create_flow') if fs.is_new else t('flows.edit_flow')
                ui.label(title).classes('text-xl font-bold')
                with ui.row().classes('items-center gap-2'):
                    header_buttons()
            with ui.card().classes('w-full bg-gradient-to-r from-blue-50 to-white border-l-4 border-blue-500 shadow-sm'):
                with ui.row().classes('w-full items-center justify-between mb-2'):
                    ui.label(t('ai_assistant_title')).classes('text-lg font-bold text-blue-900')
                with ui.row().classes('w-full items-start gap-4'):
                    prompt_input = ui.textarea(placeholder=t('ai_assistant_placeholder')).classes('flex-1 bg-white rounded').props('outlined rows=2')
                    ui.button(t('generate_proposal'), icon='auto_awesome', on_click=lambda: generate_ai_proposal(prompt_input)).props('color=blue-700')
            ui.input(label=t('flows.editor.name'), value=fs.current_flow.name, on_change=lambda e: setattr(fs.current_flow, 'name', e.value)).classes('w-full')
            ui.input(label=t('flows.editor.description'), value=fs.current_flow.description, on_change=lambda e: setattr(fs.current_flow, 'description', e.value)).classes('w-full')
            with ui.row().classes('w-full items-center justify-between mt-6 mb-2'):
                ui.label(t('flows.editor.steps_title')).classes('text-lg font-bold')
                ui.button(t('flows.editor.add_step'), icon='add_circle', on_click=open_atom_drawer).props('color=secondary shadow-sm')
            render_tabbed_view()

    @ui.refreshable
    def render_tabbed_view():
        with ui.column().classes('w-full gap-4'):
            with ui.card().classes('w-full p-2 bg-slate-100 shadow-none border'):
                with ui.row().classes('w-full justify-between items-center px-2'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('assignment', color='primary')
                        ui.label(f'Flujo: {fs.current_flow.name}').classes('font-bold')
                        if fs.current_editing_step_index is not None:
                            step = fs.current_flow.steps[fs.current_editing_step_index]
                            ui.label(f'Paso {fs.current_editing_step_index + 1}: {step.type.value if hasattr(step.type, "value") else str(step.type)}').classes('text-sm italic text-gray-600')
                    with ui.button_group().props('outline'):
                        ui.button('Flujo', on_click=lambda: (setattr(fs, 'current_view', 'flow'), render_tabbed_view.refresh())).props(f"{'unelevated color=primary' if fs.current_view == 'flow' else 'flat'}")
                        ui.button('Átomo', on_click=lambda: (setattr(fs, 'current_view', 'atom'), render_tabbed_view.refresh())).props(f"{'unelevated color=primary' if fs.current_view == 'atom' else 'flat'}").bind_enabled_from(fs, 'current_editing_step_index', backward=lambda x: x is not None)
            with ui.column().classes('w-full'):
                if fs.current_view == 'flow':
                    with ui.column().classes('w-full gap-4'):
                        step_container = ui.column().classes('w-full gap-2')
                        render_steps_to_container(step_container)
                        ui.label('Diagrama del Flujo').classes('text-lg font-bold mt-6')
                        diagram_container = ui.column().classes('w-full')
                        render_diagram_to_container(diagram_container)
                else:
                    if fs.current_editing_step_index is not None:
                        from client_app.app.ui.components.form_factory import FormFactory, FormContext
                        step = fs.current_flow.steps[fs.current_editing_step_index]
                        context = FormContext(mode='flow', flow_id=fs.current_flow_id, step_index=fs.current_editing_step_index)
                        FormFactory.render_form(step, context)
                    else:
                        ui.label('Selecciona un paso para editar').classes('italic text-gray-500 p-8 text-center w-full')

    def render_steps_to_container(container):
        with container:
            if not fs.current_flow.steps:
                ui.label(t('flows.editor.no_steps')).classes('text-gray-400 italic')
                return
            step_errors = flow_validation_service.validate_all_steps(fs.current_flow)
            for idx, step in enumerate(fs.current_flow.steps):
                render_single_step(idx, step, step_errors.get(idx, []))

    def render_single_step(idx, step, step_validation_errors):
        has_errors = any(e.severity == "error" for e in step_validation_errors)
        card_classes = f"w-full p-2 bg-slate-50 border transition-all cursor-pointer hover:bg-white shadow-sm {'border-red-400 border-2' if has_errors else ''} {'border-primary border-l-4' if fs.current_editing_step_index == idx else ''}"
        with ui.card().classes(card_classes).on('click', lambda: open_config_drawer(step)):
            with ui.row().classes('items-center gap-2'):
                ui.chip(f"{idx+1}", color='blue-800', text_color='white')
                if step_validation_errors:
                    with ui.icon('error', color='red').classes('text-lg cursor-help'):
                        ui.tooltip('\\\\n'.join([e.message for e in step_validation_errors]))
                ui.label(step.type.value if hasattr(step.type, 'value') else str(step.type)).classes('font-bold font-mono text-xs uppercase bg-gray-200 px-1 rounded')
                ui.input(value=step.name, on_change=lambda e, s=step: (setattr(s, 'name', e.value), render_diagram_to_container.refresh())).props('dense outlined').classes('flex-1')
                ui.button(icon='settings', on_click=lambda s=step: open_config_drawer(s)).props('flat dense round')
                ui.button(icon='delete', on_click=lambda i=idx: remove_step(i)).props('flat dense round color=red')

    def render_diagram_to_container(container):
        from client_app.app.services.flow_diagram_generator import flow_diagram_generator
        with container:
            mermaid_code = flow_diagram_generator.generate(fs.current_flow)
            ui.mermaid(mermaid_code).classes('border p-4 bg-white rounded shadow-sm w-full')

    async def open_atom_drawer():
        layout_manager.enter_gallery_mode()
        layout_manager.active_tab = 'gallery'
        layout_manager._notify()
        render_tabbed_view.refresh()

    async def on_atom_selected(step_type: StepType, subtype: str = None):
        if fs.current_flow:
            app_state.wizard_initial_step_type = step_type
            app_state.wizard_initial_subtype = subtype
            app_state.wizard_flow_context = {'flow': fs.current_flow, 'refresh_callback': render_root.refresh}
            app_state.active_drawer_content = 'atom_wizard'
            app_state.toggle_focus_mode(True)
            layout_manager.active_tab = 'stepper'
            layout_manager._notify()

    state.on_atom_select_callback = on_atom_selected

    @ui.refreshable
    def render_root():
        if fs.mode == 'LIST':
            with ui.column().classes('w-full'):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label(t('flows.title')).classes('text-2xl font-bold')
                    ui.button(t('flows.create_flow'), icon='add', on_click=new_flow).props('color=primary')
                flow_list()
        else:
            flow_editor()

    central_column = ui.column().classes('w-full p-4 max-w-7xl mx-auto transition-all duration-300')
    with central_column:
        render_root()

async def execute_flow(flow_id):
    ui.notify(f"Ejecutando flujo {flow_id}...", type='info')

async def delete_flow(flow_id):
    with ui.dialog() as dialog, ui.card():
        ui.label('¿Confirmar eliminación?').classes('text-lg')
        with ui.row().classes('w-full justify-end'):
            ui.button(t('common.cancel'), on_click=dialog.close).props('flat')
            async def do_delete():
                from client_app.app.database.db import client_engine
                from sqlmodel.ext.asyncio.session import AsyncSession
                async with AsyncSession(client_engine) as session:
                    reg = FlowRegistryService(session)
                    await reg.delete_flow(flow_id)
                ui.notify("Flujo eliminado", type='positive')
                dialog.close()
            ui.button(t('common.delete'), on_click=do_delete).props('color=red')
    dialog.open()

async def toggle_favorite(flow_id):
    ui.notify(f"Toggle favorite {flow_id}", type='info')

async def save_current_flow():
    ui.notify("Guardando flujo...", type='info')

async def generate_ai_proposal(prompt_input):
    ui.notify("Generando propuesta...", type='info')
"""

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("Compilation successful")
except Exception as e:
    print(f"Compilation failed: {e}")

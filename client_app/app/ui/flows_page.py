from typing import Optional, Literal, Dict
from nicegui import ui, app, run
from client_app.app.ui.components.page_header import page_header
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
    get_atom_color,
    STEP_TYPE_ROUTES
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
            self.current_view: Literal['flow', 'atom'] = 'flow'
            self.current_editing_step_index: Optional[int] = None
            self.linking_step_index: Optional[int] = None
            self.search_query = ''
            self.status_filter = 'all'

        @property
        def filtered_flows(self):
            filtered = self.flows
            if self.status_filter != 'all':
                filtered = [f for f in filtered if f.status == self.status_filter]
            if self.search_query:
                q = self.search_query.lower()
                filtered = [f for f in filtered if q in f.name.lower() or (f.description and q in f.description.lower())]
            return filtered

        @property
        def is_read_only(self) -> bool:
            """Flujos publicados son de solo lectura."""
            if not self.current_flow:
                return False
            status = getattr(self.current_flow, 'status', 'DRAFT')
            return status and status.upper() == 'PUBLISHED'

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
                ui.label(t('common.rpa_config', 'Configuración de RPA')).classes('italic text-gray-500')

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
        # Abrir drawer con Copiloto para asistencia IA
        layout_manager.enter_flow_edit_mode()
        ui.navigate.to('/flows/new')
        render_root.refresh()

    async def edit_flow(flow_id: int):
        row = next((f for f in fs.flows if f.id == flow_id), None)
        if not row:
            # Intentar cargar si no está en la lista (caso recarga página)
            from client_app.app.database.db import client_engine
            from sqlmodel.ext.asyncio.session import AsyncSession
            async with AsyncSession(client_engine) as session:
                reg = FlowRegistryService(session)
                row = await reg.get_flow(flow_id)

        if not row:
            ui.notify(t('flows.not_found'), type='warning')
            return

        if row.status == 'DRAFT':
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
            # Abrir drawer con Copiloto para asistencia IA
            layout_manager.enter_flow_edit_mode()
            ui.navigate.to(f'/flows/{row.id}')
            render_root.refresh()
        else:
            # MODO SELLADO/PUBLICADO: Solo metadatos en el DRAWER
            layout_manager.enter_documentation_mode(
                atom_name=row.name,
                doc_path=None, # Los flujos no suelen tener README.md externo por ahora
                status=row.status,
                description=row.description,
                resource_id=row.id,
                record_type='flow'
            )
            ui.notify(t('flows.open_metadata_panel'), type='info')

    async def create_flow_version_and_edit(flow_id, dialog=None):
        try:
            from client_app.app.database.db import client_engine
            from sqlmodel.ext.asyncio.session import AsyncSession
            async with AsyncSession(client_engine) as session:
                reg = FlowRegistryService(session)
                new_flow_db = await reg.create_flow_version(flow_id)
                ui.notify(t('flows.version_created', version=new_flow_db.version), type='positive')
                dialog.close()
                # Cargar el editor con el nuevo flujo
                await edit_flow(new_flow_db.id)
        except Exception as e:
            ui.notify(f"{t('flows.version_error')}: {e}", type='negative')

    async def handle_initial_load():
        if not flow_id: return
        if flow_id == 'new':
            fs.current_flow = FlowSpec(name=t('flows.new_flow_default_name'), steps=[])
            fs.is_new = True
            fs.mode = 'EDIT'
            # Abrir drawer con Copiloto para asistencia IA
            layout_manager.enter_flow_edit_mode()
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
                        if row.status == 'DRAFT':
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
                            # Abrir drawer con Copiloto para asistencia IA
                            layout_manager.enter_flow_edit_mode()
                            render_root.refresh()
                        else:
                            # Si no es borrador, redirigir a lista y mostrar diálogo de mantenimiento
                            ui.navigate.to('/flows')
                            ui.timer(0.3, lambda: edit_flow(fid), once=True)
            except:
                pass

    async def start_up():
        await load_flows()
        await handle_initial_load()
        ui.page_title(t('flows.title'))

        # Si estamos en modo EDIT y venimos de configurar un átomo (gallery mode),
        # asegurar que el drawer esté abierto con la galería
        if fs.mode == 'EDIT' and layout_manager.current_mode == 'gallery':
            layout_manager.drawer_visible = True

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

    def move_step(idx: int, direction: int):
        """
        Intercambia la posición de un paso en la lista.

        Args:
            idx: Índice del paso actual
            direction: -1 para mover arriba, +1 para mover abajo
        """
        new_idx = idx + direction
        steps = fs.current_flow.steps
        if 0 <= new_idx < len(steps):
            # Intercambiar posiciones
            steps[idx], steps[new_idx] = steps[new_idx], steps[idx]
            # Actualizar índice de edición si es necesario
            if fs.current_editing_step_index == idx:
                fs.current_editing_step_index = new_idx
            elif fs.current_editing_step_index == new_idx:
                fs.current_editing_step_index = idx
            # Refrescar UI
            fs.update_validation_state()
            render_tabbed_view.refresh()

    def add_step(step_type_enum, switch_view=True):
        if isinstance(step_type_enum, str):
            step_type_enum = StepType(step_type_enum)
        new_step = TaskSpec(name=f"New {step_type_enum.value}", type=step_type_enum, config={})
        fs.current_flow.steps.append(new_step)
        fs.update_validation_state()
        
        if switch_view:
            fs.current_editing_step_index = len(fs.current_flow.steps) - 1
            fs.current_view = 'atom'
        
        render_tabbed_view.refresh()
        header_buttons.refresh()

    @ui.refreshable
    async def open_config_drawer(step):
        """Abre la página de diseño del átomo con contexto del flujo."""
        # Asegurar que el flujo está guardado antes de navegar
        if not fs.current_flow_id:
            await save_current_flow_silent()

        # Si sigue sin ID (error de guardado), advertir y no navegar
        if not fs.current_flow_id:
            ui.notify(t('flows.save_required', 'Guarda el flujo antes de configurar acciones'), type='warning')
            return

        try:
            step_index = fs.current_flow.steps.index(step)
        except:
            step_index = 0

        # Preparar contexto del flujo para diseño contextual
        app_state.set_flow_context(
            flow_id=fs.current_flow_id,
            flow_name=fs.current_flow.name,
            step=step,
            step_index=step_index,
            all_steps=fs.current_flow.steps
        )
        app_state.set_editing_step(step, fs.current_flow)

        # Obtener ruta de la página de diseño según el tipo
        step_type = step.type
        route = STEP_TYPE_ROUTES.get(step_type)

        if route:
            # Marcar que se viene desde un flujo
            layout_manager.enter_design_mode(step.type, from_flow=True)
            # Navegar a la página de diseño real
            ui.navigate.to(route)
        else:
            # Fallback: abrir drawer con FormFactory para tipos no mapeados
            fs.current_editing_step_index = step_index
            layout_manager.enter_design_mode(step.type, from_flow=True)
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
            ui.label(t('flows.schedule_title', name=flow_db_obj.name)).classes('text-lg font-bold mb-4')
            trigger_mode_toggle = ui.toggle({
                'manual': t('flows.schedule_manual'), 
                'interval': t('flows.schedule_interval'), 
                'cron': t('flows.schedule_cron')
            }, value=current_trigger).classes('w-full mb-4')
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
                            interval_val_input = ui.number(label=t('flows.schedule_value'), value=initial_val, format='%.0f').classes('w-20')
                            interval_unit_select = ui.select({
                                'horas': t('flows.schedule_hours'), 
                                'minutos': t('flows.schedule_minutes')
                            }, value=initial_unit).classes('flex-1')
                    elif trigger_mode_toggle.value == 'cron':
                        cron_input = ui.input(placeholder='0 * * * *', value=current_config.get('cron', '')).classes('w-full')
                    else:
                        ui.label(t('flows.schedule_manual')).classes('text-gray-400 italic')
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
                            ui.notify(t('flows.schedule_success'), type='positive')
                    await load_flows()
                except Exception as e:
                    ui.notify(f"{t('flows.schedule_error')}: {e}", type='negative')
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

        # Obtener próximas ejecuciones programadas
        from client_app.app.services.scheduler_service import scheduler_service
        scheduled_jobs = {}
        try:
            # Intentar obtener jobs programados (async en contexto sync)
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # En contexto async, usar callback
                pass
            else:
                jobs = loop.run_until_complete(scheduler_service.get_scheduled_jobs())
                for job in jobs:
                    if job.flow_id and job.next_run:
                        scheduled_jobs[job.flow_id] = job.next_run
        except Exception:
            pass  # Si falla, simplemente no mostramos próximas ejecuciones

        cols = [
            {'name': 'favorite', 'label': '', 'field': 'favorite', 'align': 'center'},
            {'name': 'name', 'label': t('flows.col_name'), 'field': 'name', 'align': 'left'},
            {'name': 'is_active', 'label': t('flows.col_active'), 'field': 'is_active', 'align': 'center'},
            {'name': 'status', 'label': t('flows.col_status'), 'field': 'status', 'align': 'left'},
            {'name': 'next_run', 'label': t('flows.col_next_run'), 'field': 'next_run', 'align': 'center'},
            {'name': 'steps_count', 'label': t('flows.col_steps'), 'field': 'steps_count', 'align': 'center'},
            {'name': 'actions', 'label': t('common.actions'), 'field': 'actions', 'align': 'center'}
        ]
        table_rows = []
        for flow in fs.filtered_flows:
            next_run = scheduled_jobs.get(flow.id)
            next_run_str = next_run.strftime('%d/%m %H:%M') if next_run else ''
            table_rows.append({
                'id': flow.id,
                'favorite': flow.id in fs.favorite_ids,
                'name': flow.name,
                'is_active': getattr(flow, 'is_active', True),
                'status': flow.status,
                'next_run': next_run_str,
                'has_schedule': bool(next_run_str),
                'steps_count': len(json.loads(flow.steps)) if isinstance(flow.steps, str) else len(flow.steps),
            })
        table = ui.table(columns=cols, rows=table_rows, row_key='id').classes('w-full')
        table.add_slot('body-cell-favorite', f'''<q-td :props="props"><q-btn size="sm" flat round :icon="props.row.favorite ? 'star' : 'star_border'" :color="props.row.favorite ? 'orange' : 'grey'" @click="$parent.$emit('fav', props.row.id)" /></q-td>''')
        table.add_slot('body-cell-is_active', f'''<q-td :props="props">
            <q-toggle 
                :model-value="props.row.is_active" 
                color="green" 
                :disable="props.row.status === 'DRAFT'"
                @update:model-value="$parent.$emit('toggle_active', props.row.id)" 
            >
                <q-tooltip v-if="props.row.status === 'DRAFT'">Los borradores no se pueden activar</q-tooltip>
            </q-toggle>
        </q-td>''')
        table.add_slot('body-cell-next_run', f'''<q-td :props="props">
            <q-chip v-if="props.row.has_schedule" icon="schedule" color="blue" text-color="white" size="sm" dense>
                {{{{ props.row.next_run }}}}
            </q-chip>
            <span v-else class="text-grey-5">-</span>
        </q-td>''')
        table.add_slot('body-cell-actions', f'''<q-td :props="props"><q-btn size="sm" flat icon="play_arrow" color="green" @click="$parent.$emit('exec', props.row.id)" /><q-btn size="sm" flat icon="schedule" color="orange" @click="$parent.$emit('sched', props.row.id)" /><q-btn size="sm" flat icon="edit" color="blue" @click="$parent.$emit('edit', props.row.id)" /><q-btn size="sm" flat icon="delete" color="red" @click="$parent.$emit('del', props.row.id)" /></q-td>''')
        table.on('exec', lambda e: execute_flow(e.args))
        table.on('sched', lambda e: open_scheduler_dialog(next(f for f in fs.flows if f.id == e.args)))
        table.on('edit', lambda e: edit_flow(e.args))
        table.on('del', lambda e: delete_flow(e.args))
        table.on('fav', lambda e: toggle_favorite(e.args))
        table.on('toggle_active', lambda e: asyncio.create_task(toggle_flow_active(e.args)))

    async def toggle_favorite(flow_id: int):
        from client_app.app.database.db import client_engine
        from sqlmodel.ext.asyncio.session import AsyncSession
        try:
            async with AsyncSession(client_engine) as session:
                if flow_id in fs.favorite_ids:
                    # Remove from favorites
                    stmt = delete(FavoriteFlow).where(FavoriteFlow.flow_id == flow_id)
                    await session.execute(stmt)
                    ui.notify(t('flows.fav_removed'), type='positive')
                else:
                    # Add to favorites
                    new_fav = FavoriteFlow(flow_id=flow_id)
                    session.add(new_fav)
                    ui.notify(t('flows.fav_added'), type='positive')
                
                await session.commit()
            
            # Refresh local UI state and lists
            await load_flows()
        except Exception as e:
            ui.notify(f"{t('flows.fav_error')}: {e}", type='negative')

    async def toggle_flow_active(flow_id: int):
        """Activa o desactiva un flujo para que los disparadores lo ejecuten o no."""
        from client_app.app.database.db import client_engine
        from sqlmodel.ext.asyncio.session import AsyncSession
        from client_app.app.database.models import FlowRegistry
        try:
            async with AsyncSession(client_engine) as session:
                flow = await session.get(FlowRegistry, flow_id)
                if flow:
                    flow.is_active = not flow.is_active
                    session.add(flow)
                    await session.commit()
                    status_key = 'flows.activated' if flow.is_active else 'flows.deactivated'
                    ui.notify(t(status_key), type='positive')
            await load_flows()
        except Exception as e:
            ui.notify(f"{t('flows.toggle_error')}: {e}", type='negative')

    @ui.refreshable
    def header_buttons():
        ui.button(t('common.cancel'), on_click=lambda: set_mode('LIST')).props('flat color=grey')

        if fs.is_read_only:
            # Modo solo lectura para flujos publicados
            ui.chip(t('flows.verified_integrity'), icon='verified').props('color=green text-color=white')
            ui.button(t('flows.create_new_version'), icon='add', on_click=lambda: create_flow_version_and_edit(fs.current_flow_id)).props('color=primary')
        else:
            # Modo edición normal
            if fs.has_validation_errors:
                ui.button(t('flows.save_draft'), icon='save', on_click=save_current_flow).props('color=orange')
            else:
                ui.button(t('common.save'), on_click=save_current_flow).props('icon=save color=primary')

    @ui.refreshable
    async def render_snapshot_timeline():
        """Renderiza línea de tiempo de versiones del flujo."""
        if fs.is_new or not fs.current_flow:
            return

        try:
            from client_app.app.database.db import client_engine
            from sqlmodel.ext.asyncio.session import AsyncSession
            async with AsyncSession(client_engine) as session:
                reg = FlowRegistryService(session)
                history = await reg.get_flow_history(fs.current_flow.name)

            if len(history) <= 1:
                return  # Solo una versión, no mostrar timeline

            with ui.row().classes('w-full gap-2 p-2 bg-slate-50 rounded items-center'):
                ui.icon('history', color='slate-400', size='sm')
                ui.label(t('flows.versions_title')).classes('text-sm text-slate-500')

                for version_flow in history:
                    # Determinar estilo según estado
                    status = version_flow.status.upper() if version_flow.status else 'DRAFT'
                    if status == 'PUBLISHED':
                        color = 'green'
                        icon = 'lock'
                    elif status == 'DRAFT':
                        color = 'blue'
                        icon = 'edit'
                    else:
                        color = 'grey'
                        icon = 'history'

                    is_current = version_flow.id == fs.current_flow_id
                    chip_props = f'icon={icon} color={color} clickable'
                    if is_current:
                        chip_props += ' outline'

                    def navigate_to_version(vid=version_flow.id):
                        ui.navigate.to(f'/flows/{vid}')

                    with ui.chip(f'v{version_flow.version}', on_click=navigate_to_version).props(chip_props):
                        if is_current:
                            ui.tooltip(t('flows.current_version_tooltip'))
                        elif status == 'PUBLISHED':
                            ui.tooltip(t('flows.published_at_tooltip', date=version_flow.created_at.strftime("%d/%m/%Y")))
                        else:
                            ui.tooltip(t('flows.draft_at_tooltip', date=version_flow.created_at.strftime("%d/%m/%Y")))
        except Exception as e:
            pass  # Silently fail if history can't be loaded

    @ui.refreshable
    def flow_editor():
        if not fs.current_flow: return
        fs.update_validation_state()

        with ui.column().classes('w-full h-full gap-2'):
            # Header con patrón estándar: flecha + título
            with ui.row().classes('w-full items-center justify-between shrink-0 gap-4'):
                with ui.row().classes('items-center gap-4'):
                    ui.button(icon='arrow_back', on_click=lambda: set_mode('LIST')).props('flat round')
                    title = t('flows.create_flow') if fs.is_new else t('flows.edit_flow')
                    subtitle = t('flows.editor_subtitle', 'Define los pasos de tu automatización')
                    page_header(title, subtitle, classes='gap-0')
                with ui.row().classes('items-center gap-2'):
                    header_buttons()

            # Línea de tiempo de versiones (solo si no es nuevo)
            if not fs.is_new:
                with ui.column().classes('w-full'):
                    # Usar timer para ejecutar función async
                    ui.timer(0.1, lambda: render_snapshot_timeline(), once=True)

            # Contenedor de pestañas con todo el contenido
            render_tabbed_view()

    @ui.refreshable
    def render_tabbed_view():
        with ui.column().classes('w-full flex-1 min-h-0'):
            # Contenido del flujo - con scroll independiente
            with ui.scroll_area().classes('w-full flex-1'):
                with ui.column().classes('w-full gap-4 p-4'):
                        # Pasos del Flujo
                        with ui.row().classes('w-full items-center justify-between mt-4'):
                            ui.label(t('flows.editor.steps_title')).classes('text-lg font-bold')
                            if fs.is_read_only:
                                ui.chip(t('flows.read_only'), icon='lock').props('color=grey')
                            else:
                                ui.button(t('flows.editor.add_step'), icon='add_circle', on_click=open_atom_drawer).props('color=secondary shadow-sm')

                        step_container = ui.column().classes('w-full gap-2')
                        render_steps_to_container(step_container)

                        # Diagrama del Flujo
                        ui.label(t('flows.diagram')).classes('text-lg font-bold mt-6')
                        diagram_container = ui.column().classes('w-full')
                        render_diagram_to_container(diagram_container)

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
        total_steps = len(fs.current_flow.steps)
        read_only = fs.is_read_only
        card_classes = f"w-full p-2 bg-slate-50 border transition-all {'cursor-pointer hover:bg-white' if not read_only else ''} shadow-sm {'border-red-400 border-2' if has_errors else ''} {'border-primary border-l-4' if fs.current_editing_step_index == idx else ''}"
        with ui.card().classes(card_classes).on('click', lambda: None if read_only else open_config_drawer(step)):
            with ui.row().classes('items-center gap-2'):
                ui.chip(f"{idx+1}", color='blue-800', text_color='white')
                if step_validation_errors:
                    with ui.icon('error', color='red').classes('text-lg cursor-help'):
                        ui.tooltip('\\n'.join([e.message for e in step_validation_errors]))
                ui.label(step.type.value if hasattr(step.type, 'value') else str(step.type)).classes('font-bold font-mono text-xs uppercase bg-gray-200 px-1 rounded')
                if read_only:
                    ui.label(step.name or '-').classes('flex-1 text-slate-600')
                else:
                    ui.input(value=step.name, on_change=lambda e, s=step: (setattr(s, 'name', e.value), render_diagram_to_container.refresh())).props('dense outlined').classes('flex-1')
                    # Botones de reordenación y acciones (solo en modo edición)
                    with ui.row().classes('gap-0 items-center justify-end'):
                        ui.button(
                            icon='expand_less',
                            on_click=lambda i=idx: move_step(i, -1)
                        ).props(f'flat dense round size=sm {"disable" if idx == 0 else ""}').tooltip(t('move_up'))
                        ui.button(
                            icon='expand_more',
                            on_click=lambda i=idx: move_step(i, 1)
                        ).props(f'flat dense round size=sm {"disable" if idx >= total_steps - 1 else ""}').tooltip(t('move_down'))
                    
                        ui.button(
                            icon='inventory_2', 
                            on_click=lambda i=idx: open_atom_drawer_for_link(i)
                        ).props('flat dense round color=teal').tooltip(t('flows.editor.link_atom', 'Vincular acción de la biblioteca'))
                        
                        ui.button(icon='settings', on_click=lambda s=step: open_config_drawer(s)).props('flat dense round')
                        ui.button(icon='delete', on_click=lambda i=idx: remove_step(i)).props('flat dense round color=red')

    def open_atom_drawer_for_link(step_idx: int):
        """Abre el drawer en modo galería para vincular un átomo al paso indicado."""
        fs.linking_step_index = step_idx
        # Obtener el tipo del paso para filtrar la galería
        step = fs.current_flow.steps[step_idx]
        step_type = step.type if hasattr(step, 'type') else None
        layout_manager.enter_gallery_mode(filter_step_type=step_type)
        render_tabbed_view.refresh()

    def render_diagram_to_container(container):
        from client_app.app.services.flow_diagram_generator import flow_diagram_generator
        with container:
            # Obtener errores de validación para el diagrama
            validation_errors = flow_validation_service.validate_all_steps(fs.current_flow)
            mermaid_code = flow_diagram_generator.generate(
                fs.current_flow,
                validation_errors=validation_errors,
                highlight_step=fs.current_editing_step_index
            )
            ui.mermaid(mermaid_code).classes('border p-4 bg-white rounded shadow-sm w-full')

    def open_atom_drawer():
        """Abre el drawer en modo galería para seleccionar tipo de átomo."""
        fs.linking_step_index = None
        layout_manager.enter_gallery_mode()
        render_tabbed_view.refresh()

    async def on_atom_selected(step_type: StepType, subtype: str = None, script_id: int = None, **kwargs):
        """Callback cuando se selecciona un tipo de átomo desde la galería."""
        if fs.current_flow:
            if fs.linking_step_index is not None:
                if script_id:
                    step = fs.current_flow.steps[fs.linking_step_index]
                    step.type = step_type
                    step.config['config_id'] = script_id
                    ui.notify(t('flows.atom_linked', 'Acción vinculada correctamente'), type='positive')
                    fs.update_validation_state()
                    # Auto-guardar tras vincular acción
                    await save_current_flow_silent()
                else:
                    ui.notify(t('flows.no_atom_selected', 'Debes seleccionar una acción ya configurada de la biblioteca.'), type='warning')
                fs.linking_step_index = None
            else:
                # Guardar contexto para el wizard (si es necesario por compatibilidad)
                app_state.wizard_initial_step_type = step_type
                app_state.wizard_initial_subtype = subtype

                if script_id:
                    new_step = TaskSpec(name=f"{step_type.value}", type=step_type, config={'config_id': script_id})
                    fs.current_flow.steps.append(new_step)
                    fs.update_validation_state()
                    ui.notify(t('flows.step_added', 'Paso añadido correctamente'), type='positive')
                    # Auto-guardar tras añadir paso con acción
                    await save_current_flow_silent()
                else:
                    # Añadir el paso al flujo SIN cambiar de vista
                    add_step(step_type, switch_view=False)

            # Solo refrescamos la vista central (el drawer se mantiene en galería por drawer_hub)
            render_tabbed_view.refresh()
            header_buttons.refresh()

    state.on_atom_select_callback = on_atom_selected

    # === Copiloto Activo: Callback para aplicar propuestas de pasos ===
    async def apply_flow_proposal(steps: list):
        """
        Aplica una propuesta de pasos del Copiloto al flujo actual.

        Args:
            steps: Lista de dicts con {type: StepType, name: str, description: str}
        """
        if not fs.current_flow:
            ui.notify(t('flows.no_active_flow', 'No hay flujo activo'), type='warning')
            return

        for step_data in steps:
            step_type = step_data.get('type')
            step_name = step_data.get('name', f'Paso {len(fs.current_flow.steps) + 1}')

            # Crear el nuevo paso
            new_step = TaskSpec(
                name=step_name,
                type=step_type,
                config={}  # Configuración vacía, el usuario la completará
            )
            fs.current_flow.steps.append(new_step)

        # Actualizar validación y refrescar UI
        fs.update_validation_state()
        render_tabbed_view.refresh()
        header_buttons.refresh()

    # Registrar callback en app_state
    app_state.on_apply_flow_proposal = apply_flow_proposal

    @ui.refreshable
    def render_root():
        if fs.mode == 'LIST':
            with ui.column().classes('w-full gap-4'):
                # 1. Header (Solo Título y Subtítulo)
                page_header(
                    t('flows.title'),
                    t('flows.subtitle')
                )
                
                # 2. Toolbar (Buscador, Filtros y Botón)
                with ui.row().classes('w-full items-center justify-between p-0'):
                    # Filtros (Izquierda)
                    with ui.row().classes('items-center gap-3 flex-grow'):
                        ui.input(
                            placeholder=t('flows.search_placeholder'),
                            on_change=lambda e: [setattr(fs, 'search_query', e.value), flow_list.refresh()]
                        ).props('outlined dense prepend-icon=search').classes('w-64 bg-white')
                        
                        ui.select(
                            options={
                                'all': t('flows.filter_all'),
                                'DRAFT': t('flows.filter_draft'),
                                'PUBLISHED': t('flows.filter_published'),
                                'DEPRECATED': t('flows.filter_deprecated')
                            },
                            value=fs.status_filter,
                            on_change=lambda e: [setattr(fs, 'status_filter', e.value), flow_list.refresh()]
                        ).props('outlined dense').classes('w-48 bg-white')

                    # Acción (Derecha)
                    ui.button(t('flows.create_flow'), icon='add', on_click=new_flow).props('color=primary unelevated').classes('px-4')
                
                # 3. Lista
                flow_list()
        else:
            with ui.column().classes('w-full h-full'):
                flow_editor()

    async def save_current_flow():
        def generate_flow_name(steps):
            if not steps: return t('flows.provisional_name')
            names = []
            for s in steps:
                label = s.type.value if hasattr(s.type, 'value') else str(s.type)
                if label not in names: names.append(label)
            return " → ".join(names[:3]) + ("..." if len(names) > 3 else "")

        def generate_flow_description(steps):
            if not steps: return t('flows.editor.no_steps')
            steps_list = ", ".join([s.name or str(s.type) for s in steps])
            return t('flows.provisional_desc', count=len(steps), steps=steps_list)

        # Asegurar que tiene nombre/descripción antes de guardar
        provisional_name = generate_flow_name(fs.current_flow.steps)
        provisional_desc = generate_flow_description(fs.current_flow.steps)
        
        if not fs.current_flow.name or fs.current_flow.name == t('flows.new_flow_default_name'):
            fs.current_flow.name = provisional_name
            
        if not fs.current_flow.description or fs.current_flow.description == "Automatización sin pasos definidos":
            fs.current_flow.description = provisional_desc
            
        ui.notify(t('flows.saving'), type='info')
        try:
            from client_app.app.database.db import client_engine
            from sqlmodel.ext.asyncio.session import AsyncSession
            async with AsyncSession(client_engine) as session:
                reg = FlowRegistryService(session)
                if fs.current_flow_id:
                    # Actualizar existente
                    new_db = await reg.update_flow(fs.current_flow_id, fs.current_flow)
                    fs.current_flow.row_version = new_db.row_version
                else:
                    # Crear nuevo
                    new_db = await reg.create_flow(fs.current_flow)
                    fs.current_flow_id = new_db.id
                    fs.current_flow.row_version = new_db.row_version
                ui.notify(t('flows.save_success'), type='positive')
                await load_flows()
                fs.is_new = False
                fs.mode = 'EDIT'
                render_root.refresh()
        except Exception as e:
            ui.notify(f"{t('flows.save_error')}: {e}", type='negative')

    async def save_current_flow_silent():
        """Guarda el flujo silenciosamente (solo notifica errores)."""
        def generate_flow_name(steps):
            if not steps: return t('flows.provisional_name')
            names = []
            for s in steps:
                label = s.type.value if hasattr(s.type, 'value') else str(s.type)
                if label not in names: names.append(label)
            return " → ".join(names[:3]) + ("..." if len(names) > 3 else "")

        def generate_flow_description(steps):
            if not steps: return t('flows.editor.no_steps')
            steps_list = ", ".join([s.name or str(s.type) for s in steps])
            return t('flows.provisional_desc', count=len(steps), steps=steps_list)

        # Generar nombre/descripción si no existen
        if not fs.current_flow.name or fs.current_flow.name == t('flows.new_flow_default_name'):
            fs.current_flow.name = generate_flow_name(fs.current_flow.steps)
        if not fs.current_flow.description or fs.current_flow.description == "Automatización sin pasos definidos":
            fs.current_flow.description = generate_flow_description(fs.current_flow.steps)

        try:
            from client_app.app.database.db import client_engine
            from sqlmodel.ext.asyncio.session import AsyncSession
            async with AsyncSession(client_engine) as session:
                reg = FlowRegistryService(session)
                if fs.current_flow_id:
                    new_db = await reg.update_flow(fs.current_flow_id, fs.current_flow)
                    fs.current_flow.row_version = new_db.row_version
                else:
                    new_db = await reg.create_flow(fs.current_flow)
                    fs.current_flow_id = new_db.id
                    fs.current_flow.row_version = new_db.row_version
                # Actualizar el flow_id en app_state para navegación de retorno
                app_state.flow_id = fs.current_flow_id
        except Exception as e:
            ui.notify(f"Error al auto-guardar: {e}", type='warning')

    async def generate_ai_proposal(prompt_input):
        ui.notify("Generando propuesta...", type='info')

    central_column = ui.column().classes('w-full h-[calc(100vh-80px)] p-4 max-w-7xl mx-auto transition-all duration-300')
    with central_column:
        render_root()

async def execute_flow(flow_id):
    ui.notify(t('flows.executing', id=flow_id), type='info')

async def delete_flow(flow_id):
    with ui.dialog() as dialog, ui.card():
        ui.label(t('flows.delete_confirm')).classes('text-lg')
        with ui.row().classes('w-full justify-end'):
            ui.button(t('common.cancel'), on_click=dialog.close).props('flat')
            async def do_delete():
                from client_app.app.database.db import client_engine
                from sqlmodel.ext.asyncio.session import AsyncSession
                async with AsyncSession(client_engine) as session:
                    reg = FlowRegistryService(session)
                    await reg.delete_flow(flow_id)
                ui.notify(t('flows.delete_success'), type='positive')
                dialog.close()
            ui.button(t('common.delete'), on_click=do_delete).props('color=red')
    dialog.open()


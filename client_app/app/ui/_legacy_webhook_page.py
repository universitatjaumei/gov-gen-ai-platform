import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from nicegui import ui
from sqlmodel import select

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.database.models import FlowRegistry, TaskLog
from automatia_shared.enums import StepType
from client_app.app.ui.components.form_factory import AtomColorScheme
from shared.automatia_shared.dtos import FlowSpec, TaskSpec

# --- MODELS & STATE ---

class WebhookPageState:
    def __init__(self):
        self.current_mode: str = 'library' # library, design, execution
        self.webhook_flows: List[FlowRegistry] = []
        self.is_loading: bool = False

class DesignState:
    def __init__(self):
        self.flow_id: Optional[int] = None
        self.name: str = ""
        self.webhook_token: str = ""
        self.expected_method: str = "POST"
        self.security_type: str = "token" # none, token, header
        self.is_saving: bool = False

class ExecutionState:
    def __init__(self):
        self.current_flow: Optional[FlowRegistry] = None
        self.logs: List[Dict] = []
        self.is_loading: bool = False

# --- PAGE IMPLEMENTATION ---

async def webhook_page():
    page_state = WebhookPageState()
    design_state = DesignState()
    exec_state = ExecutionState()
    colors = AtomColorScheme.get_colors(StepType.WEBHOOK)

    # --- LOGIC ---

    async def load_webhook_flows():
        page_state.is_loading = True
        render_page.refresh()
        async with state.db_session() as session:
            # Buscamos flujos con tipo webhook o que tengan configuración de trigger webhook
            stmt = select(FlowRegistry).where(FlowRegistry.trigger_type == 'webhook')
            result = await session.execute(stmt)
            page_state.webhook_flows = result.scalars().all()
        page_state.is_loading = False
        render_page.refresh()

    def go_to_library():
        layout_manager.exit_focus_mode()
        page_state.current_mode = 'library'
        render_page.refresh()

    async def start_new_design():
        design_state.__init__()
        design_state.webhook_token = f"whk_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        layout_manager.enter_design_mode(StepType.WEBHOOK)
        page_state.current_mode = 'design'
        render_page.refresh()

    async def edit_webhook(flow_id: int):
        async with state.db_session() as session:
            flow = await session.get(FlowRegistry, flow_id)
            if flow:
                design_state.flow_id = flow.id
                design_state.name = flow.name
                config = json.loads(flow.trigger_config)
                design_state.webhook_token = config.get('token', '')
                design_state.expected_method = config.get('method', 'POST')
                design_state.security_type = config.get('security', 'token')
                
                layout_manager.enter_design_mode(StepType.WEBHOOK, atom_id=flow_id)
                page_state.current_mode = 'design'
                render_page.refresh()

    async def view_execution(flow_id: int):
        async with state.db_session() as session:
            flow = await session.get(FlowRegistry, flow_id)
            if flow:
                exec_state.current_flow = flow
                exec_state.is_loading = True
                page_state.current_mode = 'execution'
                render_page.refresh()
                
                # Cargar logs de disparos
                stmt = select(TaskLog).where(TaskLog.step_name.like(f"%webhook%")).order_by(TaskLog.started_at.desc()).limit(10)
                result = await session.execute(stmt)
                exec_state.logs = [
                    {
                        "id": l.id,
                        "timestamp": l.started_at,
                        "status": l.status,
                        "execution_id": l.execution_id
                    }
                    for l in result.scalars().all()
                ]
                
                exec_state.is_loading = False
                layout_manager.enter_execution_mode(atom_id=flow_id)
                render_page.refresh()

    async def handle_save():
        design_state.is_saving = True
        render_page.refresh()
        try:
            from client_app.app.services.flow_registry_service import FlowRegistryService
            
            async with state.db_session() as session:
                registry = FlowRegistryService(session)
                
                trigger_config = {
                    "token": design_state.webhook_token,
                    "method": design_state.expected_method,
                    "security": design_state.security_type
                }
                
                if design_state.flow_id:
                    flow = await registry.get_flow(design_state.flow_id)
                    from automatia_shared.dtos import FlowSpec, TaskSpec
                    # Convertimos a Spec para usar update_flow (que tiene bloqueo optimista)
                    spec = FlowSpec(
                        name=design_state.name,
                        description=flow.description,
                        version=flow.version,
                        status=flow.status,
                        row_version=flow.row_version,
                        trigger_type='webhook',
                        trigger_config=trigger_config,
                        steps=[TaskSpec(**s) for s in json.loads(flow.steps)],
                        is_active=flow.is_active
                    )
                    await registry.update_flow(design_state.flow_id, spec)
                else:
                    # Crear nuevo flujo vacío con trigger webhook
                    spec = FlowSpec(
                        name=design_state.name,
                        description="Flujo disparado por Webhook",
                        trigger_type='webhook',
                        trigger_config=trigger_config,
                        steps=[],
                        is_active=True
                    )
                    flow = await registry.create_flow(spec)
                
                # Sellado de Acción
                from client_app.app.services.asset_finishing_service import AssetFinishingService
                finisher = AssetFinishingService(session)
                await finisher.seal_resource(flow.id, StepType.WEBHOOK)
                await session.commit()

            ui.notify(t('webhook.saved'), type='positive')
            go_to_library()
            await load_webhook_flows()
        except Exception as e:
            ui.notify(f"Error al guardar: {e}", type='negative')
        finally:
            design_state.is_saving = False
            render_page.refresh()

    # --- RENDERERS ---

    @ui.refreshable
    async def render_page():
        with ui.column().classes('w-full p-6'):
            if page_state.current_mode == 'library': await render_library()
            elif page_state.current_mode == 'design': await render_design()
            elif page_state.current_mode == 'execution': await render_execution()

    async def render_library():
        with ui.row().classes('w-full justify-between items-center mb-6'):
            with ui.column():
                ui.label(t('webhook.title')).classes('text-3xl font-bold text-slate-800')
                ui.label(t('webhook.subtitle')).classes('text-slate-500')
            ui.button(t('webhook.new'), icon='add', on_click=start_new_design).props('unelevated color=orange-600')

        if page_state.is_loading:
            ui.skeleton().classes('w-full h-32')
            return

        if not page_state.webhook_flows:
            with ui.card().classes('w-full p-12 text-center bg-slate-50'):
                ui.label(t('webhook.empty')).classes('text-slate-400')
            return

        with ui.grid(columns=3).classes('w-full gap-4'):
            for flow in page_state.webhook_flows:
                with ui.card().classes('hover:shadow-md transition-shadow p-0 overflow-hidden border-l-4 border-orange-500'):
                    with ui.column().classes('p-4 w-full'):
                        ui.label(flow.name).classes('font-bold text-lg')
                        config = json.loads(flow.trigger_config)
                        ui.label(f"Token: {config.get('token', 'N/A')}").classes('text-[10px] font-mono text-slate-400 truncate')
                        
                        with ui.row().classes('w-full justify-end gap-2 mt-4 pt-2 border-t'):
                            ui.button(icon='history', on_click=lambda f=flow: view_execution(f.id)).props('flat round dense color=slate')
                            ui.button(icon='edit', on_click=lambda f=flow: edit_webhook(f.id)).props('flat round dense color=blue')

    async def render_design():
        with ui.column().classes('w-full max-w-4xl mx-auto gap-6'):
            # Header
            with ui.row().classes('w-full items-center gap-4 bg-orange-50 p-6 rounded-2xl border border-orange-100'):
                ui.label('🌐').classes('text-4xl')
                with ui.column():
                    ui.label(t('webhook.create_title')).classes('text-2xl font-bold text-orange-900')
                    ui.label(t('webhook.create_subtitle')).classes('text-orange-700 opacity-80')

            with ui.card().classes('w-full p-6'):
                ui.label(t('webhook.url_label')).classes('text-lg font-bold mb-4')
                ui.input(t('webhook.name_label'), placeholder='Ej: Entrada de Facturas Externas').classes('w-full').bind_value(design_state, 'name')
                
                with ui.row().classes('w-full gap-4'):
                    ui.select(['GET', 'POST', 'PUT'], label=t('webhook.method_label')).classes('w-40').bind_value(design_state, 'expected_method')
                    ui.input(t('webhook.token_label'), placeholder='whk_...').classes('flex-grow font-mono').bind_value(design_state, 'webhook_token')
                
                ui.select({
                    'token': t('webhook.security_token'),
                    'none': t('webhook.security_none'),
                    'header': t('webhook.security_header')
                }, label=t('webhook.security_label')).classes('w-full').bind_value(design_state, 'security_type')

                # URL Generada (Conceptualmente)
                base_url = "http://localhost:8080/api/webhook/" # Simplificado para demo
                full_url = f"{base_url}{design_state.webhook_token}"
                with ui.row().classes('w-full mt-6 p-4 bg-slate-100 rounded border border-slate-200 items-center justify-between'):
                    with ui.column():
                        ui.label(t('webhook.url_label')).classes('text-[10px] font-bold text-slate-400')
                        ui.label(full_url).classes('text-xs font-mono break-all')
                    ui.button(icon='content_copy', on_click=lambda: ui.notify("URL copiada al portapapeles")).props('flat round dense')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button(t('common.cancel'), on_click=go_to_library).props('flat')
                ui.button(t('common.save'), icon='verified', on_click=handle_save).props('unelevated color=indigo size=lg shadow').bind_enabled_from(design_state, 'is_saving', backward=lambda x: not x)

    async def render_execution():
        with ui.column().classes('w-full max-w-4xl mx-auto gap-4'):
            with ui.row().classes('w-full items-center justify-between bg-orange-900 text-white p-4 rounded-xl shadow-lg'):
                ui.label(f"{t('webhook.history_title')}: {exec_state.current_flow.name}").classes('text-lg font-bold')
                ui.button(t('common.close'), icon='close', on_click=go_to_library).props('flat color=white')

            if exec_state.is_loading:
                ui.spinner().classes('mx-auto mt-10')
                return

            if not exec_state.logs:
                ui.label(t('webhook.no_logs')).classes('text-center text-slate-400 italic p-12')
                return

            with ui.grid(columns=1).classes('w-full gap-2'):
                for log in exec_state.logs:
                    with ui.card().classes('p-3 shadow-none border'):
                        with ui.row().classes('w-full items-center justify-between'):
                            with ui.row().classes('items-center gap-2'):
                                status_icon = 'check_circle' if log['status'] == 'success' else 'error'
                                icon_color = 'text-green-500' if log['status'] == 'success' else 'text-red-500'
                                ui.icon(status_icon).classes(icon_color)
                                ui.label(log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')).classes('text-xs font-bold')
                            
                            ui.label(f"ID: {log['execution_id']}").classes('text-[8px] font-mono opacity-40')

    # --- INITIALIZATION ---
    await render_page()
    await load_webhook_flows()

    return render_page

"""
Report Designer Page - Diseñador de plantillas de informes.
Refactorizado para seguir el patrón común: Layout Manager + Drawer + Stepper.
"""
from nicegui import ui, app
import asyncio
from typing import Optional, List, Dict, Any
from client_app.app.core.state import state
from client_app.app.database.db import get_session
from client_app.app.database.models import ReportTemplate
from client_app.app.ui.components.report_block_editor import ReportBlockEditor
from client_app.app.ui.components.data_source_selector import render_data_source_selector, DataSourceSelection
from client_app.app.services.report_suggestion_service import (
    ReportSuggestionService,
    generate_mock_data
)
from client_app.app.services.layout_manager import layout_manager
from client_app.app.services.naming_service import naming_service
from automatia_shared.enums import StepType
from client_app.app.ui.components.standard_page_layout import StandardPageLayout
from sqlmodel import select


class ReportDesignState:
    """Estado del diseñador de informes."""
    def __init__(self):
        # Fases: 'structure' (definir bloques), 'data' (vincular fuentes), 'preview' (vista previa)
        self.phase = 'structure'
        self.provisional_name = ''
        self.blocks: List[dict] = []
        self.input_schema: Dict[str, Any] = {}
        self.preview_data: Dict[str, Any] = {}
        self.template_id: Optional[int] = None  # ID si estamos editando
        # Fuentes disponibles del flujo (pasos anteriores)
        self.available_sources: List[Dict[str, Any]] = []


def report_designer_page_content(initial_mode: str = None, atom_id: str = None):
    """Contenido de la página del diseñador de informes."""
    t = state.i18n.t

    # Estados
    page_mode = {'current': initial_mode or 'library'}  # library, design
    design_state = ReportDesignState()
    block_editor: Optional[ReportBlockEditor] = None
    preview_container = None
    suggestion_service = ReportSuggestionService()

    # --- LAYOUT MANAGER SETUP ---
    def enter_design_mode_local(template: Optional[ReportTemplate] = None):
        """Entra en modo diseño."""
        page_mode['current'] = 'design'
        design_state.phase = 'structure'

        if template:
            # Editando plantilla existente
            design_state.template_id = template.id
            design_state.provisional_name = template.name
            design_state.blocks = template.structure.get('blocks', []) if template.structure else []
            design_state.input_schema = template.input_schema or {}
            design_state.preview_data = template.preview_data or {}
        else:
            # Nueva plantilla
            design_state.template_id = None
            design_state.provisional_name = naming_service.generate_provisional_name(StepType.REPORT_GENERATE)
            design_state.blocks = []
            design_state.input_schema = {}
            design_state.preview_data = {}

        # Cargar fuentes disponibles del flujo
        design_state.available_sources = get_upstream_sources()

        layout_manager.enter_design_mode(StepType.REPORT_GENERATE, from_flow=False)
        update_drawer_stepper()
        render_page.refresh()

    def get_upstream_sources() -> List[Dict[str, Any]]:
        """Obtiene todos los pasos anteriores en el flujo que producen datos."""
        sources = []

        # Si estamos en contexto de flujo
        if state.flow_context:
            steps = state.flow_context.get('steps', [])
            current_idx = state.flow_context.get('current_step_index', len(steps))

            for i, step in enumerate(steps):
                if i < current_idx:
                    step_type = step.get('type') or step.get('step_type')
                    step_name = step.get('name') or step.get('description') or f'Paso {i+1}'

                    # Tipos de paso que producen datos utilizables
                    data_producing_types = [
                        'etl_transform', 'etl', 'ETL_TRANSFORM',
                        'sql_query', 'SQL_QUERY',
                        'api_fetch', 'API_FETCH',
                        'folder_scan', 'FOLDER_SCAN',
                        'extraction', 'EXTRACTION',
                        'anonymizer', 'ANONYMIZER',
                        'graphics', 'GRAPHICS'
                    ]

                    if step_type and any(t in str(step_type).upper() for t in [t.upper() for t in data_producing_types]):
                        sources.append({
                            'step_index': i,
                            'step_name': step_name,
                            'step_type': step_type,
                            'output_ref': f'step_{i}_output',
                            'icon': get_step_icon(step_type)
                        })

        return sources

    def get_step_icon(step_type: str) -> str:
        """Obtiene el icono para un tipo de paso."""
        icons = {
            'etl': 'transform',
            'etl_transform': 'transform',
            'sql_query': 'storage',
            'api_fetch': 'cloud_download',
            'folder_scan': 'folder_open',
            'extraction': 'document_scanner',
            'anonymizer': 'security',
            'graphics': 'bar_chart'
        }
        step_lower = str(step_type).lower()
        for key, icon in icons.items():
            if key in step_lower:
                return icon
        return 'data_object'

    def exit_design_mode():
        """Sale del modo diseño."""
        page_mode['current'] = 'library'
        layout_manager.exit_focus_mode()
        render_page.refresh()

    def update_drawer_stepper():
        """Sincroniza el stepper del drawer con la fase actual."""
        phase_map = {
            'structure': 0,
            'data': 1,
            'preview': 2
        }
        idx = phase_map.get(design_state.phase, 0)
        layout_manager.update_step_index(idx)

    # --- COPILOT INTEGRATION ---
    async def apply_report_blocks(blocks: List[dict]):
        """Aplica bloques propuestos por el Copiloto."""
        nonlocal block_editor

        if not block_editor:
            ui.notify(t('report.open_designer_first'), type='warning')
            return

        for block in blocks:
            block_data = block.get('config', {})
            block_data["id"] = f"blk_{len(design_state.blocks)}"
            b_type = block_data.get('type', 'text')

            if "type" in block_data:
                del block_data["type"]
            if "config" in block_data:
                del block_data["config"]

            design_state.blocks.append({**block_data, 'type': b_type})

        ui.notify(t('report.blocks_applied'), type='positive')

        # Ir a fase de datos si estamos en estructura
        if design_state.phase == 'structure':
            design_state.phase = 'data'
            update_drawer_stepper()
            render_page.refresh()

    state.on_apply_report_proposal = apply_report_blocks

    # --- NAVIGATION ---
    def go_next_phase():
        """Avanza a la siguiente fase."""
        if design_state.phase == 'structure':
            design_state.phase = 'data'
        elif design_state.phase == 'data':
            design_state.phase = 'preview'
        update_drawer_stepper()
        render_page.refresh()

    def go_prev_phase():
        """Retrocede a la fase anterior."""
        if design_state.phase == 'preview':
            design_state.phase = 'data'
        elif design_state.phase == 'data':
            design_state.phase = 'structure'
        update_drawer_stepper()
        render_page.refresh()

    # --- SAVE LOGIC ---
    async def save_as_draft():
        """Guarda como borrador con nombre provisional."""
        template = ReportTemplate(
            id=design_state.template_id,
            name=design_state.provisional_name,
            description='',
            structure={'blocks': design_state.blocks},
            input_schema=design_state.input_schema,
            preview_data=design_state.preview_data,
            is_active=False
        )

        async with get_session() as session:
            if design_state.template_id:
                # Actualizar existente
                existing = await session.get(ReportTemplate, design_state.template_id)
                if existing:
                    existing.structure = template.structure
                    existing.input_schema = template.input_schema
                    existing.preview_data = template.preview_data
                    session.add(existing)
            else:
                session.add(template)
            await session.commit()
            if not design_state.template_id:
                await session.refresh(template)
                design_state.template_id = template.id

        ui.notify(t('report.draft_saved'), type='positive')

    async def save_as_action():
        """Abre modal para guardar con nombre definitivo."""
        name_input = None

        async def do_save():
            final_name = name_input.value.strip()
            if not final_name:
                ui.notify(t('report.name_required'), type='warning')
                return

            template = ReportTemplate(
                id=design_state.template_id,
                name=final_name,
                description='',
                structure={'blocks': design_state.blocks},
                input_schema=design_state.input_schema,
                preview_data=design_state.preview_data,
                is_active=True  # Publicado
            )

            async with get_session() as session:
                if design_state.template_id:
                    existing = await session.get(ReportTemplate, design_state.template_id)
                    if existing:
                        existing.name = final_name
                        existing.structure = template.structure
                        existing.input_schema = template.input_schema
                        existing.preview_data = template.preview_data
                        existing.is_active = True
                        session.add(existing)
                else:
                    session.add(template)
                await session.commit()

            dialog.close()
            ui.notify(t('report.saved_success'), type='positive')
            exit_design_mode()

        with ui.dialog() as dialog, ui.card().classes('w-96 p-6'):
            ui.label(t('report.save_action_title')).classes('text-xl font-bold mb-4')
            name_input = ui.input(
                label=t('common.name'),
                value=design_state.provisional_name if not design_state.provisional_name.startswith('Informe_') else ''
            ).classes('w-full mb-4')

            with ui.row().classes('w-full justify-end gap-2'):
                ui.button(t('common.cancel'), on_click=dialog.close).props('flat')
                ui.button(t('common.save'), on_click=do_save).props('color=primary')

        dialog.open()

    # --- LIBRARY MODE ---
    library_state = {'templates': [], 'loaded': False}

    async def load_templates():
        """Carga plantillas disponibles."""
        async with get_session() as session:
            result = await session.exec(select(ReportTemplate))
            library_state['templates'] = result.all()
            library_state['loaded'] = True
            render_page.refresh()

    def render_library():
        """Renderiza modo biblioteca."""
        if not library_state['loaded']:
            with ui.column().classes('w-full h-64 items-center justify-center'):
                ui.spinner(size='lg')
                ui.label(t('common.loading')).classes('text-slate-500')
            ui.timer(0.1, load_templates, once=True)
            return

        resources = []
        for tpl in library_state['templates']:
            resources.append({
                'id': tpl.id,
                'name': tpl.name,
                'description': tpl.description or t('common.no_description'),
                'status': 'published' if tpl.is_active else 'draft',
                'source_module': 'report',
                'doc_path': None,
                'created_at': tpl.created_at,
                'is_favorite': False,
                '_original': tpl
            })

        layout = StandardPageLayout(
            title=t('report.page_title'),
            source_module='report',
            resources=resources,
            on_create=lambda: enter_design_mode_local(None),
            on_edit=lambda r: enter_design_mode_local(r['_original']),
            on_delete=lambda r: None,
            on_execute=lambda r: None,
            help_description=t('report.help_description'),
            input_contract=['input_schema', 'context_data'],
            output_contract=['pdf_report', 'html_report']
        )
        layout.render()

    # --- DESIGN MODE PHASES ---
    def render_structure_phase():
        """Fase 1: Definir estructura del informe (bloques con títulos)."""
        nonlocal block_editor

        with ui.column().classes('w-full max-w-4xl mx-auto gap-4'):
            # Instrucciones
            with ui.row().classes('w-full items-center gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200'):
                ui.icon('info', color='primary')
                ui.label(t('report.structure_instructions')).classes('text-sm text-slate-600')

            # Editor de bloques
            with ui.card().classes('w-full p-4'):
                with ui.scroll_area().classes('w-full h-80'):
                    block_editor = ReportBlockEditor(
                        blocks=design_state.blocks,
                        on_change=lambda blocks: setattr(design_state, 'blocks', blocks)
                    )
                    block_editor.render()

            # Aviso informativo para usar el Copiloto con IA
            with ui.row().classes('w-full items-center gap-3 p-3 bg-blue-50 rounded-lg border border-blue-200'):
                ui.icon('auto_awesome', color='primary')
                with ui.column().classes('flex-grow gap-0'):
                    ui.label(t('report.copilot_suggestion_title')).classes('text-sm font-medium text-blue-700')
                    ui.label(t('report.copilot_suggestion_desc')).classes('text-xs text-blue-600')
                ui.button(
                    t('report.open_copilot'),
                    on_click=lambda: layout_manager.set_active_tab('copilot')
                ).props('flat dense color=primary')

            # Navegación
            with ui.row().classes('w-full justify-end mt-4'):
                can_continue = len(design_state.blocks) > 0
                next_btn = ui.button(
                    t('common.next'),
                    icon='arrow_forward',
                    on_click=go_next_phase
                ).props('color=primary')
                if not can_continue:
                    next_btn.disable()
                    ui.label(t('report.add_blocks_to_continue')).classes('text-sm text-amber-600')

    def render_data_phase():
        """Fase 2: Vincular fuentes de datos a cada bloque."""
        with ui.column().classes('w-full max-w-4xl mx-auto gap-4'):
            # Instrucciones
            with ui.row().classes('w-full items-center gap-3 p-3 bg-slate-50 rounded-lg border border-slate-200'):
                ui.icon('link', color='primary')
                ui.label(t('report.data_binding_instructions')).classes('text-sm text-slate-600')

            # Mostrar fuentes disponibles si estamos en contexto de flujo
            if design_state.available_sources:
                with ui.expansion(t('report.available_sources'), icon='inventory_2').classes('w-full'):
                    with ui.row().classes('w-full flex-wrap gap-2 p-2'):
                        for source in design_state.available_sources:
                            with ui.chip().props('color=primary outline'):
                                ui.icon(source.get('icon', 'data_object'), size='xs')
                                ui.label(source.get('step_name', 'Paso')).classes('text-sm')

            # Lista de bloques que requieren datos
            data_blocks = [b for b in design_state.blocks if b.get('type') in ['table', 'chart']]

            if not data_blocks:
                with ui.card().classes('w-full p-6 text-center'):
                    ui.icon('check_circle', size='xl', color='positive')
                    ui.label(t('report.no_data_blocks')).classes('text-lg text-slate-600 mt-2')
                    ui.label(t('report.no_data_blocks_hint')).classes('text-sm text-slate-400')
            else:
                for block in data_blocks:
                    render_block_data_binding(block)

            # Navegación
            with ui.row().classes('w-full justify-between mt-4'):
                ui.button(t('common.back'), icon='arrow_back', on_click=go_prev_phase).props('flat')
                ui.button(t('common.next'), icon='arrow_forward', on_click=go_next_phase).props('color=primary')

    def render_block_data_binding(block: Dict[str, Any]):
        """Renderiza el selector de fuente de datos para un bloque."""
        block_type = block.get('type')
        block_title = block.get('title') or block.get('id', 'Bloque')
        block_icon = 'table_chart' if block_type == 'table' else 'bar_chart'

        with ui.card().classes('w-full p-4 mb-3'):
            with ui.row().classes('w-full items-center gap-3 mb-3'):
                ui.icon(block_icon, color='primary')
                ui.label(block_title).classes('font-medium text-lg')
                # Indicador de estado
                has_source = block.get('data_source') is not None
                if has_source:
                    ui.chip(t('report.source_linked'), icon='check').props('color=positive dense')
                else:
                    ui.chip(t('report.source_pending'), icon='warning').props('color=warning dense')

            # Selector de fuente
            with ui.column().classes('w-full gap-2'):
                ui.label(t('report.select_data_source')).classes('text-sm font-medium text-slate-600')

                # Opción 1: Pasos anteriores del flujo
                if design_state.available_sources:
                    ui.label(t('report.from_flow_step')).classes('text-xs text-slate-400 mt-2')
                    with ui.row().classes('w-full flex-wrap gap-2'):
                        for source in design_state.available_sources:
                            is_selected = (
                                block.get('data_source') and
                                block['data_source'].get('step_index') == source['step_index']
                            )
                            btn_props = 'color=primary' if is_selected else 'outline color=primary'

                            def select_flow_source(b=block, s=source):
                                b['data_source'] = {
                                    'type': 'flow_step',
                                    'step_index': s['step_index'],
                                    'step_name': s['step_name'],
                                    'output_ref': s['output_ref']
                                }
                                render_page.refresh()

                            ui.button(
                                source.get('step_name', 'Paso'),
                                icon=source.get('icon', 'data_object'),
                                on_click=select_flow_source
                            ).props(btn_props + ' dense')

                # Opción 2: Campo manual
                ui.label(t('report.or_manual_field')).classes('text-xs text-slate-400 mt-3')
                with ui.row().classes('w-full items-center gap-2'):
                    current_field = block.get('data_field', '')
                    field_input = ui.input(
                        value=current_field,
                        placeholder=t('report.data_field_placeholder'),
                        on_change=lambda e, b=block: b.update({'data_field': e.value})
                    ).classes('flex-grow')
                    ui.button(
                        icon='clear',
                        on_click=lambda b=block: (b.pop('data_source', None), b.update({'data_field': ''}), render_page.refresh())
                    ).props('flat dense').tooltip(t('report.clear_source'))

    preview_state = {'mock_data': {}, 'loaded': False}

    async def load_preview_data():
        """Carga datos mock para la vista previa."""
        if design_state.input_schema:
            preview_state['mock_data'] = await generate_mock_data(design_state.input_schema, num_rows=5)
        elif design_state.preview_data:
            preview_state['mock_data'] = design_state.preview_data
        else:
            preview_state['mock_data'] = {}
        preview_state['loaded'] = True
        render_page.refresh()

    def render_preview_phase():
        """Fase 3: Vista previa."""
        nonlocal preview_container

        with ui.column().classes('w-full h-full p-4 gap-4'):
            # Header
            with ui.row().classes('w-full justify-between items-center'):
                ui.label(t('report.preview_title')).classes('text-xl font-bold text-slate-800')

                def refresh_preview():
                    preview_state['loaded'] = False
                    render_page.refresh()

                ui.button(
                    t('report.refresh_preview'),
                    icon='refresh',
                    on_click=refresh_preview
                ).props('flat dense')

            # Vista previa
            with ui.card().classes('w-full flex-grow p-4 bg-slate-50'):
                with ui.scroll_area().classes('w-full h-96'):
                    preview_container = ui.column().classes('w-full gap-4')

                    if not design_state.blocks:
                        with preview_container:
                            ui.label(t('report.add_blocks_hint')).classes('text-gray-500 text-center w-full py-8')
                    elif not preview_state['loaded']:
                        with preview_container:
                            ui.spinner(size='lg')
                        ui.timer(0.1, load_preview_data, once=True)
                    else:
                        with preview_container:
                            for block in design_state.blocks:
                                render_preview_block_sync(block, preview_state['mock_data'])

            # Navegación y guardado
            with ui.row().classes('w-full justify-between mt-4'):
                ui.button(t('common.back'), icon='arrow_back', on_click=go_prev_phase).props('flat')
                with ui.row().classes('gap-2'):
                    ui.button(t('report.save_draft'), icon='drafts', on_click=save_as_draft).props('flat')
                    ui.button(t('report.save_action'), icon='save', on_click=save_as_action).props('color=primary')

    def render_preview_block_sync(block: dict, mock_data: dict):
        """Renderiza un bloque en la vista previa (síncrono)."""
        block_type = block.get("type")

        if block_type == "text":
            content = block.get("content", "")
            for key, value in mock_data.items():
                if isinstance(value, str):
                    content = content.replace(f"{{{{{key}}}}}", value)
            ui.markdown(content).classes('w-full')

        elif block_type == "chart":
            render_chart_preview_sync(block, mock_data)

        elif block_type == "table":
            render_table_preview_sync(block, mock_data)

    def render_chart_preview_sync(block: dict, mock_data: dict):
        """Renderiza gráfico de vista previa."""
        chart_type = block.get("chart_type", "bar")
        data_field = block.get("data_field")
        x_field = block.get("x_field")
        y_field = block.get("y_field")

        chart_data = []
        if data_field:
            chart_data = mock_data.get(data_field, [])

        if not chart_data and mock_data:
            for v in mock_data.values():
                if isinstance(v, list):
                    chart_data = v
                    break

        if not chart_data:
            ui.label(t('report.no_chart_data')).classes('text-gray-400')
            return

        x_data = []
        y_data = []

        if x_field:
            x_data = [item.get(x_field, i) for i, item in enumerate(chart_data) if isinstance(item, dict)]
        else:
            x_data = list(range(len(chart_data)))

        if y_field:
            y_data = [item.get(y_field, 0) for item in chart_data if isinstance(item, dict)]
        else:
            y_data = [item for item in chart_data if isinstance(item, (int, float))]

        options = {
            "title": {"text": block.get("title", "")},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": x_data},
            "yAxis": {"type": "value"},
            "series": [{"type": chart_type, "data": y_data}]
        }

        if chart_type == "pie":
            options = {
                "title": {"text": block.get("title", "")},
                "tooltip": {"trigger": "item"},
                "series": [{
                    "type": "pie",
                    "data": [{"name": str(x), "value": y} for x, y in zip(x_data, y_data)]
                }]
            }

        ui.echart(options).classes('w-full h-64')

    def render_table_preview_sync(block: dict, mock_data: dict):
        """Renderiza tabla de vista previa."""
        data_field = block.get("data_field")
        columns_config = block.get("columns", [])

        table_data = mock_data.get(data_field, [])
        if not table_data:
            for v in mock_data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    table_data = v
                    break

        if not table_data:
            ui.label(t('report.no_table_data')).classes('text-gray-500')
            return

        if columns_config:
            columns = [{"name": c["field"], "label": c.get("header", c["field"]), "field": c["field"]} for c in columns_config]
        else:
            columns = [{"name": k, "label": k, "field": k} for k in table_data[0].keys()]

        ui.table(columns=columns, rows=table_data).classes('w-full')

    # --- MAIN RENDER ---
    @ui.refreshable
    def render_page():
        if page_mode['current'] == 'library':
            render_library()
        else:
            # Modo diseño
            with ui.column().classes('w-full h-full'):
                # Header - Patrón estándar (título azul + subtítulo gris)
                with ui.row().classes('w-full items-center gap-4 mb-2 p-4'):
                    ui.button(icon='arrow_back', on_click=exit_design_mode).props('flat round color=primary')
                    with ui.column().classes('gap-0'):
                        ui.label(t('report.editor_title')).classes('text-3xl font-bold text-primary')
                        ui.label(t('report.editor_subtitle')).classes('text-sm text-slate-500')

                # Contenido según fase
                with ui.column().classes('w-full flex-grow p-4'):
                    if design_state.phase == 'structure':
                        render_structure_phase()
                    elif design_state.phase == 'data':
                        render_data_phase()
                    elif design_state.phase == 'preview':
                        render_preview_phase()

    render_page()

    # Initial mode setup
    if initial_mode == 'design':
        enter_design_mode_local(None)
    elif atom_id:
        # Cargar plantilla existente
        async def load_and_edit():
            async with get_session() as session:
                template = await session.get(ReportTemplate, int(atom_id))
                if template:
                    enter_design_mode_local(template)
        ui.timer(0.1, load_and_edit, once=True)


def report_designer_page():
    """Entry point for main.py routing."""
    from nicegui import app
    initial_mode = app.storage.user.get('report_initial_mode', None)
    atom_id = app.storage.user.get('report_atom_id', None)

    # Clear after reading
    if 'report_initial_mode' in app.storage.user:
        del app.storage.user['report_initial_mode']
    if 'report_atom_id' in app.storage.user:
        del app.storage.user['report_atom_id']

    report_designer_page_content(initial_mode=initial_mode, atom_id=atom_id)

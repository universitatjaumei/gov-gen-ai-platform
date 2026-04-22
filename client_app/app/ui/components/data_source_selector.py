"""
DataSourceSelector - Selector unificado de fuentes de datos para átomos consumidores.

Implementa el patrón de diseño unificado descrito en naming.md:
- Carga manual de archivos (si soportada)
- Selección de átomo del catálogo
- Variable de paso anterior (en modo contextual)

Uso:
    render_data_source_selector(
        consumer_type=StepType.EXTRACTION,
        on_source_selected=handle_source,
        flow_context=state.flow_context
    )
"""
from typing import Any, Callable, Optional, Dict, List
from nicegui import ui
from automatia_shared.enums import StepType
from dataclasses import dataclass
from client_app.app.core.state import state


# ============================================================================
# TIPOS Y ESTRUCTURAS
# ============================================================================

@dataclass
class DataSourceSelection:
    """Representa la fuente de datos seleccionada."""
    source_type: str  # 'manual', 'catalog', 'flow_step'
    # Para manual upload
    file_path: Optional[str] = None
    file_content: Optional[bytes] = None
    file_name: Optional[str] = None
    file_format: Optional[str] = None
    # Para catálogo
    atom_id: Optional[int] = None
    atom_name: Optional[str] = None
    output_contract: Optional[Dict] = None
    # Para paso de flujo
    step_index: Optional[int] = None
    step_name: Optional[str] = None
    output_ref: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'source_type': self.source_type,
            'file_path': self.file_path,
            'file_name': self.file_name,
            'file_format': self.file_format,
            'atom_id': self.atom_id,
            'atom_name': self.atom_name,
            'output_contract': self.output_contract,
            'step_index': self.step_index,
            'step_name': self.step_name,
            'output_ref': self.output_ref,
        }


# ============================================================================
# ICONOS Y COLORES POR TIPO DE ÁTOMO
# ============================================================================

ATOM_TYPE_ICONS: Dict[str, str] = {
    'api_fetch': 'cloud_download',
    'sql_query': 'storage',
    'email': 'email',
    'connection': 'link',
    'extraction': 'content_cut',
    'etl': 'transform',
    'etl_transform': 'swap_horiz',
    'rpa_execute': 'travel_explore',
    'report_generate': 'assessment',
    'folder_watcher': 'folder_open',
    'email_watcher': 'mark_email_unread',
    # --- Nuevos tipos de la taxonomía v2 ---
    'scheduler': 'schedule',
    'folder_scan': 'folder_copy',
    'email_scan': 'inbox',
    'archive_file': 'archive',
    'graphics': 'bar_chart',
    'anonymization': 'security',
    'masking': 'visibility_off',
    'custom_script': 'code',
    'smtp': 'send',
}

ATOM_TYPE_COLORS: Dict[str, str] = {
    'api_fetch': 'blue',
    'sql_query': 'green',
    'email': 'amber',
    'connection': 'cyan',
    'extraction': 'orange',
    'etl': 'teal',
    'etl_transform': 'indigo',
    'rpa_execute': 'pink',
    'report_generate': 'deep-purple',
    'folder_watcher': 'brown',
    'email_watcher': 'amber',
    # --- Nuevos tipos de la taxonomía v2 ---
    'scheduler': 'purple',
    'folder_scan': 'light-blue',
    'email_scan': 'amber',
    'archive_file': 'grey',
    'graphics': 'red',
    'anonymization': 'deep-orange',
    'masking': 'blue-grey',
    'custom_script': 'lime',
    'smtp': 'cyan',
}

FORMAT_ICONS: Dict[str, str] = {
    'pdf': 'picture_as_pdf',
    'docx': 'description',
    'xlsx': 'table_chart',
    'csv': 'grid_on',
    'json': 'data_object',
    'xml': 'code',
    'txt': 'article',
    'image': 'image',
}


def get_atom_icon(atom_type: str) -> str:
    return ATOM_TYPE_ICONS.get(atom_type, 'extension')


def get_atom_color(atom_type: str) -> str:
    return ATOM_TYPE_COLORS.get(atom_type, 'grey')


# ============================================================================
# COMPONENTE PRINCIPAL
# ============================================================================

class DataSourceSelectorState:
    """Estado interno del selector."""
    def __init__(self):
        self.active_tab: str = 'manual'  # 'manual', 'catalog', 'flow_step'
        self.selection: Optional[DataSourceSelection] = None
        self.uploaded_files: List[Dict] = []
        self.uploaded_file: Optional[Any] = None
        self.selected_atom: Optional[Dict] = None
        self.selected_step: Optional[Dict] = None
        # Estado de previsualización de datos
        self.preview_data: Optional[Any] = None   # PreviewResult
        self.is_loading_preview: bool = False
        self.preview_error: Optional[str] = None
        self.refresh_preview_fn: Optional[Any] = None  # Callable para refrescar área
        self.on_preview_loaded: Optional[Any] = None  # Callback cuando preview se carga (para refrescar UI padre)


def render_data_source_selector(
    consumer_type: StepType,
    on_source_selected: Callable[[DataSourceSelection], None],
    flow_context: Optional[Dict[str, Any]] = None,
    available_atoms: Optional[List[Dict[str, Any]]] = None,
    initial_selection: Optional[DataSourceSelection] = None,
    compact: bool = False,
    upload_formats_override: Optional[List[str]] = None,
    selector_state_override: Optional[DataSourceSelectorState] = None
):
    """
    Renderiza el selector unificado de fuentes de datos.

    Args:
        consumer_type: Tipo de átomo consumidor (EXTRACTION, ETL, etc.)
        on_source_selected: Callback cuando se selecciona una fuente
        flow_context: Contexto del flujo (si existe, habilita selección de pasos)
        available_atoms: Lista de átomos del catálogo (opcional, se carga si no se provee)
        initial_selection: Selección inicial (para edición)
        compact: Modo compacto sin descripción detallada
        upload_formats_override: Lista de formatos permitidos (sobrescribe los por defecto)
        selector_state_override: Estado persistente del selector (opcional)
    """
    from client_app.app.services.data_contract_service import data_contract_service

    # Obtener función de traducción ANTES de sobrescribir state
    t = state.i18n.t

    # Estado local o persistente
    selector_state = selector_state_override or DataSourceSelectorState()
    if initial_selection and not selector_state_override:
        selector_state.active_tab = initial_selection.source_type
        selector_state.selection = initial_selection

    # Obtener información de compatibilidad
    supports_manual = data_contract_service.supports_manual_upload(consumer_type)
    # Usar formatos override si se proporcionan, sino los por defecto
    upload_formats = upload_formats_override if upload_formats_override else data_contract_service.get_supported_upload_formats(consumer_type)
    compatible_sources = data_contract_service.get_compatible_sources(consumer_type)

    # Determinar tabs disponibles
    available_tabs = []
    if supports_manual:
        available_tabs.append(('manual', t('data_source.manual_tab', 'Cargar archivo'), 'upload_file'))
    available_tabs.append(('catalog', t('data_source.catalog_tab', 'Del catálogo'), 'apps'))
    if flow_context and flow_context.get('mode') == 'contextual':
        available_tabs.append(('flow_step', t('data_source.flow_tab', 'Paso anterior'), 'account_tree'))

    # Determinar tab inicial
    if flow_context and flow_context.get('mode') == 'contextual':
        selector_state.active_tab = 'flow_step'
    elif not supports_manual:
        selector_state.active_tab = 'catalog'

    # Container principal
    with ui.card().classes('w-full p-4 border border-gray-200 shadow-sm rounded-lg'):
        # Tabs de selección compactas e inline
        @ui.refreshable
        def render_tabs():
            with ui.row().classes('w-full items-center justify-between mb-4'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('input', color='primary', size='md')
                    ui.label(t('data_source.title', 'Fuente de datos')).classes('font-bold text-xl text-primary')

                with ui.tabs().classes('bg-slate-100 rounded-lg p-1').props('dense flat') as tabs:
                    for tab_id, tab_label, tab_icon in available_tabs:
                        ui.tab(tab_id, label=tab_label, icon=tab_icon).classes('rounded-md px-4 text-xs font-bold')

            with ui.tab_panels(tabs, value=selector_state.active_tab).classes('w-full bg-transparent'):
                # Panel: Carga manual
                if supports_manual:
                    with ui.tab_panel('manual').classes('p-0'):
                        _render_manual_upload_panel(
                            upload_formats=upload_formats,
                            selector_state=selector_state,
                            on_source_selected=on_source_selected
                        )

                # Panel: Catálogo de átomos
                with ui.tab_panel('catalog').classes('p-0'):
                    _render_catalog_panel(
                        compatible_sources=compatible_sources,
                        available_atoms=available_atoms,
                        selector_state=selector_state,
                        on_source_selected=on_source_selected
                    )

                # Panel: Paso del flujo
                if flow_context and flow_context.get('mode') == 'contextual':
                    with ui.tab_panel('flow_step').classes('p-0'):
                        _render_flow_step_panel(
                            flow_context=flow_context,
                            compatible_sources=compatible_sources,
                            selector_state=selector_state,
                            on_source_selected=on_source_selected
                        )

        render_tabs()

        # Mostrar selección actual
        if selector_state.selection and selector_state.active_tab != 'manual':
            _render_current_selection(selector_state.selection)


def _render_manual_upload_panel(
    upload_formats: List[str],
    selector_state: DataSourceSelectorState,
    on_source_selected: Callable[[DataSourceSelection], None]
):
    """Renderiza el panel de carga manual de archivos."""
    t = state.i18n.t

    with ui.column().classes('w-full gap-1 py-1'):
        # Formatos soportados
        with ui.row().classes('items-center gap-2 flex-wrap'):
            ui.label(t('data_source.formats_label', 'Formatos:')).classes('text-sm text-gray-600')
            for fmt in upload_formats:
                icon = FORMAT_ICONS.get(fmt, 'insert_drive_file')
                ui.chip(fmt.upper(), icon=icon).props('dense size=sm outline color=grey')

        # Zona de upload
        async def handle_upload(e):
            try:
                # Normalization to avoid issues
                import re
                file_name = re.sub(r'[^a-zA-Z0-9\._-]', '_', e.file.name)
                
                content = await e.file.read()
                if not isinstance(content, (bytes, bytearray)):
                     ui.notify(f"Error: El contenido del archivo no es válido ({type(content).__name__}).", type='negative')
                     return
                     
                file_ext = file_name.split('.')[-1].lower() if '.' in file_name else ''

                selection = DataSourceSelection(
                    source_type='manual',
                    file_content=content,
                    file_name=file_name,
                    file_format=file_ext
                )
                selector_state.selection = selection
                
                file_info = {'name': file_name, 'size': len(content)}
                if not hasattr(selector_state, 'uploaded_files'):
                    selector_state.uploaded_files = []
                selector_state.uploaded_files.append(file_info)
                # Ensure deterministic behavior by sorting alphabetically
                selector_state.uploaded_files.sort(key=lambda x: x['name'])
                selector_state.uploaded_file = file_info  # For backward compatibility
                
                import inspect
                if inspect.iscoroutinefunction(on_source_selected):
                    await on_source_selected(selection)
                else:
                    res = on_source_selected(selection)
                    if inspect.isawaitable(res):
                        await res
                # Refrescar la lista de archivos
                render_uploaded_files.refresh()
            except Exception as ex:
                ui.notify(f"Error en carga: {ex}", type='negative')

        with ui.card().classes(
            'w-full border-2 border-dashed border-slate-200 bg-slate-50 '
            'hover:border-primary hover:bg-blue-50 transition-all rounded-xl shadow-none'
        ):
            with ui.column().classes('w-full items-center justify-center p-4 gap-2'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('cloud_upload', size='md', color='primary')
                    ui.label(t('data_source.upload_hint', 'Arrastra un archivo aquí o haz clic para seleccionar')).classes(
                        'text-slate-500 font-medium'
                    )

                # Accept string basado en formatos
                accept_str = ','.join([f'.{fmt}' for fmt in upload_formats])
                ui.upload(
                    on_upload=handle_upload,
                    auto_upload=True,
                ).props(f'accept="{accept_str}" flat bordered dense multiple').classes('w-full h-16')

        def _clear_all_selections():
            selector_state.selection = None
            selector_state.uploaded_files = []
            selector_state.uploaded_file = None
            render_uploaded_files.refresh()

        async def _clear_one_selection(idx):
            import asyncio
            if hasattr(selector_state, 'uploaded_files') and idx < len(selector_state.uploaded_files):
                selector_state.uploaded_files.pop(idx)
            if not selector_state.uploaded_files:
                selector_state.selection = None
                selector_state.uploaded_file = None
            # Permitir que el evento del botón se complete antes de refrescar
            await asyncio.sleep(0)
            render_uploaded_files.refresh()

        # Archivos cargados con refreshable local para evitar errores de ciclo de vida
        @ui.refreshable
        def render_uploaded_files():
            if hasattr(selector_state, 'uploaded_files') and selector_state.uploaded_files:
                with ui.column().classes('w-full gap-1 mt-2'):
                    for i, file_info in enumerate(selector_state.uploaded_files):
                        is_first = (i == 0)
                        bg_color = 'bg-blue-50 border-blue-200' if is_first else 'bg-green-50 border-green-200'
                        icon_color = 'blue' if is_first else 'green'
                        icon_name = 'stars' if is_first else 'check_circle'

                        with ui.card().classes(f'w-full p-2 {bg_color} border shadow-none'):
                            with ui.row().classes('items-center gap-3 w-full'):
                                ui.icon(icon_name, color=icon_color)
                                with ui.column().classes('flex-1 gap-0'):
                                    ui.label(file_info['name']).classes('font-medium text-slate-800')
                                    if is_first:
                                        ui.label('Documento guía (muestra para la programación)').classes('text-xs font-bold text-blue-700')
                                    ui.label(f"{file_info['size']:,} bytes").classes(
                                        'text-xs text-gray-500'
                                    )
                                ui.button(icon='close', on_click=lambda idx=i: _clear_one_selection(idx)).props(
                                    'flat round dense color=grey'
                                )

        render_uploaded_files()


def _render_catalog_panel(
    compatible_sources: List[StepType],
    available_atoms: Optional[List[Dict]],
    selector_state: DataSourceSelectorState,
    on_source_selected: Callable[[DataSourceSelection], None]
):
    """Renderiza el panel de selección desde catálogo."""
    import asyncio
    from client_app.app.services.atom_service import atom_service
    t = state.i18n.t

    # Estado local para átomos cargados
    loaded_atoms: List[Dict] = []
    is_loading = True
    search_text = ''

    with ui.column().classes('w-full gap-3 py-3'):
        # Info sobre tipos compatibles
        with ui.row().classes('items-center gap-2 flex-wrap mb-2'):
            ui.label(t('data_source.compatible_with', 'Compatible con:')).classes('text-sm text-gray-600')
            for src_type in compatible_sources[:5]:  # Mostrar máximo 5
                icon = get_atom_icon(src_type.value)
                color = get_atom_color(src_type.value)
                ui.chip(src_type.value.replace('_', ' ').title(), icon=icon).props(
                    f'dense size=sm outline color={color}'
                )
            if len(compatible_sources) > 5:
                ui.label(f'+{len(compatible_sources) - 5} más').classes('text-xs text-gray-400')

        # Búsqueda
        search_input = ui.input(placeholder=t('data_source.search_placeholder', 'Buscar acción...')).props(
            'dense outlined'
        ).classes('w-full')

        # Contenedor para lista de átomos
        @ui.refreshable
        def render_atoms_list():
            nonlocal is_loading, loaded_atoms, search_text

            if is_loading:
                with ui.card().classes('w-full p-4 bg-gray-50'):
                    with ui.column().classes('items-center gap-2'):
                        ui.icon('search', size='lg', color='grey')
                        ui.label(t('data_source.loading_catalog', 'Cargando acciones del catálogo...')).classes('text-gray-500')
                        ui.spinner()
                return

            # Filtrar por búsqueda y compatibilidad
            filtered_atoms = []
            for atom in loaded_atoms:
                atom_type = atom.get('atom_type', '')
                atom_name = atom.get('name', '').lower()

                # Filtrar por tipo compatible
                try:
                    if StepType(atom_type) not in compatible_sources:
                        continue
                except ValueError:
                    continue

                # Filtrar por texto de búsqueda
                if search_text and search_text.lower() not in atom_name:
                    continue

                filtered_atoms.append(atom)

            if not filtered_atoms:
                with ui.card().classes('w-full p-4 bg-amber-50 border border-amber-200'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('info', color='amber')
                        ui.label(t('data_source.no_compatible', 'No hay acciones compatibles en el catálogo')).classes('text-amber-800')
                return

            with ui.scroll_area().classes('w-full h-64 border rounded'):
                with ui.column().classes('w-full gap-2 p-2'):
                    for atom in filtered_atoms:
                        _render_atom_card(atom, selector_state, on_source_selected)

        # Handler para búsqueda
        def on_search_change(e):
            nonlocal search_text
            search_text = e.value or ''
            render_atoms_list.refresh()

        search_input.on('update:model-value', on_search_change)

        # Cargar átomos
        async def load_atoms():
            nonlocal is_loading, loaded_atoms

            if available_atoms is not None:
                # Usar átomos proporcionados
                loaded_atoms = available_atoms
            else:
                # Cargar desde el servicio
                try:
                    atoms_db = await atom_service.list_atoms()
                    loaded_atoms = [
                        {
                            'id': a.id,
                            'name': a.name,
                            'atom_type': a.atom_type.value if hasattr(a.atom_type, 'value') else str(a.atom_type),
                            'description': a.description or '',
                            'output_contract': a.output_contract or {}
                        }
                        for a in atoms_db
                    ]
                except Exception as e:
                    print(f"Error loading atoms: {e}")
                    loaded_atoms = []

            is_loading = False
            render_atoms_list.refresh()

        # Renderizar lista inicial y disparar carga
        render_atoms_list()
        asyncio.create_task(load_atoms())

        # Área de preview para el átomo seleccionado
        @ui.refreshable
        def catalog_preview_area():
            _render_preview_area(selector_state)

        selector_state.refresh_preview_fn = catalog_preview_area.refresh
        catalog_preview_area()


def _render_atom_card(
    atom: Dict,
    selector_state: DataSourceSelectorState,
    on_source_selected: Callable[[DataSourceSelection], None]
):
    """Renderiza una card de átomo seleccionable."""
    atom_id = atom.get('id')
    atom_name = atom.get('name', 'Sin nombre')
    atom_type = atom.get('atom_type', '')
    description = atom.get('description', '')
    output_contract = atom.get('output_contract', {})

    icon = get_atom_icon(atom_type)
    color = get_atom_color(atom_type)
    is_selected = selector_state.selected_atom and selector_state.selected_atom.get('id') == atom_id

    card_classes = 'w-full p-3 cursor-pointer transition-all hover:shadow-md'
    if is_selected:
        card_classes += ' border-2 border-primary bg-blue-50'
    else:
        card_classes += ' border border-gray-200 hover:border-primary'

    async def select_atom():
        import asyncio
        import inspect
        from client_app.app.services.preview_data_service import preview_data_service

        selector_state.selected_atom = atom
        selection = DataSourceSelection(
            source_type='catalog',
            atom_id=atom_id,
            atom_name=atom_name,
            output_contract=output_contract
        )
        selector_state.selection = selection

        # Manejar callback async/sync correctamente
        if inspect.iscoroutinefunction(on_source_selected):
            await on_source_selected(selection)
        else:
            res = on_source_selected(selection)
            if inspect.isawaitable(res):
                await res

        # Cargar preview del átomo de forma asíncrona
        async def _load_atom_preview():
            selector_state.preview_data = None
            selector_state.preview_error = None
            selector_state.is_loading_preview = True
            if selector_state.refresh_preview_fn:
                selector_state.refresh_preview_fn()
            try:
                if atom_id:
                    # Tipos de átomos que producen archivos y necesitan ejecución real
                    file_producing_types = {'folder_scan', 'folder_watcher', 'email_scan', 'email_watcher'}
                    atom_type_lower = str(atom_type).lower() if atom_type else ''

                    if atom_type_lower in file_producing_types:
                        # Ejecutar el átomo realmente para obtener lista de archivos
                        result = await preview_data_service.execute_atom_for_preview(atom_id, max_rows=15)
                    else:
                        # Para otros tipos, usar datos de ejemplo o mock
                        result = await preview_data_service.get_preview_from_atom(atom_id, max_rows=8)
                else:
                    # Sin ID (átomo proporcionado externamente): mock desde output_contract
                    contract = output_contract if isinstance(output_contract, dict) else {}
                    result = await preview_data_service.generate_mock_from_contract(contract, num_rows=5)
                if result.success:
                    selector_state.preview_data = result
                else:
                    selector_state.preview_error = result.error
            except Exception as ex:
                selector_state.preview_error = f"Error al cargar datos de ejemplo: {str(ex)}"
            finally:
                selector_state.is_loading_preview = False
                if selector_state.refresh_preview_fn:
                    selector_state.refresh_preview_fn()
                # Notificar al componente padre que el preview está listo
                if selector_state.on_preview_loaded:
                    selector_state.on_preview_loaded()

        asyncio.create_task(_load_atom_preview())

    with ui.card().classes(card_classes).on('click', select_atom):
        with ui.row().classes('items-center gap-3 w-full'):
            ui.icon(icon, color=color).classes('text-xl')
            with ui.column().classes('flex-1 gap-0'):
                ui.label(atom_name).classes('font-medium')
                if description:
                    ui.label(description[:50] + ('...' if len(description) > 50 else '')).classes(
                        'text-xs text-gray-500'
                    )
            ui.chip(atom_type.replace('_', ' ').title()).props(f'dense size=sm color={color}')
            if is_selected:
                ui.icon('check_circle', color='primary')


def _render_flow_step_panel(
    flow_context: Dict[str, Any],
    compatible_sources: List[StepType],
    selector_state: DataSourceSelectorState,
    on_source_selected: Callable[[DataSourceSelection], None]
):
    """Renderiza el panel de selección de paso del flujo con previsualización."""
    import asyncio
    from client_app.app.services.preview_data_service import preview_data_service

    available_vars = flow_context.get('available_variables', [])
    flow_name = flow_context.get('flow_name', 'Flujo')
    flow_id = flow_context.get('flow_id', 0)
    all_steps_config = flow_context.get('all_steps_config', [])

    with ui.column().classes('w-full gap-3 py-3'):
        # Header con contexto
        with ui.card().classes('w-full p-3 bg-blue-50 border border-blue-200'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('account_tree', color='blue')
                ui.label(f'Flujo: {flow_name}').classes('font-medium text-blue-800')
                ui.label(f'({len(available_vars)} pasos anteriores)').classes(
                    'text-sm text-blue-600'
                )

        if not available_vars:
            with ui.card().classes('w-full p-4 bg-amber-50 border border-amber-200'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('warning', color='amber')
                    ui.label('Este es el primer paso del flujo. No hay pasos anteriores.').classes(
                        'text-amber-800'
                    )
        else:
            # Lista de pasos disponibles
            with ui.column().classes('w-full gap-2'):
                ui.label('Selecciona el paso que provee los datos:').classes(
                    'text-sm text-gray-600 font-medium'
                )

                for var in available_vars:
                    step_type = var.get('step_type', '')
                    try:
                        if StepType(step_type) not in compatible_sources:
                            pass
                    except ValueError:
                        continue

                    _render_step_card(
                        var, selector_state, on_source_selected,
                        flow_id=flow_id,
                        all_steps_config=all_steps_config,
                        preview_service=preview_data_service
                    )

        # Área de previsualización (compartida para todos los pasos)
        @ui.refreshable
        def preview_area():
            _render_preview_area(selector_state)

        selector_state.refresh_preview_fn = preview_area.refresh
        preview_area()


def _render_step_card(
    step_var: Dict,
    selector_state: DataSourceSelectorState,
    on_source_selected: Callable[[DataSourceSelection], None],
    flow_id: int = 0,
    all_steps_config: Optional[List[Dict]] = None,
    preview_service: Optional[Any] = None
):
    """Renderiza una card de paso seleccionable con botón de previsualización."""
    import asyncio

    step_index = step_var.get('step_index')
    step_name = step_var.get('step_name', f'Paso {step_index + 1}')
    step_type = step_var.get('step_type', '')
    output_ref = step_var.get('output_ref', '')
    outputs = step_var.get('outputs', [])

    icon = get_atom_icon(step_type)
    color = get_atom_color(step_type)
    is_selected = selector_state.selected_step and selector_state.selected_step.get('step_index') == step_index

    card_classes = 'w-full p-3 cursor-pointer transition-all hover:shadow-md'
    if is_selected:
        card_classes += ' border-2 border-primary bg-blue-50'
    else:
        card_classes += ' border border-gray-200 hover:border-primary'

    async def select_step():
        import inspect
        selector_state.selected_step = step_var
        selection = DataSourceSelection(
            source_type='flow_step',
            step_index=step_index,
            step_name=step_name,
            output_ref=output_ref
        )
        selector_state.selection = selection

        # Manejar callback async/sync correctamente
        if inspect.iscoroutinefunction(on_source_selected):
            await on_source_selected(selection)
        else:
            res = on_source_selected(selection)
            if inspect.isawaitable(res):
                await res

    async def load_preview(e=None):
        """Ejecuta el paso real y carga el preview de datos."""
        import logging
        log = logging.getLogger(__name__)

        # Primero seleccionar el paso
        await select_step()

        # Limpiar estado anterior
        selector_state.preview_data = None
        selector_state.preview_error = None
        selector_state.is_loading_preview = True
        if selector_state.refresh_preview_fn:
            selector_state.refresh_preview_fn()

        try:
            if preview_service and all_steps_config:
                result = await preview_service.get_preview_from_previous_step(
                    flow_id=flow_id,
                    source_step_index=step_index,
                    all_steps_config=all_steps_config,
                    max_rows=15
                )
                log.info(f"[DataPreview] result.success={result.success}, "
                         f"columns={result.columns[:3] if result.columns else []}, "
                         f"rows_count={len(result.rows)}, "
                         f"error={result.error}")
                if result.success:
                    selector_state.preview_data = result
                else:
                    selector_state.preview_error = result.error
            else:
                selector_state.preview_error = "Configuración de pasos no disponible para previsualización."
        except Exception as ex:
            import traceback
            log.error(f"[DataPreview] Exception: {traceback.format_exc()}")
            selector_state.preview_error = f"Error inesperado: {str(ex)}"
        finally:
            selector_state.is_loading_preview = False
            log.info(f"[DataPreview] Final state: preview_data={selector_state.preview_data is not None}, "
                     f"preview_error={selector_state.preview_error}, "
                     f"refresh_fn={selector_state.refresh_preview_fn is not None}")
            if selector_state.refresh_preview_fn:
                selector_state.refresh_preview_fn()
            # Notificar al componente padre que el preview está listo
            if selector_state.on_preview_loaded:
                selector_state.on_preview_loaded()

    with ui.card().classes(card_classes):
        with ui.row().classes('items-center gap-3 w-full'):
            # Número de paso
            with ui.badge(str(step_index + 1), color='grey').classes('text-sm'):
                pass

            ui.icon(icon, color=color).classes('text-xl')

            with ui.column().classes('flex-1 gap-0'):
                ui.label(step_name).classes('font-medium')
                ui.label(step_type.replace('_', ' ').title()).classes('text-xs text-gray-500')

            # Mostrar outputs disponibles
            if outputs:
                ui.chip(f'{len(outputs)} campos', icon='data_object').props('dense size=sm outline')

            if is_selected:
                ui.icon('check_circle', color='primary')

            # Botón para seleccionar y cargar preview
            btn = ui.button(
                'Cargar datos',
                icon='play_arrow'
            ).props('dense flat color=primary size=sm').classes('ml-auto')
            
            # Usar 'click.stop' para ejecutar la función asíncrona sin propagar y sin create_task que pierde el slot
            btn.on('click.stop', load_preview)



def _render_preview_area(selector_state: DataSourceSelectorState) -> None:
    """
    Renderiza el área de previsualización de datos.
    Muestra: spinner si está cargando, tabla si hay datos, card de error si falló.
    """
    if selector_state.is_loading_preview:
        with ui.card().classes('w-full p-4 bg-slate-50 border border-slate-200 mt-3'):
            with ui.row().classes('items-center gap-3'):
                ui.spinner('dots', size='md', color='primary')
                with ui.column().classes('gap-0'):
                    ui.label('Ejecutando paso y cargando datos...').classes('font-medium text-slate-700')
                    ui.label(
                        '⚠️ Se está ejecutando código real del paso (llamadas a APIs, queries, etc.)'
                    ).classes('text-xs text-amber-600')
        return

    if selector_state.preview_error:
        with ui.card().classes('w-full p-3 bg-red-50 border border-red-200 mt-3'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('error_outline', color='red')
                with ui.column().classes('flex-1 gap-0'):
                    ui.label('Error al cargar el preview').classes('font-medium text-red-800')
                    ui.label(selector_state.preview_error).classes('text-xs text-red-600 break-words')
        return

    if selector_state.preview_data:
        _render_data_preview(selector_state.preview_data)


def _render_file_preview(preview: Any, file_rows: list) -> None:
    """
    Renderiza una vista especial para previsualización de archivos.
    Muestra los archivos con iconos apropiados según su extensión.
    """
    # Detectar archivos PDF
    pdf_files = []
    other_files = []

    for row in file_rows:
        file_path = row.get('path', row.get('file_path', ''))
        file_name = row.get('name', row.get('file_name', row.get('filename', '')))
        extension = row.get('extension', '')

        if not extension and file_path:
            extension = file_path.split('.')[-1] if '.' in file_path else ''

        file_info = {
            'path': file_path,
            'name': file_name or file_path.split('\\')[-1].split('/')[-1],
            'extension': extension.lower().strip('.')
        }

        if file_info['extension'] == 'pdf':
            pdf_files.append(file_info)
        else:
            other_files.append(file_info)

    total_files = len(file_rows)
    pdf_count = len(pdf_files)

    # Badge según origen
    source_badges = {
        'executed_step': ('bolt', 'positive', 'Datos reales'),
        'sample_data': ('save', 'info', 'Datos de ejemplo'),
        'mock_data': ('auto_awesome', 'grey', 'Datos generados'),
    }
    source_type = getattr(preview, 'source_type', 'unknown')
    icon_name, badge_color, badge_label = source_badges.get(
        source_type, ('help', 'grey', 'Datos')
    )

    with ui.card().classes('w-full p-3 bg-green-50 border border-green-200 mt-3'):
        # Header
        with ui.row().classes('items-center gap-2 mb-2 flex-wrap'):
            ui.icon('folder_open', color='green')
            ui.label('Archivos disponibles').classes('font-bold text-green-800')
            ui.chip(f'{total_files} archivo(s)', icon='insert_drive_file').props('dense size=sm outline color=green')
            if pdf_count > 0:
                ui.chip(f'{pdf_count} PDF', icon='picture_as_pdf').props('dense size=sm color=red')
            ui.chip(badge_label, icon=icon_name).props(f'dense size=sm color={badge_color}')

        # Lista de archivos (mostrar hasta 8)
        with ui.column().classes('w-full gap-1'):
            display_files = (pdf_files + other_files)[:8]
            for f in display_files:
                ext = f['extension']
                icon = 'picture_as_pdf' if ext == 'pdf' else 'insert_drive_file'
                icon_color = 'red' if ext == 'pdf' else 'grey'

                with ui.row().classes('items-center gap-2 py-1 px-2 bg-white rounded'):
                    ui.icon(icon, color=icon_color, size='sm')
                    ui.label(f['name']).classes('text-xs text-slate-700 truncate flex-1')
                    if ext:
                        ui.chip(ext.upper()).props('dense size=xs outline color=grey')

            if total_files > 8:
                ui.label(f'... y {total_files - 8} archivo(s) más').classes('text-xs text-slate-500 italic mt-1')


def _render_data_preview(preview: Any) -> None:
    """
    Renderiza la tabla de previsualización de datos con metadatos.
    Soporta tanto datos tabulares como listas de archivos.
    """
    if not preview:
        with ui.card().classes('w-full p-3 bg-slate-50 border border-slate-200 mt-3'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('info', color='grey')
                ui.label('No hay datos de previsualización disponibles.').classes('text-sm text-slate-600')
        return

    # Verificar si hay datos de archivos en el preview (aunque no sea tabular)
    has_file_data = False
    file_rows = []

    if preview.columns and preview.rows:
        # Detectar si los datos contienen información de archivos
        file_columns = {'path', 'file_path', 'name', 'file_name', 'filename', 'extension'}
        if any(col.lower() in file_columns for col in preview.columns):
            has_file_data = True
            file_rows = preview.rows

    # Si no hay columnas pero hay metadata con información de archivos
    if not preview.columns:
        meta = getattr(preview, 'metadata', {})
        step_type = meta.get('step_type', '')

        # Tipos que producen archivos
        file_producing_types = {'folder_scan', 'folder_watcher', 'email_scan', 'email_watcher'}

        if step_type.lower() in file_producing_types:
            # Mostrar mensaje informativo para fuentes de archivos
            with ui.card().classes('w-full p-3 bg-blue-50 border border-blue-200 mt-3'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('folder_open', color='blue')
                    ui.label(
                        'Este paso produce archivos. Los archivos se procesarán cuando el flujo se ejecute.'
                    ).classes('text-sm text-blue-700')
            return

        # Para otros tipos, mostrar el mensaje genérico
        with ui.card().classes('w-full p-3 bg-slate-50 border border-slate-200 mt-3'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('info', color='grey')
                source_label = {
                    'executed_step': 'datos reales del paso',
                    'sample_data': 'datos de ejemplo de la acción',
                    'mock_data': 'datos de ejemplo generados'
                }.get(getattr(preview, 'source_type', ''), 'datos')
                ui.label(
                    f'El paso se ejecutó correctamente ({source_label}) pero no retornó datos tabulares.'
                ).classes('text-sm text-slate-600')
        return

    # Si hay datos de archivos, mostrar vista especial de archivos
    if has_file_data:
        _render_file_preview(preview, file_rows)
        return

    # Badge según origen
    source_badges = {
        'executed_step': ('bolt', 'positive', 'Datos reales'),
        'sample_data': ('save', 'info', 'Datos de ejemplo guardados'),
        'mock_data': ('auto_awesome', 'grey', 'Datos de ejemplo generados'),
    }
    source_type = getattr(preview, 'source_type', 'unknown')
    icon_name, badge_color, badge_label = source_badges.get(
        source_type, ('help', 'grey', 'Datos')
    )

    with ui.card().classes('w-full p-3 bg-slate-50 border border-slate-200 mt-3'):
        # Header
        with ui.row().classes('items-center gap-2 mb-2 flex-wrap'):
            ui.icon('table_chart', color='primary')
            ui.label('Vista previa de datos').classes('font-bold text-slate-700')
            ui.chip(
                f'{preview.preview_rows} de {preview.row_count} filas',
                icon='format_list_numbered'
            ).props('dense size=sm outline color=primary')
            ui.chip(badge_label, icon=icon_name).props(f'dense size=sm color={badge_color}')
            if getattr(preview, 'is_real_execution', False):
                ui.chip('Ejecución real', icon='bolt').props('dense size=sm color=amber')

        # Tabla
        if preview.rows and preview.columns:
            table_columns = [
                {'name': col, 'label': col, 'field': col, 'align': 'left', 'sortable': True}
                for col in preview.columns
            ]
            ui.table(
                columns=table_columns,
                rows=preview.rows,
                row_key=preview.columns[0] if preview.columns else 'id'
            ).classes('w-full').props('dense flat bordered')

        # Metadatos colapsables
        meta = getattr(preview, 'metadata', {})
        if meta:
            with ui.expansion('Metadatos', icon='info_outline').classes('mt-1 text-xs'):
                with ui.column().classes('gap-1'):
                    for key, value in meta.items():
                        if key != 'dtypes':
                            ui.label(f'{key}: {value}').classes('text-xs text-gray-500')


def _render_current_selection(selection: DataSourceSelection):
    """Muestra un resumen de la selección actual."""
    with ui.card().classes('w-full p-2 bg-green-50 border border-green-200 mt-1'):
        with ui.row().classes('items-center gap-3 w-full'):
            ui.icon('check_circle', color='green').classes('text-lg')

            if selection.source_type == 'manual':
                ui.label(f'Archivo: {selection.file_name}').classes('font-medium text-green-800')
            elif selection.source_type == 'catalog':
                ui.label(f'Acción: {selection.atom_name}').classes('font-medium text-green-800')
            elif selection.source_type == 'flow_step':
                ui.label(f'Paso {selection.step_index + 1}: {selection.step_name}').classes(
                    'font-medium text-green-800'
                )


def _clear_selection(selector_state: DataSourceSelectorState):
    """Limpia la selección actual y el estado de preview."""
    selector_state.selection = None
    selector_state.uploaded_file = None
    selector_state.selected_atom = None
    selector_state.selected_step = None
    selector_state.preview_data = None
    selector_state.preview_error = None
    selector_state.is_loading_preview = False


# ============================================================================
# VERSIÓN COMPACTA PARA INLINE
# ============================================================================

def render_compact_source_indicator(
    selection: Optional[DataSourceSelection],
    on_change: Callable[[], None]
) -> None:
    """
    Renderiza un indicador compacto de la fuente seleccionada con botón para cambiar.

    Args:
        selection: Selección actual (o None si no hay)
        on_change: Callback para abrir el selector completo
    """
    t = state.i18n.t

    if not selection:
        with ui.button(t('data_source.select_source_btn', 'Seleccionar fuente de datos'), icon='add', on_click=on_change).props(
            'outline color=primary'
        ).classes('w-full'):
            pass
        return

    with ui.card().classes('w-full p-2 bg-gray-50'):
        with ui.row().classes('items-center gap-2 w-full'):
            if selection.source_type == 'manual':
                ui.icon('upload_file', color='blue')
                ui.label(selection.file_name or 'Archivo cargado').classes('flex-1 text-sm')
            elif selection.source_type == 'catalog':
                ui.icon('apps', color='green')
                ui.label(selection.atom_name or 'Acción del catálogo').classes('flex-1 text-sm')
            elif selection.source_type == 'flow_step':
                ui.icon('account_tree', color='purple')
                ui.label(f'Paso {selection.step_index + 1}: {selection.step_name}').classes(
                    'flex-1 text-sm'
                )

            ui.button(icon='edit', on_click=on_change).props('flat round dense size=sm')

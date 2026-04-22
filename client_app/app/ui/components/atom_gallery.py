"""
Shared Atom Gallery Component - Galería unificada de selección de átomos.

Este componente se usa tanto en:
- flows_page.py (al añadir un paso al flujo)
- atoms_page.py (al crear un nuevo átomo)

REFACTORIZADO (Fase 3 Taxonomía):
- Usa ATOM_CATEGORIES_V2 con las 4 capas funcionales
- Muestra iconos de categoría (bolt, login, psychology, logout)
- Soporte para selección de subtipos CONNECTION
"""
from typing import Optional, Callable
from nicegui import ui
from automatia_shared.enums import StepType, AtomCategory

from client_app.app.config.atom_catalog import (
    ATOM_CATEGORIES_V2,
    CATEGORY_ICONS,
    get_category_label,
    get_atom_metadata,
    get_category_for_step_type,
    CONNECTION_METADATA,
)
from client_app.app.services.resource_listing_service import resource_listing_service
from client_app.app.core.state import state
from client_app.app.services.atom_service import atom_service
from client_app.app.services.api_connection_service import api_connection_service

async def render_connection_subtypes_section(
    on_select: Callable[[StepType], None],
    wizard_mode: bool,
    closer: Optional[Callable],
    gallery_refreshable
):
    """
    Renderiza la vista de subtipos de conexión.

    Args:
        on_select: Callback al seleccionar (recibe step_type, subtype)
        wizard_mode: Si está en modo wizard
        closer: Función para cerrar el diálogo
        gallery_refreshable: Referencia al refreshable para volver atrás
    """
    with ui.column().classes('w-full gap-4'):
        # Header con botón atrás
        with ui.row().classes('w-full items-center gap-2 mb-4'):
            def go_back():
                state.wizard_show_connection_subtypes = False
                gallery_refreshable.refresh()

            ui.button(icon='arrow_back', on_click=go_back).props('flat dense round')
            ui.label(state.i18n.t('gallery.select_connection_type', 'Selecciona el tipo de conexión')).classes('text-lg font-bold text-slate-700')

        # Grid de subtipos
        with ui.grid().classes('w-full grid-cols-2 gap-3'):
            for subtype, metadata in CONNECTION_METADATA.items():
                # Handler para subtipo
                def make_subtype_handler(st):
                    async def handler():
                        # Guardar en state
                        state.wizard_initial_step_type = StepType.CONNECTION
                        state.wizard_initial_subtype = st
                        state.wizard_show_connection_subtypes = False

                        # Llamar callback con subtype
                        try:
                            result = on_select(StepType.CONNECTION, st)
                        except TypeError:
                            # Callback antiguo solo acepta step_type
                            result = on_select(StepType.CONNECTION)

                        if hasattr(result, '__await__'):
                            await result

                        if closer and not wizard_mode:
                            closer()
                    return handler

                # Card del subtipo
                with ui.card().classes(
                    f'p-4 hover:shadow-lg transition-all cursor-pointer '
                    f'border-l-4 border-{metadata.color}-500 group'
                ).props('flat bordered').on('click', make_subtype_handler(subtype)):
                    with ui.row().classes('items-center gap-3'):
                        ui.icon(metadata.icon, size='md').classes(f'text-{metadata.color}-600')
                        with ui.column().classes('gap-0 flex-1'):
                            ui.label(metadata.label).classes('font-bold text-slate-700')
                            ui.label(metadata.description).classes('text-xs text-gray-500 line-clamp-2')


async def render_atom_gallery(
    container: ui.element,
    on_select: Callable[[StepType], None],
    show_library: bool = True,
    search_input: Optional[ui.input] = None,
    wizard_mode: bool = False,
    closer: Optional[Callable] = None,
    filter_step_type: Optional[StepType] = None
):
    """
    Renderiza la galería unificada de átomos dentro de un contenedor dedicado.
    Organiza los recursos usando la nueva taxonomía de 4 capas funcionales.

    Args:
        container: Elemento NiceGUI donde se inyectará la galería.
        on_select: Callback invocado al elegir un átomo (recibe StepType).
        show_library: Si es True, incluye la sección de recursos personales.
        search_input: Entrada de texto opcional para filtrado en tiempo real.
        wizard_mode: Indica si se está usando dentro de un flujo paso a paso.
        closer: Función opcional para cerrar diálogos contenedores.
        filter_step_type: Si se especifica, filtra para mostrar solo acciones de este tipo.
    """
    with container:
        # SEARCH STATE
        search_state = {'query': ''}

        # If external search input provided, bind to it.
        if search_input:
            search_input.on('input', lambda e: [search_state.update({'query': e.value.lower()}), gallery_content.refresh()])

        @ui.refreshable
        async def gallery_content():
            # Si estamos mostrando subtipos de conexión
            if state.wizard_show_connection_subtypes:
                await render_connection_subtypes_section(on_select, wizard_mode, closer, gallery_content)
                return
            query = search_state['query']
            t = state.i18n.t  # Definir t aquí para que esté disponible en todas las secciones

            # Nombre del tipo para filtrado (si hay filtro activo)
            # filter_step_type puede ser StepType enum, string (name) o string (value)
            # Normalizamos a MAYÚSCULAS para comparación consistente
            if filter_step_type:
                if hasattr(filter_step_type, 'name'):
                    # Es un enum StepType
                    filter_type_name = filter_step_type.name.upper()
                else:
                    # Es un string - puede ser 'api_fetch' (value) o 'API_FETCH' (name)
                    filter_type_name = str(filter_step_type).upper()
                    # Si es un value como 'api_fetch', convertir a name 'API_FETCH'
                    # Los values tienen underscore y están en minúsculas
                    filter_type_name = filter_type_name.replace('-', '_')
            else:
                filter_type_name = None

            # --- SECTION A: LIBRARY (MY ATOMS & PLAYBOOKS + SCRIPT LIBRARY) ---
            if show_library:
                # 1. Fetch Resources
                playbooks = await resource_listing_service.list_rpa_playbooks()

                # Script library atoms - cargar todos y filtrar en Python
                all_library_atoms = await resource_listing_service.list_script_library_atoms()
                library_atoms_raw = [
                    a for a in all_library_atoms
                    if a.get('status', '').lower() in ('validated', 'published')
                ]

                # Atom registry items (user's custom configured actions from the new catalog)
                # list_atoms() already filters by is_active=True
                catalog_atoms_raw = await atom_service.list_atoms()
                catalog_atoms = [
                    {
                        'id': a.id,
                        'name': a.name,
                        'description': a.description or '',
                        'source_module': 'catalog',
                        'status': a.status or 'PUBLISHED',
                        'step_type': a.atom_type.name if hasattr(a.atom_type, 'name') else str(a.atom_type),
                        'is_favorite': False
                    }
                    for a in catalog_atoms_raw
                    # Excluir solo DEPRECATED - is_active ya filtra los inactivos
                    if (a.status or 'PUBLISHED').upper() != 'DEPRECATED'
                ]

                # API configurations (from APIEndpointConfig table)
                api_configs_raw = await api_connection_service.list_configs()
                api_configs = [
                    {
                        'id': c['id'],
                        'name': c['name'],
                        'description': c.get('url', ''),
                        'source_module': 'api_config',
                        'status': 'PUBLISHED',
                        'step_type': 'API_FETCH',
                        'is_favorite': False
                    }
                    for c in api_configs_raw
                ]

                library_atoms = library_atoms_raw + catalog_atoms + api_configs

                # Filtrar por tipo si hay filtro activo (comparación case-insensitive)
                if filter_type_name:
                    library_atoms = [a for a in library_atoms if a.get('step_type', '').upper() == filter_type_name]

                # Dedup playbooks by ID just in case
                unique_playbooks = {p['id']: p for p in playbooks}.values() if playbooks else []
                # Filtrar playbooks solo si el filtro es RPA_EXECUTE o no hay filtro
                if filter_type_name and filter_type_name.upper() != 'RPA_EXECUTE':
                    unique_playbooks = []

                # Agrupar átomos por categoría funcional (misma taxonomía que "Crear nuevo")
                grouped_by_category: dict[AtomCategory, list] = {cat: [] for cat in AtomCategory}

                for atom in library_atoms:
                    if query and query not in atom['name'].lower():
                        continue
                    # Obtener StepType del átomo
                    try:
                        step_type = StepType[atom['step_type']]
                        category = get_category_for_step_type(step_type)
                        if category:
                            grouped_by_category[category].append(atom)
                        else:
                            # Si no tiene categoría, ponerlo en PROCESSOR como fallback
                            grouped_by_category[AtomCategory.PROCESSOR].append(atom)
                    except (KeyError, ValueError):
                        # Si el step_type no es válido, ponerlo en PROCESSOR
                        grouped_by_category[AtomCategory.PROCESSOR].append(atom)

                has_items = bool(unique_playbooks) or bool(library_atoms)

                # Library Expansion (Default closed, open if query or filter active)
                is_lib_expanded = bool(query) or bool(filter_type_name)
                with ui.expansion(t('gallery.my_library', 'Mi biblioteca'), icon='inventory_2', value=is_lib_expanded).props('dense header-class="text-slate-700 font-bold bg-slate-50"').classes('w-full mb-4 border rounded'):
                    with ui.scroll_area().classes('w-full max-h-80'):
                        with ui.column().classes('w-full p-2 bg-white'):
                            if has_items:
                                # --- Playbooks RPA ---
                                if unique_playbooks:
                                    filtered_playbooks = [pb for pb in unique_playbooks if not query or query in pb['name'].lower()]
                                    if filtered_playbooks:
                                        ui.label(t('gallery.playbooks_rpa', 'Playbooks RPA')).classes('text-[10px] font-bold text-slate-400 uppercase mb-1')
                                        with ui.column().classes('w-full gap-0 mb-2'):
                                            for pb in filtered_playbooks:
                                                def make_pb_handler(pb_id, _pb_name):
                                                    async def handler():
                                                        result = on_select(StepType.RPA_EXECUTE, script_id=pb_id)
                                                        if hasattr(result, '__await__'):
                                                            await result
                                                        if closer and not wizard_mode:
                                                            closer()
                                                    return handler

                                                meta = get_atom_metadata(StepType.RPA_EXECUTE)
                                                with ui.row().classes(
                                                    'w-full items-center gap-2 px-2 py-1 hover:bg-slate-50 '
                                                    'cursor-pointer rounded transition-colors'
                                                ).on('click', make_pb_handler(pb['id'], pb['name'])):
                                                    ui.badge('RPA', color=meta.color).props('dense').classes('text-[9px] w-10 justify-center')
                                                    ui.label(pb['name']).classes('text-xs text-slate-700 flex-1')

                                # --- Átomos por categoría funcional (lista compacta) ---
                                # Siglas cortas para cada tipo de átomo
                                TYPE_ABBREV = {
                                    'RPA_EXECUTE': 'RPA', 'EXTRACTION': 'PDF', 'ETL_TRANSFORM': 'ETL',
                                    'CUSTOM_SCRIPT': 'PY', 'GRAPHICS': 'GFX', 'REPORT_GENERATE': 'RPT',
                                    'SQL_QUERY': 'SQL', 'SQL_INSERT': 'SQL', 'API_FETCH': 'API',
                                    'FOLDER_SCAN': 'DIR', 'EMAIL_SCAN': 'MAIL', 'SMTP': 'SMTP',
                                    'ARCHIVE_FILE': 'FILE', 'ANONYMIZATION': 'ANON', 'PDF_TOOLS': 'PDF',
                                    'LLM_PROCESS': 'LLM', 'FOLDER_WATCHER': 'WATCH', 'EMAIL_WATCHER': 'MAIL',
                                    'WEB_WATCHER': 'WEB', 'SCHEDULER': 'CRON',
                                }

                                for category in AtomCategory:
                                    atoms = grouped_by_category.get(category, [])
                                    if not atoms:
                                        continue

                                    cat_label = get_category_label(category)
                                    ui.label(cat_label).classes('text-[10px] font-bold text-slate-400 uppercase mt-2 mb-1')

                                    with ui.column().classes('w-full gap-0'):
                                        for atom in atoms:
                                            # Obtener metadata del átomo
                                            try:
                                                atom_step_type = StepType[atom['step_type']]
                                                meta = get_atom_metadata(atom_step_type)
                                                atom_color = meta.color
                                                abbrev = TYPE_ABBREV.get(atom['step_type'], atom['step_type'][:3])
                                            except (KeyError, ValueError):
                                                atom_color = 'gray'
                                                abbrev = '...'

                                            atom_name = atom['name']
                                            atom_id = atom['id']
                                            atom_step_type_str = atom['step_type']
                                            atom_status = atom.get('status', '')

                                            def make_atom_handler(a_id, a_step_type):
                                                async def handler():
                                                    step_type = StepType[a_step_type]
                                                    try:
                                                        result = on_select(step_type, script_id=a_id)
                                                    except TypeError:
                                                        result = on_select(step_type)
                                                    if hasattr(result, '__await__'):
                                                        await result
                                                    if closer and not wizard_mode:
                                                        closer()
                                                return handler

                                            with ui.row().classes(
                                                'w-full items-center gap-2 px-2 py-1 hover:bg-slate-50 '
                                                'cursor-pointer rounded transition-colors'
                                            ).on('click', make_atom_handler(atom_id, atom_step_type_str)):
                                                ui.badge(abbrev, color=atom_color).props('dense').classes('text-[9px] w-10 justify-center')
                                                ui.label(atom_name).classes('text-xs text-slate-700 flex-1')
                                                if atom_status.lower() == 'published':
                                                    ui.icon('verified', size='xs', color='green').classes('opacity-60')
                            else:
                                if filter_type_name:
                                    # Mensaje específico cuando hay filtro pero no hay acciones de ese tipo
                                    ui.label(t('gallery.empty_library_filtered', f'No hay acciones de tipo {filter_type_name} en tu biblioteca.')).classes('text-sm text-gray-400 italic ml-1 p-2')
                                    ui.label(t('gallery.create_first', 'Crea una primero desde la página de configuración de este tipo de acción.')).classes('text-xs text-gray-400 italic ml-1 px-2')
                                else:
                                    ui.label(t('gallery.empty_library', 'No se encontraron elementos en tu biblioteca.')).classes('text-sm text-gray-400 italic ml-1 p-2')


            # --- SECTION B: NEW ATOM (CATALOG) - NUEVA TAXONOMÍA ---
            # Ocultar sección "Crear nuevo" cuando se está vinculando (filtro activo)
            if not filter_type_name:
                with ui.column().classes('w-full'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('add_circle', color='secondary').classes('text-xl')
                        ui.label(t('gallery.create_new', 'Crear nuevo')).classes('text-md font-bold text-slate-700 uppercase tracking-wide')

                    # Short labels mapping for compact view
                    SHORT_LABELS = {
                        StepType.RPA_EXECUTE: "RPA",
                        StepType.EXTRACTION: "PDF/AI",
                        StepType.ANONYMIZATION: "ANON",
                        StepType.MASKING: "MASK",
                        StepType.CUSTOM_SCRIPT: "SCRIPT",
                        StepType.ETL_TRANSFORM: "ETL",
                        StepType.NAVIGATION: "NAV",
                        StepType.REPORT_GENERATE: "REPORT",
                        StepType.EMAIL_SEND: "SEND",
                        StepType.API_FETCH: "API",
                        StepType.SQL_QUERY: "SQL",
                        StepType.SQL_INSERT: "INSERT",
                        # Nuevos átomos
                        StepType.FOLDER_WATCHER: "WATCH",
                        StepType.EMAIL_WATCHER: "MAIL",
                        StepType.SCHEDULER: "SCHED",
                        StepType.FOLDER_SCAN: "SCAN",
                        StepType.EMAIL_SCAN: "INBOX",
                        StepType.GRAPHICS: "CHART",
                        StepType.ARCHIVE_FILE: "SAVE",
                        StepType.SMTP: "SMTP",
                        StepType.PDF_TOOLS: "PDF",
                        StepType.WEB_WATCHER: "WEB",
                    }

                    # Iterar sobre las categorías funcionales
                    for category in AtomCategory:
                        steps_list = ATOM_CATEGORIES_V2.get(category, [])
                        if not steps_list:
                            continue

                        # Filter steps in this category based on search
                        visible_steps = []
                        for step_type in steps_list:
                            meta = get_atom_metadata(step_type)
                            if query in meta.label.lower() or query in meta.description.lower():
                                visible_steps.append(step_type)

                        if not visible_steps:
                            continue

                        # Obtener icono y label de la categoría
                        cat_icon = CATEGORY_ICONS.get(category, 'folder_open')
                        cat_label = get_category_label(category)

                        # Collapsible Category Expansion
                        # Default expanded ONLY if there is a search query
                        is_expanded = bool(query)

                        with ui.expansion(cat_label, icon=cat_icon, value=is_expanded).props('dense header-class="text-slate-700 font-bold bg-slate-50"').classes('w-full mb-2 border rounded overflow-hidden'):
                            with ui.column().classes('w-full p-2 bg-white'):
                                # Compact 2-Column Grid
                                with ui.grid().classes('w-full grid-cols-2 gap-2'):
                                    for step_type in visible_steps:
                                        meta = get_atom_metadata(step_type)
                                        short_label = SHORT_LABELS.get(step_type, meta.label.split(' ')[0][:6].upper())

                                        # Click Handler - EXTENDIDO para CONNECTION
                                        def make_click_handler(st):
                                            async def handler():
                                                # Si es CONNECTION, mostrar subtipos en lugar de seleccionar
                                                if st == StepType.CONNECTION:
                                                    state.wizard_show_connection_subtypes = True
                                                    gallery_content.refresh()
                                                    return

                                                # Llamar callback (puede ser para añadir al flujo o para standalone)
                                                result = on_select(st)
                                                if hasattr(result, '__await__'):
                                                    await result

                                                # Cerrar drawer/dialog si aplica (solo si no es wizard mode)
                                                if closer and not wizard_mode:
                                                    closer()
                                            return handler

                                        # Ultra-Compact Chip/Card Design
                                        with ui.card().classes(f'p-2 hover:shadow-md transition-all cursor-pointer border-l-4 border-{meta.color}-500 group flex-row items-center gap-2 h-10 min-h-0').props('flat bordered').on('click', make_click_handler(step_type)):
                                            # Icon
                                            ui.icon(meta.icon, size='xs').classes(f'text-{meta.color}-600')

                                            # Short Label
                                            ui.label(short_label).classes('font-bold text-xs text-slate-700 leading-tight truncate flex-1')

        await gallery_content()


async def show_atom_gallery(
    on_select: Callable[[StepType], None],
    show_library: bool = True,
    show_stepper: bool = False,
    wizard_mode: bool = False
):
    """
    Opens a unified atom selection gallery (Modal Dialog Version).

    Reset estado de subtipos al abrir para siempre empezar en vista principal.
    """
    # Reset estado de wizard para empezar siempre en vista de tipos
    state.wizard_show_connection_subtypes = False
    state.wizard_initial_subtype = None

    with ui.dialog() as gallery_dialog, ui.card().classes('w-[80vw] max-w-5xl h-[70vh] flex flex-col p-0 overflow-hidden'):

        # 1. Header & Search
        t = state.i18n.t
        with ui.row().classes('w-full items-center justify-between p-4 bg-slate-50 border-b shrink-0'):
            ui.label(t('gallery.title', 'Galería de Acciones')).classes('text-xl font-bold text-slate-800')

            # Search Input
            search_input = ui.input(placeholder=t('gallery.search_placeholder', 'Buscar acción...')) \
                .props('dense outlined rounded icon=search') \
                .classes('w-64')

            ui.button(icon='close', on_click=gallery_dialog.close).props('flat round dense color=grey')

        # 2. Stepper (optional)
        if show_stepper:
            with ui.row().classes('w-full justify-center gap-4 p-4 border-b shrink-0'):
                wizard_steps = [
                    t('gallery.wizard.type', 'Tipo'), 
                    t('gallery.wizard.info', 'Información'), 
                    t('gallery.wizard.config', 'Configuración')
                ]
                for i, label in enumerate(wizard_steps, 1):
                    active = i == 1
                    color = 'primary' if active else 'grey'
                    with ui.row().classes('items-center gap-2'):
                        ui.badge(str(i), color=color).classes('text-lg')
                        ui.label(label).classes(f'font-bold' if active else 'text-gray-500')
                    if i < 3:
                        ui.icon('arrow_forward', color='grey').classes('mx-2')

        # 3. Main Content Area
        with ui.scroll_area().classes('flex-1 w-full p-6 bg-white') as container:
           await render_atom_gallery(
               container=container,
               on_select=on_select,
               show_library=show_library,
               search_input=search_input,
               wizard_mode=wizard_mode,
               closer=gallery_dialog.close
           )

        gallery_dialog.open()

    return gallery_dialog

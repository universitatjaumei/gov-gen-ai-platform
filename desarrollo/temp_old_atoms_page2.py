"""
Acciones Page - UI de Administraci├│n de Acciones (anteriormente ├ütomos).
Permite gestionar el cat├ílogo de acciones reutilizables.
"""
import json
from typing import Optional, List, Dict, Any
from nicegui import ui

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.services.atom_service import atom_service
from client_app.app.database.models import AtomRegistry, FlowStep
from automatia_shared.enums import StepType

from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.database.db import client_engine

# Import centralized atom catalog
from client_app.app.config.atom_catalog import (
    ATOM_CATALOG,
    ATOM_CATEGORIES,
    get_all_atoms,
    get_atoms_by_category,
    get_atom_metadata,
    get_atom_icon,
    get_atom_color
)


class AtomsPageState:
    """
    Mantiene el estado reactivo de la p├ígina de administraci├│n de acciones.
    Incluye la lista de acciones cargadas, filtros activos y estados de carga.
    """
    def __init__(self):
        self.atoms: List[AtomRegistry] = []
        self.filter_type: Optional[StepType] = None
        self.filter_user_only: bool = False
        self.filter_system_only: bool = False
        self.is_loading: bool = False
        self.usage_counts: Dict[int, int] = {}  # atom_id -> count of FlowSteps


async def load_atoms(page_state: AtomsPageState):
    """Carga las acciones con los filtros aplicados."""
    page_state.is_loading = True

    # Cargar acciones
    page_state.atoms = await atom_service.list_atoms(
        atom_type=page_state.filter_type,
        user_only=page_state.filter_user_only
    )

    # Si filtro sistema est├í activo, filtrar solo is_system=True
    if page_state.filter_system_only:
        page_state.atoms = [a for a in page_state.atoms if a.is_system]

    # Cargar conteo de usos para cada acci├│n
    async with AsyncSession(client_engine) as session:
        for atom in page_state.atoms:
            query = select(func.count()).select_from(FlowStep).where(
                FlowStep.atom_id == atom.id
            )
            result = await session.execute(query)
            page_state.usage_counts[atom.id] = result.scalar() or 0

    page_state.is_loading = False


def get_step_type_options() -> List[Dict[str, Any]]:
    """Retorna opciones de StepType para select."""
    all_atoms = get_all_atoms()
    options = [{'label': 'Todos', 'value': None}]
    
    for atom_meta in all_atoms:
        options.append({
            'label': atom_meta.label,
            'value': atom_meta.step_type
        })
    
    return options


# Now using centralized catalog functions
# get_atom_icon() and get_atom_color() are imported from atom_catalog





def atoms_page_content():
    """
    Renderiza la interfaz principal para la gesti├│n del cat├ílogo de acciones.
    Permite visualizar, filtrar, editar y crear nuevos bloques de construcci├│n
    reutilizables para los flujos de trabajo.
    """
    t = state.i18n.t
    page_state = AtomsPageState()

    # Estado del modo de la p├ígina: 'list' o 'gallery'
    page_mode = {'current': 'list'}

    async def refresh_atoms():
        await load_atoms(page_state)
        render_page_content.refresh()

    def show_gallery():
        """Muestra la galer├¡a de tipos de acciones en el cuerpo central."""
        page_mode['current'] = 'gallery'
        render_page_content.refresh()

    def show_list():
        """Vuelve a mostrar la lista de acciones."""
        page_mode['current'] = 'list'
        render_page_content.refresh()

    def handle_atom_type_selected(step_type: StepType):
        """Navega a la p├ígina de dise├▒o del tipo de acci├│n seleccionado."""
        from client_app.app.config.atom_catalog import STEP_TYPE_ROUTES
        route = STEP_TYPE_ROUTES.get(step_type)
        if route:
            ui.navigate.to(route)
        else:
            # Para acciones sin p├ígina dedicada, mostrar mensaje
            ui.notify(f'El tipo {step_type.value} a├║n no tiene p├ígina de dise├▒o', type='warning')

    @ui.refreshable
    def render_page_content():
        if page_mode['current'] == 'gallery':
            render_gallery_mode()
        else:
            render_list_mode()

    def render_gallery_mode():
        """Renderiza la galer├¡a de tipos de acciones para crear una nueva."""
        from client_app.app.config.atom_catalog import (
            ATOM_CATEGORIES_V2, CATEGORY_ICONS, CATEGORY_LABELS,
            get_atom_metadata, AtomCategory
        )

        # Header con bot├│n de volver
        with ui.row().classes('w-full items-center justify-between mb-4'):
            with ui.row().classes('items-center gap-2'):
                ui.button(icon='arrow_back', on_click=show_list).props('flat round')
                ui.label(t('atoms.step1_title')).classes('text-2xl font-bold')

        # Descripci├│n
        ui.label(t('atoms.select_type_hint', 'Elige el tipo de acci├│n que deseas crear. Ser├ís redirigido a la p├ígina de dise├▒o correspondiente.')).classes('text-gray-600 mb-6')

        # Grid de categor├¡as
        for category in AtomCategory:
            if category == AtomCategory.TRIGGER:
                continue  # Ocultar disparadores

            steps_list = ATOM_CATEGORIES_V2.get(category, [])
            if not steps_list:
                continue

            cat_icon = CATEGORY_ICONS.get(category, 'folder_open')
            cat_label = CATEGORY_LABELS.get(category, category.value)

            with ui.expansion(cat_label, icon=cat_icon, value=True).props('dense header-class="text-slate-700 font-bold bg-slate-50"').classes('w-full mb-2 border rounded overflow-hidden'):
                with ui.row().classes('w-full p-4 gap-4 flex-wrap'):
                    for step_type in steps_list:
                        meta = get_atom_metadata(step_type)

                        # Card clickable para cada tipo
                        with ui.card().classes(f'w-64 p-4 hover:shadow-lg transition-all cursor-pointer border-l-4 border-{meta.color}-500'):
                            with ui.row().classes('items-center gap-3 mb-2'):
                                ui.icon(meta.icon, size='md').classes(f'text-{meta.color}-600')
                                ui.label(meta.label).classes('font-bold text-lg')
                            ui.label(meta.description).classes('text-gray-600 text-sm')

                            # Bot├│n de crear
                            ui.button(
                                t('atoms.create'),
                                icon='add',
                                on_click=lambda st=step_type: handle_atom_type_selected(st)
                            ).props('flat color=primary').classes('mt-2')

    def render_list_mode():
        """Renderiza la lista de acciones existentes."""
        # Header
        with ui.row().classes('w-full items-center justify-between mb-4'):
            ui.label(t('atoms.title')).classes('text-2xl font-bold')
            ui.button(
                t('atoms.new'),
                icon='add',
                on_click=show_gallery
            ).classes('bg-primary text-white')

        # Filters
        render_filters()

        # List
        render_atoms_list()

    def render_filters():
        """Renderiza los filtros de la lista de acciones."""
        with ui.card().classes('w-full p-4 mb-4'):
            with ui.row().classes('w-full items-center gap-4 flex-wrap'):
                ui.label(t('atoms.filters', 'Filtros:')).classes('font-bold')

                # Filtro por tipo
                def on_type_change(e):
                    page_state.filter_type = e.value
                    ui.timer(0.1, refresh_atoms, once=True)

                ui.select(
                    options={opt['value']: opt['label'] for opt in get_step_type_options()},
                    value=None,
                    label=t('atoms.filter_type', 'Tipo'),
                    on_change=on_type_change
                ).classes('w-48')

                # Filtro solo m├¡os
                def on_user_only_change(e):
                    page_state.filter_user_only = e.value
                    if e.value:
                        page_state.filter_system_only = False
                    ui.timer(0.1, refresh_atoms, once=True)

                ui.checkbox(
                    t('atoms.filter_user_only', 'Solo m├¡os'),
                    value=False,
                    on_change=on_user_only_change
                )

                # Filtro solo sistema
                def on_system_only_change(e):
                    page_state.filter_system_only = e.value
                    if e.value:
                        page_state.filter_user_only = False
                    ui.timer(0.1, refresh_atoms, once=True)

                ui.checkbox(
                    t('atoms.filter_system_only', 'Solo sistema'),
                    value=False,
                    on_change=on_system_only_change
                )

                ui.space()

                ui.button(
                    icon='refresh',
                    on_click=refresh_atoms
                ).props('flat round')

    # === ATOMS LIST ===
    @ui.refreshable
    def render_atoms_list():
        if page_state.is_loading:
            with ui.row().classes('w-full justify-center p-8'):
                ui.spinner(size='lg')
                ui.label(t('atoms.loading'))
            return

        if not page_state.atoms:
            with ui.card().classes('w-full p-8 text-center'):
                ui.icon('inventory_2', size='xl').classes('text-gray-400')
                ui.label(t('atoms.empty')).classes('text-gray-500 text-lg mt-2')
                ui.label(t('atoms.empty_hint')).classes('text-gray-400')
            return

        # Grid de cards
        with ui.row().classes('w-full gap-4 flex-wrap'):
            for atom in page_state.atoms:
                render_atom_card(atom, page_state, refresh_atoms)

    def render_atom_card(atom: AtomRegistry, page_state: AtomsPageState, refresh_callback):
        """Renderiza una card de acci├│n."""
        usage_count = page_state.usage_counts.get(atom.id, 0)
        step_type = atom.atom_type if isinstance(atom.atom_type, StepType) else StepType(atom.atom_type)
        icon = get_atom_icon(step_type)
        color = get_atom_color(step_type)

        with ui.card().classes('w-72 p-4 hover:shadow-lg transition-shadow'):
            # Header
            with ui.row().classes('w-full items-center gap-2 mb-2'):
                ui.icon(icon, color=color).classes('text-2xl')
                with ui.column().classes('flex-1 gap-0'):
                    ui.label(atom.name).classes('font-bold text-lg truncate')
                    ui.chip(
                        step_type.value.replace('_', ' ').title(),
                        color=color
                    ).props('dense outline')

            # Description
            desc = atom.description or t('atoms.no_description')
            ui.label(desc).classes('text-gray-600 text-sm h-12 overflow-hidden')

            # Stats
            with ui.row().classes('w-full items-center gap-4 mt-2 text-sm text-gray-500'):
                with ui.row().classes('items-center gap-1'):
                    ui.icon('account_tree', size='xs')
                    ui.label(f'{usage_count} usos')

                with ui.row().classes('items-center gap-1'):
                    ui.icon('tag', size='xs')
                    ui.label(f'v{atom.version}')

                if atom.is_system:
                    ui.chip('Sistema', color='blue').props('dense')

            ui.separator().classes('my-2')

            # Actions
            with ui.row().classes('w-full justify-end gap-1'):
                # Ver detalle
                ui.button(
                    icon='visibility',
                    on_click=lambda a=atom: show_atom_detail_dialog(a)
                ).props('flat round dense').tooltip(t('atoms.view'))

                # Editar (solo si no es del sistema)
                if not atom.is_system:
                    ui.button(
                        icon='edit',
                        on_click=lambda a=atom: show_edit_atom_dialog(a, refresh_callback)
                    ).props('flat round dense').tooltip(t('atoms.edit'))

                # Duplicar
                ui.button(
                    icon='content_copy',
                    on_click=lambda a=atom: show_duplicate_dialog(a, refresh_callback)
                ).props('flat round dense').tooltip(t('atoms.duplicate'))

                # Eliminar (solo si no tiene usos y no es del sistema)
                if not atom.is_system and usage_count == 0:
                    ui.button(
                        icon='delete',
                        color='red',
                        on_click=lambda a=atom: show_delete_dialog(a, refresh_callback)
                    ).props('flat round dense').tooltip(t('atoms.delete'))

    # Initial load
    ui.timer(0.1, refresh_atoms, once=True)
    render_page_content()


def show_atom_detail_dialog(atom: AtomRegistry):
    """
    Muestra un cuadro de di├ílogo modal con la informaci├│n t├®cnica detallada de una acci├│n.
    Incluye entradas, salidas, configuraci├│n y metadatos de seguridad.
    """
    t = state.i18n.t

    with ui.dialog() as dialog, ui.card().classes('w-[600px] max-h-[80vh]'):
        with ui.row().classes('w-full items-center justify-between mb-4'):
            ui.label(atom.name).classes('text-xl font-bold')
            ui.button(icon='close', on_click=dialog.close).props('flat round')

        step_type = atom.atom_type if isinstance(atom.atom_type, StepType) else StepType(atom.atom_type)

        # Info b├ísica
        with ui.row().classes('gap-4 mb-4'):
            ui.chip(step_type.value.replace('_', ' ').capitalize(), icon=get_atom_icon(step_type))
            ui.chip(f'v{atom.version}', icon='tag')
            if atom.is_system:
                ui.chip('Sistema', color='blue', icon='verified')

        if atom.description:
            ui.label(atom.description).classes('text-gray-600 mb-4')

        ui.separator()

        # Config Schema
        with ui.expansion(t('atoms.config_schema'), icon='schema').classes('w-full'):
            try:
                schema = json.loads(atom.config_schema) if atom.config_schema else {}
                ui.json_editor({'content': {'json': schema}}).classes('h-48')
            except json.JSONDecodeError:
                ui.label(t('atoms.schema_error', 'Error al parsear schema')).classes('text-red-500')

        # Default Config
        with ui.expansion(t('atoms.default_config'), icon='settings').classes('w-full'):
            try:
                default = json.loads(atom.default_config) if atom.default_config else {}
                ui.json_editor({'content': {'json': default}}).classes('h-48')
            except json.JSONDecodeError:
                ui.label(t('atoms.config_error', 'Error al parsear config')).classes('text-red-500')

        with ui.row().classes('w-full justify-end mt-4'):
            ui.button(t('common.close'), on_click=dialog.close)

    dialog.open()


async def show_edit_atom_dialog(atom: AtomRegistry, refresh_callback):
    """Abre di├ílogo de edici├│n seg├║n el estado de la acci├│n."""
    t = state.i18n.t

    if getattr(atom, 'status', 'PUBLISHED') == 'DRAFT':
        # MODO BORRADOR: Abrir editor completo
        await _show_full_edit_dialog(atom, refresh_callback)
    else:
        # MODO SELLADO/PUBLICADO: Solo metadatos editables
        await show_maintenance_dialog(atom, refresh_callback)


async def _show_full_edit_dialog(atom: AtomRegistry, refresh_callback):
    """Modal para edici├│n completa de ├ítomo (modo DRAFT)."""
    t = state.i18n.t

    # Estado local del formulario
    form_data = {
        'name': atom.name,
        'description': atom.description or '',
        'config_schema': atom.config_schema,
        'default_config': atom.default_config or '{}',
        'version': atom.version
    }

    async def save_changes():
        try:
            await atom_service.update_atom(
                atom_id=atom.id,
                name=form_data['name'],
                description=form_data['description'],
                config_schema=form_data['config_schema'],
                default_config=form_data['default_config'],
                version=form_data['version']
            )
            ui.notify(t('atoms.updated'), type='positive')
            dialog.close()
            await refresh_callback()
        except ValueError as e:
            ui.notify(str(e), type='negative')

        with ui.dialog() as dialog, ui.card().classes('w-[600px]'):
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label(t('atoms.edit_title')).classes('text-xl font-bold')
                ui.button(icon='close', on_click=dialog.close).props('flat round')

            ui.input(
                label=t('atoms.name'),
                value=form_data['name'],
                on_change=lambda e: form_data.update({'name': e.value})
            ).classes('w-full')

            ui.textarea(
                label=t('atoms.description'),
                value=form_data['description'],
                on_change=lambda e: form_data.update({'description': e.value})
            ).classes('w-full')

            ui.input(
                label=t('atoms.version'),
                value=form_data['version'],
                on_change=lambda e: form_data.update({'version': e.value})
            ).classes('w-48')

        with ui.expansion(t('atoms.config_schema'), icon='schema').classes('w-full'):
            ui.textarea(
                value=form_data['config_schema'],
                on_change=lambda e: form_data.update({'config_schema': e.value})
            ).classes('w-full font-mono').props('rows=8')

        with ui.expansion(t('atoms.default_config'), icon='settings').classes('w-full'):
            ui.textarea(
                value=form_data['default_config'],
                on_change=lambda e: form_data.update({'default_config': e.value})
            ).classes('w-full font-mono').props('rows=6')

        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button(t('common.cancel'), on_click=dialog.close).props('flat')
            ui.button(
                t('common.save'),
                icon='save',
                on_click=save_changes
            ).classes('bg-primary text-white')

    dialog.open()


async def show_maintenance_dialog(atom: AtomRegistry, refresh_callback):
    """Abre el DrawerHub en modo documentaci├│n para edici├│n de metadatos."""
    layout_manager.enter_documentation_mode(
        atom_name=atom.name,
        doc_path=getattr(atom, 'doc_path', None),
        status=getattr(atom, 'status', 'PUBLISHED'),
        description=atom.description,
        resource_id=atom.id,
        record_type='atom'
    )
    ui.notify("Abriendo panel de metadatos en el lateral", type='info')


async def save_atom_metadata(atom_id, name, description, dialog, refresh_callback):
    try:
        await atom_service.update_atom(
            atom_id=atom_id,
            name=name,
            description=description
        )
        ui.notify("Metadatos actualizados", type='positive')
        dialog.close()
        await refresh_callback()
    except Exception as e:
        ui.notify(f"Error: {e}", type='negative')


async def create_atom_version_and_edit(atom_id, dialog, refresh_callback):
    try:
        new_atom = await atom_service.create_new_version(atom_id)
        ui.notify(f"Nueva versi├│n {new_atom.version} creada como Borrador", type='positive')
        dialog.close()
        # Refrescar lista y abrir editor
        await refresh_callback()
        await show_edit_atom_dialog(new_atom, refresh_callback)
    except Exception as e:
        ui.notify(f"Error: {e}", type='negative')


def show_duplicate_dialog(atom: AtomRegistry, refresh_callback):
    """Muestra di├ílogo para duplicar acci├│n."""
    t = state.i18n.t
    new_name = {'value': f'{atom.name} (copia)'}

    async def do_duplicate():
        try:
            await atom_service.duplicate_atom(atom.id, new_name['value'])
            ui.notify(t('atoms.duplicated'), type='positive')
            dialog.close()
            await refresh_callback()
        except ValueError as e:
            ui.notify(str(e), type='negative')

    with ui.dialog() as dialog, ui.card().classes('w-96'):
        ui.label(t('atoms.duplicate_title')).classes('text-lg font-bold mb-4')
        ui.label(t('atoms.duplicate_hint')).classes('text-gray-600')

        ui.input(
            label=t('atoms.new_name'),
            value=new_name['value'],
            on_change=lambda e: new_name.update({'value': e.value})
        ).classes('w-full my-4')

        with ui.row().classes('w-full justify-end gap-2'):
            ui.button(t('common.cancel'), on_click=dialog.close).props('flat')
            ui.button(
                t('atoms.duplicate'),
                icon='content_copy',
                on_click=do_duplicate
            ).classes('bg-primary text-white')

    dialog.open()


def show_delete_dialog(atom: AtomRegistry, refresh_callback):
    """Muestra di├ílogo de confirmaci├│n para eliminar."""
    t = state.i18n.t

    async def do_delete():
        success = await atom_service.delete_atom(atom.id)
        if success:
            ui.notify(t('atoms.deleted'), type='positive')
            dialog.close()
            await refresh_callback()
        else:
            ui.notify(t('atoms.delete_error'), type='negative')

    with ui.dialog() as dialog, ui.card().classes('w-96'):
        ui.label(t('atoms.delete_title')).classes('text-lg font-bold mb-4')
        ui.label(
            t('atoms.delete_confirm')
        ).classes('text-gray-600')
        ui.label(
            t('atoms.delete_warning')
        ).classes('text-orange-600 text-sm mt-2')

        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button(t('common.cancel'), on_click=dialog.close).props('flat')
            ui.button(
                t('common.delete'),
                icon='delete',
                color='red',
                on_click=do_delete
            )

    dialog.open()


def show_atom_wizard(initial_step_type: StepType, refresh_callback):
    """
    Despliega el asistente (wizard) para la creaci├│n de una nueva acci├│n.
    Gu├¡a al usuario a trav├®s del proceso de configuraci├│n, definici├│n de datos
    y guardado en el cat├ílogo.

    Args:
        initial_step_type: El tipo de acci├│n seleccionado inicialmente.
        refresh_callback: Funci├│n a llamar para refrescar la lista de acciones al finalizar.
    """
    t = state.i18n.t

    form_data = {
        'name': '',
        'description': t('atoms.default_desc', 'Acci├│n personalizada'),
        'atom_type': initial_step_type,
        'config_schema': '{"type": "object", "properties": {}, "required": []}',
        'default_config': '{}',
        'version': '1.0.0'
    }

    # Start directly at Step 2 since type is already selected from Gallery
    wizard_step = {'current': 2} 

    async def create_atom():
        try:
            await atom_service.create_atom(
                name=form_data['name'],
                atom_type=form_data['atom_type'],
                config_schema=form_data['config_schema'],
                description=form_data['description'],
                default_config=form_data['default_config'],
                version=form_data['version']
            )
            ui.notify(t('atoms.created'), type='positive')
            dialog.close()
            await refresh_callback()
        except ValueError as e:
            ui.notify(str(e), type='negative')

    # Larger dialog size for Wizard (matches Flow Editor Gallery dimension for consistency)
    with ui.dialog() as dialog, ui.card().classes('w-[80vw] max-w-5xl h-[70vh] flex flex-col p-0 overflow-hidden'):
        
        # Header Area
        with ui.row().classes('w-full items-center justify-between p-4 bg-slate-50 border-b shrink-0'):
            # Show Type in Title
            op_label = get_atom_metadata(initial_step_type).label
            ui.label(t('atoms.create_title') + f': {op_label}').classes('text-xl font-bold text-slate-800')
            ui.button(icon='close', on_click=dialog.close).props('flat round dense color=grey')

        # Wizard stepper
        @ui.refreshable
        def render_wizard():
            # Step indicators
            with ui.row().classes('w-full justify-center gap-4 mb-6 border-b pb-4 pt-4 bg-white'):
                for i, label in enumerate([t('atoms.step1_indicator', 'Tipo'), t('atoms.step2_indicator', 'Informaci├│n'), t('atoms.step3_indicator', 'Configuraci├│n')], 1):
                    # We render all steps but Step 1 is already "done" in previous screen
                    active = wizard_step['current'] == i
                    completed = wizard_step['current'] > i or i == 1 # Step 1 is always completed here
                    color = 'primary' if active else ('positive' if completed else 'grey')
                    with ui.row().classes('items-center gap-2'):
                        ui.badge(str(i), color=color).classes('text-lg')
                        ui.label(label).classes(f'font-bold' if active else 'text-gray-500')
                    if i < 3:
                        ui.icon('arrow_forward', color='grey').classes('mx-2')

            # Step 2: Informaci├│n b├ísica
            if wizard_step['current'] == 2:
                with ui.column().classes('w-full h-full p-6'):
                    ui.label(t('atoms.step2_title')).classes('text-lg font-bold mb-4')
                    
                    with ui.row().classes('items-center gap-4 mb-6'):
                         # Show selected atom icon/info summary
                         meta = get_atom_metadata(form_data['atom_type'])
                         ui.icon(meta.icon, size='2em').classes(f'text-{meta.color}-600 p-2 bg-{meta.color}-50 rounded-lg')
                         with ui.column().classes('gap-0'):
                             ui.label(meta.label).classes('font-bold text-gray-800')
                             ui.label(meta.description).classes('text-sm text-gray-500')
                             ui.button(t('atoms.change_type', 'Cambiar Tipo'), on_click=dialog.close).props('flat dense color=primary size=sm').classes('-ml-2')


                    ui.input(
                        label=t('atoms.name') + ' *',
                        value=form_data['name'],
                        on_change=lambda e: form_data.update({'name': e.value})
                    ).classes('w-full mb-4').props('outlined')

                    ui.textarea(
                        label=t('atoms.description'),
                        value=form_data['description'],
                        on_change=lambda e: form_data.update({'description': e.value})
                    ).classes('w-full mb-4').props('outlined rows=3')

                    ui.input(
                        label=t('atoms.version'),
                        value=form_data['version'],
                        on_change=lambda e: form_data.update({'version': e.value})
                    ).classes('w-48').props('outlined')

                    with ui.row().classes('w-full justify-end mt-auto pt-4 border-t'):
                        next_btn = ui.button(
                            t('common.next'),
                            icon='arrow_forward',
                            on_click=lambda: [wizard_step.update({'current': 3}), render_wizard.refresh()]
                        ).classes('bg-primary text-white')
                        # Disable button if name is empty
                        if not form_data['name'].strip():
                            next_btn.disable()

            # Step 3: Configuraci├│n
            elif wizard_step['current'] == 3:
                with ui.column().classes('w-full h-full p-6'):
                    ui.label(t('atoms.step3_title')).classes('text-lg font-bold mb-4')

                    ui.label(
                        t('atoms.schema_hint')
                    ).classes('text-gray-600 mb-4')

                    with ui.expansion(t('atoms.json_schema_advanced', 'Esquema JSON (avanzado)'), icon='code').classes('w-full mb-4'):
                        ui.textarea(
                            value=form_data['config_schema'],
                            on_change=lambda e: form_data.update({'config_schema': e.value})
                        ).classes('w-full font-mono').props('rows=8 outlined')

                    with ui.expansion(t('atoms.default_config_json', 'Valores por defecto (JSON)'), icon='settings').classes('w-full'):
                        ui.textarea(
                            value=form_data['default_config'],
                            on_change=lambda e: form_data.update({'default_config': e.value})
                        ).classes('w-full font-mono').props('rows=6 outlined')

                    with ui.row().classes('w-full justify-between mt-auto pt-4 border-t'):
                        ui.button(
                            t('common.back'),
                            icon='arrow_back',
                            on_click=lambda: [wizard_step.update({'current': 2}), render_wizard.refresh()]
                        ).props('flat')
                        ui.button(
                            t('atoms.create'),
                            icon='check',
                            on_click=create_atom
                        ).classes('bg-positive text-white')

        render_wizard()
        dialog.open()


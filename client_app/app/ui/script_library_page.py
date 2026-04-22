from nicegui import ui
import asyncio
import json
from typing import List, Optional, Dict, Any

from client_app.app.database.models import ScriptLibrary
from client_app.app.services.script_library_service import script_library_service
from client_app.app.ui.components.unified_resource_card import unified_resource_card
from client_app.app.ui.components.markdown_viewer import MarkdownViewer
from client_app.app.services.doc_generator_service import doc_generator
from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from pathlib import Path

# Docs base path
DOCS_BASE_PATH = Path("data/storage/scripts/docs")

# State for the page
page_state = {
    'search': '',
    'filter_module': 'all',
    'filter_status': 'all'
}

import logging
from automatia_shared.enums import StepType
from client_app.app.config.atom_catalog import STEP_TYPE_ROUTES
from client_app.app.core.state import state as app_state

page_mode = {'current': 'list'}

async def script_library_page_content():
    """
    Controlador unificado del Catálogo de Acciones.
    Permite explorar, filtrar y gestionar todos los activos de automatización.
    """
    t = state.i18n.t
    title_text = t('atoms.title', "Catálogo de acciones")
    
    # Enable all statuses by default
    page_state['filter_status'] = 'all'

    # Components refs using a dict to bypass closure reassignment issues
    ui_refs = {'header_list': None, 'header_gallery': None}

    def close_creation_wizard():
        page_mode['current'] = 'list'
        app_state.on_atom_select_callback = None
        layout_manager.exit_focus_mode()
        if ui_refs['header_gallery']:
            ui_refs['header_gallery'].visible = False
            ui_refs['header_gallery'].update()
        if ui_refs['header_list']:
            ui_refs['header_list'].visible = True
            ui_refs['header_list'].update()

    async def global_on_type_selected(step_type, subtype=None, script_id=None, **kwargs):
        """Callback puro e independiente inyectado al Drawer."""
        route = STEP_TYPE_ROUTES.get(step_type)
        ui.notify(f"Navigating to {step_type}: {route}", type='info')
        if route:
            app_state.clear_atom_editing_context()
            separator = '&' if '?' in route else '?'
            route_with_mode = f"{route}{separator}initial_mode=design"
            ui.navigate.to(route_with_mode)
            from client_app.app.services.layout_manager import layout_manager
            layout_manager.exit_focus_mode()
            return True
        else:
            ui.notify(t('atoms.no_design_page', name=str(step_type)), type='warning')
            return False

    def open_creation_wizard():
        page_mode['current'] = 'gallery'
        app_state.on_atom_select_callback = global_on_type_selected
        layout_manager.enter_gallery_mode(show_library=False)  # No mostrar biblioteca, ya está en la página principal
        if ui_refs['header_list']:
            ui_refs['header_list'].visible = False
            ui_refs['header_list'].update()
        if ui_refs['header_gallery']:
            ui_refs['header_gallery'].visible = True
            ui_refs['header_gallery'].update()
    
    # CONTENT CONTAINER
    with ui.column().classes('w-full p-4 max-w-7xl mx-auto'):
        
        # Header - Modo Galería (Oculto inicialmente)
        with ui.row().classes('w-full justify-between items-center mb-4') as h_gallery:
            ui_refs['header_gallery'] = h_gallery
            h_gallery.visible = False
            with ui.row().classes('items-center gap-2'):
                ui.button(icon='arrow_back', on_click=close_creation_wizard).props('flat round')
                ui.label(t('atoms.step1_title', "Seleccionar tipo de acción")).classes("text-2xl font-bold text-primary")
                
        # Header - Modo Lista
        with ui.row().classes('w-full justify-between items-center mb-4') as h_list:
            ui_refs['header_list'] = h_list
            ui.label(title_text).classes("text-2xl font-bold text-primary")
            ui.button(t('atoms.new', "Nueva acción"), icon='add', on_click=open_creation_wizard).classes('bg-primary text-white shadow-md')

        # === Toolbar: Search & Filter ===
        with ui.row().classes('w-full items-center gap-4 mb-6 bg-gray-50 p-4 rounded-lg'):
            # Search
            ui.input(
                placeholder=t('atoms.search_placeholder', "Buscar por nombre, descripción o tags..."),
                on_change=lambda e: update_filters(search=e.value)
            ).props('outlined dense prepend-icon=search').classes('flex-grow')

            # Filters
            ui.select(
                options={
                    'all': t('atoms.filter_all_types', 'Todos los tipos'),
                    'custom': t('menu_items.custom_script', 'Scripts Python'),
                    'rpa': t('menu_items.rpa', 'Playbooks RPA'),
                    'extraction': t('menu_items.documents', 'Extracción PDF'),
                    'etl': t('menu_items.etl', 'ETL'),
                    'graphics': t('menu_items.graphics', 'Gráficos')
                },
                value=page_state['filter_module'],
                on_change=lambda e: update_filters(module=e.value)
            ).props('outlined dense').classes('w-48')

            # Status Filter
            status_options = {
                'all': t('atoms.filter_all_statuses'),
                'draft': t('dash_filter_draft'),
                'validated': t('dash_filter_success'),
                'published': t('dash_filter_all')
            }
            
            ui.select(
                options=status_options,
                value=page_state['filter_status'],
                on_change=lambda e: update_filters(status=e.value)
            ).props('outlined dense').classes('w-48')
        
        # === Resource Content ===
        content_container = ui.column().classes('w-full gap-8')

    async def load_resources():
        """Carga y filtra los recursos de la biblioteca."""

        content_container.clear()
        
        # Build query filters
        query = page_state['search'] if page_state['search'] else None
        module = page_state['filter_module'] if page_state['filter_module'] != 'all' else None
        
        # Load all resources
        results = await script_library_service.search_scripts(
            query=query,
            source_module=module
        )
        
        # Sort by Favorite then Name
        results.sort(key=lambda x: (not x.is_favorite, x.name.lower()))
        
        # Categorization Logic - Nueva Taxonomía de 4 Capas
        CAT_MAP = {
            # Disparadores (Triggers)
            'folder_watcher': t('gallery.trigger', 'Disparadores'),
            'email_watcher': t('gallery.trigger', 'Disparadores'),
            'scheduler': t('gallery.trigger', 'Disparadores'),
            # Entradas (Inputs)
            'sql': t('gallery.input', 'Entradas'),
            'api': t('gallery.input', 'Entradas'),
            'folder_scan': t('gallery.input', 'Entradas'),
            'email_scan': t('gallery.input', 'Entradas'),
            'db': t('gallery.input', 'Entradas'),
            # Procesadores (Processors)
            'extraction': t('gallery.processor', 'Procesadores'),
            'rpa': t('gallery.processor', 'Procesadores'),
            'custom': t('gallery.processor', 'Procesadores'),
            'etl': t('gallery.processor', 'Procesadores'),
            'anonymization': t('gallery.processor', 'Procesadores'),
            'masking': t('gallery.processor', 'Procesadores'),
            'graphics': t('gallery.processor', 'Procesadores'),
            'report': t('gallery.processor', 'Procesadores'),
            # Salidas (Outputs)
            'smtp': t('gallery.output', 'Salidas'),
            'archive': t('gallery.output', 'Salidas'),
            'email_send': t('gallery.output', 'Salidas'),
            # Legacy mappings
            'mail': t('gallery.trigger', 'Disparadores'),
            'email': t('gallery.trigger', 'Disparadores'),
            'folder': t('gallery.trigger', 'Disparadores'),
            'pdf_tools': t('gallery.utility', 'Utilidades'),
        }
        
        # Filter by status
        publicados = [s for s in results if s.status in ('published', 'validated')]
        en_creacion = [s for s in results if s.status == 'draft']
        
        tgt = page_state['filter_status']
        if tgt != 'all':
            if tgt == 'draft': 
                publicados = []
            elif tgt in ('published', 'validated'):
                en_creacion = []
                publicados = [s for s in publicados if s.status == tgt]

        def render_category_group(title, scripts):
            if not scripts: return
            
            # Group by Technical Category
            grouped = {}
            for s in scripts:
                cat = CAT_MAP.get(s.source_module, 'Otros')
                if cat not in grouped: grouped[cat] = []
                grouped[cat].append(s)
            
            if not grouped: return

            with content_container:
                if title:
                    ui.label(title).classes('text-xl font-bold text-primary mb-4')
                
                # Render Subsections
                for cat_name, items in grouped.items():
                    if not items: continue

                    ui.label(cat_name).classes('text-lg font-semibold text-gray-700 ml-2 mb-2')

                    # Responsive Grid Layout (Max 3 columns to prevent overlapping)
                    with ui.grid().classes('w-full grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 mb-10 p-2'):
                        for item in items:
                            try:
                                unified_resource_card(
                                    resource=item,
                                    on_execute=open_execution,
                                    on_edit=open_refine,
                                    on_click=open_details,
                                    on_delete=handle_delete_request
                                )
                            except Exception as e:
                                with ui.card().classes('w-full bg-red-100 p-2'):
                                    ui.label(f"Error rendering {item.name}: {e}").classes('text-red-500 text-xs')

        # Render Sections
        if not results:
             with content_container:
                ui.label(t('atoms.no_resources_found', "No se encontraron recursos.")).classes("text-center text-gray-500 mt-8 w-full")
        else:
            if publicados:
                render_category_group(t('atoms.catalog_published', "Acciones publicadas"), publicados)
            
            if en_creacion:
                if publicados:
                    with content_container: ui.separator().classes('my-4')
                render_category_group(t('atoms.catalog_drafts', "Acciones en creación"), en_creacion)


    def update_filters(search=None, module=None, status=None):
        if search is not None: page_state['search'] = search
        if module is not None: page_state['filter_module'] = module
        if status is not None: page_state['filter_status'] = status
        asyncio.create_task(load_resources())

    async def open_details(resource: ScriptLibrary):
        """Abre el panel lateral de detalles."""
        from client_app.app.core.state import app_state
        # Fetch full resource
        try:
             full_resource = await script_library_service.get_script(resource.id)
             if not full_resource:
                 ui.notify(t('common.error_loading', "Error: No se pudo cargar el recurso."), type='negative')
                 return

             # Global Drawer integration
             app_state.active_resource_for_details = full_resource
             app_state.active_drawer_content = 'resource_details'
             app_state.toggle_focus_mode(True)
                
        except Exception as e:
             ui.notify(f"{t('common.error_loading', 'Error al cargar detalles')}: {e}", type='negative')

    def open_execution(resource: ScriptLibrary):
        """Navigate to execution UI."""
        if resource.source_module == 'custom':
            if resource.source_automation_id: ui.navigate.to(f'/custom-scripts/{resource.source_automation_id}')
            else: ui.notify(t('common.error_script_not_found', 'No se encontró el script de origen'), type='negative')
        elif resource.source_module == 'extraction': ui.navigate.to(f'/documents?initial_mode=execution&atom_id={resource.id}')
        elif resource.source_module == 'etl': ui.navigate.to(f'/etl?initial_mode=execution&atom_id={resource.id}')
        elif resource.source_module == 'rpa': ui.navigate.to(f'/rpa?initial_mode=execution&atom_id={resource.id}')
        elif resource.source_module == 'graphics': ui.navigate.to(f'/graphics?initial_mode=execution&atom_id={resource.id}')
        elif resource.source_module == 'smtp': ui.navigate.to(f'/outputs/smtp?initial_mode=execution&atom_id={resource.id}')
        elif resource.source_module in ['anonymization', 'anonymizer']: ui.navigate.to(f'/processors/anonymizer?initial_mode=execution&atom_id={resource.id}')
        elif resource.source_module == 'pdf_tools': ui.navigate.to(f'/atoms/pdf-tools/{resource.id}?initial_mode=execution')
        else: ui.notify(f'{t("common.not_available", "Ejecución no disponible")} para {resource.source_module}', type='warning')

    def open_refine(resource: ScriptLibrary):
        """Redirige al editor o abre diálogo de mantenimiento según estado."""
        status = getattr(resource, 'status', 'published').lower()

        if status == 'draft':
            # MODO BORRADOR: Intentar navegar al editor específico
            if resource.source_module == 'custom':
                if resource.source_automation_id:
                    ui.navigate.to(f'/custom-scripts/{resource.source_automation_id}/edit')
                else:
                    ui.notify(t('common.error_script_not_found', 'No se encontró el script de origen.'), type='negative')
            elif resource.source_module == 'extraction':
                ui.navigate.to('/documents')
            elif resource.source_module == 'etl':
                ui.navigate.to('/etl')
            elif resource.source_module == 'rpa':
                ui.navigate.to('/rpa')
            elif resource.source_module == 'graphics':
                ui.navigate.to('/graphics')
            else:
                # Si es un borrador pero no tiene editor dedicado, usar el drawer
                layout_manager.enter_documentation_mode(
                    atom_name=resource.name,
                    doc_path=resource.doc_path,
                    status=resource.status,
                    description=resource.description,
                    resource_id=resource.id,
                    record_type='library'
                )
        else:
            # MODO SELLADO (Validated/Published): Diálogo de edición rápida
            open_edit_dialog(resource)

    def open_edit_dialog(resource: ScriptLibrary):
        """Abre un diálogo para editar nombre y descripción del recurso."""
        with ui.dialog() as dialog, ui.card().classes('p-6 min-w-[400px]'):
            ui.label(t('common.edit')).classes('text-xl font-bold text-gray-800 mb-4')

            # Campos de edición
            name_input = ui.input(
                t('common.name'),
                value=resource.name or ''
            ).classes('w-full mb-2').props('outlined')

            async def save_changes():
                """Guarda los cambios de nombre."""
                new_name = name_input.value.strip()

                if not new_name:
                    ui.notify(t('common.error_name_required'), type='warning')
                    return

                try:
                    await script_library_service.update_script_metadata(
                        script_id=resource.id,
                        name=new_name,
                        description=resource.description or '' # Maintain existing description
                    )
                    ui.notify(t('common.success'), type='positive')
                    dialog.close()
                    # Recargar la lista para reflejar los cambios
                    await load_resources()
                except Exception as e:
                    ui.notify(f"{t('common.error_save', 'Error al guardar')}: {e}", type='negative')

            # Botones de acción
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button(t('common.cancel'), on_click=dialog.close).props('flat')
                ui.button(t('common.save'), on_click=save_changes).props('color=primary')

        dialog.open()

    async def handle_delete_request(resource: ScriptLibrary):
        """Handle delete request with dependency checking."""
        try:
            deps = await script_library_service.get_atom_dependencies(resource.id)
            with ui.dialog() as confirm_dialog, ui.card().classes('p-6 min-w-[400px]'):
                if deps['count'] > 0:
                    ui.label('⚠️ ' + t('common.warning', 'Advertencia')).classes('text-xl font-bold text-orange-600 mb-4')
                    ui.label(t('atoms.delete_usage_warning', name=resource.name).replace('{count}', str(deps['count']))).classes('text-gray-700 mb-2')
                    with ui.column().classes('bg-orange-50 p-3 rounded mb-4 max-h-[200px] overflow-y-auto'):
                        for flow in deps['flows']:
                            with ui.row().classes('gap-2 items-start mb-2'):
                                ui.icon('warning', size='sm').classes('text-orange-500 mt-0.5')
                                with ui.column().classes('gap-0'):
                                    ui.label(f"{flow['name']}").classes('font-semibold text-gray-800')
                    ui.label(t('atoms.delete_risk_warning', 'Si lo eliminas, estos flujos podrían fallar.')).classes('text-sm text-gray-600 mb-4')
                else:
                    ui.label(t('atoms.delete_confirm_title', 'Confirmar eliminación')).classes('text-lg font-bold text-gray-800 mb-4')
                    ui.label(t('atoms.delete_confirm_msg', 'Se eliminará permanentemente: {name}').replace('{name}', resource.name)).classes('text-gray-700 mb-4')
                
                with ui.row().classes('w-full justify-end gap-2'):
                    ui.button(t('common.cancel'), on_click=confirm_dialog.close).props('outline')
                    async def execute_delete():
                        confirm_dialog.close()
                        await script_library_service.delete_script(resource.id, force=True)
                        ui.notify(t('common.deleted_success', name=resource.name), type='positive')
                        await load_resources()
                    ui.button(t('common.delete'), on_click=execute_delete, color='red')
            confirm_dialog.open()
        except Exception as e: ui.notify(f'Error: {e}', type='negative')

    # Initial Load
    await load_resources()

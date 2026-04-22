"""
Pagina unificada de Paquetes (Importacion/Exportacion).
Combina Prompt 2.3 (Exportacion) y Prompt 3.3 (Importacion).

Permite al usuario:
- Exportar scripts, playbooks y workflows.
- Importar paquetes .automatia validados.
"""

import asyncio
import base64
import json
from typing import List, Dict, Any, Set, Optional
from nicegui import ui, events

from client_app.app.core.state import state
from client_app.app.services.automatism_export_service import automatism_export_service
from client_app.app.services.automatism_import_service import (
    automatism_import_service,
    ConflictResolution,
    ImportResult
)
from client_app.app.services.import_validation_service import (
    import_validation_service,
    ValidationResult,
    ImportPermission
)
from client_app.app.services.custom_script_service import custom_script_service

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from client_app.app.database.db import client_engine
from client_app.app.database.models import FlowRegistry, RpaPlaybook, CustomScript


class PackagesPageState:
    """
    Mantiene el estado reactivo de la página de Paquetes (Importación/Exportación).
    Gestiona la selección de activos para exportar, los archivos subidos para importar,
    los resultados de validación y la resolución de conflictos de nombres.
    """

    def __init__(self):
        # --- EXPORT STATE ---
        self.selected_scripts: Set[int] = set()
        self.selected_playbooks: Set[int] = set()
        self.selected_workflows: Set[int] = set()

        self.scripts: List[CustomScript] = []
        self.playbooks: List[RpaPlaybook] = []
        self.workflows: List[FlowRegistry] = []

        self.package_name: str = ""
        self.package_description: str = ""
        self.include_dependencies: bool = True

        self.is_loading: bool = False
        self.is_exporting: bool = False
        self.export_error: str = ""
        self.load_error: str = ""

        # --- IMPORT STATE ---
        self.uploaded_file: Optional[bytes] = None
        self.uploaded_filename: str = ""
        self.validation_result: Optional[ValidationResult] = None
        self.import_result: Optional[ImportResult] = None
        
        self.is_validating: bool = False
        self.is_importing: bool = False
        self.import_error: str = ""
        
        # Conflict resolutions: {name: resolution}
        self.conflict_resolutions: Dict[str, ConflictResolution] = {}

    # --- Export Properties ---
    @property
    def total_selected(self) -> int:
        return (
            len(self.selected_scripts) +
            len(self.selected_playbooks) +
            len(self.selected_workflows)
        )

    def can_export(self) -> bool:
        return self.total_selected > 0 and len(self.package_name.strip()) > 0
        
    # --- Import Helpers ---
    def reset_import(self):
        """Reinicia el estado de importación para permitir procesar un nuevo archivo."""
        self.uploaded_file = None
        self.uploaded_filename = ""
        self.validation_result = None
        self.import_result = None
        self.import_error = ""
        self.conflict_resolutions = {}


def packages_page_content():
    """
    Controlador principal de la interfaz unificada de Paquetes (.automatia).
    Permite empaquetar flujos de trabajo con sus dependencias para portabilidad 
    e importar activos verificando su integridad, firmas y permisos.
    """
    # Use fallback translations if keys missing
    def t(key, default=None):
        val = state.i18n.t(key)
        if val == key and default:
            return default
        return val

    wizard = PackagesPageState()

    # === CARGA DE DATOS (Export) ===

    async def load_data():
        """
        Carga todos los activos exportables (scripts, playbooks, workflows) 
        registrados en la base de datos local del cliente.
        """
        wizard.is_loading = True
        render_export_tab.refresh()

        try:
            # Cargar scripts
            wizard.scripts = await custom_script_service.get_all_scripts()

            # Cargar playbooks
            async with AsyncSession(client_engine) as session:
                result = await session.exec(select(RpaPlaybook))
                wizard.playbooks = list(result.all())

            # Cargar workflows
            async with AsyncSession(client_engine) as session:
                result = await session.exec(
                    select(FlowRegistry).where(FlowRegistry.is_active == True)
                )
                wizard.workflows = list(result.all())

        except Exception as e:
            wizard.load_error = str(e)
        finally:
            wizard.is_loading = False
            render_export_tab.refresh()


    # === IMPORT ACTIONS ===

    async def handle_upload(e: events.UploadEventArguments):
        """
        Gestiona la subida de un archivo de paquete. 
        Inicia el proceso de validación estructural y de seguridad mediante 
        el servicio de validación de importaciones.
        """
        """Maneja la carga del archivo .automatia."""
        try:
            # Normalization to avoid issues
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9\._-]', '_', e.file.name)
            
            content = await e.file.read()
            if not isinstance(content, (bytes, bytearray)):
                 ui.notify(f"Error: El contenido del archivo no es válido ({type(content).__name__}).", type='negative')
                 return
            
            wizard.uploaded_file = content
            wizard.uploaded_filename = safe_name
            wizard.is_validating = True
            render_import_tab.refresh()
            
            # Validar
            wizard.validation_result = await import_validation_service.validate_package(content)
            
            # Inicializar resoluciones de conflictos
            wizard.conflict_resolutions = {}
            for conflict in wizard.validation_result.conflicts:
                # Default logic: Rename
                wizard.conflict_resolutions[conflict['name']] = ConflictResolution.RENAME
                
        except Exception as ex:
            wizard.import_error = f"Error validando paquete: {str(ex)}"
        finally:
            wizard.is_validating = False
            render_import_tab.refresh()

    async def do_import():
        """
        Ejecuta la importación definitiva del paquete.
        Aplica las resoluciones de conflictos seleccionadas por el usuario y 
        persiste los nuevos activos en la base de datos.
        """
        """Ejecuta la importacion."""
        if not wizard.validation_result or not wizard.validation_result.is_valid:
            return
            
        if wizard.validation_result.permission == ImportPermission.DENIED:
            ui.notify("Permiso denegado para importar este paquete", type='negative')
            return
            
        if wizard.validation_result.permission == ImportPermission.REQUIRES_PARTNER:
            ui.notify("Este paquete requiere aprobación del partner para su importación (contacto directo requerido)", type='warning')
            return

        wizard.is_importing = True
        render_import_tab.refresh()
        
        try:
            result = await automatism_import_service.import_package(
                package_bytes=wizard.uploaded_file,
                conflict_resolutions=wizard.conflict_resolutions
            )
            wizard.import_result = result
            
            if result.success:
                ui.notify(f"Importacion exitosa: {result.scripts_imported} scripts, {result.playbooks_imported} playbooks", type='positive')
                # Recargar datos para la tab de exportacion/visualizacion
                await load_data()
            else:
                ui.notify("Importacion fallo", type='negative')
                
        except Exception as ex:
            wizard.import_error = f"Error importando: {str(ex)}"
            ui.notify(t('admin.packages.import_error', 'Error importando: {error}').format(error=str(ex)), type='negative')
        finally:
            wizard.is_importing = False
            render_import_tab.refresh()

    # === EXPORT ACTIONS ===
    
    # ... helpers for export selection ...
    def toggle_script(script_id: int, selected: bool):
        if selected: wizard.selected_scripts.add(script_id)
        else: wizard.selected_scripts.discard(script_id)
        render_export_options.refresh()

    def toggle_playbook(playbook_id: int, selected: bool):
        if selected: wizard.selected_playbooks.add(playbook_id)
        else: wizard.selected_playbooks.discard(playbook_id)
        render_export_options.refresh()

    def toggle_workflow(workflow_id: int, selected: bool):
        if selected: wizard.selected_workflows.add(workflow_id)
        else: wizard.selected_workflows.discard(workflow_id)
        render_export_options.refresh()
        
    async def do_export():
        """
        Inicia el proceso de empaquetado y exportación.
        Resuelve dependencias si es necesario, genera el archivo .automatia 
        y activa la descarga en el navegador del usuario.
        """
        """Ejecuta la exportacion y ofrece descarga."""
        if not wizard.can_export():
            ui.notify(t('export_pkg.error_no_selection', 'Seleccione items y un nombre'), type='warning')
            return

        wizard.is_exporting = True
        wizard.export_error = ""
        render_export_options.refresh()

        try:
            # Determinar tipo de exportacion
            # (Simplificado: siempre usa export_package, si solo workflow usa export_workflow)
            # Logica existente de export_page.py...
            if wizard.selected_workflows and not wizard.selected_scripts and not wizard.selected_playbooks:
                if len(wizard.selected_workflows) == 1:
                    flow_id = list(wizard.selected_workflows)[0]
                    result = await automatism_export_service.export_workflow(
                        flow_id=flow_id,
                        name=wizard.package_name,
                        include_dependencies=wizard.include_dependencies,
                        description=wizard.package_description
                    )
                else:
                    # Multiples workflows
                    all_script_ids = set()
                    all_playbook_ids = set()
                    for flow_id in wizard.selected_workflows:
                        flow = next((w for w in wizard.workflows if w.id == flow_id), None)
                        if flow:
                            deps = await automatism_export_service._resolve_workflow_dependencies(flow)
                            all_script_ids.update(s.id for s in deps['scripts'])
                            all_playbook_ids.update(p.id for p in deps['playbooks'])
                    
                    result = await automatism_export_service.export_package(
                        name=wizard.package_name,
                        script_ids=list(all_script_ids) if all_script_ids else None,
                        playbook_ids=list(all_playbook_ids) if all_playbook_ids else None,
                        description=wizard.package_description
                    )
            else:
                 result = await automatism_export_service.export_package(
                    name=wizard.package_name,
                    script_ids=list(wizard.selected_scripts) if wizard.selected_scripts else None,
                    playbook_ids=list(wizard.selected_playbooks) if wizard.selected_playbooks else None,
                    description=wizard.package_description
                )

            # Ofrecer descarga
            if isinstance(result, bytes) or isinstance(result, str):
                # Si es str es path, leerlo
                if isinstance(result, str):
                    with open(result, 'rb') as f:
                        file_bytes = f.read()
                else:
                    file_bytes = result
                    
                filename = f"{wizard.package_name.replace(' ', '_')}.automatia"
                b64_content = base64.b64encode(file_bytes).decode('utf-8')

                ui.run_javascript(f'''
                    const link = document.createElement('a');
                    link.href = 'data:application/zip;base64,{b64_content}';
                    link.download = '{filename}';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                ''')

                ui.notify(t('export_pkg.success', 'Paquete exportado correctamente'), type='positive')
                
                # Limpiar
                wizard.selected_scripts.clear()
                wizard.selected_playbooks.clear()
                wizard.selected_workflows.clear()
                wizard.package_name = ""
                wizard.package_description = ""
                render_export_tab.refresh()

        except Exception as e:
            wizard.export_error = str(e)
            ui.notify(f"Error: {e}", type='negative')
        finally:
            wizard.is_exporting = False
            render_export_options.refresh()


    # === UI RENDERING ===

    @ui.refreshable
    def render_import_tab():
        """
        Renderiza la interfaz de importación.
        Muestra la zona de carga, el resumen de validación, la gestión de conflictos
        y el progreso de la tarea de importación.
        """
        # 1. Zona de carga (si no hay archivo cargado)
        if not wizard.uploaded_file:
            with ui.card().classes('w-full p-8 items-center justify-center border-2 border-dashed border-gray-300 bg-gray-50'):
                ui.icon('cloud_upload', size='4em').classes('text-gray-400 mb-4')
                ui.label(t('admin.packages.import_hint')).classes('text-gray-600 font-medium')
                ui.upload(
                    on_upload=handle_upload,
                    auto_upload=True,
                    max_files=1
                ).props('accept=.automatia').classes('w-full max-w-xs')
            return

        # 2. Spinner validando
        if wizard.is_validating:
            with ui.column().classes('w-full items-center justify-center py-8'):
                ui.spinner(size='lg')
                ui.label(t('admin.packages.validating', 'Validando paquete...')).classes('text-gray-500 mt-2')
            return

        # 3. Resultado de Validacion
        if wizard.validation_result:
            validation = wizard.validation_result
            
            # Header del paquete
            with ui.card().classes('w-full p-4 mb-4 bg-white border border-gray-200'):
                 with ui.row().classes('w-full items-center justify-between'):
                    with ui.row().classes('items-center gap-3'):
                        ui.icon('inventory_2', size='2em').classes('text-blue-600')
                        with ui.column().classes('gap-0'):
                            ui.label(validation.manifest.get('name', 'Sin nombre')).classes('text-xl font-bold')
                            ui.label(validation.manifest.get('description', '')).classes('text-gray-500 text-sm')
                    
                    # Boton cancelar/limpiar
                    ui.button(t('admin.packages.change_file'), icon='close', on_click=wizard.reset_import).props('flat dense color=grey')

            # Panel de Estado (Permisos e Integridad)
            with ui.row().classes('w-full gap-4 mb-4'):
                # Integridad
                with ui.card().classes('flex-1 p-3 items-center'):
                     if validation.is_valid:
                         ui.icon('check_circle', color='green', size='2em')
                         ui.label('Integridad Verificada').classes('font-bold text-green-700')
                     else:
                         ui.icon('error', color='red', size='2em')
                         ui.label('Paquete Inválido').classes('font-bold text-red-700')
                         
                # Firma
                with ui.card().classes('flex-1 p-3 items-center'):
                    sig = validation.manifest.get("signature", {})
                    if sig.get("type") == "PARTNER":
                        ui.icon('verified_user', color='purple', size='2em')
                        ui.label(t('admin.packages.partner_signed')).classes('font-bold text-purple-700')
                    else:
                        ui.icon('fingerprint', color='blue', size='2em')
                        ui.label(t('admin.packages.client_signed')).classes('font-bold text-blue-700')

                # Permisos
                with ui.card().classes('flex-1 p-3 items-center'):
                    if validation.permission == ImportPermission.ALLOWED:
                        ui.icon('lock_open', color='green', size='2em')
                        ui.label(t('admin.packages.import_allowed')).classes('font-bold text-green-700')
                    elif validation.permission == ImportPermission.REQUIRES_PARTNER:
                        ui.icon('lock_clock', color='orange', size='2em')
                        ui.label(t('admin.packages.requires_approval')).classes('font-bold text-orange-700')
                    else:
                        ui.icon('lock', color='red', size='2em')
                        ui.label(t('admin.packages.import_denied')).classes('font-bold text-red-700')

            # Resumen de Contenido
            with ui.card().classes('w-full p-4 mb-4'):
                ui.label(t('admin.packages.package_content')).classes('font-bold mb-2')
                with ui.row().classes('gap-4'):
                    contents = validation.manifest.get("contents", {})
                    if contents.get("scripts"):
                        ui.chip(f'{len(contents["scripts"])} Scripts', icon='code')
                    if contents.get("playbooks"):
                        ui.chip(f'{len(contents["playbooks"])} Playbooks', icon='travel_explore')
                    if contents.get("workflows"):
                        ui.chip(f'{len(contents["workflows"])} Workflows', icon='account_tree')

            # Conflictos
            if validation.conflicts:
                with ui.card().classes('w-full p-4 mb-4 border border-orange-200 bg-orange-50'):
                    with ui.row().classes('items-center gap-2 mb-2'):
                        ui.icon('warning', color='orange')
                        ui.label(f"{t('admin.packages.conflicts_detected')} ({len(validation.conflicts)})").classes('font-bold text-orange-800')
                    
                    for conflict in validation.conflicts:
                        with ui.row().classes('w-full items-center justify-between p-2 bg-white rounded shadow-sm mb-1'):
                            with ui.row().classes('items-center gap-2'):
                                icon = 'code' if conflict['type'] == 'script' else ('travel_explore' if conflict['type'] == 'playbook' else 'account_tree')
                                ui.icon(icon, color='gray')
                                ui.label(conflict['name']).classes('font-medium')
                                ui.label(f"({t('admin.packages.already_exists')})").classes('text-xs text-red-500')
                            
                            # Opciones de resolucion
                            ui.toggle(
                                options={
                                    ConflictResolution.RENAME: t('admin.packages.rename'),
                                    ConflictResolution.OVERWRITE: t('admin.packages.overwrite'),
                                    ConflictResolution.SKIP: t('admin.packages.skip')
                                },
                                value=wizard.conflict_resolutions.get(conflict['name'], ConflictResolution.RENAME),
                                on_change=lambda e, name=conflict['name']: wizard.conflict_resolutions.update({name: e.value})
                            ).props('dense toggle-color=primary')

            # Errores/Warnings
            if validation.errors:
                with ui.card().classes('w-full p-4 bg-red-50 mb-4'):
                    ui.label(t('admin.packages.blocking_errors')).classes('font-bold text-red-800')
                    for err in validation.errors:
                        ui.label(f"• {err}").classes('text-red-600 ml-2')

            if validation.warnings:
                with ui.card().classes('w-full p-4 bg-yellow-50 mb-4'):
                    ui.label(t('admin.packages.warnings')).classes('font-bold text-yellow-800')
                    for warn in validation.warnings:
                        ui.label(f"• {warn}").classes('text-yellow-700 ml-2')

            # Botones Finales
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button(t('common.cancel'), on_click=wizard.reset_import).props('flat')
                
                import_btn = ui.button(
                    t('admin.packages.import_button'),
                    icon='file_download',
                    on_click=do_import
                ).props('color=primary')
                
                if not validation.is_valid or validation.permission == ImportPermission.DENIED:
                    import_btn.props('disable')
                
                if wizard.is_importing:
                    import_btn.props('loading')

        # 4. Resultado Final
        if wizard.import_result:
            with ui.card().classes('w-full p-8 items-center justify-center bg-green-50'):
                result = wizard.import_result
                if result.success:
                    ui.icon('check_circle', color='green', size='4em').classes('mb-4')
                    ui.label(t('admin.packages.import_success')).classes('text-2xl font-bold text-green-800 mb-2')
                    ui.label(t('admin.packages.import_summary', scripts=result.scripts_imported, playbooks=result.playbooks_imported, workflows=result.workflows_imported)).classes('text-center mb-6')
                    ui.button(t('common.close'), on_click=wizard.reset_import).props('color=primary')
                else:
                    ui.icon('error', color='red', size='4em').classes('mb-4')
                    ui.label(t('admin.packages.import_failed', 'Hubo problemas en la importación')).classes('text-2xl font-bold text-red-800')



    @ui.refreshable
    def render_export_tab():
        """
        Renderiza la interfaz de selección de activos para exportación.
        Organiza scripts, playbooks y flujos en pestañas categorizadas.
        """
        if wizard.is_loading:
            ui.spinner(size='lg')
            return

        with ui.column().classes('w-full gap-6'):
            # SECCIÓN 1: SELECCIÓN DE CONTENIDO (Full Width)
            with ui.card().classes('w-full'):
                with ui.tabs().classes('w-full') as tabs:
                    tab_scripts = ui.tab('Scripts', label=t('admin.packages.no_scripts') if not wizard.scripts else 'Scripts')
                    tab_playbooks = ui.tab('Playbooks', label=t('admin.packages.no_playbooks') if not wizard.playbooks else 'Playbooks')
                    tab_workflows = ui.tab('Workflows', label=t('admin.packages.no_workflows') if not wizard.workflows else 'Workflows')

                with ui.tab_panels(tabs, value=tab_scripts).classes('w-full'):
                    
                    # SCRIPTS TAB
                    with ui.tab_panel(tab_scripts).classes('p-4'):
                        if not wizard.scripts:
                            ui.label(t('admin.packages.no_scripts')).classes('text-gray-500 italic')
                        else:
                            for script in wizard.scripts:
                                is_sel = script.id in wizard.selected_scripts
                                with ui.card().classes(f'w-full p-2 mb-1 cursor-pointer {"bg-blue-50 border-blue-300" if is_sel else ""}') \
                                    .on('click', lambda s=script: toggle_script(s.id, s.id not in wizard.selected_scripts)):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.checkbox(value=is_sel, on_change=lambda e, s=script: toggle_script(s.id, e.value))
                                        ui.label(script.name).classes('font-bold')
                                        ui.badge(script.status).props('color=grey' if script.status=='draft' else 'green')

                    # PLAYBOOKS TAB
                    with ui.tab_panel(tab_playbooks).classes('p-4'):
                        if not wizard.playbooks:
                            ui.label(t('admin.packages.no_playbooks')).classes('text-gray-500 italic')
                        else:
                            for pb in wizard.playbooks:
                                is_sel = pb.id in wizard.selected_playbooks
                                with ui.card().classes(f'w-full p-2 mb-1 cursor-pointer {"bg-purple-50 border-purple-300" if is_sel else ""}') \
                                    .on('click', lambda p=pb: toggle_playbook(p.id, p.id not in wizard.selected_playbooks)):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.checkbox(value=is_sel, on_change=lambda e, p=pb: toggle_playbook(p.id, e.value))
                                        ui.label(pb.name).classes('font-bold')

                    # WORKFLOWS TAB
                    with ui.tab_panel(tab_workflows).classes('p-4'):
                        if not wizard.workflows:
                            ui.label(t('admin.packages.no_workflows')).classes('text-gray-500 italic')
                        else:
                            for wf in wizard.workflows:
                                is_sel = wf.id in wizard.selected_workflows
                                with ui.card().classes(f'w-full p-2 mb-1 cursor-pointer {"bg-green-50 border-green-300" if is_sel else ""}') \
                                    .on('click', lambda w=wf: toggle_workflow(w.id, w.id not in wizard.selected_workflows)):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.checkbox(value=is_sel, on_change=lambda e, w=wf: toggle_workflow(w.id, e.value))
                                        ui.label(wf.name).classes('font-bold')

            # SECCIÓN 2: OPCIONES (Full Width abajo)
            render_export_options()

    @ui.refreshable
    def render_export_options():
        """Opciones de exportación en formato grid."""
        with ui.card().classes('w-full p-6'):
            ui.label(t('admin.packages.export_options')).classes('text-lg font-bold mb-4')
            
            # Fila 1: Nombre y Descripción (2 columnas)
            with ui.row().classes('w-full gap-8 mb-6'):
                # Columna 1
                ui.input(t('admin.packages.package_name')).bind_value(wizard, 'package_name').classes('w-1/2')
                
                # Columna 2
                ui.input(t('common.description')).bind_value(wizard, 'package_description').classes('w-1/2')
            
            # Fila 2: Dependencias y Botón (2 columnas)
            with ui.row().classes('w-full gap-8 items-start'):
                # Columna 1: Checkbox Dependencias + Warning
                with ui.column().classes('w-1/2'):
                    cb = ui.checkbox(t('admin.packages.include_deps')).bind_value(wizard, 'include_dependencies')
                    with cb:
                        ui.tooltip(t('admin.packages.deps_tooltip')).classes('bg-gray-800 text-white p-2 text-sm')
                    
                    # Warning visible solo si está desmarcado
                    with ui.row().classes('items-center gap-2 text-orange-600 bg-orange-50 p-2 rounded').bind_visibility_from(wizard, 'include_dependencies', backward=lambda x: not x):
                        ui.icon('warning', size='sm')
                        ui.label(t('admin.packages.deps_warning')).classes('text-xs leading-tight')

                # Columna 2: Botón Exportar + Contador
                with ui.row().classes('w-1/2 items-center justify-end gap-4'):
                    count = wizard.total_selected
                    if count > 0:
                        ui.label(f"{count} {t('admin.packages.items_selected')}").classes('text-gray-500 text-sm')
                    
                    btn = ui.button(t('admin.packages.export_button'), icon='file_upload', on_click=do_export).props('color=black text-color=white')
                    if not wizard.can_export():
                        btn.props('disable')
                    if wizard.is_exporting:
                        btn.props('loading')


    # === MAIN LAYOUT ===
    with ui.column().classes('w-full h-full max-w-7xl mx-auto p-4'):
        # Tabs Principales (Header removed per unified style)

        # Tabs Principales
        with ui.tabs().classes('w-full text-lg') as main_tabs:
            tab_import = ui.tab('Importar', label=t('common.import'))
            tab_export = ui.tab('Exportar', label=t('common.export'))

        with ui.tab_panels(main_tabs, value=tab_import).classes('w-full bg-transparent'):
            
            # Pestaña Importar
            with ui.tab_panel(tab_import).classes('p-0 pt-4'):
                render_import_tab()

            # Pestaña Exportar
            with ui.tab_panel(tab_export).classes('p-0 pt-4'):
                render_export_tab()
    
    # Cargar datos al inicio
    asyncio.create_task(load_data())

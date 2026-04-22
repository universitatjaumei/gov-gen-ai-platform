from nicegui import ui
from automatia_shared.enums import StepType
from client_app.app.services.layout_manager import layout_manager
from client_app.app.core.state import state as app_state
from client_app.app.services.script_library_service import script_library_service
from client_app.app.services.atom_service import atom_service
from client_app.app.services.flow_registry_service import flow_registry_service
from client_app.app.config.capability_map import get_atom_capability, DEFAULT_CAPABILITY

class DrawerHub:
    """
    Panel de asistencia contextual con 3 pestañas:
    1. Ajustes (stepper): Galería de átomos + Wizard de configuración.
       - Si no hay paso seleccionado → muestra galería de átomos
       - Si hay paso seleccionado → muestra wizard de configuración
    2. Variables (pills): Pills disponibles del flujo.
    3. Copiloto (copilot): Sugerencias e IA.

    IMPORTANTE: El estado de pestañas se sincroniza con layout_manager.active_tab
    mediante binding reactivo de NiceGUI (no watchers manuales).
    """

    def __init__(self):
        self._tab_panels_component = None  # Referencia a tab_panels
        self.t = app_state.i18n.t

    @ui.refreshable
    def _render_content(self):
        """Renderiza el contenido interno del drawer (tabs + paneles)."""
        # 1. Resolver capacidades actuales
        # PRIORIDAD 1: Modo flow_edit (solo Copiloto)
        # PRIORIDAD 2: Modo diseño standalone (tipo explícito en layout_manager)
        # PRIORIDAD 3: Modo edición desde flujo (editing_step)
        is_flow_edit_mode = layout_manager.current_mode == 'flow_edit'
        atom_type = layout_manager.designing_atom_type

        if is_flow_edit_mode:
            # En modo flow_edit mostramos todas las pestañas: Galería (stepper), Variables (pills) y Copiloto
            cap = DEFAULT_CAPABILITY
            cap_has_stepper = True
            cap_has_variables = True
        elif atom_type:
            cap = get_atom_capability(atom_type)
            cap_has_stepper = cap.has_stepper
            cap_has_variables = cap.has_variables
        elif app_state.editing_step:
            cap = get_atom_capability(app_state.editing_step.type)
            cap_has_stepper = cap.has_stepper
            cap_has_variables = cap.has_variables
        else:
            # Default fallback
            cap = DEFAULT_CAPABILITY
            # Mostrar stepper en gallery mode o doc mode
            is_gallery_or_doc = layout_manager.current_mode in ['gallery', 'documentation']
            cap_has_stepper = is_gallery_or_doc
            # En modo documentación mostramos la pestaña de variables (pills) para los contratos
            cap_has_variables = layout_manager.current_mode == 'documentation'

        # Ya no ocultamos cap_has_variables en standalone porque necesitamos mostrar las variables globales.

        # 2. Ajustar pestaña activa si la actual está prohibida por capacidades
        if not cap_has_stepper and layout_manager.active_tab == 'stepper':
            layout_manager.active_tab = 'copilot'
        if not cap_has_variables and layout_manager.active_tab == 'pills':
            layout_manager.active_tab = 'copilot'

        # Ensure active_tab is at least one of the available ones
        valid_tabs = []
        if cap_has_stepper: valid_tabs.append('stepper')
        if cap_has_variables: valid_tabs.append('pills')
        valid_tabs.append('copilot')

        if layout_manager.active_tab not in valid_tabs:
            if not cap_has_stepper and cap_has_variables:
                layout_manager.active_tab = 'copilot'
            else:
                layout_manager.active_tab = valid_tabs[0]

        # 3. Renderizar Header
        with ui.row().classes('w-full items-center justify-between p-4 border-b border-slate-200 bg-slate-50/50'):
            with ui.row().classes('items-center gap-2'):
                if layout_manager.current_mode == 'gallery':
                    ui.icon('inventory_2', color='primary', size='sm')
                    ui.label(self.t('gallery.title', 'Galería de acciones')).classes('text-lg font-bold text-slate-800')
                else:
                    ui.icon('support_agent', color='primary', size='sm')
                    ui.label(self.t('drawer.title')).classes('text-lg font-bold text-slate-800')
            ui.button(icon='close', on_click=lambda: layout_manager.exit_focus_mode()).props('flat round dense color=grey')

        # 4. Renderizar Tabs (ocultar si solo hay Copiloto)
        tabs = None
        show_tabs = cap_has_stepper or cap_has_variables  # Solo mostrar tabs si hay más de una pestaña

        if show_tabs:
            with ui.tabs(value=layout_manager.active_tab).classes('w-full border-b border-slate-200 shadow-none').props('dense') as tabs:
                # Solo mostrar si capability lo permite
                if cap_has_stepper:
                    ui.tab('stepper', icon='tune').props('dense').classes('text-xs')

                if cap_has_variables:
                    ui.tab('pills', icon='data_object').props('dense').classes('text-xs')

                ui.tab('copilot', icon='auto_awesome').props('dense').classes('text-xs')

        # 5. Renderizar Paneles
        if show_tabs:
            with ui.tab_panels(tabs, value=layout_manager.active_tab).classes('w-full flex-grow') as tab_panels:
                self._tab_panels_component = tab_panels

                # Panel Stepper
                if cap_has_stepper:
                    with ui.tab_panel('stepper').classes('p-0'):
                        self._render_stepper_panel()

                if cap_has_variables:
                    with ui.tab_panel('pills').classes('p-4'):
                        self._render_pills_panel()

                with ui.tab_panel('copilot').classes('p-2'):
                    self._render_copilot_panel()
        else:
            # Solo Copiloto, renderizar directamente sin tabs
            with ui.column().classes('w-full flex-grow p-2'):
                self._render_copilot_panel()

        # Guardar referencia para sync externo
        self._tabs_component = tabs

    def render(self):
        """Renderiza el contenedor principal del drawer."""
        with ui.column().classes('w-full h-full p-0 gap-0') as container:
            self._render_content()

            # Estado local para detectar cambios
            sync_state = {
                'last_tab': layout_manager.active_tab,
                'last_mode': layout_manager.current_mode,
                'last_atom_type': layout_manager.designing_atom_type,
                'last_editing_step': app_state.editing_step,
                'last_doc_data': layout_manager.doc_atom_data,
                'last_step_index': (layout_manager.page_design_config or {}).get('current_step_index', 0),
                'last_gallery_filter': layout_manager.gallery_filter_step_type,
            }

            # Referencia al contenedor para verificar si sigue existiendo
            drawer_container = container

            def sync_drawer():
                """Sincroniza las pestañas y contenido con layout_manager."""
                # Verificar si el contenedor sigue existiendo
                if drawer_container.is_deleted:
                    return

                try:
                    needs_structure_refresh = False
                    needs_panel_refresh = False

                    # 1. Detectar cambios estructurales (tipo de átomo)
                    if layout_manager.designing_atom_type != sync_state['last_atom_type']:
                        sync_state['last_atom_type'] = layout_manager.designing_atom_type
                        needs_structure_refresh = True

                    if app_state.editing_step != sync_state['last_editing_step']:
                        sync_state['last_editing_step'] = app_state.editing_step
                        needs_structure_refresh = True

                    # 2. Detectar cambios de pestaña (solo visual)
                    if layout_manager.active_tab != sync_state['last_tab']:
                        sync_state['last_tab'] = layout_manager.active_tab
                        # Si la estructura no cambia, actualizamos el valor de los tabs existentes
                        if not needs_structure_refresh and getattr(self, '_tabs_component', None) is not None:
                            self._tabs_component.value = layout_manager.active_tab

                    # 3. Detectar cambios de modo (Layout mode)
                    if layout_manager.current_mode != sync_state['last_mode']:
                        sync_state['last_mode'] = layout_manager.current_mode
                        needs_structure_refresh = True # Cambiar a Estructural para recalcular visibilidad de TABS

                    # 4. Detectar cambios en el índice del stepper (fase del wizard)
                    current_step_index = (layout_manager.page_design_config or {}).get('current_step_index', 0)
                    if current_step_index != sync_state['last_step_index']:
                        sync_state['last_step_index'] = current_step_index
                        needs_panel_refresh = True

                    # 5. Detectar cambios en el filtro de galería (al vincular a diferentes pasos)
                    if layout_manager.gallery_filter_step_type != sync_state['last_gallery_filter']:
                        sync_state['last_gallery_filter'] = layout_manager.gallery_filter_step_type
                        needs_panel_refresh = True

                    # Ejecutar refrescos
                    if needs_structure_refresh:
                        self._render_content.refresh()
                    elif needs_panel_refresh:
                        self._render_stepper_panel.refresh()
                        self._render_pills_panel.refresh()
                        self._render_copilot_panel.refresh()

                except RuntimeError:
                    # El drawer ha sido destruido, no hacer nada más
                    return

                # Reprogramar el timer solo si el contenedor sigue existiendo
                if not drawer_container.is_deleted:
                    ui.timer(0.2, sync_drawer, once=True)

            # Timer inicial con once=True (se reprograma manualmente)
            ui.timer(0.2, sync_drawer, once=True)

    @ui.refreshable
    def _render_stepper_panel(self):
        # ... (resto igual)
        step = app_state.editing_step
        is_gallery_mode = layout_manager.current_mode == 'gallery'
        is_design_mode = layout_manager.current_mode == 'design'
        is_documentation_mode = layout_manager.current_mode == 'documentation'
        known_atom_type = layout_manager.designing_atom_type

        # Determinar qué mostrar
        if is_documentation_mode:
            # Modo documentación → mostrar README.md
            self._render_documentation_content()
        elif is_gallery_mode:
            # Modo galería explícito → mostrar galería
            self._render_gallery_content()
        elif is_design_mode and known_atom_type is not None:
            # PRIORIDAD: Modo diseño con tipo conocido (desde página específica) 
            # → mostrar wizard de progreso en lugar del formulario (que ya está en la página)
            self._render_design_progress(known_atom_type)
        else:
            # Fallback → mostrar galería
            self._render_gallery_content()

    @ui.refreshable
    def _render_pills_panel(self):
        """
        Muestra variables (pills) disponibles basándose en el contexto actual del editor.
        En modo documentación, muestra el contrato de datos del átomo.
        """
        # Modo documentación → mostrar contrato de datos
        # Modo documentación → mostrar contrato de datos
        if layout_manager.current_mode == 'documentation':
            self._render_contract_content()
            return

        # Verificar si el tipo de átomo actual tiene variables visibles
        if layout_manager.designing_atom_type:
            cap = get_atom_capability(layout_manager.designing_atom_type)
            if not cap.has_variables:
                with ui.column().classes('w-full items-center justify-center p-8 text-gray-400'):
                    ui.icon('do_not_disturb', size='lg').classes('mb-2')
                    ui.label(self.t('drawer.no_variables')).classes('text-sm italic')
                return

            # CHECK: ¿Qué modo de variables usar?
            if cap.variables_view_mode == 'schema_mapper':
                # Modo Mapeo de Esquema (API/SQL)
                from client_app.app.ui.components.schema_mapper import SchemaMapper
                
                step = app_state.editing_step
                if step:
                    mapper = SchemaMapper(step=step)
                    mapper.render()
                else:
                    ui.label(self.t('drawer.select_step')).classes('italic text-gray-500')
                return

            if cap.variables_view_mode == 'file_filter':
                # Modo Filtro de Archivos (Scanners)
                from client_app.app.ui.components.file_type_selector import FileTypeSelector

                step = app_state.editing_step
                page_config = layout_manager.page_design_config

                if step:
                    # Contexto de flujo: usar step
                    selector = FileTypeSelector(step=step)
                    selector.render()
                elif page_config is not None:
                    # Contexto de página standalone: usar config directa
                    selector = FileTypeSelector(config=page_config)
                    selector.render()
                else:
                    ui.label(self.t('drawer.select_step')).classes('italic text-gray-500')
                return

            if cap.variables_view_mode == 'define_outputs':
                # Generic Output Definition (Fallback)
                from client_app.app.ui.components.variable_editor import OutputVariableEditor
                step = app_state.editing_step
                if step:
                    editor = OutputVariableEditor(step=step)
                    editor.render()
                return

        from client_app.app.ui.components.variable_selector import render_variable_selector
        from client_app.app.services.data_flow_analyzer import data_flow_analyzer

        flow = app_state.editing_flow
        step = app_state.editing_step

        # Determinar índice del paso actual
        step_index = 0
        if step and flow and getattr(flow, 'steps', None):
            try:
                step_index = flow.steps.index(step)
            except ValueError:
                step_index = len(flow.steps)

        with ui.column().classes('w-full gap-4'):
            if flow:
                flow_name = getattr(flow, 'name', 'Flujo sin nombre')
                with ui.row().classes('items-center gap-2 p-2 bg-blue-50 w-full rounded border border-blue-100'):
                    ui.icon('account_tree', color='blue').classes('text-lg')
                    with ui.column().classes('gap-0'):
                        ui.label('CONTEXTO DE FLUJO').classes('text-[10px] font-bold text-blue-400')
                        ui.label(flow_name).classes('text-sm font-bold text-blue-900')
            else:
                with ui.row().classes('items-center gap-2 p-2 bg-gray-50 w-full rounded border border-gray-200'):
                    ui.icon('info', color='gray').classes('text-lg')
                    ui.label('Diseño independiente (sin flujo asociado)').classes('text-sm text-gray-600')

            ui.label(self.t('drawer.available_data')).classes('text-sm font-bold text-gray-400 uppercase tracking-wider')
            ui.label(self.t('drawer.variable_help')).classes('text-xs text-gray-500 mb-2')

            def handle_pill_click(ref):
                ui.notify(self.t('drawer.variable_copied', ref=ref), type='positive', position='bottom')
                # Intentar copiar al portapapeles si es posible en NiceGUI
                ui.run_javascript(f'navigator.clipboard.writeText("{ref}")')

            render_variable_selector(
                flow=flow,
                current_step_index=step_index,
                on_select=handle_pill_click,
                show_descriptions=True,
                compact=False
            )


    @ui.refreshable
    def _render_copilot_panel(self):
        """
        Panel del Copiloto con sugerencias contextuales y chat interactivo.

        Estructura:
        - En modo flow_edit: Panel de generación de propuestas de automatización
        - Parte superior: Sugerencias del CoherenceService (compactas)
        - Parte inferior: Chat interactivo con RAG
        """
        from client_app.app.services.coherence_service import CoherenceService
        from client_app.app.ui.components.copilot_chat import CopilotChat

        # Modo especial: Editor de flujos (solo Copiloto con generación de propuestas)
        is_flow_edit_mode = layout_manager.current_mode == 'flow_edit'

        coherence = CoherenceService()
        flow = app_state.editing_flow
        step = app_state.editing_step

        # Recopilar problemas actuales
        issues = []
        if step and not step.name:
            issues.append({'type': 'MISSING_NAME', 'message': self.t('drawer.no_name_warning')})

        suggestions = coherence.analyze_issues(issues)

        # Obtener ayuda contextual estática de la capacidad del átomo
        atom_type = layout_manager.designing_atom_type
        cap = get_atom_capability(atom_type) if atom_type else None
        context_help = cap.contextual_help if cap else []

        # Las sugerencias contextuales ahora vienen del copilot_context_service
        with ui.column().classes('w-full h-full gap-0'):
            # Ayuda contextual compacta (colapsable si hay mucho contenido)
            has_context_content = context_help or suggestions or layout_manager.designing_atom_type == StepType.ETL_TRANSFORM

            if has_context_content:
                # Usar expansion colapsable para no ocupar espacio
                with ui.expansion(
                    self.t('drawer.contextual_help', 'Ayuda contextual'),
                    icon='help_outline',
                    value=False  # Colapsado por defecto
                ).classes('w-full text-xs border-b shrink-0').props('dense'):
                    with ui.column().classes('w-full gap-2 p-2'):
                        # 1. Ayuda Contextual (Estatica)
                        for help_item in context_help:
                            with ui.row().classes('items-start gap-2'):
                                ui.icon(help_item.get('icon', 'lightbulb'), color='blue-700', size='xs')
                                ui.label(help_item['message']).classes('text-xs text-slate-600')

                        # 2. Sugerencias Dinámicas (Coherence)
                        for sugg in suggestions[:2]:
                            severity = sugg.get('severity', 'info')
                            color = 'orange' if severity == 'high' else 'blue'
                            with ui.row().classes('items-start gap-2'):
                                ui.icon('auto_fix_high', color=color, size='xs')
                                ui.label(sugg['description']).classes(f'text-xs text-{color}-700')

                        # Especial para ETL
                        if layout_manager.designing_atom_type == StepType.ETL_TRANSFORM:
                            ui.button('Analizar datos', icon='analytics', on_click=lambda: ui.run_javascript("emit('run_etl_analysis')"))\
                                .props('unelevated color=indigo dense size=sm')

            # Parte inferior: Chat interactivo (ocupa el resto del espacio)
            with ui.column().classes('w-full flex-1 min-h-0'):
                chat = CopilotChat()
                chat.render()

                # Inyectar sugerencias como mensajes del sistema si hay problemas criticos
                for sugg in suggestions:
                    if sugg.get('severity') == 'high':
                        chat.inject_system_message(
                            issue_type=sugg.get('type', 'warning'),
                            message=sugg.get('description', ''),
                            action_label=sugg.get('action_label'),
                            action_type=sugg.get('action_type')
                        )

    def refresh(self):
        """Método público para forzar actualización de paneles."""
        self._render_stepper_panel.refresh()
        self._render_pills_panel.refresh()
        self._render_copilot_panel.refresh()

    def _render_gallery_content(self):
        """Renderiza la galería de átomos dentro de la pestaña Ajustes."""
        from client_app.app.ui.components.atom_gallery import render_atom_gallery

        # Callback wrapper to handle selection
        async def on_select_wrapper(step_type, subtype=None, script_id=None, **kwargs):
            # Ejecutar el callback global (añade el átomo al flujo o navega a standalone)
            if app_state.on_atom_select_callback:
                try:
                    result = await app_state.on_atom_select_callback(step_type, subtype=subtype, script_id=script_id, **kwargs)
                except TypeError:
                    result = await app_state.on_atom_select_callback(step_type, subtype)
                # Si el callback devuelve True, significa que ya navegó y no debemos refrescar
                if result is True:
                    return

            # Refrescar el panel para mostrar el wizard si corresponde
            self._render_stepper_panel.refresh()

        with ui.column().classes('w-full h-full'):
            # Header contextual - diferente si hay filtro activo
            filter_type = layout_manager.gallery_filter_step_type
            with ui.row().classes('w-full items-center gap-2 p-4 border-b bg-slate-50'):
                if filter_type:
                    ui.icon('link', color='teal')
                    from client_app.app.config.atom_catalog import get_atom_metadata
                    from automatia_shared.enums import StepType
                    # filter_type puede ser StepType enum o string
                    if isinstance(filter_type, str):
                        try:
                            filter_type_enum = StepType[filter_type]
                        except KeyError:
                            filter_type_enum = None
                    else:
                        filter_type_enum = filter_type
                    if filter_type_enum:
                        meta = get_atom_metadata(filter_type_enum)
                        ui.label(self.t('drawer.link_action', type=meta.label, default=f'Vincular {meta.label}')).classes('font-bold text-slate-700')
                    else:
                        ui.label(self.t('drawer.link_action_generic', default='Vincular acción')).classes('font-bold text-slate-700')
                else:
                    ui.icon('add_circle', color='primary')
                    ui.label(self.t('drawer.select_resource')).classes('font-bold text-slate-700')

            # Container para la galería
            with ui.column().classes('w-full h-full') as container:
                async def load_gallery():
                    await render_atom_gallery(
                        container=container,
                        on_select=on_select_wrapper,
                        show_library=layout_manager.gallery_show_library,
                        wizard_mode=True,
                        filter_step_type=layout_manager.gallery_filter_step_type
                    )
                ui.timer(0.1, load_gallery, once=True)

    @ui.refreshable
    def _render_documentation_content(self):
        """Renderiza el README.md del átomo en modo documentación."""
        from client_app.app.ui.components.markdown_viewer import MarkdownViewer
        from pathlib import Path

        doc_data = layout_manager.doc_atom_data or {}
        atom_name = doc_data.get('name', self.t('drawer.atom_default_name'))
        doc_path = doc_data.get('doc_path')
        status = doc_data.get('status', 'PUBLISHED')

        with ui.column().classes('w-full h-full'):
            # Header con nombre del átomo
            with ui.row().classes('w-full items-center justify-between p-4 border-b bg-slate-50'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('menu_book', color='primary')
                    ui.label(self.t('drawer.doc_title', name=atom_name)).classes('font-bold text-slate-700')

            # Contenido del README / Metadatos
            with ui.scroll_area().classes('w-full flex-grow p-4'):
                # === SECCIÓN DE METADATOS (Nombre y Descripción) ===
                resource_id = doc_data.get('resource_id')
                rec_type = doc_data.get('record_type', 'atom')
                description = doc_data.get('description', '')
                
                if resource_id:
                    with ui.card().classes('w-full p-4 mb-4 bg-blue-50/30 border border-blue-100 shadow-none'):
                        ui.label(self.t('drawer.atom_metadata')).classes('text-xs font-bold text-blue-600 mb-2 uppercase')
                        
                        name_editor = ui.input(self.t('common.name'), value=atom_name).classes('w-full').props('outlined dense')
                        
                        # Only show description editor for FLOWS, not for atoms/library items
                        show_desc = rec_type == 'flow'
                        desc_editor = None
                        if show_desc:
                            desc_editor = ui.textarea(self.t('common.description'), value=description).classes('w-full').props('outlined autogrow')
                        
                        async def save_metadata():
                            try:
                                new_desc = desc_editor.value if desc_editor else description
                                if rec_type == 'library':
                                    await script_library_service.update_script_metadata(
                                        resource_id, name_editor.value, new_desc
                                    )
                                elif rec_type == 'flow':
                                    await flow_registry_service.update_flow_metadata(
                                        resource_id, name_editor.value, new_desc
                                    )
                                else:
                                    await atom_service.update_atom(
                                        atom_id=resource_id,
                                        name=name_editor.value,
                                        description=new_desc
                                    )
                                ui.notify(self.t('drawer.metadata_updated'), type='positive')
                                # Actualizar datos locales para reflejar el cambio en el header
                                layout_manager.doc_atom_data['name'] = name_editor.value
                                layout_manager.doc_atom_data['description'] = new_desc
                                self._render_documentation_content.refresh()
                            except Exception as e:
                                ui.notify(f"Error al guardar metadatos: {e}", type='negative')
                        
                        ui.button(self.t('drawer.save_metadata'), icon='save', on_click=save_metadata).classes('w-full mt-2 bg-blue-600 text-white')

                        # === BOTÓN CREAR NUEVA VERSIÓN ===
                        if status != 'DRAFT':
                            async def create_new_version():
                                try:
                                    if rec_type == 'atom':
                                        new_atom = await atom_service.create_new_version(resource_id)
                                        ui.notify(self.t('drawer.new_version_created', version=new_atom.version), type='positive')
                                        # Recargar drawer con el nuevo átomo (Opcional: navegar al editor)
                                        layout_manager.enter_documentation_mode(
                                            atom_name=new_atom.name, doc_path=new_atom.doc_path, status='DRAFT',
                                            description=new_atom.description, resource_id=new_atom.id, record_type='atom'
                                        )
                                    elif rec_type == 'flow':
                                        new_flow = await flow_registry_service.create_flow_version(resource_id)
                                        ui.notify(self.t('drawer.new_version_created', version=new_flow.version), type='positive')
                                        layout_manager.enter_documentation_mode(
                                            atom_name=new_flow.name, doc_path=None, status='DRAFT',
                                            description=new_flow.description, resource_id=new_flow.id, record_type='flow'
                                        )
                                    else:
                                        # Para library, el versionado es más complejo y depende del módulo original
                                        ui.notify(self.t('drawer.create_version_original'), type='info')
                                    
                                    self._render_documentation_content.refresh()
                                except Exception as e:
                                    ui.notify(f"Error al versionar: {e}", type='negative')

                            ui.button(self.t('drawer.create_new_version'), icon='content_copy', on_click=create_new_version)\
                                .classes('w-full mt-2 bg-purple-50 text-purple-700 border border-purple-200 shadow-none')

                ui.separator().classes('my-4')

                if doc_path:
                    path = Path(doc_path)
                    
                    def open_full_doc_viewer():
                        ui.navigate.to('/docs')

                    ui.label('Documentación Adjunta').classes('text-xs font-bold text-gray-500 uppercase mb-2')
                    ui.button('Leer Documentación Completa', icon='menu_book', on_click=open_full_doc_viewer)\
                        .classes('w-full bg-blue-50 text-blue-700 border border-blue-200 shadow-sm').props('outline')

                else:
                    with ui.column().classes('w-full items-center justify-center p-8 text-gray-400'):
                        ui.icon('description', size='lg').classes('mb-2')
                        ui.label(self.t('drawer.no_doc')).classes('text-sm italic')
                        ui.label(self.t('drawer.no_readme')).classes('text-xs')

    def _render_contract_content(self):
        """Renderiza enlaces al contrato de datos del átomo en modo documentación."""
        from client_app.app.ui.components.contract_viewer import ContractViewer

        doc_data = layout_manager.doc_atom_data or {}
        atom_name = doc_data.get('name', 'Acción')
        input_contract = doc_data.get('input_contract')
        output_contract = doc_data.get('output_contract')

        with ui.column().classes('w-full h-full p-4 gap-4'):
            if not input_contract and not output_contract:
                with ui.column().classes('w-full items-center justify-center p-8 text-gray-400'):
                    ui.icon('info', size='lg').classes('mb-2')
                    ui.label('Esta acción no tiene contrato de datos definido').classes('text-sm italic text-center')
            else:
                ui.label('Contratos de Datos').classes('text-xs font-bold text-gray-500 uppercase mb-2')
                
                def open_contract_dialog():
                    with ui.dialog() as contract_dialog, ui.card().classes('w-full max-w-4xl h-[80vh] flex flex-col p-0'):
                        with ui.row().classes('w-full justify-between items-center bg-slate-100 p-4 border-b shrink-0'):
                            ui.label(f"Contrato: {atom_name}").classes('text-xl font-bold text-slate-800')
                            ui.button(icon='close', on_click=contract_dialog.close).props('flat round color=slate-700')
                        
                        viewer = ContractViewer(
                            input_contract=input_contract,
                            output_contract=output_contract,
                            atom_name=atom_name
                        )
                        viewer.render()
                    contract_dialog.open()

                ui.button('Ver Contrato de Entradas y Salidas', icon='data_object', on_click=open_contract_dialog)\
                    .classes('w-full bg-green-50 text-green-700 border border-green-200 shadow-sm').props('outline')

    def _render_design_progress(self, atom_type):
        """Renderiza el progreso del diseño usando capability_map."""
        from client_app.app.config.atom_catalog import get_atom_metadata

        # Mapa de traducción de nombres de pasos (clave → clave de traducción)
        step_name_translations = {
            'Documento': 'stepper.document',
            'Campos': 'stepper.fields',
            'Generación': 'stepper.generation',
            'Validación': 'stepper.validation',
            'Descripción': 'stepper.description',
            'Validación y Sello': 'stepper.validation_seal',
            'Datos': 'stepper.data',
            'Transformación': 'stepper.transformation',
            'Revisión': 'stepper.review',
            'Config': 'stepper.config',
            'Preview': 'stepper.preview',
        }
        step_hint_translations = {
            'Sube documento de ejemplo': 'stepper.hint_upload_doc',
            'Define campos a extraer': 'stepper.hint_define_fields',
            'Script de extracción': 'stepper.hint_extraction_script',
            'Verifica resultados': 'stepper.hint_verify_results',
            'Limpieza y Privacidad': 'stepper.hint_data_cleaning',
            'Valida resultados': 'stepper.hint_validate_results',
            'Selecciona fuente de datos': 'stepper.hint_select_source',
            'Tipo y opciones de grafico': 'stepper.hint_chart_options',
            'Vista previa y guardado': 'stepper.hint_preview_save',
            'Define qué debe hacer': 'stepper.hint_define_action',
            'Código generado por IA': 'stepper.hint_ai_code',
            'Prueba y sella': 'stepper.hint_test_seal',
            'Código Python generado': 'stepper.hint_python_code',
            'Prueba y promociona': 'stepper.hint_test_promote',
        }

        def translate_step_name(name):
            key = step_name_translations.get(name)
            return self.t(key, name) if key else name

        def translate_step_hint(hint):
            key = step_hint_translations.get(hint)
            return self.t(key, hint) if key else hint

        # Obtener capacidades del átomo
        cap = get_atom_capability(atom_type)
        steps_config = cap.steps

        try:
            meta = get_atom_metadata(atom_type)
        except:
            meta = None

        with ui.scroll_area().classes('w-full h-full'):
            with ui.column().classes('w-full p-4 gap-4'):
                # Header con info del tipo de átomo
                with ui.row().classes('w-full items-center gap-3 p-3 bg-slate-50 rounded-lg'):
                    if meta:
                        ui.icon(meta.icon, color='primary', size='md')
                        with ui.column().classes('flex-1 gap-0'):
                            ui.label(meta.label).classes('font-bold text-slate-800')
                            ui.label(meta.description).classes('text-xs text-slate-500 line-clamp-2')
                    else:
                        ui.icon('settings', color='primary', size='md')
                        ui.label(f'Diseñando: {atom_type.value if hasattr(atom_type, "value") else str(atom_type)}').classes('font-bold')

                ui.separator()

                # Indicador de progreso del wizard
                ui.label(self.t('drawer.design_progress')).classes('text-sm font-bold text-gray-500 uppercase tracking-wider')

                for i, step_info in enumerate(steps_config):
                    # Usar configuración de la página de diseño si disponible
                    design_config = layout_manager.page_design_config or {}
                    current_idx = design_config.get('current_step_index', 0)
                    completed_idxs = design_config.get('completed_step_indexes', [])

                    is_current = (i == current_idx)
                    is_completed = (i in completed_idxs)

                    color = 'primary' if is_current else ('positive' if is_completed else 'grey')
                    icon = 'check_circle' if is_completed else ('radio_button_checked' if is_current else 'radio_button_unchecked')

                    with ui.row().classes(f'w-full items-center gap-3 p-2 rounded {"bg-blue-50" if is_current else ""}'):
                        ui.icon(icon, color=color).classes('text-lg')
                        with ui.column().classes('flex-1 gap-0'):
                            ui.label(translate_step_name(step_info['name'])).classes(f'{"font-bold" if is_current else "text-gray-600"}')
                            if step_info.get('hint'):
                                ui.label(translate_step_hint(step_info['hint'])).classes('text-xs text-gray-400')

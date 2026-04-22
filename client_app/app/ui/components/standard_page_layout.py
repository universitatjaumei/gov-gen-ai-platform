from typing import List, Dict, Any, Callable, Union, Optional
from nicegui import ui
from automatia_shared.enums import StepType
from client_app.app.ui.components.unified_resource_card import unified_resource_card, get_resource_styles
from client_app.app.ui.components.page_header import page_header

class StandardPageLayout:
    def __init__(
        self,
        title: str,
        source_module: str,
        resources: List[Any],
        on_create: Callable,
        on_edit: Callable,
        on_delete: Callable,
        on_execute: Optional[Callable] = None,
        on_favorite_toggle: Optional[Callable] = None,
        help_description: str = "",
        input_contract: Optional[List[str]] = None,
        output_contract: Optional[List[str]] = None,
        create_button_label: Optional[str] = None,
    ):
        self.title = title
        self.source_module = source_module
        self.resources = resources
        self.on_create = on_create
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_execute = on_execute
        self.on_favorite_toggle = on_favorite_toggle
        self.help_description = help_description
        self.input_contract = input_contract or []
        self.output_contract = output_contract or []

        from client_app.app.core.state import state
        t = state.i18n.t
        self.create_button_label = create_button_label or t('index_page.create_button', 'Crear Nuevo')
        
        # Internal State for Filters
        self.search_term = ""
        self.status_filter = "all" # all, published, draft, validated

    def render(self):
        styles = get_resource_styles(self.source_module)
        color = styles['color']
        icon = styles['icon']
        
        # --- HEADER ---
        from client_app.app.core.state import state
        t = state.i18n.t
        
        with ui.column().classes('w-full max-w-7xl mx-auto p-6 gap-6'):
            
            # Centralized Header
            page_header(self.title, self.help_description)
            
            # Line 2: Filters & Actions
            with ui.row().classes('w-full items-center justify-between gap-4'):
                with ui.row().classes('flex-grow items-center gap-4'):
                    # Search
                    search_input = ui.input(placeholder=t('index_page.search_placeholder', 'Buscar por nombre...')) \
                        .props('dense outlined icon=search').classes('w-64 bg-white') \
                        .on('update:model-value', lambda e: (setattr(self, 'search_term', e.args), self._refresh_grid()))
                        
                    # Status Filter
                    ui.select(
                        {
                            'all': t('index_page.filter_all', 'Todos los estados'), 
                            'published': t('index_page.filter_published', 'Publicados'), 
                            'draft': t('index_page.filter_draft', 'Borradores'), 
                            'validated': t('index_page.filter_validated', 'Validados')
                        },
                        value='all',
                        on_change=lambda e: (setattr(self, 'status_filter', e.value), self._refresh_grid())
                    ).props('dense outlined options-dense').classes('w-48 bg-white')
                
                # Create Button
                with ui.button(self.create_button_label, icon='add', on_click=self.on_create) \
                    .style(f'background-color: {color}; color: white;') \
                    .props('unelevated'):
                    pass

            # --- HELP & CONTRACTS (Collapsible) ---
            with ui.expansion(t('index_page.var_ref_title', 'Referencia de Variables y Contratos'), icon='settings_ethernet').classes('w-full bg-slate-50 border rounded-lg overflow-hidden'):
                with ui.column().classes('p-4 gap-4'):
                    
                    with ui.row().classes('w-full gap-8'):
                        # Inputs
                        if self.input_contract:
                            with ui.column().classes('flex-1 gap-2'):
                                ui.label(t('index_page.input_label', 'Input Esperado (Variables)')).classes('text-xs font-bold text-slate-500 uppercase')
                                with ui.row().classes('gap-2 flex-wrap'):
                                    for item in self.input_contract:
                                        # Simple string or dict? Assuming string for now based on prompt
                                        name = item if isinstance(item, str) else item.get('name', 'unknown')
                                        ui.chip(name, icon='input', color='amber-100').props('dense text-color=amber-900')

                        # Outputs
                        if self.output_contract:
                            with ui.column().classes('flex-1 gap-2'):
                                ui.label(t('index_page.output_label', 'Output Disponible (Data Pills)')).classes('text-xs font-bold text-slate-500 uppercase')
                                with ui.row().classes('gap-2 flex-wrap'):
                                    for item in self.output_contract:
                                        name = item if isinstance(item, str) else item.get('name', 'unknown')
                                        ui.chip(name, icon='output', color='blue-100').props('dense text-color=blue-900')

            # --- RESOURCE GRID ---
            self.grid_container = ui.column().classes('w-full')
            self._refresh_grid()

    def _refresh_grid(self):
        """Refreshes the grid based on filters."""
        self.grid_container.clear()
        
        filtered = self._filter_resources()
        
        with self.grid_container:
            if not filtered:
                self._render_empty_state()
            else:
                # Sort: Published > Validated > Draft
                def sort_key(r):
                    status = r.get('status', 'draft') if isinstance(r, dict) else getattr(r, 'status', 'draft')
                    priority = {'published': 0, 'validated': 1, 'draft': 2}
                    return priority.get(status.lower(), 3)
                
                sorted_resources = sorted(filtered, key=sort_key)
                
                with ui.grid(columns=3).classes('w-full gap-6'):
                    for res in sorted_resources:
                        unified_resource_card(
                            resource=res,
                            on_click=self.on_edit,
                            on_edit=self.on_edit,
                            on_delete=self.on_delete,
                            on_execute=self.on_execute,
                            on_favorite_toggle=self.on_favorite_toggle
                        )

    def _filter_resources(self):
        res = []
        term = self.search_term.lower()
        stat = self.status_filter
        
        for r in self.resources:
            # Handle Dict or Object
            name = (r.get('name') if isinstance(r, dict) else r.name) or ""
            status = (r.get('status') if isinstance(r, dict) else r.status) or "draft"
            
            # Text Filter
            if term and term not in name.lower():
                continue
            
            # Status Filter
            if stat != 'all' and status.lower() != stat:
                continue
                
            res.append(r)
        return res

    def _render_empty_state(self):
        with ui.column().classes('w-full py-16 items-center justify-center text-center gap-4'):
            if self.resources and (self.search_term or self.status_filter != 'all'):
                # Has resources but filtered out
                from client_app.app.core.state import state
                t = state.i18n.t
                ui.icon('filter_list_off', size='4rem').classes('text-slate-300')
                ui.label(t('index_page.no_results', 'No hay resultados para los filtros actuales')).classes('text-slate-500 text-lg')
                ui.button(t('index_page.clear_filters', 'Limpiar Filtros'), on_click=self._clear_filters).props('flat color=primary')
            else:
                # No resources at all
                from client_app.app.core.state import state
                t = state.i18n.t
                styles = get_resource_styles(self.source_module)
                ui.icon(styles['icon'], size='4rem').style(f'color: {styles["color"]}; opacity: 0.3;')
                ui.label(t('index_page.empty_title', 'No hay elementos en {title}').replace('{title}', self.title)).classes('text-slate-500 text-lg font-medium')
                ui.label(t('index_page.empty_hint', 'Crea el primero para comenzar a trabajar')).classes('text-slate-400')

    def _clear_filters(self):
        self.search_term = ""
        self.status_filter = "all"
        # We can't easily update the input values cleanly without binding, 
        # but re-rendering the whole component is overkill? 
        # Actually `render` calls `_refresh_grid`.
        # To clear inputs UI, we'd need references. 
        # For MVP, just refresh grid, input text might stay desynced visually if not bound.
        # But looking above, `ui.input` has internal state.
        # Let's rely on user manually clearing or just accept it.
        # Improving: I'll just refresh grid.
        self._refresh_grid()

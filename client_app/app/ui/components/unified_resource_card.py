
from nicegui import ui
import asyncio
from typing import Optional, Dict, Any, Union
from automatia_shared.enums import StepType
from client_app.app.database.models import ScriptLibrary
from client_app.app.services.script_library_service import script_library_service

# --- CONFIGURATION & MAPPINGS ---

def get_resource_styles(source_module: str) -> Dict[str, str]:
    """Returns color and icon configuration for a given module."""
    mod = source_module.lower() if source_module else 'custom'
    
    styles = {
        'extraction': {'icon': 'description', 'color': '#3b82f6'},
        'etl': {'icon': 'transform', 'color': '#22c55e'},
        'rpa': {'icon': 'travel_explore', 'color': '#9333ea'},
        'custom': {'icon': 'code', 'color': '#4f46e5'},
        'api': {'icon': 'api', 'color': '#0891b2'},
        'db': {'icon': 'storage', 'color': '#10b981'},
        'sql': {'icon': 'storage', 'color': '#10b981'},
        'mail': {'icon': 'email', 'color': '#d97706'},
        'email': {'icon': 'email', 'color': '#d97706'},
        'folder': {'icon': 'folder', 'color': '#ea580c'},
        'webhook': {'icon': 'link', 'color': '#7c3aed'},
        'smtp': {'icon': 'send', 'color': '#0d9488'},
        'graphics': {'icon': 'bar_chart', 'color': '#ec4899'},
    }
    
    return styles.get(mod, styles['custom'])

def get_status_styles(status: str) -> str:
    """Returns CSS styles for status badges."""
    s = status.lower() if status else 'draft'
    styles = {
        'draft': 'background-color: #f3f4f6; color: #4b5563;',
        'validated': 'background-color: #ffedd5; color: #c2410c;',
        'published': 'background-color: #dcfce7; color: #15803d;'
    }
    return styles.get(s, 'background-color: #f3f4f6; color: #6b7280;')

# --- COMPONENT ---

class UnifiedResourceCard:
    """
    Standardized card for all resources.
    Uses ultra-robust styling with base columns to ensure visibility.
    """
    def __init__(
        self,
        resource: Union[ScriptLibrary, Dict[str, Any]],
        on_execute=None,
        on_edit=None,
        on_delete=None,
        on_favorite_toggle=None,
        on_click=None,
        on_doc_click=None
    ):
        self.resource = resource
        self.on_execute = on_execute
        self.on_edit = on_edit
        self.on_delete = on_delete
        self.on_favorite_toggle = on_favorite_toggle
        self.on_click = on_click
        self.on_doc_click = on_doc_click

        # Extract properties
        if isinstance(resource, ScriptLibrary):
            self.id = resource.id
            self.name = resource.name or "Sin nombre"
            self.description = resource.description or "Sin descripción disponible."
            self.module = resource.source_module
            self.status = resource.status
            self.is_favorite = resource.is_favorite
            self.doc_path = resource.doc_path
            self.input_contract = getattr(resource, 'input_contract', None)
            self.output_contract = getattr(resource, 'output_contract', None)
            
            # Phase 4/5 logic for sample data
            meta = getattr(resource, 'source_metadata', {}) or {}
            self.has_sample_data = 'sample_data' in meta
            
            # Creation date
            raw_date = getattr(resource, 'created_at', None)
            self.created_at_str = self._format_date(raw_date)
        else:
            self.id = resource.get('id')
            self.name = resource.get('name', 'Sin nombre')
            self.description = resource.get('description', 'Sin descripción.')
            self.module = resource.get('source_module', 'custom')
            self.status = resource.get('status', 'published')
            self.is_favorite = resource.get('is_favorite', False)
            self.doc_path = resource.get('doc_path')
            self.input_contract = resource.get('input_contract')
            self.output_contract = resource.get('output_contract')
            
            meta = resource.get('source_metadata', {}) or {}
            self.has_sample_data = bool(resource.get('sample_data') or 'sample_data' in meta)
            
            # Creation date
            raw_date = resource.get('created_at')
            self.created_at_str = self._format_date(raw_date)

    @staticmethod
    def _format_date(value) -> str:
        """Format a datetime or ISO string as DD/MM/YYYY, or empty string if unavailable."""
        if not value:
            return ''
        try:
            from datetime import datetime
            if isinstance(value, str):
                # Accept ISO format: 2026-03-06T07:15:52 or 2026-03-06
                value = value[:19]  # strip microseconds/timezone
                dt = datetime.fromisoformat(value)
            elif hasattr(value, 'strftime'):
                dt = value
            else:
                return ''
            return dt.strftime('%d/%m/%Y')
        except Exception:
            return ''


    def render(self):
        """Renders the card using NiceGUI."""
        styles = get_resource_styles(self.module)
        accent_color = styles['color']
        icon_name = styles['icon']
        
        # Main Container - Manually styled column to act as a card
        # Compact height without description
        with ui.column().style(
            f'height: 100px; width: 100%; min-width: 220px; padding: 0; margin: 0; '
            f'border-left: 5px solid {accent_color}; overflow: hidden; '
            f'display: flex; flex-direction: column; background-color: white; '
            f'border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; '
            f'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);'
        ).classes('transition-all duration-300 hover:shadow-lg'):

            # --- UPPER CONTENT (Body) ---
            with ui.column().classes('w-full p-3 gap-0').style('flex-grow: 1; overflow: hidden; display: flex; flex-direction: column;'):

                # Header Row (Title and Favorite)
                with ui.row().classes('w-full items-center justify-between no-wrap'):
                    with ui.row().classes('gap-2 items-center flex-grow no-wrap'):
                        ui.icon(icon_name, size='1.1em').style(f'color: {accent_color}; flex-shrink: 0;')

                        # Name - CLICKABLE
                        name_el = ui.label(self.name).style(
                            'font-weight: 700; color: #1e293b; line-height: 1.25; font-size: 0.8rem; '
                            'overflow: hidden; text-overflow: ellipsis; white-space: nowrap; '
                            'cursor: pointer; flex-grow: 1;'
                        ).classes('hover:text-primary')
                        if self.on_click:
                            name_el.on('click', lambda: self.on_click(self.resource))

                    # Favorite Star (Standalone clickable element)
                    self._render_favorite_star()

            # --- LOWER BAR (Footer) ---
            with ui.row().classes('w-full px-3 py-1 items-center justify-between no-wrap') \
                         .style('background-color: #f8fafc; border-top: 1px solid #f1f5f9; height: 38px; flex-shrink: 0;'):
                
                # Status and Indicators
                with ui.row().classes('items-center gap-2 no-wrap'):
                    status_style = get_status_styles(self.status)
                    ui.label(self.status.upper()).style(
                        f'font-size: 8px; font-weight: 800; padding: 2px 8px; {status_style} white-space: nowrap;'
                    )
                    
                    # Creation date (shown when available)
                    if self.created_at_str:
                        ui.label(self.created_at_str).style(
                            'font-size: 9px; color: #94a3b8; font-weight: 500; white-space: nowrap;'
                        )
                    
                    if getattr(self, 'has_sample_data', False):
                        sample_icon = ui.icon('table_view', size='1.1em', color='blue-500') \
                            .tooltip('Datos de ejemplo disponibles') \
                            .classes('cursor-pointer hover:text-blue-700')
                        sample_icon.on('click.stop', lambda: self._show_sample_data())
                    
                    if self.doc_path:
                        doc_icon = ui.icon('description', size='1.1em', color='blue-grey-4') \
                            .tooltip('Ver documentación') \
                            .classes('cursor-pointer hover:text-primary')
                        doc_icon.on('click.stop', lambda: self._handle_doc_click())

                # Actions buttons
                with ui.row().classes('gap-0 no-wrap'):
                    EXECUTABLE_MODULES = ['custom', 'extraction', 'etl', 'rpa', 'graphics', 'anonymization', 'pdf_tools', 'anonymizer']
                    if self.status != 'draft' and self.on_execute and getattr(self, 'module', '') in EXECUTABLE_MODULES:
                        ui.button(on_click=lambda: self.on_execute(self.resource)) \
                            .props('icon=play_arrow round flat dense color=positive size=sm').tooltip('Ejecutar')
                    
                    if self.on_edit:
                        ui.button(on_click=lambda: self.on_edit(self.resource)) \
                            .props('icon=edit round flat dense color=primary size=sm').tooltip('Editar')
                    
                    if self.on_delete:
                        ui.button(on_click=lambda: self.on_delete(self.resource)) \
                            .props('icon=delete round flat dense color=negative size=sm').tooltip('Eliminar')

    def _handle_doc_click(self):
        """Maneja el click en el icono de documentación."""
        if self.on_doc_click:
            # Usar callback personalizado si existe
            self.on_doc_click(self.resource)
        else:
            # Comportamiento por defecto: abrir drawer en modo documentación
            from client_app.app.services.layout_manager import layout_manager
            
            # Get resource ID safely
            res_id = getattr(self.resource, 'id', None)
            
            # Determine record type for correct service selection
            from client_app.app.database.models import ScriptLibrary
            rec_type = 'library' if isinstance(self.resource, ScriptLibrary) else 'atom'
            
            layout_manager.enter_documentation_mode(
                atom_name=self.name,
                doc_path=self.doc_path,
                input_contract=self.input_contract,
                output_contract=self.output_contract,
                status=self.status,
                description=self.description,
                resource_id=res_id,
                record_type=rec_type
            )

    def _render_favorite_star(self):
        """Renders the star icon with toggle logic."""
        fav_icon = 'star' if self.is_favorite else 'star_border'
        fav_color = '#eab308' if self.is_favorite else '#cbd5e1'
        
        async def toggle():
            if self.on_favorite_toggle:
                await self.on_favorite_toggle(self.resource)
                return
            
            if isinstance(self.resource, ScriptLibrary) and self.id:
                self.is_favorite = not self.is_favorite
                star.props(f'name={"star" if self.is_favorite else "star_border"}')
                star.style(f'color: {"#eab308" if self.is_favorite else "#cbd5e1"};')
                asyncio.create_task(script_library_service.toggle_favorite(self.id))

        star = ui.icon(fav_icon).style(f'color: {fav_color}; cursor: pointer; font-size: 1.3em; flex-shrink: 0;')
        star.on('click.stop', toggle)

    def _show_sample_data(self):
        """Muestra un dialogo con la muestra de datos guardada."""
        async def fetch_and_show():
            data_dict = None
            if isinstance(self.resource, ScriptLibrary):
                from client_app.app.database.client_engine import AsyncSession, client_engine
                from client_app.app.database.models import ScriptLibrary as DBScript
                import json
                async with AsyncSession(client_engine) as session:
                    db_script = await session.get(DBScript, self.id)
                    if db_script and getattr(db_script, 'source_metadata', None):
                        sample_str = db_script.source_metadata.get('sample_data')
                        if sample_str:
                            if isinstance(sample_str, str):
                                try: data_dict = json.loads(sample_str)
                                except: pass
                            else:
                                data_dict = sample_str
            else:
                data_str = self.resource.get('sample_data')
                if not data_str and self.resource.get('source_metadata'):
                    data_str = self.resource['source_metadata'].get('sample_data')
                
                if data_str:
                    if isinstance(data_str, str):
                        import json
                        try: data_dict = json.loads(data_str)
                        except: pass
                    else:
                        data_dict = data_str

            if not data_dict or 'rows' not in data_dict:
                ui.notify("No se pudieron cargar los datos de ejemplo.", type='warning')
                return

            with ui.dialog() as dialog, ui.card().classes('min-w-[700px] max-w-4xl max-h-[80vh] flex flex-col p-0'):
                with ui.row().classes('w-full justify-between items-center bg-slate-50 p-4 border-b shrink-0 m-0'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('table_view', color='primary', size='md')
                        with ui.column().classes('gap-0'):
                            ui.label('Muestra de Datos Capturada').classes('text-lg font-bold text-slate-800')
                            ui.label(self.name).classes('text-sm text-slate-500')
                    
                    ui.button(icon='close', on_click=dialog.close).props('flat round dense')
                
                with ui.scroll_area().classes('w-full p-4 flex-grow bg-white'):
                    rows = data_dict.get('preview_rows', data_dict.get('rows', []))
                    if rows:
                        import pandas as pd
                        df = pd.DataFrame(rows)
                        ui.table.from_pandas(df).classes('w-full').props('dense flat bordered separator=cell')
                    else:
                        ui.label("Estructura sin filas configurada.").classes('text-slate-500 italic')
                        
                with ui.row().classes('w-full p-4 bg-slate-50 border-t justify-between shrink-0 items-center m-0'):
                    meta = data_dict.get('metadata', {})
                    if meta and 'generated_at' in meta:
                        date_str = meta['generated_at'][:16].replace('T', ' ')
                        ui.label(f"Capturado el: {date_str}").classes('text-xs text-slate-400')
                    else:
                        ui.space()
                    ui.button("Cerrar", on_click=dialog.close).props('outline color=primary')

            dialog.open()
            
        asyncio.create_task(fetch_and_show())

def unified_resource_card(**kwargs):
    """Factory function."""
    card = UnifiedResourceCard(**kwargs)
    card.render()
    return card

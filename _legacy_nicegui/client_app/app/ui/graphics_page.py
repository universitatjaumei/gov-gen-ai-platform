"""
Graphics Page - Redesigned with dual-mode (Assisted/AI) following ETL patterns.

Implements:
- Assisted Mode: Deterministic chart generation without AI
- AI Mode: Custom visualizations with generative AI
- Wizard-style UI with phases in drawer stepper
- Compact selectors and consistent styling
"""

from nicegui import ui, app
import pandas as pd
import io
import asyncio
import base64
import os
import hashlib
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import uuid4
from pathlib import Path

from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.ui.components.privacy_indicator import render_privacy_indicator
from client_app.app.modules.factory.graphics_factory import GraphicsFactory, GraphicsScript
from client_app.app.services.clarification_service import clarification_service, ClarificationResponse
from client_app.app.ui.components.clarification_dialog import ClarificationDialog
from client_app.app.services.asset_finishing_service import AssetFinishingService
from client_app.app.database.models import ScriptLibrary
from client_app.app.ui.components.data_source_selector import render_data_source_selector, DataSourceSelection, DataSourceSelectorState
from client_app.app.ui.components.standard_page_layout import StandardPageLayout
from client_app.app.models.chart_configuration import (
    ChartConfiguration, CHART_TYPES, COLOR_PALETTES, CHART_STYLES
)
from client_app.app.services.deterministic_graphics_service import DeterministicGraphicsService
from automatia_shared.enums import StepType
from client_app.app.services.naming_service import naming_service


# --- CONSTANTS ---
GRAPHICS_UPLOAD_DIR = Path("data/uploads/graphics")
GRAPHICS_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# --- STATE CLASSES ---

class GraphicsState:
    """Global state for the graphics page."""
    def __init__(self):
        self.current_mode = 'library'  # 'library', 'design', 'execution'
        self.selected_chart_id = None
        self.saved_charts: List[ScriptLibrary] = []
        self.search_query = ""


class GraphicsDesignState:
    """Reactive state for the Graphics Design Wizard."""
    def __init__(self):
        self.phase = 'upload'  # upload, config, preview, results

        # Data source
        self.data_source: Optional[DataSourceSelection] = None
        self.data_source_selector_state = DataSourceSelectorState()
        self.df: Optional[pd.DataFrame] = None
        self.df_preview: Optional[pd.DataFrame] = None
        self.filename: Optional[str] = None
        self.df_metadata: Optional[Dict] = None

        # Mode selection: 'assisted' (deterministic) or 'ai' (generative)
        self.visualization_mode = 'assisted'

        # Assisted mode config
        self.chart_type: Optional[str] = None
        self.chart_config: Dict[str, Any] = {}

        # AI mode config
        self.user_prompt = ""
        self.ai_suggestions = []

        # Results
        self.generated_script: Optional[GraphicsScript] = None
        self.result_img_src = None
        self.result_img_bytes = None

        # UI Control
        self.is_generating = False
        self.is_sealing = False
        self.stepper = None

    def reset(self):
        self.__init__()

    def get_column_names(self) -> List[str]:
        """Get column names from loaded DataFrame."""
        if self.df is not None:
            return list(self.df.columns)
        return []

    def get_numeric_columns(self) -> List[str]:
        """Get numeric column names."""
        if self.df is not None:
            return list(self.df.select_dtypes(include=['number']).columns)
        return []

    def get_categorical_columns(self) -> List[str]:
        """Get categorical column names."""
        if self.df is not None:
            return list(self.df.select_dtypes(include=['object', 'category']).columns)
        return []


class GraphicsExecutionState:
    """Execution mode state."""
    def __init__(self):
        self.script_entry: Optional[ScriptLibrary] = None
        self.df: Optional[pd.DataFrame] = None
        self.filename: Optional[str] = None
        self.is_running = False
        self.result_img_src = None


def _update_global_data_context(df: pd.DataFrame) -> None:
    """
    Actualiza el contexto de datos global para que el Copiloto conozca las columnas.
    Debe llamarse cada vez que se carga un nuevo DataFrame.
    """
    if df is None or df.empty:
        state.current_data_context = None
        return

    # Obtener valores de ejemplo (2-3 valores únicos por columna, anonimizados)
    sample_values = {}
    for col in df.columns:
        try:
            unique_vals = df[col].dropna().unique()[:3]
            sample_values[col] = [str(v)[:50] for v in unique_vals]  # Limitar longitud
        except Exception:
            sample_values[col] = []

    state.current_data_context = {
        'columns': list(df.columns),
        'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
        'row_count': len(df),
        'sample_values': sample_values
    }


# --- PAGE CONTENT ---

async def graphics_page_content(initial_mode: Optional[str] = None, atom_id: Optional[int] = None):
    """
    Refactored Graphics Page Controller.
    Three-mode architecture: Library, Design, Execution.
    Visual Identity: Blue (primary).
    """
    t = state.i18n.t

    # Persistent page state
    page_state = GraphicsState()
    design_state = GraphicsDesignState()
    exec_state = GraphicsExecutionState()
    factory = GraphicsFactory()
    deterministic_service = DeterministicGraphicsService()
    clarification_dialog = ClarificationDialog()

    # --- INITIAL LAYOUT SETUP ---
    flow_config_id = None
    if state.flow_context and state.flow_context.get('mode') == 'contextual':
        page_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.GRAPHICS, from_flow=True)
        # Obtener config_id del paso si existe
        step = state.flow_context.get('step')
        if step and hasattr(step, 'config') and step.config:
            flow_config_id = step.config.get('config_id')
    elif initial_mode == 'design':
        page_state.current_mode = 'design'
        layout_manager.enter_design_mode(StepType.GRAPHICS, from_flow=False)
        design_state.user_prompt = naming_service.generate_provisional_name(StepType.GRAPHICS)
        update_drawer_stepper()
    elif initial_mode == 'execution':
        page_state.current_mode = 'execution'
        if atom_id:
            page_state.selected_chart_id = atom_id
    else:
        page_state.current_mode = 'library'
        layout_manager.exit_focus_mode()

    # --- COPILOT ACTIVE INTEGRATION ---
    async def apply_graphics_config(config: Dict):
        """Aplica una propuesta de gráfico del Copiloto."""
        if 'type' in config:
            design_state.chart_type = config.pop('type')  # Extraer type para el state
        
        # Merge de la configuración
        design_state.chart_config.update(config)
        
        # Cambiar a modo asistido para ver los cambios
        if design_state.visualization_mode != 'assisted':
            design_state.visualization_mode = 'assisted'
            
        # Forzar transición a página de configuración para ver los campos aplicados
        design_state.phase = 'config'
        update_drawer_stepper()
            
        ui.notify('Configuración de gráfico aplicada desde el Copiloto', type='positive')
        render_page.refresh()

    state.on_apply_graphics_proposal = apply_graphics_config

    # --- HELPERS ---

    def update_drawer_stepper():
        """Sync drawer stepper with current page phase."""
        phase_map = {
            'upload': 0,
            'config': 1,
            'preview': 2,
            'results': 2
        }
        idx = phase_map.get(design_state.phase, 0)
        layout_manager.update_step_index(idx)

    async def load_saved_charts():
        """Load graphics scripts from database."""
        async with state.db_session() as session:
            from sqlalchemy import select
            stmt = select(ScriptLibrary).where(ScriptLibrary.source_module == 'graphics')
            result = await session.execute(stmt)
            page_state.saved_charts = list(result.scalars().all())
            render_page.refresh()

    def go_to_library():
        from client_app.app.core.state import app_state
        # Si viene desde un flujo, volver al flujo
        flow_id = None
        if app_state.flow_context and app_state.flow_context.get('mode') == 'contextual':
            flow_id = app_state.flow_context.get('flow_id')
        elif app_state.editing_flow and app_state.flow_id:
            flow_id = app_state.flow_id

        if flow_id:
            layout_manager.exit_design_mode_to_flow()
            app_state.clear_flow_context()
            app_state.clear_atom_editing_context()
            ui.navigate.to(f'/flows/{flow_id}')
            return

        page_state.current_mode = 'library'
        layout_manager.exit_focus_mode()
        render_page.refresh()

    def go_to_previous_phase():
        """Navigate to previous wizard phase."""
        phase_order = ['upload', 'config', 'preview']
        current = design_state.phase
        if current == 'results':
            current = 'preview'

        try:
            idx = phase_order.index(current)
            if idx == 0:
                go_to_library()
            else:
                design_state.phase = phase_order[idx - 1]
                update_drawer_stepper()
                render_page.refresh()
        except ValueError:
            go_to_library()

    def start_new_design():
        page_state.current_mode = 'design'
        design_state.reset()
        layout_manager.enter_design_mode(StepType.GRAPHICS)
        update_drawer_stepper()
        render_page.refresh()

    async def edit_chart(script: ScriptLibrary):
        if getattr(script, 'status', 'published') == 'draft':
            page_state.current_mode = 'design'
            page_state.selected_chart_id = script.id
            design_state.reset()
            design_state.user_prompt = script.user_prompt or ""
            design_state.phase = 'config'
            layout_manager.enter_design_mode(StepType.GRAPHICS, atom_id=str(script.id))
            update_drawer_stepper()
            render_page.refresh()
        else:
            layout_manager.enter_documentation_mode(
                atom_name=script.name,
                doc_path=script.doc_path,
                status=script.status,
                description=script.description,
                resource_id=script.id,
                record_type='library'
            )
            ui.notify("Abriendo edicion de metadatos", type='info')

    async def run_chart(script: ScriptLibrary):
        page_state.current_mode = 'execution'
        exec_state.script_entry = script
        layout_manager.enter_execution_mode(str(script.id))
        render_page.refresh()

    async def delete_chart(script_id: int):
        async with state.db_session() as session:
            script = await session.get(ScriptLibrary, script_id)
            if script:
                await session.delete(script)
                await session.commit()
                ui.notify("Grafico eliminado", type='positive')
                await load_saved_charts()

    def detect_format(filename: str) -> str:
        ext = Path(filename).suffix.lower()
        format_map = {'.csv': 'csv', '.xlsx': 'excel', '.xls': 'excel', '.json': 'json', '.parquet': 'parquet'}
        return format_map.get(ext, 'csv')

    async def read_df(content: bytes, filename: str) -> pd.DataFrame:
        filename_lower = filename.lower()
        if filename_lower.endswith('.csv'):
            try:
                return pd.read_csv(io.BytesIO(content), sep=None, engine='python', on_bad_lines='warn')
            except:
                return pd.read_csv(io.BytesIO(content), encoding='latin-1')
        elif filename_lower.endswith('.parquet'):
            return pd.read_parquet(io.BytesIO(content))
        else:
            return pd.read_excel(io.BytesIO(content))

    # --- RENDERERS ---

    main_container = ui.column().classes('w-full p-0')

    @ui.refreshable
    async def render_page():
        main_container.clear()
        with main_container:
            if page_state.current_mode == 'library':
                await render_library()
            elif page_state.current_mode == 'design':
                await render_design()
            elif page_state.current_mode == 'execution':
                await render_execution()

    async def toggle_favorite(resource):
        """Toggle favorito para un gráfico."""
        chart_id = resource.get('id')
        if chart_id:
            from client_app.app.services.script_library_service import script_library_service
            await script_library_service.toggle_favorite(chart_id)
            await load_saved_charts()
            render_page.refresh()

    async def render_library():
        resources = []
        for chart in page_state.saved_charts:
            resources.append({
                'id': chart.id,
                'name': chart.name,
                'description': chart.description or 'Sin descripcion',
                'status': chart.status or 'draft',
                'source_module': 'graphics',
                'doc_path': chart.doc_path,
                'is_favorite': chart.is_favorite,
                'created_at': chart.created_at,
                '_original': chart
            })

        layout = StandardPageLayout(
            title='Visualizacion de datos',
            source_module='graphics',
            resources=resources,
            on_create=start_new_design,
            on_edit=lambda r: edit_chart(r['_original']),
            on_delete=lambda r: delete_chart(r['id']),
            on_execute=lambda r: run_chart(r['_original']),
            on_favorite_toggle=toggle_favorite,
            help_description='Genera graficos y visualizaciones a partir de tus datos de forma rapida y sin coste.',
            input_contract=['data_source', 'chart_configuration'],
            output_contract=['chart_image', 'python_code']
        )
        layout.render()

    async def render_design():
        update_drawer_stepper()

        from client_app.app.core.state import app_state
        is_flow_context = app_state.editing_flow and layout_manager.from_flow_context

        # Header
        if is_flow_context:
            with ui.row().classes('w-full bg-slate-50 border-b p-4 items-center gap-3 mb-6'):
                ui.icon('insert_chart', size='md', color='primary')
                with ui.column().classes('gap-0'):
                    ui.label(f'Configurando visualizacion...').classes('text-2xl font-bold text-primary')
                    ui.label(f'Flujo: {app_state.flow_name}').classes('text-sm text-slate-500')
                ui.space()
                ui.button('VOLVER AL FLUJO', icon='arrow_back', on_click=go_to_library).props('flat color=primary')
        else:
            with ui.row().classes('w-full items-center gap-4 mb-2'):
                ui.button(icon='arrow_back', on_click=go_to_previous_phase).props('flat round color=primary')
                with ui.column().classes('gap-0'):
                    ui.label('Configurador de Visualizaciones').classes('text-3xl font-bold text-primary')
                    ui.label('Crea graficos de forma rapida con el modo asistido o usa IA para visualizaciones complejas.').classes('text-sm text-slate-500')

        # Phase Container (Wizard body)
        with ui.column().classes('w-full max-w-5xl bg-white rounded-xl shadow-sm p-6 gap-6'):
            if design_state.phase == 'upload':
                await render_design_upload()

            elif design_state.phase == 'config':
                await render_design_config()
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Atras', on_click=lambda: (setattr(design_state, 'phase', 'upload'), update_drawer_stepper(), render_page.refresh())).props('flat')
                    ui.button('Ver Vista Previa', icon='visibility', on_click=lambda: (setattr(design_state, 'phase', 'preview'), update_drawer_stepper(), render_page.refresh())).props('unelevated color=primary')

            elif design_state.phase == 'preview' or design_state.phase == 'results':
                await render_design_preview()
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Atras', on_click=lambda: (setattr(design_state, 'phase', 'config'), update_drawer_stepper(), render_page.refresh())).props('flat')

    async def render_design_upload():
        """Phase 1: Data Upload."""
        with ui.column().classes('w-full gap-4'):
            # H2 Title - Removed by user request

            def handle_source_selection(selection: DataSourceSelection):
                design_state.data_source = selection
                if selection.source_type == 'manual' and selection.file_content:
                    client = ui.context.client
                    asyncio.create_task(process_uploaded_file(selection, client))
                elif selection.source_type == 'catalog':
                    ui.notify(state.i18n.t('etl.source_atom', name=selection.atom_name), type='info')
                elif selection.source_type == 'flow_step':
                    ui.notify(f'Usando datos del paso: {selection.step_name}', type='info')
                render_page.refresh()

            async def process_uploaded_file(selection: DataSourceSelection, client):
                with client:
                    try:
                        import re
                        filename = selection.file_name or 'upload.csv'
                        filename = re.sub(r'[^a-zA-Z0-9\._-]', '_', filename)

                        design_state.filename = filename
                        design_state.df = await read_df(selection.file_content, filename)
                        design_state.df_preview = design_state.df.head(10)
                        design_state.df_metadata = {
                            'columns': list(design_state.df.columns),
                            'rows': len(design_state.df),
                            'dtypes': {col: str(dtype) for col, dtype in design_state.df.dtypes.items()}
                        }
                        _update_global_data_context(design_state.df)
                        render_page.refresh()
                        ui.notify(f"Archivo cargado: {len(design_state.df)} filas", type='positive')
                    except Exception as ex:
                        ui.notify(f"Error carga: {ex}", type='negative')

            render_data_source_selector(
                consumer_type=StepType.GRAPHICS,
                on_source_selected=handle_source_selection,
                flow_context=state.flow_context,
                initial_selection=design_state.data_source,
                upload_formats_override=['csv', 'xlsx', 'parquet', 'json'],
                selector_state_override=design_state.data_source_selector_state
            )

            # Continue button
            with ui.row().classes('w-full justify-end mt-2'):
                can_proceed = (
                    design_state.df is not None or
                    (design_state.data_source and design_state.data_source.source_type in ['catalog', 'flow_step'])
                )
                
                def proceed_to_config():
                    if design_state.df is None and design_state.data_source_selector_state and hasattr(design_state.data_source_selector_state, 'preview_data'):
                        preview_data = design_state.data_source_selector_state.preview_data
                        if preview_data:
                            design_state.df = preview_data.to_dataframe()
                            if design_state.df is not None and not design_state.df.empty:
                                design_state.df_metadata = {
                                    'columns': list(design_state.df.columns),
                                    'rows': len(design_state.df),
                                    'dtypes': {col: str(dtype) for col, dtype in design_state.df.dtypes.items()}
                                }
                                _update_global_data_context(design_state.df)
                    setattr(design_state, 'phase', 'config')
                    update_drawer_stepper()
                    render_page.refresh()
                
                ui.button('Continuar', on_click=proceed_to_config).props('unelevated color=primary').set_enabled(can_proceed)

            # Data preview
            if design_state.df_preview is not None:
                with ui.card().classes('w-full p-2 mt-2'):
                    ui.label('Vista Previa de Datos').classes('text-xs font-bold text-slate-500 mb-2')
                    ui.table.from_pandas(design_state.df_preview.head(5)).classes('w-full').props('dense flat')

    async def render_design_config():
        """Phase 2: Chart Configuration (Assisted or AI mode)."""
        with ui.column().classes('w-full gap-4'):
            # H2 Title
            ui.label('Tipo de Visualizacion').classes('text-xl font-bold text-primary')

            # Mode selector
            with ui.row().classes('w-full items-center gap-6 p-4 border rounded-lg shadow-sm mb-2 bg-slate-50'):
                with ui.row().classes('items-center gap-4'):
                    ui.radio(
                        {'assisted': 'Asistida (Recomendado)', 'ai': 'Personalizada (IA)'},
                        value=design_state.visualization_mode
                    ).bind_value(design_state, 'visualization_mode').props('inline')

                    with ui.row().classes('items-center gap-2'):
                        ui.icon('help_outline', size='20px', color='slate-400').tooltip('Asistida: Graficos rapidos, sin coste y 100% predecibles.')
                        ui.icon('auto_awesome', size='20px', color='indigo-300').tooltip('IA: Para visualizaciones complejas que requieren logica personalizada.')

            # Conditional rendering based on mode
            if design_state.visualization_mode == 'assisted':
                await render_assisted_config()
            else:
                await render_ai_config()

    async def render_assisted_config():
        """Render assisted mode configuration (deterministic charts)."""

        # Chart type selector - compact grid
        with ui.card().classes('w-full p-4 mb-4'):
            ui.label('Selecciona el tipo de grafico').classes('text-sm font-bold text-slate-700 mb-3')

            with ui.grid(columns=4).classes('w-full gap-2'):
                for chart_type, meta in CHART_TYPES.items():
                    def select_chart(t=chart_type):
                        design_state.chart_type = t
                        design_state.chart_config = {'chart_type': t}
                        render_page.refresh()

                    is_selected = design_state.chart_type == chart_type
                    bg_color = 'bg-blue-100 border-blue-500' if is_selected else 'bg-white hover:bg-slate-100'

                    with ui.card().classes(f'cursor-pointer p-2 flex flex-row items-center gap-2 border transition-all {bg_color}')\
                        .on('click', select_chart):
                        ui.icon(meta['icon'], color='primary' if is_selected else 'slate').classes('text-xl')
                        ui.label(meta['label']).classes('text-xs font-medium')

        # Configuration form based on selected chart type
        if design_state.chart_type:
            await render_chart_config_form()

    async def render_chart_config_form():
        """Render configuration form for the selected chart type."""
        chart_type = design_state.chart_type
        meta = CHART_TYPES.get(chart_type, {})
        config = design_state.chart_config

        columns = design_state.get_column_names()
        numeric_cols = design_state.get_numeric_columns()
        categorical_cols = design_state.get_categorical_columns()

        with ui.card().classes('w-full p-4 border rounded-xl shadow-none bg-slate-50/50'):
            ui.label(f"Configurando: {meta.get('label', chart_type)}").classes('text-sm font-bold text-primary mb-3')
            ui.label(meta.get('description', '')).classes('text-xs text-slate-500 mb-4')

            # Compact 2-column layout for form fields
            with ui.grid(columns=2).classes('w-full gap-4'):
                # Data mapping fields based on chart type
                if chart_type in ['bar', 'barh', 'bar_grouped', 'bar_stacked']:
                    ui.select(categorical_cols or columns, label='Eje X (Categorias)', with_input=True).bind_value(config, 'x_column').props('dense outlined')
                    ui.select(numeric_cols or columns, label='Eje Y (Valores)', with_input=True).bind_value(config, 'y_column').props('dense outlined')

                    if chart_type in ['bar_grouped', 'bar_stacked']:
                        ui.select(categorical_cols or columns, label='Agrupar por (Color)', with_input=True, clearable=True).bind_value(config, 'color_column').props('dense outlined')
                    else:
                        ui.select(categorical_cols or columns, label='Color (Opcional)', with_input=True, clearable=True).bind_value(config, 'color_column').props('dense outlined')

                    agg_options = {'none': 'Sin agregacion', 'sum': 'Suma', 'mean': 'Promedio', 'count': 'Contar', 'max': 'Maximo', 'min': 'Minimo'}
                    ui.select(agg_options, label='Agregacion', value='none').bind_value(config, 'aggregation').props('dense outlined')

                elif chart_type in ['line', 'line_multi']:
                    ui.select(columns, label='Eje X (Tiempo/Indice)', with_input=True).bind_value(config, 'x_column').props('dense outlined')

                    if chart_type == 'line':
                        ui.select(numeric_cols or columns, label='Eje Y (Valores)', with_input=True).bind_value(config, 'y_column').props('dense outlined')
                        ui.select(categorical_cols or columns, label='Agrupar por (Opcional)', with_input=True, clearable=True).bind_value(config, 'color_column').props('dense outlined')
                    else:
                        ui.select(numeric_cols or columns, label='Columnas Y (Multiples)', multiple=True, with_input=True).bind_value(config, 'y_columns').props('dense outlined use-chips')

                elif chart_type in ['pie', 'donut']:
                    ui.select(categorical_cols or columns, label='Etiquetas (Categorias)', with_input=True).bind_value(config, 'label_column').props('dense outlined')
                    ui.select(numeric_cols or columns, label='Valores', with_input=True).bind_value(config, 'value_column').props('dense outlined')

                    if chart_type == 'donut':
                        ui.number(label='Ratio interior', value=0.3, min=0.1, max=0.8, step=0.1).bind_value(config, 'donut_ratio').props('dense outlined')

                elif chart_type in ['scatter', 'bubble']:
                    ui.select(numeric_cols or columns, label='Eje X', with_input=True).bind_value(config, 'x_column').props('dense outlined')
                    ui.select(numeric_cols or columns, label='Eje Y', with_input=True).bind_value(config, 'y_column').props('dense outlined')
                    ui.select(categorical_cols or columns, label='Color (Opcional)', with_input=True, clearable=True).bind_value(config, 'color_column').props('dense outlined')

                    if chart_type == 'bubble':
                        ui.select(numeric_cols or columns, label='Tamano (Valores)', with_input=True).bind_value(config, 'size_column').props('dense outlined')

                elif chart_type == 'histogram':
                    ui.select(numeric_cols or columns, label='Columna', with_input=True).bind_value(config, 'x_column').props('dense outlined')
                    ui.number(label='Numero de bins', value=20, min=5, max=100).bind_value(config, 'bins').props('dense outlined')
                    ui.select(categorical_cols or columns, label='Agrupar por (Opcional)', with_input=True, clearable=True).bind_value(config, 'color_column').props('dense outlined')

                elif chart_type in ['boxplot', 'violin']:
                    ui.select(numeric_cols or columns, label='Valores (Y)', with_input=True).bind_value(config, 'y_column').props('dense outlined')
                    ui.select(categorical_cols or columns, label='Agrupar por (X)', with_input=True, clearable=True).bind_value(config, 'x_column').props('dense outlined')
                    ui.select(categorical_cols or columns, label='Color (Opcional)', with_input=True, clearable=True).bind_value(config, 'color_column').props('dense outlined')

                elif chart_type == 'heatmap':
                    ui.label('El heatmap mostrara la correlacion entre todas las columnas numericas.').classes('text-xs text-slate-500 col-span-2')

            # Styling options - collapsible
            with ui.expansion('Opciones de estilo', icon='palette').classes('w-full mt-4'):
                with ui.grid(columns=2).classes('w-full gap-4 p-2'):
                    ui.input(label='Titulo del grafico').bind_value(config, 'title').props('dense outlined')
                    ui.select(COLOR_PALETTES, label='Paleta de colores', value='viridis').bind_value(config, 'palette').props('dense outlined')
                    ui.select(CHART_STYLES, label='Estilo', value='whitegrid').bind_value(config, 'style').props('dense outlined')

                    with ui.row().classes('items-center gap-4'):
                        ui.checkbox('Mostrar leyenda').bind_value(config, 'show_legend')
                        ui.checkbox('Mostrar valores').bind_value(config, 'show_values')

    async def render_ai_config():
        """Render AI mode configuration."""
        with ui.card().classes('w-full p-4'):
            ui.label('Describe tu visualizacion').classes('text-sm font-bold text-slate-700 mb-2')

            ui.textarea(
                label='Instrucciones para la IA',
                placeholder='Ej: "Grafico de barras mostrando ventas por region, con colores por trimestre y una linea de tendencia"'
            ).bind_value(design_state, 'user_prompt').classes('w-full').props('outlined rows=5')

            ui.separator().classes('my-4')

            # Quick suggestions
            if design_state.df_metadata:
                ui.label('Sugerencias rapidas:').classes('text-xs text-slate-500 mb-2')

                cols = design_state.df_metadata.get('columns', [])[:5]
                suggestions = [
                    f"Grafico de barras de {cols[1] if len(cols) > 1 else 'valores'} por {cols[0] if cols else 'categoria'}",
                    f"Linea de tendencia temporal",
                    f"Distribucion de {cols[0] if cols else 'variable'}",
                    f"Correlacion entre variables numericas"
                ]

                with ui.row().classes('gap-2 flex-wrap'):
                    for sugg in suggestions:
                        def apply_sugg(s=sugg):
                            design_state.user_prompt = s
                            render_page.refresh()
                        ui.button(sugg, on_click=apply_sugg).props('outline sm color=primary').classes('rounded-full')

    async def render_design_preview():
        """Phase 3: Preview and Generate."""
        with ui.column().classes('w-full gap-4'):
            # Fetch df if not exists but preview data exists
            if design_state.df is None and design_state.data_source_selector_state and hasattr(design_state.data_source_selector_state, 'preview_data'):
                preview_data = design_state.data_source_selector_state.preview_data
                if preview_data:
                    design_state.df = preview_data.to_dataframe()

            if design_state.df is None:
                ui.label('No hay datos disponibles para previsualizar. Por favor, selecciona un origen de datos en el Paso 1.').classes('text-red-500 italic p-4 bg-red-50 rounded')
                return

            # H2 Title
            ui.label('Vista Previa').classes('text-xl font-bold text-primary')

            if design_state.visualization_mode == 'assisted':
                await render_assisted_preview()
            else:
                await render_ai_preview()

    async def render_assisted_preview():
        """Preview for assisted mode."""
        if not design_state.chart_type:
            ui.label('Selecciona un tipo de grafico primero.').classes('text-red-500 italic')
            return

        # Build configuration
        config_dict = design_state.chart_config.copy()
        config_dict['chart_type'] = design_state.chart_type

        # Set defaults
        if 'palette' not in config_dict:
            config_dict['palette'] = 'viridis'
        if 'style' not in config_dict:
            config_dict['style'] = 'whitegrid'
        if 'show_legend' not in config_dict:
            config_dict['show_legend'] = True
        if 'show_values' not in config_dict:
            config_dict['show_values'] = False
        if 'size' not in config_dict:
            config_dict['size'] = (10, 6)

        try:
            chart_config = ChartConfiguration(**config_dict)

            # Generate preview
            if design_state.result_img_src is None or design_state.is_generating:
                with ui.column().classes('w-full items-center p-8'):
                    ui.spinner('dots', size='lg', color='primary')
                    ui.label('Generando vista previa...').classes('text-slate-500')

                # Generate chart
                try:
                    img_bytes = await deterministic_service.generate_chart(design_state.df, chart_config)
                    design_state.result_img_bytes = img_bytes
                    b64 = base64.b64encode(img_bytes).decode('utf-8')
                    design_state.result_img_src = f"data:image/png;base64,{b64}"
                    render_page.refresh()
                except Exception as e:
                    ui.label(f"Error generando grafico: {str(e)}").classes('text-red-500')
                    return

            # Show result
            if design_state.result_img_src:
                ui.image(design_state.result_img_src).classes('w-full rounded-xl border shadow-lg')

                # Action buttons
                with ui.row().classes('w-full justify-center gap-4 mt-6'):
                    # Green button - Test/Regenerate
                    async def regenerate():
                        design_state.result_img_src = None
                        render_page.refresh()

                    ui.button('REGENERAR', icon='refresh', on_click=regenerate).props('unelevated color=green-600')

                    # Blue button - Save as atom
                    ui.button(state.i18n.t('atoms.btn_save_atom', 'Guardar como Acción'), icon='save', on_click=lambda: save_assisted_atom(chart_config)).props('unelevated color=primary')

                # Show generated script
                with ui.expansion('Ver codigo Python', icon='code').classes('w-full mt-4 bg-slate-100'):
                    script = deterministic_service.generate_script(chart_config)
                    ui.code(script, language='python').classes('text-xs')

        except Exception as e:
            ui.label(f"Error en configuracion: {str(e)}").classes('text-red-500')

    async def render_ai_preview():
        """Preview for AI mode."""
        if not design_state.user_prompt:
            ui.label('Describe la visualizacion que deseas.').classes('text-red-500 italic')
            return

        if design_state.is_generating:
            with ui.column().classes('w-full items-center p-12'):
                ui.spinner('comment', size='lg', color='primary')
                ui.label('La IA esta generando tu visualizacion...').classes('mt-4 text-primary font-bold animate-pulse')

        elif design_state.result_img_src:
            ui.image(design_state.result_img_src).classes('w-full rounded-xl border-4 border-white shadow-xl')

            with ui.expansion('Ver codigo generado', icon='code').classes('w-full bg-slate-100 rounded-lg mt-4'):
                ui.code(design_state.generated_script.code if design_state.generated_script else '', language='python').classes('text-xs')

            with ui.row().classes('w-full justify-center gap-4 mt-6'):
                ui.button('REGENERAR', icon='refresh', on_click=handle_ai_generation).props('unelevated color=green-600')
                ui.button(state.i18n.t('atoms.btn_save_atom', 'Guardar como Acción'), icon='save', on_click=handle_ai_seal).props('unelevated color=primary')

        else:
            # Show generate button
            with ui.row().classes('w-full justify-center'):
                ui.button('GENERAR CON IA', icon='auto_awesome', on_click=handle_ai_generation).props('unelevated color=indigo-600 size=lg')

    async def handle_ai_generation():
        """Handle AI-based chart generation."""
        if not design_state.user_prompt:
            ui.notify("Define un objetivo", type='warning')
            return

        design_state.is_generating = True
        design_state.result_img_src = None
        render_page.refresh()

        try:
            # Analyze metadata
            if design_state.df_metadata is None and design_state.df is not None:
                design_state.df_metadata = factory.analyze_dataframe(design_state.df)

            # Clarification check
            clarification_result = await clarification_service.analyze_for_clarification(
                module_type="custom_script",
                user_input={"prompt": design_state.user_prompt, "metadata": design_state.df_metadata},
                context={"examples": []}
            )

            final_prompt = design_state.user_prompt
            if clarification_result.needs_clarification:
                responses = await clarification_dialog.show(clarification_result)
                if responses:
                    added_info = "\n\nCLARIFICACIONES:\n"
                    for resp in responses:
                        added_info += f"- {resp.question_id}: {resp.answer}\n"
                    final_prompt += added_info

            # Generate script
            design_state.generated_script = await factory.generate_script(design_state.df_metadata, final_prompt)

            # Execute script
            img_bytes = await factory.execute_script(design_state.generated_script, design_state.df)
            design_state.result_img_bytes = img_bytes
            b64 = base64.b64encode(img_bytes).decode('utf-8')
            design_state.result_img_src = f"data:image/png;base64,{b64}"

        except Exception as ex:
            ui.notify(f"Error en generacion: {ex}", type='negative')

        finally:
            design_state.is_generating = False
            render_page.refresh()

    async def save_assisted_atom(chart_config: ChartConfiguration):
        """Save assisted mode chart as atom."""
        design_state.is_sealing = True

        try:
            async with state.db_session() as session:
                # Generate script
                code = deterministic_service.generate_script(chart_config)
                code_hash = hashlib.sha256(code.encode()).hexdigest()

                # Setup path
                storage_root = Path("data/storage/scripts/src")
                storage_root.mkdir(parents=True, exist_ok=True)
                relative_path = f"graphics_assisted_{uuid4().hex[:8]}.py"
                full_path = storage_root / relative_path

                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(code)

                # Create entry
                chart_name = chart_config.title or f"Grafico {CHART_TYPES.get(chart_config.chart_type, {}).get('label', chart_config.chart_type)}"

                entry = ScriptLibrary(
                    source_module='graphics',
                    name=chart_name[:50],
                    description=f"Grafico {chart_config.chart_type} generado con modo asistido",
                    script_path=str(full_path),
                    code_hash=code_hash,
                    user_prompt=f"[Assisted] {chart_config.chart_type}",
                    status='draft'
                )
                session.add(entry)
                await session.flush()

                # Seal with Finishing Service
                finisher = AssetFinishingService(session)
                await finisher.seal_resource(entry.id)
                await session.commit()
                script_id = entry.id

            # Fase 4: Auto-captura de Sample Data
            try:
                if hasattr(design_state, 'df') and design_state.df is not None:
                    from client_app.app.services.script_library_service import script_library_service
                    await script_library_service.update_script_sample_data(
                        script_id=script_id,
                        data=design_state.df,
                        source="auto_graphics"
                    )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Error guardando sample_data en Graphics (assisted): {e}")

            # Actualizar el step en el flujo actual (contextual mode)
            from client_app.app.core.state import app_state
            if app_state.flow_context and app_state.flow_context.get('mode') == 'contextual':
                step = app_state.flow_context.get('step')
                if step:
                    step.config['config_id'] = script_id
                    step.config['script_id'] = script_id
                    if app_state.editing_flow and hasattr(app_state.editing_flow, 'steps'):
                        app_state.refresh_flow_context_steps(app_state.editing_flow.steps)
                    if hasattr(app_state, 'on_step_change') and callable(app_state.on_step_change):
                        app_state.on_step_change()

            ui.notify("Grafico guardado en biblioteca", type='positive')
            go_to_library()
            await load_saved_charts()

        except Exception as ex:
            ui.notify(f"Error al guardar: {ex}", type='negative')

        finally:
            design_state.is_sealing = False

    async def handle_ai_seal():
        """Save AI-generated chart as action."""
        if not design_state.generated_script:
            return

        design_state.is_sealing = True

        try:
            async with state.db_session() as session:
                code = design_state.generated_script.code
                code_hash = hashlib.sha256(code.encode()).hexdigest()

                storage_root = Path("data/storage/scripts/src")
                storage_root.mkdir(parents=True, exist_ok=True)
                relative_path = f"graphics_ai_{uuid4().hex[:8]}.py"
                full_path = storage_root / relative_path

                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(code)

                entry = ScriptLibrary(
                    source_module='graphics',
                    name=design_state.user_prompt[:50] or "Nuevo Grafico",
                    description=f"Grafico generado con IA: {design_state.user_prompt}",
                    script_path=str(full_path),
                    code_hash=code_hash,
                    user_prompt=design_state.user_prompt,
                    status='draft'
                )
                session.add(entry)
                await session.flush()

                finisher = AssetFinishingService(session)
                await finisher.seal_resource(entry.id)
                await session.commit()
                script_id = entry.id

            # Fase 4: Auto-captura de Sample Data
            try:
                if hasattr(design_state, 'df') and design_state.df is not None:
                    from client_app.app.services.script_library_service import script_library_service
                    await script_library_service.update_script_sample_data(
                        script_id=script_id,
                        data=design_state.df,
                        source="auto_graphics_ai"
                    )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Error guardando sample_data en Graphics (ai): {e}")

            # Actualizar el step en el flujo actual (contextual mode)
            from client_app.app.core.state import app_state
            if app_state.flow_context and app_state.flow_context.get('mode') == 'contextual':
                step = app_state.flow_context.get('step')
                if step:
                    step.config['config_id'] = script_id
                    step.config['script_id'] = script_id
                    if app_state.editing_flow and hasattr(app_state.editing_flow, 'steps'):
                        app_state.refresh_flow_context_steps(app_state.editing_flow.steps)
                    if hasattr(app_state, 'on_step_change') and callable(app_state.on_step_change):
                        app_state.on_step_change()

            ui.notify("Grafico sellado y guardado en biblioteca", type='positive')
            go_to_library()
            await load_saved_charts()

        except Exception as ex:
            ui.notify(f"Error al sellar: {ex}", type='negative')

        finally:
            design_state.is_sealing = False

    async def render_execution():
        """Execution mode for running saved charts."""
        script = exec_state.script_entry
        if not script:
            return

        with ui.row().classes('w-full items-center gap-4 mb-6'):
            ui.button(icon='arrow_back', on_click=go_to_library).props('flat round')
            ui.label(f'Ejecutar: {script.name}').classes('text-2xl font-bold text-primary')

        with ui.card().classes('w-full max-w-4xl mx-auto p-8 shadow-md border-t-8 border-primary'):
            ui.label('Paso 1: Proporcionar Datos').classes('text-lg font-bold mb-4')

            async def handle_exec_upload(e):
                try:
                    import re
                    safe_name = re.sub(r'[^a-zA-Z0-9\._-]', '_', e.name)
                    exec_state.filename = safe_name
                    content = e.content.read()
                    exec_state.df = await read_df(content, safe_name)
                    ui.notify("Datos cargados", type='positive')
                    render_page.refresh()
                except Exception as ex:
                    ui.notify(f"Error: {ex}", type='negative')

            ui.upload(on_upload=handle_exec_upload, label='Seleccionar archivo de datos', auto_upload=True).classes('w-full')

            if exec_state.df is not None:
                ui.label('Paso 2: Generar Grafico').classes('text-lg font-bold mt-8 mb-4')

                async def run_execution():
                    exec_state.is_running = True
                    render_page.refresh()

                    try:
                        script_path = Path(script.script_path)
                        if not script_path.exists():
                            raise FileNotFoundError(f"Script no encontrado en {script_path}")

                        code = script_path.read_text(encoding='utf-8')
                        script_obj = GraphicsScript(code=code, libraries=[])
                        img_bytes = await factory.execute_script(script_obj, exec_state.df)

                        b64 = base64.b64encode(img_bytes).decode('utf-8')
                        exec_state.result_img_src = f"data:image/png;base64,{b64}"
                        ui.notify("Grafico generado", type='positive')

                    except Exception as ex:
                        ui.notify(f"Error: {ex}", type='negative')

                    finally:
                        exec_state.is_running = False
                        render_page.refresh()

                ui.button('Generar Grafico', icon='play_arrow', on_click=run_execution).props('unelevated color=green-600 size=lg').classes('w-full py-4')

            if exec_state.is_running:
                with ui.column().classes('w-full items-center mt-6'):
                    ui.spinner('gears', size='lg', color='primary')
                    ui.label('Procesando...').classes('mt-2')

            if exec_state.result_img_src:
                ui.separator().classes('my-8')
                ui.label('Resultado:').classes('font-bold mb-2')
                ui.image(exec_state.result_img_src).classes('w-full rounded-lg shadow-md')

    # --- INITIAL RENDER ---
    await load_saved_charts()

    # Si hay config_id del flujo, cargar el gráfico
    if flow_config_id:
        async with state.db_session() as session:
            script = await session.get(ScriptLibrary, int(flow_config_id))
            if script:
                await edit_chart(script)

    # Mode refinement (if ID was provided for execution)
    if page_state.current_mode == 'execution' and page_state.selected_chart_id:
        async with state.db_session() as session:
            script = await session.get(ScriptLibrary, int(page_state.selected_chart_id))
            if script:
                exec_state.script_entry = script
                layout_manager.enter_execution_mode(str(script.id))

    await render_page()


# Keep original function name for backwards compatibility
graphics_page = graphics_page_content

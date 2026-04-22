from nicegui import ui
import asyncio
from typing import Optional, List, Dict, Any, Union, Literal
import pandas as pd
from pathlib import Path
import io
import os
from client_app.app.services.anonymization_service import AnonymizationService, AnonymizationRule
from client_app.app.core.state import state
from client_app.app.services.layout_manager import layout_manager
from client_app.app.ui.components.page_header import page_header
from client_app.app.ui.components.data_source_selector import render_data_source_selector, DataSourceSelection, DataSourceSelectorState
from automatia_shared.enums import StepType
from client_app.app.services.naming_service import naming_service
from client_app.app.services.atom_service import atom_service
import json
import os
from client_app.app.ui.components.unified_resource_card import get_resource_styles

# Output directory for utility mode
ANONYMIZER_OUTPUT_DIR = Path("data/utilities/output/anonymizer")


class AnonymizerState:
    def __init__(self):
        # Hybrid Mode: No 'library'/'design' switch. Just direct interaction.
        self.df: Optional[pd.DataFrame] = None
        self.preview_df: Optional[pd.DataFrame] = None
        self.filename: Optional[str] = None

        # Analysis
        self.analysis_results: List[Dict[str, Any]] = []
        self.columns_config: Dict[str, AnonymizationRule] = {}

        # Execution
        self.result_buffer = None

        # Source
        self.data_source: Optional[DataSourceSelection] = None
        self.data_source_selector_state = DataSourceSelectorState()

        # Atom mode specific
        self.atom_name: str = ""

    def reset(self):
        self.df = None
        self.preview_df = None
        self.filename = None
        self.analysis_results = []
        self.columns_config = {}
        self.result_buffer = None
        self.data_source = None


class AnonymizerPage:
    """
    Página del anonimizador con soporte para modo dual.

    Modes:
        - 'utility': Uso directo desde menú Utilidades. Sin nombre, sin drawer.
        - 'atom': Configuración de átomo para flujos. Con nombre y guardado.
        - 'execution': Ejecución standalone de un átomo guardado.
    """

    def __init__(self, mode: Literal['utility', 'atom', 'execution'] = 'utility', atom_id: Optional[int] = None):
        self.mode = mode
        self.atom_id = atom_id
        self.service = AnonymizationService()
        self.state = AnonymizerState()
        self.container = None

        # Ensure output directory exists for utility mode
        if mode == 'utility':
            ANONYMIZER_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        elif mode == 'atom':
            # Provisional naming for new atom
            self.state.atom_name = naming_service.generate_provisional_name(StepType.ANONYMIZATION)
            layout_manager.enter_design_mode(StepType.ANONYMIZATION)
        elif mode == 'execution' and atom_id:
            layout_manager.enter_execution_mode(atom_id)

    async def render(self):
        self.container = ui.column().classes('w-full h-full')
        await self._refresh_ui()

    async def _refresh_ui(self):
        self.container.clear()

        with self.container:
            with ui.column().classes('w-full max-w-7xl mx-auto p-6 gap-6'):
                # Branch by mode
                if self.mode == 'utility' or self.mode == 'execution':
                    await self._render_utility_mode()
                else:
                    await self._render_atom_mode()

    # ========== UTILITY MODE ==========

    async def _render_utility_mode(self):
        """UI simplificada para uso directo desde Utilidades."""
        t = state.i18n.t

        page_header(
            t('anonymizer.title', 'Anonimizador'),
            t('anonymizer.utility_subtitle', 'Enmascara datos sensibles en archivos Excel, CSV o JSON')
        )

        # Compact help section
        with ui.expansion(t('anonymizer.help_title', 'Ayuda'), icon='help_outline').classes('w-full bg-slate-50 border rounded-lg overflow-hidden'):
            with ui.column().classes('p-4 gap-2'):
                ui.label(
                    t('anonymizer.help_text',
                      'Sube un archivo para analizar automáticamente columnas sensibles '
                      'y aplicar reglas de anonimización (GDPR/LOPD).')
                ).classes('text-slate-600 text-sm')
                with ui.row().classes('gap-2 flex-wrap'):
                    ui.chip('Excel (.xlsx)', icon='description', color='green-100').props('dense text-color=green-900')
                    ui.chip('CSV (.csv)', icon='description', color='green-100').props('dense text-color=green-900')
                    ui.chip('JSON (.json)', icon='code', color='green-100').props('dense text-color=green-900')

        # Main content
        if self.state.df is None:
            await self._render_utility_upload()
        else:
            await self._render_workspace()

    async def _render_utility_upload(self):
        """Sección de carga simplificada para modo utilidad."""
        t = state.i18n.t

        with ui.card().classes('w-full max-w-7xl mx-auto p-6 text-center border-dashed border-2 border-slate-300 hover:border-slate-400 bg-slate-50 transition-colors'):
            with ui.row().classes('w-full items-center justify-center gap-4 mb-6'):
                ui.icon('cloud_upload', size='3rem').classes('text-slate-400')
                ui.label(t('anonymizer.select_file', 'Selecciona un archivo para comenzar')).classes('text-2xl font-bold text-slate-700')

            # Simple file upload for utility mode (no flow step selection)
            async def handle_upload(e):
                try:
                    # Normalization to avoid issues
                    import re
                    safe_name = re.sub(r'[^a-zA-Z0-9\._-]', '_', e.file.name)
                    
                    # Save to temp location and process
                    import tempfile
                    import os
                    ext = Path(safe_name).suffix
                    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                        content = await e.file.read()
                        if not isinstance(content, (bytes, bytearray)):
                             ui.notify(f"Error: El contenido del archivo no es válido ({type(content).__name__}).", type='negative')
                             return
                        tmp.write(content)
                        tmp_path = tmp.name

                    df = await self.service.load_dataframe(tmp_path)
                    self.state.df = df
                    self.state.preview_df = df.head(10)
                    self.state.filename = safe_name
                    await self._run_analysis()
                    await self._refresh_ui()
                    ui.notify(t('anonymizer.file_loaded', 'Archivo cargado y analizado'), type='positive')
                except Exception as ex:
                    ui.notify(f'{t("anonymizer.error_loading", "Error al cargar")}: {ex}', type='negative')
                finally:
                    if 'tmp_path' in locals() and os.path.exists(tmp_path):
                        os.unlink(tmp_path)

            ui.upload(
                label=t('anonymizer.upload_label', 'Arrastra archivos aquí o haz clic'),
                auto_upload=True,
                on_upload=handle_upload
            ).props('accept=".xlsx,.xls,.csv,.json" flat bordered').classes('w-full')

    # ========== ATOM MODE ==========

    async def _render_atom_mode(self):
        """UI completa para configuración de átomo en flujos."""
        t = state.i18n.t

        styles = get_resource_styles('anonymizer')

        styles = get_resource_styles('anonymizer')

        # Contextual Header (Flow vs Standalone)
        from client_app.app.core.state import app_state
        
        if app_state.editing_flow and layout_manager.from_flow_context:
            # Banner azul contextual (SOLO si viene de flujo)
            with ui.row().classes('w-full bg-primary text-white p-3 items-center gap-3 mb-6 rounded-b shadow-md'):
                ui.icon('assignment', size='md')
                ui.label(f'Configurando paso {app_state.flow_step_index + 1}: {app_state.editing_step.name if app_state.editing_step else "Anonimizador"}').classes('font-bold')
                ui.label(f'Flujo: {app_state.flow_name}').classes('text-xs opacity-80')
                
                ui.space()
                
                async def back_to_flow():
                    layout_manager.exit_design_mode_to_flow()
                    app_state.clear_atom_editing_context()
                    ui.navigate.to(f'/flows/{app_state.flow_id}')
                
                ui.button('VOLVER AL FLUJO', icon='arrow_back', on_click=back_to_flow).props('flat text-color=white')
        else:
            # Header estándar (SOLO en modo standalone)
            page_header(
                t('anonymizer.title', 'Anonimizador'),
                t('anonymizer.atom_subtitle', 'Configura el enmascaramiento de datos para usar en flujos')
            )

        # Help section
        with ui.expansion(t('anonymizer.help_title', 'Ayuda y Referencia'), icon='help_outline').classes('w-full bg-slate-50 border rounded-lg overflow-hidden'):
            with ui.column().classes('p-4 gap-4'):
                ui.label(
                    t('anonymizer.help_text',
                      'Sube un archivo (Excel, CSV) para analizar automáticamente columnas sensibles '
                      'y aplicar reglas de anonimización (GDPR/LOPD). Descarga el resultado procesado.')
                ).classes('text-slate-600 text-sm')

                with ui.row().classes('w-full gap-8'):
                    with ui.column().classes('flex-1 gap-2'):
                        ui.label(t('anonymizer.supported_input', 'Input soportado')).classes('text-xs font-bold text-slate-500 uppercase')
                        with ui.row().classes('gap-2 flex-wrap'):
                            ui.chip('Excel (.xlsx)', icon='description', color='green-100').props('dense text-color=green-900')
                            ui.chip('CSV (.csv)', icon='description', color='green-100').props('dense text-color=green-900')
                            ui.chip('JSON (.json)', icon='code', color='green-100').props('dense text-color=green-900')

        # Main content
        if self.state.df is None:
            await self._render_upload_section()
        else:
            await self._render_workspace()

    # ========== SHARED METHODS ==========

    async def _render_upload_section(self):
        with ui.card().classes('w-full max-w-7xl mx-auto p-6 text-center border-dashed border-2 border-slate-300 hover:border-slate-400 bg-slate-50 transition-colors'):
            with ui.row().classes('w-full items-center justify-center gap-4 mb-6'):
                ui.icon('cloud_upload', size='3rem').classes('text-slate-400')
                ui.label('Selecciona un archivo para comenzar').classes('text-2xl font-bold text-slate-700')
            
            def handle_selection(selection: DataSourceSelection):
                self.state.data_source = selection
                asyncio.create_task(self._process_selection(selection))

            render_data_source_selector(
                consumer_type=StepType.ANONYMIZATION,
                on_source_selected=handle_selection,
                flow_context=state.flow_context,
                initial_selection=None,
                compact=False,
                selector_state_override=self.state.data_source_selector_state
            )
            
            # Additional manual button if selector is too hidden
            # Actually render_ds_selector renders buttons.

    async def _process_selection(self, selection: DataSourceSelection):
        """Process the selected file immediately."""
        ui.notify(f'Cargando {selection.file_name or "datos"}...', type='info')

        try:
            df = None

            if selection.source_type == 'manual' and selection.file_content:
                # Archivo cargado manualmente - leer desde file_content (bytes)
                filename = selection.file_name or 'upload.csv'
                file_ext = filename.split('.')[-1].lower() if '.' in filename else 'csv'

                if file_ext == 'csv':
                    df = pd.read_csv(io.BytesIO(selection.file_content))
                elif file_ext in ['xlsx', 'xls']:
                    df = pd.read_excel(io.BytesIO(selection.file_content))
                elif file_ext == 'json':
                    df = pd.read_json(io.BytesIO(selection.file_content))
                elif file_ext == 'parquet':
                    df = pd.read_parquet(io.BytesIO(selection.file_content))
                else:
                    df = pd.read_csv(io.BytesIO(selection.file_content))

                self.state.filename = filename

            elif selection.source_type == 'flow_step':
                # Datos de paso anterior - obtener del preview_data si está disponible
                selector_state = self.state.data_source_selector_state
                if selector_state.preview_data:
                    df = selector_state.preview_data.to_dataframe()
                    self.state.filename = f"Paso: {selection.step_name}"
                else:
                    ui.notify('Haz clic en "Cargar datos" para obtener los datos del paso anterior', type='warning')
                    return

            elif selection.source_type == 'catalog':
                # Datos de átomo del catálogo - obtener del preview_data
                selector_state = self.state.data_source_selector_state
                if selector_state.preview_data:
                    df = selector_state.preview_data.to_dataframe()
                    self.state.filename = f"Acción: {selection.atom_name}"
                else:
                    ui.notify('Haz clic en la acción para cargar sus datos de ejemplo', type='warning')
                    return

            if df is not None and not df.empty:
                self.state.df = df
                self.state.preview_df = df.head(10)

                # Auto-analyze
                await self._run_analysis()

                await self._refresh_ui()
                ui.notify('Archivo cargado y analizado', type='positive')
            else:
                ui.notify('No se pudieron cargar datos válidos', type='warning')

        except Exception as e:
            ui.notify(f'Error al cargar archivo: {e}', type='negative')

    async def _run_analysis(self):
        """Run standard PII analysis."""
        if self.state.df is not None:
            self.state.analysis_results = await self.service.analyze_dataframe(self.state.df)
            # Pre-populate config based on suggestions
            self.state.columns_config = {}
            for col in self.state.df.columns:
                # Find suggestion for this col
                suggestion = next((r for r in self.state.analysis_results if r['column'] == col), None)
                if suggestion:
                    self.state.columns_config[col] = AnonymizationRule(
                        method=suggestion['suggested_method'],
                        params={}, # Default params
                        entity_type_raw=suggestion['entity_type_raw']
                    )
                else:
                    self.state.columns_config[col] = AnonymizationRule(method="none", params={})

    async def _render_workspace(self):
        with ui.column().classes('w-full gap-6'):
            
            # Action Bar
            with ui.row().classes('w-full justify-between items-center bg-white p-4 rounded shadow-sm border'):
                with ui.row().classes('items-center gap-4'):
                    ui.button(on_click=self._reset_workspace, icon='arrow_back').props('flat round').tooltip('Volver a subir')
                    with ui.column().classes('gap-0'):
                        ui.label(self.state.filename or 'Datos en memoria').classes('font-bold')
                        ui.label(f'{len(self.state.df)} filas detectadas').classes('text-xs text-slate-500')
                
                with ui.row().classes('items-center gap-2'):
                    # Save as Atom (Only in Atom Mode)
                    if self.mode == 'atom':
                        ui.button('Guardar como Acción', icon='save', on_click=self._save_as_atom) \
                            .classes('bg-green-600 text-white shadow-md font-bold')
                    
                    # Direct Process (Always available)
                    ui.button('Procesar y Descargar', icon='download', on_click=self._process_and_download) \
                        .classes('bg-slate-800 text-white shadow-lg font-bold')

            # Split columns into Sensitive and Non-Sensitive
            sensitive_cols = []
            non_sensitive_cols = []
            
            for col in self.state.df.columns:
                rule = self.state.columns_config.get(col)
                if rule and rule.method != 'none':
                    sensitive_cols.append(col)
                else:
                    non_sensitive_cols.append(col)

            # Full-screen grid for sensitive columns
            if sensitive_cols:
                ui.label('Campos Sensibles Detectados').classes('font-bold text-lg mb-2')
                with ui.row().classes('w-full gap-4 mb-6'):
                    for col in sensitive_cols:
                        self._render_column_config(col)
            
            # Expansion for non-sensitive columns
            if non_sensitive_cols:
                with ui.expansion('Ver más campos', icon='visibility_off').classes('w-full bg-slate-50 border rounded-lg overflow-hidden'):
                    with ui.row().classes('w-full gap-4 p-4'):
                        for col in non_sensitive_cols:
                            self._render_column_config(col)

            # Preview Section (always full width below or in its own area)
            with ui.column().classes('w-full p-4 bg-white rounded shadow-sm border mt-6'):
                ui.label('Vista Previa (5 filas)').classes('font-bold text-lg mb-4')
                self.preview_container = ui.column().classes('w-full')
                await self._render_preview_table()
                ui.button('Actualizar Vista Previa', icon='refresh', on_click=self._update_preview_ui).props('flat w-full')

    def _render_column_config(self, col_name: str):
        rule = self.state.columns_config.get(col_name)
        if not rule: return

        analysis_info = next((r for r in self.state.analysis_results if r['column'] == col_name), None)
        score = analysis_info['confidence_score'] if analysis_info else 0.0
        entity_type = rule.entity_type_raw # Use the raw type stored in the rule
        # Custom options based on type
        options = {
            'none': 'Original (Sin cambios)',
            'redact': 'Redactar (***)',
            'faker': 'Datos Falsos (Faker)',
        }
        
        if entity_type == 'PERSON':
            options['initials'] = 'Iniciales (J.P.)'
        elif entity_type == 'ID':
            options['aepd'] = 'AEPD (LOPDGDD)'
            
        # Add general options
        options.update({
            'hash': 'Hash (SHA256)',
            'perturbation': 'Perturbación Numérica',
            'suppression': 'Suprimir Columna'
        })

        with ui.card().classes('p-3 border-l-4 min-w-[300px] flex-1').style(f'border-left-color: {"red" if score > 0.5 else "gray"}'):
            with ui.column().classes('w-full gap-2'):
                with ui.row().classes('w-full justify-between items-center'):
                    with ui.column().classes('gap-0'):
                        ui.label(col_name).classes('font-bold')
                        if score > 0.5:
                            ui.label(f'{entity_type} ({int(score*100)}%)').classes('text-xs text-red-500 font-bold')
                
                ui.select(
                    options, 
                    value=rule.method,
                    on_change=lambda e: self._update_rule(col_name, e.value)
                ).props('dense outlined').classes('w-full')

    def _update_rule(self, col: str, method: str):
        self.state.columns_config[col].method = method
        # Optional: Auto-refresh preview? Maybe too heavy.

    async def _update_preview_ui(self):
        # Apply rules to head(5)
        if self.state.df is None: return
        
        sample = self.state.df.head(5).copy()
        processed = await self.service.apply_anonymization(sample, self.state.columns_config)
        
        self.state.preview_df = processed
        
        self.preview_container.clear()
        with self.preview_container:
            await self._render_preview_table()

    async def _render_preview_table(self):
        if self.state.preview_df is not None:
             ui.table(
                 columns=[{'name': col, 'label': col, 'field': col} for col in self.state.preview_df.columns],
                 rows=self.state.preview_df.to_dict('records')
             ).classes('w-full text-xs')

    def _reset_workspace(self):
        self.state.reset()
        asyncio.create_task(self._refresh_ui())

    async def _process_and_download(self):
        if self.state.df is None: return
        
        ui.notify('Procesando archivo completo...', type='info')
        
        try:
            # Process full DF
            processed_df = await self.service.apply_anonymization(self.state.df, self.state.columns_config)
            
            # Helper to download
            # For now convert to CSV string
            # In utility mode, also save to output directory
            if self.mode == 'utility':
                output_name = f"anon_{self.state.filename or 'data.csv'}"
                if not output_name.endswith('.csv'): output_name += '.csv'
                
                output_path = ANONYMIZER_OUTPUT_DIR / output_name
                processed_df.to_csv(output_path, index=False)
                
                with ui.dialog() as success_dialog, ui.card().classes('p-6'):
                    with ui.column().classes('items-center gap-4'):
                        ui.icon('check_circle', size='xl', color='green')
                        ui.label('Procesamiento completado').classes('text-xl font-bold')
                        ui.label(f'Archivo guardado en: {ANONYMIZER_OUTPUT_DIR}').classes('text-sm text-slate-500')
                        
                        with ui.row().classes('gap-2'):
                            ui.button('Abrir carpeta', icon='folder_open', 
                                      on_click=lambda: os.startfile(str(ANONYMIZER_OUTPUT_DIR))).props('outline')
                            ui.button('Cerrar', on_click=success_dialog.close).props('flat')
                success_dialog.open()

            # Trigger browser download with original extension logic
            filename = self.state.filename or "datos.xlsx"
            is_csv = filename.lower().endswith('.csv')
            
            output = io.BytesIO()
            if is_csv:
                processed_df.to_csv(output, index=False)
                mime_type = 'text/csv'
                dl_name = "anonimizado.csv"
            else:
                processed_df.to_excel(output, index=False, engine='openpyxl')
                mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                dl_name = "anonimizado.xlsx"
            
            output.seek(0)
            ui.download(output.getvalue(), dl_name)
            ui.notify('Descarga iniciada', type='positive')
            
        except Exception as e:
            ui.notify(f'Error en procesamiento: {e}', type='negative')

    async def _save_as_atom(self):
        """Saves current configuration as a reusable atom."""
        # Prepare config
        config = {
            'columns_config': {col: {'method': rule.method, 'params': rule.params} 
                              for col, rule in self.state.columns_config.items()}
        }
        
        # Provisional name
        prov_name = naming_service.provisional_name(StepType.ANONYMIZATION, config)
        
        with ui.dialog() as d, ui.card().classes('p-6 min-w-[400px]'):
            ui.label('Guardar como Acción').classes('text-xl font-bold mb-4')
            name_input = ui.input('Nombre de la Acción', value=prov_name).props('outlined autofocus').classes('w-full mb-4')
            desc_input = ui.input('Descripción', value='Enmascaramiento de datos personalizado').props('outlined').classes('w-full mb-6')
            
            async def confirm():
                try:
                    # Define a schema for Flow Editor visibility
                    schema = {
                        "type": "object",
                        "properties": {
                            "columns_config": {
                                "type": "object",
                                "title": "Reglas de Enmascaramiento",
                                "description": "Mapa de columna -> método (redact, faker, etc.)"
                            }
                        }
                    }
                    
                    await atom_service.create_atom(
                        name=name_input.value,
                        atom_type=StepType.ANONYMIZATION,
                        description=desc_input.value,
                        config_schema=json.dumps(schema),
                        default_config=json.dumps(config),
                        input_contract=json.dumps({'dataset': 'file'}),
                        output_contract=json.dumps({'dataset': 'file'}),
                        category='utility'
                    )
                    ui.notify('Acción guardada en el catálogo', type='positive')
                    d.close()
                except Exception as e:
                    ui.notify(f'Error al guardar: {e}', type='negative')
            
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancelar', on_click=d.close).props('flat')
                ui.button('Guardar Acción', on_click=confirm).props('color=primary unelevated')
        d.open()

async def anonymizer_page_content(mode: Literal['utility', 'atom', 'execution'] = 'utility', atom_id: Optional[int] = None):
    """
    Entry point for the anonymizer page.

    Args:
        mode: 'utility' for direct use, 'atom' for flow configuration, 'execution' for standalone execution
    """
    page = AnonymizerPage(mode=mode, atom_id=atom_id)
    await page.render()


@ui.page('/processors/anonymizer')
async def anonymizer_legacy_route(initial_mode: Optional[str] = None, atom_id: Optional[int] = None):
    mode = 'execution' if initial_mode == 'execution' else 'atom'
    page = AnonymizerPage(mode=mode, atom_id=atom_id)
    await page.render()


@ui.page('/atoms/anonymizer/new')
async def anonymizer_new_route():
    """Ruta para crear un nuevo átomo de anonimización desde el catálogo."""
    state.clear_flow_context()  # Ensure standalone mode (no flow context)
    layout_manager.enter_design_mode(StepType.ANONYMIZATION)
    page = AnonymizerPage(mode='atom')
    await page.render()


@ui.page('/utilities/anonymizer')
async def anonymizer_utility_route():
    """Ruta para uso directo del anonimizador."""
    layout_manager.exit_focus_mode()
    page = AnonymizerPage(mode='utility')
    await page.render()

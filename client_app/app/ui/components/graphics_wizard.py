
from nicegui import ui
import pandas as pd
import io
import asyncio
from typing import Optional, List, Dict

from client_app.app.modules.factory.graphics_factory import GraphicsFactory, GraphicsScript
from client_app.app.services.clarification_service import clarification_service, ClarificationResponse
from client_app.app.ui.components.clarification_dialog import ClarificationDialog
from client_app.app.ui.components.privacy_indicator import render_privacy_indicator

class GraphicsWizard:
    """
    Wizard UI for the Graphics Module.
    Steps:
    1. Analysis (Upload -> Stats -> Questions)
    2. Suggestion (Strategy selection -> Visualization Ideas)
    3. Generation (Clarification -> Code -> Chart)
    """

    def __init__(self):
        self.factory = GraphicsFactory() # Default config
        self.df: Optional[pd.DataFrame] = None
        self.filename: Optional[str] = None
        self.df_metadata: Optional[Dict] = None
        self.selected_question: Optional[str] = None
        self.generated_script: Optional[GraphicsScript] = None
        
        self.stepper = None
        self.clarification_dialog = ClarificationDialog()

    @ui.refreshable
    def _render_uploader(self):
        with ui.column().classes('w-full gap-4'):
            # Upload Card (Replicated from ETL Page with Indigo styling)
            with ui.card().classes('w-full min-h-[300px] p-0 border-2 border-dashed border-indigo-300 bg-indigo-50 relative overflow-hidden'):
                # Upload status overlay
                with ui.column().classes('items-center justify-center w-full h-full py-12 pointer-events-none'):
                    ui.icon('cloud_upload', size='4em').classes('text-indigo-500 mb-2 opacity-50')
                    
                    if self.filename:
                        ui.label(f"✓ {self.filename}").classes('text-xl font-bold text-indigo-700')
                        ui.label("Archivo cargado y analizado").classes('text-sm text-indigo-600')
                    else:
                        ui.label('Arrastra y suelta tu archivo aquí (CSV/Excel)').classes('text-xl font-bold opacity-70 text-indigo-900')
                        ui.label('o haz clic para seleccionar').classes('text-sm opacity-60 text-indigo-700')
                        ui.label('.csv, .xlsx').classes('text-xs opacity-50 mt-2')
                
                # Upload component
                ui.upload(on_upload=self._handle_upload, auto_upload=True, multiple=False)\
                    .props('accept=.csv,.xlsx flat color=indigo-700 label=""') \
                    .classes('absolute inset-0 z-10 bg-transparent') \
                    .style('width: 100%; height: 100%;')

    def render(self):
        with ui.column().classes('w-full items-center'):
            self.stepper = ui.stepper().props('vertical').classes('w-full max-w-4xl')

            with self.stepper:
                # STEP 1: Data & Analysis
                with ui.step('Análisis de Datos'):
                    self._render_uploader()
                    self.analysis_container = ui.column().classes('w-full mt-4')
                    with ui.stepper_navigation():
                        ui.button('Siguiente', on_click=self.stepper.next)

                # STEP 2: Strategy / Suggestions
                with ui.step('Estrategia de Visualización'):
                    ui.label('Selecciona una pregunta de negocio o escribe la tuya')
                    self.questions_container = ui.column().classes('w-full mt-2')
                    self.prompt_input = ui.input('Tu objetivo de visualización').classes('w-full')
                    
                    ui.button('Generar Sugerencias', on_click=self._generate_suggestions)
                    self.suggestions_container = ui.row().classes('w-full gap-4 mt-4')

                    with ui.stepper_navigation():
                        ui.button('Generar Gráfico', on_click=self._handle_generation_request).props('color=primary')
                        ui.button('Atrás', on_click=self.stepper.previous).props('flat')

                # STEP 3: Result
                with ui.step('Resultado'):
                    self.result_container = ui.column().classes('w-full')
                    with ui.stepper_navigation():
                        ui.button('Reiniciar', on_click=self._reset).props('outline')

    async def _handle_upload(self, e):
        try:
            # Normalization to avoid issues
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9\._-]', '_', e.file.name)
            self.filename = safe_name
            
            content = await e.file.read()
            if not isinstance(content, (bytes, bytearray)):
                 ui.notify(f"Error: El contenido del archivo no es válido ({type(content).__name__}).", type='negative')
                 return
            
            filename_lower = safe_name.lower()
            if filename_lower.endswith('.csv'):
                self.df = pd.read_csv(io.BytesIO(content))
            else: # xlsx (default fallback or explicit)
                 try:
                    self.df = pd.read_excel(io.BytesIO(content), engine='openpyxl')
                 except Exception:
                    # Fallback check if it was ZIP but not valid Excel
                     if content.startswith(b'PK'):
                         ui.notify("Error: Archivo ZIP/Office inválido (posible DOCX/PPTX renombrado)", type='negative')
                     raise
            
            ui.notify(f"Cargado: {len(self.df)} filas", type='positive')
            self._render_uploader.refresh() # Update UI to show filename
            
            # Run analysis
            self.df_metadata = self.factory.analyze_dataframe(self.df)
            
            # Show summary
            self.analysis_container.clear()
            with self.analysis_container:
                ui.label(f"Columnas: {', '.join(self.df_metadata['columns'])}")
                ui.label("Analizando preguntas de negocio...")
                ui.spinner()
            
            # Async generate business questions
            questions = await self.factory.generate_business_questions(self.df_metadata)
            
            # Render questions in Step 2 container (pre-fill)
            self.questions_container.clear()
            with self.questions_container:
                ui.label("Preguntas sugeridas:").classes('text-sm text-gray-500')
                for q in questions:
                    ui.button(q, on_click=lambda sent_q=q: self.prompt_input.set_value(sent_q)).props('outline sm')

            self.analysis_container.clear()
            with self.analysis_container:
                ui.label(f"Columnas: {', '.join(self.df_metadata['columns'])}")
                ui.label(f"Filas: {self.df_metadata['rows']}")
                ui.label("Análisis completo. Procede al siguiente paso.").classes('text-green-600')

        except Exception as ex:
            ui.notify(f"Error: {str(ex)}", type='negative')
            self.filename = None
            self._render_uploader.refresh()

    async def _generate_suggestions(self):
        prompt = self.prompt_input.value
        if not prompt:
            ui.notify("Escribe un objetivo primero", type='warning')
            return
            
        self.suggestions_container.clear()
        with self.suggestions_container:
            ui.spinner()
            
        suggestions = await self.factory.generate_visualization_suggestions(self.df_metadata, prompt)
        
        self.suggestions_container.clear()
        with self.suggestions_container:
            for sugg in suggestions:
                with ui.card().classes('w-64'):
                    ui.label(sugg.get('type', 'Chart')).classes('font-bold')
                    ui.label(sugg.get('reason', ''))
                    ui.label(sugg.get('description', '')).classes('text-sm text-gray-500')

    async def _handle_generation_request(self):
        prompt = self.prompt_input.value
        if not prompt:
            ui.notify("Define qué quieres graficar", type='warning')
            return

        # 1. Clarification Check
        ui.notify("Analizando ambigüedades...", type='info')
        try:
            clarification_result = await clarification_service.analyze_for_clarification(
                module_type="custom_script",
                user_input={"prompt": prompt, "metadata": self.df_metadata},
                context={"examples": []} # Could pass examples if available
            )
            
            clarifications = []
            if clarification_result.needs_clarification:
                # Show Dialog
                responses = await self.clarification_dialog.show(clarification_result)
                if responses: # If not skipped/cancelled
                    clarifications = responses
                    # Append clarifications to prompt or context
                    prompt = self._enrich_prompt(prompt, clarifications)
            
            # 2. Generation
            ui.notify("Generando script...", type='info')
            self.generated_script = await self.factory.generate_script(self.df_metadata, prompt)
            
            # 3. Execution
            ui.notify("Ejecutando script...", type='info')
            img_bytes = await self.factory.execute_script(self.generated_script, self.df)
            
            self._show_result(self.generated_script.code, img_bytes)
            self.stepper.next()

        except Exception as e:
            ui.notify(f"Error en generación: {e}", type='negative')

    def _enrich_prompt(self, prompt: str, clarifications: List[ClarificationResponse]) -> str:
        added_info = "\n\nCLARIFICACIONES:\n"
        for resp in clarifications:
            added_info += f"- {resp.question_id}: {resp.answer}\n"
        return prompt + added_info

    def _show_result(self, code: str, img_bytes: bytes):
        import base64
        self.result_container.clear()
        
        # Convert bytes to base64 for display
        b64_img = base64.b64encode(img_bytes).decode('utf-8')
        img_src = f"data:image/png;base64,{b64_img}"
        
        with self.result_container:
            ui.label("Resultado Visual:").classes('text-xl font-bold mb-2')
            ui.image(img_src).classes('w-full max-w-4xl border rounded shadow-lg')
            
            ui.label("Código Generado:").classes('font-bold mt-4')
            ui.code(code, language='python').classes('w-full')

    def _reset(self):
        self.df = None
        self.df_metadata = None
        self.prompt_input.value = ""
        self.stepper.set_value('Análisis de Datos')
        self.analysis_container.clear()
        self.questions_container.clear()
        self.suggestions_container.clear()

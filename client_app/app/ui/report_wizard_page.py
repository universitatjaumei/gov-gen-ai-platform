from nicegui import ui
import asyncio
from typing import List, Dict, Any
from client_app.app.services.report_analyzer_service import ReportAnalyzerService
from client_app.app.modules.factory.report_factory import ReportFactory

class ReportWizardPage:
    """
    Wizard UI for generating reports with AI analysis.
    Steps:
    1. Data & Template Selection
    2. Analysis (Auto/Interactive)
    3. Customization (Editor)
    4. Generation
    """
    
    def __init__(self):
        self.analyzer_service = ReportAnalyzerService()
        self.report_factory = ReportFactory()
        
        self.current_step = 0
        self.steps_ui = None
        
        # State
        self.selected_template = "generic_report.html"
        self.context_data: Dict[str, Any] = {} # This would be loaded from data source
        self.editor_content = ""
        self.user_instructions = ""
        self.selected_context_keys: List[str] = []
        self.available_keys: List[str] = []
        
        self.setup_ui()

    def setup_ui(self):
        with ui.column().classes('w-full p-4'):
            ui.label('Generador de Informes').classes('text-2xl font-bold mb-4')
            
            with ui.stepper().props('vertical').classes('w-full') as stepper:
                self.steps_ui = stepper
                
                with ui.step('Selección de Datos'):
                    ui.label('Seleccione la fuente de datos y plantilla')
                    # Mock selectors for now
                    ui.select(['generic_report.html', 'sales_report.html'], value=self.selected_template, label='Plantilla').bind_value(self, 'selected_template')
                    # In a real app, file picker or DB source selector
                    ui.button('Siguiente', on_click=lambda: stepper.next())
                
                with ui.step('Análisis IA'):
                    ui.label('Configuración del Análisis')
                    with ui.row():
                        with ui.column():
                            ui.label('Contexto Disponible:')
                            # Dynamic checkboxes container
                            self.context_container = ui.column()
                            
                        with ui.column().classes('w-full'):
                            ui.textarea(label='Instrucciones para la IA', placeholder='Ej: Enfócate en los totales...').bind_value(self, 'user_instructions').classes('w-full')
                            
                    with ui.row():
                        ui.button('Analizar (Regenerar)', on_click=lambda: self.run_analysis(append=False)).props('color=primary')
                        ui.button('Ampliar Análisis', on_click=lambda: self.run_analysis(append=True)).props('color=secondary')
                    
                    ui.button('Siguiente', on_click=lambda: stepper.next())

                with ui.step('Edición y Revisión'):
                    ui.label('Revise y edite el contenido del informe')
                    self.editor = ui.textarea(label='Contenido del Informe').bind_value(self, 'editor_content').classes('w-full h-64')
                    ui.button('Siguiente', on_click=lambda: stepper.next())
                
                with ui.step('Generación'):
                    ui.label('Listo para generar PDF')
                    ui.button('Generar PDF', on_click=self.generate_report)
                    self.result_label = ui.label()

    def load_mock_data(self):
        """Helper to simulate loading data for the wizard"""
        # In prod this comes from ETL service
        self.context_data = {
            "title": "Informe Mensual",
            "tables": ["<table...>...</table>"],
            "charts": ["file:///chart1.png"],
            "text_no_ia": "Datos crudos..."
        }
        self.available_keys = list(self.context_data.keys())
        # Refresh checkboxes
        self.context_container.clear()
        with self.context_container:
            for key in self.available_keys:
                ui.checkbox(key, value=True, on_change=lambda e, k=key: self.toggle_context(k, e.value))
                self.selected_context_keys.append(key)

    def toggle_context(self, key, value):
        if value:
            if key not in self.selected_context_keys:
                self.selected_context_keys.append(key)
        else:
            if key in self.selected_context_keys:
                self.selected_context_keys.remove(key)

    async def run_analysis(self, append: bool = False):
        """Call AI service and update editor"""
        # Ensure data is loaded (mock)
        if not self.context_data:
            self.load_mock_data()
            
        ui.notify('Analizando...', type='info')
        
        try:
            # We call the service logic - usually this blocks, so maybe run in executor if heavy
            # For mockup async mocking check
            result = self.analyzer_service.analyze_data(
                context=self.context_data,
                selection=self.selected_context_keys,
                user_instructions=self.user_instructions
            )
            
            # Combine text parts
            new_text = f"{result.get('introduction_text', '')}\n\n{result.get('analysis_text', '')}"
            
            if append:
                self.editor_content += f"\n\n--- Análisis Ampliado ---\n{new_text}"
            else:
                self.editor_content = new_text
                
            ui.notify('Análisis completado', type='positive')
            
        except Exception as e:
            ui.notify(f'Error en análisis: {e}', type='negative')

    async def generate_report(self):
        """Generate final PDF"""
        try:
            # Prepare final context
            final_context = self.context_data.copy()
            # Inject introduction/content from editor
            final_context['introduction_text'] = self.editor_content
            
            output_path = "/tmp/report_generated.pdf" # In prod, valid path
            
            # Run factory
            # Run factory - Ensure context is passed first, then output_path
            self.report_factory.generate_pdf(final_context, output_path, template_name=self.selected_template)
            
            self.result_label.text = f"PDF generado en: {output_path}"
            ui.notify('PDF Generado', type='positive')
            
        except Exception as e:
            ui.notify(f'Error generando PDF: {e}', type='negative')

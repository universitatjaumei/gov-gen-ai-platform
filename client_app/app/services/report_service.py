from datetime import datetime
from typing import Dict, Any, Optional
from client_app.app.modules.factory.report_factory import ReportFactory
from client_app.app.services.report_analyzer_service import ReportAnalyzerService
from client_app.app.database.models import ReportHistory
from client_app.app.core.state import state

# Basic exception
class ReportGenerationError(Exception):
    pass

class ReportService:
    """
    Servicio de alto nivel para la generación de informes.
    Orquesta la preparación de datos, el análisis por IA (opcional), la generación de PDF y la persistencia.
    Diseñado para uso programático (API/RPA).
    """

    def __init__(self):
        self.factory = ReportFactory()
        self.analyzer = ReportAnalyzerService()

    async def create_report_headless(
        self,
        context: Dict[str, Any],
        template_name: str,
        output_path: str,
        run_analysis: bool = False,
        analysis_instructions: str = ""
    ) -> ReportHistory:
        """
        Genera un informe de forma programática.

        Args:
            context: Datos para el informe (tablas, gráficos, metadatos).
            template_name: Nombre del archivo de plantilla.
            output_path: Ruta de destino para el PDF generado.
            run_analysis: Si es True, ejecuta el análisis por IA sobre el contexto antes de la generación.
            analysis_instructions: Instrucciones para la IA si run_analysis es True.

        Returns:
            Objeto ReportHistory con la información del informe guardada en la base de datos.
        """
        try:
            # 1. AI Analysis (Optional)
            if run_analysis:
                # Automate selection: analyze everything by default in headless mode
                analysis_result = self.analyzer.analyze_data(
                    context=context,
                    selection=None, # Analyze all provided context
                    user_instructions=analysis_instructions
                )
                
                # Merge analysis into context
                # Assuming template expects 'introduction_text' or similar
                context['introduction_text'] = analysis_result.get('introduction_text', '')
                context['analysis_text'] = analysis_result.get('analysis_text', '')

            # 2. Generation
            # Note: template_name is now passed as a keyword argument to support multiple backends
            self.factory.generate_pdf(context, output_path, template_name=template_name)

            # 3. Persistence
            # We use an async session to save history
            report_record = ReportHistory(
                report_name=context.get("title", "Untitled Report"),
                pdf_path=output_path,
                template_used=template_name,
                generated_at=datetime.utcnow(),
                status="success",
                user_instructions=analysis_instructions if run_analysis else None
            )

            async with state.db_session() as session:
                session.add(report_record)
                await session.commit()
                await session.refresh(report_record)
                
            return report_record

        except Exception as e:
            # Log failure if needed (could save failed record)
            raise ReportGenerationError(f"Failed to generate report: {e}")

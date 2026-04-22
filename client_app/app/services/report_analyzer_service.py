import logging
from typing import Dict, List, Optional, Any
from client_app.app.modules.privacy.anonymizer import Anonymizer
from client_app.app.clients.brain_client import BrainClient

logger = logging.getLogger(__name__)

class ReportAnalyzerService:
    """
    Servicio encargado de analizar datos de informes utilizando el cerebro (AI Brain).
    Gestiona un ciclo de procesamiento seguro que incluye:
    1. Filtrado de contexto (opcional).
    2. Anonimización de datos sensibles.
    3. Inferencia mediante el motor de IA.
    4. Desanonimización de los resultados.
    """

    def __init__(self):
        self.anonymizer = Anonymizer()
        self.brain_client = BrainClient()

    def _filter_context(self, context: Dict[str, Any], selection: Optional[List[str]]) -> Dict[str, Any]:
        """
        Filtra el contexto del informe para mantener solo las claves seleccionadas (ej. 'graficos', 'tablas').
        Preserva metadatos básicos como el título.

        Args:
            context: El contexto completo del informe.
            selection: Lista de claves de interés.

        Returns:
            Contexto filtrado para reducir el tamaño del prompt.
        """
        if not selection:
            return context
            
        filtered = {"title": context.get("title", "")}
        
        # Add selected keys if they exist in context
        for key in selection:
            if key in context:
                filtered[key] = context[key]
                
        # If user selected specific items (like 'table_1'), we'd need more complex logic.
        # For now, matching the requirement of "tables/graphics", we assume keys match.
        
        return filtered

    def analyze_data(
        self, 
        context: Dict[str, Any], 
        selection: Optional[List[str]] = None, 
        user_instructions: str = ""
    ) -> Dict[str, str]:
        """
        Analiza los datos de un informe mediante IA de forma segura y privada.

        Args:
            context: Contexto completo del informe (tablas, gráficos, texto).
            selection: Lista de claves a analizar. Si es None, analiza todo.
            user_instructions: Instrucciones adicionales del usuario para guiar el análisis.

        Returns:
            Resultados del análisis (texto resumido, hallazgos, etc.) desanonimizados.
        """
        try:
            logger.info("Starting safe report analysis.")
            
            # 1. Selection
            target_context = self._filter_context(context, selection)
            
            # 2. Anonymization
            anonymized_context, mapping = self.anonymizer.anonymize_structure(target_context)
            logger.debug("Context anonymized.")
            
            # 3. Brain Inference
            # We construct a prompt or pass parameters. 
            # Assuming brain_client.analyze_data takes the data and optional instructions.
            logger.info("Sending anonymized data to Brain.")
            brain_response = self.brain_client.analyze_data(
                data=anonymized_context,
                extra_instructions=user_instructions,
                task_type="report_analysis"
            )
            
            # 4. Deanonymization
            # We assume response is a dict with text fields, or just find any string and deanonymize.
            # Simplified approach: deanonymize values if they are strings.
            deanonymized_response = {}
            for key, value in brain_response.items():
                if isinstance(value, str):
                    deanonymized_response[key] = self.anonymizer.deanonymize_text(value, mapping)
                else:
                    deanonymized_response[key] = value
            
            logger.info("Analysis complete and deanonymized.")
            return deanonymized_response

        except Exception as e:
            logger.error(f"Error during report analysis: {e}")
            raise

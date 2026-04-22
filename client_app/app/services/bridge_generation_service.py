
"""
Bridge Generation Service - Smart Type Bridges using AI.

Este servicio utiliza la inteligencia del 'Brain' para generar código Python
capaz de transformar datos entre formatos incompatibles (ej. List[Dict] -> DataFrame),
actuando como un "puente" inteligente en el flujo de trabajo.
"""
from typing import Dict, Any, Optional
import json
import logging

from client_app.app.clients.brain_client import BrainAPIClient
from client_app.app.services.script_generator_service import script_generator_service

logger = logging.getLogger(__name__)

class BridgeGenerationService:
    """
    Servicio para la generación automática de código de transformación (Smart Bridges).
    Utiliza el ScriptGeneratorService subyacente pero con prompts especializados en
    conversión de tipos.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def generate_bridge_code(
        self, 
        source_type: str, 
        target_type: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Genera el código Python para una función de transformación 'transform(input_data)'.
        
        Args:
            source_type: Descripción del tipo de origen (ej. "List[Dict]", "JSON String").
            target_type: Descripción del tipo de destino (ej. "pandas.DataFrame", "CSV String").
            context: Información adicional opcional (ej. esquema de datos, ejemplos).
            
        Returns:
            Código fuente Python de la función 'transform'.
        """
        # Construir un prompt específico para puentes
        user_prompt = f"""
        Necesito una función Python llamada 'transform' que convierta datos de tipo '{source_type}' a tipo '{target_type}'.
        La entrada se pasa como argumento 'input_data'.
        La salida debe ser el dato convertido.
        
        Detalles adicionales:
        - El código debe ser robusto y manejar excepciones básicas.
        - Debe importar las librerías necesarias dentro de la función (si es posible) o asumir entornos estándar (pandas, json).
        """
        
        if context:
            examples = context.get('examples', [])
            if examples:
                user_prompt += f"\nEjemplos de datos de entrada:\n{examples}"
            
            schema = context.get('schema', {})
            if schema:
                user_prompt += f"\nEsquema de datos esperado:\n{json.dumps(schema, indent=2)}"

        # Delegar a ScriptGeneratorService
        # Usamos output_type="text" o "code" para obtener solo el snippet
        result = await script_generator_service.generate_script(
            user_prompt=user_prompt,
            output_type="code"
        )
        
        if result.get("success"):
            return result.get("code", "")
        else:
            logger.error(f"Error generando bridge: {result.get('error')}")
            # Fallback a un template simple o error
            return f"# Error generando puente: {result.get('error')}\ndef transform(input_data):\n    raise NotImplementedError('Bridge generation failed')"

bridge_generation_service = BridgeGenerationService()

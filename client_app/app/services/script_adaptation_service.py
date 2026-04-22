from dataclasses import dataclass
from typing import Optional, List
import ast
import logging
from client_app.app.services.script_generator_service import script_generator_service

logger = logging.getLogger(__name__)

@dataclass
class ScriptAnalysis:
    """Representa el análisis estructural de un script."""
    detected_purpose: str  # Propósito detectado del script
    main_function: Optional[str]  # Nombre de la función principal detectada
    inputs: List[str]  # Lista de parámetros de entrada detectados
    outputs: List[str]  # Lista de valores de retorno detectados

@dataclass
class AdaptationResult:
    """Resultado del proceso de adaptación del script."""
    success: bool  # Indica si la adaptación fue exitosa
    adapted_code: str  # Código Python final ya adaptado
    preview: str  # Vista previa legible del código
    error: Optional[str] = None  # Mensaje de error si falló

class ScriptAdaptationService:
    """
    Servicio encargado de adaptar scripts externos para que cumplan con los
    requisitos de ejecución de la plataforma.
    Permite envolver código heredado en estructuras compatibles con ETL o Extracción.
    """

    TARGET_REQUIREMENTS = {
        "etl_transform": """
        - Debe tener función principal: def transform(df: pd.DataFrame) -> pd.DataFrame:
        - Input: pandas DataFrame
        - Output: pandas DataFrame transformado
        - Debe importar pandas as pd
        """,
        "extraction": """
        - Debe tener función principal: def extrae_datos(file_path: str) -> dict:
        - Input: ruta a archivo (str)
        - Output: diccionario con datos extraídos {clave: valor}
        """
    }

    async def analyze_script(self, code: str) -> ScriptAnalysis:
        """
        Realiza un análisis estático del código fuente para identificar su estructura.
        Utiliza el módulo AST para detectar funciones y puntos de entrada.

        Args:
            code: Código fuente Python a analizar.

        Returns:
            Objeto ScriptAnalysis con el resumen estructural del script.
        """
        main_func = None
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Heurística simple: la primera función o una llamada 'main'/'transform'
                    if node.name in ['main', 'transform', 'process', 'run']:
                        main_func = node.name
                    elif not main_func:
                         main_func = node.name
        except Exception:
            pass
            
        return ScriptAnalysis(
            detected_purpose="unknown",
            main_function=main_func,
            inputs=[],
            outputs=[]
        )

    async def adapt_to_platform(
        self,
        code: str,
        target_type: str = "etl_transform",
        use_ai: bool = True
    ) -> AdaptationResult:
        """
        Adapta un script externo al formato estándar de la plataforma.

        Args:
            code: El código original que se desea adaptar.
            target_type: El tipo de contrato destino ('etl_transform', 'extraction', etc.).
            use_ai: Si es True, utiliza el motor de IA para realizar la adaptación lógica.

        Returns:
            Objeto AdaptationResult con el código adaptado.
        """
        if use_ai:
            return await self._adapt_with_ai(code, target_type)
        else:
            return self.adapt_from_template(code, target_type)

    def adapt_from_template(self, code: str, target_type: str) -> AdaptationResult:
        """
        Adapta el código utilizando plantillas estáticas y técnicas de wrapping (envoltorio).
        Este es un método determinista que no requiere IA.
        """
        adapted = code
        if target_type == "etl_transform":
            # Indent code and wrap
            lines = code.splitlines()
            indented = "\n    ".join(lines)
            adapted = f"import pandas as pd\n\ndef transform(df):\n    {indented}\n    return df"
        
        return AdaptationResult(
            success=True,
            adapted_code=adapted,
            preview=adapted[:200]
        )

    async def _adapt_with_ai(self, code: str, target_type: str) -> AdaptationResult:
        """
        Utiliza el motor de IA (vía ScriptGeneratorService) para refactorizar el código.
        Solicita a la IA que mantenga la intención original cumpliendo los requisitos técnicos.
        """
        reqs = self.TARGET_REQUIREMENTS.get(target_type, "Función autocontenida.")
        
        prompt = f"""
        Adapta el siguiente script Python para usarse como un paso {target_type}
        en un sistema de workflows.

        Requisitos para {target_type}:
        {reqs}

        - Mantén la lógica original.
        - Asegura imports necesarios.
        - Maneja errores básicos.

        Script original:
        ```python
        {code}
        ```

        Responde SOLO con un JSON válido:
        {{
            "code": "código completo adaptado...",
            "description": "explicación breve"
        }}
        """
        
        response = await script_generator_service.generate_custom_script(prompt=prompt)
        
        if response["success"] and response.get("parsed"):
            parsed = response["parsed"]
            parsed = response["parsed"]
            code_content = parsed.get("code", "")
            description = parsed.get("description")
            
            # Add docstring if description is provided
            if description and code_content:
                # Check if code already starts with a docstring to avoid duplication
                if not code_content.strip().startswith('"""') and not code_content.strip().startswith("'''"):
                    code_content = f'"""\n{description}\n"""\n\n{code_content}'
            
            return AdaptationResult(
                success=True,
                adapted_code=code_content,
                preview=code_content[:200]
            )
        else:
             return AdaptationResult(
                success=False,
                adapted_code="",
                preview="",
                error=response.get("error", "Error adapting script with AI")
            )

script_adaptation_service = ScriptAdaptationService()

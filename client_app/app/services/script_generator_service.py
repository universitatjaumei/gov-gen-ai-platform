"""
Servicio Script Generator - Generación autónoma de scripts Python mediante IA.
Implementación central de CS-03 para la creación de automatismos bajo demanda.
"""
import json
import logging
from typing import List, Dict, Optional, Any
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.clients.brain_client import BrainAPIClient
from client_app.app.database.db import client_engine
from client_app.app.database.models import SecurityPolicy, ServerConnection

logger = logging.getLogger(__name__)

# --- TEMPLATES ---

GENERATION_PROMPT_TEMPLATE = """
Eres un experto programador Python. Tu tarea es crear un script que automatice lo que el usuario necesita.

## PETICIÓN DEL USUARIO
{user_prompt}

## ARCHIVOS DE EJEMPLO (si los hay)
{example_files_info}

## RESTRICCIONES
- El script debe ser autocontenido y ejecutable.
- Solo puedes usar estas librerías: {allowed_libraries}
- NO puedes usar: {forbidden_libraries}
- El script debe manejar errores gracefully.
- Utiliza 'print' para loguear progreso.

## CLARIFICACIONES ADICIONALES
El usuario ha respondido a las siguientes preguntas para precisar la tarea:
{clarifications_text}

## FORMATO DE SALIDA ESPERADO
El usuario espera: {output_type}

## RESPUESTA
Responde EXACTAMENTE en este formato JSON (sin texto adicional). Importante: en el campo "description" incluye siempre dos bloques estandarizados (con su contenido) usando las etiquetas <help_config>...</help_config> (Explicando brevemente cómo configurar tu script) y <help_example>...</help_example> (Dando un ejemplo de entrada y salida):
```json
{{
    "code": "# Script Python aquí...",
    "description": "Explicación en lenguaje natural de qué hace el script. \n\n<help_config>\n### Cómo configurar\n(instrucciones...)\n</help_config>\n\n<help_example>\n### Ejemplo\n(ejemplo...)\n</help_example>",
    "required_libraries": ["pandas", "..."],
    "input_type": "file|files|text|none",
    "input_extensions": [".csv", ".xlsx"],
    "output_type": "file|text|dataframe|chart"
}}
```
"""

REFINEMENT_PROMPT_TEMPLATE = """
Eres un experto programador Python. Debes mejorar un script existente basándote en el feedback del usuario.

## CÓDIGO ACTUAL
```python
{original_code}
```

## FEEDBACK DEL USUARIO
{user_feedback}

## ERROR DE EJECUCIÓN (si lo hay)
{error_message}

## RESULTADO ACTUAL (si lo hay)
{execution_result}

## INSTRUCCIONES
- Corrige los problemas indicados.
- Mantén la funcionalidad que ya funcionaba.
- Solo puedes usar estas librerías: {allowed_libraries}

## RESPUESTA
Responde EXACTAMENTE en este formato JSON (sin texto adicional):
```json
{{
    "code": "# Script Python corregido...",
    "description": "Qué cambios se hicieron",
    "required_libraries": ["pandas", "..."],
    "changes_made": ["Cambio 1", "Cambio 2"]
}}
```
"""

async def get_security_policy() -> SecurityPolicy:
    """Helper to get the default security policy."""
    async with AsyncSession(client_engine) as session:
        result = await session.execute(select(SecurityPolicy))
        policy = result.scalars().first()
        if not policy:
            # Fallback default
            return SecurityPolicy()
        return policy

from client_app.app.core.state import state


class ScriptGeneratorService:
    """
    Servicio central encargado de orquestar la generación, refinamiento y
    auditoría de seguridad de scripts Python generados por IA.
    """
    def __init__(self):
        """Inicializa el servicio y el estado del cliente de cerebro."""
        self._brain_client = None
        self._license_key = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Garantiza que el cliente y la licencia estén cargados una sola vez."""
        if not self._initialized:
            self._brain_client, self._license_key = await self._get_client_and_license()
            self._initialized = True

    async def _get_client_and_license(self):
        """
        Resuelve dinámicamente el cliente de cerebro a utilizar (siempre API)
        y recupera la clave de licencia válida del sistema.

        Returns:
            Tupla (client, license_key).
        """
        async with AsyncSession(client_engine) as session:
            conn = await session.get(ServerConnection, "default")
            
            # Use dynamically resolved URL or default to 8080 (standard monolith port)
            url = conn.brain_url if (conn and conn.brain_url) else "http://localhost:8080"
            license_key = conn.license_key if (conn and conn.license_key) else "DEV_LICENSE_KEY_12345"
            
            # Handle common dev seed mismatches
            if license_key in ["demo_key_123", "dev_key"]:
                license_key = "DEV_LICENSE_KEY_12345"
            
            return BrainAPIClient(base_url=url), license_key

    async def generate_script(
        self,
        user_prompt: str,
        example_files: List[str] = None,
        output_type: str = "file",
        context: str = None,
        clarifications: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Genera un nuevo script Python basado en la solicitud del usuario.
        Utiliza una plantilla enriquecida con contexto local y aclaraciones previas.

        Args:
            user_prompt: Petición principal en lenguaje natural.
            example_files: Lista de rutas a archivos de ejemplo para análisis de estructura.
            output_type: Formato de salida esperado (p.ej., 'file', 'table').
            context: Información adicional de contexto.
            clarifications: Respuestas detalladas a preguntas de precisión.

        Returns:
            Diccionario con el código generado, descripción y metadatos técnicos.
        """
        try:
            await self._ensure_initialized()
            client = self._brain_client
            license_key = self._license_key
            policy = await get_security_policy()
            
            # Construct Prompt
            prompt_text = GENERATION_PROMPT_TEMPLATE.format(
                user_prompt=user_prompt,
                example_files_info=str(example_files) if example_files else "Ninguno",
                allowed_libraries=policy.allowed_imports,
                forbidden_libraries=policy.forbidden_imports,
                output_type=output_type,
                clarifications_text=json.dumps(clarifications, indent=2, ensure_ascii=False) if clarifications else "Ninguna"
            )
            
            # Call Brain
            # generate_script API expects: prompt, output_schema.
            # We treat the entire JSON response structure as the output schema implicitly 
            # or rely on the prompt to enforce it.
            # BrainAPIClient.generate_script signature: prompt, output_schema, license_key...
            
            # We treat 'output_schema' as a hint for structured output if supported, 
            # otherwise just the prompt does the heavy lifting.
            response = await client.generate_script(
                prompt=prompt_text,
                output_schema={}, # Flexible
                license_key=license_key
            )
            
            # Parse Response
            # The Brain might return text containing markdown JSON
            content = response.get("text", "") or response.get("script", "")
            parsed = self._extract_json(content)
            
            if not parsed:
                 return {
                    "success": False,
                    "error": "El servidor no devolvió un JSON válido.",
                    "raw_response": content
                }

            # Check Libraries
            libs_check = await self.check_libraries(parsed.get("required_libraries", []))
            
            return {
                "success": True,
                "code": parsed.get("code", ""),
                "description": parsed.get("description", ""),
                "required_libraries": parsed.get("required_libraries", []),
                "input_type": parsed.get("input_type", "file"),
                "input_extensions": parsed.get("input_extensions", []),
                "output_type": parsed.get("output_type", "file"),
                "warnings": libs_check["forbidden"] + libs_check["unknown"],
                "error": None
            }

        except Exception as e:
            logger.exception("Error generating script")
            return {
                "success": False,
                "error": str(e)
            }
    async def refine_script(
        self,
        original_code: str,
        user_feedback: str,
        error_message: str = None,
        execution_result: str = None
    ) -> Dict[str, Any]:
        """
        Refina un script existente basándose en comentarios del usuario o fallos de ejecución.

        Args:
            original_code: Código fuente actual que se desea mejorar.
            user_feedback: Instrucciones de cambio proporcionadas por el usuario.
            error_message: Mensaje de error (si el refinamiento es por un fallo técnico).
            execution_result: Salida de la última ejecución para contexto adicional.

        Returns:
            Diccionario con el código corregido y la lista de cambios realizados.
        """
        try:
            await self._ensure_initialized()
            client = self._brain_client
            license_key = self._license_key
            policy = await get_security_policy()

            # Construct Prompt
            prompt_text = REFINEMENT_PROMPT_TEMPLATE.format(
                original_code=original_code,
                user_feedback=user_feedback,
                error_message=error_message or "None",
                execution_result=execution_result or "None",
                allowed_libraries=policy.allowed_imports
            )

            # Call Brain
            response = await client.generate_script(
                prompt=prompt_text,
                output_schema={}, 
                license_key=license_key
            )

            # Parse Response
            content = response.get("text", "") or response.get("script", "")
            parsed = self._extract_json(content)

            if not parsed:
                 return {
                    "success": False,
                    "error": "El servidor no devolvió un JSON válido durante el refinamiento.",
                    "raw_response": content
                }

            # Check Libraries
            libs_check = await self.check_libraries(parsed.get("required_libraries", []))

            # Merge with original data structure if needed, but usually we return a fresh struct
            return {
                "success": True,
                "code": parsed.get("code", ""),
                "description": parsed.get("description", ""),
                "required_libraries": parsed.get("required_libraries", []),
                "changes_made": parsed.get("changes_made", []),
                "warnings": libs_check["forbidden"] + libs_check["unknown"],
                "error": None
            }

        except Exception as e:
            logger.exception("Error refining script")
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_custom_script(
        self,
        prompt: str,
        output_schema: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Genera un script utilizando un prompt personalizado, ignorando las plantillas internas.
        Útil para componentes con su propia lógica de prompting específica.

        Args:
            prompt: Instrucción completa (low-level prompt).
            output_schema: Esquema JSON que debe seguir la respuesta de la IA.

        Returns:
            Respuesta estructurada con el código y metadatos resultantes.
        """
        try:
            client, license_key = await self._get_client_and_license()
            
            response = await client.generate_script(
                prompt=prompt,
                output_schema=output_schema or {},
                license_key=license_key
            )
            
            content = response.get("text", "") or response.get("script", "")
            
            # Try parsing if it looks like JSON
            parsed = self._extract_json(content)
            
            return {
                "success": True,
                "content": content,
                "parsed": parsed,
                "error": None
            }
            
        except Exception as e:
            logger.exception("Error generating custom script")
            return {
                "success": False,
                "error": str(e)
            }

    async def check_libraries(self, required_libraries: List[str]) -> Dict[str, List[str]]:
        """
        Verifica las librerías solicitadas por la IA contra la política de seguridad.
        Clasifica cada librería como 'allowed' o 'blocked'.

        Args:
            required_libraries: Lista de nombres de paquetes (pip packages).

        Returns:
            Lista de diccionarios con el estado de seguridad de cada librería.
        """
        policy = await get_security_policy()
        
        allowed = json.loads(policy.allowed_imports) if isinstance(policy.allowed_imports, str) else policy.allowed_imports
        forbidden = json.loads(policy.forbidden_imports) if isinstance(policy.forbidden_imports, str) else policy.forbidden_imports
        
        result = {
            "allowed": [],
            "forbidden": [],
            "unknown": []
        }
        
        for lib in required_libraries:
            if lib in allowed:
                result["allowed"].append(lib)
            elif lib in forbidden:
                result["forbidden"].append(lib)
            else:
                result["unknown"].append(lib)
                
        return result

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extractor robusto de JSON embebido en bloques de código markdown.
        Busca bloques delimitados por ```json y maneja posibles errores de padding.

        Args:
            text: Texto plano que contiene el bloque JSON.

        Returns:
            Diccionario parseado o None si el formato es inválido.
        """
        try:
            # Try direct parse
            return json.loads(text)
        except json.JSONDecodeError:
            pass
            
        # Try finding markdown blocks
        try:
            start = text.find("```json")
            if start != -1:
                end = text.find("```", start + 7)
                if end != -1:
                    json_str = text[start+7:end].strip()
                    return json.loads(json_str)
        except Exception:
            pass
            
        return None

script_generator_service = ScriptGeneratorService()

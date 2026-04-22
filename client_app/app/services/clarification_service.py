
"""
ClarificationService - Servicio central para clarificaciones previas a generación.

Este servicio permite a la IA solicitar información adicional antes de generar
scripts, reduciendo ciclos de refinamiento y mejorando la precisión.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
import json
import logging

from client_app.app.clients.brain_client import BrainAPIClient

logger = logging.getLogger(__name__)


class QuestionType(Enum):
    """Tipos de preguntas de clarificación."""
    SINGLE_CHOICE = "single_choice"      # Una opción de varias
    MULTIPLE_CHOICE = "multiple_choice"  # Varias opciones
    FREE_TEXT = "free_text"              # Respuesta abierta
    YES_NO = "yes_no"                    # Booleano
    FILE_UPLOAD = "file_upload"          # Archivo adicional


@dataclass
class ClarificationQuestion:
    """Representa una pregunta de clarificación."""
    id: str
    question: str
    type: QuestionType
    options: Optional[List[str]] = None  # Para choice types
    hint: Optional[str] = None           # Ayuda contextual
    required: bool = True
    default: Optional[str] = None


@dataclass
class ClarificationResponse:
    """Representa una respuesta del usuario a una pregunta."""
    question_id: str
    answer: Union[str, List[str], bool]


@dataclass
class ClarificationResult:
    """Resultado del análisis de clarificación."""
    needs_clarification: bool
    questions: List[ClarificationQuestion]
    confidence_score: float  # 0-1, qué tan segura está la IA
    reasoning: str           # Por qué necesita estas preguntas


# Mapeo de módulo a tier de modelo para clarificación
MODULE_TIER_MAP = {
    "custom_script": 3,  # supervision - máxima ambigüedad
    "etl": 2,            # logico_navegacion
    "rpa": 2,            # logico_navegacion
    "extraction": 2      # logico_navegacion
}

# Mapeo de tier a role_key
TIER_TO_ROLE = {
    1: "extraccion_pdf",
    2: "logico_navegacion",
    3: "supervision"
}


class ClarificationService:
    """
    Servicio central para gestionar clarificaciones previas a generación.

    Flujo:
    1. analyze_for_clarification() - Analiza si necesita más info
    2. Si needs_clarification=True, mostrar UI con preguntas
    3. generate_with_clarifications() - Genera con las respuestas
    """

    CONFIDENCE_THRESHOLD = 0.8  # Si >= umbral, no necesita clarificación
    MAX_QUESTIONS = 3           # Máximo de preguntas para evitar fatiga

    def __init__(self):
        """
        Inicializa el servicio de clarificación con un registro vacío de plantillas de prompts.
        """
        self._prompts: Dict[str, str] = {}

    def get_supported_modules(self) -> List[str]:
        """Retorna los módulos que soportan clarificación."""
        return list(MODULE_TIER_MAP.keys())

    def get_module_tier(self, module_type: str) -> int:
        """Retorna el tier de modelo para un módulo."""
        return MODULE_TIER_MAP.get(module_type, 2)

    def get_module_role(self, module_type: str) -> str:
        """Retorna el role_key para un módulo."""
        tier = self.get_module_tier(module_type)
        return TIER_TO_ROLE.get(tier, "logico_navegacion")

    async def analyze_for_clarification(
        self,
        module_type: str,
        user_input: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ClarificationResult:
        """
        Analiza si la IA necesita más información antes de proceder con la generación.

        Examina el input del usuario y el contexto disponible para detectar posibles
        ambigüedades. Si el nivel de confianza es inferior al umbral establecido,
        se generan preguntas de clarificación.

        Args:
            module_type (str): Tipo de módulo ('custom_script', 'etl', 'rpa', 'extraction').
            user_input (Dict[str, Any]): Datos originales del formulario del usuario.
            context (Dict[str, Any]): Metadatos adicionales (archivos, ejemplos, etc.).

        Returns:
            ClarificationResult: Objeto que indica si se requiere clarificación y
                contiene las preguntas a realizar.

        Raises:
            ValueError: Si el `module_type` no está soportado por el servicio.
        """
        if module_type not in self.get_supported_modules():
            raise ValueError(f"Módulo no soportado: {module_type}")

        # Obtener prompt específico del módulo
        prompt = self._get_analysis_prompt(module_type, user_input, context)

        # Llamar a la IA
        response = await self._call_ai_for_analysis(module_type, prompt)

        # Parsear respuesta
        return self._parse_analysis_response(response)

    async def generate_with_clarifications(
        self,
        module_type: str,
        user_input: Dict[str, Any],
        clarifications: List[ClarificationResponse],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Genera el artefacto final incorporando las respuestas de clarificación del usuario.

        Este método es el punto de entrada para la generación tras resolver ambigüedades.
        Primero construye un `enriched_input` que unifica los datos originales con
        las respuestas obtenidas, y luego delega la ejecución al servicio técnico
        correspondiente.

        Args:
            module_type (str): Tipo de módulo para la generación.
            user_input (Dict[str, Any]): Datos originales proporcionados por el usuario.
            clarifications (List[ClarificationResponse]): Lista de respuestas a las
                preguntas de clarificación planteadas previamente.
            context (Dict[str, Any]): Contexto técnico del entorno de ejecución.

        Returns:
            Dict[str, Any]: Resultado de la generación (depende del módulo delegado).
        """
        # Enriquecer el input con las clarificaciones
        enriched_input = self._enrich_input_with_clarifications(
            user_input, clarifications
        )

        # Delegar al servicio específico del módulo
        return await self._delegate_generation(module_type, enriched_input, context)

    def _get_analysis_prompt(
        self,
        module_type: str,
        user_input: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Construye el prompt de análisis final combinando la plantilla del módulo con los datos de entrada.

        Args:
            module_type: El tipo de módulo para el que se genera el prompt.
            user_input: Datos proporcionados por el usuario.
            context: Contexto adicional disponible.

        Returns:
            Cadena de texto con el prompt listo para ser enviado a la IA.
        """
        # Los prompts específicos se registran externamente
        base_prompt = self._prompts.get(f"clarification_{module_type}")

        if not base_prompt:
            # Fallback a prompt genérico
            base_prompt = self._get_generic_analysis_prompt()

        # Formatear con los datos del usuario
        return base_prompt.format(
            user_input=json.dumps(user_input, ensure_ascii=False, indent=2),
            context_summary=self._summarize_context(context),
            module_type=module_type
        )

    def _get_generic_analysis_prompt(self) -> str:
        """
        Retorna una plantilla de prompt genérica para situaciones donde no hay un prompt específico de módulo.
        """
        return """
Analiza la siguiente petición y determina si necesitas más información.

## PETICIÓN DEL USUARIO
{user_input}

## CONTEXTO DISPONIBLE
{context_summary}

## INSTRUCCIONES
- Si la información es suficiente (confidence >= 0.8), indica needs_clarification: false
- Si hay ambigüedades, genera máximo 3 preguntas críticas
- NO preguntes obviedades
- Prioriza preguntas que afecten la estructura del resultado

## RESPUESTA (JSON)
```json
{{
    "needs_clarification": true|false,
    "confidence_score": 0.0-1.0,
    "reasoning": "Explicación breve",
    "questions": [...]
}}
```
"""

    def _summarize_context(self, context: Dict[str, Any]) -> str:
        """
        Genera un resumen textual del contexto disponible (archivos, ejemplos, etc.)
        para incluirlo en el prompt de análisis.
        """
        if not context:
            return "Sin contexto adicional."

        summary_parts = []
        if "files" in context:
            summary_parts.append(f"Archivos: {len(context['files'])}")
        if "examples" in context:
            summary_parts.append(f"Ejemplos disponibles: {len(context['examples'])}")

        return "; ".join(summary_parts) if summary_parts else "Contexto vacío."

    async def _call_ai_for_analysis(
        self,
        module_type: str,
        prompt: str
    ) -> Dict[str, Any]:
        """
        Inicia la llamada asíncrona a la BrainAPI para obtener el análisis de ambigüedad.
        """
        role = self.get_module_role(module_type)
        
        # Resolver parámetros de conexión desde la base de datos local
        from client_app.app.database.models import ServerConnection
        from client_app.app.database.db import client_engine
        from sqlmodel.ext.asyncio.session import AsyncSession
        from sqlmodel import select
        
        async with AsyncSession(client_engine) as session:
            stmt = select(ServerConnection).where(ServerConnection.is_active == True)
            res = await session.exec(stmt)
            conn = res.first()
            brain_url = conn.brain_url if conn else "http://localhost:8000"
            license_key = conn.license_key if conn else "TRIAL-KEY"

        client = BrainAPIClient(base_url=brain_url)
        response = await client.call_llm(prompt, role=role, license_key=license_key)

        # Parsear JSON de la respuesta
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"Error parseando respuesta de clarificación: {response}")
            return {
                "needs_clarification": False,
                "confidence_score": 0.5,
                "reasoning": "Error en análisis",
                "questions": []
            }

    def _parse_analysis_response(self, response: Dict[str, Any]) -> ClarificationResult:
        """
        Transforma la respuesta JSON de la IA en objetos ClarificationQuestion y ClarificationResult.
        """
        questions = []

        for q_data in response.get("questions", []):
            try:
                question = ClarificationQuestion(
                    id=q_data.get("id", f"q_{len(questions)+1}"),
                    question=q_data["question"],
                    type=QuestionType(q_data.get("type", "free_text")),
                    options=q_data.get("options"),
                    hint=q_data.get("hint"),
                    required=q_data.get("required", True),
                    default=q_data.get("default")
                )
                questions.append(question)
            except (KeyError, ValueError) as e:
                logger.warning(f"Error parseando pregunta: {e}")
                continue

        # Limitar a MAX_QUESTIONS
        questions = questions[:self.MAX_QUESTIONS]

        return ClarificationResult(
            needs_clarification=response.get("needs_clarification", False),
            questions=questions,
            confidence_score=float(response.get("confidence_score", 0.5)),
            reasoning=response.get("reasoning", "")
        )

    def _enrich_input_with_clarifications(
        self,
        user_input: Dict[str, Any],
        clarifications: List[ClarificationResponse]
    ) -> Dict[str, Any]:
        """
        Crea un 'enriched_input' combinando los datos originales con las clarificaciones.

        El `enriched_input` es un diccionario que actúa como fuente única de verdad para
        los servicios de generación. Las clarificaciones se almacenan bajo la clave
        interna `_clarifications`, permitiendo a los LLM y motores de reglas acceder
        a la información refinada sin perder los datos originales.

        Data Flow:
            1. Se realiza una copia profunda (vía `.copy()`) del `user_input`.
            2. Se extraen los pares {pregunta_id: respuesta} de la lista `clarifications`.
            3. Se inyecta el diccionario de respuestas en `_clarifications`.
            4. El resultado se pasa a `_delegate_generation`.

        Args:
            user_input (Dict[str, Any]): Diccionario original de entrada del usuario.
            clarifications (List[ClarificationResponse]): Respuestas validadas.

        Returns:
            Dict[str, Any]: El `enriched_input` listo para su procesamiento técnico.
        """
        enriched = user_input.copy()
        enriched["_clarifications"] = {
            resp.question_id: resp.answer for resp in clarifications
        }
        return enriched

    async def _delegate_generation(
        self,
        module_type: str,
        enriched_input: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Delega el proceso final de generación al servicio de módulo correspondiente.
        """
        # Mapping dispatch
        if module_type == "custom_script":
            return await self._delegate_custom_script(enriched_input, context)
            
        elif module_type == "extraction":
            return await self._delegate_extraction(enriched_input, context)

        elif module_type == "etl":
           return await self._delegate_etl(enriched_input, context)

        elif module_type == "rpa":
             return await self._delegate_rpa(enriched_input, context)

        error_msg = f"Delegación no implementada para módulo: {module_type}"
        import logging
        logging.getLogger(__name__).error(error_msg)
        raise NotImplementedError(error_msg)

    async def _delegate_rpa(self, enriched_input: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delega la generación de RPA al ejecutor.
        """
        from client_app.app.core.state import state
        from datetime import datetime
        
        recording_logs = enriched_input.get("recording_logs") or enriched_input.get("logs", [])
        
        # Si tenemos logs de grabación, procedemos al análisis
        if recording_logs:
            try:
                # Extraer contexto relevante
                analysis_context = context.copy()
                analysis_context.update(enriched_input.get("context", {}))
                
                playbook = await state.rpa.analyze_recording(
                    recording_logs=recording_logs,
                    context_dict=analysis_context
                )
                
                return {
                    "status": "success",
                    "module_type": "rpa",
                    "playbook": playbook,
                    "generated_at": datetime.now().isoformat(),
                    "metadata": {
                        "steps_count": len(playbook),
                        "source": "recording_analysis"
                    }
                }
            except Exception as e:
                return {
                    "status": "error", 
                    "module_type": "rpa",
                    "error":f"Error analizando grabación RPA: {str(e)}"
                }

        # Si no hay logs, devolvemos estructura indicando que falta grabación
        # Esto permite que la UI solicite la grabación al usuario
        return {
            "status": "pending_input",
            "module_type": "rpa", 
            "message": "Se requiere una grabación de acciones para generar el RPA.",
            "required_input": "recording_logs",
            "suggested_action": "open_recorder"
        }

    async def _delegate_custom_script(
        self,
        enriched_input: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delegación especializada a ScriptGeneratorService."""
        # Use injected service or import
        script_gen = getattr(self, "script_generator", None)
        if not script_gen:
            from client_app.app.services.script_generator_service import script_generator_service
            script_gen = script_generator_service
        
        prompt = enriched_input.get("user_prompt") or enriched_input.get("prompt", "")
        clarifications = enriched_input.get("_clarifications", {})
        
        # Extract files from context or input
        example_files = context.get("examples", [])
        if not example_files and "files" in context:
             # If "files" exists in context, it might be the files to process or examples
             # Assume for custom script, context['files'] might be relevant examples or input sample
             # But script_generator.generate_script expects list of paths
             example_files = [f for f in context.get("files", []) if isinstance(f, str)]

        return await script_gen.generate_script(
            user_prompt=prompt,
            example_files=example_files,
            output_type=enriched_input.get("output_type", "file"),
            context=self._summarize_context(context), # Pass context summary as string? Or full dict? signature says str
            clarifications=clarifications
        )

    async def _delegate_extraction(
        self,
        enriched_input: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delegación especializada a ExtractionService."""
        # Use injected service or import
        extract_svc = getattr(self, "extraction_service", None)
        if not extract_svc:
            from client_app.app.services.extraction_service import ExtractionService
            extract_svc = ExtractionService() # Instantiate

        # input for extraction usually involves files
        files = enriched_input.get("files", [])
        if not files and "files" in context:
            files = context["files"]
            
        if not files:
             return {"error": "No files provided for extraction."}

        # User instructions might come from prompt
        user_definition = enriched_input.get("user_prompt", "")
        clarifications = enriched_input.get("_clarifications", {})
        
        # Append clarifications to user definition
        if clarifications:
            clarification_text = "\nCLARIFICACIONES:\n" + "\n".join([f"- {k}: {v}" for k, v in clarifications.items()])
            user_definition += clarification_text

        # Use process_files_generic for now (Phase 1)
        # Assuming we want generic extraction guided by LLM
        return await extract_svc.process_files_generic(
            file_paths=files,
            target_fields=enriched_input.get("target_fields"), # Optional
            recognize_all=True, # Default to auto-discovery if fields not present
            on_progress=lambda x: None # No UI callback here
        )

    async def _delegate_etl(
        self,
        enriched_input: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Delegación especializada a ETLService/Factory."""
        from client_app.app.modules.factory.etl_factory import ETLScriptFactory
        from client_app.app.services.etl_service import ETLService
        from sqlmodel.ext.asyncio.session import AsyncSession
        from client_app.app.database.db import client_engine

        # We need a session for ETLService
        async with AsyncSession(client_engine) as session:
            # We can use ETLService to orchestrate, or Factory directly if we just want code.
            # "generate_with_clarifications" implies we want the *artifact* (script) or result?
            # Usually for ETL we want the SCRIPT first.
            
            # Using Factory directly to generate script
            factory = ETLScriptFactory()
            
            # Prepare inputs
            source_file = enriched_input.get("source_file")
            if not source_file and "files" in context and context["files"]:
                source_file = context["files"][0]
                
            if not source_file:
                 return {"error": "No source file provided for ETL."}
                 
            # We need to read a sample of the source file to pass to factory
            # ETLService has helper for this, maybe reuse ETLService?
            etl_service = ETLService(session=session, factory=factory)
            
            # Helper to peek at file format/content
            try:
                fmt = etl_service._detect_format(source_file)
                df = await etl_service._read_source_file(source_file, fmt)
                sample = df.head(10)
            except Exception as e:
                return {"error": f"Failed to read source file: {e}"}

            user_instructions = enriched_input.get("user_prompt", "")
            clarifications = enriched_input.get("_clarifications", {})
             # Append clarifications
            if clarifications:
                clarification_text = "\nCLARIFICACIONES:\n" + "\n".join([f"- {k}: {v}" for k, v in clarifications.items()])
                user_instructions += clarification_text
            
            # Resolve Client (needed by factory)
            client, license_key = await etl_service._get_brain_client()

            result = await factory.generate_transformation_script(
                source_sample=sample,
                target_spec=enriched_input.get("target_spec", "Auto-detect transformation"),
                output_format=enriched_input.get("output_format", "csv"),
                user_instructions=user_instructions,
                client=client,
                license_key=license_key
            )
            
            return result

    def register_module_prompt(self, module_type: str, prompt_template: str):
        """Registra un prompt de análisis para un módulo."""
        self._prompts[f"clarification_{module_type}"] = prompt_template


# Singleton para uso global
clarification_service = ClarificationService()

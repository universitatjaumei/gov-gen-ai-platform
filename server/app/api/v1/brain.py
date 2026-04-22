"""
Brain API Router - V1
Endpoints para orquestación de IA y servicios de cerebro.
"""

from typing import List, Dict, Any, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, Header, Body
from pydantic import BaseModel
import base64
import traceback

from server.app.services.knowledge_orchestrator_service import knowledge_orchestrator
from server.app.modules.brain.infrastructure.llm_gateway import ejecutar_tarea
from server.app.services.ai_brain import AIBrainService
from server.app.modules.brain.billing_engine import billing_engine

router = APIRouter(
    prefix="/brain",
    tags=["brain"]
)


# =============================================================================
# REQUEST MODELS
# =============================================================================

# --- Script Generation ---
class GenerateScriptRequest(BaseModel):
    """Solicitud para generar un script de automatización mediante un prompt."""
    prompt: str
    output_schema: Dict[str, Any]
    model: Optional[str] = None
    temperature: float = 0.7


# --- Extraction ---
class AnalyzeDocumentRequest(BaseModel):
    """Solicitud para analizar la estructura de documentos (Fase 0)."""
    texto_a: str
    texto_b: str
    definicion_usuario: str
    service_id: str = "sys_phase0_discovery"


class ExtractDataRequest(BaseModel):
    """Solicitud para extraer datos de un documento (Fase 1)."""
    user_definition: str
    target_fields: List[str] = []
    usar_tier_2: bool = False
    ejemplos_validacion: Optional[Dict[str, Any]] = None
    texto_fitz: Optional[str] = None
    texto_plumber: Optional[str] = None


class RefineExtractionRequest(BaseModel):
    """Solicitud para refinar una extracción con feedback (Fase 1.5)."""
    texto_fitz: str
    texto_plumber: str
    datos_anteriores: Dict[str, Any]
    feedback_usuario: str
    service_id: str = "sys_phase1_refinement"


class GuidedFieldRequest(BaseModel):
    """Solicitud para extraer un campo específico mediante un snippet de texto."""
    field_name: str
    snippet_text: str
    expected_format: str = "text"


# --- Factory ---
class GenerateExtractionScriptRequest(BaseModel):
    """Solicitud para generar un script de extracción determinista (Fase 3)."""
    docs_text_list: List[Dict[str, str]]
    campos_objetivo: List[str]
    values_example: Optional[Dict[str, Any]] = None
    info_discovery: Optional[Dict[str, Any]] = None
    feedback: Optional[str] = None
    field_definitions: Optional[List[Dict[str, Any]]] = None


class RefineScriptRequest(BaseModel):
    """Solicitud para refinar un script de extracción tras un error."""
    script_actual: str
    reporte_forense: str
    feedback_history: List[Dict[str, Any]]
    texto_documento: str
    target_fields: List[str] = []


class ScriptEscalationRequest(BaseModel):
    """Solicitud para escalar la creación/corrección de un script al Partner."""
    script_name: str
    original_code: str
    client_notes: Optional[str] = None
    escalation_type: str = "extraction"


class ForensicAuditRequest(BaseModel):
    """Solicitud para auditar un script comparando sus resultados con la IA."""
    referencia_ia: Dict[str, Any]
    resultado_script: Any


# --- RPA ---
class AnalyzeRecordingRequest(BaseModel):
    """Solicitud para analizar una grabación de usuario y generar un playbook RPA."""
    recording_logs: List[Dict[str, Any]]
    context_dict: Optional[Dict[str, Any]] = None


class RefinePlaybookRequest(BaseModel):
    """Solicitud para refinar un playbook RPA existente."""
    current_playbook: List[Dict[str, Any]]
    recording_logs: List[Dict[str, Any]]
    error_logs: str
    user_feedback_history: List[str]
    context_data: Dict[str, Any]


class VisualLocateRequest(BaseModel):
    """Solicitud para localizar un elemento visualmente en una captura de pantalla."""
    png_base64: str  # Base64 encoded image
    description: str
    viewport: Dict[str, int]


# --- LLM ---
class CallLLMRequest(BaseModel):
    """Solicitud genérica de llamada al LLM."""
    prompt: str
    role: str = "general"  # Role hint for model selection
    service_id: Optional[str] = None # Nuevo: ID de prompt específico
    config_summary: Optional[Dict[str, Any]] = None # Nuevo: Contexto para formatear el prompt
    model: Optional[str] = None
    temperature: float = 0.5


# --- COPILOT ---
class CopilotAskRequest(BaseModel):
    """Solicitud de consulta al asistente Copilot."""
    query: str
    local_context: str = ""
    conversation_history: List[Dict[str, str]] = []
    atom_id: Optional[str] = None
    flow_context: Optional[Dict[str, Any]] = None
    mode: str = "idle"  # flow, atom, wizard, documentation, idle
    model: Optional[str] = None
    temperature: float = 0.5


class GenerateBridgeRequest(BaseModel):
    """Solicitud para generar código de conversión entre tipos (Bridge)."""
    source_type: str
    target_type: str
    source_name: str
    target_name: str
    example_value: Optional[str] = None
    model: Optional[str] = None


# --- AGENT ---
class AgentStepRequest(BaseModel):
    """Solicitud para ejecutar un paso del agente autónomo."""
    task_instruction: str
    page_state: Dict[str, Any]  # {url, title, screenshot_base64, html_snippet}
    action_history: List[Dict[str, Any]]  # [{action, selector, value, result, timestamp}]


# --- SECURITY ENDPOINTS ---

@router.get("/security/effective_policy")
async def get_effective_policy(
    x_license_key: str = Header(...)
):
    """
    Obtiene la política de seguridad efectiva para el cliente actual.

    La política se resuelve usando el motor de cascada:
    CLIENTE > PARTNER > SISTEMA

    Returns:
        Política efectiva con:
        - allowed_domains: List[str]
        - allowed_libraries: List[str]
        - forbidden_libraries: List[str]
        - max_memory_mb: int
        - max_execution_time: int
        - applied_level: str (CLIENT, PARTNER, SYSTEM)
        - screenshot_policy: str (BLOCK, REVIEW, TRUSTED)
    """
    from sqlmodel import select
    from sqlmodel.ext.asyncio.session import AsyncSession
    from server.app.database.db import server_engine
    from server.app.database.models import ClientAccount
    from server.app.services.security_policy_service import SecurityPolicyService
    import hashlib

    default_policy = {
        "allowed_domains": [],
        "allowed_libraries": ["pandas", "json", "re", "math", "datetime"],
        "forbidden_libraries": ["os", "sys", "subprocess"],
        "max_memory_mb": 512,
        "max_execution_time": 300,
        "applied_level": "SYSTEM",
        "scope": "SYSTEM",
        "screenshot_policy": "REVIEW"
    }

    try:
        # Hash the license key to find the client
        key_hash = hashlib.sha256(x_license_key.encode()).hexdigest()

        async with AsyncSession(server_engine) as session:
            # Find client by license_key hash
            result = await session.execute(
                select(ClientAccount).where(ClientAccount.license_key == key_hash)
            )
            client = result.scalar_one_or_none()

            if not client:
                return default_policy

            # Get effective policy using cascade
            policy_service = SecurityPolicyService(session)
            effective_policy = await policy_service.get_effective_policy(client.client_id)

            return effective_policy

    except Exception as e:
        print(f"[API ERROR] get_effective_policy: {e}")
        return default_policy


# --- LICENSE ENDPOINTS ---

@router.get("/validate_license")
async def validate_license(x_license_key: str = Header(...)):
    """
    Valida una licencia y retorna información de cuota.

    Returns:
        - valid: bool
        - quota_remaining: int (tokens restantes)
        - expires_at: str (ISO format)
    """
    brain_service = AIBrainService()
    try:
        license_obj = await brain_service._validate_license(x_license_key)
        return {
            "valid": True,
            "quota_remaining": license_obj.remaining_tokens(),
            "expires_at": license_obj.valid_until.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# --- ORCHESTRATION ENDPOINTS ---

class OrchestrateRequest(BaseModel):
    """Solicitud para la orquestación central de un flujo basado en lenguaje natural."""
    prompt: str
    local_inventory: List[Dict[str, Any]] = []
    client_id: Optional[str] = None
    partner_id: Optional[str] = None

@router.post("/orchestrate")
async def orchestrate(
    request: OrchestrateRequest,
    x_license_key: str = Header(...),
) -> Dict[str, Any]:
    """
    Orquestador central de flujos basado en lenguaje natural.

    Este método coordina la construcción de un prompt híbrido que combina la consulta
    del usuario con el inventario local y el conocimiento del servidor, para luego
    ejecutar una tarea en el LLM configurado.

    Args:
        request (OrchestrateRequest): Objeto con el prompt del usuario e inventario local.
        x_license_key (str): Clave de licencia proporcionada en la cabecera HTTP.

    Returns:
        Dict[str, Any]: Resultado de la ejecución del LLM, incluyendo la respuesta generada
            y metadatos de consumo de tokens.

    Raises:
        HTTPException: 401 si la licencia es inválida o 500 si ocurre un error interno.

    Flow:
        1. Valida la licencia del cliente.
        2. Obtiene el contexto de cliente y partner.
        3. Construye el prompt híbrido mediante el `knowledge_orchestrator`.
        4. Resuelve la configuración del modelo de "supervisión".
        5. Ejecuta la tarea en el LLM y registra el consumo en el motor de facturación.
    """
    brain_service = AIBrainService()
    
    try:
        # 1. Validar Licencia
        # Internamente _validate_license lanza ValueError si falla
        license_obj = await brain_service._validate_license(x_license_key)
        
        # Uso de identificadores del contexto de licencia si no vienen en la request
        client_id = request.client_id or license_obj.client_id
        # El partner_id lo sacamos del Cliente asociado a la licencia
        # Para simplificar en este paso, asumimos que AIBrainService tiene acceso a estos datos
        # si no vienen explícitamente.
        
        partner_id = request.partner_id
        if not partner_id:
             from sqlmodel import select
             from sqlmodel.ext.asyncio.session import AsyncSession
             from server.app.database.db import server_engine
             from server.app.database.models import ClientAccount
             async with AsyncSession(server_engine) as session:
                 client = await session.get(ClientAccount, client_id)
                 partner_id = client.partner_id if client else None

        # 2. Construir System Prompt Híbrido
        system_prompt = await knowledge_orchestrator.build_hybrid_system_prompt(
            user_query=request.prompt,
            local_inventory=request.local_inventory,
            client_id=client_id,
            partner_id=partner_id,
            prompt_name="flow_orchestrator"
        )
        
        # 3. Resolver Config de Modelo para Orquestación
        # Usamos el rol "supervision" por defecto para orquestación de flujos
        config, _ = await brain_service._resolve_server_config(role_key="supervision")
        
        # 4. Ejecutar Tarea en LLM
        # Combinamos system_prompt y prompt del usuario
        full_query = f"{system_prompt}\n\nUSER QUERY:\n{request.prompt}"
        
        result = await ejecutar_tarea(
            prompt=full_query,
            config=config,
            script_origen="orchestrator"
        )
        
        # 5. Registrar Consumo (Opcional, pero recomendado)
        try:
             await billing_engine.record_consumption(
                 client_id=license_obj.client_id,
                 tokens=result.get("tokens_used", 0),
                 model=config.get("model", "unknown"),
                 operation_type="orchestrate_flow"
             )
        except Exception as billing_err:
             print(f"[BILLING ERROR] Could not record consumption: {billing_err}")
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        print(f"[API ERROR] Orchestrate: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error interno del orquestador")


# =============================================================================
# SCRIPT GENERATION ENDPOINTS
# =============================================================================

@router.post("/generate_script")
async def generate_script(
    request: GenerateScriptRequest,
    x_license_key: str = Header(...)
) -> Dict[str, Any]:
    """
    Genera un script de extracción basado en un prompt y un esquema de salida.

    Utiliza el Tier 3 (supervisión) para asegurar la máxima calidad y precisión del
    código generado.

    Args:
        request (GenerateScriptRequest): Parámetros de generación (prompt, esquema, etc.).
        x_license_key (str): Clave de licencia para validación y facturación.

    Returns:
        Dict[str, Any]: Diccionario con el script generado (`script`) y el recuento
            de tokens utilizados (`tokens_used`).

    Raises:
        HTTPException: 401 si falla la licencia o 500 ante errores de generación.
    """
    brain_service = AIBrainService()

    try:
        # 1. Validar licencia
        await brain_service._validate_license(x_license_key)

        # 2. Resolver config para generación de scripts
        config, system_prompt = await brain_service._resolve_server_config(
            service_id="sys_phase3_factory_gen",
            role_key="supervision"
        )

        # 3. Construir prompt completo
        schema_str = str(request.output_schema)
        full_prompt = f"{system_prompt}\n\nOUTPUT SCHEMA:\n{schema_str}\n\nTASK:\n{request.prompt}"

        # 4. Ejecutar
        result = await ejecutar_tarea(
            prompt=full_prompt,
            config=config,
            script_origen="generate_script_api"
        )

        # 5. Registrar Consumo (Proceso en background para no bloquear)
        try:
             await billing_engine.record_consumption(
                 client_id=license_obj.client_id,
                 tokens=result.get("tokens_used", 0),
                 model=result.get("model_used") or config.get("model", "unknown"),
                 operation_type="generate_script"
             )
        except Exception as billing_err:
             print(f"[BILLING ERROR] Could not record consumption: {billing_err}")

        return {
            "script": result.get("response", ""),
            "tokens_used": result.get("tokens_used", 0)
        }

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        print(f"[API ERROR] generate_script: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error generando script")


@router.post("/call_llm")
async def call_llm(
    request: CallLLMRequest,
    x_license_key: str = Header(...)
) -> Dict[str, Any]:
    """
    Realiza una llamada genérica al LLM para tareas auxiliares.

    Selecciona el modelo adecuado basándose en la pista de 'role' proporcionada
    en la solicitud, permitiendo optimizar velocidad vs. inteligencia.

    Args:
        request (CallLLMRequest): Datos de la llamada (prompt, role, temperatura).
        x_license_key (str): Clave de licencia del cliente.

    Returns:
        Dict[str, Any]: Respuesta del LLM (`response`) y tokens consumidos (`tokens_used`).

    Role Mapping:
        - "general": Tier 1 (Máxima velocidad, tareas simples).
        - "analysis": Tier 2 (Balanceado, tareas lógicas).
        - "supervision": Tier 3 (Máxima inteligencia, supervisión técnica).
    """
    brain_service = AIBrainService()

    try:
        # Mapear role a tier
        role_mapping = {
            "general": "extraccion_pdf",      # Tier 1
            "analysis": "logico_navegacion",  # Tier 2
            "supervision": "supervision"       # Tier 3
        }
        role_key = role_mapping.get(request.role, "logico_navegacion")

        return {
            "response": await brain_service.call_llm(
                prompt=request.prompt,
                role_key=role_key,
                service_id=request.service_id,
                config_summary=request.config_summary,
                model=request.model,
                temperature=request.temperature,
                license_key=x_license_key
            ),
            "tokens_used": 0 # TODO: AIBrainService.call_llm should return tokens too
        }

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        print(f"[API ERROR] call_llm: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error en llamada LLM")


# =============================================================================
# EXTRACTION ENDPOINTS
# =============================================================================

@router.post("/extraction/analyze_structure")
async def analyze_document_structure(
    request: AnalyzeDocumentRequest,
    x_license_key: str = Header(...)
):
    """
    Fase 0: Descubrimiento de estructura de documentos.
    Analiza dos documentos para identificar campos y patrones comunes.
    """
    brain_service = AIBrainService()

    try:
        await brain_service._validate_license(x_license_key)

        result = await brain_service.analyze_document_structure(
            texto_a=request.texto_a,
            texto_b=request.texto_b,
            definicion_usuario=request.definicion_usuario,
            service_id=request.service_id
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        print(f"[API ERROR] analyze_structure: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error analizando estructura")


@router.post("/extraction/extract")
async def extract_data(
    request: ExtractDataRequest,
    x_license_key: str = Header(...)
):
    """
    Fase 1: Extracción de datos desde texto pre-procesado.
    Requiere texto_fitz y texto_plumber (el cliente debe extraer el texto del PDF).
    """
    brain_service = AIBrainService()

    try:
        await brain_service._validate_license(x_license_key)

        if not request.texto_fitz or not request.texto_plumber:
            raise HTTPException(
                status_code=400,
                detail="Se requiere texto_fitz y texto_plumber. El cliente debe extraer el texto del PDF."
            )

        result = await brain_service.extract_data(
            file_path="",  # No usado cuando se provee texto
            user_definition=request.user_definition,
            target_fields=request.target_fields,
            usar_tier_2=request.usar_tier_2,
            ejemplos_validacion=request.ejemplos_validacion,
            texto_fitz=request.texto_fitz,
            texto_plumber=request.texto_plumber
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API ERROR] extract_data: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error extrayendo datos")


@router.post("/extraction/refine")
async def refine_extraction(
    request: RefineExtractionRequest,
    x_license_key: str = Header(...)
):
    """
    Fase 1.5: Refinamiento de extracción con feedback del usuario.
    """
    brain_service = AIBrainService()

    try:
        await brain_service._validate_license(x_license_key)

        result = await brain_service.refine_extraction_data(
            texto_fitz=request.texto_fitz,
            texto_plumber=request.texto_plumber,
            datos_anteriores=request.datos_anteriores,
            feedback_usuario=request.feedback_usuario,
            service_id=request.service_id
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        print(f"[API ERROR] refine_extraction: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error refinando extracción")


@router.post("/extraction/guided_field")
async def extract_guided_field(
    request: GuidedFieldRequest,
    x_license_key: str = Header(...)
):
    """
    Extracción guiada de un campo específico desde un snippet.
    Usa estrategia fast->smart con fallback automático.
    """
    brain_service = AIBrainService()

    try:
        await brain_service._validate_license(x_license_key)

        result = await brain_service.extract_field_generic_guided(
            field_name=request.field_name,
            snippet_text=request.snippet_text,
            expected_format=request.expected_format
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        print(f"[API ERROR] guided_field: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error extrayendo campo")


# =============================================================================
# FACTORY ENDPOINTS (Script Generation & Audit)
# =============================================================================

@router.post("/factory/generate_script")
async def generate_extraction_script(
    request: GenerateExtractionScriptRequest,
    x_license_key: str = Header(...)
):
    """
    Fase 3: Genera script de extracción determinista.
    Recibe múltiples documentos para crear un script robusto.
    """
    brain_service = AIBrainService()

    try:
        await brain_service._validate_license(x_license_key)

        script = await brain_service.generate_extraction_script(
            docs_text_list=request.docs_text_list,
            campos_objetivo=request.campos_objetivo,
            values_example=request.values_example,
            info_discovery=request.info_discovery,
            feedback=request.feedback,
            field_definitions=request.field_definitions,
            license_key=x_license_key
        )

        return {"script": script}

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        print(f"[API ERROR] generate_extraction_script: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error generando script de extracción")


@router.post("/factory/refine_script")
async def refine_script(
    request: RefineScriptRequest,
    x_license_key: str = Header(...)
):
    """
    Refinamiento iterativo de script con logs de error.
    Usa reporte forense para corregir el script.
    """
    brain_service = AIBrainService()

    try:
        await brain_service._validate_license(x_license_key)

        script = await brain_service.refine_script_with_error_logs(
            script_actual=request.script_actual,
            reporte_forense=request.reporte_forense,
            feedback_history=request.feedback_history,
            texto_documento=request.texto_documento,
            target_fields=request.target_fields
        )

        return {"script": script}

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        print(f"[API ERROR] refine_script: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error refinando script")


@router.post("/factory/audit")
async def forensic_audit(
    request: ForensicAuditRequest,
    x_license_key: str = Header(...)
):
    """
    Genera reporte forense comparando resultado esperado vs obtenido.
    """
    brain_service = AIBrainService()

    try:
        await brain_service._validate_license(x_license_key)

        report = await brain_service.generate_forensic_audit(
            referencia_ia=request.referencia_ia,
            resultado_script=request.resultado_script
        )

        return {"report": report}

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        print(f"[API ERROR] forensic_audit: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error generando auditoría")


# =============================================================================
# RPA ENDPOINTS
# =============================================================================

@router.post("/factory/escalate")
async def escalate_script(
    request: ScriptEscalationRequest,
    x_license_key: str = Header(...)
):
    """
    Escala un script fallido al buzón del Partner para su revisión.
    """
    from sqlmodel import select
    from sqlmodel.ext.asyncio.session import AsyncSession
    from server.app.database.db import server_engine
    from server.app.database.models import ClientAccount, ScriptEscalation
    import hashlib

    brain_service = AIBrainService()

    try:
        await brain_service._validate_license(x_license_key)

        key_hash = hashlib.sha256(x_license_key.encode()).hexdigest()

        async with AsyncSession(server_engine) as session:
            result = await session.execute(
                select(ClientAccount).where(ClientAccount.license_key == key_hash)
            )
            client = result.scalar_one_or_none()
            
            if not client:
                raise ValueError("Licencia no corresponde a ningún cliente válido")

            # Crear la escalación asignada al partner del cliente
            new_escalation = ScriptEscalation(
                partner_id=client.partner_id,
                client_id=client.client_id,
                script_name=request.script_name,
                original_code=request.original_code,
                escalation_type=request.escalation_type,
                client_notes=request.client_notes,
                status="PENDING"
            )
            
            session.add(new_escalation)
            await session.commit()
            await session.refresh(new_escalation)
            
            return {"status": "success", "escalation_id": new_escalation.id}

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        print(f"[API ERROR] escalate_script: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error al escalar el script")


# =============================================================================
# RPA ENDPOINTS
# =============================================================================

@router.post("/rpa/analyze")
async def analyze_recording(
    request: AnalyzeRecordingRequest,
    x_license_key: str = Header(...)
):
    """
    Analiza logs de grabación para generar Playbook RPA.
    Convierte acciones del usuario en pasos ejecutables.
    """
    brain_service = AIBrainService()

    try:
        await brain_service._validate_license(x_license_key)

        playbook = await brain_service.analyze_recording(
            recording_logs=request.recording_logs,
            context=request.context_dict or {}
        )

        return {"playbook": playbook}

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        print(f"[API ERROR] analyze_recording: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error analizando grabación")


@router.post("/rpa/refine")
async def refine_playbook(
    request: RefinePlaybookRequest,
    x_license_key: str = Header(...)
):
    """
    Refina Playbook existente con feedback y logs de error.
    """
    brain_service = AIBrainService()

    try:
        await brain_service._validate_license(x_license_key)

        playbook = await brain_service.refine_playbook(
            current_playbook=request.current_playbook,
            recording_logs=request.recording_logs,
            error_logs=request.error_logs,
            user_feedback_history=request.user_feedback_history,
            context=request.context_data
        )

        return {"playbook": playbook}

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        print(f"[API ERROR] refine_playbook: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error refinando playbook")


@router.post("/rpa/visual_locate")
async def visual_locate_element(
    request: VisualLocateRequest,
    x_license_key: str = Header(...)
):
    """
    Localiza coordenadas de un elemento visual en una imagen.
    Usa visión por IA para encontrar elementos por descripción.

    Request:
        png_base64: Imagen codificada en base64
        description: Descripción del elemento a buscar
        viewport: {width, height} de la pantalla

    Returns:
        coordinates: [x, y] o null si no se encuentra
    """
    brain_service = AIBrainService()

    try:
        await brain_service._validate_license(x_license_key)

        # Decodificar imagen
        try:
            image_bytes = base64.b64decode(request.png_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="Imagen base64 inválida")

        coords = await brain_service.get_element_coordinates(
            image_bytes=image_bytes,
            element_description=request.description,
            viewport=request.viewport
        )

        return {"coordinates": list(coords) if coords else None}

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API ERROR] visual_locate: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error localizando elemento")


# =============================================================================
# COPILOT ENDPOINTS
# =============================================================================

@router.post("/copilot/ask")
async def ask_copilot(
    request: CopilotAskRequest,
    x_license_key: str = Header(...)
):
    """
    Copiloto RAG para consultas sobre átomos y flujos.

    Utiliza contexto local del cliente (README.md de átomos) más
    el conocimiento del servidor para dar respuestas precisas.

    Returns:
        - response: Respuesta del copiloto en markdown
        - suggestions: Lista de acciones sugeridas
        - has_bridge_suggestion: Si sugiere crear un puente de tipos
        - tokens_used: Tokens consumidos
    """
    brain_service = AIBrainService()

    try:
        await brain_service._validate_license(x_license_key)

        # Obtener prompt del copiloto
        from sqlmodel import select
        from sqlmodel.ext.asyncio.session import AsyncSession
        from server.app.database.db import server_engine
        from server.app.database.models import SystemPrompt

        system_prompt = ""
        async with AsyncSession(server_engine) as session:
            result = await session.execute(
                select(SystemPrompt).where(SystemPrompt.name == "copilot_helper")
            )
            prompt_obj = result.scalar_one_or_none()
            if prompt_obj:
                system_prompt = prompt_obj.content

        # Construir contexto del átomo
        atom_context = ""
        if request.atom_id:
            atom_context = f"Átomo seleccionado: {request.atom_id}"
        if request.flow_context:
            atom_context += f"\nContexto del flujo: {request.flow_context}"
        if request.local_context:
            atom_context += f"\n\nDocumentación local:\n{request.local_context}"

        # Reemplazar placeholders en el prompt
        system_prompt = system_prompt.replace("{mode}", request.mode or "idle")
        system_prompt = system_prompt.replace("{atom_context}", atom_context or "No hay contexto disponible")

        # Construir historial de conversación
        conversation = ""
        if request.conversation_history:
            for msg in request.conversation_history[-5:]:  # Últimos 5 mensajes
                role = msg.get("role", "user")
                content = msg.get("content", "")
                conversation += f"\n{role.upper()}: {content}"

        # Construir prompt completo
        full_prompt = f"{system_prompt}\n\nHISTORIAL:{conversation}\n\nUSUARIO: {request.query}"

        # Resolver config - usar Tier 1 para velocidad (ayuda contextual rápida)
        config, _ = await brain_service._resolve_server_config(role_key="extraccion_pdf")

        # Ejecutar
        result = await ejecutar_tarea(
            prompt=full_prompt,
            config_rol=config,
            script_origen="copilot_ask"
        )

        response_text = result.get("response", "")

        # Detectar si sugiere crear un puente
        has_bridge = any(
            keyword in response_text.lower()
            for keyword in ["puente", "bridge", "conversión de tipo", "type conversion"]
        )

        # Extraer sugerencias (líneas que empiezan con - o *)
        suggestions = []
        for line in response_text.split("\n"):
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                suggestions.append(line[2:])

        return {
            "response": response_text,
            "suggestions": suggestions[:5],  # Máximo 5 sugerencias
            "has_bridge_suggestion": has_bridge,
            "tokens_used": result.get("tokens_used", 0)
        }

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        print(f"[API ERROR] copilot_ask: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error en copiloto")


@router.post("/copilot/generate_bridge")
async def generate_bridge_code(
    request: GenerateBridgeRequest,
    x_license_key: str = Header(...)
):
    """
    Genera código puente para conversión entre tipos incompatibles.

    Usado cuando se conectan nodos con tipos diferentes (ej: STR → INT).

    Returns:
        - code: Código Python del script puente
        - tokens_used: Tokens consumidos
    """
    brain_service = AIBrainService()

    try:
        await brain_service._validate_license(x_license_key)

        # Prompt específico para generación de puentes
        bridge_prompt = f"""Genera un script Python mínimo para convertir datos de tipo {request.source_type} a {request.target_type}.

CONTEXTO:
- Campo origen: {request.source_name} (tipo: {request.source_type})
- Campo destino: {request.target_name} (tipo: {request.target_type})
{f"- Valor de ejemplo: {request.example_value}" if request.example_value else ""}

REQUISITOS:
1. El script debe tener una función `transform(value)` que reciba el valor y retorne el convertido
2. Debe manejar errores gracefully (retornar None o valor por defecto si falla)
3. Código limpio, sin imports innecesarios
4. Incluir docstring breve

FORMATO DE RESPUESTA:
Responde SOLO con el código Python, sin explicaciones ni markdown.
"""

        # Usar Tier 3 para mejor calidad de código
        config, _ = await brain_service._resolve_server_config(role_key="supervision")

        result = await ejecutar_tarea(
            prompt=bridge_prompt,
            config=config,
            script_origen="bridge_generator"
        )

        code = result.get("response", "")

        # Limpiar posibles bloques de código markdown
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        return {
            "code": code,
            "tokens_used": result.get("tokens_used", 0)
        }

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        print(f"[API ERROR] generate_bridge: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error generando puente")


# =============================================================================
# AGENT ENDPOINTS
# =============================================================================

@router.post("/agent/step")
async def agent_step(
    request: AgentStepRequest,
    x_license_key: str = Header(...)
):
    """
    Ejecuta un paso del agente autónomo.

    El cliente envía el estado actual de la página y el historial de acciones,
    y el servidor responde con la siguiente acción a ejecutar.

    Este endpoint permite ejecutar agentes en modo split (cliente-servidor)
    donde el navegador está en el cliente pero la inteligencia está en el servidor.

    Returns:
        - action: str (click, fill, navigate, wait, visual_click, done, error)
        - selector: str (CSS selector o descripción del elemento)
        - value: str (valor para fill o URL para navigate)
        - reasoning: str (explicación del agente)
        - is_complete: bool (si la tarea está completa)
    """
    brain_service = AIBrainService()

    try:
        await brain_service._validate_license(x_license_key)

        # Build agent prompt
        history_summary = ""
        if request.action_history:
            history_summary = "\\n".join([
                f"Step {h.get('step', '?')}: {h.get('action', '?')} -> {h.get('result', {}).get('success', '?')}"
                for h in request.action_history[-5:]  # Last 5 actions
            ])

        page_info = f"""
URL: {request.page_state.get('url', 'unknown')}
Title: {request.page_state.get('title', 'unknown')}
"""

        agent_prompt = f"""Eres un agente de automatización web. Tu tarea es:
{request.task_instruction}

ESTADO ACTUAL DE LA PÁGINA:
{page_info}

HISTORIAL DE ACCIONES RECIENTES:
{history_summary if history_summary else "Ninguna acción previa"}

Analiza la situación y decide la siguiente acción. Responde en JSON con este formato exacto:
{{
    "action": "click|fill|navigate|wait|visual_click|done|error",
    "selector": "CSS selector o descripción del elemento",
    "value": "valor para fill o URL para navigate (vacío si no aplica)",
    "reasoning": "Explicación breve de por qué tomas esta acción",
    "is_complete": true|false
}}

REGLAS:
- Si la tarea está completa, usa action="done" y is_complete=true
- Si hay un error irrecuperable, usa action="error"
- Para clicks, usa selectores CSS específicos
- Si el selector CSS falla, usa visual_click con una descripción del elemento
- Mantén las acciones simples y una a la vez

Responde SOLO con el JSON, sin explicaciones adicionales."""

        # Use Tier 3 (supervision) for agent reasoning
        config, _ = await brain_service._resolve_server_config(role_key="supervision")

        result = await ejecutar_tarea(
            prompt=agent_prompt,
            config=config,
            script_origen="agent_step"
        )

        response_text = result.get("response", "")

        # Parse JSON response
        import json as json_module
        try:
            # Clean response if wrapped in code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            parsed = json_module.loads(response_text)

            return {
                "action": parsed.get("action", "error"),
                "selector": parsed.get("selector", ""),
                "value": parsed.get("value", ""),
                "reasoning": parsed.get("reasoning", ""),
                "is_complete": parsed.get("is_complete", False)
            }

        except json_module.JSONDecodeError:
            # If parsing fails, return error action
            return {
                "action": "error",
                "selector": "",
                "value": "",
                "reasoning": f"Failed to parse agent response: {response_text[:200]}",
                "is_complete": True
            }

    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        print(f"[API ERROR] agent_step: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Error en paso de agente")

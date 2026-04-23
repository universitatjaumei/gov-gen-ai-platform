"""
AIBrainService - Fachada segura para operaciones de IA en el servidor.

Este servicio es el punto de entrada principal para todas las operaciones de IA 
en AutomatIA. Se encarga de:
1. Resolución de configuraciones (prompts y modelos) desde la base de datos.
2. Delegación a estrategias específicas (Cortex, Extracción).
3. Control de acceso y sanitización de datos.
4. Validación de licencias y seguimiento de consumo de tokens.
"""
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Union, Optional, Tuple
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from server.app.modules.automation.infrastructure.llm_gateway import ejecutar_tarea

# Server-Side Imports
from server.app.database.db import server_engine
from server.app.database.models import AIConfig, ExtractionServiceConfig, License, ClientAccount, LicenseActivation
from automatia_shared.enums import LicenseStatus
from server.app.modules.automation.cortex import analyze_recording_with_ai, refine_playbook_with_ai, locate_visual_element
from server.app.modules.automation.extraction_strategies import (
    analyze_document_structure,
    extraer_datos_precision,
    generar_script_determinista,
    supervisar_codigo,
    regenerar_script_iterativo,
    generar_reporte_forense,
    refinar_extraccion_con_feedback,
    filtrar_datos_irrelevantes,
    extraer_dato_desde_snippet,
    extract_field_from_snippet
)

# Mapeo de Tier numérico a role_key de AIConfig
TIER_TO_ROLE = {
    1: "extraccion_pdf",      # Tier 1: Flash (rápido, económico)
    2: "logico_navegacion",   # Tier 2: Lógica (balanceado)
    3: "supervision"          # Tier 3: Supervisión (potente, costoso)
}

class AIBrainService:
    """
    Fachada segura del servidor para operaciones de Inteligencia Artificial.

    Responsabilidades:
    1. Autenticar y autorizar solicitudes (Validación de licencias).
    2. Resolver configuraciones (Prompts/Modelos) desde la BD del servidor.
       - El cliente nunca envía prompts o configuraciones de modelo.
    3. Delegar tareas a Cortex (Lógica/RPA) o Extraction (Documentos).
    4. Controlar el flujo de datos y sanitizar respuestas.
    """

    # --- INTERNAL SERVER HELPERS ---

    async def _resolve_server_config(self, service_id: str = None, role_key: str = None) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Resuelve internamente la configuración (Prompt + Modelo) adecuada.
        
        Prioridad de resolución:
        1. tier_override (si está definido) -> se mapea a un rol vía TIER_TO_ROLE.
        2. suggested_model (si está definido) -> se usa un modelo específico.
        3. role_key -> se usa el modelo por defecto para dicho rol.

        Args:
           service_id: ID para servicios de extracción (ej: 'facturas_v1').
           role_key: Clave para roles genéricos (ej: 'logico_navegacion').

        Returns:
            Tuple[Dict, str]: (Diccionario de configuración del modelo, Prompt de sistema).
        """
        async with AsyncSession(server_engine) as session:

            # 1. Fetch System Prompts & Specific Configs (if service_id)
            system_prompt = None
            suggested_model_id = None
            tier_override = None

            if service_id:
                stmt = select(ExtractionServiceConfig).where(ExtractionServiceConfig.service_id == service_id)
                res = await session.exec(stmt)
                svc_config = res.first()
                if svc_config:
                    system_prompt = svc_config.system_prompt_template
                    suggested_model_id = svc_config.suggested_model
                    tier_override = svc_config.tier_override

            # 2. Determine target role with priority resolution
            target_role = role_key

            # PRIORITY 1: tier_override forces specific tier
            if tier_override and tier_override in TIER_TO_ROLE:
                target_role = TIER_TO_ROLE[tier_override]

            if not target_role:
                # Infer capability from service_id or use default
                target_role = "logico_navegacion" # Default fallback

            # 3. Fetch AI Role Configuration (Model/Provider)
            stmt_role = select(AIConfig).where(AIConfig.role_key == target_role)
            res_role = await session.exec(stmt_role)
            role_config = res_role.first()

            final_config = {}
            if role_config:
                # PRIORITY 2: suggested_model overrides role model (only if no tier_override)
                if suggested_model_id and not tier_override:
                    model_id = suggested_model_id
                else:
                    model_id = role_config.model_id

                final_config = {
                    "provider": role_config.provider,
                    "model_id": model_id
                }
                print(f"[AIBrain] Role '{target_role}' loaded from DB: provider={role_config.provider}, model={model_id}")
            else:
                 # Fallback hardcoded for safety during bootstrap
                 print(f"[AIBrain] WARNING: Role '{target_role}' NOT FOUND in DB. Using hardcoded fallback (google).")
                 final_config = {"provider": "google", "model_id": "gemini-2.0-flash-exp"}

            return final_config, system_prompt


    # --- CONFIGURATION MANAGEMENT (SERVER API) ---
    # These methods allow the Client (Admin UI) to manage Server Configs via the Brain API.

    async def get_system_prompts(self) -> List[Dict]:
        """
        Obtiene la lista de prompts de sistema disponibles en el servidor.
        
        Filtra aquellos configurados como plantillas genéricas (ID 'sys_' o nombre 'System:').

        Returns:
            List[Dict]: Lista de diccionarios con la configuración de cada prompt.
        """
        async with AsyncSession(server_engine) as session:
            statement = select(ExtractionServiceConfig)
            results = await session.exec(statement)
            configs = results.all()
            return [
                {
                    "service_id": c.service_id,
                    "name": c.name,
                    "description": c.description,
                    "system_prompt_template": c.system_prompt_template
                } for c in configs
                if str(c.service_id).startswith('sys_') or str(c.name).startswith('System:')
            ]

    async def get_service_config(self, service_id: str) -> Optional[ExtractionServiceConfig]:
        """
        Obtiene la configuración completa de un servicio de extracción por su ID.
        """
        async with AsyncSession(server_engine) as session:
            return await session.get(ExtractionServiceConfig, service_id)

    async def save_service_config(self, config: ExtractionServiceConfig):
        """
        Guarda o actualiza la configuración de un servicio de extracción en la BD.
        """
        async with AsyncSession(server_engine) as session:
            session.add(config)
            await session.commit()



    # --- PUBLIC API (SECURE) ---

    async def analyze_recording(self, recording_logs: List[Dict], context: Dict[str, Any]) -> List[Dict]:
        """
        Analiza logs de navegación para generar un playbook automatizado.
        
        Resuelve automáticamente el prompt de análisis de RPA y delega la lógica 
        a Cortex para transformar acciones crudas en pasos estructurados.

        Args:
            recording_logs: Lista de acciones grabadas por el cliente.
            context: Variables de negocio disponibles para la generalización.

        Returns:
            List[Dict]: Lista de pasos del playbook generado.
        """
        print("[AIBrainService] Secure Request: Analyze Recording")

        # Internal configuration lookup
        # Updated to use specific RPA Analysis Prompt from DB
        config, system_prompt = await self._resolve_server_config(service_id="sys_rpa_analysis", role_key="logico_navegacion")

        if not system_prompt:
             # Fallback logic might be needed if init wasn't run, but we should enforce DB consistecy.
             print("[AIBrainService] Warning: sys_rpa_analysis prompt not found. RPA might fail.")

        # Call Cortex
        return await analyze_recording_with_ai(
            self._sanitize(recording_logs),
            self._sanitize(context),
            config,
            system_prompt_override=system_prompt # Pass prompt to cortex
        )

    async def refine_playbook(
        self,
        current_playbook: List[Dict],
        recording_logs: List[Dict],
        error_logs: str,
        user_feedback_history: List[str],
        context: Dict[str, Any]
    ) -> List[Dict]:
        """
        Solicita el refinamiento de un playbook RPA basado en errores detectados o feedback del usuario.
        """
        print("[AIBrainService] Secure Request: Refine Playbook")

        # Internal configuration lookup (Uses Supervision Tier)
        # Updated to use RPA Refinement Prompt from DB
        config, system_prompt = await self._resolve_server_config(service_id="sys_rpa_refinement", role_key="supervision")

        clean_history = [str(f) for f in user_feedback_history]

        return await refine_playbook_with_ai(
            self._sanitize(current_playbook),
            self._sanitize(recording_logs),
            str(error_logs),
            clean_history,
            self._sanitize(context),
            config,
            system_prompt_override=system_prompt # Pass prompt to cortex
        )

    async def get_element_coordinates(self, image_bytes: bytes, element_description: str, viewport: Dict[str, int]) -> Optional[Tuple[int, int]]:
        """
        Solicita coordenadas de un elemento visual.
        """
        print("[AIBrainService] Secure Request: Vision Coordinates")

        # 1. Config Lookup
        config, system_prompt = await self._resolve_server_config(service_id="sys_rpa_vision", role_key="logico_navegacion") # Default fallback role

        if not system_prompt:
             print("[AIBrainService] Warning: sys_rpa_vision prompt not found.")

        return await locate_visual_element(
            image_bytes,
            element_description,
            viewport,
            config,
            system_prompt=system_prompt
        )

    # --- DOCUMENT EXTRACTION METHODS (SECURE) ---

    async def analyze_document_structure(self, texto_a: str, texto_b: str, definicion_usuario: str, service_id: str = "sys_phase0_discovery") -> Dict[str, Any]:
        """
        Fase 0: Descubrimiento de estructura documental con escalado automático.
        
        Intenta primero una extracción rápida (Tier 1) y, si el formato no es 
        válido, escala a un modelo más inteligente (Tier 2/3).

        Args:
            texto_a: Texto extraído mediante motor lineal.
            texto_b: Texto extraído respetando el layout visual.
            definicion_usuario: (Legacy) Definición de campos.
            service_id: ID del servicio de descubrimiento a utilizar.

        Returns:
            Dict[str, Any]: Estructura detectada con campos y niveles de confianza.
        """
        print(f"[AIBrainService] Secure Request: Discovery (Service: {service_id})")

        # 1. Try Fast (Default)
        # Note: 'definicion_usuario' is unused in new strategy but kept for interface compat
        config_fast, sys_fast = await self._resolve_server_config(service_id=service_id, role_key="phase0_discovery_fast")

        # Call Strategy (Fast)
        resp = await analyze_document_structure(texto_a, texto_b, "es", config_fast, sys_fast)

        # 2. Check & Fallback
        if not resp.get("format_ok"):
             print(f"[AIBrain] Discovery Fast failed (Format Invalid). Escalating to Smartest.")

             # Resolve Smart
             config_smart, sys_smart = await self._resolve_server_config(service_id=service_id, role_key="phase0_discovery_smart")

             # Call Strategy (Smart)
             resp = await analyze_document_structure(texto_a, texto_b, "es", config_smart, sys_smart)

        return resp

    async def extract_data(self, file_path: str, user_definition: str, target_fields: List[str] = [], usar_tier_2: bool = False, ejemplos_validacion: Optional[Dict] = None, texto_fitz: Optional[str] = None, texto_plumber: Optional[str] = None) -> Dict[str, Any]:
        """
        Orquesta la extracción de datos de precisión para un documento.
        
        Resuelve la configuración dinámica según el Tier solicitado (1 o 2).
        Soporta la inyección de texto pre-procesado o la lectura directa del PDF.

        Args:
            file_path: Ruta al archivo (si no se provee texto).
            user_definition: Instrucciones adicionales del usuario.
            target_fields: Lista de nombres de campos a extraer.
            usar_tier_2: Si es True, utiliza modelos de razonamiento superior.
            ejemplos_validacion: Datos de ejemplo para guiar el formato.
            texto_fitz: Texto ya extraído vía fitz (opcional).
            texto_plumber: Texto ya extraído vía pdfplumber (opcional).

        Returns:
            Dict[str, Any]: Datos extraídos en formato clave-valor.
        """
        from server.app.modules.automation.extraction_strategies import extraer_datos_precision
        from automatia_shared.core.reader import extraer_texto_dual

        # 1. Resolver Config + Prompt (Dynamic)
        # Recuperamos la configuracion correcta segun el nivel (Tier 1 vs Tier 2)
        role = "logico_navegacion" if usar_tier_2 else "extraccion_pdf"
        config, system_prompt = await self._resolve_server_config(
            service_id="sys_phase1_extraction",
            role_key=role
        )

        if not system_prompt:
             raise RuntimeError("No se encontro el prompt de sistema sys_phase1_extraction")

        # 2. Leer archivo (Dual) SI NO se provee texto
        if not texto_fitz or not texto_plumber:
            texto_fitz, texto_plumber, _ = extraer_texto_dual(file_path)

        # 3. Ejecutar Estrategia
        return await extraer_datos_precision(
            texto_fitz,
            texto_plumber,
            target_fields,
            user_definition,
            config,
            system_prompt,
            usar_tier_2=usar_tier_2,
            ejemplos_validacion=ejemplos_validacion
        )

    async def refine_extraction_data(self, texto_fitz: str, texto_plumber: str, datos_anteriores: Dict[str, Any], feedback_usuario: str, service_id: str = "sys_phase1_refinement") -> Dict[str, Any]:
        """
        Fase 1.5: Refinamiento de datos de extracción basado en feedback.
        
        Permite corregir extracciones fallidas proporcionando el contexto previo 
        y las instrucciones del usuario (ej: "El IBAN está en el pie de página").

        Args:
            texto_fitz: Texto extraído vía fitz.
            texto_plumber: Texto extraído vía pdfplumber.
            datos_anteriores: El JSON que se desea refinar.
            feedback_usuario: Instrucciones naturales de corrección.
            service_id: ID del servicio de refinamiento.

        Returns:
            Dict[str, Any]: Nuevo conjunto de datos refinado.
        """
        print(f"[AIBrainService] Secure Request: Refinement (Service: {service_id})")

        # Refinement usually needs higher intelligence
        config, system_prompt = await self._resolve_server_config(service_id=service_id, role_key="logico_navegacion")

        if not system_prompt:
             return {"error": f"System Prompt not found for {service_id}"}

        return await refinar_extraccion_con_feedback(
            texto_fitz,
            texto_plumber,
            self._sanitize(datos_anteriores),
            feedback_usuario,
            config,
            system_prompt
        )

    async def generate_extraction_script(self, docs_text_list: List[Dict[str, str]], campos_objetivo: List[str], values_example: Optional[Dict] = None, info_discovery: Optional[Dict] = None, feedback: str = None, tabla_auditoria: str = None, field_definitions: Optional[List[Dict]] = None, license_key: Optional[str] = None) -> str:
        """
        Fase 3: Generación de scripts de extracción deterministas (Factory).
        
        Utiliza el nivel más alto de inteligencia (Tier 3) para escribir código 
        Python capaz de extraer datos de forma repetible sin usar LLM en cada ejecución.
        Realiza una validación de licencia previa antes de proceder.

        Args:
            docs_text_list: Lista de diccionarios con texto de varios documentos.
            campos_objetivo: Lista de campos que el script debe extraer.
            values_example: Valores extraídos previamente para guiar la lógica.
            info_discovery: Información de la estructura detectada en Fase 0.
            feedback: Instrucciones de ajuste del usuario.
            tabla_auditoria: Errores detectados en versiones previas del script.
            field_definitions: Metadatos estrictos de tipos de campos.
            license_key: Clave del cliente para validación de créditos.

        Returns:
            str: Código Python autogenerado y listo para ejecución local.
        """
        print(f"[AIBrainService] Secure Request: Generate Script ({len(docs_text_list)} docs)")

        # 0. Pre-flight Billing Validation
        if license_key:
             from server.app.modules.automation.billing_engine import BillingEngine, PartnerCreditError, LicenseError
             billing = BillingEngine()
             try:
                 # Hash the key as the server expects hashed IDs for internal lookup from hashed keys
                 # assuming billing.validate_access takes license_id (which is often the key or mapped to it)
                 # In this architecture, license_id is the PK. We need to find license_id from hashed license_key.
                 license_id = await self._get_license_id_from_key(license_key)
                 if license_id:
                     await billing.validate_access(license_id)
                 else:
                     raise ValueError("Invalid license key")
             except (PartnerCreditError, LicenseError) as e:
                 # Re-raise to be caught by caller or UI
                 raise 

        # 1. Resolve Config & Prompt for Factory Gen
        # Using Tier 2 (logico_navegacion) for initial generation, Tier 3 reserved for refinement
        config, system_prompt = await self._resolve_server_config(service_id="sys_phase3_factory_gen", role_key="logico_navegacion")

        if not system_prompt:
             raise RuntimeError("No se encontro el prompt sys_phase3_factory_gen")

        return await generar_script_determinista(
            docs_text_list, campos_objetivo, config, system_prompt,
            self._sanitize(values_example), self._sanitize(info_discovery),
            feedback, tabla_auditoria,
            field_definitions=self._sanitize(field_definitions)
        )

    async def clean_data_noise(self, raw_data: Dict[str, Any], user_definition: str, service_id: str = "sys_utility_noise_filter") -> Dict[str, Any]:
        """
        Filtro de Ruido (Utility).
        Uses Tier 2 (Logic) to semantically filter noise.
        """
        print(f"[AIBrainService] Secure Request: clean_data_noise (Tier 2, Service: {service_id})")

        # 1. FORZAR USO DE TIER 2 (Logico/Navegacion)
        # Fetch config AND system_prompt (Required by strategy)
        config, system_prompt = await self._resolve_server_config(service_id=service_id, role_key="logico_navegacion")

        if not system_prompt:
             return {"error": f"System Prompt not found for {service_id}"}

        # Configurar correctamente el objeto config si es una lista/dict plano
        # filtrar_datos_irrelevantes espera un dict, y si dentro tiene 'logico_navegacion', lo usa.
        # _resolve_server_config devuelve ya el dict final del rol, por lo que podemos pasarlo envuelto
        # o adaptar la estrategia.

        # Estrategia espera: config['logico_navegacion'] o config plano.
        # Pasemos un wrapper para estar seguros.
        config_wrapper = {"logico_navegacion": config}

        return await filtrar_datos_irrelevantes(
            self._sanitize(raw_data),
            user_definition,
            config_wrapper,
            system_prompt
        )

    async def audit_script(self, script_codigo: str, campos_objetivo: List[str]) -> Dict[str, Any]:
        """Auditoria de codigo (Local Logic)."""
        # This is static analysis, no LLM config needed really, but kept for signature consistency
        return supervisar_codigo(script_codigo, campos_objetivo, {})

    async def refine_script_with_error_logs(self, script_actual: str, reporte_forense: str, feedback_history: List[Dict], texto_documento: str, target_fields: List[str] = []) -> str:
        """Refinamiento iterativo de script."""
        print(f"[AIBrainService] Secure Request: Refine Script (Targets: {len(target_fields)})")

        # Uses tier 3 (Supervision) + Refinement Prompt
        config, system_prompt = await self._resolve_server_config(service_id="sys_phase3_refinement", role_key="supervision")

        if not system_prompt:
             # Fallback? No, logic depends on prompts now.
             raise RuntimeError("No se encontro el prompt sys_phase3_refinement")

        return await regenerar_script_iterativo(
            script_actual, reporte_forense, self._sanitize(feedback_history),
            texto_documento, config, system_prompt,
            campos_objetivo=target_fields
        )

    async def generate_forensic_audit(self, referencia_ia: Dict, resultado_script: Any) -> str:
        """Generacion de reporte forense (Audit)."""
        print(f"[AIBrainService] Secure Request: Forensic Audit (Result type: {type(resultado_script)})")

        config, system_prompt = await self._resolve_server_config(service_id="sys_phase3_audit_forensic", role_key="supervision")

        if not system_prompt:
             raise RuntimeError("No se encontro el prompt sys_phase3_audit_forensic")

        return await generar_reporte_forense(
            self._sanitize(referencia_ia), self._sanitize(resultado_script), config, system_prompt
        )

    def _sanitize(self, data: Any) -> Any:
        """
        Sanitiza estructuras de datos de forma recursiva.
        
        Asegura que todos los objetos sean serializables a JSON, convirtiendo 
        modelos de SQLModel/Pydantic a diccionarios estándar.

        Args:
            data: El objeto o estructura a limpiar.

        Returns:
            Any: Versión sanitizada de la entrada.
        """
        if isinstance(data, dict):
            return {k: self._sanitize(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize(v) for v in data]
        elif hasattr(data, "model_dump"): # Pydantic v2
            return self._sanitize(data.model_dump())
        elif hasattr(data, "dict"): # Pydantic v1
            return self._sanitize(data.dict())
        elif hasattr(data, "__dict__"): # Generic Objects
            return self._sanitize(data.__dict__)
        else:
            return data

    async def generate_script_anchor_based(self, doc1_texts: Dict[str, str], doc2_texts: Dict[str, str], field_definitions: List[Dict], feedback: str = "") -> str:
        """
        Generates an extraction script using the 'Anchor-Based' strategy.
        Focuses on finding patterns in Doc1 that are likely to persist in Doc2 (and others).

        Args:
            doc1_texts: {fitz, plumber} for the first document (primary reference).
            doc2_texts: {fitz, plumber} for the second document (validation reference).
            field_definitions: List of {name, description, example_value, is_optional}.
        """
        print("[AIBrainService] Secure Request: Generate Anchor-Based Script")

        # 1. Resolve Config
        # Using Tier 2 (logico_navegacion) for initial generation, Tier 3 reserved for refinement
        config, system_prompt = await self._resolve_server_config(service_id="sys_phase3_factory_gen", role_key="logico_navegacion")

        if not system_prompt:
             # Fallback just in case
             config, system_prompt = await self._resolve_server_config(service_id="sys_pdf_extraction", role_key="logico_navegacion")

        # 2. Prepare Multi-Doc Context
        # Doc 1 is the primary source, Doc 2 is context for "generalizability".
        docs_list = [
            {"filename": "Documento_Referencia_1.pdf", "fitz": doc1_texts.get('fitz',''), "plumber": doc1_texts.get('plumber','')},
            {"filename": "Documento_Validacion_2.pdf", "fitz": doc2_texts.get('fitz',''), "plumber": doc2_texts.get('plumber','')},
        ]

        # 3. Call Strategy
        script = await generar_script_determinista(
            docs_text_list=docs_list,
            campos_objetivo=[f['name'] for f in field_definitions],
            config=config,
            system_prompt=system_prompt,
            valores_ejemplo={f['name']: f['example_value'] for f in field_definitions},
            field_definitions=field_definitions, # TRIGGERS ANCHOR MODE
            feedback_usuario=feedback
        )

        return script

    async def analyze_snippet(self, field_name: str, snippet_text: str, expected_format: str = "") -> dict:
        """
        Extrae un único campo de un fragmento de texto (snippet) usando IA.
        Implementa una estrategia de escalado: primero intenta con un modelo rápido (Tier 1)
        y si falla o el formato no es válido, escala a uno más capaz (Tier 2).

        Args:
            field_name: Nombre del campo a buscar.
            snippet_text: Texto donde buscar la información.
            expected_format: Formato esperado del valor.

        Returns:
            dict: Diccionario con valor, página, confianza, fuente y validez de formato.
        """
        print(f"[AIBrainService] Secure Request: Analyze Snippet for '{field_name}'")

        # 1. Tier 1
        config, system_prompt = await self._resolve_server_config(service_id="sys_fallback_snippet", role_key="extraccion_pdf")
        if not system_prompt:
             config, system_prompt = await self._resolve_server_config(service_id="sys_pdf_extraction", role_key="extraccion_pdf")

        if system_prompt:
            result = await extraer_dato_desde_snippet(field_name, snippet_text, expected_format, config, system_prompt)
            # Result expected: {valor, confidence, format_ok, pagina}

            # Legacy/Fallback parsing if AI didn't follow JSON perfectly
            val = result.get('valor') or result.get(field_name)
            is_ok = result.get('format_ok', False)
            if isinstance(is_ok, str): is_ok = is_ok.lower() == 'true'

            if val and str(val).strip() and is_ok:
                return {
                    "valor": val,
                    "pagina": result.get('pagina'),
                    "confidence": float(result.get('confidence', 0.8)), # Default high if it thinks it's ok
                    "source": "llm",
                    "format_ok": True
                }
            else:
                print(f"[AIBrainService] Tier 1 failed/invalid for '{field_name}'. Escalating.")

        # 2. Tier 2
        config_t2, system_prompt_t2 = await self._resolve_server_config(service_id="sys_fallback_snippet", role_key="logico_navegacion")
        if not system_prompt_t2:
             print("[AIBrainService] Tier 2 Prompt missing.")
             return {}

        result_t2 = await extraer_dato_desde_snippet(field_name, snippet_text, expected_format, config_t2, system_prompt_t2)

        val_t2 = result_t2.get('valor') or result_t2.get(field_name)
        return {
            "valor": val_t2,
            "pagina": result_t2.get('pagina'),
            "confidence": float(result_t2.get('confidence', 0.9)),
            "source": "llm",
            "format_ok": result_t2.get('format_ok', True)
        }

    async def extract_field_generic_guided(self, field_name: str, snippet_text: str, expected_format: str = 'text') -> Dict[str, Any]:
        """
        Usa un prompt corto y robusto para extraer SOLO el campo indicado desde el snippet KV.
        Devuelve: {"valor":"...", "pagina": <int|None>, "confidence": 0.0..1.0, "format_ok": true|false}
        """
        role_fast = "field_extract_fast"
        role_smart = "field_extract_smart"

        class ExecutorAdapter:
            def __init__(self, brain): self.brain = brain
            async def run(self, role, system, user):
                db_role = "logico_navegacion" if "smart" in role else "extraccion_pdf"
                config, _ = await self.brain._resolve_server_config(role_key=db_role)
                res = await ejecutar_tarea(system + "\n" + user, config, script_origen="field_recovery")
                return res.get("response", "")

        executor = ExecutorAdapter(self)

        resp = await extract_field_from_snippet(
            field_name=field_name,
            snippet_text=snippet_text,
            expected_format=expected_format,
            role=role_fast,
            executor=executor
        )
        if not (resp and resp.get("format_ok")):
            resp2 = await extract_field_from_snippet(
                field_name=field_name, snippet_text=snippet_text,
                expected_format=expected_format, role=role_smart, executor=executor
            )
            if resp2:
                resp = resp2

        return resp or {"valor": "", "pagina": None, "confidence": 0.0, "format_ok": False}

    # --- LICENSE VALIDATION AND TOKEN MANAGEMENT ---

    async def _get_license_id_from_key(self, license_key: str) -> Optional[str]:
        """
        Obtiene el UUID de la licencia a partir de su clave pública.

        Args:
            license_key: Clave de licencia en texto plano.

        Returns:
            Optional[str]: ID interno de la licencia o None si no se encuentra.
        """
        key_hash = hashlib.sha256(license_key.encode()).hexdigest()
        async with AsyncSession(server_engine) as session:
            result = await session.execute(
                select(License.license_id).join(ClientAccount).where(ClientAccount.license_key == key_hash)
            )
            return result.scalar_one_or_none()

    async def _validate_license(self, license_key: str) -> License:
        """
        Valida licencia y retorna objeto License si es válida.

        Args:
            license_key: Clave de licencia en texto plano

        Returns:
            License: Objeto de licencia válido

        Raises:
            ValueError: Si licencia es inválida, expirada o excedida
        """
        # 1. Hash de la clave
        key_hash = hashlib.sha256(license_key.encode()).hexdigest()

        async with AsyncSession(server_engine) as session:
            # 2. Buscar cliente por license_key
            result = await session.execute(
                select(ClientAccount).where(ClientAccount.license_key == key_hash)
            )
            client = result.scalar_one_or_none()

            if not client:
                raise ValueError("Licencia no encontrada")

            if not client.is_active:
                raise ValueError("Cuenta de cliente suspendida")

            # 3. Buscar licencia
            result = await session.execute(
                select(License).where(License.client_id == client.client_id)
            )
            license = result.scalar_one_or_none()

            if not license:
                raise ValueError("Licencia no configurada para este cliente")

            # 4. Validar estado (usa método is_valid() de License)
            if not license.is_valid():
                # Determinar causa específica
                if license.status != LicenseStatus.ACTIVE.value:
                    raise ValueError(f"Licencia en estado: {license.status}")
                elif license.consumed_tokens >= license.quota_tokens:
                    raise ValueError("Cuota de tokens excedida")
                elif datetime.utcnow() > license.valid_until:
                    raise ValueError("Licencia expirada")

            return license

    async def generate_text(
        self,
        prompt: str,
        license_key: str,
        model: str = None,
        temperature: float = 0.7,
        service_id: str = None,
        config_summary: Dict[str, Any] = None
    ) -> str:
        """
        Genera texto validando licencia primero.
        """
        # 1. VALIDAR LICENCIA (crítico)
        license = await self._validate_license(license_key)

        # 2. GENERAR TEXTO
        # response = await self._call_llm(prompt, model, temperature)
        response = await self.call_llm(
            prompt=prompt,
            license_key=license_key,
            model=model,
            temperature=temperature,
            service_id=service_id,
            config_summary=config_summary
        )

        return response

    async def call_llm(
        self,
        prompt: str,
        role_key: str = "logico_navegacion",
        service_id: str = None,
        config_summary: Dict[str, Any] = None,
        license_key: str = None,
        model: str = None,
        temperature: float = 0.7
    ) -> str:
        """
        Llama al LLM (Tiered) con soporte para templates de prompt.
        """
        # Resolver configuración
        config, system_prompt = await self._resolve_server_config(
            service_id=service_id, 
            role_key=role_key
        )
        
        # Si hay template y contexto, formatear
        if system_prompt and config_summary:
            try:
                system_prompt = system_prompt.format(**config_summary)
            except Exception as e:
                print(f"[AIBrain] Error formatting prompt: {e}")
        
        # El modelo puede ser sobreescrito por la request
        if model:
            config["model_id"] = model

        # Llamar al LLM gateway
        result = await ejecutar_tarea(
            f"{system_prompt}\n\n{prompt}" if system_prompt else prompt,
            config,
            script_origen="call_llm"
        )
        
        # Registrar consumo si hay licencia
        if license_key:
            try:
                license_obj = await self._validate_license(license_key)
                await self._update_token_consumption(
                    license_id=license_obj.license_id,
                    tokens=result.get("tokens_used", 0)
                )
            except Exception as e:
                print(f"[AIBrain] Error recording consumption: {e}")

        return result.get("response", "")

    async def _call_llm(self, prompt: str, model: str = None, temperature: float = 0.7) -> str:
        """
        Llama al LLM para generar texto (Legacy helper).
        """
        return await self.call_llm(prompt=prompt, model=model, temperature=temperature)

    async def _update_token_consumption(self, license_id: str, tokens: int):
        """
        Actualiza consumo de tokens en la licencia.
        Usa BillingEngine para centralizar la lógica de facturación.

        Args:
            license_id: ID de la licencia
            tokens: Cantidad de tokens consumidos
        """
        # Lazy import to avoid circular dependencies if any, though here it should be fine
        from server.app.modules.automation.billing_engine import BillingEngine
        billing_engine = BillingEngine()
        await billing_engine.record_consumption(
             license_id=license_id,
             tokens_used=tokens,
             operation="text_generation"
        )

    def _count_tokens(self, prompt: str, response: str) -> int:
        """
        Estima cantidad de tokens (simplificado).

        Regla aproximada: 1 token ≈ 4 caracteres
        En producción usar tiktoken o API del provider.

        Args:
            prompt: Texto de entrada
            response: Texto de salida

        Returns:
            int: Estimación de tokens
        """
        total_chars = len(prompt) + len(response)
        estimated_tokens = total_chars // 4
        return estimated_tokens

    # --- DEVICE ACCESS CONTROL (MULTIASIENTO) ---

    async def verify_device_access(
        self,
        license_key: str,
        machine_id: str,
        device_name: str = None
    ) -> dict:
        """
        Verifica y registra el acceso de un dispositivo bajo una licencia.
        
        Implementa el control de "asientos" (multi-seat). Si el dispositivo es nuevo, 
        consume un puesto de la licencia si hay disponibilidad.

        Args:
            license_key: Clave de licencia pública.
            machine_id: Identificador de hardware (UUID de máquina).
            device_name: Nombre legible del equipo (opcional).

        Returns:
            dict: Estado del acceso {"allowed": True, ...}.

        Raises:
            PermissionError: Si se ha alcanzado el límite de puestos contratados.
            ValueError: Si la licencia es inválida o inexistente.
        """
        # 1. Validar licencia (reutiliza lógica existente)
        license = await self._validate_license(license_key)

        async with AsyncSession(server_engine) as session:
            # 2. Buscar activación existente para este (license_id, machine_id)
            stmt = select(LicenseActivation).where(
                LicenseActivation.license_id == license.license_id,
                LicenseActivation.machine_id == machine_id
            )
            result = await session.execute(stmt)
            existing_activation = result.scalar_one_or_none()

            # CASO A: Ya existe activación para este dispositivo
            if existing_activation:
                # Actualizar last_seen
                existing_activation.last_seen = datetime.utcnow()
                session.add(existing_activation)
                await session.commit()
                return {"allowed": True, "message": "Acceso permitido"}

            # CASO B: Nueva activación
            # Contar activaciones actuales
            count_stmt = select(LicenseActivation).where(
                LicenseActivation.license_id == license.license_id
            )
            count_result = await session.execute(count_stmt)
            current_activations = len(count_result.scalars().all())

            # B.1: Hay puestos disponibles
            if current_activations < license.max_seats:
                new_activation = LicenseActivation(
                    license_id=license.license_id,
                    machine_id=machine_id,
                    device_name=device_name,
                    activated_at=datetime.utcnow(),
                    last_seen=datetime.utcnow()
                )
                session.add(new_activation)
                await session.commit()
                return {"allowed": True, "message": "Nuevo dispositivo registrado"}

            # B.2: No hay puestos disponibles
            raise PermissionError(
                f"Límite de puestos excedido ({current_activations}/{license.max_seats}). "
                "Contacte a su administrador."
            )

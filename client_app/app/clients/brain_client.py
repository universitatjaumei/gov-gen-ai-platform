# client_app/app/clients/brain_client.py
"""
Cliente HTTP para comunicación con el servidor Brain.

Este módulo reemplaza los imports directos de AIBrainService,
permitiendo una separación limpia entre cliente y servidor.

SEGURIDAD:
- La autenticación se realiza via Headers (X-License-Key), no en query params
- Los query params aparecen en logs de servidor y URLs, los headers son más seguros
- Timeouts configurados para operaciones de LLM (120s) vs conexión (10s)

En desarrollo local, el servidor Brain debe ejecutarse en localhost:8080.
En producción, la URL se configura en ServerConnection.
"""
import httpx
import os
import sys
from typing import Any, Optional, Dict, List, Tuple



from dataclasses import dataclass, field

@dataclass
class LicenseInfo:
    """Información de licencia devuelta por el servidor."""
    valid: bool
    quota_remaining: int
    expires_at: str
    tier: str = "TRIAL"
    features: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'LicenseInfo':
        return LicenseInfo(
            valid=data.get("valid", False),
            quota_remaining=data.get("quota_remaining", 0),
            expires_at=data.get("expires_at", ""),
            tier=data.get("tier", "TRIAL"),
            features=data.get("features", [])
        )

class BrainAPIClient:
    """
    Cliente HTTP para el servidor Brain (AIBrainService).

    Maneja autenticación via Headers y timeouts extendidos para LLMs.

    Uso:
        client = BrainAPIClient(base_url="http://localhost:8080")
        result = await client.generate_script(
            prompt="...",
            output_schema={},
            license_key="..."
        )

    Atributos:
        base_url: URL base del servidor Brain
        timeout: Configuración de timeouts (120s total, 10s conexión)
    """

    def __init__(self, base_url: str = "http://localhost:8080"):
        """
        Inicializa el cliente con la URL del servidor Brain.

        Args:
            base_url: URL base del servidor (default: localhost:8080)
        """
        self.base_url = base_url.rstrip("/")
        # Timeout: 180s para operaciones normales, 10s para conexión inicial
        self.timeout = httpx.Timeout(180.0, connect=10.0)
        # Timeout extendido para operaciones largas (generación de scripts, etc.)
        self.timeout_extended = httpx.Timeout(300.0, connect=10.0)

    def _get_headers(self, license_key: str) -> Dict[str, str]:
        """
        Genera headers con autenticación para las peticiones.

        La licencia viaja en headers por seguridad:
        - Los query params aparecen en logs de acceso del servidor
        - Los headers son más seguros para credenciales

        Args:
            license_key: Clave de licencia del cliente

        Returns:
            Dict con headers necesarios para la petición
        """
        return {
            "X-License-Key": license_key,
            "Content-Type": "application/json"
        }

    async def post_generic(
        self,
        endpoint: str,
        json_data: Dict[str, Any],
        license_key: str = "TRIAL-KEY"
    ) -> Dict[str, Any]:
        """
        Realiza una petición POST genérica al servidor Brain.
        Útil para endpoints nuevos o específicos no cubiertos por métodos dedicados.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}{endpoint}",
                headers=self._get_headers(license_key),
                json=json_data
            )
            
            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")
                
            response.raise_for_status()
            return response.json()

    async def _log_telemetry(
        self, 
        service_id: str, 
        start_time: float, 
        model: Optional[str], 
        response_data: Optional[Dict] = None, 
        error_message: Optional[str] = None
    ):
        """
        Helper method to log telemetry asynchronously without blocking.
        Uses local import to avoid circular dependency with SyncService.
        """
        import time
        try:
            from client_app.app.services.sync_service import sync_service
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Extract basic metrics if available
            # Assuming standard OpenAI format or simplified {tokens_used: int}
            prompt_tokens = 0
            completion_tokens = 0
            
            if response_data:
                usage = response_data.get("usage", {})
                if usage:
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                else:
                    # Fallback for simplified APIs
                    total = response_data.get("tokens_used", 0)
                    completion_tokens = total # Approximate if split not available
            
            # Validar status
            status = "error" if error_message else "success"
            
            # Fire and forget logging
            await sync_service.log_run_manifest(
                execution_id=None, # Auto-generated
                service_id=service_id,
                model_used=model or "default",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                duration_ms=duration_ms,
                status=status,
                error_message=error_message
            )
        except Exception as e:
            # Telemetry should never break the app
            print(f"[BrainAPIClient] Telemetry logging failed: {e}")

    async def generate_script(
        self,
        prompt: str,
        output_schema: dict,
        license_key: str,
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> dict:
        """
        Genera un script de extracción via API.
        """
        import time
        start_time = time.time()
        
        if os.getenv("DEBUG_IA_TRAFFIC") == "true":
            # [AUDITORÍA DE PRIVACIDAD] Safe log for Windows and visibility
            try:
                # Use repr for safety or encode/decode if needed
                safe_prompt = repr(prompt)
                print(f"\n[AUDITORÍA DE PRIVACIDAD] Payload enviado al Brain: {safe_prompt}\n")
            except Exception:
                print("\n[AUDITORÍA DE PRIVACIDAD] Error al loguear payload (problema de encoding)\n")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/brain/generate_script",
                    headers=self._get_headers(license_key),
                    json={
                        "prompt": prompt,
                        "output_schema": output_schema,
                        "model": model,
                        "temperature": temperature
                    }
                )

                if response.status_code == 401:
                    raise ValueError("Licencia no válida o expirada")

                response.raise_for_status()
                result = response.json()
                
                # Log telemetry success
                await self._log_telemetry(
                    service_id="generate_script",
                    start_time=start_time,
                    model=model,
                    response_data=result
                )
                
                return result
        except Exception as e:
            # Log telemetry error
            await self._log_telemetry(
                service_id="generate_script",
                start_time=start_time,
                model=model,
                error_message=str(e)
            )
            raise e

    async def validate_license(self, license_key: str) -> LicenseInfo:
        """
        Valida una licencia contra el servidor.

        Llama a GET /api/brain/validate_license

        NOTA: La licencia viaja en HEADERS, no en query params por seguridad.
        Los query params aparecen en logs de acceso del servidor.

        Args:
            license_key: Clave de licencia a validar

        Returns:
            LicenseInfo: Objeto con información de la licencia

        Raises:
            ValueError: Si la licencia no existe o está expirada
            httpx.HTTPError: Si hay error de red o servidor
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/brain/validate_license",
                headers=self._get_headers(license_key)
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida")

            response.raise_for_status()
            return LicenseInfo.from_dict(response.json())

    async def verify_partner_token(self, token: str) -> bool:
        """
        Verifica un token de partner específico.
        
        Llama a POST /api/brain/auth/verify_partner_token
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Intentar ruta específica de auth si existe
                # Asumimos que auth_router está montado en /api/brain/auth o /auth
                # Probamos /api/brain/auth primero por consistencia
                response = await client.post(
                    f"{self.base_url}/api/brain/auth/verify_partner_token",
                    headers={"Content-Type": "application/json"},
                    json={"token": token}
                )
                
                if response.status_code == 404:
                    # Fallback a ruta raíz /auth/verify_partner_token si no está namespaceada
                    response = await client.post(
                        f"{self.base_url}/auth/verify_partner_token",
                        headers={"Content-Type": "application/json"},
                        json={"token": token}
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("valid", False)
                    
                return False
        except Exception as e:
            print(f"[BrainAPIClient] Error verificando partner token: {e}")
            return False

    async def get_effective_policy(self, license_key: str) -> Dict[str, Any]:
        """
        Obtiene la política de seguridad efectiva desde el servidor.
        
        Llama a GET /api/brain/security/policy
        
        Args:
            license_key: Clave de licencia
            
        Returns:
            Dict con la configuración de seguridad y firma RSA
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/api/brain/security/policy",
                headers=self._get_headers(license_key)
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            response.raise_for_status()
            return response.json()

    async def call_llm(
        self,
        prompt: str,
        role: str = "general",
        service_id: Optional[str] = None,
        config_summary: Optional[Dict[str, Any]] = None,
        license_key: str = "TRIAL-KEY",
        model: Optional[str] = None,
        temperature: float = 0.5
    ) -> str:
        """
        Llama al LLM para tareas genéricas (análisis, clarificación).
        """
        import time
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/brain/call_llm",
                    headers=self._get_headers(license_key),
                    json={
                        "prompt": prompt,
                        "role": role,
                        "service_id": service_id,
                        "config_summary": config_summary,
                        "model": model,
                        "temperature": temperature
                    }
                )

                if response.status_code == 401:
                    raise ValueError("Licencia no válida o expirada")

                response.raise_for_status()
                result = response.json()
                
                # Log telemetry success
                await self._log_telemetry(
                    service_id=f"call_llm_{role}",
                    start_time=start_time,
                    model=model,
                    response_data=result
                )

                return result.get("response", "")
        except Exception as e:
            # Log telemetry error
            await self._log_telemetry(
                service_id=f"call_llm_{role}",
                start_time=start_time,
                model=model,
                error_message=str(e)
            )
            raise e

    async def orchestrate_flow(
        self, 
        prompt: str, 
        license_key: str,
        local_inventory: List[Dict[str, Any]] = [],
        client_id: Optional[str] = None,
        partner_id: Optional[str] = None
    ) -> dict:
        """
        Invoca al orquestador de flujos (sys_flow_orchestrator).
        Envía inventario local y contexto al servidor.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/brain/orchestrate",
                headers=self._get_headers(license_key),
                json={
                    "prompt": prompt,
                    "local_inventory": local_inventory,
                    "client_id": client_id,
                    "partner_id": partner_id
                }
            )
            # Handle 422/Needs Clarification if API supports it via status
            # For now assume 200 OK with specific body
            response.raise_for_status()
            return response.json()

    async def generate_code(self, prompt: str, language: str = "python", service_id: str = "default", license_key: str = "TRIAL-KEY") -> Dict[str, Any]:
        """
        Generic code generation. Delegates to generate_script with appropriate schema.
        """
        return await self.generate_script(
            prompt=f"Generate {language} code: {prompt}",
            output_schema={"language": language, "service_id": service_id},
            license_key=license_key
        )

    # --- DOCUMENT EXTRACTION METHODS ---

    async def analyze_document_structure(
        self,
        texto_a: str,
        texto_b: str,
        definicion_usuario: str,
        service_id: str = "sys_phase0_discovery",
        license_key: str = "TRIAL-KEY"
    ) -> Dict[str, Any]:
        """
        Fase 0: Descubrimiento de estructura de documentos.

        Llama a POST /api/brain/extraction/analyze_structure

        Args:
            texto_a: Texto del primer documento
            texto_b: Texto del segundo documento
            definicion_usuario: Descripción de qué campos buscar
            service_id: ID del servicio de prompt
            license_key: Clave de licencia

        Returns:
            dict: Estructura descubierta con campos identificados
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/brain/extraction/analyze_structure",
                headers=self._get_headers(license_key),
                json={
                    "texto_a": texto_a,
                    "texto_b": texto_b,
                    "definicion_usuario": definicion_usuario,
                    "service_id": service_id
                }
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            response.raise_for_status()
            return response.json()

    async def extract_data(
        self,
        file_path: str,
        user_definition: str,
        target_fields: List[str] = [],
        usar_tier_2: bool = False,
        ejemplos_validacion: Optional[Dict] = None,
        texto_fitz: Optional[str] = None,
        texto_plumber: Optional[str] = None,
        license_key: str = "TRIAL-KEY"
    ) -> Dict[str, Any]:
        """
        Fase 1: Extracción de datos desde texto pre-procesado.

        Llama a POST /api/brain/extraction/extract

        NOTA: El cliente debe extraer el texto del PDF antes de llamar.
        El servidor no tiene acceso a archivos locales.

        Args:
            file_path: Ruta original del archivo (para referencia)
            user_definition: Descripción de qué extraer
            target_fields: Lista de campos objetivo
            usar_tier_2: Si usar modelo más inteligente
            ejemplos_validacion: Ejemplos para validación
            texto_fitz: Texto extraído con PyMuPDF
            texto_plumber: Texto extraído con pdfplumber
            license_key: Clave de licencia

        Returns:
            dict: Datos extraídos
        """
        if not texto_fitz or not texto_plumber:
            raise ValueError("Se requiere texto_fitz y texto_plumber. Extrae el texto del PDF primero.")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/brain/extraction/extract",
                headers=self._get_headers(license_key),
                json={
                    "user_definition": user_definition,
                    "target_fields": target_fields,
                    "usar_tier_2": usar_tier_2,
                    "ejemplos_validacion": ejemplos_validacion,
                    "texto_fitz": texto_fitz,
                    "texto_plumber": texto_plumber
                }
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            response.raise_for_status()
            return response.json()

    async def refine_extraction_data(
        self,
        texto_fitz: str,
        texto_plumber: str,
        datos_anteriores: Dict[str, Any],
        feedback_usuario: str,
        service_id: str = "sys_phase1_refinement",
        license_key: str = "TRIAL-KEY"
    ) -> Dict[str, Any]:
        """
        Fase 1.5: Refinamiento de extracción con feedback.

        Llama a POST /api/brain/extraction/refine
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/brain/extraction/refine",
                headers=self._get_headers(license_key),
                json={
                    "texto_fitz": texto_fitz,
                    "texto_plumber": texto_plumber,
                    "datos_anteriores": datos_anteriores,
                    "feedback_usuario": feedback_usuario,
                    "service_id": service_id
                }
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            response.raise_for_status()
            return response.json()


    async def analyze_snippet(
        self,
        field_name: str,
        snippet_text: str,
        expected_format: str = "",
        license_key: str = "TRIAL-KEY"
    ) -> dict:
        """
        Análisis de snippet. Redirige a extract_field_generic_guided.
        """
        return await self.extract_field_generic_guided(
            field_name=field_name,
            snippet_text=snippet_text,
            expected_format=expected_format or "text",
            license_key=license_key
        )

    async def extract_field_generic_guided(
        self,
        field_name: str,
        snippet_text: str,
        expected_format: str = "text",
        license_key: str = "TRIAL-KEY"
    ) -> Dict[str, Any]:
        """
        Extracción guiada de un campo desde un snippet.

        Llama a POST /api/brain/extraction/guided_field
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/brain/extraction/guided_field",
                headers=self._get_headers(license_key),
                json={
                    "field_name": field_name,
                    "snippet_text": snippet_text,
                    "expected_format": expected_format
                }
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            response.raise_for_status()
            return response.json()

    # --- SCRIPT GENERATION & AUDIT METHODS ---

    async def generate_extraction_script(
        self,
        docs_text_list: List[Dict],
        campos_objetivo: List[str],
        values_example: Optional[Dict],
        info_discovery: Optional[Dict],
        feedback: Optional[str],
        field_definitions: Optional[List[Dict]],
        license_key: str = "TRIAL-KEY"
    ) -> str:
        """
        Fase 3: Genera script de extracción determinista.

        Llama a POST /api/brain/factory/generate_script

        Args:
            docs_text_list: Lista de textos de documentos [{fitz, plumber}, ...]
            campos_objetivo: Lista de campos a extraer
            values_example: Valores de ejemplo para cada campo
            info_discovery: Información de la fase de descubrimiento
            feedback: Feedback del usuario para ajustes
            field_definitions: Definiciones detalladas de campos
            license_key: Clave de licencia

        Returns:
            str: Código Python del script generado
        """
        # Usar timeout extendido para generación de scripts (operación larga)
        async with httpx.AsyncClient(timeout=self.timeout_extended) as client:
            response = await client.post(
                f"{self.base_url}/api/brain/factory/generate_script",
                headers=self._get_headers(license_key),
                json={
                    "docs_text_list": docs_text_list,
                    "campos_objetivo": campos_objetivo,
                    "values_example": values_example,
                    "info_discovery": info_discovery,
                    "feedback": feedback,
                    "field_definitions": field_definitions
                }
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            response.raise_for_status()
            result = response.json()
            return result.get("script", "")

    async def refine_script_with_error_logs(
        self,
        script_actual: str,
        reporte_forense: str,
        feedback_history: List[Dict],
        texto_documento: str,
        target_fields: List[str] = [],
        license_key: str = "TRIAL-KEY"
    ) -> str:
        """
        Refinamiento iterativo de script con logs de error.

        Llama a POST /api/brain/factory/refine_script
        """
        # Usar timeout extendido para refinamiento de scripts (operación larga)
        async with httpx.AsyncClient(timeout=self.timeout_extended) as client:
            response = await client.post(
                f"{self.base_url}/api/brain/factory/refine_script",
                headers=self._get_headers(license_key),
                json={
                    "script_actual": script_actual,
                    "reporte_forense": reporte_forense,
                    "feedback_history": feedback_history,
                    "texto_documento": texto_documento,
                    "target_fields": target_fields
                }
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            response.raise_for_status()
            result = response.json()
            return result.get("script", "")

    async def escalate_script(
        self,
        script_name: str,
        original_code: str,
        client_notes: Optional[str] = None,
        escalation_type: str = "extraction",
        license_key: str = "TRIAL-KEY"
    ) -> Dict[str, Any]:
        """
        Escala un script fallido al buzón del Partner.

        Llama a POST /api/brain/factory/escalate
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/brain/factory/escalate",
                headers=self._get_headers(license_key),
                json={
                    "script_name": script_name,
                    "original_code": original_code,
                    "client_notes": client_notes,
                    "escalation_type": escalation_type
                }
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            response.raise_for_status()
            return response.json()

    async def generate_forensic_audit(
        self,
        referencia_ia: Dict,
        resultado_script: Any,
        license_key: str = "TRIAL-KEY"
    ) -> Dict[str, Any]:
        """
        Genera reporte forense comparando resultado esperado vs obtenido.

        Llama a POST /api/brain/factory/audit
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/brain/factory/audit",
                headers=self._get_headers(license_key),
                json={
                    "referencia_ia": referencia_ia,
                    "resultado_script": resultado_script
                }
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            response.raise_for_status()
            result = response.json()
            return {"report": result.get("report", "")}

    # --- RPA METHODS ---

    async def analyze_recording(
        self,
        recording_logs: List[Dict],
        context_dict: Optional[Dict] = None,
        license_key: str = "TRIAL-KEY"
    ) -> List[Dict]:
        """
        Analiza logs de grabación para generar Playbook RPA.

        Llama a POST /api/brain/rpa/analyze

        Args:
            recording_logs: Lista de eventos grabados
            context_dict: Contexto adicional (opcional)
            license_key: Clave de licencia

        Returns:
            List[Dict]: Playbook generado como lista de pasos
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/brain/rpa/analyze",
                headers=self._get_headers(license_key),
                json={
                    "recording_logs": recording_logs,
                    "context_dict": context_dict
                }
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            response.raise_for_status()
            result = response.json()
            return result.get("playbook", [])

    async def refine_playbook(
        self,
        current_playbook: List[Dict],
        recording_logs: List[Dict],
        error_logs: str,
        user_feedback_history: List[str],
        context_data: Dict,
        license_key: str = "TRIAL-KEY"
    ) -> List[Dict]:
        """
        Refina Playbook existente con feedback y logs de error.

        Llama a POST /api/brain/rpa/refine
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/brain/rpa/refine",
                headers=self._get_headers(license_key),
                json={
                    "current_playbook": current_playbook,
                    "recording_logs": recording_logs,
                    "error_logs": error_logs,
                    "user_feedback_history": user_feedback_history,
                    "context_data": context_data
                }
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            response.raise_for_status()
            result = response.json()
            return result.get("playbook", [])

    async def get_element_coordinates(
        self,
        png_bytes: bytes,
        description: str,
        viewport: Dict,
        license_key: str = "TRIAL-KEY"
    ) -> Optional[Tuple[int, int]]:
        """
        Localiza coordenadas de un elemento visual en una imagen.

        Llama a POST /api/brain/rpa/visual_locate

        Args:
            png_bytes: Imagen PNG en bytes
            description: Descripción del elemento a buscar
            viewport: Dimensiones de la pantalla {width, height}
            license_key: Clave de licencia

        Returns:
            Tuple[int, int] o None: Coordenadas (x, y) o None si no se encuentra
        """
        import base64

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/brain/rpa/visual_locate",
                headers=self._get_headers(license_key),
                json={
                    "png_base64": base64.b64encode(png_bytes).decode("utf-8"),
                    "description": description,
                    "viewport": viewport
                }
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            response.raise_for_status()
            result = response.json()
            coords = result.get("coordinates")
            if coords and len(coords) == 2:
                return (coords[0], coords[1])
            return None

    # --- COPILOT METHODS (Prompt #9) ---

    async def ask_copilot(
        self,
        query: str,
        license_key: str,
        local_context: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        atom_id: Optional[str] = None,
        flow_context: Optional[Dict[str, Any]] = None,
        mode: str = "idle",
        model: Optional[str] = None,
        temperature: float = 0.5
    ) -> Dict[str, Any]:
        """
        Envia una consulta al Copiloto del Brain con contexto local RAG.

        Args:
            query: Pregunta del usuario
            license_key: Clave de licencia
            local_context: Contexto RAG local
            conversation_history: Historial de chat
            atom_id: ID del átomo seleccionado
            flow_context: Contexto del flujo
            mode: Modo actual (flow, atom, wizard, documentation, idle)
            model: Modelo a usar
            temperature: Temperatura
        """
        import time
        start_time = time.time()

        # Construir el payload
        payload = {
            "query": query,
            "local_context": local_context or "",
            "conversation_history": conversation_history or [],
            "atom_id": atom_id,
            "flow_context": flow_context or {},
            "mode": mode,
            "model": model,
            "temperature": temperature
        }

        if os.getenv("DEBUG_IA_TRAFFIC") == "true":
            try:
                import json
                safe_payload = json.dumps(payload, indent=2, default=str)
                print(f"\n[AUDITORIA COPILOT] Payload enviado al Brain:\n{safe_payload}\n")
            except Exception:
                print("\n[AUDITORIA COPILOT] Error al loguear payload\n")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/brain/copilot/ask",
                    headers=self._get_headers(license_key),
                    json=payload
                )

                if response.status_code == 401:
                    raise ValueError("Licencia no valida o expirada")

                response.raise_for_status()
                result = response.json()
                
                # Log telemetry
                await self._log_telemetry(
                    service_id="ask_copilot",
                    start_time=start_time,
                    model=model,
                    response_data=result
                )
                
                return result
        except Exception as e:
            # Log telemetry error
            await self._log_telemetry(
                service_id="ask_copilot",
                start_time=start_time,
                model=model,
                error_message=str(e)
            )
            raise e

    async def ask_copilot_with_rag(
        self,
        query: str,
        license_key: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        atom_id: Optional[str] = None,
        flow_context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        temperature: float = 0.5
    ) -> Dict[str, Any]:
        """
        Metodo de conveniencia que integra automaticamente el RAG local.

        Busca contexto relevante en la documentacion local y lo incluye
        en la peticion al Brain.

        Args:
            query: Pregunta del usuario
            license_key: Clave de licencia
            conversation_history: Historial de chat
            atom_id: ID del atomo seleccionado
            flow_context: Contexto del flujo
            model: Modelo a usar
            temperature: Temperatura

        Returns:
            Respuesta del copiloto con contexto local integrado
        """
        # Obtener contexto local via RAG
        local_context = ""
        try:
            from client_app.app.services.local_knowledge_service import local_knowledge_service
            local_context = local_knowledge_service.get_context_for_query(query)
        except Exception as e:
            # Si falla el RAG, continuar sin contexto local
            if os.getenv("DEBUG_IA_TRAFFIC") == "true":
                print(f"[COPILOT RAG] Warning: Error obteniendo contexto local: {e}")

        return await self.ask_copilot(
            query=query,
            license_key=license_key,
            local_context=local_context,
            conversation_history=conversation_history,
            atom_id=atom_id,
            flow_context=flow_context,
            model=model,
            temperature=temperature
        )

    async def get_effective_policy(
        self,
        license_key: str
    ) -> Dict[str, Any]:
        """
        Obtiene la política de seguridad efectiva para el cliente actual.

        La política se resuelve usando el motor de cascada del servidor:
        CLIENTE > PARTNER > SISTEMA

        Args:
            license_key: Clave de licencia del cliente

        Returns:
            dict: Política efectiva con campos como:
                - allowed_domains: List[str]
                - allowed_libraries: List[str]
                - forbidden_libraries: List[str]
                - max_memory_mb: int
                - max_execution_time: int
                - applied_level: str (CLIENT, PARTNER, SYSTEM)
                - screenshot_policy: str (BLOCK, REVIEW, TRUSTED)

        Raises:
            ValueError: Si la licencia no es válida
            httpx.HTTPError: Si hay error de red
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/brain/security/effective_policy",
                headers=self._get_headers(license_key)
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            response.raise_for_status()
            return response.json()

    async def run_agent_step(
        self,
        task_instruction: str,
        page_state: Dict[str, Any],
        action_history: List[Dict[str, Any]],
        license_key: str = "TRIAL-KEY"
    ) -> Dict[str, Any]:
        """
        Ejecuta un paso de agente autónomo usando el LLM del servidor.

        El cliente envía el estado de la página y el historial de acciones,
        y el servidor responde con la siguiente acción a ejecutar.

        Args:
            task_instruction: Instrucción original de la tarea
            page_state: Estado actual de la página {url, title, screenshot_base64, html_snippet}
            action_history: Historial de acciones ejecutadas [{action, result, timestamp}]
            license_key: Clave de licencia

        Returns:
            dict: {
                "action": str,  # click, fill, navigate, done, error
                "selector": str,  # CSS selector o descripción
                "value": str,  # Valor para fill o URL para navigate
                "reasoning": str,  # Explicación del agente
                "is_complete": bool  # Si la tarea está completa
            }

        Raises:
            ValueError: Si la licencia no es válida
            httpx.HTTPError: Si hay error de red
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/brain/agent/step",
                headers=self._get_headers(license_key),
                json={
                    "task_instruction": task_instruction,
                    "page_state": page_state,
                    "action_history": action_history
                }
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            response.raise_for_status()
            return response.json()

    async def generate_bridge_code(
        self,
        source_type: str,
        target_type: str,
        source_name: str,
        target_name: str,
        license_key: str,
        example_value: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Solicita al Brain generar un script puente para conversion de tipos.

        Usado por TypeCompatibilityService (Prompt #10) cuando se detectan
        incompatibilidades de tipos entre conexiones de flujo.

        Args:
            source_type: Tipo de dato de origen (ej: "STR")
            target_type: Tipo de dato de destino (ej: "INT")
            source_name: Nombre del campo de origen
            target_name: Nombre del campo de destino
            license_key: Clave de licencia
            example_value: Valor de ejemplo para guiar la conversion
            model: Modelo a usar

        Returns:
            str: Codigo Python del script puente

        Raises:
            ValueError: Si la licencia no es valida
            httpx.HTTPError: Si hay error de red
        """
        payload = {
            "source_type": source_type,
            "target_type": target_type,
            "source_name": source_name,
            "target_name": target_name,
            "example_value": example_value,
            "model": model
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/brain/copilot/generate_bridge",
                headers=self._get_headers(license_key),
                json=payload
            )

            if response.status_code == 401:
                raise ValueError("Licencia no valida o expirada")

            response.raise_for_status()
            result = response.json()
            return result.get("code", "")

    # --- LIBRARY METHODS (Prompts #3-4: Push/Download con firma) ---

    def _get_library_headers(
        self,
        license_key: str,
        client_id: Optional[str] = None,
        partner_id: Optional[str] = None,
        client_groups: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Genera headers para las peticiones a la biblioteca.

        Incluye contexto de cliente/partner para control de acceso.

        Args:
            license_key: Clave de licencia
            client_id: ID del cliente (opcional)
            partner_id: ID del partner (opcional)
            client_groups: Grupos de acceso del cliente (lista JSON)

        Returns:
            Dict con headers necesarios
        """
        import json

        headers = self._get_headers(license_key)

        if client_id:
            headers["X-Client-ID"] = client_id
        if partner_id:
            headers["X-Partner-ID"] = partner_id
        if client_groups:
            headers["X-Client-Groups"] = json.dumps(client_groups)

        return headers

    async def push_to_library(
        self,
        manifest: Dict[str, Any],
        license_key: str,
        client_id: Optional[str] = None,
        partner_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publica una automatización en la biblioteca central del servidor.

        Envía un manifiesto al endpoint POST /v1/library/push.
        El servidor firmará automáticamente el contenido antes de persistirlo.

        Args:
            manifest: Diccionario con los datos de la automatización.
                     Debe contener al menos: id, name, type, code_content.
            license_key: Clave de licencia del cliente
            client_id: ID del cliente propietario (opcional)
            partner_id: ID del partner (opcional)

        Returns:
            dict: {
                "status": "success",
                "id": str,       # ID del item creado/actualizado
                "version": int,  # Versión del item
                "signed": bool   # Si el servidor firmó el manifiesto
            }

        Raises:
            ValueError: Si la licencia no es válida
            httpx.HTTPError: Si hay error de red o servidor
            httpx.HTTPStatusError: Si el servidor retorna error (4xx, 5xx)
        """
        # Construir el payload según AutomationBlueprintDTO
        payload = {
            "id": manifest.get("id"),
            "name": manifest.get("name"),
            "type": manifest.get("type", "extraction"),
            "code_content": manifest.get("code_content", ""),
            "version": manifest.get("version", 1),
            "updated_at": manifest.get("updated_at"),
            "client_id": client_id or manifest.get("client_id"),
            "partner_id": partner_id or manifest.get("partner_id"),
            "is_system_template": manifest.get("is_system_template", False),
            "signature": manifest.get("signature"),  # Puede venir pre-firmado
            "access_groups": manifest.get("access_groups", []),
            "is_workflow": manifest.get("is_workflow", False),
            "metadata": manifest.get("metadata", {})
        }

        # Añadir updated_at si no existe
        if not payload.get("updated_at"):
            from datetime import datetime, timezone
            payload["updated_at"] = datetime.now(timezone.utc).isoformat()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v1/library/push",
                headers=self._get_library_headers(
                    license_key,
                    client_id=client_id,
                    partner_id=partner_id
                ),
                json=payload
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            if response.status_code == 500:
                # Error de servidor (puede ser problema de firma)
                error_detail = response.json().get("detail", "Error interno del servidor")
                raise httpx.HTTPStatusError(
                    f"Error del servidor: {error_detail}",
                    request=response.request,
                    response=response
                )

            response.raise_for_status()
            return response.json()

    async def download_from_library(
        self,
        item_id: str,
        license_key: str,
        client_id: Optional[str] = None,
        partner_id: Optional[str] = None,
        client_groups: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Descarga una automatización de la biblioteca central.

        Obtiene el manifiesto completo incluyendo la firma criptográfica
        del servidor para verificación de integridad.

        Args:
            item_id: ID único de la automatización a descargar
            license_key: Clave de licencia del cliente
            client_id: ID del cliente (para control de acceso)
            partner_id: ID del partner (para control de acceso)
            client_groups: Grupos de acceso del cliente

        Returns:
            dict: AutomationBlueprintDTO con campos:
                - id: str
                - name: str
                - type: str
                - code_content: str
                - version: int
                - updated_at: str (ISO format)
                - client_id: Optional[str]
                - partner_id: Optional[str]
                - is_system_template: bool
                - signature: Optional[str]  # Firma RSA del servidor
                - access_groups: List[str]
                - is_workflow: bool
                - metadata: Dict

        Raises:
            ValueError: Si la licencia no es válida
            httpx.HTTPStatusError: Si el item no existe (404) o acceso denegado (403)
            httpx.HTTPError: Si hay error de red
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/v1/library/download/{item_id}",
                headers=self._get_library_headers(
                    license_key,
                    client_id=client_id,
                    partner_id=partner_id,
                    client_groups=client_groups
                )
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            if response.status_code == 403:
                raise httpx.HTTPStatusError(
                    f"Acceso denegado a la automatización '{item_id}'",
                    request=response.request,
                    response=response
                )

            if response.status_code == 404:
                raise httpx.HTTPStatusError(
                    f"Automatización '{item_id}' no encontrada",
                    request=response.request,
                    response=response
                )

            response.raise_for_status()
            return response.json()

    async def get_library_manifest(
        self,
        license_key: str,
        client_id: Optional[str] = None,
        partner_id: Optional[str] = None,
        client_groups: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene el manifiesto ligero de automatizaciones visibles.

        Retorna una lista de metadatos básicos (sin código) para
        sincronización y descubrimiento de recursos disponibles.

        Args:
            license_key: Clave de licencia
            client_id: ID del cliente
            partner_id: ID del partner
            client_groups: Grupos de acceso

        Returns:
            List[dict]: Lista de items con {id, name, version, updated_at, is_workflow}

        Raises:
            ValueError: Si la licencia no es válida
            httpx.HTTPError: Si hay error de red
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/v1/library/manifest",
                headers=self._get_library_headers(
                    license_key,
                    client_id=client_id,
                    partner_id=partner_id,
                    client_groups=client_groups
                )
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            response.raise_for_status()
            return response.json()


    async def escalate_support_request(
        self,
        asset_id: Optional[int],
        asset_type: str,
        details: Dict[str, Any],
        user_comment: str,
        license_key: str
    ) -> Dict[str, Any]:
        """
        Envía una solicitud de soporte técnico al Partner.
        
        Llama a POST /api/brain/support/escalate
        """
        payload = {
            "asset_id": asset_id,
            "asset_type": asset_type,
            "details": details,
            "user_comment": user_comment
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/brain/support/escalate",
                headers=self._get_headers(license_key),
                json=payload
            )

            if response.status_code == 401:
                raise ValueError("Licencia no válida o expirada")

            response.raise_for_status()
            return response.json()


async def get_brain_url_from_db() -> str:
    """
    Obtiene la URL del servidor Brain desde la base de datos.

    Lee la configuración de ServerConnection y devuelve la URL configurada.
    Si no hay configuración, retorna el valor por defecto.

    Returns:
        str: URL del servidor Brain (ej: "http://localhost:8080")
    """
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlmodel import select
    from client_app.app.database.db import client_engine
    from client_app.app.database.models import ServerConnection

    try:
        async with AsyncSession(client_engine) as session:
            result = await session.exec(select(ServerConnection).where(ServerConnection.is_active == True))
            conn = result.first()
            if conn and conn.brain_url:
                return conn.brain_url
    except Exception:
        pass

    return "http://localhost:8080"


async def get_brain_client() -> BrainAPIClient:
    """
    Crea un BrainAPIClient con la URL configurada en la base de datos.

    Esta función debe usarse en lugar de BrainAPIClient() sin parámetros
    para asegurar que se usa la URL correcta de configuración.

    Returns:
        BrainAPIClient: Cliente configurado con la URL de la BD
    """
    url = await get_brain_url_from_db()
    return BrainAPIClient(base_url=url)

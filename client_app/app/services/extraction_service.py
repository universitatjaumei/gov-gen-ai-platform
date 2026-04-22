import os
import gc
import re
import uuid
import json
import importlib.util
import shutil
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import difflib

import pandas as pd
from nicegui import run # Optimization for IO-bound tasks
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession



# Imports internos - Client App
from client_app.app.database.db import client_engine
from client_app.app.database.models import ExtractionLog, UserExtractionConfig
from client_app.app.core.exporters import formatear_excel_dual
from client_app.app.services.sandbox_service import SandboxExecutionService
from client_app.app.modules.privacy.anonymizer import AnonymizationContext
from client_app.app.core.audit import audit_operation
from client_app.app.services.enterprise_audit_service import enterprise_audit_service

# Import directo ELIMINADO en favor de Adapter Pattern
# from server.app.services.ai_brain import AIBrainService
from client_app.app.clients.brain_client import BrainAPIClient
from client_app.app.core.state import state

# Imports desde automatia_shared
from automatia_shared.core.reader import extraer_texto_dual
from automatia_shared.core.execution_manager import ExecutionPathManager
from automatia_shared.core.pdf_reader import PdfReaderDual
from automatia_shared.core.consolidator import DataConsolidator
from client_app.app.services.script_library_service import script_library_service # Unified Promotion

@dataclass
class FieldDef:
    """Definición de un campo para extracción."""
    name: str
    description: str
    example_value: str
    is_optional: bool
    page_hint: Optional[str] = None


# === PROMPT #4: Contract Building for Extraction ===

from automatia_shared.contracts.ui_contract import (
    InputType, 
    InputDefinition, 
    UIContract, 
    DataContract, 
    OutputSchema, 
    OutputField
)


# Type mapping from user-friendly names to InputType enum
EXTRACTION_TYPE_MAP = {
    'string': InputType.STR,
    'str': InputType.STR,
    'text': InputType.STR,
    'texto': InputType.STR,
    'int': InputType.INT,
    'integer': InputType.INT,
    'numero': InputType.INT,
    'number': InputType.INT,
    'float': InputType.FLOAT,
    'decimal': InputType.FLOAT,
    'money': InputType.FLOAT,
    'date': InputType.DATE,
    'fecha': InputType.DATE,
    'datetime': InputType.DATETIME,
    'bool': InputType.BOOL,
    'boolean': InputType.BOOL,
    'booleano': InputType.BOOL,
    'file': InputType.FILE,
    'archivo': InputType.FILE,
}


def _humanize_label(name: str) -> str:
    """Convert snake_case name to Human Readable Label."""
    return name.replace('_', ' ').replace('-', ' ').title()


def _map_field_type(type_str: str) -> str:
    """Map user-specified type to InputType enum value."""
    type_lower = (type_str or 'string').lower().strip()
    input_type = EXTRACTION_TYPE_MAP.get(type_lower, InputType.STR)
    return input_type.value




def generate_extraction_readme(
    name: str,
    description: str,
    field_definitions: List[Dict[str, Any]],
    engine: str = "fitz"
) -> str:
    """
    Genera un archivo README.md estandarizado para un robot de extracción.
    Incluye secciones de Título, Descripción, Tipo, Entrada y Esquema de Salida.

    Args:
        name: Nombre del robot.
        description: Descripción del propósito del robot.
        field_definitions: Lista de campos que el robot es capaz de extraer.
        engine: Motor tecnológico de base.

    Returns:
        Contenido en formato Markdown.
    """
    lines = [
        f"# {name}",
        "",
        f"{description or 'Robot de extracción de datos desde documentos.'}",
        "",
        "## Tipo",
        "",
        "Extracción de Documentos (Factory Mode)",
        "",
        f"**Motor de Extracción:** {engine}",
        "",
        "## Entrada",
        "",
        "| Campo | Tipo | Descripción |",
        "|-------|------|-------------|",
        "| input_document | FILE | Documento PDF a procesar |",
        "",
        "## Esquema de Salida",
        "",
        "| Campo | Tipo | Obligatorio | Descripción |",
        "|-------|------|-------------|-------------|",
    ]

    for field in field_definitions:
        fname = field.get("name", "")
        ftype = field.get("type", "string")
        freq = "Sí" if not field.get("is_optional", False) else "No"
        fdesc = field.get("description", "")
        lines.append(f"| {fname} | {ftype} | {freq} | {fdesc} |")

    lines.extend([
        "",
        "## Uso",
        "",
        "Este robot procesa documentos PDF y extrae los campos definidos en el esquema de salida.",
        "Los datos extraídos se devuelven en formato JSON.",
        "",
        "---",
        "",
        "*Generado automáticamente por Gov Gen AI Factory*"
    ])

    return "\n".join(lines)


# === END PROMPT #4 ===

def _fuzzy_equal(a: str, b: str, threshold: float = 0.95) -> bool:
    return difflib.SequenceMatcher(None, (a or '').strip(), (b or '').strip()).ratio() >= threshold

def validate_field_value(field_name: str, value: Any, rules: Dict[str, Any]) -> Tuple[bool, Any]:
    """
    Realiza una validación determinista y normalización de un valor extraído.

    Aplica reglas basadas en el tipo de dato (fecha, moneda, etc.) y expresiones regulares
    para asegurar que el dato cumple con los requisitos del contrato.

    Args:
        field_name: Nombre del campo a validar.
        value: Valor extraído por el motor de IA o script.
        rules: Diccionario de reglas de validación.

    Returns:
        Una tupla (éxito, valor_normalizado).
    """
    if value is None:
        return False, None
        
    val_str = str(value).strip()
    norm_val = value # Default keep original
    
    # 1. Type: Date
    if rules.get("type") == "date":
        # Simple regex dd/mm/yyyy or yyyy-mm-dd
        # This is a basic check; can be expanded
        date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|(\d{4}[/-]\d{1,2}[/-]\d{1,2})'
        if not re.search(date_pattern, val_str):
             return False, val_str
    
    # 2. Type: Money/Float
    if rules.get("type") in ["money", "float", "int"]:
        # Remove currency symbols and normalize ,/. 
        # Heuristic: if ',' is last separator, it's decimal (ES), else '.'
        clean = re.sub(r'[^\d.,-]', '', val_str)
        try:
            # Parse logic (simplified)
            # Assumption: standard float parsing might fail on 1.000,00
            # We skip complex parsing here for brevity, just check if it LOOKS like a number
            if not re.match(r'^-?\d+([.,]\d+)?$', clean):
                 return False, val_str
        except:
             return False, val_str
             
    # 3. Regex
    if "regex" in rules:
        if not re.fullmatch(rules["regex"], val_str):
            return False, val_str
            
    return True, norm_val

def validate_execution_results(extracted: Dict[str, Any], field_defs: List[FieldDef]) -> tuple[bool, Dict[str, str]]:
    """
    Valida los resultados globales de una ejecución de extracción contra las
    definiciones de campos esperadas.

    Verifica obligatoriedad y realiza comparaciones 'fuzzy' contra valores de ejemplo
    para detectar posibles desvíos o alucinaciones en la extracción.

    Returns:
        Tupla (éxito_global, diccionario_de_errores).
    """
    errors = {}
    ok = True
    
    # Normalize
    data_to_check = extracted
    if 'datos' in extracted and isinstance(extracted['datos'], dict):
        data_to_check = extracted['datos']
    
    for fd in field_defs:
        key = fd.name
        anchor = fd.example_value
        is_opt = fd.is_optional
        val = data_to_check.get(key, None)

        if not is_opt:
            if val is None or (isinstance(val, str) and val.strip() == ''):
                errors[key] = 'FALLO_CRITICO: campo obligatorio vacío o ausente'
                ok = False
                continue
        else:
            if val is None:
                 errors[key] = 'FALLO_TECNICO: opcional devolvió None (debe ser "")'
                 continue

        if anchor:
            val_str = str(val) if val is not None else ""
            if isinstance(val, dict):
                 val_str = str(val.get('valor', val))
            if isinstance(val, (list, tuple)):
                 val_str = ' '.join(str(x) for x in val)
            
            if not _fuzzy_equal(val_str, str(anchor)):
                errors[key] = f'ANCHOR_MISMATCH: esperado≈"{anchor}", obtenido="{val_str}"'
                ok = False
    
    return ok, errors

# --- FALLBACK & SNIPPET HELPERS ---

def extract_snippet_by_page(filename: str, page_index: int, anchor_hint: str = None, window: int = 2000) -> str:
    """Extracts a text window around a hint or center of page."""
    import fitz
    try:
        doc = fitz.open(filename)
        if page_index < 0 or page_index >= len(doc):
             return ""
        text = doc[page_index].get_text()
        doc.close()
        
        # Locate hint
        center = len(text) // 2
        if anchor_hint and anchor_hint.strip():
            found_idx = text.lower().find(anchor_hint.lower())
            if found_idx >= 0:
                center = found_idx
        
        start = max(0, center - window // 2)
        end = min(len(text), start + window)
        return text[start:end]
    except Exception as e:
        # Error extracting snippet - silent fallback
        return ""

async def _analyze_snippet_fallback(brain, filename: str, field_name: str, meta_hint: dict) -> str:
    """Orchestrates the snippet extraction fallback."""
    page_idx = meta_hint.get('page', 0)
    anchor = meta_hint.get('anchor_hint', '')
    
    snippet = await run.io_bound(extract_snippet_by_page, filename, page_idx, anchor)
    if not snippet:
        return ""
        
    result = await brain.analyze_snippet(field_name, snippet, expected_format="")
    return result.get(field_name, "")




# --- BRAIN CLIENT (Centralizado) ---


class ExtractionService:
    """
    Servicio unificado de Extracción de Datos desde Documentos.
    Orquesta la lógica de Factory (IA generativa), Sandbox (ejecución segura)
    y procesamiento por lotes (Batch).
    """

    def __init__(self, brain: Optional[Any] = None, logger=None, reader: Optional[PdfReaderDual] = None, settings=None):
        # NOTE: 'brain' arg is legacy/local injection. We now use dynamic resolution.
        self._local_brain_ref = brain 
        self.logger = logger
        self.settings = settings or {}
        self._anonymizer: Optional[AnonymizationContext] = None
        # Initialize Reader if not provided
        # Límites aumentados para aprovechar ventanas de contexto de LLMs modernos
        # La ejecución posterior del script es determinista (sin coste), así que vale
        # la pena enviar más contexto para generar scripts de mayor calidad
        self.reader = reader or PdfReaderDual(
             max_chars_lineal=self.settings.get('reader_max_chars_lineal', 50000),
             max_chars_layout=self.settings.get('reader_max_chars_layout', 50000)
        )
        # Usar rutas absolutas para evitar problemas con el directorio de trabajo
        self.sandbox_dir = Path("app/modules/extraccion/sandbox").resolve()
        self.services_dir = Path("app/modules/extraccion/.servicios_generados").resolve() # Dot-folder to be ignored by watchfiles
        # Asegurar que los directorios existen
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.services_dir.mkdir(parents=True, exist_ok=True)
        self.path_manager = ExecutionPathManager()
        self.sandbox = SandboxExecutionService(self.path_manager)
        # self.results_dir deprecated in favor of path_manager, but kept for legacy
        self.results_dir = Path("data/resultados")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def build_extraction_contract(self, data: Dict[str, Any]) -> DataContract:
        """
        Construye un DataContract unificado para un robot de extracción.
        
        Args:
            data: Diccionario con la definición ("fields", "config", etc).
                  Se espera formato: {"fields": [{"name":..., "type":...}], "config": {...}}

        Returns:
            DataContract validado con Pydantic.
        """
        # 1. Mapear campos crudos a objetos OutputField
        fields = []
        for f in data.get("fields", []):
            field_type_str = f.get("type", "string")
            # Map simple string type to InputType enum if needed, or rely on Pydantic validation
            # Current OutputField.type expects InputType enum.
            # We reuse _map_field_type logic but need to cast back to InputType enum
            
            # _map_field_type returns string value of enum. OutputField expects InputType enum member?
            # OutputField definition: type: InputType
            # InputType is Enum. Pydantic can often coercion from value.
            
            mapped_type_val = _map_field_type(field_type_str)
            
            fields.append(
                OutputField(
                    name=f["name"],
                    label=f.get("label") or _humanize_label(f["name"]),
                    type=mapped_type_val, # Pydantic will coerce string value to Enum
                    description=f.get("description", ""),
                    example=f.get("example_value"),
                    nullable=f.get("is_optional", False)
                )
            )

        # 2. Construir inputs por defecto (el documento a leer)
        default_inputs = [
            InputDefinition(
                 name="input_document",
                 label="Documento de Entrada",
                 type=InputType.FILE,
                 required=True,
                 description="Archivo PDF o documento a procesar"
            )
        ]

        # 3. Instanciar el esquema de salida
        output_schema = OutputSchema(fields=fields)
        ui_contract = UIContract(inputs=default_inputs, version="1.0.0")

        # 4. Retornar el contrato completo
        return DataContract(
            version="1.0.0",
            inputs=ui_contract,
            outputs=output_schema,
            # Config extra can be stored? DataContract doesn't have a generic config dict field 
            # based on shared definition we just saw?
            # Let's check DataContract definition again.
            # DataContract: inputs, outputs, version. No 'config'.
            # So we rely on mapping.
        )


    async def _get_active_license_key(self) -> Optional[str]:
        """Retrieves active license key from local db."""
        from client_app.app.database.db import client_engine
        from client_app.app.database.models import ServerConnection
        from sqlmodel.ext.asyncio.session import AsyncSession
        from sqlmodel import select
        
        async with AsyncSession(client_engine) as session:
            stmt = select(ServerConnection).where(ServerConnection.is_active == True)
            res = await session.exec(stmt)
            conn = res.first()
            return conn.license_key if conn else None

    async def _get_brain_client(self):
        """
        Returns (client, license_key).
        Always resolves to BrainAPIClient (Split or Monolith) to avoid direct imports.
        """
        # 1. Resolve License Key
        key = await self._get_active_license_key()
        
        # [FIX] Handle Seed Mismatch
        if not key or key in ["demo_key_123", "dev_key"]:
            key = "DEV_LICENSE_KEY_12345"
             
        # 2. Resolve URL from DB
        from client_app.app.database.models import ServerConnection
        async with AsyncSession(client_engine) as session:
            conn = await session.get(ServerConnection, "default")
            url = conn.brain_url if (conn and conn.brain_url) else "http://localhost:8080"
            return BrainAPIClient(base_url=url), key

    # --- CONFIGURATION METHODS (Delegated to Brain) ---
    # Client cannot access Server DB directly.


    # --- CONFIGURATION (Delegated to Brain) ---

    @audit_operation(action_type="anonymization", module="extraction_service")
    async def extract_with_ai(
        self,
        texto_fitz: str,
        texto_plumber: str,
        campos: List[str],
        config: dict,
        user_definition: str = ""
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Realiza la extracción de campos mediante IA asegurando la anonimización de datos PII.
        El flujo incluye: Anonimización -> Envío a Brain -> De-anonimización (rehidratación).

        Args:
            texto_fitz: Texto lineal extraído con PyMuPDF.
            texto_plumber: Texto con layout extraído con PDFPlumber.
            campos: Lista de nombres de campos a extraer.
            config: Configuración adicional (engine, file_path, etc.).

        Returns:
            Tupla (resultado_de_extraccion, estadisticas_privacidad).
        """
        try:
            file_path = config.get("file_path", "unknown.pdf")
            
            # 1. SIEMPRE anonimizar
            self._anonymizer = AnonymizationContext(locale="es_ES")
            
            texto_fitz_anon = self._anonymizer.anonymize(texto_fitz)
            texto_plumber_anon = self._anonymizer.anonymize(texto_plumber)
            
            # Log de auditoría (sin revelar datos)
            entity_count = len(self._anonymizer.fake_to_real)
            await enterprise_audit_service.log_pii_operation(
                operation="anonymize",
                pii_types={"entities": entity_count},
                method="regex+ner",
                module="extraction_service",
                source_description=file_path
            )

            if self.logger:
                self.logger.info(f"Anonimizadas {entity_count} entidades antes de enviar a IA")
            
            # 2. Llamar a IA con datos anonimizados
            client, license_key = await self._get_brain_client()
            
            import time
            t0_llm = time.time()
            resultado = await client.extract_data(
                file_path=file_path,
                user_definition=user_definition,
                target_fields=campos,
                usar_tier_2=config.get("usar_tier_2", False),
                texto_fitz=texto_fitz_anon,
                texto_plumber=texto_plumber_anon,
                license_key=license_key # Explicit license for API compat
            )
            print(f"[⏱️ Profiler] Extracción directa LLM (extract_with_ai): {time.time() - t0_llm:.2f}s")
            
            # 3. SIEMPRE rehidratar
            t0_rehid = time.time()
            resultado_clean = self._anonymizer.deanonymize(resultado)
            print(f"[⏱️ Profiler] Rehidratación de PII (extract_with_ai): {time.time() - t0_rehid:.2f}s")
            
            # Capturar estadisticas antes de limpiar
            stats = self._anonymizer.get_stats()
            
            if self.logger:
                self.logger.info("Resultado rehidratado con datos originales")
                
            return resultado_clean, stats
            
        finally:
            # 4. Limpiar contexto (seguridad)
            self._anonymizer = None

    async def get_available_services(self) -> Dict[str, str]:
        """
        Devuelve servicios de extracción disponibles desde la BD local del cliente.
        Incluye el servicio genérico y las configuraciones personalizadas del usuario.
        """
        services = [{"service_id": "GENERIC_LLM", "name": "Análisis Genérico (LLM)"}]

        # Leer configuraciones del usuario desde BD local
        async with AsyncSession(client_engine) as session:
            stmt = select(UserExtractionConfig)
            results = await session.exec(stmt)
            for c in results.all():
                services.append({
                    "service_id": c.service_id,
                    "name": c.name
                })

        # Convertir a Dict[id: name] para la UI
        return {s['service_id']: s['name'] for s in services}



    # --- USER CONFIG MANAGEMENT (CLIENT DB) ---
    
    async def get_all_user_configs(self) -> List[Dict]:
        """Devuelve todas las configuraciones de usuario desde client_local.db"""
        from client_app.app.database.models import UserExtractionConfig
        async with AsyncSession(client_engine) as session:
            stmt = select(UserExtractionConfig)
            results = await session.exec(stmt)
            return [c.model_dump() for c in results.all()]

    async def get_user_config(self, service_id: str) -> Optional[Dict]:
        from client_app.app.database.models import UserExtractionConfig
        async with AsyncSession(client_engine) as session:
            res = await session.get(UserExtractionConfig, service_id)
            return res.model_dump() if res else None

    async def save_user_config(self, config_data: Dict):
        from client_app.app.database.models import UserExtractionConfig
        async with AsyncSession(client_engine) as session:
            s_id = config_data.get("service_id")
            existing = await session.get(UserExtractionConfig, s_id)
            if existing:
                for k, v in config_data.items():
                    setattr(existing, k, v)
                session.add(existing)
            else:
                # Create new
                new_conf = UserExtractionConfig(**config_data)
                session.add(new_conf)
            await session.commit()

    # --- EXECUTION METHODS ---

    async def process_files(
        self, 
        file_paths: List[str], 
        service_id: str, 
        fase: int = 0, 
        user_definition: str = "",
        on_progress=None
    ) -> Dict[str, Any]:
        """
        Punto de entrada principal para procesar uno o varios archivos.
        Resuelve la estrategia de extracción (Genérica LLM o Servicio Específico).
        """
        # 1. Resolver Estrategia
        if service_id == "GENERIC_LLM":
            return await self.process_files_generic(
                file_paths, 
                on_progress=on_progress,
                recognize_all=True,
                user_definition=user_definition
            )
        
        # 2. Check for Generic Action (stored instructions)
        if service_id.startswith("gen_action_"):
            from client_app.app.database.models import UserExtractionConfig
            from client_app.app.database.db import client_engine
            from sqlmodel.ext.asyncio.session import AsyncSession
            
            async with AsyncSession(client_engine) as session:
                config = await session.get(UserExtractionConfig, service_id)
                if config and config.expected_schema.get('type') == 'generic_llm_action':
                    stored_instructions = config.expected_schema.get('instructions', "")
                    fields = [f.get('name') for f in config.expected_schema.get('fields', [])]
                    
                    combined_instructions = f"{stored_instructions}\n{user_definition}".strip()
                    
                    return await self.process_files_generic(
                        file_paths,
                        on_progress=on_progress,
                        target_fields=fields,
                        user_definition=combined_instructions
                    )

        return {"error": f"Servicio '{service_id}' no reconocido o no migrado."}

    async def suggest_fields_from_doc1(self, doc1_path: str, top_k: int = 15, on_progress=None, language_hint: str = 'es', allow_long: bool = False, sample_strategy: str = 'spread') -> Dict[str, Any]:
        """
        Analiza el primer documento (Doc1) para sugerir automáticamente campos a extraer.
        Implementa la 'Fase 0' (Discovery) con guardrails de seguridad y rendimiento.
        """
        if not doc1_path: return {"status": "no_doc", "fields": [], "top_k": top_k}
        
        # Thresholds (Defaults if settings not present)
        settings = getattr(self, 'settings', {})
        page_hard = settings.get('phase0_page_hard_limit', 50)
        page_warn = settings.get('phase0_page_warn_threshold', 10)
        sample_window = settings.get('phase0_sample_window', 12)

        try:
             # 1. Read Meta
             if on_progress: on_progress({"phase": "definition", "subphase": "reading", "message": f" Leyendo {Path(doc1_path).name}", "percent": 5})
             
             # Check pages first
             _, num_pages = await self.reader.get_pages_and_count(doc1_path)
             
             # 2. Guardrails
             if num_pages > page_hard and not allow_long:
                 if on_progress: on_progress({"phase": "definition", "subphase": "reading", "message": f"Muy largo ({num_pages} págs).", "percent": 100, "done": True})
                 return {"status": "too_long_hard", "fields": [], "top_k": top_k, "num_pages": num_pages}
             
             warn = (num_pages > page_warn)
             if warn:
                 if on_progress: on_progress({"phase": "definition", "subphase": "reading", "message": f"Muestreando ({sample_strategy})...", "percent": 10})
                 doc_text_a, doc_text_b = await self._sample_texts(doc1_path, sample_strategy, sample_window)
             else:
                 doc_text_a, doc_text_b, _ = await self.reader.read_dual(doc1_path)
             
             # 3. Analyze
             if on_progress: on_progress({"phase": "definition", "subphase": "analysis", "message": "Analizando estructura (Fase 0)", "percent": 25})
             
             client, license_key = await self._get_brain_client()
             desc_dual = await client.analyze_document_structure(
                 doc_text_a, doc_text_b, definicion_usuario="", service_id="sys_phase0_discovery", license_key=license_key
             )
             
             # 4. Merge & Limit
             merged_fields = DataConsolidator.merge_discovery_fields(desc_dual)
             fields = []
             for item in merged_fields:
                 fields.append({
                     "name": item["name"],
                     "score": item["score"],
                     "page_hint": item.get("page_hint")
                 })
                 
             fields = fields[:top_k]
             
             if on_progress: on_progress({"phase": "definition", "subphase": "analysis", "message": "Completado", "percent": 100, "done": True})
             return {"status": "ok", "fields": fields, "top_k": top_k, "num_pages": num_pages, "warn": warn}
             
        except Exception as e:
             print(f"[Suggest] Error: {e}")
             return {"status": "error", "fields": [], "error": str(e)}

    async def build_kv_snippet_window(self, doc_path: str, field_name: str, page_hint: Optional[int] = None, window: int = 3) -> str:
        """
        Construye un fragmento de texto (snippet) enfocado en pares clave-valor (KV)
        cercanos a un campo específico para ayudar en la recuperación de datos fallidos.
        """
        try:
            _, n = await self.reader.get_pages_and_count(doc_path)
            
            def _fuzzy(s: str) -> bool:
                return field_name.lower() in s.lower()

            target_pages = []
            if page_hint:
                 target_pages = list(range(max(1, page_hint-window), min(n, page_hint+window)+1))
            else:
                 target_pages = list(range(1, min(n, 6)+1))

            lines = []
            # First pass: collect relevant
            for p in target_pages:
                kv_pairs = await self.reader.read_page_kv(doc_path, p)
                for kv in kv_pairs:
                    if _fuzzy(kv["key"]) or _fuzzy(kv["value"]):
                        lines.append(f"{kv['key']}: {kv['value']} (p.{p})")
            
            # Fallback if empty: grab generic context from first target page
            if not lines and target_pages:
                 kv_pairs = await self.reader.read_page_kv(doc_path, target_pages[0])
                 for kv in kv_pairs[:10]:
                     lines.append(f"{kv['key']}: {kv['value']} (p.{target_pages[0]})")

            txt = "\n".join(lines)
            return txt[:8000]
        except Exception as e:
            # Error building KV snippet - silent fallback
            return ""

    async def get_doc_meta(self, doc_path: str) -> Dict[str, Any]:
        """Devuelve metadatos ligeros (num_pages)."""
        try:
            return {'num_pages': await self._safe_page_count(doc_path)}
        except Exception:
            return {'num_pages': 0}

    async def _safe_page_count(self, doc_path: str) -> int:
        try:
             _, n = await self.reader.get_pages_and_count(doc_path)
             return n
        except:
            return 0

    async def _sample_texts(self, doc_path: str, strategy: str, window: int, page_hints: List[int] = None) -> Tuple[str, str]:
        """
        Extrae muestras de texto de un documento extenso basándose en diferentes estrategias
        (spread, first, last, middle) para balancear contexto y límites de tokens.
        Inyecta obligatoriamente las `page_hints` si se proporcionan.
        """
        try:
             _, n = await self.reader.get_pages_and_count(doc_path)
             if n == 0: return "", ""
             
             w = max(1, int(window))
             
             if strategy == 'first': sel = list(range(1, min(w, n) + 1))
             elif strategy == 'last': sel = list(range(max(1, n - w + 1), n + 1))
             elif strategy == 'middle': 
                 start = max(1, int((n - w) / 2))
                 sel = list(range(start, min(n, start + w) + 1))
             else: # spread
                 if w >= n: sel = list(range(1, n + 1))
                 else:
                     step = n / (w + 1)
                     sel = sorted({max(1, min(n, int(round(step * (i + 1))))) for i in range(w)})
             
             # Inyectar las páginas requeridas por el usuario
             if page_hints:
                 for ph in page_hints:
                     # Validar límites
                     if 1 <= ph <= n and ph not in sel:
                         sel.append(ph)
                 
                 # Reordenar las páginas para mantener secuencialidad lógica
                 sel = sorted(list(set(sel)))
                 
             text_a_parts = []
             text_b_parts = []
             
             for p in sel:
                 a, b = await self.reader.read_page_dual(doc_path, page=p)
                 text_a_parts.append(a)
                 text_b_parts.append(b)
                 
             return "\n".join(text_a_parts), "\n".join(text_b_parts)
             
        except Exception as e:
             print(f"[Sampling] Error: {e}")
             # Fallback - límite ampliado para aprovechar contexto de LLMs modernos
             a, b, _ = await self.reader.read_dual(doc_path)
             return a[:150000], b[:150000]

    @audit_operation(action_type="extraction", module="extraction_service")
    async def process_files_generic(
        self, 
        file_paths: List[str], 
        on_progress=None, 
        target_fields: List[str] = None, 
        recognize_all: bool = False, 
        top_k: int = 15,
        user_definition: str = ""
    ) -> Dict:
        """
        Ejecuta el motor de extracción genérico guiado por LLM.
        Soporta tanto autodescubrimiento estructural como extracción dirigida por campos.
        """
        if not file_paths: return {}
        
        # 1. Validate Input
        if not target_fields and not recognize_all:
             return {'status': 'needs_fields', 'error': 'Debe especificar campos o activar autodescubrimiento.'}
             
        primer_pdf = file_paths[0]
        start_time = datetime.now()

        try:
            if on_progress: on_progress("Leyendo documento (OCR Dual)...")
            texto_a, texto_b, es_extenso = await run.io_bound(extraer_texto_dual, primer_pdf)
            
            # --- STEP 1: DISCOVERY (If needed) ---
            if recognize_all and not target_fields:
                if on_progress: on_progress("Analizando estructura para auto-descubrimiento...")
                
                client, license_key = await self._get_brain_client()
                desc_dual = await client.analyze_document_structure(
                    texto_a, texto_b, definicion_usuario="", service_id="sys_phase0_discovery", license_key=license_key
                )
                
                merged_fields = DataConsolidator.merge_discovery_fields(desc_dual)
                target_fields = [f['name'] for f in merged_fields[:top_k]]
                
                if not target_fields:
                     if on_progress: on_progress("No se detectaron campos automáticos.")
                     return DataConsolidator.consolidate_result({}, "generic-llm-empty", 1.0)
            
            # --- STEP 2: EXTRACTION (Phase 1) ---
            if on_progress: on_progress(f"Extrayendo {len(target_fields or [])} campos...")
            
            # Anonymized Extraction via extract_with_ai
            extraction_result, privacy_stats = await self.extract_with_ai(
                texto_fitz=texto_a,
                texto_plumber=texto_b,
                campos=target_fields,
                config={"file_path": primer_pdf, "usar_tier_2": False},
                user_definition=user_definition
            )

            # --- STEP 3: CONSOLIDATION ---
            if on_progress: on_progress("Generando resultados...")
            
            cleaned_result = extraction_result
            relevantes = cleaned_result.get('datos', cleaned_result) if isinstance(cleaned_result, dict) else cleaned_result
            clean_data = relevantes if isinstance(relevantes, dict) else {'datos': relevantes}
            
            consolidated = DataConsolidator.consolidate_result(
                clean_data=clean_data,
                source_engine="generic-llm-guided",
                confidence_score=0.9,
                processing_metadata={
                    "phase": "generic_guided",
                    "file_count": len(file_paths),
                    "processing_seconds": (datetime.now() - start_time).total_seconds(),
                    "fields_used": target_fields,
                    "privacy_stats": privacy_stats,
                    "_docs_text_anon": [{"fitz": texto_a, "plumber": texto_b}]
                }
            )
            
            return consolidated

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # --- REFINEMENT LOGIC (PHASE 1.5) ---

    async def refine_with_llm(self, file_path: str, current_data: Dict[str, Any], feedback: str, user_definition: str, service_id: str = "sys_phase1_refinement") -> Dict[str, Any]:
        """
        Orquesta el refinamiento de la extracción basado en feedback humano.
        Incluye limpieza de ruido (Smart Union/Filter) post-refinamiento.
        Aplica anonimización PII antes de enviar al LLM y rehidrata los resultados.
        """
        start_time = datetime.now()

        try:
            # 1. Leer Documento (Dual Mode)
            texto_a, texto_b, _ = await run.io_bound(extraer_texto_dual, file_path)

            # 2. ANONIMIZACIÓN: Proteger PII antes de enviar al LLM
            anonymizer = AnonymizationContext(locale="es_ES")
            texto_a_anon = anonymizer.anonymize(texto_a)
            texto_b_anon = anonymizer.anonymize(texto_b)
            # También anonimizar datos anteriores que podrían contener PII
            current_data_anon = anonymizer.anonymize(current_data)

            entity_count = len(anonymizer.fake_to_real)
            if self.logger:
                self.logger.info(f"[refine_with_llm] Anonimizadas {entity_count} entidades antes de enviar a IA")

            # Log de auditoría PII
            if entity_count > 0:
                await enterprise_audit_service.log_pii_operation(
                    operation="anonymize",
                    pii_types={"entities": entity_count},
                    method="regex+ner",
                    module="extraction_service.refine_with_llm",
                    source_description=file_path
                )

            # 3. Refinar con LLM (Fase 1.5) usando datos anonimizados
            client, license_key = await self._get_brain_client()
            import time
            t0_llm = time.time()
            refined_result_anon = await client.refine_extraction_data(
                texto_fitz=texto_a_anon,
                texto_plumber=texto_b_anon,
                datos_anteriores=current_data_anon,
                feedback_usuario=feedback,
                service_id=service_id,
                license_key=license_key
            )
            print(f"[⏱️ Profiler] Refinamiento interactivo LLM (refine_with_llm): {time.time() - t0_llm:.2f}s")

            # 4. REHIDRATACIÓN: Restaurar datos originales
            t0_rehid = time.time()
            refined_result = anonymizer.deanonymize(refined_result_anon)
            print(f"[⏱️ Profiler] Rehidratación de PII (refine_with_llm): {time.time() - t0_rehid:.2f}s")

            if self.logger:
                self.logger.info("[refine_with_llm] Resultado rehidratado con datos originales")
            
            # 3. Limpieza de Ruido (Semantic Filtering) - REMOVED
            # The user requested to remove 'clean_data_noise'.
            # We assume refinement is trustworthy.
            # print(f"[ExtractionService] 🧹 Applying Noise Filter to Refined Data...")
            cleaned_result = refined_result
            
            # 4. Consolidation
            relevantes = cleaned_result.get('relevantes', refined_result) if isinstance(cleaned_result, dict) else cleaned_result
            otros = {}
            
            clean_data = relevantes if isinstance(relevantes, dict) else {'datos': relevantes}
            
            consolidated = DataConsolidator.consolidate_result(
                clean_data=clean_data,
                source_engine="ai_refinement_tier2", # Refinement usually uses Logic Tier
                confidence_score=0.95, # Higher confidence after feedback
                processing_metadata={
                    "phase": "1.5 (Refinement)",
                    "processing_seconds": (datetime.now() - start_time).total_seconds(),
                    "ignored_fields": otros,
                    "feedback_used": True
                }
            )
            
            return consolidated

        except Exception as e:
             return {"status": "error", "error": f"Refinement Failed: {str(e)}"}


    # --- BATCH PROCESSING (PHASE 2) ---

    async def process_batch_with_llm(
        self,
        file_paths: List[str],
        validated_first_result: Dict[str, Any],
        user_definition: str,
        tier_level: int = 1,
        on_progress: Optional[callable] = None,
        execution_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta Lote via LLM en paralelo. Ideal para acciones genéricas.
        """
        print(f"[Batch] Starting LLM Batch with {len(file_paths)} files (Tier {tier_level})")
        
        # 1. Prepare Target Schema & Template
        # Try to find the business data (fields) in different possible structures
        if 'data' in validated_first_result:
            template_data = validated_first_result['data']
        elif 'datos' in validated_first_result:
            template_data = validated_first_result['datos']
        else:
            template_data = validated_first_result
            
        target_fields = [k for k in template_data.keys() if k not in ('metadata', 'status', 'meta', 'error', '_filename', 'filename')]
        
        # Ensure we have the clean fields only
        template_data = {k: template_data[k] for k in target_fields}
            
        print(f"[Batch] Using SCHEMA: {target_fields}")
        
        if not file_paths: return {"error": "No files provided"}

        print(f"[Batch] 🚀 Starting Batch for {len(file_paths)} files. Template Fields: {target_fields}")

        # Wrap first result in 'datos' format for Excel exporter compatibility
        first_path = file_paths[0] if file_paths else None
        first_filename = Path(first_path).name if first_path else 'unknown'
        wrapped_first_result = {
            "datos": template_data,  # already cleaned: only target_fields
            "archivo_origen": validated_first_result.get('filename', validated_first_result.get('_filename', first_filename)),
            "status": "success"
        }

        from collections import defaultdict

        # 2. First Result (Validated) — already wrapped above
        final_results = [wrapped_first_result]
        files_to_process = [p for p in file_paths if Path(p).name != first_filename]

        # Few-Shot & Anchors
        ejemplos_validacion = template_data

        # Derive Anchors for Escalation
        # Use local FieldDef class defined at module level
        field_defs = [FieldDef(name=k, example_value=v, description="", page_hint="", is_optional=True) for k, v in template_data.items()]
        anchors_meta = await self._derive_anchors_from_doc1(first_path, field_defs)
        print(f"[Batch] ⚓ Anchors Derived for {len(anchors_meta)} fields") 
        
        # 3. Concurrency & Counters
        sem = asyncio.Semaphore(4) 
        field_fail_counter = defaultdict(int)
        
        # 4. Worker Function
        async def _process_single_safe(file_path: str, idx: int):
            async with sem:
                try:
                    f_start = datetime.now()
                    fname = Path(file_path).name
                    if on_progress: on_progress(f"Iniciando: {fname}")

                    # A. Read
                    texto_a, texto_b, _ = await run.io_bound(extraer_texto_dual, file_path)

                    # B. ANONIMIZACIÓN: Proteger PII antes de enviar al LLM
                    anonymizer = AnonymizationContext(locale="es_ES")
                    texto_a_anon = anonymizer.anonymize(texto_a)
                    texto_b_anon = anonymizer.anonymize(texto_b)

                    # Log de auditoría PII
                    entity_count = len(anonymizer.fake_to_real)
                    if entity_count > 0:
                        await enterprise_audit_service.log_pii_operation(
                            operation="anonymize",
                            pii_types={"entities": entity_count},
                            method="regex+ner",
                            module="extraction_service.batch_llm",
                            source_description=fname
                        )

                    # C. Extract (Using Template Fields - STRICT) con datos anonimizados
                    client, license_key = await self._get_brain_client()

                    import time
                    t0_llm = time.time()
                    # Pasar textos anonimizados al LLM
                    raw_result_anon = await client.extract_data(
                        file_path=file_path,
                        user_definition=user_definition,
                        target_fields=target_fields,
                        usar_tier_2=(tier_level == 2),
                        ejemplos_validacion=ejemplos_validacion,
                        texto_fitz=texto_a_anon,
                        texto_plumber=texto_b_anon,
                        license_key=license_key
                    )
                    print(f"[⏱️ Profiler] Extracción por lotes LLM ({fname}): {time.time() - t0_llm:.2f}s")

                    # D. REHIDRATACIÓN: Restaurar datos originales
                    t0_rehid = time.time()
                    raw_result = anonymizer.deanonymize(raw_result_anon)
                    print(f"[⏱️ Profiler] Rehidratación de PII ({fname}): {time.time() - t0_rehid:.2f}s")

                    # E. Strict Local Filtering (Optimized)
                    # 1. Normalize Source Data
                    if isinstance(raw_result, dict) and 'datos' in raw_result:
                        source_data = raw_result['datos']
                    else:
                        source_data = raw_result if isinstance(raw_result, dict) else {}

                    # 2. Strict Filter by Schema
                    clean_data = DataConsolidator.filter_by_schema(source_data, target_fields)

                    # 3. Calculate Ignored Fields (Diff)
                    ignored_fields = {}
                    for k, v in source_data.items():
                        if k not in clean_data:
                            ignored_fields[k] = v

                    # F. ESCALATION LOGIC (Generic Guided) - con anonimización
                    for field in target_fields:
                        val = clean_data.get(field)
                        is_empty = not val or (isinstance(val, str) and not val.strip())

                        if is_empty:
                            field_fail_counter[field] += 1
                            if idx < 10 and field_fail_counter[field] >= 3 and field in anchors_meta:
                                print(f"[Batch] Escalating '{field}' for {fname}")
                                if on_progress: on_progress({"message": f"Escalando '{field}'...", "subphase": "fallback_generic"})

                                meta = anchors_meta[field]
                                window_text = await run.io_bound(extract_snippet_by_page, file_path, meta.get('page', 0), meta.get('anchor_hint'), 4000)

                                if window_text:
                                     # Anonimizar window_text antes de enviar al LLM
                                     window_text_anon = anonymizer.anonymize(window_text)
                                     client, license_key = await self._get_brain_client()
                                     gg = await client.extract_field_generic_guided(field, window_text_anon, license_key=license_key)
                                     if gg.format_ok and gg.val:
                                          # Rehidratar el valor recuperado
                                          recovered_val = anonymizer.deanonymize(gg.val)
                                          clean_data[field] = recovered_val
                                          print(f"[Batch] Recovered '{field}'")

                    # 4. Fill Missing Keys (Optional consistency)
                    for k in target_fields:
                        if k not in clean_data:
                            clean_data[k] = "" # Plain empty string for missing keys

                    # D. Consolidate
                    consolidated = DataConsolidator.consolidate_result(
                        clean_data=clean_data,
                        source_engine=f"ai_batch_tier{tier_level}+schema_filter",
                        confidence_score=0.9, # Higher confidence due to strict schema
                        processing_metadata={
                            "phase": "2 (Batch Optimized)",
                            "processing_seconds": (datetime.now() - f_start).total_seconds(),
                            "ignored_fields": ignored_fields 
                        }
                    )
                    
                    consolidated['filename'] = fname # Inject for Export
                    return consolidated
                    
                except Exception as e:
                    print(f"[Batch] ❌ Error processing {file_path}: {e}")
                    return {
                        "status": "error",
                        "filename": Path(file_path).name,
                        "error": str(e),
                        "data": {}
                    }
                finally:
                    if on_progress: on_progress(None) # Signal completion step
                    await asyncio.sleep(0) # Yield control to Event Loop
        
        # 5. Execute Parallel Tasks
        if files_to_process:
             tasks = [_process_single_safe(fp, i) for i, fp in enumerate(files_to_process)]
             batch_results = await asyncio.gather(*tasks)
             final_results.extend(batch_results)
             
        # 6. Export to Excel
        try:
             # Use clean name based on context or generic
             base_name = "Resultados_Extraccion"
             
             output_path, df_processed = await asyncio.to_thread(
                 formatear_excel_dual,
                 resultados_raw=final_results, 
                 nombre_archivo_base=base_name,
                 output_dir=output_dir_str
            )
             
             # Ensure Absolute Path
             abs_path = str(Path(output_path).resolve())
             
             error_count = sum(1 for r in final_results if r.get('status') == 'error')
             
             return {
                'success': True,
                'excel_path': abs_path, 
                'processed_count': len(final_results),
                'errors': error_count
            }
        except Exception as e:
             return {"status": "error", "error": f"Export Failed: {str(e)}"}


    async def execute_in_sandbox(self, code: str, file_paths: List[str]) -> Dict[str, Any]:
        """
        Ejecuta código generado en el Sandbox Seguro.
        Delega en SandboxExecutionService.
        """
        tmp_id = f"debug_{uuid.uuid4().hex[:8]}"
        return await self.sandbox.execute_in_sandbox(code, file_paths, tmp_id)

    async def process_batch_with_script(
        self,
        execution_id: str,
        script_code: str,
        validated_results: List[Dict[str, Any]],
        on_progress: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta el Script Generado en TODOS los archivos del lote.
        OPTIMIZACIÓN: Si los archivos de validación (input) ya están procesados en 'validated_results',
        no los re-calcula. Hace Merge.
        """
        try:
            # 1. Setup Environment
            exec_path = self.path_manager.get_execution_path(execution_id)
            input_dir = exec_path / "input"
            output_path = self.path_manager.get_output_dir(execution_id)
            
            files = [f for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']
            if not files:
                 return {"status": "error", "error": "No files to process"}

            print(f"[Batch] 🚀 Starting Production Batch for {len(files)} files via Script.")
            
            # 2. Identify Files to Process vs Merging
            # Create a Map of Validated Results by Filename for quick lookup
            # Expected validated_results structure: [{data:..., _filename: 'foo.pdf'}, ...]
            # Wait, `_filename` was injected in run_factory_pipeline for Audit. 
            # Let's ensure we use the correct key. In factory: cleaned_inner['_filename'] = fname
            
            validated_map = {}
            if validated_results:
                for item in validated_results:
                    # Depending on structure, filename might be in item or item['_filename']
                    fname = item.get('_filename') or item.get('filename')
                    if fname:
                        validated_map[fname] = item
            
            files_to_process = []
            final_results = []
            
            for f in files:
                fname = f.name
                if fname in validated_map:
                    print(f"[Batch] ⏩ Skipping {fname} (Already Validated)")
                    # Clean up _filename before final output if needed, or keep for consistency
                    # Make sure it matches structure of new results
                    cached = validated_map[fname]
                    # Ensure it has 'filename' key standard
                    cached['filename'] = fname 
                    final_results.append(cached)
                else:
                    files_to_process.append(str(f))
            
            # 3. Execute Remaining in Sandbox
            if files_to_process:
                if on_progress: on_progress(f"Procesando {len(files_to_process)} archivos restantes...")
                
                # We reuse execute_in_sandbox which returns {data: [results...]}
                # Note: execute_in_sandbox takes a LIST of paths.
                
                # Optimization: Should we chunk it? 
                # For now, pass all. The sandbox harness iterates.
                exec_result = await self.sandbox.execute_in_sandbox(
                    code=script_code,
                    file_paths=files_to_process,
                    execution_id=execution_id
                )
                
                if not exec_result.get('success'):
                     print(f"[Batch] ⚠️ Sandbox Warning: {exec_result.get('error')}")
                     # If generic error, we might have partial results?
                     # Currently harness returns all or error.
                     # If error, maybe we fail the batch? Or strict failure.
                     # Let's assume critical failure if harness fails.
                     return {"status": "error", "error": exec_result.get('error')}
                
                # Aggregate Results
                batch_data = exec_result.get('data', [])
                if isinstance(batch_data, list):
                    for item in batch_data:
                         # item: {filename, data, status}
                         if item.get('status') == 'success':
                             res_data = item.get('data', {})
                             res_data['filename'] = Path(item.get('filename', '')).name # Ensure standard key
                             final_results.append(res_data)
                         else:
                             # Setup Error Record
                             final_results.append({
                                 "filename": Path(item.get('filename', '')).name,
                                 "status": "error",
                                 "error": item.get('error')
                             })
            
            # 4. Export to Excel
            if on_progress: on_progress("Generando Excel final...")
            
            base_name = "Resultados_Finales_Factory"
            output_file, _ = await asyncio.to_thread(
                  formatear_excel_dual,
                  resultados_raw=final_results, 
                  nombre_archivo_base=base_name,
                  output_dir=str(output_path)
            )
             
            abs_path = str(Path(output_file).resolve())
            error_count = sum(1 for r in final_results if r.get('status') == 'error')
            
            # --- MANIFEST UPDATE ---
            try:
                # We need to construct RunManifest manually since it wasn't injected into service yet
                # ideally we call path_manager helper, but for now:
                from automatia_shared.core.execution_manager import RunManifest
                run_dir = self.path_manager.get_execution_path(execution_id)
                manifest = RunManifest(run_dir / "run_manifest.json")
                manifest.load()
                manifest.add_batch_run({
                    "batch_id": f"batch_{len(manifest.data.get('batch_runs', [])) + 1:04d}",
                    "files_count": len(files),
                    "processed_count": len(final_results),
                    "error_count": error_count,
                    "output_excel": abs_path,
                    "timestamp": datetime.now().isoformat(),
                    "status": "completed"
                })
            except Exception as e:
                print(f"[Batch] ⚠️ Failed to update manifest: {e}")
              
            return {
                'success': True,
                'excel_path': abs_path, 
                'processed_count': len(final_results),
                'errors': error_count,
                'data': final_results # Return data for UI if needed
            }

        except Exception as e:
             return {"status": "error", "error": f"Batch Execution Failed: {str(e)}"}



    # --- FACTORY PIPELINE (PHASE 3) ---

    def _normalize_script_result(self, extracted: dict, default_page: int = None) -> dict:
        """
        Convierte {campo: valor_primitivo|dict} a {campo: {valor, pagina?, source, confidence?}}
        Mantiene dicts que ya traigan 'valor'. Por defecto: source='script'.
        """
        normalized = {}
        for k, v in (extracted or {}).items():
            if isinstance(v, dict) and 'valor' in v:
                v2 = dict(v)
                v2.setdefault('source', 'script')
                normalized[k] = v2
            else:
                normalized[k] = {
                    'valor': v,
                    'pagina': default_page, 
                    'source': 'script'
                }
        return normalized

    async def _derive_anchors_from_doc1(self, filename: str, field_defs: List[FieldDef]) -> Dict[str, Dict]:
        """
        Locates the example values in Doc 1 to create 'Anchor Metadata' (Page, Context).
        This helps the fallback mechanism know WHERE to look in Doc 2.
        """
        anchors_meta = {}
        try:
            import fitz
            doc = fitz.open(filename)
            
            for fd in field_defs:
                target = fd.example_value
                if not target: continue
                
                # Search across pages
                for page_num, page in enumerate(doc):
                    text = page.get_text()
                    if target in text: 
                        idx = text.find(target)
                        start = max(0, idx - 50)
                        hint = text[start:idx].strip()
                        
                        anchors_meta[fd.name] = {
                            "page": page_num,
                            "anchor_hint": hint[-20:] if hint else target[:10] 
                        }
                        break
            doc.close()
        except Exception as e:
            print(f"[Factory] ⚠️ Error deriving anchors: {e}")
            
        return anchors_meta

    async def _apply_fallback_logic(self, brain_service, final_results: List[Dict], validation_files: List[Any], anchors_meta: Dict, field_defs: List[FieldDef], field_policies: Dict[str, Dict] = None, license_key: str = "TRIAL-KEY"):
        """
        Iterates over results, checks policies, and applies snippet fallback.
        Mutates final_results in place.
        Supports 'qa_policy': 'none'|'light'|'llm' and validation rules.
        """
        if not anchors_meta or not field_defs: return

        print("[Factory] 🛡️ Applying Snippet Fallback & QA Safety Net...")
        field_policies = field_policies or {}
        
        # Resolve 'validation' block in field_policies/schema if it exists
        # For now, we assume policies passed might have 'validation' key or we support separate validation map?
        # User spec says: rules come from UserExtractionConfig.expected_schema.validation
        # We assume 'field_policies' dictionary MIGHT containing validation rules or we pass them separately.
        # Let's assume field_policies structure: { "Field": { "fallback_policy":..., "qa_policy":..., "validation": {...rules...} } }
        # Or merged.
        
        for i, res_item in enumerate(final_results):
            if res_item.get('status') != 'success': continue
            
            raw_data = res_item.get('data', {})
            data_norm = self._normalize_script_result(raw_data)
            
            filename_key = res_item.get('filename')
            full_path = None
            for f in validation_files:
                if f.name == filename_key:
                    full_path = str(f)
                    break
            
            if not full_path: continue

            updated = False
            for fd in field_defs:
                name = fd.name
                policy = field_policies.get(name, {}) # Defaults handled inside
                fallback_mode = policy.get("fallback_policy", "on_fail")
                qa_mode = policy.get("qa_policy", "none")
                validation_rules = policy.get("validation", {})
                
                if fallback_mode == "never": continue
                
                # Current Value
                curr_obj = data_norm.get(name, {})
                val = curr_obj.get('valor')
                
                need_llm = False
                
                # Check 1: Empty/Missing
                is_empty = val is None or str(val).strip() == ""
                
                # Check 2: Light QA (Deterministic)
                qa_failed = False
                if not is_empty and qa_mode in ["light", "llm"]:
                     ok, _ = validate_field_value(name, val, validation_rules)
                     if not ok:
                          print(f"   >>> ⚠️ Field '{name}' failed Light QA. Value: '{val}'")
                          qa_failed = True
                
                # --- DECISION MATRIX ---
                # 1. ALWAYS
                if fallback_mode == "always":
                    need_llm = True
                    
                # 2. ON_FAIL (Default) or THRESHOLD
                elif fallback_mode in ["on_fail", "threshold"]:
                     # Trigger if Empty (Mandatory) OR QA Failed
                     if (not fd.is_optional and is_empty) or qa_failed:
                         need_llm = True
                     
                     # Threshold Logic
                     if fallback_mode == "threshold" and not need_llm and not is_empty:
                         th = float(policy.get("threshold", 0.95))
                         anchor = fd.example_value
                         if anchor and not _fuzzy_equal(str(val), anchor, th):
                             need_llm = True

                if need_llm and name in anchors_meta:
                    print(f"   >>> Fallback triggered for '{name}' (Policy: {fallback_mode}, QA: {qa_mode}) in {filename_key}")
                    hint_meta = anchors_meta[name]
                    
                    page_idx = hint_meta.get('page', 0)
                    anchor_hint = hint_meta.get('anchor_hint', '')
                    snippet = await run.io_bound(extract_snippet_by_page, full_path, page_idx, anchor_hint)
                    
                    if snippet:
                         llm_resp = await brain_service.analyze_snippet(name, snippet, expected_format=validation_rules.get("type", ""), license_key=license_key)
                         
                         # Check LLM Result
                         new_val = llm_resp.get('valor')
                         
                         # Re-run QA on LLM result if needed? 
                         # Architecture says: "Si venimos de LLM/snippet → escalar a rol “smartest” una sola vez; si vuelve a fallar, mantener vacío"
                         # analyze_snippet already does Tier 1 -> Tier 2 escalation on format failure.
                         # We trust analyze_snippet's "format_ok".
                         
                         if llm_resp.get('format_ok') and new_val:
                              print(f"   >>> ✅ Recovered: {new_val}")
                              data_norm[name] = llm_resp
                              updated = True
                         else:
                              # If failed, stick to original or empty?
                              # "si vuelve a fallar, mantener vacío/None según opcionalidad y registrar meta.warning"
                              pass
            
            res_item['data'] = data_norm

    async def run_factory_pipeline(self, execution_id: str, user_feedback: str = "", reference_data: Optional[Dict[str, Any]] = None, field_definitions: Optional[List[FieldDef]] = None, execution_options: Optional[Dict[str, Any]] = None, on_progress=None, force_discovery: bool = False) -> Dict[str, Any]:
        """
        Orquesta la factoría de generación de scripts de extracción deterministas.
        Flujo: Descubrimiento -> Generación de Script -> Auditoría de Seguridad ->
        Ejecución en Sandbox -> Validación de resultados -> Auto-reparación (opcional).

        Args:
            execution_id: ID de la ejecución actual.
            user_feedback: Comentarios del usuario para ajustar el comportamiento.
            reference_data: Datos de ejemplo proporcionados por el usuario.
            field_definitions: Especificación formal de los campos.
            execution_options: Opciones de motor y niveles de seguridad.
            on_progress: Callback para la interfaz.
            force_discovery: Si True, fuerza el descubrimiento LLM aunque haya field_definitions.

        Returns:
            Paquete con el script generado, informe de auditoría y resultados de prueba.
        """
        try:
            import time
            pipeline_start_t = time.time()
            
            # 1. SETUP & DATA RETRIEVAL
            if on_progress: on_progress({"message": "Preparando entorno y leyendo archivos...", "percent": 5})
            
            exec_path = self.path_manager.get_execution_path(execution_id)
            input_dir = exec_path / "inputs" 
            
            # Compatibility with old 'input' if exists
            if not input_dir.exists() and (exec_path / "input").exists():
                input_dir = exec_path / "input"
            
            
            files = [f for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']
            if not files:
                 return {"status": "error", "error": f"No PDF files found in {input_dir}"}
            
            # --- MULTI-FILE VALIDATION (TOP 2) ---
            validation_files = files[:2] 
            print(f"[Factory] Validando con {len(validation_files)} archivo(s).")
            
            # Read Texts for Brain Context
            # Read Texts for Brain Context
            t0 = time.time()
            
            async def _read_doc(vf_path):
                ta, tb, _ = await run.io_bound(extraer_texto_dual, str(vf_path))
                return {
                    "filename": vf_path.name,
                    "file_path": str(vf_path.absolute()),
                    "fitz": ta,
                    "plumber": tb
                }
                
            docs_text_list = await asyncio.gather(*[_read_doc(vf) for vf in validation_files])
            print(f"[⏱️ Profiler] Lectura OCR de {len(validation_files)} docs completada en {time.time() - t0:.2f}s")
            
            gc.collect()
            
            # Re-run Discovery on FIRST file
            if on_progress: on_progress({"message": "Analizando estructura documental...", "percent": 15})
            
            if not docs_text_list:
                 return {"status": "error", "error": f"Error leyendo archivos de validación."}

            client, license_key = await self._get_brain_client()

            # === REF DATA & FIELD DEFS ===
            target_fields = []
            values_example = None
            discovery_info = None  # Solo se usa en auto-descubrimiento

            # Auto-descubrimiento forzado por el usuario
            if force_discovery:
                print("[Factory] 🔍 Auto-descubrimiento activado por el usuario, ejecutando análisis LLM...")
                if on_progress:
                    on_progress({"message": "Descubriendo campos estructurados via LLM...", "percent": 15})
                
                t0_disc = time.time()
                desc_dual = await client.analyze_document_structure(
                    docs_text_list[0]["fitz"],
                    docs_text_list[0]["plumber"],
                    "",
                    license_key=license_key
                )
                print(f"[⏱️ Profiler] Fase 0 Auto-descubrimiento LLM: {time.time() - t0_disc:.2f}s")
                discovery_info = desc_dual

            if not field_definitions and reference_data:
                # Usuario proporcionó datos de referencia
                print(f"[Factory] 🎯 Usando datos validados por usuario como referencia ({len(reference_data)} campos).")
                target_fields = list(reference_data.keys())
                values_example = reference_data
                field_defs = [
                    FieldDef(name=k, description="", example_value=v, is_optional=False, page_hint="")
                    for k, v in reference_data.items()
                ]
            elif field_definitions:
                # Usuario proporcionó definiciones de campos
                print(f"[Factory] 🎯 Usando definiciones de campos pre-configuradas ({len(field_definitions)} campos).")
                field_defs = field_definitions
                target_fields = [fd.name for fd in field_defs]
                values_example = {fd.name: fd.example_value for fd in field_defs}
            elif not force_discovery:
                # Sin información del usuario y sin force_discovery → auto-descubrimiento via LLM
                print("[Factory] ⚠️ No hay datos de referencia, ejecutando auto-descubrimiento via LLM...")
                
                t0_disc = time.time()
                desc_dual = await client.analyze_document_structure(
                    docs_text_list[0]["fitz"],
                    docs_text_list[0]["plumber"],
                    "",
                    license_key=license_key
                )
                print(f"[⏱️ Profiler] Fase 0 Auto-descubrimiento LLM automático: {time.time() - t0_disc:.2f}s")
                
                discovery_info = desc_dual
                target_fields = DataConsolidator.merge_discovery_fields(desc_dual)
                field_defs = []
            else:
                # force_discovery ya ejecutado, sin field_definitions
                target_fields = DataConsolidator.merge_discovery_fields(discovery_info) if discovery_info else []
                field_defs = []
            
            # Derive Anchors for Fallback (Snippet Strategy)
            anchors_meta = {}
            if field_defs:
                 anchors_meta = await self._derive_anchors_from_doc1(str(validation_files[0]), field_defs)
                 print(f"[Factory] ⚓ Anchors Derived for {len(anchors_meta)} fields.")
            
            # ===================================================
            # CORE FACTORY PIPELINE PROCESS
            # ===================================================

            # --- ANONYMIZATION PHASE ---
            from client_app.app.services.anonymization_service import AnonymizationService
            anon_service = AnonymizationService()
            
            if on_progress: on_progress({"message": "Anonimizando PII para generación segura...", "percent": 20})
            
            docs_text_list_anon = []
            anon_mappings = {}
            
            # Parsear las páginas requeridas del usuario desde field_defs para el muestreo
            extracted_page_hints = []
            if field_defs:
                for fd in field_defs:
                    if fd.page_hint:
                        # Permite formatos como "1", "1,3,5"
                        parts = fd.page_hint.replace(' ', '').split(',')
                        for part in parts:
                            if part.isdigit():
                                extracted_page_hints.append(int(part))
            
            # Quitar repetidos para ser eficientes
            extracted_page_hints = list(set(extracted_page_hints))
            
            async def _anonymize_doc(idx, doc):
                t0_anon = time.time()
                filename = doc.get("filename", f"Doc_{idx}.pdf")
                if "file_path" in doc:
                    texto_fitz, texto_plumber = await self._sample_texts(
                        doc["file_path"], strategy="spread", window=30, page_hints=extracted_page_hints
                    )
                    MAX_CHARS = 150000
                    if len(texto_fitz) > MAX_CHARS:
                        texto_fitz = texto_fitz[:MAX_CHARS//2] + "\n...[TRUNCATED]...\n" + texto_fitz[-MAX_CHARS//2:]
                    if len(texto_plumber) > MAX_CHARS:
                        texto_plumber = texto_plumber[:MAX_CHARS//2] + "\n...[TRUNCATED]...\n" + texto_plumber[-MAX_CHARS//2:]
                else:
                    tf = doc.get('fitz', '')
                    tp = doc.get('plumber', '')
                    MAX_CHARS_FALLBACK = 150000

                    texto_fitz = tf[:MAX_CHARS_FALLBACK//2] + "\n...[TRUNCATED]...\n" + tf[-MAX_CHARS_FALLBACK//2:] if len(tf) > MAX_CHARS_FALLBACK else tf
                    texto_plumber = tp[:MAX_CHARS_FALLBACK//2] + "\n...[TRUNCATED]...\n" + tp[-MAX_CHARS_FALLBACK//2:] if len(tp) > MAX_CHARS_FALLBACK else tp

                res_f = await anon_service.anonymize_text(texto_fitz)
                res_p = await anon_service.anonymize_text(texto_plumber)

                # Capturar estructura de formulario detectada (anclas como "Nombre:", "Apellidos:")
                # Esto ayuda a la IA a entender que campos separados deben combinarse
                form_hint_f = res_f.get("form_structure_hint")
                form_hint_p = res_p.get("form_structure_hint")
                # Usar el hint más completo (el que tenga más información)
                form_structure_hint = form_hint_f or form_hint_p

                print(f"[⏱️ Profiler] Anonimización de {filename}: {time.time() - t0_anon:.2f}s")
                return {
                     "filename": filename,
                     "fitz": res_f.get("anonymized_text", ""),
                     "plumber": res_p.get("anonymized_text", ""),
                     "mappings": {**res_f.get("mapping", {}), **res_p.get("mapping", {})},
                     "form_structure_hint": form_structure_hint
                }

            anon_results = await asyncio.gather(*[_anonymize_doc(idx, doc) for idx, doc in enumerate(docs_text_list)])

            # Recopilar hints de estructura de formulario de todos los documentos
            form_structure_hints = []
            for res_meta in anon_results:
                docs_text_list_anon.append({
                     "filename": res_meta["filename"],
                     "fitz": res_meta["fitz"],
                     "plumber": res_meta["plumber"]
                })
                anon_mappings.update(res_meta["mappings"])
                # Capturar hint de estructura si existe
                if res_meta.get("form_structure_hint"):
                    form_structure_hints.append(res_meta["form_structure_hint"])

            # Usar el primer hint válido (asumiendo estructura similar entre documentos)
            combined_form_hint = form_structure_hints[0] if form_structure_hints else None
            if combined_form_hint:
                print(f"[Factory] 📋 Estructura de formulario detectada:\n{combined_form_hint[:200]}...")
            # === DEBUG: Log anonymized data sent to LLM ===
            try:
                import os
                from datetime import datetime as dt
                debug_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'logs')
                os.makedirs(debug_dir, exist_ok=True)
                debug_file = os.path.join(debug_dir, f'llm_anonymized_input_{dt.now().strftime("%Y%m%d_%H%M%S")}.txt')
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write("=== DATOS ANONIMIZADOS ENVIADOS AL LLM ===\n\n")
                    total_chars = 0
                    for idx_d, doc_anon in enumerate(docs_text_list_anon):
                        fitz_text = doc_anon.get('fitz', '')
                        plumber_text = doc_anon.get('plumber', '')
                        total_chars += len(fitz_text) + len(plumber_text)
                        f.write(f"--- Documento {idx_d + 1}: {doc_anon.get('filename', 'N/A')} ---\n")
                        f.write(f"[FITZ] ({len(fitz_text)} chars):\n{fitz_text[:5000]}\n\n")
                        f.write(f"[PLUMBER] ({len(plumber_text)} chars):\n{plumber_text[:5000]}\n\n")
                    f.write(f"\n=== TOTAL CARACTERES ENVIADOS: {total_chars} ===\n\n")
                    # El mapping NO se envía al LLM, solo mostrar estadísticas
                    f.write(f"=== ESTADÍSTICAS DE ANONIMIZACIÓN ===\n")
                    f.write(f"  Total de elementos anonimizados: {len(anon_mappings)}\n")
                    f.write(f"  Placeholders utilizados: {list(anon_mappings.keys())}\n")
                print(f"[Factory DEBUG] Datos anonimizados guardados en: {debug_file}")
            except Exception as e_debug:
                print(f"[Factory DEBUG] Error guardando log de anonimización: {e_debug}")

            # --- GENERATION LOOP (Validation & Auto-Healing) ---
            max_attempts = 2
            current_script = ""
            best_result = None
            validation_errors = {}

            # Preparar feedback enriquecido con estructura de formulario detectada
            # Esto ayuda a la IA a entender campos separados que deben combinarse
            enriched_feedback = user_feedback or ""
            if combined_form_hint:
                enriched_feedback = f"{combined_form_hint}\n\n{enriched_feedback}" if enriched_feedback else combined_form_hint

            for attempt in range(1, max_attempts + 1):
                if on_progress:
                    msg = f"Diseñando algoritmo (Intento {attempt}/{max_attempts})..." if attempt > 1 else f"Diseñando algoritmo de extracción..."
                    on_progress({"message": msg, "percent": 25 + (attempt - 1) * 10})

                # A. GENERATE SCRIPT
                if attempt == 1:
                    if on_progress: on_progress({"message": "Generando Script de Extracción Determinista (Brain)...", "percent": 35})

                    client, license_key = await self._get_brain_client()

                    t0_llm = time.time()
                    current_script_anon = await client.generate_extraction_script(
                        docs_text_list=docs_text_list_anon,
                        campos_objetivo=target_fields,
                        values_example=values_example,
                        info_discovery=discovery_info,
                        feedback=enriched_feedback if enriched_feedback else None,
                        field_definitions=[asdict(fd) for fd in field_defs] if field_defs else None,
                        license_key=license_key
                    )
                    print(f"[⏱️ Profiler] Generación Script LLM (Tier Principal): {time.time() - t0_llm:.2f}s")
                    
                    if on_progress: on_progress({"message": "Rehidratando PII en el script generado...", "percent": 40})
                    current_script = current_script_anon
                    for placeholder, original in anon_mappings.items():
                         current_script = current_script.replace(placeholder, str(original))
                    # Strip potential markdown code fences from LLM output
                    import re as _re
                    current_script = _re.sub(r'^\s*```(?:python)?\s*\n?', '', current_script.strip(), flags=_re.IGNORECASE)
                    current_script = _re.sub(r'\s*```\s*$', '', current_script.strip())
                    # PROMPT 8: Add to Script Library (Draft)
                    if current_script:
                        try:
                            await script_library_service.add_script(
                                source_module='extraction',
                                name=f"Extraction Script {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                code=current_script,
                                description=f"Auto-generated extraction script for fields: {target_fields[:5]}...",
                                tags=['extraction', 'generated'],
                                user_prompt=f"Target fields: {target_fields}",
                                source_metadata={'discovery_info': 'available'}
                            )
                        except Exception as e:
                            print(f"[Factory] Warning: Failed to save script to library: {e}")
                else:
                    # Auto-Healing / Refinement
                    if on_progress: on_progress({"message": "Auto-Reparando script con Tier de Supervisión...", "percent": 45})
                    doc1_text_anon = docs_text_list_anon[0]['fitz']
                    error_report = f"Validation Errors from previous attempt:\n{json.dumps(validation_errors, indent=2, ensure_ascii=False)}"
                    
                    # Se requiere uso explícito de inteligencia mayor en Refinamiento.
                    # Pasamos documento anonimizado para mantener seguridad, y el último log de fallos.
                    t0_llm_ref = time.time()
                    current_script_anon = await client.refine_script_with_error_logs(
                        script_actual=current_script_anon,
                        reporte_forense=error_report,
                        feedback_history=[], 
                        texto_documento=doc1_text_anon, 
                        target_fields=target_fields,
                        license_key=license_key
                    )
                    print(f"[⏱️ Profiler] LLM Auto-Heal (Intento {attempt}): {time.time() - t0_llm_ref:.2f}s")
                    
                    if on_progress: on_progress({"message": "Rehidratando script corregido...", "percent": 50})
                    current_script = current_script_anon
                    for placeholder, original in anon_mappings.items():
                         current_script = current_script.replace(placeholder, str(original))
                    
                    # Strip potential markdown code fences from LLM output
                    import re as _re
                    current_script = _re.sub(r'^\s*```(?:python)?\s*\n?', '', current_script.strip(), flags=_re.IGNORECASE)
                    current_script = _re.sub(r'\s*```\s*$', '', current_script.strip())
                    
                    # Update the anonymized version too for potential next iteration (though current_script_anon is usually fresh from LLM)
                    current_script_anon = current_script_anon # placeholder if we needed more processing

                # B. SECURITY AUDIT
                from automatia_shared.core.security import audit_code
                audit_result = audit_code(current_script)
                status = audit_result['status']
                reasons = audit_result['reasons']
                
                try:
                    self.path_manager.save_script_version(execution_id, current_script, security_status=status, logs=reasons)
                except Exception as e:
                     print(f"[Factory] ⚠️ Failed to version script: {e}")

                if status == 'CRITICAL':
                     return {"status": "error", "error": f"Security Critical Block: {reasons}", "code": current_script}
                
                if status == 'WARNING':
                     return {
                         "status": "action_required",
                         "action": "authorize_security",
                         "reasons": reasons,
                         "execution_id": execution_id,
                         "script_hash": hashlib.sha256(current_script.encode()).hexdigest()[:8],
                         "code": current_script
                     }
                
                # C. EXECUTE (SANDBOX) - Doc 1 Only for Validation (Fast Fail)
                if on_progress: on_progress({"message": "Ejecutando prueba en Sandbox (Doc 1)...", "percent": 55})
                
                doc1_path = str(validation_files[0])
                
                t0_sandbox = time.time()
                exec_result = await self.sandbox.execute_in_sandbox(
                    code=current_script,
                    file_paths=[doc1_path], 
                    execution_id=execution_id
                )
                print(f"[⏱️ Profiler] Ejecución en Sandbox Segura: {time.time() - t0_sandbox:.2f}s")
                
                if not exec_result.get('success'):
                     validation_errors = {"Runtime Error": exec_result.get('error')}
                     print(f"[Factory] ❌ Runtime Error on Attempt {attempt}: {exec_result.get('error')}")
                     continue # Retry loop
                
                # D. VALIDATE RESULTS
                extracted_data = {}
                batch_data = exec_result.get('data', [])
                if batch_data and isinstance(batch_data, list):
                     extracted_data = batch_data[0].get('data', {})
                elif isinstance(batch_data, dict):
                     extracted_data = batch_data
                
                if field_defs: 
                    is_valid, v_errors = validate_execution_results(extracted_data, field_defs)
                    
                    # USER LOGIC: 
                    # 1. First attempt must be 100% (is_valid == True) 
                    # 2. If it is 100%, we break (success)
                    # 3. If it's the first attempt and < 100%, we continue to Auto-Heal (Supervisor IA)
                    # 4. If it's the second attempt and success rate is > 40%, we accept it for human validation
                    
                    total_fields = len(field_defs)
                    failed_fields = len(v_errors)
                    success_rate = ((total_fields - failed_fields) / total_fields) * 100 if total_fields > 0 else 100

                    if is_valid:
                        print(f"[Factory] ✅ Validation Output PASS (100% success).")
                        best_result = (current_script, exec_result)
                        break 
                    elif attempt == 1:
                        print(f"[Factory] ❌ Attempt 1 failed ({success_rate:.1f}%). Triggering Auto-Heal (Supervisor IA)...")
                        validation_errors = v_errors
                        # Continue to Attempt 2
                    elif attempt == 2 and success_rate > 40:
                        print(f"[Factory] ⚠️ Attempt 2 below 100% but > 40% ({success_rate:.1f}%). Accepting for human validation.")
                        best_result = (current_script, exec_result)
                        break
                    else:
                        print(f"[Factory] ❌ Validation Output FAILED ({success_rate:.1f}%): {v_errors}")
                        validation_errors = v_errors
                        # Continue to next attempt if any
                else:
                    # No validation definitions, accept result
                    best_result = (current_script, exec_result)
                    break 

            # LOOP END
            
            if not best_result:
                 # If we have a script but specific validation failed, we might still return it with errors?
                 # Or treat as total failure.
                 # User said: "Si sigue fallando: ofrecer fallback por snippet (Prompt 5) o parar."
                 # Returning error for now with logs.
                 if current_script:
                      return {
                          "status": "error", 
                          "error": f"Validation Failed after {max_attempts} attempts.",
                          "code": current_script,
                          "meta": {"validation_errors": validation_errors},
                          "docs_text_list_anon": docs_text_list_anon,
                          "anon_mappings": anon_mappings
                      }
                 else:
                      return {"status": "error", "error": "Failed to generate script."}
            
            final_script, final_exec_result = best_result
            
            # Run remaining validation files if any (for Forensic Audit consistency check)
            if len(validation_files) > 1:
                 if on_progress: on_progress({"message": f"Validando resto de archivos ({len(validation_files)-1})...", "percent": 65})
                 remaining_files = [str(f) for f in validation_files[1:]]
                 extra_exec = await self.sandbox.execute_in_sandbox(
                     code=final_script,
                     file_paths=remaining_files,
                     execution_id=execution_id
                 )
                 # Merge results
                 if final_exec_result.get('data') and isinstance(final_exec_result['data'], list):
                      final_exec_result['data'].extend(extra_exec.get('data', []))
                 else:
                      # If first result wasn't a list (should be), normalize
                      final_exec_result['data'] = [final_exec_result.get('data')] + extra_exec.get('data', [])

            # Apply Fallback Logic (Service-Side Healing)
            if field_defs and anchors_meta:
                 # Check Fallback Timing (Default: Synchronous)
                 fallback_mode = "synchronous"
                 if reference_data and reference_data.get('fallback_mode') == 'deferred':
                      fallback_mode = 'deferred'
                 
                 if fallback_mode == 'synchronous':
                     if on_progress: on_progress({"message": "Verificando consistencia de datos (Fallback & Policy)...", "percent": 75})
                     # Load policies if available (TODO: Load from DB), for now default
                     field_policies = {} 
                     if reference_data and 'field_policies' in reference_data:
                          field_policies = reference_data['field_policies']
                     
                     await self._apply_fallback_logic(
                         client, 
                         final_exec_result.get('data', []), 
                         validation_files, 
                         anchors_meta, 
                         field_defs,
                         field_policies=field_policies,
                         license_key=license_key
                     )
                 else:
                     if on_progress: on_progress({"message": "Fallback diferido (omitido por config).", "percent": 75})


            # 4. ANALYSIS OF QUALITY AND CONSISTENCY (Forensic Audit)
            if on_progress: on_progress({"message": "Realizando análisis de calidad y consistencia...", "percent": 85})
            
            batch_data = final_exec_result.get('data', [])
            clean_results_list = []
            
            if isinstance(batch_data, list):
                for item in batch_data:
                    if item.get('status') == 'success':
                        fname = item.get('filename')
                        cleaned_inner = self._sanitize_for_audit(item.get('data', {}), target_fields)
                        if isinstance(cleaned_inner, dict):
                            cleaned_inner['_filename'] = fname
                        clean_results_list.append(cleaned_inner)
            else:
                 clean_results_list = [self._sanitize_for_audit(batch_data, target_fields)]
            
            referencia = {
                "campos_esperados": target_fields,
                "discovery_meta": discovery_info,
                "nota": "Validar que los valores VARÍEN entre documentos si son datos únicos."
            }
            if values_example:
                clean_reference_values = self._sanitize_for_audit(values_example, target_fields)
                referencia["valores_validos"] = clean_reference_values

            audit_report = await client.generate_forensic_audit(
                referencia_ia=referencia,
                resultado_script=clean_results_list,
                license_key=license_key
            )
            
            # 5. CONSOLIDATE PACKAGE
            if on_progress: on_progress({"message": "Finalizando...", "percent": 95})
            
            ui_preview_result = clean_results_list[0] if clean_results_list else {}
            
            # Re-validate final result for UI reporting
            final_report = {}
            if field_defs and ui_preview_result:
                _, final_errors = validate_execution_results(ui_preview_result, field_defs)
                # Structure: {field: {valid: bool, error: str}}
                for fd in field_defs:
                    is_err = fd.name in final_errors
                    final_report[fd.name] = {
                        "valid": not is_err,
                        "error": final_errors.get(fd.name),
                        "value": ui_preview_result.get(fd.name)
                    }

            return {
                "status": "success",
                "code": final_script,
                "result": ui_preview_result, 
                "batch_results": clean_results_list,
                "audit": audit_report,
                "execution_id": execution_id,
                "anchors": anchors_meta, # Return anchors for UI comparison
                "validation_report": final_report, # Detailed per-field status
                "docs_text_list_anon": docs_text_list_anon,
                "anon_mappings": anon_mappings
            }

        except Exception as e:
            # Handle billing errors by checking error message/type
            # In split mode, these errors come via HTTP 401/402 responses from BrainAPIClient
            error_msg = str(e).lower()
            error_type = type(e).__name__

            if "credit" in error_msg or "insufficient" in error_msg:
                return {"status": "error", "error": "billing_error_insufficient_credits", "is_billing": True}
            if "quota" in error_msg or "license" in error_msg or "expirada" in error_msg:
                return {"status": "error", "error": "billing_error_quota_exceeded", "is_billing": True}

            # Handle LLM provider errors (503 UNAVAILABLE, rate limits, etc.)
            if "503" in error_msg or "unavailable" in error_msg or "high demand" in error_msg:
                print(f"[Factory] LLM Provider Error: {e}")
                return {"status": "error", "error": "Error del proveedor LLM: El servicio está temporalmente no disponible (sobrecarga). Intenta más tarde o cambia el proveedor en el panel de administración."}

            if "429" in error_msg or "rate limit" in error_msg or "too many requests" in error_msg:
                print(f"[Factory] LLM Rate Limit Error: {e}")
                return {"status": "error", "error": "Error del proveedor LLM: Se excedió el límite de solicitudes. Espera unos minutos o cambia el proveedor."}

            if "api key" in error_msg or "authentication" in error_msg or "401" in error_msg:
                print(f"[Factory] LLM Auth Error: {e}")
                return {"status": "error", "error": "Error de autenticación LLM: Verifica la API key del proveedor en el panel de administración."}

            # Handle timeout errors with a clearer message
            if "timeout" in error_msg or "ReadTimeout" in error_type or "ConnectTimeout" in error_type:
                print(f"[Factory] Timeout error: {e}")
                return {"status": "error", "error": "Timeout: El servidor tardó demasiado en responder. Por favor, inténtalo de nuevo."}

            # Handle connection errors
            if "connect" in error_msg or "connection" in error_msg:
                print(f"[Factory] Connection error: {e}")
                return {"status": "error", "error": "Error de conexión: No se pudo conectar con el servidor. Verifica tu conexión."}

            # Handle 500 errors that may contain LLM info
            if "500" in error_msg or "internal server error" in error_msg:
                # Check if it's an LLM-related error
                if "google" in error_msg or "openrouter" in error_msg or "llm" in error_msg:
                    print(f"[Factory] LLM Server Error: {e}")
                    return {"status": "error", "error": f"Error del proveedor LLM: {str(e)}. Verifica la configuración en el panel de administración."}

            print(f"[Factory] Pipeline Failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}


    async def register_service(
        self,
        service_id: str,
        name: str,
        description: str,
        field_definitions: List[Dict],
        policies: Dict,
        options: Dict,
        code: str = ""
    ) -> bool:
        """
        Registra una configuración de extracción personalizada en la base de datos local.
        Sincroniza el robot con la biblioteca de scripts y realiza el sellado atómico del activo.

        Args:
            service_id: Identificador único del servicio.
            name: Nombre comercial del robot.
            description: Descripción funcional.
            field_definitions: Lista de campos configurados.
            policies: Políticas de fallback y QA.
            options: Opciones técnicas (motor, etc.).
            code: Código fuente Python si se trata de un robot determinista.
        """
        from sqlmodel import Session, select

        # Serialize Configuration
        schema_payload = {
            "fields": field_definitions,
            "policies": policies,
            "execution_options": options,
            "type": "deterministic_v2"
        }

        # PROMPT #4: Build precalculated contract
        engine = options.get('engine', 'fitz')
        precalculated_contract = build_extraction_contract(
            name=name,
            field_definitions=field_definitions,
            description=description,
            engine=engine
        )

        try:
            # Upsert Logic
            with Session(client_engine) as session:
                # Check existing
                existing = session.exec(
                    select(UserExtractionConfig).where(UserExtractionConfig.service_id == service_id)
                ).first()

                if existing:
                    existing.name = name
                    existing.description = description
                    existing.expected_schema = schema_payload
                    existing.updated_at = datetime.now()
                    session.add(existing)
                    print(f"[ExtractionService] Updated Custom Service: {service_id}")
                else:
                    new_svc = UserExtractionConfig(
                        service_id=service_id,
                        name=name,
                        description=description,
                        module="custom_extraction",
                        expected_schema=schema_payload
                    )
                    session.add(new_svc)

                session.commit()

            # PROMPT #4: Sync with ScriptLibrary
            if code:
                try:
                    # Convert DataContract to dict for JSON serialization
                    ui_contract_dict = {}
                    if precalculated_contract:
                        if hasattr(precalculated_contract, 'model_dump'):
                            ui_contract_dict = precalculated_contract.model_dump()
                        elif hasattr(precalculated_contract, 'dict'):
                            ui_contract_dict = precalculated_contract.dict()
                        elif isinstance(precalculated_contract, dict):
                            ui_contract_dict = precalculated_contract

                    library_script = await script_library_service.add_script(
                        source_module='extraction',
                        name=name,
                        code=code,
                        description=description or f"Robot de extracción: {name}",
                        tags=['extraction', 'factory', engine],
                        ui_contract=ui_contract_dict,
                        data_contract={},
                        source_automation_id=service_id,
                        source_metadata={
                            'engine': engine,
                            'field_count': len(field_definitions)
                        }
                    )
                    print(f"✅ Service synced to Library: {library_script.id}")

                    # Trigger Atomic Sealing
                    if library_script:
                        from client_app.app.services.asset_finishing_service import AssetFinishingService

                        async with AsyncSession(client_engine) as seal_session:
                            finishing_svc = AssetFinishingService(session=seal_session)
                            await finishing_svc.seal_resource(
                                script_id=library_script.id,
                                precalculated_contract=ui_contract_dict,
                                target_status='published'
                            )
                            print(f"✅ Atomic Seal applied to {library_script.id}")

                except Exception as lib_error:
                    print(f"⚠️ [register_service] Library sync warning: {lib_error}")

            return True

        except Exception as e:
            print(f"❌ [register_service] Error: {e}")
            return False

    async def list_custom_services(self) -> List[UserExtractionConfig]:
        """
        Lists all custom services registered by the user.
        """
        from sqlmodel import Session, select
        try:
             with Session(client_engine) as session:
                 statement = select(UserExtractionConfig)
                 results = session.exec(statement).all()
                 return results
        except Exception as e:
             print(f"[ExtractionService] Error listing services: {e}")
             return []

    async def execute_batch_background(
        self,
        service_id: str,
        files: List[str],
        on_progress: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Ejecuta un lote de archivos utilizando un servicio/script guardado en la biblioteca.
        Se ejecuta en segundo plano gestionando su propio execution_id.
        """
        try:
            from client_app.app.services.script_library_service import script_library_service
            from client_app.app.database.models import ScriptLibrary
            from client_app.app.database.db import client_engine
            from sqlmodel import select
            from sqlmodel.ext.asyncio.session import AsyncSession
            import shutil
            from pathlib import Path

            library_script = None
            try:
                # Si el service_id es directamente el ID numérico de ScriptLibrary
                script_id = int(service_id)
                library_script = await script_library_service.get_script(script_id)
            except ValueError:
                # Si el service_id viene como string alfanumérico (UserExtractionConfig.service_id)
                async with AsyncSession(client_engine) as session:
                    # Intentamos buscar por metadata JSON o nombre si el string es complejo
                    # Una forma directa y segura es buscar todos los de extracción y filtrar en memoria si SQLite JSON1 no está
                    all_extraction_scripts = await session.exec(select(ScriptLibrary).where(ScriptLibrary.source_module == 'extraction'))
                    for script in all_extraction_scripts:
                        meta = script.source_metadata if isinstance(script.source_metadata, dict) else {}
                        if script.source_automation_id == service_id or meta.get('service_id') == service_id:
                            library_script = script
                            # We need the code materialized, get_script does that
                            library_script = await script_library_service.get_script(script.id)
                            break
                            
            if not library_script or not library_script.code:
                return {"status": "error", "error": f"Script no encontrado o sin código para ID {service_id}"}
                
            script_code = library_script.code
            
            # Crear un execution_context ad-hoc
            execution_id = self.path_manager.create_execution_context(task_type='PDF_EXTRACTION')
            exec_path = self.path_manager.get_execution_path(execution_id)
            
            # Guardar el script para el batch runner
            script_dir = exec_path / "scripts"
            script_dir.mkdir(parents=True, exist_ok=True)
            script_file = script_dir / "script_current.py"
            with open(script_file, "w", encoding="utf-8") as f:
                f.write(script_code)
                
            # Copiar archivos al input_dir
            input_dir = self.path_manager.get_input_dir(execution_id)
            staged_files = []
            
            for fpath in files:
                src = Path(fpath)
                if src.exists():
                    dst = input_dir / src.name
                    if str(src.absolute()) != str(dst.absolute()):
                        shutil.copy2(str(src), str(dst))
                    staged_files.append(str(dst))
                    
            
            if on_progress:
                on_progress({'message': 'Preparando entorno de ejecución...', 'percent': 5})
                
            # Delegar a la ejecución existente
            res = await self.run_batch_execution(
                execution_id=execution_id,
                file_paths=staged_files,
                execution_options={'service_id': service_id},
                on_progress=on_progress
            )

            # --- UPDATE STATISTICS ---
            if res.get('status') == 'success' and library_script:
                try:
                    stats = {
                        'total': len(staged_files),
                        'success': sum(1 for r in res.get('batch_results', []) if r.get('status') == 'OK')
                    }
                    async with AsyncSession(client_engine) as stats_session:
                        # Refetch to ensure fresh state
                        db_script = await stats_session.get(ScriptLibrary, library_script.id)
                        if db_script:
                            db_script.execution_count += stats['total']
                            db_script.success_count += stats['success']
                            db_script.last_executed = datetime.utcnow()
                            stats_session.add(db_script)
                            await stats_session.commit()
                            print(f"📊 Stats updated for script {library_script.id}: +{stats['total']} execs, +{stats['success']} success")
                except Exception as stats_err:
                    print(f"⚠️ [Batch] Error updating script stats: {stats_err}")

            return res
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": f"Error en execute_batch_background: {e}"}

    async def run_batch_execution(self, execution_id: str, file_paths: Optional[List[str]] = None, execution_options: Optional[Dict[str, Any]] = None, on_progress: Optional[callable] = None) -> Dict[str, Any]:
        """
        Ejecuta un script de extracción sobre un lote de archivos con seguimiento granular.
        Permite notificar el progreso documento por documento a la interfaz de usuario.
        """
        import time
        
        # 0. Setup
        if not execution_options: execution_options = {}
        fallback_mode = execution_options.get('fallback_mode', 'synchronous')
        
        # 1. Get Script Code
        exec_path = self.path_manager.get_execution_path(execution_id)
        # Assuming script_current.py is the active one
        script_path = exec_path / "scripts" / "script_current.py"
        
        if not script_path.exists():
             # Fallback to verify if we can find any script version? 
             # Or assume run_factory_pipeline succceeded
             return {"status": "error", "error": f"No active script found for {execution_id}"}
             
        with open(script_path, 'r', encoding='utf-8') as f:
             current_code = f.read()

        # 2. Identify Files
        if not file_paths:
             input_dir = self.path_manager.get_input_dir(execution_id)
             if input_dir.exists():
                file_paths = [str(f) for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']
        
        if not file_paths:
             return {"status": "error", "error": "No files to process."}

        # 3. Output Container
        final_data_map = {}
        processed_count = 0
        total_files = len(file_paths)
        
        # 4. Loop with Concurrency (Semaphore)
        # Using a semaphore to limit sandbox processes
        sem = asyncio.Semaphore(4) 
        
        async def _process_single_doc(path: str):
            nonlocal processed_count
            fname = Path(path).name
            start_ts = time.time()
            
            # Event: Started
            if on_progress:
                on_progress({'filename': fname, 'status': 'STARTING', 'percent': int((processed_count/total_files)*100)})

            try:
                # A. Execute Script (Sandbox)
                # We execute PER FILE to get granular status
                exec_res = await self.sandbox.execute_in_sandbox(
                    code=current_code,
                    file_paths=[path],
                    execution_id=execution_id
                )
                script_data = {}
                if exec_res.get('success'):
                    # Unwrap list
                    raw_list = exec_res.get('data', [])
                    if raw_list and isinstance(raw_list, list):
                        script_data = raw_list[0].get('data', {})
                    else:
                        script_data = {}
                else:
                    # Script Error
                    pass

                # B. Validate & Fallback (if sync)
                llm_recovery_count = 0
                
                if fallback_mode == 'synchronous':
                    # Logic for determining fallback needed?
                    # We need field policies and anchors.
                    # For now, simplistic check: no data = bad
                    pass
                
                duration = time.time() - start_ts
                
                # Event: Finished
                # Count keys for stats
                n_script = len(script_data) if script_data else 0
                
                processed_count += 1
                if on_progress:
                    on_progress({
                        'filename': fname, 
                        'script_fields': n_script, 
                        'llm_fields': llm_recovery_count, 
                        'status': 'OK' if exec_res.get('success') else 'ERROR',
                        'duration': f"{duration:.1f}s",
                        'percent': int((processed_count/total_files)*100)
                    })
                
                # C. Log to DB for Dashboard
                await self.log_extraction(
                    filename=fname,
                    service_id=execution_options.get('service_id', 'batch_extraction'),
                    model='sandbox_python',
                    input_t=0, # No LLM tokens for direct script
                    output_t=0,
                    status='success' if exec_res.get('success') else 'error',
                    processing_time=duration,
                    result=script_data,
                    error_message=exec_res.get('error') if not exec_res.get('success') else None
                )

                return {'filename': fname, 'data': script_data, 'status': 'OK' if exec_res.get('success') else 'ERROR'}
                
            except Exception as e:
                print(f"Error processing {fname}: {e}")
                processed_count += 1 # Ensure progress continues even on crash
                if on_progress:
                    on_progress({'filename': fname, 'status': 'CRASH', 'error': str(e), 'percent': int((processed_count/total_files)*100)})
                return {'filename': fname, 'status': 'CRASH', 'error': str(e)}

        # Run All document tasks
        tasks = [_process_single_doc(p) for p in file_paths]
        results = await asyncio.gather(*tasks)
        
        # 5. Consolidate & Normalize for Excel/UI
        # We need a list of results for the exporter
        batch_results_list = []
        data_map = {}
        
        for r in results:
             filename = r['filename']
             raw_data = r.get('data', {})
             
             # Normalize simple KV to metadata-rich dict if needed
             # {Key: Val} -> {Key: {valor: Val, source: 'script'}}
             normalized_data = {}
             for k, v in raw_data.items():
                 if isinstance(v, dict) and 'valor' in v:
                     normalized_data[k] = v
                 else:
                     normalized_data[k] = {
                         'valor': v,
                         'source': 'script', # Default to script if raw
                         'confidence': 1.0,
                         'pagina': None
                     }
             
             data_map[filename] = normalized_data
             batch_results_list.append({
                 'filename': filename,
                 'data': normalized_data,
                 'status': r.get('status', 'ok')
             })

        # 6. Generate Excel
        output_dir = self.path_manager.get_output_dir(execution_id)
        excel_path, _ = await run.io_bound(
            formatear_excel_dual, 
            batch_results_list, 
            f"Resultados_Lote_{execution_id}", 
            str(output_dir)
        )
             
        return {
            'status': 'success', 
            'data': data_map, 
            'excel_path': str(excel_path),
            'batch_results': batch_results_list
        }

    async def resolve_pending_with_snippets(self, execution_id: str, batch_results: List[Dict], field_definitions: List[Dict], on_progress: Optional[callable] = None) -> Dict[str, Any]:
        """
        Post-processing step for 'Deferred' fallback mode.
        Iterates over results, identifies missing mandatory fields, and attempts to recover them using LLM + Snippets.
        """
        updated_results = []
        input_dir = self.path_manager.get_input_dir(execution_id)
        
        total_docs = len(batch_results)
        processed_count = 0
        
        # Helper to find definition
        def get_def(name):
            for f in field_definitions:
                if f['name'] == name: return f
            return None

        for item in batch_results:
            filename = item['filename']
            data = item.get('data', {})
            file_path = input_dir / filename
            
            changes_made = False
            
            # Check fields
            for field_def in field_definitions:
                fname = field_def['name']
                is_optional = field_def.get('is_optional', False)
                
                # Check if present and valid
                current_val = data.get(fname)
                val_content = None
                
                # Normalize check
                if isinstance(current_val, dict):
                    val_content = current_val.get('valor')
                else:
                    val_content = current_val
                
                # If missing (None or empty string) AND not optional (or strict policy?)
                # For now: if missing.
                if not val_content and val_content != 0: # 0 is valid
                     # Attempt Recovery
                     if file_path.exists():
                         try:
                             # 1. Get Context (KV Snippet)
                             # We need 'anchor' logic? Or just search by name?
                             # build_kv_snippet_window(pdf_path, field_name, ...)
                             # We assume field name is the key.
                             snippet = await self.build_kv_snippet_window(str(file_path), fname)
                             
                             if snippet:
                                 # 2. ANONIMIZACIÓN antes de enviar al LLM
                                 anonymizer = AnonymizationContext(locale="es_ES")
                                 snippet_anon = anonymizer.anonymize(snippet)

                                 # Log de auditoría PII
                                 entity_count = len(anonymizer.fake_to_real)
                                 if entity_count > 0:
                                     await enterprise_audit_service.log_pii_operation(
                                         operation="anonymize",
                                         pii_types={"entities": entity_count},
                                         method="regex+ner",
                                         module="extraction_service.recovery_snippet",
                                         source_description=filename
                                     )

                                 # 3. Ask LLM con datos anonimizados
                                 client, license_key = await self._get_brain_client()
                                 recovered_anon = await client.extract_field_generic_guided(snippet_anon, field_def, license_key=license_key)

                                 # 4. REHIDRATACIÓN del resultado
                                 recovered = anonymizer.deanonymize(recovered_anon)

                                 if recovered and recovered.get('valor'):
                                     # Update Data
                                     data[fname] = {
                                         'valor': recovered['valor'],
                                         'source': 'llm',
                                         'confidence': recovered.get('confidence', 0.8),
                                         'pagina': recovered.get('pagina'),
                                         'notas': 'Recovered via Snippet'
                                     }
                                     changes_made = True
                         except Exception as e:
                             print(f"Failed recovery for {fname} in {filename}: {e}")
            
            updated_results.append(item)
            processed_count += 1
            if on_progress:
                 on_progress({
                     'filename': filename,
                     'status': 'RECOVERING',
                     'percent': int((processed_count/total_docs)*100),
                     'changes': changes_made
                 })

        # Re-Generate Excel
        data_map = {r['filename']: r['data'] for r in updated_results}
        
        output_dir = self.path_manager.get_output_dir(execution_id)
        excel_path, _ = await run.io_bound(
            formatear_excel_dual, 
            updated_results, 
            f"Resultados_Lote_Resolved_{execution_id}", 
            str(output_dir)
        )

        return {
            'status': 'success',
            'data': data_map,
            'excel_path': str(excel_path),
            'batch_results': updated_results
        }


    async def auto_heal_current_script(self, execution_id: str, validation_report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs a targeted refinement iteration to fix specific validation errors.
        Triggered manually from UI.
        """
        try:
            print(f"[AutoHeal] 🚑 Starting Repair for Execution: {execution_id}")
            
            # 1. Load Context
            exec_path = self.path_manager.get_execution_path(execution_id)
            current_script = self.path_manager.load_latest_script(execution_id)
            if not current_script:
                 return {"status": "error", "error": "No script found to repair."}
            
            # Load Doc 1 text (cached or re-read)
            # For simplicity, we assume inputs exist
            input_dir = exec_path / "inputs" 
            if not input_dir.exists() and (exec_path / "input").exists():
                 input_dir = exec_path / "input"
            
            files = [f for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']
            if not files:
                 return {"status": "error", "error": f"No files in context."}
            
            doc1_path = str(files[0])
            ta, tb, _ = await run.io_bound(extraer_texto_dual, doc1_path)

            # ANONIMIZACIÓN: Proteger PII antes de enviar al LLM
            anonymizer = AnonymizationContext(locale="es_ES")
            ta_anon = anonymizer.anonymize(ta)

            # Log de auditoría PII
            entity_count = len(anonymizer.fake_to_real)
            if entity_count > 0:
                await enterprise_audit_service.log_pii_operation(
                    operation="anonymize",
                    pii_types={"entities": entity_count},
                    method="regex+ner",
                    module="extraction_service.auto_heal",
                    execution_id=execution_id
                )

            # 2. Build Error Report for AI
            # validation_report is {field: {valid, error, value}}
            # Filter only errors
            active_errors = {k: v for k, v in validation_report.items() if not v.get('valid')}
            if not active_errors:
                 return {"status": "success", "message": "No errors to fix.", "code": current_script}

            error_msg = f"User Request Auto-Heal. Active Validation Errors:\n{json.dumps(active_errors, indent=2)}"

            # 3. Call AI Refinement con texto anonimizado
            target_fields = list(validation_report.keys())

            client, license_key = await self._get_brain_client()

            new_script_anon = await client.refine_script_with_error_logs(
                script_actual=current_script,
                reporte_forense=error_msg,
                feedback_history=["User clicked Auto-Heal"],
                texto_documento=ta_anon,
                target_fields=target_fields,
                license_key=license_key
            )

            # REHIDRATACIÓN: Restaurar datos originales en el script
            new_script = anonymizer.deanonymize(new_script_anon)
            
            # 4. Audit & Save
            from automatia_shared.core.security import audit_code
            audit = audit_code(new_script)
            if audit['status'] == 'CRITICAL':
                 return {"status": "error", "error": f"Healed code unsafe: {audit['reasons']}"}
            
            self.path_manager.save_script_version(execution_id, new_script, logs=audit['reasons'])
            
            # 5. Execute & Re-Validate
            exec_result = await self.sandbox.execute_in_sandbox(new_script, [doc1_path], execution_id)
            
            if not exec_result.get('success'):
                 return {"status": "error", "error": f"Runtime Error in Healed Script: {exec_result.get('error')}"}
            
            # Extract data
            batch_data = exec_result.get('data', [])
            result_data = {}
            if batch_data:
                result_data = batch_data[0].get('data', {}) if isinstance(batch_data, list) else batch_data.get('data', {})
                
            return {
                "status": "success",
                "code": new_script,
                "result": result_data,
                "audit": audit
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _sanitize_for_audit(self, data: Any, target_fields: Optional[List[str]] = None) -> Any:
        """
        Limpia recursivamente el objeto de datos para la auditoría:
        - Elimina claves técnicas (blacklist).
        - Aplana estructuras {valor: X} si es relevante.
        - Filtra claves raíz si se pasa target_fields.
        """
        blacklist = {'status', 'success', 'error', 'filename', 'archivo_origen', 'pagina', 'page', 'confianza', 'confidence'}
        
        if isinstance(data, list):
            return [self._sanitize_for_audit(item) for item in data]
        
        if isinstance(data, dict):
            # 1. Filter Blacklist & Recursion
            clean_dict = {}
            for k, v in data.items():
                if k.lower() not in blacklist:
                    clean_dict[k] = self._sanitize_for_audit(v)
            
            # 2. Logic: Flatten {valor: ...}
            # Si tiene 'valor', y tras limpiar el resto no queda mucho más ruido...
            # La regla "si es el único dato relevante" es subjetiva. 
            # Simplificación: Si 'valor' existe, lo priorizamos como EL valor del campo.
            if 'valor' in clean_dict:
                return clean_dict['valor']
                
            # 3. Root Filter (Only applied if target_fields is passed AND we are likely at root)
            # This check is tricky effectively for recursion. 
            # We assume target_fields is only relevant for the ROOT dictionary of the extraction.
            # But since this is recursive, we can't easily know if we are at root.
            # WORKAROUND: Apply target_fields filtering OUTSIDE/BEFORE recursion?
            # Or pass 'is_root' flag? Let's use logic: if keys intersect significantly with target_fields?
            # Better: The caller calls this with target_fields ONLY for the root call.
            # But I can't change the signature of recursive calls easily without a helper.
            # Lets do strict filtering at the end of this function ONLY if target_fields is passed.
            # BUT wait, if I pass target_fields to recursive calls, it filters nested dicts too? bad.
            # So I should handle root filtering separate from recursion. Or assume target_fields is only passed to root.
            
            if target_fields:
                final_filtered = {}
                for k in target_fields:
                    if k in clean_dict:
                        final_filtered[k] = clean_dict[k]
                return final_filtered
                
            return clean_dict
            
        return data

    async def refine_factory_pipeline(self, execution_id: str, user_feedback: str, previous_code: str, audit_report: str = "", reference_data: Optional[Dict[str, Any]] = None, field_definitions: Optional[List[Any]] = None, docs_text_list_anon: Optional[List[Dict[str, str]]] = None, anon_mappings: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Orchestrates the Refinement Loop (Human-in-the-Loop).
        1. Brain: Refine Code (Tier 3).
        2. Executor: Run in Sandbox.
        3. Validate results and loop back to user if needed.
        """
        try:
            import time
            t0_pipeline = time.time()
            print(f"🔧 [Factory] Refining Pipeline for {execution_id}...")
            
            desc_dual = None # Initialize to avoid UnboundLocalError
            
            # 1. Prepare Data
            input_dir = self.path_manager.get_input_dir(execution_id)
            files = [f for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']
            if not files:
                 return {"status": "error", "error": f"No PDF files found in {input_dir}"}
            
            primer_pdf = files[0]
            
            from client_app.app.services.anonymization_service import AnonymizationContext
            anonymizer = AnonymizationContext(locale="es_ES")

            if docs_text_list_anon and anon_mappings:
                print(f"[Refine] Usando texto anonimizado de cache para evitar read OCR redundante.")
                texto_a_anon = docs_text_list_anon[0]['fitz']
                anonymizer.fake_to_real = anon_mappings
            else:
                t0_ocr = time.time()
                texto_a, _, _ = await run.io_bound(extraer_texto_dual, str(primer_pdf))
                print(f"[⏱️ Profiler] Lectura OCR (Refinement): {time.time() - t0_ocr:.2f}s")
                
                # ANONIMIZACIÓN: Proteger PII antes de enviar al LLM
                t0_anon = time.time()
                texto_a_anon = anonymizer.anonymize(texto_a)
                print(f"[⏱️ Profiler] Anonimización (Refinement): {time.time() - t0_anon:.2f}s")

                # Log de auditoría PII
                entity_count = len(anonymizer.fake_to_real)
                if entity_count > 0:
                    await enterprise_audit_service.log_pii_operation(
                        operation="anonymize",
                        pii_types={"entities": entity_count},
                        method="regex+ner",
                        module="extraction_service.refine_factory",
                        execution_id=execution_id
                    )

            # === CORRECTION: Use Reference Data if available OR Discovery ===
            if reference_data:
                print(f"[Refine] Usando referencia validada ({len(reference_data)} campos).")
                target_fields = list(reference_data.keys())
            elif field_definitions:
                print(f"[Refine] Usando field_definitions ({len(field_definitions)} campos).")
                target_fields = [f.name if hasattr(f, 'name') else f.get('name') for f in field_definitions]
            else:
                 # Fallback: Re-Run Discovery to ensure we have targets
                 print("[Refine] No referencia explicita ni field_definitions, re-calculando estructura basica para guiar la reparacion...")

                 client, license_key = await self._get_brain_client()

                 # Usar texto anonimizado para discovery
                 t0_disc = time.time()
                 desc_dual = await client.analyze_document_structure(texto_a_anon, "", "", license_key=license_key)
                 print(f"[⏱️ Profiler] Discovery LLM (Refinamiento): {time.time() - t0_disc:.2f}s")
                 target_fields = DataConsolidator.merge_discovery_fields(desc_dual)

            # 2. Refine Script (Brain) - con texto anonimizado
            feedback_history = [{"role": "user", "content": user_feedback}]

            if 'client' not in locals():
                 client, license_key = await self._get_brain_client()

            t0_llm = time.time()
            new_code_anon = await client.refine_script_with_error_logs(
                script_actual=previous_code,
                reporte_forense=audit_report,
                feedback_history=feedback_history,
                texto_documento=texto_a_anon,
                target_fields=target_fields,
                license_key=license_key
            )
            print(f"[⏱️ Profiler] Generación Script LLM (Refinamiento): {time.time() - t0_llm:.2f}s")

            # REHIDRATACIÓN: Restaurar datos originales en el script
            new_code = anonymizer.deanonymize(new_code_anon)
            
            # --- VERSIONING (Refinement) ---
            try:
                self.path_manager.save_script_version(execution_id, new_code)
            except Exception as e:
                 print(f"[Refine] ⚠️ Failed to version script: {e}")
            
            # 3. Execution (Sandbox)
            t0_sbx = time.time()
            exec_result = await self.sandbox.execute_in_sandbox(
                code=new_code,
                file_paths=[str(primer_pdf)],
                execution_id=execution_id
            )
            print(f"[⏱️ Profiler] Ejecución en Sandbox Segura (Refinamiento): {time.time() - t0_sbx:.2f}s")
            
            if not exec_result.get('success'):
                 return {"status": "error", "error": f"Runtime Error en el script refinado: {exec_result.get('error')}", "code": new_code}
            
            # 4. Validar resultados contra definiciones
            extracted_data = {}
            batch_data = exec_result.get('data', [])
            if batch_data and isinstance(batch_data, list):
                 extracted_data = batch_data[0].get('data', {})
                 
            validation_errors = {}
            final_report = {}
            is_valid_overall = True
            
            if field_definitions:
                # FieldDef is defined in this same file (extraction_service.py)
                try:
                     parsed_defs = [FieldDef(**fd) if isinstance(fd, dict) else fd for fd in field_definitions]
                except Exception:
                     parsed_defs = field_definitions
                     
                from client_app.app.ui.extraction_page import validate_execution_results
                is_valid_overall, validation_errors = validate_execution_results(extracted_data, parsed_defs)
                
                # Build report for UI
                for fd in parsed_defs:
                    fd_name = fd.name if hasattr(fd, 'name') else fd.get('name')
                    is_err = fd_name in validation_errors
                    final_report[fd_name] = {
                        "valid": not is_err,
                        "error": validation_errors.get(fd_name),
                        "value": extracted_data.get(fd_name)
                    }

            # --- MULTI-DOC PROCESSING (Ensure Doc 2 is processed in Refinement too) ---
            if len(files) > 1:
                print(f"[Refine] Procesando archivos adicionales para validación completa.")
                extra_files = [str(f) for f in files[1:2]] # Top 2
                extra_exec = await self.sandbox.execute_in_sandbox(
                    code=new_code,
                    file_paths=extra_files,
                    execution_id=execution_id
                )
                if exec_result.get('data') and isinstance(exec_result['data'], list):
                    exec_result['data'].extend(extra_exec.get('data', []))

            # USER LOGIC for Refinement: if success > 40%, we allow it
            total_fields = len(field_definitions) if field_definitions else 1
            failed_fields = len(validation_errors)
            success_rate = ((total_fields - failed_fields) / total_fields) * 100 if total_fields > 0 else 100

            if not is_valid_overall and success_rate <= 40:
                # Discrepancia detectada en Tier 3 y por debajo del umbral del 40%
                return {
                    "status": "error",
                    "error": f"El script refinado tiene una tasa de éxito muy baja ({success_rate:.1f}%).",
                    "code": new_code,
                    "meta": {"validation_errors": validation_errors},
                    "result": extracted_data,
                    "validation_report": final_report
                }
            
            # 5. Generar auditoría de éxito
            discovery_meta = desc_dual or {}
            referencia = {
                "campos_esperados": target_fields, 
                "discovery_meta": discovery_meta
            }
            clean_result = self._sanitize_for_audit(extracted_data, target_fields)
            
            new_audit = await client.generate_forensic_audit(
                referencia_ia=referencia,
                resultado_script=clean_result,
                license_key=license_key
            )
            
            # 5. Sanitize for UI Batch Preview (all docs including Doc 1)
            clean_batch_results = []
            if exec_result.get('data') and isinstance(exec_result['data'], list):
                for item in exec_result['data']:
                    # item is {'filename': ..., 'data': {...}, 'status': 'success'/'error'}
                    raw_item_data = item.get('data', {})
                    # Filter to only target fields if we have them
                    if target_fields and isinstance(target_fields[0], str):
                        cleaned = {k: raw_item_data.get(k) for k in target_fields if k in raw_item_data}
                    else:
                        cleaned = dict(raw_item_data)
                    cleaned['_filename'] = item.get('filename')
                    clean_batch_results.append(cleaned)

            return {
                "status": "success",
                "code": new_code,
                "result": extracted_data,
                "batch_results": clean_batch_results,
                "audit": new_audit,
                "validation_report": final_report,
                "execution_result": exec_result 
            }
            
        except Exception as e:
            print(f"❌ [Refine] Failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}

    async def refine_generic_pipeline(
        self, 
        execution_id: str, 
        user_feedback: str, 
        previous_data: Dict[str, Any],
        docs_text_list_anon: Optional[List[Dict[str, str]]] = None, 
        anon_mappings: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Refina datos de extracción genérica (Tier 2).
        No genera código, solo ajusta el JSON basado en feedback e inteligencia superior.
        """
        try:
            print(f"🔧 [Refine] Refining Generic Logic for {execution_id}...")
            
            # 1. Obtener texto (desde cache si es posible)
            texto_fitz = ""
            texto_plumber = ""

            if docs_text_list_anon and len(docs_text_list_anon) > 0:
                texto_fitz = docs_text_list_anon[0].get('fitz', "")
                texto_plumber = docs_text_list_anon[0].get('plumber', "")
                print("[Refine] Reutilizando texto anonimizado de cache.")
            else:
                # Fallback: leer primer doc del input
                input_dir = self.path_manager.get_input_dir(execution_id)
                files = [f for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']
                if not files:
                    return {"status": "error", "error": "No hay archivos para leer texto."}
                
                texto_fitz, texto_plumber, _ = await run.io_bound(extraer_texto_dual, str(files[0]))

            # 2. Llamar al cerebro (Tier 2)
            client, license_key = await self._get_brain_client()
            refined_data = await client.refine_extraction_data(
                texto_fitz=texto_fitz,
                texto_plumber=texto_plumber,
                datos_anteriores=previous_data,
                feedback_usuario=user_feedback,
                service_id="sys_phase1_refinement",  # Fixed: Use predefined system prompt ID
                license_key=license_key
            )
            
            return {
                "status": "success",
                "result": refined_data,
                "meta": {"method": "tier2_refinement"}
            }

        except Exception as e:
            print(f"❌ [Refine Generic] Error: {e}")
            return {"status": "error", "error": str(e)}

    async def deploy_generic_action(
        self,
        execution_id: str,
        service_name: str,
        instructions: str,
        field_definitions: List[Dict[str, Any]],
        description: str = ""
    ) -> Tuple[str, Optional[int], Optional[str]]:
        """
        Guarda una configuración de extracción genérica con instrucciones personalizadas.
        A diferencia de Factory, no guarda un .py, sino instrucciones en el expected_schema.
        Ahora también sincroniza con ScriptLibrary para tener README/Contrato.
        """
        from client_app.app.database.models import UserExtractionConfig
        from client_app.app.database.db import client_engine
        from datetime import datetime
        import uuid
        from sqlalchemy.ext.asyncio import AsyncSession
        from client_app.app.services.script_library_service import script_library_service
        from client_app.app.services.asset_finishing_service import AssetFinishingService, DOCS_DIR
        
        service_id = f"gen_action_{uuid.uuid4().hex[:6]}"
        
        schema_payload = {
            "fields": field_definitions,
            "instructions": instructions,
            "type": "generic_llm_action",
            "execution_id_origin": execution_id
        }
        
        async with AsyncSession(client_engine) as session:
            new_service = UserExtractionConfig(
                service_id=service_id,
                name=service_name,
                description=description or f"Acción genérica refinada ({service_name})",
                module=None,
                target_function=None,
                expected_schema=schema_payload,
                status="published",
                created_at=datetime.utcnow()
            )
            session.add(new_service)
            await session.commit()
            
        print(f"✅ Generic Action registered in DB: {service_id}")

        # Sync with ScriptLibrary to allow "Open Contract" (README)
        library_script_id = None
        readme_path = None
        
        try:
            async with AsyncSession(client_engine) as session:
                # Add to library as a "generic" resource (empty code)
                # We use the instructions as code or just a placeholder
                library_script = await script_library_service.add_script(
                    source_module='extraction',
                    name=service_name,
                    code=f"# Generic Action: {service_name}\n# Instructions:\n{instructions}",
                    description=description or f"Acción genérica: {service_name}",
                    tags=['extraction', 'generic', 'llm'],
                    ui_contract={"inputs": [], "outputs": field_definitions, "version": "1.0.0"},
                    data_contract={},
                    source_automation_id=service_id,
                    source_metadata={
                        'type': 'generic_llm',
                        'execution_id': execution_id,
                        'field_count': len(field_definitions)
                    }
                )
                library_script_id = library_script.id
                
                # Apply Atomic Sealing to generate README/Contract
                finishing_svc = AssetFinishingService(session=session)
                sealed_script = await finishing_svc.seal_resource(
                    script_id=library_script.id,
                    precalculated_contract={"inputs": [], "outputs": field_definitions, "version": "1.0.0"},
                    target_status='published'
                )
                
                if sealed_script and sealed_script.doc_path:
                    readme_path = str(DOCS_DIR / sealed_script.doc_path)
                
                print(f"✅ Generic Action synced to Library and Sealed: {library_script_id}")
        except Exception as e:
            print(f"⚠️ [Deployment] Library sync warning for generic action: {e}")

        return service_id, library_script_id, readme_path

    # --- DEPLOYMENT ---

    async def deploy_and_execute_batch(
        self,
        execution_id: str,
        service_name: str,
        script_code: str,
        all_files: List[str],
        first_file_result: Dict[str, Any],
        description: str = "",
        field_definitions: Optional[List[Dict[str, Any]]] = None,
        on_progress: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        1. Persist Script (Deploy) con contrato de datos.
        2. Run Batch on remaining files using the NEW script.
        3. Merge & Export to Excel.
        4. Generate documentation (README).
        """
        try:
            # 1. DEPLOY (Persist)
            if on_progress: on_progress("Guardando robot y configuración...")
            
            service_id = None
            library_script_id = None
            readme_path = None
            
            # Convertir field_definitions de FieldDef a dict si es necesario
            field_defs_dict = None
            if field_definitions:
                field_defs_dict = []
                for fd in field_definitions:
                    if hasattr(fd, 'name'):  # Es un FieldDef
                        field_defs_dict.append({
                            "name": fd.name,
                            "description": fd.description,
                            "example_value": fd.example_value,
                            "is_optional": fd.is_optional,
                            "page_hint": getattr(fd, 'page_hint', None)
                        })
                    else:  # Ya es un dict
                        field_defs_dict.append(fd)

            if script_code:
                # Escribir script al path esperado por deploy_script_to_production
                exec_path = self.path_manager.get_execution_path(execution_id)
                sb_script = exec_path / "sandbox" / f"script_{execution_id}.py"
                sb_script.parent.mkdir(parents=True, exist_ok=True)
                with open(sb_script, 'w', encoding='utf-8') as f:
                    f.write(script_code)

                service_id, library_script_id, readme_path = await self.deploy_script_to_production(
                    execution_id, service_name, description, field_definitions=field_defs_dict
                )
            else:
                # Generic Mode: No hay script code, guardamos la Acción Genérica
                print("[Deploy] Deploying Generic Action (Instructions Mode)")
                # Las instrucciones vienen del estado acumulado o la descripción
                # En el flujo de UI, las instrucciones se pasan usualmente en la descripción 
                # pero para ser robustos, si no hay script_code y estamos aquí, es una acción genérica.
                # NOTA: En el flujo actual, description contiene el feedback acumulado.
                service_id, library_script_id, readme_path = await self.deploy_generic_action(
                    execution_id, service_name, description, field_defs_dict, description
                )
            
            # 2. IDENTIFY REMAINING FILES
            # Filter out the one processed (first_file_result['filename'])
            first_fname = first_file_result.get('filename')
            if not first_fname and all_files:
                first_fname = Path(all_files[0]).name
            
            # Normalize to basename for robust comparison
            first_basename = Path(first_fname).name
            
            # Filter: Check if basename matches
            remaining_files = [f for f in all_files if Path(f).name != first_basename]
            
            print(f"[Deploy] Batch Processing: {len(remaining_files)} remaining files (Total: {len(all_files)}, first_file: {first_basename})")

            # 3. BATCH EXECUTE
            # Check script_code: if strictly empty/None, it's generic. 
            # But let's be more robust by checking if we have any script code OR if we used factory mode.
            is_generic = not script_code or script_code.strip() == ""
            if is_generic:
                # Generic Mode Batch (LLM-based)
                print("[Deploy] Starting LLM Batch for Generic Action")
                batch_res = await self.process_batch_with_llm(
                    file_paths=all_files,
                    validated_first_result=first_file_result,
                    user_definition=description, # Instructions
                    tier_level=1,
                    on_progress=on_progress,
                    execution_id=execution_id
                )
                # process_batch_with_llm returns a standard batch response with excel_path
                batch_res = batch_res or {}
                return {
                    "status": "success",
                    "service_id": service_id,
                    "library_script_id": library_script_id,
                    "readme_path": readme_path,
                    "script_name": service_name,
                    "processed_count": batch_res.get('processed_count', 0),
                    "excel_path": batch_res.get('excel_path'),
                    "errors": batch_res.get('errors', 0),
                    "contract_fields": [f['name'] for f in field_defs_dict] if field_defs_dict else [],
                    "contract_fields_count": len(field_defs_dict) if field_defs_dict else 0
                }

            # Factory Mode Batch (Sandbox-based)
            # Asegurar estructura correcta para el Excel (compatible con formatear_excel_dual)
            # first_file_result suele venir consolidado: {'status': 'ok', 'data': {...}, 'meta': {...}}
            factory_data = first_file_result.get('data', first_file_result.get('datos', first_file_result))
            first_wrapper = {
                "datos": factory_data,
                "archivo_origen": first_basename,
                "status": "success"
            }
            final_results = [first_wrapper]
            
            if remaining_files:
                if on_progress:
                    try:
                        on_progress(f"Procesando {len(remaining_files)} archivos restantes...")
                    except Exception as prog_err:
                        print(f"⚠️ [Deploy] Progress callback error: {prog_err}")

                # Concurrency
                sem = asyncio.Semaphore(10) # Optimized for Sandbox (CPU/IO)

                async def worker(fp):
                    try:
                        async with sem:
                            print(f"[Deploy] Processing file: {Path(fp).name}")
                            res = await self.sandbox.execute_in_sandbox(
                                code=script_code,
                                file_paths=[fp],
                                execution_id=f"{execution_id}_batch_{uuid.uuid4().hex[:4]}"
                            )
                            # Extract data part (execute_in_sandbox returns a list of results inside 'data')
                            raw_data = res.get('data', [])
                            extracted_data = {}
                            if isinstance(raw_data, list) and len(raw_data) > 0:
                                extracted_data = raw_data[0].get('data', {})
                            elif isinstance(raw_data, dict):
                                extracted_data = raw_data

                            # Envolver para compatibilidad con formatear_excel_dual
                            return {
                                "datos": extracted_data,
                                "archivo_origen": Path(fp).name,
                                "status": 'success' if res.get('success') else 'error'
                            }
                    except Exception as worker_err:
                        print(f"❌ [Deploy] Worker error for {Path(fp).name}: {worker_err}")
                        import traceback
                        traceback.print_exc()
                        return {
                            "datos": {},
                            "archivo_origen": Path(fp).name,
                            "status": "error",
                            "error": str(worker_err)
                        }

                tasks = [worker(f) for f in remaining_files]
                print(f"[Deploy] Created {len(tasks)} worker tasks")

                try:
                    batch_res = await asyncio.gather(*tasks, return_exceptions=True)
                    # Handle any exceptions returned by gather
                    processed_results = []
                    for i, res in enumerate(batch_res):
                        if isinstance(res, Exception):
                            print(f"❌ [Deploy] Task {i} returned exception: {res}")
                            processed_results.append({
                                "datos": {},
                                "archivo_origen": Path(remaining_files[i]).name if i < len(remaining_files) else "unknown",
                                "status": "error",
                                "error": str(res)
                            })
                        else:
                            processed_results.append(res)
                    final_results.extend(processed_results)
                except Exception as gather_err:
                    print(f"❌ [Deploy] Gather failed: {gather_err}")
                    import traceback
                    traceback.print_exc()
            
            # 4. EXPORT EXCEL
            if on_progress: on_progress("Generando Excel final...")
            
            # Use execution context for output
            output_dir = self.path_manager.get_output_dir(execution_id)
            base_name = f"Resultados_{service_name.replace(' ', '_')}"
            
            excel_path, _ = await run.io_bound(
                formatear_excel_dual,
                resultados_raw=final_results,
                nombre_archivo_base=base_name,
                output_dir=str(output_dir)
            )
            
            return {
                "status": "success",
                "service_id": service_id,
                "library_script_id": library_script_id if 'library_script_id' in locals() else None,
                "readme_path": readme_path if 'readme_path' in locals() else None,
                "excel_path": str(Path(excel_path).resolve()),
                "processed_count": len(final_results),
                "errors": sum(1 for r in final_results if r.get('status') == 'error')
            }

        except Exception as e:
            print(f"❌ [Deploy] Batch Failed: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}

    async def deploy_script_to_production(
        self,
        execution_id: str,
        service_name: str,
        description: str = "",
        field_definitions: Optional[List[Dict[str, Any]]] = None,
        engine: str = "fitz"
    ) -> str:
        """
        Promociona un script de Sandbox a Producción (Services Dir + Client DB).

        Prompt #4: Now integrates with ScriptLibrary and triggers Atomic Sealing
        to generate UIContract and README automatically.

        Args:
            execution_id: ID of the execution context
            service_name: User-friendly name for the service
            description: Description of what the service does
            field_definitions: List of field definitions for contract generation
                Each: {"name": str, "type": str, "description"?: str, "is_optional"?: bool}
            engine: Extraction engine used (fitz/pdfplumber)

        Returns:
            service_id: The unique ID of the deployed service
        """
        from client_app.app.database.models import UserExtractionConfig
        from client_app.app.database.db import client_engine

        # 1. Resolver Source Path (Sandbox)
        exec_path = self.path_manager.get_execution_path(execution_id)
        src_script = exec_path / "sandbox" / f"script_{execution_id}.py"

        if not src_script.exists():
            raise FileNotFoundError(f"Script temporal no encontrado en: {src_script}")

        # 2. Read script code for library sync
        with open(src_script, 'r', encoding='utf-8') as f:
            script_code = f.read()

        # 3. Generar Destination Path (Services)
        safe_name = "".join([c for c in service_name if c.isalnum() or c=='_']).lower()
        if not safe_name: safe_name = "service_unnamed"

        # Unique Filename: custom_{name}_{uuid}.py
        unique_suffix = uuid.uuid4().hex[:6]
        module_filename = f"custom_{safe_name}_{unique_suffix}"

        # Asegurar que el directorio de servicios existe (ruta absoluta para evitar problemas)
        services_dir_abs = Path(self.services_dir).resolve()
        services_dir_abs.mkdir(parents=True, exist_ok=True)
        dest_script = services_dir_abs / f"{module_filename}.py"

        # 4. Mover y Renombrar
        shutil.copy2(src_script, dest_script)
        print(f"[Deployment] Script deployed to: {dest_script}")

        # 5. Registrar en Client DB
        service_id = f"custom_{safe_name}_{unique_suffix}"
        library_script_id = None

        # PROMPT #4: Build contract from field definitions
        precalculated_contract = None
        if field_definitions:
            precalculated_contract = self.build_extraction_contract({
                "name": service_name,
                "fields": field_definitions,
                "description": description,
                "engine": engine
            })
            print(f"[Deployment] Contract built with {len(field_definitions)} output fields")

        try:
            async with AsyncSession(client_engine) as session:
                # Store field definitions in expected_schema
                schema_payload = {
                    "fields": field_definitions or [],
                    "engine": engine,
                    "type": "extraction"
                }

                new_service = UserExtractionConfig(
                    service_id=service_id,
                    name=service_name,
                    description=description or f"Deployed from Execution {execution_id}",
                    module=module_filename,
                    target_function="extraer_datos",
                    expected_schema=schema_payload,
                    status="published",
                    created_at=datetime.utcnow()
                )
                session.add(new_service)
                await session.commit()
                print(f"✅ Service registered in DB: {service_id}")

            # PROMPT #4: Sync with ScriptLibrary for unified catalog
            library_script = None
            readme_path = None  # Initialize before try block to avoid UnboundLocalError
            try:
                # Convert DataContract to dict for JSON serialization in SQLAlchemy
                ui_contract_dict = {}
                if precalculated_contract:
                    if hasattr(precalculated_contract, 'model_dump'):
                        ui_contract_dict = precalculated_contract.model_dump()
                    elif hasattr(precalculated_contract, 'dict'):
                        ui_contract_dict = precalculated_contract.dict()
                    elif isinstance(precalculated_contract, dict):
                        ui_contract_dict = precalculated_contract

                library_script = await script_library_service.add_script(
                    source_module='extraction',
                    name=service_name,
                    code=script_code,
                    description=description or f"Robot de extracción: {service_name}",
                    tags=['extraction', 'factory', engine],
                    ui_contract=ui_contract_dict,
                    data_contract={},
                    source_automation_id=service_id,
                    source_metadata={
                        'engine': engine,
                        'execution_id': execution_id,
                        'field_count': len(field_definitions) if field_definitions else 0
                    }
                )
                library_script_id = library_script.id
                print(f"✅ Script synced to Library: {library_script_id}")

                # PROMPT #4: Trigger Atomic Sealing with precalculated contract
                if library_script:
                    try:
                        from client_app.app.services.asset_finishing_service import AssetFinishingService, DOCS_DIR

                        async with AsyncSession(client_engine) as seal_session:
                            finishing_svc = AssetFinishingService(session=seal_session)
                            sealed_script = await finishing_svc.seal_resource(
                                script_id=library_script.id,
                                precalculated_contract=ui_contract_dict,
                                target_status='published'
                            )
                            print(f"✅ Atomic Seal applied to library script {library_script.id}")

                            # Extraer readme_path del script sellado
                            if sealed_script and sealed_script.doc_path:
                                readme_path = str(DOCS_DIR / sealed_script.doc_path)

                    except Exception as seal_error:
                        print(f"⚠️ [Deployment] Sealing warning: {seal_error}")
                        # Don't fail deployment if sealing fails

            except Exception as lib_error:
                print(f"⚠️ [Deployment] Library sync warning: {lib_error}")
                import traceback
                traceback.print_exc()
                # Log the error but continue - script is saved locally
                # The library_script_id will be None, which signals partial success

            return service_id, library_script_id, readme_path

        except Exception as e:
            print(f"❌ DB Registration failed: {e}")
            raise e
    
    # --- LOGGING ---

    async def log_extraction(self, filename: str, service_id: str, model: str, input_t: int, output_t: int, status: str, processing_time: float, result: Optional[Dict] = None, privacy_stats: Optional[Dict] = None, error_message: Optional[str] = None):
        """Registra la extracción en SQLite de forma segura."""
        try:
            async with AsyncSession(client_engine) as session:
                log_entry = ExtractionLog(
                    filename=filename,
                    service_used=service_id,
                    model_used=model,
                    input_tokens=input_t,
                    output_tokens=output_t,
                    status=status,
                    processing_time_seconds=processing_time,
                    extraction_result=result,
                    privacy_stats=privacy_stats,
                    error_message=error_message
                )
                session.add(log_entry)
                await session.commit()
        except Exception as e:
             # Silent fail for logging to avoid stopping the main process
             print(f"[ExtractionService] ⚠️ Error saving log to DB: {e}")

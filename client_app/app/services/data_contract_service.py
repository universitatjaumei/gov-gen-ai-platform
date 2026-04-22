
import json
import csv
import io
from typing import Dict, Any, List, Union, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from automatia_shared.contracts.ui_contract import InputType
from automatia_shared.enums import StepType


# ============================================================================
# DATA CONTRACTS - Estructuras para definir contratos de entrada/salida
# ============================================================================

@dataclass
class DataField:
    """Campo individual de un contrato de datos."""
    name: str
    type: str  # string, integer, number, boolean, date, datetime, object, array
    label: Optional[str] = None
    description: Optional[str] = None
    required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'type': self.type,
            'label': self.label or self.name,
            'description': self.description or '',
            'required': self.required
        }


@dataclass
class OutputContract:
    """Contrato de salida de un átomo - define qué datos produce."""
    fields: List[DataField] = field(default_factory=list)
    format: str = "json"  # json, csv, xml, binary
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'fields': [f.to_dict() for f in self.fields],
            'format': self.format,
            'description': self.description
        }


@dataclass
class InputContract:
    """Contrato de entrada de un átomo - define qué datos consume."""
    accepts_formats: List[str] = field(default_factory=lambda: ["json", "csv"])
    required_fields: List[DataField] = field(default_factory=list)
    optional_fields: List[DataField] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            'accepts_formats': self.accepts_formats,
            'required_fields': [f.to_dict() for f in self.required_fields],
            'optional_fields': [f.to_dict() for f in self.optional_fields],
            'description': self.description
        }


# ============================================================================
# CLASIFICACIÓN DE ÁTOMOS - Fuentes vs Consumidores
# ============================================================================

# Átomos FUENTE: producen datos que otros pueden consumir
SOURCE_ATOMS: Set[StepType] = {
    StepType.API_FETCH,      # Obtiene datos de APIs
    StepType.SQL_QUERY,      # Consulta bases de datos
    StepType.EMAIL,          # Recibe emails (legacy)
    StepType.CONNECTION,     # Conexión genérica que produce datos
    # --- Nuevos tipos de la taxonomía v2 ---
    StepType.FOLDER_WATCHER, # Monitorea carpetas (trigger con output)
    StepType.EMAIL_WATCHER,  # Monitorea bandeja (trigger con output)
    StepType.WEB_WATCHER,    # Monitorea páginas web (trigger con output)
    StepType.FOLDER_SCAN,    # Escaneo pasivo de carpeta (input)
    StepType.EMAIL_SCAN,     # Escaneo de emails por criterio (input)
    # WEBHOOK eliminado - No viable en instalaciones locales detrás de firewall
}

# Átomos CONSUMIDORES: procesan datos de entrada
CONSUMER_ATOMS: Set[StepType] = {
    StepType.EXTRACTION,     # Extrae campos de documentos
    StepType.ETL,            # Transforma datos
    StepType.ETL_TRANSFORM,  # Transformación específica
    StepType.RPA_EXECUTE,    # Automatización robótica
    StepType.REPORT_GENERATE,# Genera informes
    StepType.ANONYMIZATION,  # Anonimiza datos
    StepType.MASKING,        # Enmascara datos sensibles
    StepType.CUSTOM_SCRIPT,  # Script personalizado
    StepType.EMAIL_SEND,     # Envía emails (necesita contenido)
    StepType.SMTP,           # Envío SMTP (alias de EMAIL_SEND)
    # --- Nuevos tipos de la taxonomía v2 ---
    StepType.GRAPHICS,       # Genera gráficos/visualizaciones
    StepType.ARCHIVE_FILE,   # Archiva resultados en carpeta
    StepType.PDF_TOOLS,      # Procesa archivos PDF (merge, split, optimize)
    StepType.LLM_PROCESS,    # Procesamiento de texto con LLM
}


# ============================================================================
# MATRIZ DE COMPATIBILIDAD - Qué fuentes puede usar cada consumidor
# ============================================================================

# Formato: CONSUMER -> [lista de fuentes compatibles]
COMPATIBLE_SOURCES: Dict[StepType, Set[StepType]] = {
    StepType.EXTRACTION: {
        StepType.API_FETCH,
        StepType.EMAIL,
        StepType.FOLDER_SCAN,
        StepType.FOLDER_WATCHER,
        StepType.EMAIL_SCAN,
        StepType.EMAIL_WATCHER,
    },
    StepType.ETL: {
        StepType.API_FETCH,
        StepType.SQL_QUERY,
        StepType.EMAIL,
        StepType.EXTRACTION,  # También puede consumir salida de extracción
        StepType.CONNECTION,
    },
    StepType.ETL_TRANSFORM: {
        StepType.API_FETCH,
        StepType.SQL_QUERY,
        StepType.EMAIL,
        StepType.EXTRACTION,
        StepType.ETL,
        StepType.CONNECTION,
    },
    StepType.RPA_EXECUTE: {
        StepType.API_FETCH,
        StepType.SQL_QUERY,
        StepType.EMAIL,
        StepType.EXTRACTION,
        StepType.ETL,
        StepType.CONNECTION,
    },
    StepType.REPORT_GENERATE: {
        StepType.API_FETCH,
        StepType.SQL_QUERY,
        StepType.EXTRACTION,
        StepType.ETL,
        StepType.CONNECTION,
    },
    StepType.ANONYMIZATION: {
        StepType.API_FETCH,
        StepType.SQL_QUERY,
        StepType.EXTRACTION,
        StepType.ETL,
        StepType.CONNECTION,
    },
    StepType.MASKING: {
        StepType.API_FETCH,
        StepType.SQL_QUERY,
        StepType.EXTRACTION,
        StepType.ETL,
        StepType.CONNECTION,
    },
    StepType.CUSTOM_SCRIPT: {
        StepType.API_FETCH,
        StepType.SQL_QUERY,
        StepType.EMAIL,
        StepType.EXTRACTION,
        StepType.ETL,
        StepType.CONNECTION,
    },
    StepType.EMAIL_SEND: {
        StepType.EXTRACTION,
        StepType.ETL,
        StepType.REPORT_GENERATE,
    },
    StepType.SMTP: {
        StepType.EXTRACTION,
        StepType.ETL,
        StepType.REPORT_GENERATE,
        StepType.GRAPHICS,
    },
    # --- Nuevos tipos de la taxonomía v2 ---
    StepType.GRAPHICS: {
        StepType.API_FETCH,
        StepType.SQL_QUERY,
        StepType.EXTRACTION,
        StepType.ETL,
        StepType.ETL_TRANSFORM,
        StepType.FOLDER_SCAN,
        StepType.EMAIL_SCAN,
        StepType.CONNECTION,
    },
    StepType.ARCHIVE_FILE: {
        StepType.EXTRACTION,
        StepType.ETL,
        StepType.ETL_TRANSFORM,
        StepType.REPORT_GENERATE,
        StepType.GRAPHICS,
        StepType.CUSTOM_SCRIPT,
    },
    # PDF_TOOLS: Procesa archivos PDF desde fuentes que producen archivos
    StepType.PDF_TOOLS: {
        StepType.FOLDER_SCAN,      # Escaneo de carpetas con PDFs
        StepType.FOLDER_WATCHER,   # Monitoreo de carpetas
        StepType.EMAIL_SCAN,       # Emails con adjuntos PDF
        StepType.EMAIL_WATCHER,    # Monitoreo de emails
    },
    # LLM_PROCESS: Procesa texto con LLM desde múltiples fuentes
    StepType.LLM_PROCESS: {
        StepType.EMAIL_SCAN,       # Cuerpos de emails para resumir/analizar
        StepType.EMAIL_WATCHER,    # Emails monitoreados
        StepType.API_FETCH,        # Datos de APIs para procesar
        StepType.EXTRACTION,       # Datos extraídos para enriquecer
        StepType.ETL,              # Datos transformados
        StepType.CUSTOM_SCRIPT,    # Salida de scripts
    },
}


# ============================================================================
# SOPORTE DE CARGA MANUAL - Qué consumidores permiten subir archivos
# ============================================================================

# Tipos que soportan carga manual de archivos
MANUAL_UPLOAD_SUPPORT: Dict[StepType, List[str]] = {
    StepType.EXTRACTION: ["pdf", "docx", "xlsx", "csv", "txt", "json", "xml", "image"],
    StepType.ETL: ["csv", "xlsx", "json", "xml", "parquet"],
    StepType.ETL_TRANSFORM: ["csv", "xlsx", "json", "xml", "parquet"],
    StepType.RPA_EXECUTE: ["xlsx", "csv"],  # Excel para llenar formularios
    StepType.REPORT_GENERATE: ["csv", "xlsx", "json", "parquet"],
    StepType.ANONYMIZATION: ["csv", "xlsx", "json"],
    StepType.MASKING: ["csv", "xlsx", "json"],
    StepType.CUSTOM_SCRIPT: ["csv", "xlsx", "json", "txt", "xml", "parquet"],
    # --- Nuevos tipos de la taxonomía v2 ---
    StepType.GRAPHICS: ["csv", "xlsx", "json", "parquet"],  # Datos para visualizar
    StepType.PDF_TOOLS: ["pdf"],  # Solo archivos PDF
    StepType.LLM_PROCESS: ["txt", "csv", "xlsx", "json", "pdf"],  # Texto o datos para procesar con LLM
    # ARCHIVE_FILE no soporta carga manual - es un output que recibe de pasos anteriores
}


# ============================================================================
# CONTRATOS DE SALIDA POR DEFECTO - Qué produce cada tipo de átomo
# ============================================================================

DEFAULT_OUTPUT_CONTRACTS: Dict[StepType, OutputContract] = {
    StepType.API_FETCH: OutputContract(
        fields=[
            DataField("response_data", "object", "Datos de respuesta", "Objeto JSON con la respuesta de la API"),
            DataField("status_code", "integer", "Código de estado", "Código HTTP de la respuesta"),
            DataField("headers", "object", "Cabeceras", "Cabeceras de la respuesta"),
        ],
        format="json",
        description="Respuesta de una llamada a API externa"
    ),
    StepType.SQL_QUERY: OutputContract(
        fields=[
            DataField("rows", "array", "Filas", "Array de registros devueltos por la consulta"),
            DataField("columns", "array", "Columnas", "Lista de nombres de columnas"),
            DataField("row_count", "integer", "Cantidad", "Número de filas devueltas"),
        ],
        format="json",
        description="Resultado de consulta SQL"
    ),
    StepType.EMAIL: OutputContract(
        fields=[
            DataField("subject", "string", "Asunto", "Asunto del email"),
            DataField("from_address", "string", "Remitente", "Dirección del remitente"),
            DataField("body_text", "string", "Cuerpo texto", "Contenido en texto plano"),
            DataField("body_html", "string", "Cuerpo HTML", "Contenido en HTML"),
            DataField("attachments", "array", "Adjuntos", "Lista de archivos adjuntos"),
            DataField("received_at", "datetime", "Recibido", "Fecha de recepción"),
        ],
        format="json",
        description="Email recibido"
    ),
    # WEBHOOK eliminado - No viable en instalaciones locales detrás de firewall
    StepType.EXTRACTION: OutputContract(
        fields=[
            DataField("extracted_fields", "object", "Campos extraídos", "Campos definidos en el contrato"),
            DataField("confidence", "number", "Confianza", "Nivel de confianza de la extracción"),
            DataField("source_file", "string", "Archivo fuente", "Nombre del archivo procesado"),
        ],
        format="json",
        description="Datos extraídos de documentos"
    ),
    StepType.ETL: OutputContract(
        fields=[
            DataField("transformed_data", "array", "Datos transformados", "Datos después de la transformación"),
            DataField("record_count", "integer", "Registros", "Número de registros procesados"),
        ],
        format="json",
        description="Datos transformados por ETL"
    ),
    StepType.REPORT_GENERATE: OutputContract(
        fields=[
            DataField("report_url", "string", "URL del informe", "Enlace al informe generado"),
            DataField("report_data", "object", "Datos del informe", "Datos en formato estructurado"),
            DataField("format", "string", "Formato", "Formato del informe (pdf, xlsx, etc.)"),
        ],
        format="json",
        description="Informe generado"
    ),
    # --- Nuevos tipos de la taxonomía v2 ---
    StepType.FOLDER_WATCHER: OutputContract(
        fields=[
            DataField("file_path", "string", "Ruta completa", "Ruta completa del archivo detectado"),
            DataField("file_name", "string", "Nombre", "Nombre del archivo"),
            DataField("file_extension", "string", "Extensión", "Extensión del archivo"),
            DataField("file_size", "integer", "Tamaño", "Tamaño en bytes"),
            DataField("modified_at", "datetime", "Modificado", "Fecha de última modificación"),
        ],
        format="json",
        description="Archivo detectado en carpeta vigilada"
    ),
    StepType.EMAIL_WATCHER: OutputContract(
        fields=[
            DataField("subject", "string", "Asunto", "Asunto del email"),
            DataField("from_address", "string", "Remitente", "Dirección del remitente"),
            DataField("body_text", "string", "Cuerpo", "Contenido del mensaje"),
            DataField("attachments", "array", "Adjuntos", "Lista de archivos adjuntos"),
            DataField("received_at", "datetime", "Recibido", "Fecha de recepción"),
        ],
        format="json",
        description="Email detectado en bandeja vigilada"
    ),
    StepType.WEB_WATCHER: OutputContract(
        fields=[
            DataField("url", "string", "URL", "URL de la página monitoreada"),
            DataField("selector", "string", "Selector", "Selector CSS/XPath utilizado"),
            DataField("previous_content", "string", "Contenido anterior", "Contenido antes del cambio"),
            DataField("current_content", "string", "Contenido actual", "Contenido después del cambio"),
            DataField("change_detected_at", "datetime", "Detectado", "Fecha/hora de detección del cambio"),
            DataField("page_title", "string", "Título", "Título de la página web"),
        ],
        format="json",
        description="Cambio detectado en página web vigilada"
    ),
    StepType.FOLDER_SCAN: OutputContract(
        fields=[
            DataField("files", "array", "Archivos", "Lista de archivos encontrados"),
            DataField("total_count", "integer", "Total", "Número total de archivos"),
            DataField("total_size_bytes", "integer", "Tamaño total", "Tamaño total en bytes"),
            DataField("scan_path", "string", "Ruta escaneada", "Carpeta escaneada"),
            DataField("pattern", "string", "Patrón", "Patrón de filtro aplicado"),
        ],
        format="json",
        description="Resultado de escaneo de carpeta"
    ),
    StepType.EMAIL_SCAN: OutputContract(
        fields=[
            DataField("emails", "array", "Emails", "Lista de emails encontrados"),
            DataField("total_count", "integer", "Total", "Número total de emails"),
            DataField("attachments_downloaded", "integer", "Adjuntos", "Número de adjuntos descargados"),
            DataField("download_path", "string", "Ruta descargas", "Carpeta de descargas"),
            DataField("body_plain", "string", "Cuerpo texto", "Contenido en texto plano"),
            DataField("body_html", "string", "Cuerpo HTML", "Contenido en HTML"),
            DataField("subject", "string", "Asunto", "Asunto del email"),
            DataField("sender", "string", "Remitente", "Dirección del remitente"),
            DataField("date", "datetime", "Fecha", "Fecha y hora del email"),
        ],
        format="json",
        description="Resultado de escaneo de emails con contenido"
    ),
    StepType.SCHEDULER: OutputContract(
        fields=[
            DataField("job_id", "string", "ID de tarea", "Identificador de la tarea programada"),
            DataField("flow_id", "integer", "ID de flujo", "Flujo a ejecutar"),
            DataField("next_run", "datetime", "Próxima ejecución", "Fecha/hora de próxima ejecución"),
            DataField("schedule_type", "string", "Tipo", "Tipo de programación"),
        ],
        format="json",
        description="Ejecución programada de flujo"
    ),
    StepType.GRAPHICS: OutputContract(
        fields=[
            DataField("chart_type", "string", "Tipo de gráfico", "Tipo de visualización generada"),
            DataField("image_path", "string", "Ruta imagen", "Ruta al archivo de imagen generado"),
            DataField("data_points", "integer", "Puntos de datos", "Número de puntos visualizados"),
        ],
        format="json",
        description="Gráfico/visualización generada"
    ),
    StepType.ARCHIVE_FILE: OutputContract(
        fields=[
            DataField("destination_path", "string", "Destino", "Ruta donde se guardó el archivo"),
            DataField("file_name", "string", "Nombre", "Nombre del archivo guardado"),
            DataField("file_size_bytes", "integer", "Tamaño", "Tamaño del archivo en bytes"),
            DataField("operation", "string", "Operación", "Tipo de operación (copy/move)"),
        ],
        format="json",
        description="Archivo archivado en destino"
    ),
    StepType.LLM_PROCESS: OutputContract(
        fields=[
            DataField("llm_output", "string", "Resultado LLM", "Texto generado por el modelo"),
            DataField("tokens_used", "integer", "Tokens usados", "Número de tokens consumidos"),
            DataField("execution_time_ms", "integer", "Tiempo (ms)", "Tiempo de ejecución en milisegundos"),
            DataField("pii_entities_masked", "integer", "PII protegidos", "Número de entidades PII enmascaradas"),
        ],
        format="json",
        description="Resultado de procesamiento con LLM"
    ),
}


# ============================================================================
# CONTRATOS DE ENTRADA POR DEFECTO - Qué espera cada tipo de átomo
# ============================================================================

DEFAULT_INPUT_CONTRACTS: Dict[StepType, InputContract] = {
    StepType.EXTRACTION: InputContract(
        accepts_formats=["pdf", "docx", "xlsx", "csv", "json", "xml", "image"],
        description="Documento para extraer campos estructurados"
    ),
    StepType.ETL: InputContract(
        accepts_formats=["json", "csv", "xlsx", "xml"],
        description="Datos estructurados para transformar"
    ),
    StepType.RPA_EXECUTE: InputContract(
        accepts_formats=["json", "xlsx", "csv"],
        description="Datos para automatización robótica"
    ),
    StepType.REPORT_GENERATE: InputContract(
        accepts_formats=["json", "csv", "xlsx"],
        description="Datos para generar informe"
    ),
    StepType.ANONYMIZATION: InputContract(
        accepts_formats=["json", "csv", "xlsx"],
        description="Datos con campos sensibles para anonimizar"
    ),
    # --- Nuevos tipos de la taxonomía v2 ---
    StepType.GRAPHICS: InputContract(
        accepts_formats=["json", "csv", "xlsx", "parquet"],
        description="Datos estructurados para generar gráficos"
    ),
    StepType.ARCHIVE_FILE: InputContract(
        accepts_formats=["*"],  # Acepta cualquier archivo para archivar
        description="Archivo(s) a guardar en destino"
    ),
    StepType.PDF_TOOLS: InputContract(
        accepts_formats=["pdf"],  # Solo archivos PDF
        description="Archivos PDF para procesar (unir, dividir, optimizar)"
    ),
    StepType.LLM_PROCESS: InputContract(
        accepts_formats=["json", "txt", "csv"],  # Datos estructurados o texto
        description="Datos o texto para procesar con LLM (resumir, analizar, extraer)"
    ),
}


class DataContractService:
    """
    Service for inferring data contracts from various source types.
    Implements Strategy Pattern for different file formats.
    """
    
    async def suggest_contract(self, source: Union[str, bytes], source_type: str, file_name: str = None) -> Dict[str, Any]:
        """
        Unified entry point for contract inference.
        
        Args:
            source: File path (str) or content (bytes)
            source_type: MIME type or extension (e.g., 'application/json', '.csv')
            file_name: Optional file name for context
            
        Returns:
            Dict with 'suggested_fields' list
        """
        # Normalize source type
        st = source_type.lower()
        if file_name:
            if file_name.endswith('.json'): st = 'application/json'
            elif file_name.endswith('.csv'): st = 'text/csv'
            elif file_name.endswith('.pdf'): st = 'application/pdf'
            
        # Dispatch strategy
        if 'pdf' in st:
            return await self._infer_from_pdf(source)
        elif 'json' in st:
            return self._infer_from_json(source)
        elif 'csv' in st:
            return self._infer_from_csv(source)
        elif 'text' in st:
            # Fallback for plain text - maybe future LLM usage
            return {"suggested_fields": []}
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

    async def _infer_from_pdf(self, source: str) -> Dict[str, Any]:
        """Delegate to existing ExtractionService."""
        # Avoid circular import
        from client_app.app.services.extraction_service import extraction_service
        
        # If source is bytes, we might need to save to temp file first
        # For now assume source is path string as per current wizard usage
        if isinstance(source, bytes):
            raise NotImplementedError("PDF inference from bytes not yet supported (needs temp file)")
            
        return await extraction_service.suggest_fields_from_doc1(source)

    def _infer_from_json(self, source: Union[str, bytes]) -> Dict[str, Any]:
        """Infer schema from JSON object or array."""
        try:
            content = source
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            # If source is a file path, read it
            if isinstance(content, str) and (content.endswith('.json') or content.endswith('.txt')):
                # Check if it looks like a path and exists? 
                # For safety, try to parse as string first.
                pass

            data = json.loads(content)
            
            # Helper to extract keys
            fields = []
            
            if isinstance(data, list):
                if not data: return {"suggested_fields": []}
                # Inspect first item
                item = data[0]
                self._extract_fields_from_dict(item, fields)
            elif isinstance(data, dict):
                self._extract_fields_from_dict(data, fields)
                
            return {"suggested_fields": fields}
            
        except Exception as e:
            print(f"JSON Inference Error: {e}")
            return {"suggested_fields": []}

    def _infer_from_csv(self, source: Union[str, bytes]) -> Dict[str, Any]:
        """Infer schema from CSV headers."""
        try:
            content = source
            if isinstance(content, bytes):
                content = content.decode('utf-8')
                
            f = io.StringIO(content)
            reader = csv.reader(f)
            headers = next(reader, None)
            
            if not headers:
                return {"suggested_fields": []}
                
            fields = []
            for h in headers:
                fields.append({
                    "name": self._sanitize_name(h),
                    "type": "string", # CSV is untyped by default, could infer from first row values
                    "description": f"Column: {h}"
                })
                
            return {"suggested_fields": fields}
            
        except Exception as e:
            print(f"CSV Inference Error: {e}")
            return {"suggested_fields": []}

    def _extract_fields_from_dict(self, data: Dict, fields_list: List):
        """Recursive/Flat extraction helper."""
        for k, v in data.items():
            t = "string"
            if isinstance(v, bool): t = "boolean"
            elif isinstance(v, int): t = "integer"
            elif isinstance(v, float): t = "number"
            elif isinstance(v, dict): t = "object"
            elif isinstance(v, list): t = "array"
            
            fields_list.append({
                "name": k,
                "type": t,
                "description": f"Detected from JSON key '{k}'"
            })

    def _sanitize_name(self, name: str) -> str:
        """Convert 'My Column' to 'my_column'."""
        return name.lower().replace(' ', '_').replace('-', '_')
    
    def _map_type_to_input_type(self, type_str: str) -> InputType:
        """Map string type to InputType enum."""
        type_map = {
            'string': InputType.STR,
            'str': InputType.STR,
            'integer': InputType.INT,
            'int': InputType.INT,
            'number': InputType.FLOAT,
            'float': InputType.FLOAT,
            'boolean': InputType.BOOL,
            'bool': InputType.BOOL,
            'date': InputType.DATE,
            'datetime': InputType.DATETIME
        }
        return type_map.get(type_str.lower(), InputType.STR)
    
    async def generate_synthetic_data(
        self,
        output_schema: Dict[str, Any],
        num_samples: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Genera datos sintéticos basados en un output schema.
        
        Args:
            output_schema: Schema de salida con lista de fields
            num_samples: Número de muestras a generar
            
        Returns:
            Lista de diccionarios con datos sintéticos
        """
        from faker import Faker
        
        fake = Faker('es_ES')  # Español
        samples = []
        
        # Extract fields from schema
        fields = output_schema.get('fields', [])
        if not fields:
            return []
        
        for _ in range(num_samples):
            sample = {}
            for field in fields:
                field_name = field.get('name', 'unknown')
                field_type = field.get('type', 'string')
                
                # Generar valor según tipo y nombre
                if field_type in ['string', 'str']:
                    name_lower = field_name.lower()
                    if 'email' in name_lower or 'correo' in name_lower:
                        sample[field_name] = fake.email()
                    elif 'nombre' in name_lower or 'name' in name_lower:
                        sample[field_name] = fake.name()
                    elif 'direccion' in name_lower or 'address' in name_lower:
                        sample[field_name] = fake.address()
                    elif 'telefono' in name_lower or 'phone' in name_lower:
                        sample[field_name] = fake.phone_number()
                    elif 'empresa' in name_lower or 'company' in name_lower:
                        sample[field_name] = fake.company()
                    elif 'ciudad' in name_lower or 'city' in name_lower:
                        sample[field_name] = fake.city()
                    elif 'pais' in name_lower or 'country' in name_lower:
                        sample[field_name] = fake.country()
                    elif 'url' in name_lower or 'web' in name_lower:
                        sample[field_name] = fake.url()
                    else:
                        sample[field_name] = fake.text(max_nb_chars=50)
                
                elif field_type in ['integer', 'int']:
                    sample[field_name] = fake.random_int(min=1, max=1000)
                
                elif field_type in ['number', 'float']:
                    sample[field_name] = round(fake.random.uniform(0, 1000), 2)
                
                elif field_type in ['date', 'datetime']:
                    sample[field_name] = fake.date()
                
                elif field_type in ['boolean', 'bool']:
                    sample[field_name] = fake.boolean()
                
                else:
                    # Default to string
                    sample[field_name] = fake.text(max_nb_chars=30)
            
            samples.append(sample)
        
        return samples
    
    async def generate_input_contract(
        self,
        input_metadata: Dict[str, Any]
    ) -> str:
        """
        Genera Input Contract JSON desde metadata de ejecución.
        
        Args:
            input_metadata: Variables y campos del documento de entrada
            
        Returns:
            JSON string del DataContract
        """
        from automatia_shared.contracts.ui_contract import DataContract, UIContract, InputDefinition
        
        # Convertir detected_fields a InputDefinitions
        input_defs = []
        for field in input_metadata.get('detected_fields', []):
            input_defs.append(InputDefinition(
                name=field['name'],
                type=self._map_type_to_input_type(field.get('type', 'string')),
                label=field.get('label', field['name']),
                required=field.get('required', False),
                description=field.get('description', '')
            ))
        
        ui_contract = UIContract(inputs=input_defs)
        contract = DataContract(inputs=ui_contract)
        return contract.model_dump_json()
    
    async def generate_output_contract(
        self,
        output_metadata: Dict[str, Any]
    ) -> str:
        """
        Genera Output Contract JSON desde metadata de ejecución.
        
        Args:
            output_metadata: Estructura y muestra del resultado
            
        Returns:
            JSON string del OutputSchema
        """
        from automatia_shared.contracts.ui_contract import OutputSchema, OutputField
        
        output_fields = []
        for field in output_metadata.get('fields', []):
            output_fields.append(OutputField(
                name=field['name'],
                type=self._map_type_to_input_type(field.get('type', 'string')),
                label=field.get('label', field['name']),
                description=field.get('description', '')
            ))
        
        schema = OutputSchema(fields=output_fields)
        return schema.model_dump_json()

    # ========================================================================
    # MÉTODOS PARA GESTIÓN DE FUENTES Y COMPATIBILIDAD
    # ========================================================================

    def is_source_atom(self, step_type: StepType) -> bool:
        """Determina si un tipo de átomo es una fuente de datos."""
        return step_type in SOURCE_ATOMS

    def is_consumer_atom(self, step_type: StepType) -> bool:
        """Determina si un tipo de átomo es un consumidor de datos."""
        return step_type in CONSUMER_ATOMS

    def supports_manual_upload(self, step_type: StepType) -> bool:
        """Determina si un tipo de átomo soporta carga manual de archivos."""
        return step_type in MANUAL_UPLOAD_SUPPORT

    def get_supported_upload_formats(self, step_type: StepType) -> List[str]:
        """Obtiene los formatos de archivo soportados para carga manual."""
        return MANUAL_UPLOAD_SUPPORT.get(step_type, [])

    def get_compatible_sources(self, consumer_type: StepType) -> List[StepType]:
        """
        Obtiene los tipos de átomo que pueden servir como fuente para un consumidor.

        Args:
            consumer_type: Tipo de átomo consumidor

        Returns:
            Lista de StepTypes que pueden ser fuentes compatibles
        """
        return list(COMPATIBLE_SOURCES.get(consumer_type, set()))

    def is_compatible_source(self, consumer_type: StepType, source_type: StepType) -> bool:
        """
        Verifica si un tipo de fuente es compatible con un consumidor.

        Args:
            consumer_type: Tipo del átomo que consume datos
            source_type: Tipo del átomo que produce datos

        Returns:
            True si son compatibles
        """
        compatible = COMPATIBLE_SOURCES.get(consumer_type, set())
        return source_type in compatible

    def get_default_output_contract(self, step_type: StepType) -> Optional[OutputContract]:
        """Obtiene el contrato de salida por defecto de un tipo de átomo."""
        return DEFAULT_OUTPUT_CONTRACTS.get(step_type)

    def get_default_input_contract(self, step_type: StepType) -> Optional[InputContract]:
        """Obtiene el contrato de entrada por defecto de un tipo de átomo."""
        return DEFAULT_INPUT_CONTRACTS.get(step_type)

    def get_available_data_sources(
        self,
        consumer_type: StepType,
        available_atoms: List[Dict[str, Any]] = None,
        flow_context: Dict[str, Any] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Obtiene todas las fuentes de datos disponibles para un consumidor.

        Combina:
        1. Carga manual (si soportada)
        2. Átomos del catálogo (filtrados por compatibilidad)
        3. Pasos previos del flujo (si hay contexto de flujo)

        Args:
            consumer_type: Tipo del átomo consumidor
            available_atoms: Lista de átomos disponibles en el catálogo
            flow_context: Contexto del flujo (si se está diseñando en contexto)

        Returns:
            Dict con claves 'manual', 'catalog', 'flow_steps'
        """
        result = {
            'manual': None,
            'catalog': [],
            'flow_steps': []
        }

        # 1. Carga manual
        if self.supports_manual_upload(consumer_type):
            result['manual'] = {
                'enabled': True,
                'formats': self.get_supported_upload_formats(consumer_type),
                'label': 'Cargar archivo manualmente'
            }

        # 2. Átomos del catálogo
        compatible_types = self.get_compatible_sources(consumer_type)
        if available_atoms:
            for atom in available_atoms:
                atom_type_str = atom.get('atom_type', '')
                try:
                    atom_type = StepType(atom_type_str)
                    if atom_type in compatible_types:
                        result['catalog'].append({
                            'id': atom.get('id'),
                            'name': atom.get('name'),
                            'type': atom_type_str,
                            'description': atom.get('description', ''),
                            'output_contract': atom.get('output_contract', {})
                        })
                except ValueError:
                    continue  # Ignorar tipos no reconocidos

        # 3. Pasos previos del flujo
        if flow_context and flow_context.get('mode') == 'contextual':
            available_vars = flow_context.get('available_variables', [])
            for var in available_vars:
                step_type_str = var.get('step_type', '')
                try:
                    step_type = StepType(step_type_str)
                    if step_type in compatible_types or step_type == consumer_type:
                        result['flow_steps'].append({
                            'step_index': var.get('step_index'),
                            'step_name': var.get('step_name'),
                            'step_type': step_type_str,
                            'output_ref': var.get('output_ref'),
                            'outputs': var.get('outputs', [])
                        })
                except ValueError:
                    continue

        return result

    def validate_source_compatibility(
        self,
        consumer_type: StepType,
        source_contract: Dict[str, Any],
        consumer_contract: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Valida si un contrato de salida es compatible con uno de entrada.

        Args:
            consumer_type: Tipo del consumidor
            source_contract: Contrato de salida de la fuente
            consumer_contract: Contrato de entrada del consumidor

        Returns:
            Dict con 'compatible', 'warnings', 'missing_fields'
        """
        result = {
            'compatible': True,
            'warnings': [],
            'missing_fields': [],
            'mapped_fields': []
        }

        source_fields = {f['name']: f for f in source_contract.get('fields', [])}
        required_fields = consumer_contract.get('required_fields', [])

        for req_field in required_fields:
            field_name = req_field.get('name') if isinstance(req_field, dict) else req_field
            if field_name not in source_fields:
                result['missing_fields'].append(field_name)
                result['compatible'] = False
            else:
                result['mapped_fields'].append({
                    'source': field_name,
                    'target': field_name,
                    'type_match': source_fields[field_name].get('type') == req_field.get('type', 'string')
                })

        if result['missing_fields']:
            result['warnings'].append(
                f"Campos requeridos no encontrados en la fuente: {', '.join(result['missing_fields'])}"
            )

        return result


# Singleton instance
data_contract_service = DataContractService()

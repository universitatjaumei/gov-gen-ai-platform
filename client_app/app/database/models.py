"""
Client-side database models for AutomatIA (On-Premise).

These models are stored in client_local.db and contain:
- User's RPA playbooks
- User extraction configurations
- Extraction logs
- API credentials (encrypted)
- Local workflow configurations
"""

from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, Dict, List, Any
from enum import Enum
import hashlib
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON, Text, event
import json
from pydantic import field_validator, field_serializer, ConfigDict, PrivateAttr

from automatia_shared.enums import TaskStatus, ScreenshotPolicyEnum, StepType, AutomationType
from automatia_shared.core.audit_models import RiskLevel


# === ENUMS PARA SISTEMA DE EXPORTACIÓN/IMPORTACIÓN ===

class PackageType(str, Enum):
    """Tipos de contenido de un paquete de automatismos."""
    SCRIPTS = "scripts"
    PLAYBOOKS = "playbooks"
    WORKFLOW = "workflow"
    MIXED = "mixed"


class PackageStatus(str, Enum):
    """Estados del ciclo de vida de un paquete."""
    CREATED = "created"
    EXPORTED = "exported"
    IMPORTED = "imported"
    REJECTED = "rejected"


# === FUNCIONES HELPER ===

def calculate_playbook_hash(actions_json: str) -> str:
    """
    Calcula SHA256 del contenido del playbook.

    Args:
        actions_json: JSON string de las acciones del playbook

    Returns:
        Hash SHA256 como string hexadecimal (64 caracteres)
    """
    return hashlib.sha256(actions_json.encode()).hexdigest()


class ReportHistory(SQLModel, table=True):
    """
    History of generated PDF reports.
    R-05 Dashboard Integration.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    report_name: str = Field(index=True)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    pdf_path: str
    template_used: str
    status: str = Field(default="success")
    user_instructions: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReportTemplate(SQLModel, table=True):
    """
    Plantilla de informe reutilizable con soporte para:
    - Bloques dinámicos (texto, tabla, gráfico)
    - Contratos de datos de entrada (input_schema)
    - Configuración de estilos y renderizado dual
    - Datos mock para vista previa
    """
    __tablename__ = "report_templates"

    # === Identificación ===
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, description="Nombre descriptivo de la plantilla")
    description: Optional[str] = Field(default=None, description="Propósito del informe")

    # === Estructura de Bloques ===
    # Lista ordenada de bloques: text, table, chart, separator, page_break
    structure: Dict[str, Any] = Field(
        default_factory=lambda: {"blocks": []},
        sa_column=Column(JSON),
        description="Estructura de bloques del informe"
    )

    # === Contrato de Datos ===
    # JSON Schema que define las variables de entrada esperadas
    input_schema: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="JSON Schema de variables de entrada"
    )

    # === Configuración de Estilos ===
    # Incluye tema, colores, fuentes y opciones de renderizado
    style_config: Dict[str, Any] = Field(
        default_factory=lambda: {
            "theme": "default",
            "colors": {"primary": "#1976D2"},
            "fonts": {"title": "Roboto", "body": "Open Sans"},
            "render": {
                "interactive_library": "echarts",  # echarts | plotly
                "export_format": "svg",            # svg | png
                "export_dpi": 300,
                "page_size": "A4"
            }
        },
        sa_column=Column(JSON),
        description="Configuración de estilos y renderizado"
    )

    # === Datos Mock para Vista Previa ===
    # Datos sintéticos que siguen el input_schema para diseño Zero-Knowledge
    preview_data: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Datos mock para vista previa sin datos reales"
    )

    # === Metadatos ===
    category: Optional[str] = Field(default="general", description="Categoría del informe")
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    is_system: bool = Field(default=False, description="Indica si es una plantilla de sistema inmutable")
    is_active: bool = Field(default=True)
    version: str = Field(default="1.0")

    # === Legacy Compatibility / Reused Fields ===
    format: str = Field(default="pdf", description="Formato soportado: 'pdf', 'odt', 'both'")
    template_type: str = Field(default="builtin", description="Tipo: 'builtin', 'html', 'reportlab'")
    data_schema: Optional[str] = Field(default=None, sa_column=Column(Text)) # Legacy text schema

    # === Auditoría ===
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(default=None)


class LocalAutomation(SQLModel, table=True):
    """
    Local replica of Brain automations.
    Synced via SyncManager.
    """
    id: str = Field(primary_key=True)
    name: str = Field(index=True)
    type: AutomationType
    code_content: str = Field(sa_column=Column(Text))
    version: int = Field(default=1)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Synchronization
    signature: Optional[str] = Field(default=None)
    is_system: bool = Field(default=False)
    local_status: str = Field(default="synced") # synced, modified, detached
    last_synced_at: datetime = Field(default_factory=datetime.utcnow)


class RpaPlaybook(SQLModel, table=True):
    """
    Stores RPA automation scripts (Playbooks).
    These are user-specific workflows for web automation.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    base_url: str
    actions: List[Dict[str, Any]] = Field(default=[], sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None

    # === INTEGRIDAD Y ORIGEN (para playbooks importados) ===
    content_hash: Optional[str] = Field(
        default=None,
        description="SHA256 del JSON de acciones para verificar integridad"
    )
    origin_license_id: Optional[str] = Field(
        default=None,
        description="ID de licencia de donde se importó el playbook"
    )
    origin_package_id: Optional[str] = Field(
        default=None,
        description="UUID del paquete de importación"
    )


class UserExtractionConfig(SQLModel, table=True):
    """
    User-customized extraction configurations.
    Allows users to override or extend system prompts.
    """
    service_id: str = Field(primary_key=True)
    name: str
    description: Optional[str] = None
    module: Optional[str] = None
    target_function: Optional[str] = None
    expected_schema: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    status: str = Field(default="draft") # draft | published | deprecated
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("expected_schema", mode="before")
    @classmethod
    def parse_json_schema(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except ValueError:
                return {}
        return v

    @field_serializer("expected_schema")
    def serialize_schema(self, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except ValueError:
                return {}
        return v


class ExtractionLog(SQLModel, table=True):
    """
    Log of document extraction operations.
    Records each extraction for audit and debugging.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    filename: str
    service_used: str
    model_used: str
    input_tokens: int
    output_tokens: int
    estimated_cost: float = Field(default=0.0)
    status: str = Field(default=TaskStatus.PENDING.value)
    processing_time_seconds: float = Field(default=0.0)
    extraction_result: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    privacy_stats: Optional[Dict[str, int]] = Field(default=None, sa_column=Column(JSON))


class ConnectionLog(SQLModel, table=True):
    """Log de eventos de conexiones y watchers."""
    __tablename__ = "connection_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    connection_type: str = Field(index=True)  # 'email', 'web', 'file', 'api'
    connection_name: str  # Nombre descriptivo de la conexión
    event_type: str  # 'connect', 'disconnect', 'error', 'trigger', 'poll'
    status: str = Field(index=True)  # 'success', 'error', 'warning', 'info'
    message: str
    details: Optional[str] = None  # JSON con detalles adicionales

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "connection_type": "email",
                "connection_name": "Gmail Work",
                "event_type": "trigger",
                "status": "success",
                "message": "Email recibido de user@example.com"
            }
        }
    )


class ProviderAPIKey(SQLModel, table=True):
    """
    API credentials per provider.
    Stored locally for user privacy.
    """
    provider: str = Field(primary_key=True, description="Provider: 'google', 'openrouter'")
    api_key: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ServerConnection(SQLModel, table=True):
    """
    Configuration for connecting to the Brain server.

    Incluye la clave pública del Partner para verificación de firmas RSA
    de los manifiestos descargados de la biblioteca central.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    brain_url: str = Field(default="https://brain.automatia.es/api")
    license_key: str = Field(description="Plain text license key (hashed when sent)")
    client_email: Optional[str] = Field(default=None)
    partner_email: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    last_validated: Optional[datetime] = None

    # Clave pública RSA del Partner (formato PEM) para verificación de firmas
    partner_public_key: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Partner RSA public key in PEM format for signature verification"
    )


class LocalCredentials(SQLModel, table=True):
    """
    Encrypted credentials for local services (IMAP, SMTP, external APIs).
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    service_name: str = Field(index=True)
    service_type: str = Field(default="IMAP", index=True) # IMAP or SMTP
    encrypted_data: str = Field(sa_column=Column(Text), description="Fernet-encrypted JSON")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DatabaseCredentialConfig(SQLModel, table=True):
    """
    Credentials for relational databases (MySQL, PostgreSQL, SQL Server, SQLite).
    R-SQL Generic Connector.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, description="Nombre descriptivo (ej: 'ERP Producción')")
    db_type: str = Field(index=True, description="mysql, postgresql, sqlserver, sqlite")
    host: str = Field(description="Host o IP del servidor")
    port: int = Field(default=0, description="Puerto (0 = default)")
    database: str = Field(description="Nombre de la base de datos")
    username: str = Field(default="", description="Usuario")
    encrypted_password: str = Field(default="", sa_column=Column(Text), description="Contraseña cifrada")
    
    ssl_enabled: bool = Field(default=False)
    extra_params: str = Field(default="{}", sa_column=Column(Text), description="JSON para parámetros extra")
    is_active: bool = Field(default=True)
    
    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def get_connection_string(self, decrypted_password: str) -> str:
        """
        Generates an SQLAlchemy-compatible connection URL for async drivers.
        """
        password = decrypted_password
        
        if self.db_type == "mysql":
            port = self.port if self.port > 0 else 3306
            return f"mysql+aiomysql://{self.username}:{password}@{self.host}:{port}/{self.database}"
        
        elif self.db_type == "postgresql":
            port = self.port if self.port > 0 else 5432
            return f"postgresql+asyncpg://{self.username}:{password}@{self.host}:{port}/{self.database}"
        
        elif self.db_type == "sqlserver":
            port = self.port if self.port > 0 else 1433
            return f"mssql+aioodbc://{self.username}:{password}@{self.host}:{port}/{self.database}?driver=ODBC+Driver+17+for+SQL+Server"
        
        elif self.db_type == "sqlite":
            return f"sqlite+aiosqlite:///{self.database}"
        
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")


class FlowRegistry(SQLModel, table=True):
    """
    Registry of user-defined workflows with versioning.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    version: str = Field(default="0.1.0")  # Semantic version
    status: str = Field(default="DRAFT")  # DRAFT|PUBLISHED|DEPRECATED
    row_version: int = Field(default=0)  # Optimistic locking
    owner_scope: Optional[str] = Field(default=None)  # partner_id or client_id
    trigger_id: Optional[int] = Field(default=None, index=True, description="ID del trigger configurado (si aplica)")
    trigger_type: str = Field(default="manual")
    trigger_config: str = Field(default="{}", sa_column=Column(Text))
    steps: str = Field(default="[]", sa_column=Column(Text))
    is_active: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TaskLog(SQLModel, table=True):
    """
    Log of workflow task executions with metrics.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    execution_id: str = Field(index=True)
    step_index: int
    step_name: str
    status: str = Field(default=TaskStatus.PENDING.value)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None  # Execution duration in milliseconds
    policy_id: Optional[int] = None  # Reference to SecurityPolicy
    peak_memory_mb: Optional[float] = None  # Peak memory usage for metrics
    result_summary: Optional[str] = None
    error_message: Optional[str] = None
    privacy_stats: Optional[Dict[str, int]] = Field(default=None, sa_column=Column(JSON))


# EnterpriseAuditLog refactorizado a shared
from automatia_shared.core.audit_models import EnterpriseAuditLog, register_immutability_listener

# Registrar listener de inmutabilidad
register_immutability_listener()


class ValidationHistory(SQLModel, table=True):
    """
    History of user validations for extraction results.
    Used for the validation loop feature.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: str = Field(index=True)
    attempt_number: int = Field(default=1)
    user_action: str  # approve, reject, retry
    feedback: Optional[str] = None
    who: Optional[str] = Field(default=None)  # User identifier
    retries: int = Field(default=0)  # Retry counter
    fields_affected: Optional[str] = Field(default=None, sa_column=Column(Text))  # JSON list of affected fields
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SecurityPolicy(SQLModel, table=True):
    """
    Security policy for sandbox execution.
    Controls what modules can be imported, allowed domains, execution limits.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    allowed_domains: str = Field(default="[]", sa_column=Column(Text))
    allowed_imports: str = Field(default='["pandas", "json", "re", "math", "datetime"]', sa_column=Column(Text))
    forbidden_imports: str = Field(default='["os", "sys", "subprocess", "requests"]', sa_column=Column(Text))
    max_execution_time: int = Field(default=300, description="Max execution time in seconds")
    max_memory_mb: int = Field(default=512, description="Max memory in MB")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # === NUEVOS CAMPOS: Screenshot Policy ===
    screenshot_policy: str = Field(
        default=ScreenshotPolicyEnum.REVIEW.value,
        description="BLOCK|REVIEW|TRUSTED - política de envío de capturas"
    )
    trusted_screenshot_domains: str = Field(
        default="[]",
        sa_column=Column(Text),
        description="JSON list de dominios permitidos en modo TRUSTED"
    )


class APIEndpointConfig(SQLModel, table=True):
    """
    Configuration for external API endpoints.
    Used by APIWatcher for consuming external REST APIs.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    url: str
    method: str = Field(default="GET")
    auth_type: str = Field(default="none", description="none, bearer, api_key, basic")
    auth_credential_id: Optional[int] = None
    headers: str = Field(default="{}", sa_column=Column(Text))
    body: str = Field(default="{}", sa_column=Column(Text))
    response_format: str = Field(default="json")
    pagination_type: Optional[str] = None  # offset, cursor, next_url
    pagination_config: str = Field(default="{}", sa_column=Column(Text))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FavoriteFlow(SQLModel, table=True):
    """
    User favorite workflows for quick access on dashboard.
    GUI-02 implementation.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    flow_id: int = Field(index=True)  # FK logic handled manually or via join
    user_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ETLJobHistory(SQLModel, table=True):
    """
    Historial de transformaciones ETL ejecutadas con IA.
    ETL-01 implementation.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    execution_id: str = Field(index=True)
    source_file: str  # Nombre archivo origen
    source_format: str  # csv, excel, xml, json, parquet
    target_format: str  # csv, excel, xml, json, parquet
    target_file: str = Field(default="")  # Archivo destino
    script_content: str = Field(sa_column=Column(Text))  # Script Python generado
    user_instructions: str = Field(default="", sa_column=Column(Text))  # Instrucciones usuario
    status: str = Field(default="draft")  # draft, validated, executed, failed
    result_summary: Optional[str] = Field(default=None, sa_column=Column(Text))  # Resumen JSON resultado
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    execution_metadata: str = Field(default="{}", sa_column=Column(Text))
    transformation_mode: str = Field(default="ai") # ai, assisted
    privacy_stats: Optional[Dict[str, int]] = Field(default=None, sa_column=Column(JSON))
    execution_time_ms: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class MailWatcherState(SQLModel, table=True):
    """
    Estado persistente del MailWatcher para auto-start y monitorización.
    Singleton table (id=1).
    """
    id: int = Field(default=1, primary_key=True)
    is_enabled: bool = Field(default=False, description="Watcher currently running")
    auto_start: bool = Field(default=False, description="Auto-start on app launch")
    last_heartbeat: Optional[datetime] = Field(default=None, description="Last heartbeat timestamp")
    error_count: int = Field(default=0, description="Consecutive error count")
    last_error: Optional[str] = Field(default=None, sa_column=Column(Text), description="Last error message")
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReceivedEmail(SQLModel, table=True):
    """
    Correos electrónicos procesados por EmailScan y EmailWatcher.
    Permite persistir el contenido de los correos para análisis posterior.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    message_id: str = Field(index=True, unique=True, description="ID único del mensaje IMAP")
    source: str = Field(description="Origen: 'watcher' o 'scan'")
    sender: str = Field(description="Dirección de correo del remitente")
    subject: str = Field(description="Asunto del correo")
    date: datetime = Field(description="Fecha y hora del correo")
    body_plain: str = Field(default="", sa_column=Column(Text), description="Cuerpo en texto plano limpio")
    body_html: Optional[str] = Field(default=None, sa_column=Column(Text), description="Cuerpo en HTML (opcional)")
    attachments_info: str = Field(default="[]", sa_column=Column(Text), description="JSON con info de adjuntos")
    is_processed: bool = Field(default=False, description="Si ya fue procesado por un flujo/LLM")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WebWatcherHistory(SQLModel, table=True):
    """
    History of detected web page changes.
    """
    id: int = Field(default=None, primary_key=True)
    config_id: int = Field(description="Reference to TriggerConfig (web_watcher)")
    url: str = Field(description="URL that changed")
    change_detected_at: datetime = Field(default_factory=datetime.utcnow)
    old_hash: Optional[str] = Field(default=None, description="Previous content hash")
    new_hash: str = Field(description="New content hash")
    screenshot_path: Optional[str] = Field(default=None, description="Path to screenshot")

    # Diff content for change visualization
    diff_text: Optional[str] = Field(default=None, sa_column=Column(Text), description="Text diff showing changes (+ added, - removed)")
    diff_html: Optional[str] = Field(default=None, sa_column=Column(Text), description="HTML formatted diff with colors")

    workflow_triggered: bool = Field(default=False, description="Workflow was triggered")
    workflow_execution_id: Optional[str] = Field(default=None, description="Workflow execution ID")


class CleanupSchedulerConfig(SQLModel, table=True):
    """
    Configuration for the file cleanup scheduler.
    Singleton table (id=1).

    Unlike server scheduler, client cleanup runs on startup
    if retention period has passed since last run.
    """
    id: int = Field(default=1, primary_key=True)
    enabled: bool = Field(default=True, description="Whether cleanup is enabled")
    interval_hours: int = Field(default=24, description="Interval in hours for periodic cleanup")
    startup_delay_minutes: int = Field(default=2, description="Minutes to wait after app start before cleanup")
    last_run: Optional[datetime] = Field(default=None, description="Timestamp of last cleanup run")
    last_files_deleted: int = Field(default=0, description="Files deleted in last run")
    last_bytes_freed: int = Field(default=0, description="Bytes freed in last run")
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CleanupPolicy(SQLModel, table=True):
    """
    Cleanup policy per folder type.
    Defines retention period for each data folder.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    folder_type: str = Field(unique=True, description="Type: uploads, etl, results, execution, screenshots")
    folder_path: str = Field(description="Relative path from app root (e.g., 'data/uploads')")
    enabled: bool = Field(default=True, description="Whether cleanup is enabled for this folder")
    retention_days: int = Field(default=7, description="Days to keep files before deletion")
    delete_empty_dirs: bool = Field(default=True, description="Delete empty subdirectories")
    file_patterns: str = Field(default="*", description="Glob patterns to match (comma-separated)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CleanupLog(SQLModel, table=True):
    """
    Log of cleanup operations for audit.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    folder_type: str = Field(description="Folder type that was cleaned (or 'summary')")
    files_deleted: int = Field(default=0)
    bytes_freed: int = Field(default=0)
    message: Optional[str] = Field(default=None, sa_column=Column(Text), description="Summary message")
    errors: Optional[str] = Field(default=None, sa_column=Column(Text), description="Error messages if any")


class CustomScript(SQLModel, table=True):
    """
    Scripts personalizados creados por usuarios mediante IA.
    Almacenado en client_local.db
    CS-01 implementation.
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    # === IDENTIFICACIÓN ===
    # === IDENTIFICACIÓN ===
    name: str = Field(index=True, description="Nombre descriptivo del script")
    description: Optional[str] = Field(default=None, sa_column=Column(Text), description="Qué hace (migrado a doc_path)")
    user_prompt: str = Field(sa_column=Column(Text), description="Petición original del usuario")
    tags: List[str] = Field(default=[], sa_column=Column(JSON), description="Tags para búsqueda")

    # === CÓDIGO & DOCS (HYBRID PERSISTENCE - PROMPT 7) ===
    # 'code' se mantiene por compatibilidad durante migración, pero se usará script_path
    code: Optional[str] = Field(default=None, sa_column=Column(Text), description="DEPRECATED: Usar script_path")
    script_path: Optional[str] = Field(default=None, description="Ruta relativa al archivo .py")
    doc_path: Optional[str] = Field(default=None, description="Ruta relativa al archivo .md")
    
    code_hash: str = Field(description="SHA256 para verificar integridad")
    required_libraries: List[str] = Field(default=[], sa_column=Column(JSON))

    # === ESQUEMA I/O ===
    input_type: str = Field(default="file", description="file, files, text, none")
    input_extensions: List[str] = Field(default=[], sa_column=Column(JSON), description="Extensiones permitidas")
    input_description: str = Field(default="", description="Descripción de entrada esperada")
    output_type: str = Field(default="file", description="file, text, dataframe, chart")
    output_description: str = Field(default="", description="Descripción de salida")

    # === UI CONTRACT & EXECUTION (PROMPT 7) ===
    ui_contract: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Contrato de UI para ejecución universal")
    data_contract: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Contrato de Datos (Schema) para validación técnica")
    execution_mode: str = Field(default="local", description="local, remote, hybrid")
    visualization_config: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Configuración de visualización de resultados")

    # === ESTADO ===
    status: str = Field(default="draft", description="draft, testing, escalated, validated, published")

    # === VALIDACIÓN ===
    validation_history: List[Dict] = Field(default=[], sa_column=Column(JSON), description="Historial de refinamientos")
    escalation_id: Optional[str] = Field(default=None, description="ID de escalación si aplica")
    validated_by: Optional[str] = Field(default=None, description="partner_id si fue validado externamente")
    validation_notes: Optional[str] = Field(default=None, sa_column=Column(Text))

    # === MÉTRICAS ===
    execution_count: int = Field(default=0)
    success_count: int = Field(default=0)
    last_executed: Optional[datetime] = Field(default=None)
    avg_execution_time_ms: int = Field(default=0)

    # === AUDITORÍA ===
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_favorite: bool = Field(default=False)

    # === ORIGEN (para scripts importados) ===
    origin_license_id: Optional[str] = Field(
        default=None,
        description="ID de licencia de donde se importó el script"
    )
    origin_package_id: Optional[str] = Field(
        default=None,
        description="UUID del paquete de importación"
    )
    original_status: Optional[str] = Field(
        default=None,
        description="Estado que tenía en origen (draft/published)"
    )

    @field_validator("data_contract", mode="before")
    @classmethod
    def validate_data_contract(cls, v):
        """Valida que el contrato de datos cumpla con el esquema Pydantic unificado."""
        if not v:
            return {}
        if isinstance(v, dict):
            from automatia_shared.contracts.ui_contract import DataContract
            try:
                # Intentar instanciar para validar
                # Si falla, Pydantic lanzará ValueError
                DataContract(**v)
            except Exception as e:
                # Podriamos lanzar error o loguear. 
                # El prompt pide "asegurar que lo que se persiste es íntegro".
                # Lanzar error es lo correcto para impedir persistencia corrupta.
                raise ValueError(f"DataContract inválido: {e}")
        return v

    @field_validator("ui_contract", mode="before")
    @classmethod
    def validate_ui_contract(cls, v):
        """Valida que el contrato de UI cumpla con el esquema Pydantic unificado."""
        if not v:
            return {}
        if isinstance(v, dict):
            from automatia_shared.contracts.ui_contract import UIContract
            try:
                UIContract(**v)
            except Exception as e:
                raise ValueError(f"UIContract inválido: {e}")
        return v


class ScriptLibrary(SQLModel, table=True):
    """
    Biblioteca unificada de scripts generados por todos los módulos.
    Centraliza gestión, validación y promoción de scripts.
    Prompt 8 Corrección - Sistema Unificado.
    """
    __tablename__ = "script_library"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # === ORIGEN Y CLASIFICACIÓN ===
    source_module: str = Field(index=True, description="Módulo origen: 'custom', 'extraction', 'etl', 'graphics'")
    name: str = Field(index=True, description="Nombre descriptivo del script")
    description: Optional[str] = Field(default=None, sa_column=Column(Text), description="Descripción funcional")
    tags: List[str] = Field(default=[], sa_column=Column(JSON), description="Tags para búsqueda")
    
    # === PERSISTENCIA HÍBRIDA ===
    script_path: str = Field(description="Ruta relativa al archivo .py en storage")
    doc_path: Optional[str] = Field(default=None, description="Ruta relativa a documentación .md")
    code_hash: str = Field(description="SHA256 del código para integridad")
    
    model_config = {"extra": "allow"}
    
    _code: Optional[str] = PrivateAttr(default=None)
    
    @property
    def code(self) -> Optional[str]:
        # Safety check for uninitialized private attributes
        if getattr(self, '__pydantic_private__', None) is None:
            return None
        return self._code
        
    @code.setter
    def code(self, value: Optional[str]):
        if getattr(self, '__pydantic_private__', None) is None:
            self.__pydantic_private__ = {}
        self._code = value
    
    # === CONTRATOS Y CONFIGURACIÓN ===
    ui_contract: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Contrato UI para ejecución")
    data_contract: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Contrato de datos (schema)")
    execution_mode: str = Field(default="local", description="local, remote, hybrid")
    visualization_config: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Config visualización")
    
    # === METADATOS DE ORIGEN ===
    source_automation_id: Optional[str] = Field(default=None, description="ID de automatización origen (si aplica)")
    source_metadata: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Metadata específica del módulo")
    user_prompt: Optional[str] = Field(default=None, sa_column=Column(Text), description="Prompt original del usuario")
    
    # === ESTADO Y PROMOCIÓN ===
    status: str = Field(default="draft", index=True, description="draft, validated, published")
    validation_errors: Optional[str] = Field(default=None, sa_column=Column(Text), description="Errores de validación AST")
    
    # === ESTADÍSTICAS ===
    execution_count: int = Field(default=0, description="Veces ejecutado")
    success_count: int = Field(default=0, description="Ejecuciones exitosas")
    last_executed: Optional[datetime] = Field(default=None, description="Última ejecución")
    avg_execution_time_ms: int = Field(default=0, description="Tiempo promedio ejecución")
    
    # === AUDITORÍA ===
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(default=None, description="Usuario creador")
    is_favorite: bool = Field(default=False, description="Marcado como favorito")
    
    def __repr__(self):
        return f"<ScriptLibrary {self.id}: [{self.source_module}] {self.name}>"


class CustomScriptExecution(SQLModel, table=True):
    """
    Registro de ejecuciones de scripts personalizados.
    CS-01 implementation.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    script_id: int = Field(foreign_key="customscript.id", index=True)

    # === EJECUCIÓN ===
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(default=None)
    duration_ms: int = Field(default=0)

    # === ESTADO ===
    status: str = Field(default="running", description="running, success, error")
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))

    # === I/O ===
    input_files: List[str] = Field(default=[], sa_column=Column(JSON))
    output_files: List[str] = Field(default=[], sa_column=Column(JSON))
    output_preview: Optional[str] = Field(default=None, sa_column=Column(Text), description="Preview del resultado")

    # === RECURSOS ===
    peak_memory_mb: Optional[float] = Field(default=None)


class PendingScreenshotReview(SQLModel, table=True):
    """
    Capturas de pantalla pendientes de revisión por el usuario.

    Se crean cuando un workflow en background necesita enviar una
    captura pero la política requiere revisión humana.
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    # Contexto de ejecución
    execution_id: str = Field(index=True, description="ID de la ejecución del workflow")
    task_id: int = Field(description="ID del TaskLog asociado")
    step_index: int = Field(description="Índice del paso que falló")

    # Captura
    screenshot_path: str = Field(description="Ruta al archivo de captura")
    source_url: str = Field(description="URL de origen")
    reason: str = Field(description="Motivo: auto_healing, design_assist, etc.")

    # Estado
    status: str = Field(default="pending", description="pending|approved|rejected|expired")
    reviewed_at: Optional[datetime] = Field(default=None)
    reviewer_notes: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Auditoría
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None, description="Expiración automática")


class AtomRegistry(SQLModel, table=True):
    """
    Catálogo de átomos reutilizables para el editor de flujos.

    Un átomo es una acción mínima y reutilizable que puede formar parte
    de múltiples flujos. Define el tipo de paso, su configuración esperada
    (JSON Schema) y valores por defecto.

    EXTENDIDO: Ahora soporta conexiones (atom_type=CONNECTION con subtype)
    y contratos de datos (input_contract, output_contract, dependencies).

    Prompt 1.1 del plan de refactorización del editor de flujos.
    Data Contracts Fase 1, Prompt 1.
    """
    __tablename__ = "atom_registry"

    id: Optional[int] = Field(default=None, primary_key=True)

    # === IDENTIFICACIÓN ===
    name: str = Field(index=True, description="Nombre descriptivo del átomo")
    atom_type: StepType = Field(
        sa_column=Column(Text),
        description="Tipo de paso: extraction, email, connection, etc."
    )

    # === SUBTIPO (para conexiones) ===
    subtype: Optional[str] = Field(
        default=None,
        description="Subtipo de conexión: EMAIL, API, DATABASE, FTP (solo para CONNECTION)"
    )

    description: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="Descripción para el usuario"
    )

    # === CONFIGURACIÓN ===
    config_schema: str = Field(
        sa_column=Column(Text),
        description="JSON Schema que define los campos de configuración"
    )
    default_config: Optional[str] = Field(
        default="{}",
        sa_column=Column(Text),
        description="Configuración por defecto (JSON)"
    )

    # === CONTRATOS DE DATOS ===
    input_contract: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="JSON Schema que define los datos de entrada esperados"
    )
    output_contract: Optional[str] = Field(
        default=None, sa_column=Column(Text),
        description="JSON Schema que define los datos de salida"
    )

    # === CAPACIDADES UI ===
    has_stepper: bool = Field(default=True, description="Si el átomo usa el stepper de ajustes")
    has_variables: bool = Field(default=True, description="Si el átomo expone variables de salida")

    # === METADATA ===
    dependencies: Optional[str] = Field(
        default="[]",
        description="Lista de dependencias (JSON array de strings)"
    )

    # === VERSIONADO ===
    version: str = Field(
        default="1.0.0",
        description="Versión semántica del átomo"
    )
    status: str = Field(default="DRAFT", index=True)  # DRAFT | PUBLISHED | DEPRECATED

    # === CLASIFICACIÓN ===
    is_active: bool = Field(
        default=True,
        description="Si el átomo está activo y disponible para uso"
    )

    # === DATOS DE EJEMPLO (para previsualización en diseño de flujos) ===
    sample_data: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description=(
            "JSON con datos de ejemplo para previsualización: "
            '{"rows": [...], "columns": [...], "generated_at": "...", "source": "manual|auto"}'
        )
    )

    # === AUDITORÍA ===
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class FlowStep(SQLModel, table=True):
    """
    Relación entre flujos y átomos - representa un paso dentro de un flujo.

    Permite que un flujo tenga múltiples átomos ordenados, y que el mismo
    átomo pueda reutilizarse en múltiples flujos con configuraciones
    personalizadas.

    Prompt 1.2 del plan de refactorización del editor de flujos.
    """
    __tablename__ = "flow_step"

    id: Optional[int] = Field(default=None, primary_key=True)

    # === RELACIONES ===
    flow_id: int = Field(
        foreign_key="flowregistry.id",
        index=True,
        description="ID del flujo al que pertenece este paso"
    )
    atom_id: Optional[int] = Field(
        default=None,
        foreign_key="atom_registry.id",
        index=True,
        description="ID del átomo base (nullable para pasos legacy sin átomo)"
    )

    # === ORDENAMIENTO ===
    step_order: int = Field(
        default=0,
        description="Orden del paso dentro del flujo (0-indexed)"
    )

    # === PERSONALIZACIÓN ===
    custom_name: Optional[str] = Field(
        default=None,
        description="Nombre personalizado para este uso del átomo"
    )
    custom_config: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="JSON que sobrescribe/extiende el default_config del átomo"
    )
    output_var_name: Optional[str] = Field(
        default=None,
        description="Nombre de la variable de salida (ej: 'datos_factura')"
    )

    # === AUDITORÍA ===
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AutomatismPackage(SQLModel, table=True):
    """
    Almacena información de paquetes exportados/importados de automatismos.

    Un paquete es un archivo .automatia (ZIP) que contiene scripts, playbooks
    y/o workflows con sus metadatos y firma de integridad.

    Prompt 1.1 del sistema de exportación/importación de automatismos.
    """
    __tablename__ = "automatism_package"

    id: Optional[int] = Field(default=None, primary_key=True)

    # === IDENTIFICACIÓN ===
    package_id: str = Field(unique=True, index=True, description="UUID único del paquete")
    name: str = Field(description="Nombre descriptivo del paquete")
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    package_type: PackageType = Field(
        sa_column=Column(Text),
        description="Tipo: scripts, playbooks, workflow, mixed"
    )

    # === ORIGEN ===
    source_license_id: str = Field(description="ID de licencia de origen")
    source_client_id: str = Field(description="ID de cliente de origen")
    source_partner_id: str = Field(description="ID de partner de origen")
    source_machine_id: Optional[str] = Field(default=None, description="ID de máquina de origen")

    # === FIRMA (del manifiesto, no de archivos individuales) ===
    signature_type: str = Field(description="CLIENT o PARTNER")
    signer_id: str = Field(description="ID del firmante (cliente o partner)")
    signature_value: str = Field(sa_column=Column(Text), description="Valor de la firma")
    signed_at: datetime = Field(description="Momento de la firma")

    # === CONTENIDO (resumen) ===
    manifest_hash: str = Field(description="SHA256 del manifest.json")
    package_hash: str = Field(description="SHA256 del ZIP completo")
    scripts_count: int = Field(default=0, description="Número de scripts en el paquete")
    playbooks_count: int = Field(default=0, description="Número de playbooks en el paquete")
    workflows_count: int = Field(default=0, description="Número de workflows en el paquete")

    # === DEPENDENCIAS (para tipo WORKFLOW) ===
    dependencies_json: Optional[str] = Field(
        default=None,
        sa_column=Column(Text),
        description="JSON con IDs de scripts/playbooks incluidos como dependencias"
    )

    # === AUDITORÍA ===
    created_at: datetime = Field(default_factory=datetime.utcnow)
    exported_at: Optional[datetime] = Field(default=None, description="Momento de exportación")
    imported_at: Optional[datetime] = Field(default=None, description="Momento de importación")
    imported_by_license_id: Optional[str] = Field(
        default=None,
        description="ID de licencia que importó el paquete"
    )

    # === ESTADO ===
    status: PackageStatus = Field(
        default=PackageStatus.CREATED,
        sa_column=Column(Text),
        description="Estado: created, exported, imported, rejected"
    )




class WizardDraft(SQLModel, table=True):
    """
    Stores partial progress of wizard assistants (e.g. ScriptCreationWizard).
    Allows draft recovery across app sessions.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    wizard_type: str = Field(index=True, description="Type: 'custom_script', 'extraction', etc.")
    current_phase: str = Field(description="Last saved phase/step")
    data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Complete wizard state as JSON")
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RunManifestLog(SQLModel, table=True):
    """
    Registra métricas de ejecución de llamadas al Brain (IA).
    Utilizado para telemetría, facturación y análisis de consumo.
    Prompt 16 - Telemetría (Client).
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # === IDENTIFICACIÓN ===
    execution_id: str = Field(index=True, description="UUID de la ejecución")
    client_id: Optional[str] = Field(default=None, description="ID del cliente para servidor (UUID)")
    service_id: str = Field(index=True, description="ID del servicio (ej: sys_script_generation)")
    
    # === MÉTRICAS DE CONSUMO ===
    model_used: str = Field(description="Nombre del modelo (ej: gpt-4o)")
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    duration_ms: int = Field(default=0)
    
    # === ESTADO ===
    status: str = Field(default="success", description="success, error")
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # === SINCRONIZACIÓN ===
    is_synced: bool = Field(default=False, index=True, description="Si ya se envió al servidor")
    synced_at: Optional[datetime] = Field(default=None)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TriggerStatus(str, Enum):
    CONFIGURED = "CONFIGURED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ERROR = "ERROR"


class TriggerConfig(SQLModel, table=True):
    """
    Configuración unificada para disparadores (Watchers/Triggers).
    Modelo unificado que reemplaza FolderWatcherConfig, WebWatcherConfig, etc.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    type: str = Field(index=True, description="file, mail, web, schedule, api")
    description: Optional[str] = None
    
    # Estado
    status: TriggerStatus = Field(default=TriggerStatus.CONFIGURED)
    is_active: bool = Field(default=False) # Helper booleano
    
    # Configuración específica (JSON)
    # File: path, extensions, recursive
    # Mail: credentials, folders, subjects
    # Web: url, selector, mode
    # Schedule: cron, interval
    configuration: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    
    # Filtros pre-procesamiento
    file_extensions: List[str] = Field(default=[], sa_column=Column(JSON))
    subject_patterns: List[str] = Field(default=[], sa_column=Column(JSON))
    content_selectors: Optional[str] = Field(default=None)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    error_count: int = Field(default=0)
    last_error: Optional[str] = None


class TriggerSubscription(SQLModel, table=True):
    """
    Relación N:M entre Triggers y Flujos.
    Un trigger puede iniciar múltiples flujos.
    """
    __tablename__ = "trigger_subscriptions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    trigger_id: int = Field(foreign_key="triggerconfig.id", index=True)
    flow_id: int = Field(foreign_key="flowregistry.id", index=True)
    
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

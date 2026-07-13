"""
Modelos de base de datos del lado del servidor para AutomatIA Brain (SaaS).

Estos modelos se almacenan en brain_server.db y contienen:
- Configuración de IA y ajustes de modelos.
- Registros de consumo de tokens (facturación).
- Prompts del sistema y configuraciones de servicios de extracción.
- Datos de precios de modelos.
"""

from datetime import datetime
from typing import Optional, Dict, List, Any
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON, Text
import json
from automatia_shared.enums import ScreenshotPolicyEnum, AutomationType
from pydantic import field_validator, field_serializer, ConfigDict

from automatia_shared.enums import LicenseStatus


class AIConfig(SQLModel, table=True):
    """
    Persiste la configuración de proveedor/modelo por rol.

    Los roles definen el nivel de capacidad (Tier):
    - extraccion_pdf: Extracción rápida de texto (Tier 1).
    - logico_navegacion: Lógica y razonamiento (Tier 2).
    - supervision: Tareas complejas y generación de código (Tier 3).
    """

    role_key: str = Field(
        primary_key=True,
        description="Unique role key (e.g., 'extraccion_pdf', 'supervision')",
    )
    provider: str = Field(description="AI provider: 'google', 'openrouter'")
    model_id: str = Field(description="Model identifier")
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TokenLog(SQLModel, table=True):
    """
    Registro unificado de consumo de tokens para fines de facturación.

    Almacena todas las llamadas a la API de los proveedores de LLM,
    permitiendo el cálculo de costes y auditoría de uso.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    script_source: str = Field(description="Module that made the call")
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float = Field(default=0.0, description="Calculated cost in USD")


class ExtractionServiceConfig(SQLModel, table=True):
    """
    Configuración para servicios de extracción, incluyendo los system prompts.

    Niveles de alcance:
    - SYSTEM: Prompts definidos por el sistema (inmutables).
    - PARTNER: Prompts personalizados por el Distribuidor.
    - CLIENT: Sobrescrituras específicas por Cliente.
    """

    service_id: str = Field(
        primary_key=True, description="Internal ID (e.g., 'sys_phase0_discovery')"
    )
    name: str = Field(description="Human-readable name")
    module: str = Field(
        default="extraction", description="Module this prompt belongs to"
    )
    target_function: Optional[str] = Field(
        default=None, description="Function that uses this prompt"
    )
    description: Optional[str] = None
    system_prompt_template: str = Field(
        sa_column=Column(Text), description="The prompt template"
    )
    expected_schema: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    suggested_model: Optional[str] = Field(
        default=None, description="Recommended model for this prompt"
    )
    tier_override: Optional[int] = Field(
        default=None,
        description="Override tier: 1=Flash, 2=Logic, 3=Supervision. None=use role default",
    )

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


class ModelPricing(SQLModel, table=True):
    """
    Datos de precios de modelos por cada millón de tokens.

    Sincronizado periódicamente a través de la API de OpenRouter.
    """

    id: str = Field(
        primary_key=True, description="Model ID (e.g., 'google/gemini-1.5-flash')"
    )
    input_cost_per_m: float = Field(description="Cost per 1M input tokens")
    output_cost_per_m: float = Field(description="Cost per 1M output tokens")
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ModelCache(SQLModel, table=True):
    """
    Caché de modelos disponibles por proveedor.

    Evita llamadas repetitivas a la API para obtener la lista de modelos.
    """

    provider: str = Field(
        primary_key=True, description="Provider: 'google', 'openrouter', 'ollama'"
    )
    models: List[str] = Field(default=[], sa_column=Column(JSON))
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class AutomationLibrary(SQLModel, table=True):
    """
    Repositorio central de automatizaciones (scripts y flujos).

    Soporta versionado, firmas criptográficas y grupos de acceso para
    una distribución segura de componentes.
    """

    __tablename__ = "automation_library"

    id: str = Field(primary_key=True, index=True)
    name: str = Field(index=True)
    type: AutomationType
    code_content: str = Field(sa_column=Column(Text))
    version: int = 1
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Jerarquía y Seguridad
    client_id: Optional[str] = Field(default=None, index=True)
    partner_id: Optional[str] = Field(default=None, index=True)
    is_system_template: bool = Field(default=False)

    # --- NUEVOS CAMPOS (Sincronizados con DTO v2.0) ---
    signature: Optional[str] = Field(default=None)  # Firma del Partner/Superadmin
    is_workflow: bool = Field(
        default=False
    )  # Distingue script simple de flujo complejo
    # Almacenado como JSON/Array en la BD
    access_groups: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    # --------------------------------------------------

    metadata_json: Optional[Dict[str, Any]] = Field(default={}, sa_column=Column(JSON))


# === MULTITENANCY MODELS (Future - Phase 1) ===


class SuperAdminAccount(SQLModel, table=True):
    """
    Cuenta de Superadministrador del Sistema.

    Gestiona la plataforma global, admins y configuraciones de IA.
    """

    model_config = ConfigDict(validate_assignment=True)

    admin_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False)
    email: str = Field(nullable=False, sa_column_kwargs={"unique": True}, index=True)
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.lower()
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v.strip()


class AdminAccount(SQLModel, table=True):
    """
    Cuenta de Administrador (gestor de organizaciones) para multi-tenencia.

    Los Admins administran múltiples organizaciones y sus créditos.
    """

    partner_id: str = Field(primary_key=True)
    name: str
    email: str = Field(nullable=False)
    credits_balance: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ClientAccount(SQLModel, table=True):
    """
    Cuenta de cliente vinculada a un Partner.

    Representa a la entidad final que utiliza la plataforma en su entorno.
    """

    client_id: str = Field(primary_key=True)
    partner_id: str = Field(foreign_key="adminaccount.partner_id")
    name: str
    email: str = Field(nullable=False)
    nif: Optional[str] = Field(default=None, description="Tax ID (NIF/CIF)")
    license_key: str = Field(description="Hashed license key for authentication")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class License(SQLModel, table=True):
    """
    Información de licencia para un cliente.

    Controla las cuotas de tokens, periodos de validez y límites de
    asientos (dispositivos) permitidos.
    """

    license_id: str = Field(primary_key=True)
    client_id: str = Field(foreign_key="clientaccount.client_id")
    quota_tokens: int = Field(default=100000)
    consumed_tokens: int = Field(default=0)
    valid_until: datetime
    status: str = Field(default=LicenseStatus.ACTIVE.value)
    max_seats: int = Field(
        default=1, description="Número máximo de dispositivos únicos permitidos"
    )

    @property
    def remaining_tokens(self) -> int:
        """Calculate remaining tokens in quota."""
        return max(0, self.quota_tokens - self.consumed_tokens)

    def is_valid(self) -> bool:
        """Check if license is currently valid."""
        if self.status != LicenseStatus.ACTIVE.value:
            return False
        if self.consumed_tokens >= self.quota_tokens:
            return False
        if datetime.utcnow() > self.valid_until:
            return False
        return True


class LicenseActivation(SQLModel, table=True):
    """
    Registro de activaciones de licencia por dispositivo.
    Permite controlar qué máquinas están usando cada licencia (multiasiento).
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    license_id: str = Field(foreign_key="license.license_id", index=True)
    machine_id: str = Field(
        index=True, description="Identificador único del hardware del cliente"
    )
    device_name: Optional[str] = Field(
        default=None,
        description="Nombre descriptivo del dispositivo (ej: 'PC de Juan')",
    )
    activated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Fecha de primera activación"
    )
    last_seen: datetime = Field(
        default_factory=datetime.utcnow, description="Última conexión del dispositivo"
    )


class BillingRecord(SQLModel, table=True):
    """
    Registro de facturación por consumo de tokens.

    Vincula el consumo específico de un cliente con su Partner para los
    procesos de facturación y liquidación.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    partner_id: str = Field(foreign_key="adminaccount.partner_id")
    client_id: str = Field(foreign_key="clientaccount.client_id")
    operation: str
    tokens_used: int
    model_id: str
    cost_usd: float = Field(default=0.0)


class TrustedScript(SQLModel, table=True):
    """
    Scripts firmados y confiables para ejecución segura.

    Almacena los scripts que han pasado procesos de validación y firma.
    """

    script_id: str = Field(primary_key=True)
    name: str
    code: str = Field(sa_column=Column(Text))
    code_hash: str = Field(description="SHA256 hash for integrity")
    status: str = Field(default="draft")  # draft, published, deprecated
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LicenseAuditLog(SQLModel, table=True):
    """
    Audit log de cambios en licencias.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    license_id: str = Field(foreign_key="license.license_id", index=True)
    action: str = Field(description="Accion: QUOTA_INCREASED, SUSPENDED, etc.")
    details: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
    performed_by: str = Field(description="Partner que realizo la accion")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ScriptEscalation(SQLModel, table=True):
    """
    Scripts escalados de Cliente a Partner para su revisión o corrección.

    Permite un flujo de soporte donde el Partner puede arreglar lógica
    compleja o extracción fallida.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    partner_id: str = Field(foreign_key="adminaccount.partner_id", index=True)
    client_id: str = Field(foreign_key="clientaccount.client_id", index=True)
    script_name: str
    original_code: str = Field(sa_column=Column(Text))
    escalation_type: str = Field(
        default="extraction", description="extraction, custom_script"
    )
    status: str = Field(default="PENDING")  # PENDING, RESOLVED, REJECTED
    client_notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ServerSecurityPolicy(SQLModel, table=True):
    """
    Política de seguridad con cascada: SYSTEM < PARTNER < CLIENT.

    El alcance determina el nivel de la política:
    - SYSTEM: Política por defecto global.
    - PARTNER: Política para todos los clientes de un partner.
    - CLIENT: Política específica para un único cliente.

    Orden de resolución: CLIENT > PARTNER > SYSTEM (gana el más específico).
    """

    __tablename__ = "server_security_policy"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Scope determines the policy level
    scope: str = Field(default="SYSTEM", description="SYSTEM, PARTNER, or CLIENT")
    partner_id: Optional[str] = Field(
        default=None, foreign_key="adminaccount.partner_id", index=True
    )
    client_id: Optional[str] = Field(
        default=None, foreign_key="clientaccount.client_id", index=True
    )

    # Allowed domains (JSON array). ["*"] = all domains allowed
    allowed_domains: str = Field(
        default='["*"]',
        sa_column=Column(Text),
        description="JSON array of allowed domains. Use ['*'] for all.",
    )

    # Allowed libraries (JSON array)
    allowed_libraries: str = Field(
        default='["pandas", "json", "re", "math", "datetime", "openpyxl", "xlrd", "numpy"]',
        sa_column=Column(Text),
        description="JSON array of allowed Python libraries",
    )

    # Forbidden libraries (JSON array) - take precedence over allowed
    forbidden_libraries: str = Field(
        default='["os", "sys", "subprocess", "requests", "socket", "shutil", "ctypes"]',
        sa_column=Column(Text),
        description="JSON array of forbidden Python libraries",
    )

    # === SCREENSHOT POLICY ===
    screenshot_policy: str = Field(
        default=ScreenshotPolicyEnum.REVIEW.value,
        description="BLOCK|REVIEW|TRUSTED - política de envío de capturas",
    )
    trusted_screenshot_domains: str = Field(
        default="[]",
        sa_column=Column(Text),
        description="JSON list de dominios permitidos en modo TRUSTED",
    )

    # Resource limits
    max_execution_time: int = Field(
        default=300, description="Max execution time in seconds"
    )
    max_memory_mb: int = Field(default=512, description="Max memory in MB")

    # Metadata
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SchedulerConfig(SQLModel, table=True):
    """
    Configuración para el programador de tareas en segundo plano.

    Controla tareas automatizadas como la actualización de la caché de modelos.
    """

    id: int = Field(default=1, primary_key=True)
    enabled: bool = Field(default=True, description="Whether scheduler is enabled")
    refresh_hour: int = Field(default=3, description="Hour to run daily refresh (0-23)")
    refresh_minute: int = Field(
        default=0, description="Minute to run daily refresh (0-59)"
    )
    last_run: Optional[datetime] = Field(
        default=None, description="Timestamp of last successful run"
    )
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SystemPrompt(SQLModel, table=True):
    """
    Prompts del Sistema para el AI Brain.

    Almacenados en el servidor para mayor seguridad y una gestión
    centralizada de las instrucciones de la IA.
    """

    id: Optional[int] = Field(default=None, primary_key=True)

    # Identification
    name: str = Field(
        index=True,
        unique=True,
        description="Unique ID: 'script_generator', 'flow_orchestrator'",
    )
    version: str = Field(default="1.0", description="Prompt versioning")

    # Content
    content: str = Field(
        sa_column=Column(Text), description="Full text of the system prompt"
    )

    # Context type
    context_type: str = Field(
        default="generic", description="Type: 'catalog_aware', 'generic', 'copilot'"
    )

    # Tier constraints
    tier: Optional[str] = Field(
        default=None, description="Required tier: 'FLASH', 'PRO', 'ULTRA' (None = all)"
    )

    # State
    is_active: bool = Field(default=True, description="Active status")

    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ClientTelemetryLog(SQLModel, table=True):
    """
    Log de telemetría sincronizado desde el cliente.
    Almacena métricas de ejecución, errores y tiempos para observabilidad centralizada.
    """

    id: Optional[int] = Field(default=None, primary_key=True)

    # Origen
    client_id: str = Field(foreign_key="clientaccount.client_id", index=True)
    machine_id: str = Field(index=True)

    # Identificadores de ejecución
    manifest_id: str = Field(
        index=True, description="ID único de ejecución generado en cliente"
    )
    script_hash: Optional[str] = Field(default=None)

    # Métricas
    execution_time_ms: int = Field(default=0)
    total_tokens: int = Field(default=0)
    cost_estimated: float = Field(default=0.0)

    # Estado
    status: str = Field(default="unknown")  # success, error
    error_type: Optional[str] = None
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Timestamps
    timestamp_client: datetime = Field(description="Hora de ejecución en cliente")
    synced_at: datetime = Field(
        default_factory=datetime.utcnow, description="Hora de recepción en servidor"
    )

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from sqlmodel import SQLModel, Field, Column, JSON, Text
from sqlalchemy import event

class ActionType(str, Enum):
    """Tipos de acciones auditables."""
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    EXPORT = "export"
    IMPORT = "import"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    ANONYMIZE = "anonymize"
    DEANONYMIZE = "deanonymize"
    APPROVE = "approve"
    REJECT = "reject"
    SYSTEM = "system"

class RiskLevel(str, Enum):
    """Niveles de riesgo para auditoría."""
    LOW = "low"         # Operaciones rutinarias (lectura)
    MEDIUM = "medium"   # Cambios de configuración, escrituras no críticas
    HIGH = "high"       # Acceso a PII, cambios críticos, borrados
    CRITICAL = "critical" # Fallos de seguridad, acceso no autorizado

class EnterpriseAuditLog(SQLModel, table=True):
    """
    Registro inmutable de auditoría para trazabilidad de operaciones
    especialmente las relacionadas con PII.
    """
    __tablename__ = "enterprise_audit_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    user_id: Optional[str] = Field(default=None, index=True)
    action_type: str = Field(index=True)  # Debería ser ActionType, pero SQLModel + Enum a veces da problemas en SQLite
    module: str = Field(index=True)
    task_log_id: Optional[int] = Field(default=None, foreign_key="tasklog.id")
    execution_id: Optional[str] = Field(default=None, index=True)

    # Métricas de Privacidad
    pii_detected_count: int = Field(default=0)
    pii_protected_count: int = Field(default=0)
    pii_types: Dict[str, int] = Field(default={}, sa_column=Column(JSON))
    anonymization_method: Optional[str] = None

    # Contexto
    source_description: Optional[str] = None
    target_description: Optional[str] = None
    ip_address: Optional[str] = None
    additional_context: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Seguridad
    risk_level: str = Field(default=RiskLevel.LOW.value, index=True)
    security_flags: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)

# Event listener for immutability check should be registered where the model is used/imported
# or we can include a helper to register it.
def register_immutability_listener():
    """
    Registra listeners de SQLAlchemy para prevenir la modificación de registros de auditoría.
    """
    @event.listens_for(EnterpriseAuditLog, "before_update")
    def receive_before_update(mapper, connection, target):
        """
        Callback de SQLAlchemy que lanza un error si se intenta actualizar un log de auditoría.
        """
        raise RuntimeError("Audit logs are immutable")

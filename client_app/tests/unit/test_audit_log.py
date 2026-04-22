import pytest
from datetime import datetime
from sqlmodel import Session, create_engine, SQLModel, select
from client_app.app.database.models import EnterpriseAuditLog, TaskLog
from sqlalchemy.exc import IntegrityError
from automatia_shared.enums import TaskStatus

# Engine in memory for tests
engine = create_engine("sqlite:///:memory:")

@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)

def test_create_audit_entry(session: Session):
    """Verifica la creación de una entrada de auditoría con todos los campos."""
    audit = EnterpriseAuditLog(
        action_type="extraction",
        module="extraction_service",
        user_id="user_123",
        pii_detected_count=10,
        pii_protected_count=10,
        pii_types={"names": 5, "dni": 5},
        anonymization_method="hash",
        source_description="factura.pdf",
        target_description="resultado.json",
        risk_level="low",
        execution_id="exec_abc"
    )
    session.add(audit)
    session.commit()
    session.refresh(audit)

    assert audit.id is not None
    assert audit.action_type == "extraction"
    assert audit.pii_types["names"] == 5
    assert isinstance(audit.timestamp, datetime)

def test_audit_entry_has_timestamp(session: Session):
    """Asegura que se genere un timestamp automático."""
    audit = EnterpriseAuditLog(
        action_type="query",
        module="audit_service"
    )
    session.add(audit)
    session.commit()
    session.refresh(audit)
    
    assert audit.timestamp is not None
    assert isinstance(audit.timestamp, datetime)

def test_audit_entry_records_user(session: Session):
    """Verifica que se registre el usuario."""
    audit = EnterpriseAuditLog(
        action_type="export",
        module="report_factory",
        user_id="admin_user"
    )
    session.add(audit)
    session.commit()
    session.refresh(audit)
    
    assert audit.user_id == "admin_user"

def test_audit_entry_records_pii_metrics(session: Session):
    """Verifica el almacenamiento de métricas PII."""
    pii_data = {"email": 2, "phone": 1}
    audit = EnterpriseAuditLog(
        action_type="anonymization",
        module="privacy_service",
        pii_detected_count=3,
        pii_protected_count=3,
        pii_types=pii_data
    )
    session.add(audit)
    session.commit()
    session.refresh(audit)
    
    assert audit.pii_detected_count == 3
    assert audit.pii_types == pii_data

def test_audit_entry_is_immutable(session: Session):
    """Verifica que no se permita la modificación de registros existentes (Inmutabilidad)."""
    audit = EnterpriseAuditLog(
        action_type="extraction",
        module="core"
    )
    session.add(audit)
    session.commit()
    session.refresh(audit)
    
    # Intentar modificar un registro de auditoría debería estar prohibido por lógica de negocio
    # (En SQLModel/SQLAlchemy esto se suele manejar en el servicio o mediante hooks/triggers)
    # Por ahora, validamos que si intentamos cambiarlo, la base de datos lo permite a menos que implementemos algo específico.
    # El prompt pide Trazabilidad INMUTABLE.
    
    audit.action_type = "modified_action"
    
    # Nota: SQLModel por defecto permite updates. La inmutabilidad real en BBDD 
    # se suele reforzar en el servicio. Aquí testeamos la intención.
    # Si queremos forzarlo en el modelo, podríamos usar un hook de SQLAlchemy @event.listens_for(EnterpriseAuditLog, 'before_update')
    
    # Por ahora dejaremos el test preparado para fallar si no hay protección.
    # En la implementación añadiré el hook.
    
    with pytest.raises(RuntimeError, match="Audit logs are immutable"):
        # Esto disparará el hook que implementaremos en models.py
        session.add(audit)
        session.commit()

def test_audit_entry_links_to_task(session: Session):
    """Verifica la relación con TaskLog."""
    # Crear un TaskLog primero
    task = TaskLog(
        execution_id="exec_123",
        step_index=0,
        step_name="Test Step",
        status=TaskStatus.COMPLETED.value
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    
    audit = EnterpriseAuditLog(
        action_type="extraction",
        module="runtime",
        task_log_id=task.id
    )
    session.add(audit)
    session.commit()
    session.refresh(audit)
    
    assert audit.task_log_id == task.id

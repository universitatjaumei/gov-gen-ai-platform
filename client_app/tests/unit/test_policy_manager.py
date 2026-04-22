# client_app/tests/unit/test_policy_manager.py
"""
Tests unitarios para PartnerPolicyManager.

Verifica:
- Aplicación de políticas de seguridad al auditor
- Cascada Partner > Cliente > Sistema
- Intersección de imports permitidos
- Carga desde base de datos
"""
import pytest
from pathlib import Path
from sqlmodel import create_engine, Session, SQLModel
from automatia_shared.core.security import SecurityAuditor, SAFE_IMPORTS
from app.modules.security.policy_manager import PartnerPolicyManager
from app.database.models import SecurityPolicy


@pytest.fixture
def db_session(tmp_path: Path):
    """Create in-memory database session for testing"""
    db_path = tmp_path / "test_policy.db"
    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


def test_apply_policy_overrides():
    """Test que las políticas se aplican correctamente al auditor."""
    policy = {
        "forbidden_imports": ["json"],  # añade restricciones
        "allowed_imports": ["pandas"],  # intersecta con whitelist base
        "max_execution_time": 30,
        "max_memory_mb": 256,
    }
    auditor = SecurityAuditor()
    mgr = PartnerPolicyManager(policy)
    mgr.apply_to_auditor(auditor)

    assert "json" in auditor.unsafe_imports
    assert mgr.get_timeout() == 30
    assert mgr.get_memory_limit() == 256


def test_policy_cascade_partner_over_client():
    """Partner policy overrides client policy."""
    client_policy = {"max_execution_time": 60}
    partner_policy = {"max_execution_time": 30}

    mgr = PartnerPolicyManager(
        client_policy=client_policy,
        partner_policy=partner_policy
    )
    assert mgr.get_timeout() == 30  # Partner wins


def test_policy_cascade_client_over_system():
    """Client policy overrides system defaults."""
    client_policy = {"max_memory_mb": 256}

    mgr = PartnerPolicyManager(client_policy=client_policy)
    assert mgr.get_memory_limit() == 256  # Client overrides default 512


def test_get_allowed_imports_intersection():
    """Allowed imports = intersection of policy and base whitelist."""
    policy = {"allowed_imports": ["pandas", "requests"]}  # requests not in base
    mgr = PartnerPolicyManager(policy)

    allowed = mgr.get_allowed_imports()
    assert "pandas" in allowed
    assert "requests" not in allowed  # Filtered out (no está en SAFE_IMPORTS)


def test_load_policy_from_db(db_session):
    """Load policy from SecurityPolicy model."""
    sp = SecurityPolicy(
        name="test_policy",
        max_execution_time=45,
        max_memory_mb=384,
        allowed_imports='["pandas", "json"]',
        forbidden_imports='["requests"]',
    )
    db_session.add(sp)
    db_session.commit()

    mgr = PartnerPolicyManager.from_db(db_session, policy_name="test_policy")
    assert mgr.get_timeout() == 45
    assert mgr.get_memory_limit() == 384


def test_load_nonexistent_policy_from_db(db_session):
    """Cargar política inexistente devuelve manager con defaults."""
    mgr = PartnerPolicyManager.from_db(db_session, policy_name="nonexistent")
    # Debe usar defaults del sistema
    assert mgr.get_timeout() == 300
    assert mgr.get_memory_limit() == 512


def test_system_defaults_when_no_policy():
    """Sin políticas, se usan defaults del sistema."""
    mgr = PartnerPolicyManager()

    assert mgr.get_timeout() == 300
    assert mgr.get_memory_limit() == 512
    assert len(mgr.get_allowed_imports()) > 0


def test_forbidden_imports_added_to_auditor():
    """Los imports prohibidos se añaden al auditor."""
    policy = {"forbidden_imports": ["pandas", "numpy"]}
    auditor = SecurityAuditor()

    mgr = PartnerPolicyManager(policy)
    mgr.apply_to_auditor(auditor)

    assert "pandas" in auditor.unsafe_imports
    assert "numpy" in auditor.unsafe_imports


def test_policy_merge_allowed_imports():
    """Los allowed_imports son intersección con SAFE_IMPORTS."""
    # 'os' está en FORBIDDEN_IMPORTS, no debería pasar
    policy = {"allowed_imports": ["pandas", "os", "json"]}
    mgr = PartnerPolicyManager(policy)

    allowed = mgr.get_allowed_imports()
    assert "pandas" in allowed
    assert "json" in allowed
    assert "os" not in allowed  # Bloqueado por no estar en SAFE_IMPORTS


def test_cascade_all_levels():
    """Cascada completa: Partner > Cliente > Sistema."""
    # Sistema: timeout=300, memory=512
    client_policy = {
        "max_execution_time": 120,  # Override sistema
        "max_memory_mb": 256,  # Override sistema
    }
    partner_policy = {
        "max_execution_time": 60,  # Override cliente
        # max_memory_mb no definido, usa cliente
    }

    mgr = PartnerPolicyManager(
        client_policy=client_policy,
        partner_policy=partner_policy
    )

    assert mgr.get_timeout() == 60  # Partner (60) > Cliente (120) > Sistema (300)
    assert mgr.get_memory_limit() == 256  # Cliente (256) > Sistema (512)


def test_empty_policy_uses_defaults():
    """Política vacía usa defaults del sistema."""
    mgr = PartnerPolicyManager(client_policy={})

    assert mgr.get_timeout() == 300
    assert mgr.get_memory_limit() == 512


def test_get_effective_policy():
    """get_effective_policy devuelve toda la configuración efectiva."""
    client_policy = {"max_execution_time": 120}
    partner_policy = {"forbidden_imports": ["json"]}

    mgr = PartnerPolicyManager(
        client_policy=client_policy,
        partner_policy=partner_policy
    )

    effective = mgr.get_effective_policy()

    assert effective["max_execution_time"] == 120
    assert "json" in effective["forbidden_imports"]
    assert effective["max_memory_mb"] == 512  # Default


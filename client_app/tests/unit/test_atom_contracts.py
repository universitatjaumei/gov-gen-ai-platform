"""
Tests para el sistema de contratos de datos en átomos.
TDD: Estos tests DEBEN FALLAR inicialmente.
"""
import pytest
from sqlmodel import Session, create_engine, SQLModel
from client_app.app.database.models import AtomRegistry
from automatia_shared.enums import StepType


class TestAtomContractsSchema:
    """Tests para verificar que AtomRegistry soporta contratos."""
    
    @pytest.fixture
    def session(self):
        """Crear sesión de prueba en memoria."""
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            yield session
    
    def test_atom_has_subtype_field(self, session):
        """
        RED: Átomo debe tener campo 'subtype' para diferenciar
        tipos de conexión (EMAIL, API, DB).
        """
        # Note: We use string literal for "EMAIL" or just a string, 
        # checking if the field accepts it.
        try:
            atom = AtomRegistry(
                name="Email Corporativo",
                atom_type=StepType.CONNECTION if hasattr(StepType, 'CONNECTION') else "connection", # Fallback for test setup if enum doesn't exist yet
                subtype="EMAIL",  # ← Este campo NO existe aún
                config_schema='{"type": "object"}',
            )
            session.add(atom)
            session.commit()
            session.refresh(atom)
            assert atom.subtype == "EMAIL"
        except Exception as e:
            pytest.fail(f"Failed to create atom with subtype: {e}")
    
    def test_atom_has_input_contract_field(self, session):
        """
        RED: Átomo debe tener campo 'input_contract' (JSON).
        """
        try:
            atom = AtomRegistry(
                name="Mail Watcher",
                atom_type="email", # Using string to avoid attribute error if enum not updated
                input_contract='{"connection_id": "uuid"}',  # ← NO existe
                config_schema='{"type": "object"}',
            )
            session.add(atom)
            session.commit()
            session.refresh(atom)
            assert atom.input_contract is not None
        except Exception as e:
            pytest.fail(f"Failed to create atom with input_contract: {e}")
    
    def test_atom_has_output_contract_field(self, session):
        """
        RED: Átomo debe tener campo 'output_contract' (JSON).
        """
        try:
            atom = AtomRegistry(
                name="PDF Extractor",
                atom_type="extraction",
                output_contract='{"text": "string", "pages": "integer"}',  # ← NO existe
                config_schema='{"type": "object"}',
            )
            session.add(atom)
            session.commit()
            session.refresh(atom)
            assert atom.output_contract is not None
        except Exception as e:
            pytest.fail(f"Failed to create atom with output_contract: {e}")
    
    def test_atom_has_dependencies_field(self, session):
        """
        RED: Átomo debe tener campo 'dependencies' (lista de IDs).
        """
        try:
            connection_atom = AtomRegistry(
                name="Email Connection",
                atom_type="connection", # Placeholder
                config_schema='{"type": "object"}',
            )
            session.add(connection_atom)
            session.commit()
            
            watcher_atom = AtomRegistry(
                name="Mail Watcher",
                atom_type="email",
                dependencies=[connection_atom.id],  # ← NO existe
                config_schema='{"type": "object"}',
            )
            session.add(watcher_atom)
            session.commit()
            session.refresh(watcher_atom)
            
            assert connection_atom.id in watcher_atom.dependencies
        except Exception as e:
             pytest.fail(f"Failed to create atom with dependencies: {e}")
    
    def test_connection_type_exists_in_enum(self):
        """
        RED: StepType debe incluir CONNECTION.
        """
        assert hasattr(StepType, 'CONNECTION'), "StepType enum missing CONNECTION"
        assert StepType.CONNECTION == "connection"


class TestAtomContractsNullability:
    """Tests para verificar que campos de contratos son opcionales."""
    
    @pytest.fixture
    def session(self):
        engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            yield session
    
    def test_subtype_is_optional(self, session):
        """
        Subtype solo es requerido para CONNECTION, opcional para otros.
        """
        try:
            atom = AtomRegistry(
                name="PDF Extractor",
                atom_type="extraction",
                # subtype NO especificado
                config_schema='{"type": "object"}',
            )
            session.add(atom)
            session.commit()
            session.refresh(atom)
            
            # Use getattr to safely check if field exists, though failures above usually catch it
            assert getattr(atom, 'subtype', None) is None
        except Exception as e:
            # If it fails because kwarg doesn't exist, that's expected in RED
            pytest.fail(f"Creation failed: {e}")
    
    def test_contracts_default_to_none(self, session):
        """
        Contratos son opcionales (None por defecto).
        """
        try:
            atom = AtomRegistry(
                name="Simple Script",
                atom_type="custom_script",
                config_schema='{"type": "object"}',
            )
            session.add(atom)
            session.commit()
            session.refresh(atom)
            
            assert getattr(atom, 'input_contract', None) is None
            assert getattr(atom, 'output_contract', None) is None
            # Dependencies might be empty list or None depending on implementation default
            assert getattr(atom, 'dependencies', []) == []
        except Exception as e:
            pytest.fail(f"Creation failed: {e}")

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from client_app.app.services.flow_registry_service import FlowRegistryService
from client_app.app.services.atom_service import AtomService, atom_service
from client_app.app.database.models import FlowRegistry, AtomRegistry
from automatia_shared.enums import StepType
from automatia_shared.dtos import FlowSpec

# --- FLOW REGISTRY SERVICE TESTS ---

@pytest.fixture
async def db_session(test_client_db):
    """Fixture para crear sesión async a partir del engine de test"""
    async_session = sessionmaker(
        test_client_db, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

@pytest.fixture
def flow_service(db_session):
    return FlowRegistryService(db_session)

@pytest.mark.asyncio
async def test_create_flow_version_logic(flow_service):
    # 1. Crear el flujo original (PUBLISHED)
    original_spec = FlowSpec(
        name="Flow Original",
        steps=[],
        version="1.0.0",
        status="PUBLISHED"
    )
    original = await flow_service.create_flow(original_spec)
    
    # Asegurar que esté en PUBLISHED para el test (create_flow pone DRAFT por defecto)
    original.status = "PUBLISHED"
    flow_service.session.add(original)
    await flow_service.session.commit()
    
    # 2. Crear nueva versión
    new_version_flow = await flow_service.create_flow_version(original.id)
    
    # 3. Validaciones
    assert new_version_flow.id != original.id
    assert new_version_flow.version == "1.1.0"
    assert new_version_flow.status == "DRAFT"
    assert "Original v1.1.0" in new_version_flow.name
    assert new_version_flow.steps == original.steps

@pytest.mark.asyncio
async def test_create_flow_version_complex_semver(flow_service):
    # Test incremental 1.2.3 -> 1.3.0
    spec = FlowSpec(name="Complex Ver", steps=[], version="2.5.9")
    original = await flow_service.create_flow(spec)
    
    new_vf = await flow_service.create_flow_version(original.id)
    assert new_vf.version == "2.6.0"

# --- ATOM SERVICE TESTS ---

class TestAtomServiceVersioning:
    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.get = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_create_atom_new_version(self, mock_session):
        original_atom = AtomRegistry(
            id=10,
            name="Atom Pro",
            atom_type=StepType.EXTRACTION,
            version="2.1.5",
            status="PUBLISHED",
            config_schema="{}",
            is_active=True
        )
        
        mock_session.get.return_value = original_atom
        
        async def mock_refresh(obj):
            obj.id = 11
            
        mock_session.refresh = mock_refresh

        with patch('client_app.app.services.atom_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context
            
            # Instancia fresca para el test (singleton)
            from client_app.app.services.atom_service import AtomService
            svc = AtomService()
            
            new_atom = await svc.create_new_version(10)
            
            assert new_atom.version == "2.2.0"
            assert new_atom.status == "DRAFT"
            assert "Atom Pro v2.2.0" in new_atom.name
            assert new_atom.atom_type == StepType.EXTRACTION
            mock_session.add.assert_called_once()

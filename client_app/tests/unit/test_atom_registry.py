"""
Tests para el modelo AtomRegistry - Catálogo de átomos reutilizables.
Prompt 1.1 del plan de refactorización del editor de flujos.

TDD: Estos tests se escriben ANTES de implementar el modelo.
"""
import pytest
import json
from datetime import datetime
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from automatia_shared.enums import StepType
# Importar los modelos ANTES del fixture para que se registren en SQLModel.metadata
from client_app.app.database.models import AtomRegistry


@pytest.fixture
async def async_engine():
    """Crea un engine async en memoria para tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine):
    """Fixture para crear sesión async."""
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


class TestAtomRegistryModel:
    """Tests para el modelo AtomRegistry."""

    @pytest.mark.asyncio
    async def test_create_atom(self, db_session):
        """Crear un átomo con nombre, tipo y configuración básica."""
        atom = AtomRegistry(
            name="Extraer datos de factura PDF",
            atom_type=StepType.EXTRACTION,
            description="Extrae campos clave de facturas en formato PDF",
            config_schema=json.dumps({
                "type": "object",
                "properties": {
                    "config_id": {"type": "integer"}
                },
                "required": ["config_id"]
            }),
            default_config=json.dumps({"config_id": None}),
            version="1.0.0",
            is_active=True
        )

        db_session.add(atom)
        await db_session.commit()
        await db_session.refresh(atom)

        assert atom.id is not None
        assert atom.name == "Extraer datos de factura PDF"
        assert atom.atom_type == StepType.EXTRACTION
        assert atom.is_active is True

    @pytest.mark.asyncio
    async def test_atom_has_required_fields(self, db_session):
        """Validar que los campos obligatorios están presentes."""
        
        atom = AtomRegistry(
            name="Test Atom",
            atom_type=StepType.EMAIL,
            config_schema=json.dumps({"type": "object"})
        )

        db_session.add(atom)
        await db_session.commit()
        await db_session.refresh(atom)

        # Campos obligatorios
        assert atom.name is not None
        assert atom.atom_type is not None
        assert atom.config_schema is not None

        # Campos con defaults
        assert atom.is_active is True   # default
        assert atom.version == "1.0.0"  # default
        assert atom.created_at is not None

    @pytest.mark.asyncio
    async def test_atom_config_schema_is_valid_json(self, db_session):
        """El config_schema debe ser JSON válido que se puede parsear."""
        
        schema = {
            "type": "object",
            "properties": {
                "url": {"type": "string", "format": "uri"},
                "method": {"type": "string", "enum": ["GET", "POST"]},
                "timeout": {"type": "integer", "default": 30}
            },
            "required": ["url"]
        }

        atom = AtomRegistry(
            name="API Fetch Atom",
            atom_type=StepType.API_FETCH,
            config_schema=json.dumps(schema),
            default_config=json.dumps({"url": "", "method": "GET", "timeout": 30})
        )

        db_session.add(atom)
        await db_session.commit()
        await db_session.refresh(atom)

        # Verificar que se puede parsear
        parsed_schema = json.loads(atom.config_schema)
        assert parsed_schema["type"] == "object"
        assert "url" in parsed_schema["properties"]
        assert parsed_schema["required"] == ["url"]

        # Verificar default_config también
        parsed_default = json.loads(atom.default_config)
        assert parsed_default["method"] == "GET"
        assert parsed_default["timeout"] == 30

    @pytest.mark.asyncio
    async def test_list_atoms_by_type(self, db_session):
        """Filtrar átomos por tipo (extraction, email, api_fetch, etc.)."""
        
        # Crear varios átomos de diferentes tipos
        atoms_data = [
            ("Extracción PDF", StepType.EXTRACTION),
            ("Extracción XML", StepType.EXTRACTION),
            ("Enviar Email", StepType.EMAIL_SEND),
            ("Llamada API REST", StepType.API_FETCH),
            ("Transformación ETL", StepType.ETL_TRANSFORM),
        ]

        for name, atom_type in atoms_data:
            atom = AtomRegistry(
                name=name,
                atom_type=atom_type,
                config_schema=json.dumps({"type": "object"})
            )
            db_session.add(atom)

        await db_session.commit()

        # Filtrar por EXTRACTION
        stmt = select(AtomRegistry).where(AtomRegistry.atom_type == StepType.EXTRACTION)
        result = await db_session.execute(stmt)
        extraction_atoms = result.scalars().all()

        assert len(extraction_atoms) == 2
        assert all(a.atom_type == StepType.EXTRACTION for a in extraction_atoms)

        # Filtrar por EMAIL_SEND
        stmt = select(AtomRegistry).where(AtomRegistry.atom_type == StepType.EMAIL_SEND)
        result = await db_session.execute(stmt)
        email_atoms = result.scalars().all()

        assert len(email_atoms) == 1
        assert email_atoms[0].name == "Enviar Email"

    @pytest.mark.asyncio
    async def test_atom_versioning(self, db_session):
        """Un átomo puede tener múltiples versiones (mismo nombre, diferente version)."""
        
        # Crear versión 1.0.0
        atom_v1 = AtomRegistry(
            name="Extractor Universal",
            atom_type=StepType.EXTRACTION,
            config_schema=json.dumps({"type": "object"}),
            version="1.0.0",
            is_active=True
        )
        db_session.add(atom_v1)
        await db_session.commit()

        # Crear versión 2.0.0 (mejora)
        atom_v2 = AtomRegistry(
            name="Extractor Universal",
            atom_type=StepType.EXTRACTION,
            config_schema=json.dumps({
                "type": "object",
                "properties": {"new_field": {"type": "string"}}
            }),
            version="2.0.0",
            is_active=True
        )
        db_session.add(atom_v2)
        await db_session.commit()

        # Marcar v1 como inactiva (deprecada)
        atom_v1.is_active = False
        await db_session.commit()

        # Buscar todas las versiones del átomo
        stmt = select(AtomRegistry).where(AtomRegistry.name == "Extractor Universal")
        result = await db_session.execute(stmt)
        all_versions = result.scalars().all()

        assert len(all_versions) == 2
        versions = {a.version for a in all_versions}
        assert versions == {"1.0.0", "2.0.0"}

        # Buscar solo versiones activas
        stmt = select(AtomRegistry).where(
            AtomRegistry.name == "Extractor Universal",
            AtomRegistry.is_active == True
        )
        result = await db_session.execute(stmt)
        active_versions = result.scalars().all()

        assert len(active_versions) == 1
        assert active_versions[0].version == "2.0.0"

    @pytest.mark.asyncio
    async def test_atom_timestamps(self, db_session):
        """Verificar que created_at y updated_at se establecen correctamente."""
        
        before_create = datetime.utcnow()

        atom = AtomRegistry(
            name="Timestamp Test",
            atom_type=StepType.CUSTOM_SCRIPT,
            config_schema=json.dumps({"type": "object"})
        )

        db_session.add(atom)
        await db_session.commit()
        await db_session.refresh(atom)

        after_create = datetime.utcnow()

        # created_at debe estar entre before y after
        assert atom.created_at is not None
        assert before_create <= atom.created_at <= after_create

        # updated_at también debe estar establecido
        assert atom.updated_at is not None

    @pytest.mark.asyncio
    async def test_atom_description_optional(self, db_session):
        """La descripción es opcional."""
        
        # Sin descripción
        atom_no_desc = AtomRegistry(
            name="Sin Descripción",
            atom_type=StepType.WEBHOOK,
            config_schema=json.dumps({"type": "object"})
        )

        # Con descripción
        atom_with_desc = AtomRegistry(
            name="Con Descripción",
            atom_type=StepType.WEBHOOK,
            config_schema=json.dumps({"type": "object"}),
            description="Este átomo procesa webhooks entrantes"
        )

        db_session.add_all([atom_no_desc, atom_with_desc])
        await db_session.commit()

        await db_session.refresh(atom_no_desc)
        await db_session.refresh(atom_with_desc)

        assert atom_no_desc.description is None
        assert atom_with_desc.description == "Este átomo procesa webhooks entrantes"

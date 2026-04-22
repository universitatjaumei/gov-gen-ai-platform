"""
Tests para campos de trazabilidad de origen en Scripts y Playbooks.
Prompt 1.2 del sistema de exportación/importación de automatismos.

TDD: Estos tests se escriben ANTES de modificar los modelos.
"""
import pytest
import json
import hashlib
from datetime import datetime
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

# Importar los modelos ANTES del fixture para que se registren en SQLModel.metadata
from client_app.app.database.models import (
    CustomScript,
    RpaPlaybook,
    calculate_playbook_hash
)


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


class TestOriginTracking:
    """Tests para campos de trazabilidad de origen."""

    @pytest.mark.asyncio
    async def test_script_tracks_origin_package(self, db_session):
        """Script importado tiene origin_package_id."""
        script = CustomScript(
            name="Script Importado",
            description="Script que fue importado de otro cliente",
            user_prompt="Crear un script de extracción",
            code="def transform(df): return df",
            code_hash="abc123hash",
            # Campos de origen para scripts importados
            origin_license_id="LIC-ORIGEN-001",
            origin_package_id="PKG-UUID-12345678",
            original_status="published"
        )

        db_session.add(script)
        await db_session.commit()
        await db_session.refresh(script)

        # Verificar campos de origen
        assert script.origin_license_id == "LIC-ORIGEN-001"
        assert script.origin_package_id == "PKG-UUID-12345678"
        assert script.original_status == "published"

    @pytest.mark.asyncio
    async def test_script_origin_fields_optional(self, db_session):
        """Los campos de origen son opcionales (scripts creados localmente)."""
        script = CustomScript(
            name="Script Local",
            description="Script creado localmente",
            user_prompt="Crear un script simple",
            code="def transform(df): return df",
            code_hash="xyz789hash"
            # Sin campos de origen - script creado localmente
        )

        db_session.add(script)
        await db_session.commit()
        await db_session.refresh(script)

        # Los campos de origen deben ser None para scripts locales
        assert script.origin_license_id is None
        assert script.origin_package_id is None
        assert script.original_status is None

    @pytest.mark.asyncio
    async def test_playbook_has_content_hash(self, db_session):
        """Playbook tiene hash de su contenido JSON."""
        actions = [
            {"type": "click", "selector": "#btn"},
            {"type": "input", "selector": "#email", "value": "test@example.com"}
        ]
        actions_json = json.dumps(actions)
        expected_hash = hashlib.sha256(actions_json.encode()).hexdigest()

        playbook = RpaPlaybook(
            name="Playbook con Hash",
            base_url="https://example.com",
            actions=actions,
            content_hash=expected_hash
        )

        db_session.add(playbook)
        await db_session.commit()
        await db_session.refresh(playbook)

        # Verificar que el hash se almacena correctamente
        assert playbook.content_hash is not None
        assert playbook.content_hash == expected_hash
        assert len(playbook.content_hash) == 64  # SHA256 = 64 caracteres hex

    @pytest.mark.asyncio
    async def test_playbook_tracks_origin(self, db_session):
        """Playbook importado tiene origin_license_id."""
        playbook = RpaPlaybook(
            name="Playbook Importado",
            base_url="https://portal.example.com",
            actions=[{"type": "navigate", "url": "/login"}],
            content_hash="hash_del_contenido",
            # Campos de origen para playbooks importados
            origin_license_id="LIC-PARTNER-002",
            origin_package_id="PKG-UUID-87654321"
        )

        db_session.add(playbook)
        await db_session.commit()
        await db_session.refresh(playbook)

        # Verificar campos de origen
        assert playbook.origin_license_id == "LIC-PARTNER-002"
        assert playbook.origin_package_id == "PKG-UUID-87654321"

    @pytest.mark.asyncio
    async def test_playbook_origin_fields_optional(self, db_session):
        """Los campos de origen son opcionales en playbooks."""
        playbook = RpaPlaybook(
            name="Playbook Local",
            base_url="https://local.example.com",
            actions=[{"type": "click", "selector": "#submit"}]
            # Sin campos de origen - playbook creado localmente
        )

        db_session.add(playbook)
        await db_session.commit()
        await db_session.refresh(playbook)

        # Los campos de origen deben ser None para playbooks locales
        assert playbook.origin_license_id is None
        assert playbook.origin_package_id is None
        assert playbook.content_hash is None  # También opcional

    @pytest.mark.asyncio
    async def test_original_status_preserved(self, db_session):
        """Se guarda el estado original del script importado."""
        # Script que era PUBLISHED en origen pero se importa como DRAFT
        script = CustomScript(
            name="Script Publicado en Origen",
            description="Era published en el cliente original",
            user_prompt="Script validado",
            code="def transform(df): return df.dropna()",
            code_hash="hash_validated",
            status="draft",  # Estado actual (importado como draft)
            original_status="published"  # Estado que tenía en origen
        )

        db_session.add(script)
        await db_session.commit()
        await db_session.refresh(script)

        # El estado actual es draft pero sabemos que era published en origen
        assert script.status == "draft"
        assert script.original_status == "published"

    @pytest.mark.asyncio
    async def test_filter_imported_scripts(self, db_session):
        """Poder filtrar scripts importados vs locales."""
        # Script local
        local_script = CustomScript(
            name="Script Local",
            description="Creado aquí",
            user_prompt="prompt",
            code="code",
            code_hash="hash1"
        )

        # Script importado
        imported_script = CustomScript(
            name="Script Importado",
            description="Viene de otro cliente",
            user_prompt="prompt",
            code="code",
            code_hash="hash2",
            origin_license_id="LIC-EXTERNO",
            origin_package_id="PKG-001"
        )

        db_session.add_all([local_script, imported_script])
        await db_session.commit()

        # Filtrar solo scripts importados (tienen origin_package_id)
        stmt = select(CustomScript).where(CustomScript.origin_package_id.isnot(None))
        result = await db_session.execute(stmt)
        imported_scripts = result.scalars().all()

        assert len(imported_scripts) == 1
        assert imported_scripts[0].name == "Script Importado"

        # Filtrar solo scripts locales (no tienen origin_package_id)
        stmt = select(CustomScript).where(CustomScript.origin_package_id.is_(None))
        result = await db_session.execute(stmt)
        local_scripts = result.scalars().all()

        assert len(local_scripts) == 1
        assert local_scripts[0].name == "Script Local"


class TestCalculatePlaybookHash:
    """Tests para la función helper calculate_playbook_hash."""

    def test_calculate_hash_basic(self):
        """Calcula hash SHA256 de JSON de acciones."""
        actions_json = '[{"type": "click", "selector": "#btn"}]'
        expected = hashlib.sha256(actions_json.encode()).hexdigest()

        result = calculate_playbook_hash(actions_json)

        assert result == expected
        assert len(result) == 64

    def test_calculate_hash_is_deterministic(self):
        """El mismo contenido siempre produce el mismo hash."""
        actions_json = '{"actions": [1, 2, 3]}'

        hash1 = calculate_playbook_hash(actions_json)
        hash2 = calculate_playbook_hash(actions_json)

        assert hash1 == hash2

    def test_calculate_hash_different_content(self):
        """Contenido diferente produce hash diferente."""
        json1 = '{"type": "click"}'
        json2 = '{"type": "input"}'

        hash1 = calculate_playbook_hash(json1)
        hash2 = calculate_playbook_hash(json2)

        assert hash1 != hash2

    def test_calculate_hash_empty_string(self):
        """Hash de string vacío es válido."""
        result = calculate_playbook_hash("")

        assert len(result) == 64
        # Hash de string vacío es conocido
        expected = hashlib.sha256("".encode()).hexdigest()
        assert result == expected

    def test_calculate_hash_complex_json(self):
        """Hash funciona con JSON complejo."""
        complex_actions = json.dumps([
            {"type": "navigate", "url": "https://example.com"},
            {"type": "wait", "selector": "#loaded"},
            {"type": "input", "selector": "#user", "value": "admin"},
            {"type": "input", "selector": "#pass", "value": "***"},
            {"type": "click", "selector": "#login"},
            {"type": "screenshot", "name": "result"}
        ])

        result = calculate_playbook_hash(complex_actions)

        assert len(result) == 64
        # Verificar que es hexadecimal válido
        int(result, 16)  # No debe lanzar excepción

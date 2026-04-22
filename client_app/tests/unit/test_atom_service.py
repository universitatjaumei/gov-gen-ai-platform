"""
Tests para AtomService - Servicio de gestión de átomos.
Prompt 1.3 del plan de refactorización del editor de flujos.

TDD: Estos tests se escriben ANTES de implementar el servicio.
"""
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

from automatia_shared.enums import StepType
from client_app.app.database.models import AtomRegistry


class TestAtomService:
    """Tests para AtomService."""

    @pytest.fixture
    def mock_session(self):
        """Mock de AsyncSession para tests unitarios."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.get = AsyncMock()
        session.execute = AsyncMock()
        session.delete = AsyncMock()
        return session

    @pytest.fixture
    def atom_service(self):
        """Instancia de AtomService para tests."""
        from client_app.app.services.atom_service import AtomService
        return AtomService()

    @pytest.mark.asyncio
    async def test_create_atom_success(self, atom_service, mock_session):
        """Crear átomo con datos válidos."""
        config_schema = json.dumps({
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"]
        })
        default_config = json.dumps({"url": "", "method": "GET"})

        # Mock para simular la creación
        created_atom = AtomRegistry(
            id=1,
            name="API Fetch Atom",
            atom_type=StepType.API_FETCH,
            description="Realiza llamadas a APIs REST",
            config_schema=config_schema,
            default_config=default_config,
            is_active=True
        )

        async def mock_refresh(obj):
            obj.id = 1
            obj.created_at = datetime.utcnow()
            obj.updated_at = datetime.utcnow()

        mock_session.refresh = mock_refresh

        with patch('client_app.app.services.atom_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            result = await atom_service.create_atom(
                name="API Fetch Atom",
                atom_type=StepType.API_FETCH,
                config_schema=config_schema,
                description="Realiza llamadas a APIs REST",
                default_config=default_config
            )

            assert result is not None
            assert result.name == "API Fetch Atom"
            assert result.atom_type == StepType.API_FETCH
            assert result.is_active is True
            mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_atom_invalid_schema(self, atom_service):
        """Rechazar si config_schema no es JSON válido."""
        invalid_schema = "esto no es json válido {"

        with pytest.raises(ValueError, match="config_schema debe ser JSON válido"):
            await atom_service.create_atom(
                name="Atom Inválido",
                atom_type=StepType.EXTRACTION,
                config_schema=invalid_schema
            )

    @pytest.mark.asyncio
    async def test_list_atoms_all(self, atom_service, mock_session):
        """Listar todos los átomos activos."""
        # Crear átomos de prueba
        atoms = [
            AtomRegistry(
                id=1,
                name="Atom 1",
                atom_type=StepType.EXTRACTION,
                config_schema="{}",
                is_active=True
            ),
            AtomRegistry(
                id=2,
                name="Atom 2",
                atom_type=StepType.API_FETCH,
                config_schema="{}",
                is_active=True
            ),
        ]

        # Mock del resultado de la consulta
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = atoms
        mock_session.execute.return_value = mock_result

        with patch('client_app.app.services.atom_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            result = await atom_service.list_atoms()

            assert len(result) == 2
            assert all(atom.is_active for atom in result)

    @pytest.mark.asyncio
    async def test_list_atoms_by_type(self, atom_service, mock_session):
        """Filtrar átomos por atom_type."""
        extraction_atoms = [
            AtomRegistry(
                id=1,
                name="Extracción PDF",
                atom_type=StepType.EXTRACTION,
                config_schema="{}",
                is_active=True
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = extraction_atoms
        mock_session.execute.return_value = mock_result

        with patch('client_app.app.services.atom_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            result = await atom_service.list_atoms(atom_type=StepType.EXTRACTION)

            assert len(result) == 1
            assert result[0].atom_type == StepType.EXTRACTION

    @pytest.mark.asyncio
    async def test_get_atom_by_id(self, atom_service, mock_session):
        """Obtener átomo por ID."""
        atom = AtomRegistry(
            id=42,
            name="Átomo Específico",
            atom_type=StepType.EMAIL_SEND,
            config_schema="{}"
        )

        mock_session.get.return_value = atom

        with patch('client_app.app.services.atom_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            result = await atom_service.get_atom(42)

            assert result is not None
            assert result.id == 42
            assert result.name == "Átomo Específico"
            mock_session.get.assert_called_once_with(AtomRegistry, 42)

    @pytest.mark.asyncio
    async def test_get_atom_not_found(self, atom_service, mock_session):
        """Obtener átomo que no existe retorna None."""
        mock_session.get.return_value = None

        with patch('client_app.app.services.atom_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            result = await atom_service.get_atom(999)

            assert result is None

    @pytest.mark.asyncio
    async def test_update_atom(self, atom_service, mock_session):
        """Actualizar nombre y descripción de un átomo."""
        existing_atom = AtomRegistry(
            id=1,
            name="Nombre Original",
            atom_type=StepType.EXTRACTION,
            description="Descripción original",
            config_schema="{}",
            is_active=True
        )

        mock_session.get.return_value = existing_atom

        with patch('client_app.app.services.atom_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            result = await atom_service.update_atom(
                atom_id=1,
                name="Nombre Actualizado",
                description="Nueva descripción"
            )

            assert result.name == "Nombre Actualizado"
            assert result.description == "Nueva descripción"
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_atom_not_found(self, atom_service, mock_session):
        """Actualizar átomo que no existe lanza error."""
        mock_session.get.return_value = None

        with patch('client_app.app.services.atom_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            with pytest.raises(ValueError, match="Atom .* not found"):
                await atom_service.update_atom(atom_id=999, name="Nuevo nombre")

    @pytest.mark.asyncio
    async def test_delete_atom_soft(self, atom_service, mock_session):
        """Eliminar átomo marca como inactivo (is_active=False)."""
        atom = AtomRegistry(
            id=1,
            name="Átomo a Eliminar",
            atom_type=StepType.EXTRACTION,
            config_schema="{}",
            is_active=True
        )

        mock_session.get.return_value = atom

        with patch('client_app.app.services.atom_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            result = await atom_service.delete_atom(1)

            assert result is True
            assert atom.is_active is False
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_atom_not_found(self, atom_service, mock_session):
        """Eliminar átomo que no existe retorna False."""
        mock_session.get.return_value = None

        with patch('client_app.app.services.atom_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            result = await atom_service.delete_atom(999)

            assert result is False

    @pytest.mark.asyncio
    async def test_duplicate_atom(self, atom_service, mock_session):
        """Crear copia de un átomo existente."""
        original_atom = AtomRegistry(
            id=1,
            name="Átomo Original",
            atom_type=StepType.API_FETCH,
            description="Descripción original",
            config_schema=json.dumps({"type": "object"}),
            default_config=json.dumps({"url": "https://api.ejemplo.com"}),
            version="1.0.0",
            is_system=True,
            is_active=True
        )

        mock_session.get.return_value = original_atom

        async def mock_refresh(obj):
            obj.id = 2
            obj.created_at = datetime.utcnow()
            obj.updated_at = datetime.utcnow()

        mock_session.refresh = mock_refresh

        with patch('client_app.app.services.atom_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            result = await atom_service.duplicate_atom(1, "Átomo Duplicado")

            assert result is not None
            assert result.name == "Átomo Duplicado"
            assert result.atom_type == original_atom.atom_type
            assert result.config_schema == original_atom.config_schema
            assert result.default_config == original_atom.default_config
            assert result.is_active is True

    @pytest.mark.asyncio
    async def test_duplicate_atom_not_found(self, atom_service, mock_session):
        """Duplicar átomo que no existe lanza error."""
        mock_session.get.return_value = None

        with patch('client_app.app.services.atom_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            with pytest.raises(ValueError, match="Atom .* not found"):
                await atom_service.duplicate_atom(999, "Nombre Copia")


class TestAtomServiceSingleton:
    """Tests para verificar el patrón singleton."""

    def test_singleton_instance(self):
        """Verificar que atom_service es singleton."""
        from client_app.app.services.atom_service import AtomService

        service1 = AtomService()
        service2 = AtomService()

        assert service1 is service2

    def test_singleton_export(self):
        """Verificar que existe la instancia exportada."""
        from client_app.app.services.atom_service import atom_service

        assert atom_service is not None
        from client_app.app.services.atom_service import AtomService
        assert isinstance(atom_service, AtomService)

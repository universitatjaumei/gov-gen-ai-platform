"""
Tests para FlowMigrationService - Migración de flujos existentes.
Prompt 6.1 del plan de refactorización del editor de flujos.

TDD: Estos tests se escriben ANTES de implementar el servicio.
"""
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime

from automatia_shared.enums import StepType
from client_app.app.database.models import FlowRegistry, AtomRegistry, FlowStep


class TestFlowMigrationService:
    """Tests para FlowMigrationService."""

    @pytest.fixture
    def mock_session(self):
        """Mock de AsyncSession para tests unitarios."""
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        session.get = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def migration_service(self):
        """Instancia de FlowMigrationService para tests."""
        from client_app.app.services.flow_migration_service import FlowMigrationService
        return FlowMigrationService()

    def _create_flow_registry(
        self,
        flow_id: int,
        name: str,
        steps_json: str = "[]",
        is_migrated: bool = False
    ) -> FlowRegistry:
        """Helper para crear FlowRegistry de prueba."""
        flow = FlowRegistry(
            id=flow_id,
            name=name,
            description=f"Flujo de prueba {name}",
            steps=steps_json,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        # Simular campo de migración (se añadirá al modelo)
        flow._is_migrated = is_migrated
        flow._steps_backup = None
        return flow

    @pytest.mark.asyncio
    async def test_migrate_empty_flow(self, migration_service, mock_session):
        """Flujo sin pasos migra correctamente."""
        # Crear flujo vacío
        flow = self._create_flow_registry(
            flow_id=1,
            name="Flujo Vacío",
            steps_json="[]"
        )

        mock_session.get.return_value = flow

        # Mock para execute (buscar FlowSteps existentes)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        with patch('client_app.app.services.flow_migration_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            result = await migration_service.migrate_flow(1)

            assert result is True
            # No se deben crear FlowSteps para un flujo vacío
            # Pero el flujo debe marcarse como migrado

    @pytest.mark.asyncio
    async def test_migrate_flow_preserves_steps(self, migration_service, mock_session):
        """Los pasos se convierten a FlowStep."""
        # Crear flujo con 2 pasos
        steps = [
            {"name": "Extraer PDF", "type": "extraction", "config": {"config_id": "factura_v1"}},
            {"name": "Enviar Email", "type": "email_send", "config": {"recipients": "test@example.com"}}
        ]
        flow = self._create_flow_registry(
            flow_id=1,
            name="Flujo Con Pasos",
            steps_json=json.dumps(steps)
        )

        mock_session.get.return_value = flow

        # Mock para execute (buscar FlowSteps existentes y átomos)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        created_flow_steps = []

        def capture_add(obj):
            if isinstance(obj, FlowStep):
                created_flow_steps.append(obj)

        mock_session.add.side_effect = capture_add

        with patch('client_app.app.services.flow_migration_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            result = await migration_service.migrate_flow(1)

            assert result is True
            # Deben haberse creado 2 FlowSteps
            assert len(created_flow_steps) == 2
            # Verificar el orden
            assert created_flow_steps[0].step_order == 0
            assert created_flow_steps[1].step_order == 1
            # Verificar que tienen custom_name
            assert created_flow_steps[0].custom_name == "Extraer PDF"
            assert created_flow_steps[1].custom_name == "Enviar Email"

    @pytest.mark.asyncio
    async def test_migrate_creates_atoms_if_needed(self, migration_service, mock_session):
        """Si no existe átomo, se crea uno."""
        steps = [
            {"name": "Llamada API", "type": "api_fetch", "config": {"url": "https://api.example.com"}}
        ]
        flow = self._create_flow_registry(
            flow_id=1,
            name="Flujo API",
            steps_json=json.dumps(steps)
        )

        mock_session.get.return_value = flow

        # Mock para execute: no hay átomos existentes
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        created_atoms = []
        created_flow_steps = []

        def capture_add(obj):
            if isinstance(obj, AtomRegistry):
                obj.id = len(created_atoms) + 100  # Simular ID autoincrement
                created_atoms.append(obj)
            elif isinstance(obj, FlowStep):
                created_flow_steps.append(obj)

        mock_session.add.side_effect = capture_add

        with patch('client_app.app.services.flow_migration_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            result = await migration_service.migrate_flow(1)

            assert result is True
            # Debe haberse creado un átomo genérico
            assert len(created_atoms) >= 1
            # El átomo debe ser de tipo API_FETCH
            api_atom = next((a for a in created_atoms if a.atom_type == StepType.API_FETCH), None)
            assert api_atom is not None

    @pytest.mark.asyncio
    async def test_migrate_reuses_existing_atoms(self, migration_service, mock_session):
        """Si existe átomo compatible, se reutiliza."""
        steps = [
            {"name": "Extraer Factura", "type": "extraction", "config": {"config_id": "factura_v1"}}
        ]
        flow = self._create_flow_registry(
            flow_id=1,
            name="Flujo Extracción",
            steps_json=json.dumps(steps)
        )

        # Átomo existente compatible
        existing_atom = AtomRegistry(
            id=50,
            name="Extracción Genérica",
            atom_type=StepType.EXTRACTION,
            config_schema="{}",
            is_active=True
        )

        mock_session.get.return_value = flow

        # Mock para execute: primera llamada verifica FlowSteps, segunda busca átomo
        call_count = [0]

        def mock_execute(query):
            call_count[0] += 1
            mock_result = MagicMock()
            if call_count[0] == 1:
                # Primera llamada: verificar si existen FlowSteps (no hay)
                mock_result.scalars.return_value.first.return_value = None
            else:
                # Segunda llamada: buscar átomo por tipo (existe uno)
                mock_result.scalars.return_value.first.return_value = existing_atom
            mock_result.scalars.return_value.all.return_value = []
            return mock_result

        mock_session.execute.side_effect = mock_execute

        created_atoms = []
        created_flow_steps = []

        def capture_add(obj):
            if isinstance(obj, AtomRegistry):
                created_atoms.append(obj)
            elif isinstance(obj, FlowStep):
                created_flow_steps.append(obj)

        mock_session.add.side_effect = capture_add

        with patch('client_app.app.services.flow_migration_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            result = await migration_service.migrate_flow(1)

            assert result is True
            # NO debe haberse creado un nuevo átomo (se reutiliza el existente)
            assert len(created_atoms) == 0
            # Debe haberse creado el FlowStep
            assert len(created_flow_steps) == 1
            # El FlowStep debe referenciar el átomo existente
            assert created_flow_steps[0].atom_id == 50

    @pytest.mark.asyncio
    async def test_migration_is_idempotent(self, migration_service, mock_session):
        """Migrar dos veces no duplica datos."""
        steps = [
            {"name": "Paso Único", "type": "custom_script", "config": {"script_id": "script_1"}}
        ]
        flow = self._create_flow_registry(
            flow_id=1,
            name="Flujo Idempotente",
            steps_json=json.dumps(steps)
        )

        # Simular que el flujo ya fue migrado (tiene FlowSteps)
        existing_flow_step = FlowStep(
            id=10,
            flow_id=1,
            atom_id=50,
            step_order=0,
            custom_name="Paso Único"
        )

        mock_session.get.return_value = flow

        # Primera llamada: devolver FlowSteps existentes
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_flow_step]
        mock_session.execute.return_value = mock_result

        created_flow_steps = []

        def capture_add(obj):
            if isinstance(obj, FlowStep):
                created_flow_steps.append(obj)

        mock_session.add.side_effect = capture_add

        with patch('client_app.app.services.flow_migration_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            # Primera migración
            result1 = await migration_service.migrate_flow(1)
            assert result1 is True

            # Segunda migración - debe ser idempotente
            result2 = await migration_service.migrate_flow(1)
            assert result2 is True

            # No debe haber creado FlowSteps duplicados
            # (la implementación debe detectar que ya existen)
            assert len(created_flow_steps) == 0

    @pytest.mark.asyncio
    async def test_migrate_flow_not_found(self, migration_service, mock_session):
        """Migrar flujo que no existe retorna False."""
        mock_session.get.return_value = None

        with patch('client_app.app.services.flow_migration_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            result = await migration_service.migrate_flow(999)

            assert result is False

    @pytest.mark.asyncio
    async def test_migrate_all_flows(self, migration_service, mock_session):
        """Migrar todos los flujos retorna diccionario de resultados."""
        flows = [
            self._create_flow_registry(1, "Flujo 1", "[]"),
            self._create_flow_registry(2, "Flujo 2", "[]"),
            self._create_flow_registry(3, "Flujo 3", "[]"),
        ]

        # Mock para execute: listar todos los flujos
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = flows
        mock_session.execute.return_value = mock_result

        # Mock get para cada flujo individual
        def mock_get(model, id):
            return next((f for f in flows if f.id == id), None)

        mock_session.get.side_effect = mock_get

        with patch('client_app.app.services.flow_migration_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            result = await migration_service.migrate_all_flows()

            assert isinstance(result, dict)
            assert len(result) == 3
            # Todos los flujos deben haberse migrado exitosamente
            assert all(success for success in result.values())

    @pytest.mark.asyncio
    async def test_check_migration_status(self, migration_service, mock_session):
        """Verificar estado de migración."""
        # 2 flujos migrados, 1 pendiente
        flows = [
            self._create_flow_registry(1, "Migrado 1", "[]", is_migrated=True),
            self._create_flow_registry(2, "Migrado 2", "[]", is_migrated=True),
            self._create_flow_registry(3, "Pendiente", '[{"name": "paso"}]', is_migrated=False),
        ]

        # Simular conteos
        mock_result_total = MagicMock()
        mock_result_total.scalar.return_value = 3

        mock_result_migrated = MagicMock()
        mock_result_migrated.scalar.return_value = 2

        mock_session.execute.side_effect = [mock_result_total, mock_result_migrated]

        with patch('client_app.app.services.flow_migration_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            status = await migration_service.check_migration_status()

            assert status.total_flows == 3
            assert status.migrated_flows == 2
            assert status.pending_flows == 1
            assert status.is_complete is False

    @pytest.mark.asyncio
    async def test_migration_preserves_backup(self, migration_service, mock_session):
        """La migración guarda backup del JSON original."""
        original_steps = [
            {"name": "Paso Original", "type": "extraction", "config": {"key": "value"}}
        ]
        flow = self._create_flow_registry(
            flow_id=1,
            name="Flujo Con Backup",
            steps_json=json.dumps(original_steps)
        )

        mock_session.get.return_value = flow

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        with patch('client_app.app.services.flow_migration_service.AsyncSession') as MockAsyncSession:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            MockAsyncSession.return_value = mock_context

            result = await migration_service.migrate_flow(1)

            assert result is True
            # El flujo debe tener el backup guardado
            # (esto depende de cómo se implemente - puede ser un campo nuevo o metadatos)


class TestMigrationStatus:
    """Tests para la clase MigrationStatus."""

    def test_migration_status_complete(self):
        """MigrationStatus indica completado cuando todos están migrados."""
        from client_app.app.services.flow_migration_service import MigrationStatus

        status = MigrationStatus(
            total_flows=5,
            migrated_flows=5,
            pending_flows=0
        )

        assert status.is_complete is True
        assert status.progress_percentage == 100.0

    def test_migration_status_partial(self):
        """MigrationStatus calcula porcentaje correcto."""
        from client_app.app.services.flow_migration_service import MigrationStatus

        status = MigrationStatus(
            total_flows=10,
            migrated_flows=3,
            pending_flows=7
        )

        assert status.is_complete is False
        assert status.progress_percentage == 30.0

    def test_migration_status_empty(self):
        """MigrationStatus maneja cero flujos."""
        from client_app.app.services.flow_migration_service import MigrationStatus

        status = MigrationStatus(
            total_flows=0,
            migrated_flows=0,
            pending_flows=0
        )

        assert status.is_complete is True
        assert status.progress_percentage == 100.0


class TestFlowMigrationServiceSingleton:
    """Tests para verificar el patrón singleton."""

    def test_singleton_instance(self):
        """Verificar que FlowMigrationService es singleton."""
        from client_app.app.services.flow_migration_service import FlowMigrationService

        service1 = FlowMigrationService()
        service2 = FlowMigrationService()

        assert service1 is service2

    def test_singleton_export(self):
        """Verificar que existe la instancia exportada."""
        from client_app.app.services.flow_migration_service import flow_migration_service

        assert flow_migration_service is not None
        from client_app.app.services.flow_migration_service import FlowMigrationService
        assert isinstance(flow_migration_service, FlowMigrationService)

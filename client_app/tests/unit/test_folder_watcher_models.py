import pytest
from datetime import datetime
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from client_app.app.database.models import FolderWatcherConfig, FolderWatcherState


class TestFolderWatcherConfig:
    """Tests para el modelo FolderWatcherConfig."""

    @pytest.mark.asyncio
    async def test_create_config(self, db_session: AsyncSession):
        """Crear configuración básica de FolderWatcher."""
        config = FolderWatcherConfig(
            name="Facturas Entrada",
            watch_path="/data/input/facturas",
            file_patterns="*.pdf,*.xml",
            flow_id=1,
            stabilization_seconds=2.0,
            recursive=False,
            is_active=True
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.id is not None
        assert config.name == "Facturas Entrada"
        assert config.file_patterns == "*.pdf,*.xml"
        assert config.stabilization_seconds == 2.0

    @pytest.mark.asyncio
    async def test_config_defaults(self, db_session: AsyncSession):
        """Verificar valores por defecto."""
        config = FolderWatcherConfig(
            name="Test",
            watch_path="/tmp/test",
            flow_id=1
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.file_patterns == "*"  # Default: todos
        assert config.stabilization_seconds == 2.0  # Default: 2 segundos
        assert config.recursive is False  # Default: no recursivo
        assert config.is_active is False  # Default: inactivo
        assert config.auto_start is False  # Default: no auto-start

    @pytest.mark.asyncio
    async def test_list_active_configs(self, db_session: AsyncSession):
        """Listar solo configuraciones activas."""
        # Crear 3 configs, 2 activas
        for i, active in enumerate([True, True, False]):
            config = FolderWatcherConfig(
                name=f"Config {i}",
                watch_path=f"/tmp/test{i}",
                flow_id=1,
                is_active=active
            )
            db_session.add(config)
        await db_session.commit()

        stmt = select(FolderWatcherConfig).where(FolderWatcherConfig.is_active == True)
        result = await db_session.exec(stmt)
        active_configs = result.all()

        assert len(active_configs) == 2

    @pytest.mark.asyncio
    async def test_update_last_triggered(self, db_session: AsyncSession):
        """Actualizar timestamp de último trigger."""
        config = FolderWatcherConfig(
            name="Test",
            watch_path="/tmp/test",
            flow_id=1
        )
        db_session.add(config)
        await db_session.commit()

        # Simular trigger
        config.last_triggered_at = datetime.utcnow()
        config.trigger_count += 1
        await db_session.commit()
        await db_session.refresh(config)

        assert config.last_triggered_at is not None
        assert config.trigger_count == 1


class TestFolderWatcherState:
    """Tests para el modelo FolderWatcherState (singleton)."""

    @pytest.mark.asyncio
    async def test_singleton_state(self, db_session: AsyncSession):
        """Estado es singleton (id=1)."""
        state = FolderWatcherState(
            id=1,
            active_watchers=0,
            last_heartbeat=datetime.utcnow()
        )
        db_session.add(state)
        await db_session.commit()

        # Recuperar por ID fijo
        loaded = await db_session.get(FolderWatcherState, 1)
        assert loaded is not None
        assert loaded.active_watchers == 0

    @pytest.mark.asyncio
    async def test_update_active_watchers(self, db_session: AsyncSession):
        """Actualizar contador de watchers activos."""
        state = await db_session.get(FolderWatcherState, 1)
        if not state:
            state = FolderWatcherState(id=1)
            db_session.add(state)
            await db_session.commit()

        state.active_watchers = 3
        state.last_heartbeat = datetime.utcnow()
        await db_session.commit()

        loaded = await db_session.get(FolderWatcherState, 1)
        assert loaded.active_watchers == 3

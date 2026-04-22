import pytest
from sqlmodel import select, delete
from app.database.models import FavoriteFlow, FlowRegistry
from datetime import datetime

@pytest.mark.asyncio
async def test_favorite_flows_lifecycle(db_session):
    """Verificar el ciclo de vida de los flujos favoritos (añadir, listar, eliminar)."""
    # Usar la session inyectada por el fixture
    session = db_session

    # 1. Crear un Flow de prueba
    flow = FlowRegistry(name="Test Flow", steps="[]", status="PUBLISHED")
    session.add(flow)
    await session.commit()
    await session.refresh(flow)
    flow_id = flow.id
    
    # 2. Añadir a Favoritos
    fav = FavoriteFlow(flow_id=flow_id)
    session.add(fav)
    await session.commit()
    
    # 3. Verificar que existe
    stmt = select(FavoriteFlow).where(FavoriteFlow.flow_id == flow_id)
    result = await session.execute(stmt)
    fav_retrieved = result.scalar_one_or_none()
    assert fav_retrieved is not None
    assert fav_retrieved.flow_id == flow_id
        
    # 4. Verificar Query de Dashboard (Join)
    # select(FlowRegistry).join(FavoriteFlow, FlowRegistry.id == FavoriteFlow.flow_id)
    dash_stmt = select(FlowRegistry).join(FavoriteFlow, FlowRegistry.id == FavoriteFlow.flow_id)
    dash_result = await session.execute(dash_stmt)
    favorites_list = dash_result.scalars().all()
    
    assert len(favorites_list) == 1
    assert favorites_list[0].name == "Test Flow"
    
    # 5. Eliminar de Favoritos
    del_stmt = delete(FavoriteFlow).where(FavoriteFlow.flow_id == flow_id)
    await session.execute(del_stmt)
    await session.commit()
    
    # 6. Verificar que ya no existe
    result_after = await session.execute(stmt)
    assert result_after.scalar_one_or_none() is None


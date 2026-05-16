
import pytest
import pandas as pd
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from sqlmodel import select

from client_app.app.services.etl_service import ETLService
from client_app.app.services.deterministic_etl_service import DeterministicETLService
from client_app.app.models.transform_operations import (
    DropColumnsOperation,
    RenameColumnsOperation,
    FormatDatesOperation,
    TransformOperation
)
from client_app.app.database.models import ETLJobHistory

@pytest.mark.asyncio
async def test_assisted_etl_pipeline_e2e(db_session, tmp_path):
    """
    Test completo del pipeline ETL en modo asistido.
    Verifica que las operaciones se aplican correctamente sin usar IA.
    """
    # 1. Preparar datos
    source_file = tmp_path / "data.csv"
    output_file = tmp_path / "data_out.csv"
    
    df = pd.DataFrame({
        'id': [1, 2, 3],
        'full_name': ['Alice Smith', 'Bob Jones', 'Charlie Brown'],
        'registration_date': ['2023-01-01', '2023-05-15', '2023-12-31'],
        'internal_code': ['A-001', 'B-002', 'C-003']
    })
    df.to_csv(source_file, index=False)
    
    # 2. Configurar operaciones
    # Usamos los modelos definidos en Phase 1
    ops = [
        RenameColumnsOperation(mapping={'full_name': 'name'}),
        DropColumnsOperation(columns=['internal_code']),
        FormatDatesOperation(column='registration_date', target_format='%d/%m/%Y')
    ]
    
    # 3. Ejecutar pipeline vía ETLService
    # No se necesita brain client en modo asistido
    service = ETLService(db_session)
    
    execution_id = "assisted_test_001"
    
    result = await service.run_etl_pipeline(
        execution_id=execution_id,
        source_file=str(source_file),
        transformation_mode='assisted',
        operations=ops,
        output_file=str(output_file),
        output_format='csv'
    )
    
    # 4. Verificaciones
    assert result['status'] == 'success'
    assert output_file.exists()
    
    df_out = pd.read_csv(output_file)
    
    # Verificar columnas
    assert 'name' in df_out.columns
    assert 'full_name' not in df_out.columns
    assert 'internal_code' not in df_out.columns
    
    # Verificar transformación de datos
    assert df_out['registration_date'].iloc[0] == '01/01/2023'
    assert df_out['registration_date'].iloc[1] == '15/05/2023'
    
    # Verificar que no se generó script por IA (debería ser el generado por DeterministicETLService)
    # ETLService en modo asistido llama a generate_script del DeterministicETLService
    assert 'Operation 1: RenameColumnsOperation' in result['script']
    
    # Verificar persistencia en base de datos
    stmt = select(ETLJobHistory).where(ETLJobHistory.execution_id == execution_id)
    db_result = await db_session.execute(stmt)
    job = db_result.scalar_one()
    
    assert job.status == 'success'
    assert job.transformation_mode == 'assisted'
    assert job.script_content == result['script']

@pytest.mark.asyncio
async def test_assisted_to_ai_switch_fallback(db_session, tmp_path):
    """
    Verifica que si pasamos modo AI pero con instrucciones, 
    se usa el flujo de IA normal.
    """
    mock_brain = MagicMock()
    mock_brain.generate_code = AsyncMock(return_value={
        'code': "def transform(df): return df",
        'model': 'mock-gpt',
        'tokens': 50
    })
    
    source_file = tmp_path / "test.csv"
    pd.DataFrame({'a': [1]}).to_csv(source_file, index=False)
    output_file = tmp_path / "test_out.csv"
    
    service = ETLService(db_session, _test_brain_client=mock_brain)
    
    result = await service.run_etl_pipeline(
        execution_id="switch_test",
        source_file=str(source_file),
        transformation_mode='ai',
        target_spec="Just return same",
        user_instructions="Just return same",
        output_file=str(output_file),
        output_format='csv'
    )
    
    assert result['status'] == 'success'
    mock_brain.generate_code.assert_called_once()
    assert 'metadata' in result
    assert result['metadata']['mode'] == 'ai'

@pytest.mark.asyncio
async def test_detect_potential_operations_utility():
    """Test unitario de la utilidad de detección (en archivo de integración por conveniencia)."""
    from client_app.app.utils.etl_utils import detect_potential_operations
    
    # Caso 1: Múltiples operaciones
    text = "Quiero eliminar la columna email y renombrar la columna nombre a cliente. También cambia el formato de fecha."
    ops = detect_potential_operations(text)
    
    types = [o['type'] for o in ops]
    assert 'drop_columns' in types
    assert 'rename_columns' in types
    assert 'format_dates' in types
    
    # Caso 2: Sin operaciones
    text = "Haz magia con mis datos y dime qué ves."
    ops = detect_potential_operations(text)
    assert len(ops) == 0
    
    # Caso 3: Inglés (soporte básico)
    text = "Remove columns A and B, then drop duplicates."
    ops = detect_potential_operations(text)
    types = [o['type'] for o in ops]
    assert 'drop_columns' in types
    assert 'remove_duplicates' in types

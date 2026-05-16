import pytest
import json
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from sqlmodel import select

from app.services.etl_service import ETLService
from app.services.validation_loop import ValidationLoopManager
from app.database.models import ETLJobHistory
from server.app.services.ai_brain import AIBrainService

@pytest.fixture
def mock_brain_service():
    brain = MagicMock(spec=AIBrainService)
    # Mock para CSV -> JSON
    brain.generate_code = AsyncMock(side_effect=lambda prompt, **kwargs: {
        'code': """
import pandas as pd

def transform(df: pd.DataFrame) -> pd.DataFrame:
    # Rename columns
    df = df.rename(columns={'cliente_nombre': 'customer_name', 'cliente_email': 'email'})
    
    # Date conversion
    df['fecha_alta'] = pd.to_datetime(df['fecha_alta'], format='%d/%m/%Y').dt.strftime('%Y-%m-%d')
    
    # Drop column
    if 'temp' in df.columns:
        df = df.drop(columns=['temp'])
        
    # Add new column
    df['source'] = 'legacy_import'
    
    return df
""",
        'model': 'mock-model',
        'tokens': 100
    })
    return brain

@pytest.fixture
def mock_brain_service_excel():
    brain = MagicMock(spec=AIBrainService)
    # Mock para Excel -> Parquet
    brain.generate_code = AsyncMock(return_value={
        'code': """
import pandas as pd

def transform(df: pd.DataFrame) -> pd.DataFrame:
    # Simple pass-through for this test
    return df
""",
        'model': 'mock-model',
        'tokens': 50
    })
    return brain

@pytest.mark.asyncio
async def test_etl_csv_to_json_with_mapping(db_session, tmp_path, mock_brain_service):
    """Test completo: CSV → JSON con renombrado de columnas."""
    # 1. Crear CSV origen
    source = tmp_path / "customers.csv"
    output = tmp_path / "customers_output.json"
    
    source.write_text(
        "cliente_nombre,cliente_email,fecha_alta,temp\n"
        "Juan,juan@test.com,01/05/2024,ABC\n"
        "Maria,maria@test.com,02/05/2024,DEF\n"
    )
    
    # 2. Ejecutar pipeline
    service = ETLService(db_session, _test_brain_client=mock_brain_service)
    
    # Mockeamos explícitamente la factoría interna si fuera necesario, 
    # pero ETLService usa brain_service pasado en init para crear su factory.
    # Aseguramos que el mock devuelva lo esperado.
    
    result = await service.run_etl_pipeline(
        execution_id="e2e_001",
        source_file=str(source),
        target_spec="""
            Renombrar 'cliente_nombre' a 'customer_name'.
            Renombrar 'cliente_email' a 'email'.
            Convertir 'fecha_alta' a formato ISO.
            Eliminar columna 'temp'.
            Añadir campo 'source' con valor 'legacy_import'.
        """,
        output_file=str(output),
        output_format="json"
    )
    
    # 3. Verificar resultado
    assert result['status'] == 'success'
    
    # Verificar archivo de salida
    assert output.exists()
    
    with open(output, 'r') as f:
        data = json.load(f)
    
    assert len(data) == 2
    row = data[0]
    
    assert 'customer_name' in row
    assert row['customer_name'] == 'Juan'
    assert 'email' in row
    assert row['email'] == 'juan@test.com'
    assert 'fecha_alta' in row
    assert row['fecha_alta'] == '2024-05-01'  # ISO format
    assert 'temp' not in row
    assert row['source'] == 'legacy_import'
    
    # 4. Verificar persistencia
    stmt = select(ETLJobHistory).where(
        ETLJobHistory.execution_id == "e2e_001"
    )
    result_db = await db_session.execute(stmt)
    job = result_db.scalar_one()
    
    assert job.status == 'success'
    assert job.source_format == 'csv'
    assert job.target_format == 'json'

@pytest.mark.asyncio
async def test_etl_excel_to_json(db_session, tmp_path, mock_brain_service_excel):
    """Test completo: Excel → JSON."""
    # 1. Crear Excel origen
    source = tmp_path / "sales.xlsx"
    output = tmp_path / "sales_output.json"
    
    df = pd.DataFrame({
        'id': [1, 2],
        'product': ['A', 'B'],
        'amount': [100, 200]
    })
    df.to_excel(source, index=False)
    
    # 2. Ejecutar pipeline
    service = ETLService(db_session, _test_brain_client=mock_brain_service_excel)
    
    result = await service.run_etl_pipeline(
        execution_id="e2e_002",
        source_file=str(source),
        target_spec="Convert to json",
        output_file=str(output),
        output_format="json"
    )
    
    # 3. Verificar resultado
    assert result['status'] == 'success'
    assert output.exists()
    
    # Leer json para verificar
    df_out = pd.read_json(output)
    assert len(df_out) == 2
    assert 'product' in df_out.columns
    assert df_out.iloc[0]['product'] == 'A'

@pytest.mark.asyncio
async def test_etl_validation_loop_retry(db_session, tmp_path):
    """Test ciclo de validación con retry."""
    
    # Mock brain que cambia comportamiento basado en el prompt (o llamada)
    brain = MagicMock(spec=AIBrainService)
    
    # Configurar side_effect para devolver diferentes scripts
    # Devuelve dicts con 'code' para que ETLScriptFactory funcione
    brain.generate_code = AsyncMock(side_effect=[
        {'code': """
def transform(df):
    df['date'] = 'wrong_format'
    return df
""", 'model': 'mock', 'tokens': 10},
        {'code': """
def transform(df):
    df['date'] = 'correct_format'
    return df
""", 'model': 'mock', 'tokens': 10}
    ])
    
    service = ETLService(db_session, _test_brain_client=brain)
    source = tmp_path / "data.csv"
    source.write_text("col1,date\n1,01-01-2024")
    output = tmp_path / "out.csv"
    
    execution_id = "e2e_retry_001"
    
    # 1. Primera ejecución
    result1 = await service.run_etl_pipeline(
        execution_id=execution_id,
        source_file=str(source),
        target_spec="spec",
        output_file=str(output),
        output_format="csv"
    )
    
    assert "wrong_format" in result1['script'] or "wrong_format" in str(result1.get('data'))
    # Nota: ETLService devuelve el script generado en result['script']
    
    # 2. Usuario rechaza (retry con feedback)
    validation_mgr = ValidationLoopManager(db_session)
    feedback_result = await validation_mgr.handle_feedback(
        task_id=execution_id,
        action='retry',
        feedback="La fecha está mal"
    )
    
    assert feedback_result['status'] == 'regenerating'
    assert feedback_result['retries'] == 1
    
    # 3. Segunda ejecución (con feedback)
    # Simulamos que la UI llama de nuevo al servicio con los instrucciones actualizadas
    current_instructions = "spec\nFeedback: La fecha está mal"
    
    result2 = await service.run_etl_pipeline(
        execution_id=execution_id + "_retry_1", 
        source_file=str(source),
        target_spec=current_instructions,
        output_file=str(output),
        output_format="csv"
    )
    
    # 4. Verificar que se aplicó feedback (el mock devolvió script_v2)
    assert "correct_format" in result2['script']
    assert result1['script'] != result2['script']


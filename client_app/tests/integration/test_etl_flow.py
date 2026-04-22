import pytest
import json
import pandas as pd
from datetime import datetime
from app.services.flow_registry_service import FlowRegistryService
from app.modules.runtime.workflow_engine import WorkflowEngine
from app.database.models import ETLJobHistory

@pytest.mark.asyncio
async def test_create_and_execute_etl_flow(db_session, tmp_path):
    """
    Test completo:
    1. Crear un historial de trabajo ETL simulado.
    2. Convertirlo en Flujo usando FlowRegistryService.
    3. Ejecutar el Flujo usando WorkflowEngine.
    """
    execution_id = "job-flow-test-001"
    
    # 1. Simulate existing ETL Job in DB
    script_content = """
import pandas as pd
def transform(df):
    df['value_doubled'] = df['value'] * 2
    return df
"""
    job = ETLJobHistory(
        execution_id=execution_id,
        source_file="dummy.csv",
        target_file="dummy_out.csv",
        source_format="csv",
        target_format="csv",
        script_content=script_content,
        status="success",
        created_at=datetime.utcnow()
    )
    db_session.add(job)
    await db_session.commit()
    
    # 2. Create Flow from Job
    registry = FlowRegistryService(db_session)
    flow_reg = await registry.create_etl_flow(
        execution_id=execution_id,
        name="Test ETL Flow",
        description="Auto-generated flow"
    )
    
    assert flow_reg.id is not None
    assert flow_reg.name == "Test ETL Flow"
    
    # Verify strict structure
    spec = registry._to_spec(flow_reg)
    assert len(spec.steps) == 1
    assert spec.steps[0].type == "etl_transform"
    assert spec.steps[0].config['script'] == script_content
    
    # 3. Execute Flow
    engine = WorkflowEngine(db_session)
    
    # Prepare input file for execution
    input_file = tmp_path / "input.csv"
    pd.DataFrame({'value': [10, 20, 30]}).to_csv(input_file, index=False)
    
    output_file = tmp_path / "output.csv"
    
    context = {
        "source_file": str(input_file),
        "output_path": str(output_file)
    }
    
    result = await engine.execute_flow(spec, context)
    
    # 4. Verify Execution
    assert result['status'] == 'completed'
    assert output_file.exists()
    
    df_out = pd.read_csv(output_file)
    assert 'value_doubled' in df_out.columns
    assert df_out.iloc[0]['value_doubled'] == 20


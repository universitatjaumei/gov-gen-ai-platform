import pytest
import pandas as pd
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from client_app.app.services.etl_service import ETLService
from client_app.app.database.models import ETLJobHistory
from sqlmodel import select


@pytest.fixture
def mock_brain():
    """Mock AI Brain Service."""
    brain = AsyncMock()
    return brain


@pytest.fixture
def mock_factory():
    """Mock ETL Script Factory."""
    factory = AsyncMock()
    factory.generate_transformation_script = AsyncMock(return_value={
        'script': '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Transform data."""
    df['new_col'] = df['old_col'] * 2
    return df[['new_col']]
''',
        'metadata': {
            'model_used': 'gemini-2.0-flash',
            'tokens': 150,
            'source_columns': ['old_col'],
            'target_columns': ['new_col']
        }
    })
    return factory


@pytest.fixture
def mock_sandbox():
    """Mock Sandbox Service."""
    sandbox = AsyncMock()
    # Mock successful execution returning transformed DataFrame
    result_df = pd.DataFrame({'new_col': [2, 4, 6]})
    sandbox.execute_in_sandbox = AsyncMock(return_value=result_df)
    return sandbox


@pytest.fixture
def temp_csv_file(tmp_path):
    """Create temporary CSV file for testing."""
    csv_file = tmp_path / "source.csv"
    df = pd.DataFrame({'old_col': [1, 2, 3]})
    df.to_csv(csv_file, index=False)
    return str(csv_file)


@pytest.fixture
def temp_excel_file(tmp_path):
    """Create temporary Excel file for testing."""
    excel_file = tmp_path / "source.xlsx"
    df = pd.DataFrame({'old_col': [1, 2, 3]})
    df.to_excel(excel_file, index=False)
    return str(excel_file)


@pytest.fixture
def temp_json_file(tmp_path):
    """Create temporary JSON file for testing."""
    json_file = tmp_path / "source.json"
    df = pd.DataFrame({'old_col': [1, 2, 3]})
    df.to_json(json_file, orient='records')
    return str(json_file)


@pytest.mark.asyncio
async def test_run_etl_pipeline_csv_to_json(
    db_session, mock_brain, mock_factory, mock_sandbox, temp_csv_file, tmp_path
):
    """Test ETL pipeline: CSV → JSON transformation."""
    service = ETLService(
        session=db_session,
        _test_brain_client=mock_brain,
        factory=mock_factory,
        sandbox=mock_sandbox
    )
    
    output_file = str(tmp_path / "output.json")
    target_spec = "Transform old_col to new_col (multiply by 2)"
    
    result = await service.run_etl_pipeline(
        execution_id="test_001",
        source_file=temp_csv_file,
        target_spec=target_spec,
        output_file=output_file,
        output_format="json"
    )
    
    assert result['status'] == 'success'
    assert 'script' in result
    assert 'data' in result
    assert Path(output_file).exists()
    
    # Verify job history was saved
    stmt = select(ETLJobHistory).where(ETLJobHistory.execution_id == "test_001")
    job = (await db_session.execute(stmt)).scalar_one_or_none()
    assert job is not None
    assert job.status == 'success'
    assert job.source_format == 'csv'
    assert job.target_format == 'json'


@pytest.mark.asyncio
async def test_run_etl_pipeline_excel_to_csv(
    db_session, mock_brain, mock_factory, mock_sandbox, temp_excel_file, tmp_path
):
    """Test ETL pipeline: Excel → CSV transformation."""
    service = ETLService(
        session=db_session,
        _test_brain_client=mock_brain,
        factory=mock_factory,
        sandbox=mock_sandbox
    )
    
    output_file = str(tmp_path / "output.csv")
    
    result = await service.run_etl_pipeline(
        execution_id="test_002",
        source_file=temp_excel_file,
        target_spec="Transform data",
        output_file=output_file,
        output_format="csv"
    )
    
    assert result['status'] == 'success'
    assert Path(output_file).exists()
    
    # Verify format detection
    stmt = select(ETLJobHistory).where(ETLJobHistory.execution_id == "test_002")
    job = (await db_session.execute(stmt)).scalar_one_or_none()
    assert job.source_format == 'excel'


@pytest.mark.asyncio
async def test_run_etl_pipeline_json_to_excel(
    db_session, mock_brain, mock_factory, mock_sandbox, temp_json_file, tmp_path
):
    """Test ETL pipeline: JSON → Excel transformation."""
    service = ETLService(
        session=db_session,
        _test_brain_client=mock_brain,
        factory=mock_factory,
        sandbox=mock_sandbox
    )
    
    output_file = str(tmp_path / "output.xlsx")
    
    result = await service.run_etl_pipeline(
        execution_id="test_003",
        source_file=temp_json_file,
        target_spec="Transform data",
        output_file=output_file,
        output_format="excel"
    )
    
    assert result['status'] == 'success'
    assert Path(output_file).exists()


@pytest.mark.asyncio
async def test_detect_format_csv(db_session, mock_brain, mock_factory, mock_sandbox):
    """Test format detection for CSV files."""
    service = ETLService(
        session=db_session,
        _test_brain_client=mock_brain,
        factory=mock_factory,
        sandbox=mock_sandbox
    )
    
    assert service._detect_format("file.csv") == "csv"
    assert service._detect_format("FILE.CSV") == "csv"


@pytest.mark.asyncio
async def test_detect_format_excel(db_session, mock_brain, mock_factory, mock_sandbox):
    """Test format detection for Excel files."""
    service = ETLService(
        session=db_session,
        _test_brain_client=mock_brain,
        factory=mock_factory,
        sandbox=mock_sandbox
    )
    
    assert service._detect_format("file.xlsx") == "excel"
    assert service._detect_format("file.xls") == "excel"


@pytest.mark.asyncio
async def test_detect_format_json(db_session, mock_brain, mock_factory, mock_sandbox):
    """Test format detection for JSON files."""
    service = ETLService(
        session=db_session,
        _test_brain_client=mock_brain,
        factory=mock_factory,
        sandbox=mock_sandbox
    )
    
    assert service._detect_format("file.json") == "json"


@pytest.mark.asyncio
async def test_security_validation_fails(
    db_session, mock_brain, mock_factory, mock_sandbox, temp_csv_file, tmp_path
):
    """Test handling of security validation failure."""
    # Mock factory to return unsafe script
    mock_factory.generate_transformation_script.return_value = {
        'script': '''def transform(df):
    import os
    os.system("rm -rf /")
    return df
''',
        'metadata': {}
    }
    
    service = ETLService(
        session=db_session,
        _test_brain_client=mock_brain,
        factory=mock_factory,
        sandbox=mock_sandbox
    )
    
    output_file = str(tmp_path / "output.json")
    
    # Should raise SecurityException or similar
    result = await service.run_etl_pipeline(
        execution_id="test_004",
        source_file=temp_csv_file,
        target_spec="Test",
        output_file=output_file,
        output_format="json"
    )
    
    assert result['status'] == 'failed'
    assert 'validation failed' in result['error'].lower()
    
    # Verify job history shows failure
    stmt = select(ETLJobHistory).where(ETLJobHistory.execution_id == "test_004")
    job = (await db_session.execute(stmt)).scalar_one_or_none()
    if job:  # Job might not be created if validation fails early
        assert job.status == 'failed'


@pytest.mark.asyncio
async def test_sandbox_execution_error(
    db_session, mock_brain, mock_factory, mock_sandbox, temp_csv_file, tmp_path
):
    """Test handling of sandbox execution errors."""
    # Mock sandbox to raise error
    mock_sandbox.execute_in_sandbox.side_effect = Exception("Sandbox execution failed")
    
    service = ETLService(
        session=db_session,
        _test_brain_client=mock_brain,
        factory=mock_factory,
        sandbox=mock_sandbox
    )
    
    output_file = str(tmp_path / "output.json")
    
    result = await service.run_etl_pipeline(
        execution_id="test_005",
        source_file=temp_csv_file,
        target_spec="Test",
        output_file=output_file,
        output_format="json"
    )
    
    assert result['status'] == 'failed'
    assert 'error' in result
    
    # Verify job history
    stmt = select(ETLJobHistory).where(ETLJobHistory.execution_id == "test_005")
    job = (await db_session.execute(stmt)).scalar_one_or_none()
    assert job is not None
    assert job.status == 'failed'
    assert job.error_message is not None


@pytest.mark.asyncio
async def test_job_history_persistence(
    db_session, mock_brain, mock_factory, mock_sandbox, temp_csv_file, tmp_path
):
    """Test that job history is correctly persisted."""
    service = ETLService(
        session=db_session,
        _test_brain_client=mock_brain,
        factory=mock_factory,
        sandbox=mock_sandbox
    )
    
    output_file = str(tmp_path / "output.json")
    
    await service.run_etl_pipeline(
        execution_id="test_006",
        source_file=temp_csv_file,
        target_spec="Test transformation",
        output_file=output_file,
        output_format="json"
    )
    
    # Verify all fields are saved
    stmt = select(ETLJobHistory).where(ETLJobHistory.execution_id == "test_006")
    job = (await db_session.execute(stmt)).scalar_one_or_none()
    
    assert job is not None
    assert job.execution_id == "test_006"
    assert job.source_file == temp_csv_file
    assert job.target_file == output_file
    assert job.source_format == "csv"
    assert job.target_format == "json"
    assert job.script_content is not None
    assert job.status == "success"
    assert job.metadata is not None
    assert job.created_at is not None
    assert job.execution_time_ms >= 0

    assert job.created_at is not None
    assert job.execution_time_ms >= 0


@pytest.mark.asyncio
async def test_run_etl_pipeline_csv_to_odt(
    db_session, mock_brain, mock_factory, mock_sandbox, temp_csv_file, tmp_path
):
    """Test ETL pipeline: CSV → ODT transformation."""
    service = ETLService(
        session=db_session,
        _test_brain_client=mock_brain,
        factory=mock_factory,
        sandbox=mock_sandbox
    )
    
    output_file = str(tmp_path / "output.odt")
    
    # Patch ReportFactory where it is defined, as it is imported inside the function
    with patch('client_app.app.modules.factory.report_factory.ReportFactory') as MockReportFactory:
        mock_rf_instance = MockReportFactory.return_value
        
        result = await service.run_etl_pipeline(
            execution_id="test_odt_001",
            source_file=temp_csv_file,
            target_spec="Transform data",
            output_file=output_file,
            output_format="odt"
        )
        
        assert result['status'] == 'success'
        
        # Verify ReportFactory usage
        MockReportFactory.assert_called_once()
        mock_rf_instance.generate_odt.assert_called_once()
        call_args = mock_rf_instance.generate_odt.call_args
        context, path = call_args[0]
        assert path == output_file
        assert 'title' in context
        assert 'table_data' in context

"""
Unit tests for DeterministicETLService.

Tests each transformation operation to ensure correct behavior.
"""

import pytest
import pandas as pd
from datetime import datetime

from client_app.app.services.deterministic_etl_service import DeterministicETLService
from client_app.app.models.transform_operations import (
    DropColumnsOperation,
    RenameColumnsOperation,
    MergeColumnsOperation,
    FormatDatesOperation,
    FilterRowsOperation,
    ReplaceValuesOperation,
    NormalizeTextOperation,
    FillNullsOperation,
    RemoveDuplicatesOperation,
    RemoveNullRowsOperation
)


@pytest.fixture
def service():
    """Create DeterministicETLService instance."""
    return DeterministicETLService()


@pytest.fixture
def sample_df():
    """Create sample DataFrame for testing."""
    return pd.DataFrame({
        'name': ['Alice', 'Bob', 'Charlie', 'Alice'],
        'age': [25, 30, None, 25],
        'city': ['New York', 'Los Angeles', 'Chicago', 'New York'],
        'salary': [50000, 60000, 70000, 50000],
        'date': ['2023-01-15', '2023-02-20', '2023-03-10', '2023-01-15']
    })


@pytest.mark.asyncio
async def test_drop_columns(service, sample_df):
    """Test dropping columns."""
    op = DropColumnsOperation(columns=['age', 'city'])
    result = await service.execute_transformation(sample_df, [op])
    
    assert 'age' not in result.columns
    assert 'city' not in result.columns
    assert 'name' in result.columns
    assert 'salary' in result.columns


@pytest.mark.asyncio
async def test_rename_columns(service, sample_df):
    """Test renaming columns."""
    op = RenameColumnsOperation(mapping={'name': 'full_name', 'age': 'years'})
    result = await service.execute_transformation(sample_df, [op])
    
    assert 'full_name' in result.columns
    assert 'years' in result.columns
    assert 'name' not in result.columns
    assert 'age' not in result.columns


@pytest.mark.asyncio
async def test_merge_columns(service, sample_df):
    """Test merging columns."""
    op = MergeColumnsOperation(
        source_columns=['name', 'city'],
        target_column='name_city',
        separator=' - ',
        drop_source=True
    )
    result = await service.execute_transformation(sample_df, [op])
    
    assert 'name_city' in result.columns
    assert result['name_city'].iloc[0] == 'Alice - New York'
    assert 'name' not in result.columns
    assert 'city' not in result.columns


@pytest.mark.asyncio
async def test_format_dates(service, sample_df):
    """Test date formatting."""
    op = FormatDatesOperation(
        column='date',
        target_format='%d/%m/%Y'
    )
    result = await service.execute_transformation(sample_df, [op])
    
    assert result['date'].iloc[0] == '15/01/2023'


@pytest.mark.asyncio
async def test_filter_rows(service, sample_df):
    """Test filtering rows."""
    op = FilterRowsOperation(
        column='salary',
        operator='>',
        value=55000
    )
    result = await service.execute_transformation(sample_df, [op])
    
    assert len(result) == 2
    assert all(result['salary'] > 55000)


@pytest.mark.asyncio
async def test_replace_values(service, sample_df):
    """Test replacing values."""
    op = ReplaceValuesOperation(
        column='city',
        replacements={'New York': 'NYC', 'Los Angeles': 'LA'}
    )
    result = await service.execute_transformation(sample_df, [op])
    
    assert result['city'].iloc[0] == 'NYC'
    assert result['city'].iloc[1] == 'LA'


@pytest.mark.asyncio
async def test_normalize_text_upper(service, sample_df):
    """Test text normalization to uppercase."""
    op = NormalizeTextOperation(
        columns=['name', 'city'],
        mode='upper'
    )
    result = await service.execute_transformation(sample_df, [op])
    
    assert result['name'].iloc[0] == 'ALICE'
    assert result['city'].iloc[0] == 'NEW YORK'


@pytest.mark.asyncio
async def test_normalize_text_snake_case(service):
    """Test text normalization to snake_case."""
    df = pd.DataFrame({'field': ['First Name', 'Last-Name', 'EmailAddress']})
    op = NormalizeTextOperation(columns=['field'], mode='snake_case')
    result = await service.execute_transformation(df, [op])
    
    assert result['field'].iloc[0] == 'first_name'
    assert result['field'].iloc[1] == 'last_name'
    assert result['field'].iloc[2] == 'email_address'


@pytest.mark.asyncio
async def test_fill_nulls(service, sample_df):
    """Test filling null values."""
    op = FillNullsOperation(
        columns=['age'],
        value=0
    )
    result = await service.execute_transformation(sample_df, [op])
    
    assert result['age'].isna().sum() == 0
    assert result['age'].iloc[2] == 0


@pytest.mark.asyncio
async def test_remove_duplicates(service, sample_df):
    """Test removing duplicate rows."""
    op = RemoveDuplicatesOperation(keep='first')
    result = await service.execute_transformation(sample_df, [op])
    
    assert len(result) == 3  # One duplicate removed


@pytest.mark.asyncio
async def test_remove_null_rows(service, sample_df):
    """Test removing rows with null values."""
    op = RemoveNullRowsOperation(how='any')
    result = await service.execute_transformation(sample_df, [op])
    
    assert len(result) == 3  # Row with null age removed
    assert result['age'].isna().sum() == 0


@pytest.mark.asyncio
async def test_multiple_operations(service, sample_df):
    """Test chaining multiple operations."""
    operations = [
        RemoveNullRowsOperation(how='any'),
        RenameColumnsOperation(mapping={'name': 'full_name'}),
        FilterRowsOperation(column='salary', operator='>', value=50000),
        DropColumnsOperation(columns=['date'])
    ]
    
    result = await service.execute_transformation(sample_df, operations)
    
    assert len(result) == 1  # Only Bob remains after all filters
    assert 'full_name' in result.columns
    assert 'date' not in result.columns
    assert result['salary'].iloc[0] == 60000

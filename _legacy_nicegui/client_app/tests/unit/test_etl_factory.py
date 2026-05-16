import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock
from client_app.app.modules.factory.etl_factory import ETLScriptFactory


@pytest.fixture
def mock_brain():
    """Mock AI Brain Service."""
    brain = AsyncMock()
    brain.generate_code = AsyncMock(return_value={
        'code': '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Rename old_name to new_name and drop temp."""
    df = df.rename(columns={'old_name': 'new_name'})
    df = df.drop(columns=['temp'], errors='ignore')
    return df
''',
        'model': 'gemini-2.0-flash',
        'tokens': 150
    })
    return brain


@pytest.fixture
def source_dataframe():
    """Sample source DataFrame."""
    return pd.DataFrame({
        'old_name': [1, 2, 3],
        'temp': ['a', 'b', 'c']
    })


@pytest.mark.asyncio
async def test_generate_simple_transformation(mock_brain, source_dataframe):
    """Test generación de script simple (renombrar columnas)."""
    factory = ETLScriptFactory()

    target_spec = "Renombrar 'old_name' a 'new_name'. Eliminar 'temp'."

    result = await factory.generate_transformation_script(
        source_sample=source_dataframe,
        target_spec=target_spec,
        output_format='csv',
        client=mock_brain,
        license_key="TEST"
    )

    assert 'script' in result
    assert 'metadata' in result
    assert 'def transform(' in result['script']
    assert 'rename' in result['script'].lower()
    assert result['metadata']['model_used'] == 'gemini-2.0-flash'
    assert result['metadata']['tokens'] == 150
    assert result['metadata']['source_columns'] == ['old_name', 'temp']


@pytest.mark.asyncio
async def test_generate_with_dataframe_example(mock_brain, source_dataframe):
    """Test generación con DataFrame de ejemplo como target."""
    factory = ETLScriptFactory()

    # Mock para retornar script diferente
    mock_brain.generate_code.return_value = {
        'code': '''def transform(df: pd.DataFrame) -> pd.DataFrame:
    """Transform based on example."""
    df['new_column'] = df['old_name'] * 2
    return df[['new_column']]
''',
        'model': 'gpt-4o',
        'tokens': 200
    }

    target_example = pd.DataFrame({
        'new_column': [2, 4, 6]
    })

    result = await factory.generate_transformation_script(
        source_sample=source_dataframe,
        target_spec=target_example,
        output_format='json',
        client=mock_brain,
        license_key="TEST"
    )

    assert 'script' in result
    assert 'new_column' in result['script']
    assert result['metadata']['target_columns'] == ['new_column']


@pytest.mark.asyncio
async def test_generate_with_schema(mock_brain, source_dataframe):
    """Test generación con esquema JSON."""
    factory = ETLScriptFactory()

    schema = {
        'customer_id': 'int',
        'customer_name': 'str'
    }

    result = await factory.generate_transformation_script(
        source_sample=source_dataframe,
        target_spec=schema,
        output_format='parquet',
        client=mock_brain,
        license_key="TEST"
    )

    assert 'script' in result
    assert result['metadata']['target_columns'] == ['customer_id', 'customer_name']


@pytest.mark.asyncio
async def test_generate_with_user_instructions(mock_brain, source_dataframe):
    """Test que las instrucciones del usuario se incluyen en el prompt."""
    factory = ETLScriptFactory()

    user_inst = "Convertir fechas a formato ISO"

    result = await factory.generate_transformation_script(
        source_sample=source_dataframe,
        target_spec="Transform data",
        output_format='csv',
        user_instructions=user_inst,
        client=mock_brain,
        license_key="TEST"
    )

    # Verificar que el brain fue llamado
    assert mock_brain.generate_code.called
    call_args = mock_brain.generate_code.call_args

    # El prompt debe incluir las instrucciones del usuario
    prompt = call_args[1]['prompt']
    assert user_inst in prompt


@pytest.mark.asyncio
async def test_extract_script_from_markdown(mock_brain, source_dataframe):
    """Test extracción de código cuando viene wrapped en markdown."""
    factory = ETLScriptFactory()

    # Mock response with markdown wrapper
    mock_brain.generate_code.return_value = {
        'code': '''```python
def transform(df: pd.DataFrame) -> pd.DataFrame:
    return df
```''',
        'model': 'test',
        'tokens': 50
    }

    result = await factory.generate_transformation_script(
        source_sample=source_dataframe,
        target_spec="Test",
        output_format='csv',
        client=mock_brain,
        license_key="TEST"
    )

    # Debe extraer solo el código, sin markdown
    assert '```' not in result['script']
    assert 'def transform(' in result['script']


@pytest.mark.asyncio
async def test_prepare_source_context(mock_brain, source_dataframe):
    """Test preparación de contexto de origen."""
    factory = ETLScriptFactory()

    context = factory._prepare_source_context(source_dataframe)

    assert context['columns'] == ['old_name', 'temp']
    assert 'dtypes' in context
    assert 'sample_rows' in context
    assert len(context['sample_rows']) == 3
    assert context['row_count'] == 3


@pytest.mark.asyncio
async def test_prepare_target_context_description(mock_brain):
    """Test preparación de contexto objetivo (descripción)."""
    factory = ETLScriptFactory()

    context = factory._prepare_target_context("Rename columns", "csv")

    assert context['type'] == 'description'
    assert context['description'] == "Rename columns"
    assert context['format'] == 'csv'


@pytest.mark.asyncio
async def test_prepare_target_context_example(mock_brain):
    """Test preparación de contexto objetivo (ejemplo DataFrame)."""
    factory = ETLScriptFactory()

    target_df = pd.DataFrame({'col1': [1, 2]})
    context = factory._prepare_target_context(target_df, "json")

    assert context['type'] == 'example'
    assert context['columns'] == ['col1']
    assert context['format'] == 'json'


@pytest.mark.asyncio
async def test_prepare_target_context_schema(mock_brain):
    """Test preparación de contexto objetivo (esquema dict)."""
    factory = ETLScriptFactory()

    schema = {'field1': 'int', 'field2': 'str'}
    context = factory._prepare_target_context(schema, "parquet")

    assert context['type'] == 'schema'
    assert context['schema'] == schema
    assert context['format'] == 'parquet'


@pytest.mark.asyncio
async def test_generate_correction_uses_tier3(mock_brain, source_dataframe):
    """Test que la corrección usa Tier 3 (Supervisor)."""
    factory = ETLScriptFactory()

    await factory.generate_transformation_script(
        source_sample=source_dataframe,
        target_spec="Fix it",
        output_format='csv',
        is_correction=True,
        client=mock_brain,
        license_key="TEST"
    )

    # Verificar que el service_id es el de supervisor
    call_args = mock_brain.generate_code.call_args
    assert call_args[1]['service_id'] == 'sys_etl_transform_supervisor'


@pytest.mark.asyncio
async def test_generate_initial_uses_tier2(mock_brain, source_dataframe):
    """Test que la generación inicial usa Tier 2 (Generator)."""
    factory = ETLScriptFactory()

    await factory.generate_transformation_script(
        source_sample=source_dataframe,
        target_spec="Create it",
        output_format='csv',
        is_correction=False,
        client=mock_brain,
        license_key="TEST"
    )

    # Verificar que el service_id es el de generator
    call_args = mock_brain.generate_code.call_args
    assert call_args[1]['service_id'] == 'sys_etl_transform_generator'


# === NEW TESTS FOR PHASE 3 IMPROVEMENTS ===

from client_app.app.modules.factory.etl_factory import MAX_REFINEMENT_ITERATIONS


@pytest.mark.asyncio
async def test_generate_script_rehydrates_anonymized_code(mock_brain, source_dataframe):
    """Test que el script generado se rehidrata cuando hay anonimización."""
    factory = ETLScriptFactory()

    mock_ctx = MagicMock()
    mock_ctx.anonymize.side_effect = lambda x: x  # Pass-through
    mock_ctx.deanonymize.side_effect = lambda x: x.replace("ANON_001", "Juan")

    mock_brain.generate_code.return_value = {
        'code': 'df["name"] = "ANON_001"',
        'model': 'test',
        'tokens': 50
    }

    result = await factory.generate_transformation_script(
        source_sample=source_dataframe,
        target_spec="Transform",
        output_format='csv',
        ctx=mock_ctx,
        client=mock_brain,
        license_key="TEST"
    )

    # Script should be rehydrated
    assert "Juan" in result['script']
    mock_ctx.deanonymize.assert_called()


@pytest.mark.asyncio
async def test_refine_transformation_script_basic(mock_brain):
    """Test refinamiento básico de script ETL."""
    factory = ETLScriptFactory()

    mock_brain.generate_code.return_value = {
        'code': 'def transform(df): return df.dropna()'
    }

    refined, needs_escalation = await factory.refine_transformation_script(
        original_script='def transform(df): return df',
        execution_error='ValueError: missing values',
        user_feedback='Handle missing data',
        source_columns=['col1', 'col2'],
        client=mock_brain,
        iteration=0
    )

    assert needs_escalation is False
    assert 'dropna' in refined
    mock_brain.generate_code.assert_called_once()


@pytest.mark.asyncio
async def test_refine_transformation_script_escalation(mock_brain):
    """Test que se dispara escalación al alcanzar max iteraciones."""
    factory = ETLScriptFactory()

    refined, needs_escalation = await factory.refine_transformation_script(
        original_script='def transform(df): return df',
        execution_error='Error',
        user_feedback='Fix it',
        source_columns=['A'],
        client=mock_brain,
        iteration=MAX_REFINEMENT_ITERATIONS  # At max
    )

    assert needs_escalation is True
    # Client should NOT be called when escalating
    mock_brain.generate_code.assert_not_called()


@pytest.mark.asyncio
async def test_refine_transformation_script_rehydrates(mock_brain):
    """Test que el script refinado se rehidrata."""
    factory = ETLScriptFactory()

    mock_ctx = MagicMock()
    mock_ctx.anonymize.side_effect = lambda x: x.replace("secret", "MASKED")
    mock_ctx.deanonymize.side_effect = lambda x: x.replace("MASKED", "secret")

    mock_brain.generate_code.return_value = {
        'code': 'df["col"] = "MASKED"'
    }

    refined, _ = await factory.refine_transformation_script(
        original_script='df["col"] = "secret"',
        execution_error='Error',
        user_feedback='Keep secret',
        source_columns=['col'],
        ctx=mock_ctx,
        client=mock_brain,
        iteration=0
    )

    assert "secret" in refined
    mock_ctx.deanonymize.assert_called()


@pytest.mark.asyncio
async def test_refine_requires_client():
    """Test que se requiere client para refinar."""
    factory = ETLScriptFactory()

    with pytest.raises(ValueError, match="BrainAPIClient is required"):
        await factory.refine_transformation_script(
            original_script='code',
            execution_error='error',
            user_feedback='fix',
            source_columns=['A'],
            client=None,
            iteration=0
        )

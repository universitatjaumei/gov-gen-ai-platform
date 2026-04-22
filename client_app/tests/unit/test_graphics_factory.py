
import pytest
import pandas as pd
from unittest.mock import MagicMock, AsyncMock
from client_app.app.modules.factory.graphics_factory import GraphicsFactory, GraphicsScript
from client_app.app.services.script_generator_service import ScriptGeneratorService

@pytest.fixture
def mock_generator():
    return MagicMock(spec=ScriptGeneratorService)

@pytest.fixture
def factory(mock_generator):
    return GraphicsFactory(mock_generator)

def test_analyze_dataframe_structure(factory):
    """Verifica la extracción correcta de metadatos del DataFrame."""
    data = {
        'Category': ['A', 'B', 'A'],
        'Value': [10, 20, 30],
        'Date': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
    }
    df = pd.DataFrame(data)
    
    metadata = factory.analyze_dataframe(df)
    
    assert metadata['rows'] == 3
    assert metadata['columns'] == ['Category', 'Value', 'Date']
    assert metadata['dtypes']['Category'] == 'object' # or string depending on pandas version
    assert 'int' in metadata['dtypes']['Value']
    assert 'datetime' in metadata['dtypes']['Date']
    assert len(metadata['sample']) == 3

@pytest.mark.asyncio
async def test_generate_script_calls_brain(factory, mock_generator):
    """Verifica que generate_script invoca al BrainService correctamente."""
    df_metadata = {"columns": ["A", "B"], "rows": 10}
    user_prompt = "Create a bar chart"
    
    # Mock return
    mock_generator.generate_custom_script = AsyncMock(return_value={
        "success": True, 
        "content": "import matplotlib.pyplot as plt\n...",
        "parsed": {"code": "import matplotlib.pyplot as plt\n..."}
    })
    
    script = await factory.generate_script(df_metadata, user_prompt)
    
    assert isinstance(script, GraphicsScript)
    assert "matplotlib" in script.code
    assert script.metadata == df_metadata
    
    # Verify call to brain
    mock_generator.generate_custom_script.assert_called_once()
    call_args = mock_generator.generate_custom_script.call_args
    assert "A" in str(call_args) # Metadata in prompt
    assert user_prompt in str(call_args)

def test_analyze_dataframe_anonymizes_pii(factory, mock_generator):
    """Verifica que los datos sensibles en la muestra sean anonimizados."""
    # Mock anonymizer
    mock_anonymizer = MagicMock()
    mock_anonymizer.anonymize.side_effect = lambda x: f"MASKED_{x}" if isinstance(x, str) else x
    
    # Inject anonymizer into factory (via property or direct set if supported, 
    # but plan said init. So we might need to recreate factory or mock dependency)
    # factory.anonymizer = mock_anonymizer
    
    # Re-instantiate to be sure
    factory = GraphicsFactory(mock_generator, anonymizer=mock_anonymizer)
    
    data = {
        'Name': ['Juan', 'Maria'],
        'Email': ['juan@test.com', 'maria@test.com']
    }
    df = pd.DataFrame(data)
    print(f"Test DF Dtypes:\n{df.dtypes}")
    print(f"Selected: {df.select_dtypes(include=['object', 'string']).columns}")
    
    metadata = factory.analyze_dataframe(df)
    
    metadata = factory.analyze_dataframe(df)
    
    # Verify mock was called
    assert mock_anonymizer.anonymize.called, "Anonymizer was NEVER called"
    print(f"Mock calls: {mock_anonymizer.anonymize.call_args_list}")

    sample = metadata['sample']
    # Check that sample values are masked
    assert sample[0]['Name'] == "MASKED_Juan", f"Expected MASKED_Juan but got: {sample[0]['Name']}"
    assert sample[0]['Email'] == "MASKED_juan@test.com", f"Expected masked email but got: {sample[0]['Email']}"
    
    # Verify describe/summary is NOT leaking raw PII top/freq if possible?
    # Summary describes stats. For categorical, 'top' might leak.
    # Metadata extraction should probably anonymize summary too or exclude top/freq for sensitive cols.
    # For now, we focus on 'sample' data.

@pytest.mark.asyncio
async def test_generate_business_questions(factory, mock_generator):
    """Verifica la generación de preguntas de negocio."""
    df_metadata = {"columns": ["Sales", "Date"], "rows": 100}
    
    # Mock return
    expected_questions = ["What is the trend?", "Best seller?"]
    mock_generator.generate_custom_script = AsyncMock(return_value={
        "success": True,
        "parsed": {"questions": expected_questions}
    })
    
    questions = await factory.generate_business_questions(df_metadata)
    
    assert questions == expected_questions
    assert mock_generator.generate_custom_script.called
    args = mock_generator.generate_custom_script.call_args
    assert "business questions" in str(args) or "Data Analyst" in str(args)

@pytest.mark.asyncio
async def test_generate_visualization_suggestions(factory, mock_generator):
    """Verifica la generación de sugerencias de visualización."""
    df_metadata = {"columns": ["Category", "Value"], "rows": 50}
    question = "Compare categories"

    expected_suggestions = [
        {"type": "bar", "reason": "Good for categorical", "description": "Bar chart"}
    ]
    mock_generator.generate_custom_script = AsyncMock(return_value={
        "success": True,
        "parsed": {"suggestions": expected_suggestions}
    })

    suggestions = await factory.generate_visualization_suggestions(df_metadata, question)

    assert suggestions == expected_suggestions
    assert mock_generator.generate_custom_script.called
    args = mock_generator.generate_custom_script.call_args
    assert question in str(args)
    assert "Data Visualization expert" in str(args)


# === NEW TESTS FOR PHASE 2 IMPROVEMENTS ===

@pytest.mark.asyncio
async def test_generate_script_rehydrates_anonymized_code(mock_generator):
    """Verifica que el código generado se rehidrata correctamente."""
    mock_anonymizer = MagicMock()
    # Simulate anonymization replacing "Juan" with "ANON_001"
    mock_anonymizer.deanonymize.side_effect = lambda x: x.replace("ANON_001", "Juan")

    factory = GraphicsFactory(mock_generator, anonymizer=mock_anonymizer)

    df_metadata = {"columns": ["Name"], "rows": 1, "sample": [{"Name": "ANON_001"}]}

    # Mock returns code with anonymized value
    mock_generator.generate_custom_script = AsyncMock(return_value={
        "success": True,
        "content": "print('ANON_001')",
        "parsed": {"code": "print('ANON_001')"}
    })

    script = await factory.generate_script(df_metadata, "Show name")

    # Code should be rehydrated
    assert "Juan" in script.code
    assert "ANON_001" not in script.code
    mock_anonymizer.deanonymize.assert_called()


@pytest.mark.asyncio
async def test_refine_script_escalation_trigger(mock_generator):
    """Verifica que se dispara la escalación tras max iteraciones."""
    factory = GraphicsFactory(mock_generator)

    # Create script already at max iterations
    script = GraphicsScript(
        code="print('test')",
        metadata={"columns": ["A"]},
        iteration_count=3  # MAX_REFINEMENT_ITERATIONS
    )

    refined, needs_escalation = await factory.refine_script_with_escalation(
        script=script,
        feedback="Fix this"
    )

    assert needs_escalation is True
    assert refined.iteration_count == 3  # Not incremented


@pytest.mark.asyncio
async def test_refine_script_increments_iteration(mock_generator):
    """Verifica que el contador de iteraciones se incrementa."""
    mock_generator.generate_custom_script = AsyncMock(return_value={
        "success": True,
        "content": "refined_code()",
        "parsed": {}
    })

    factory = GraphicsFactory(mock_generator)

    script = GraphicsScript(
        code="original_code()",
        metadata={"columns": ["A"], "rows": 10},
        iteration_count=1
    )

    refined, needs_escalation = await factory.refine_script_with_escalation(
        script=script,
        feedback="Make it better"
    )

    assert needs_escalation is False
    assert refined.iteration_count == 2
    assert "refined_code" in refined.code


@pytest.mark.asyncio
async def test_refine_script_rehydrates_code(mock_generator):
    """Verifica que el código refinado se rehidrata."""
    mock_anonymizer = MagicMock()
    mock_anonymizer.anonymize.side_effect = lambda x: x.replace("secret", "MASKED")
    mock_anonymizer.deanonymize.side_effect = lambda x: x.replace("MASKED", "secret")

    mock_generator.generate_custom_script = AsyncMock(return_value={
        "success": True,
        "content": "print('MASKED')",
        "parsed": {}
    })

    factory = GraphicsFactory(mock_generator, anonymizer=mock_anonymizer)

    script = GraphicsScript(
        code="print('secret')",
        metadata={"columns": ["A"]},
        iteration_count=0
    )

    refined, _ = await factory.refine_script_with_escalation(
        script=script,
        feedback="Keep secret value"
    )

    assert "secret" in refined.code
    mock_anonymizer.deanonymize.assert_called()


import pytest
import pandas as pd
from app.modules.privacy.anonymizer import AnonymizationContext

@pytest.fixture
def anon_ctx():
    return AnonymizationContext()

def test_anonymize_dataframe_integration(anon_ctx):
    """
    Test integration of dataframe anonymization logic used in UI.
    Simulates the flow:
    1. Load DF
    2. Configure Columns
    3. Run Anonymization
    """
    # 1. Simulate Loaded DF
    data = {
        'nombre': ['Juan Pérez', 'Maria Garcia'],
        'dni': ['12345678X', 'L1234567X'],
        'email': ['juan@test.com', 'maria@test.com'],
        'notas': ['Nota 1', 'Nota 2']
    }
    df = pd.DataFrame(data)
    
    # 2. Simulate UI Configuration (columns_config)
    # We select columns and modes as if chosen in UI
    config = {
        'nombre': {'type': 'PERSON_NAME'},
        'dni': {'type': 'DNI', 'mode': 'AEPD'}, # Testing AEPD mode integration
        'email': {'type': 'EMAIL'},
        'notas': {'type': 'IGNORE'} # Should be ignored
    }
    
    # 3. Run Anonymization (Backend logic called by UI)
    result_df = anon_ctx.anonymize_dataframe(df, config)
    
    # Verifications
    
    # DNI (AEPD Mode)
    # 12345678X -> ***4567**
    assert result_df['dni'].iloc[0] == '***4567**'
    # L1234567X -> ****4567*
    assert result_df['dni'].iloc[1] == '****4567*'
    
    # Name (Should be faked)
    assert result_df['nombre'].iloc[0] != 'Juan Pérez'
    assert "Pérez" not in result_df['nombre'].iloc[0] # Very unlikely to generate same name
    
    # Email (Should be faked)
    assert result_df['email'].iloc[0] != 'juan@test.com'
    assert '@' in result_df['email'].iloc[0]
    
    # Notes (Ignored)
    assert result_df['notas'].iloc[0] == 'Nota 1'
    
    # Verify shape
    assert result_df.shape == df.shape


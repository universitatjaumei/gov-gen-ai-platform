import pytest
import os
import io
import json
import pandas as pd
from unittest.mock import MagicMock, patch, AsyncMock
from client_app.app.clients.brain_client import BrainAPIClient
from client_app.app.modules.factory.etl_factory import ETLScriptFactory
from client_app.app.modules.privacy.anonymizer import AnonymizationContext

@pytest.mark.asyncio
async def test_privacy_audit_interceptor_capture(capsys):
    """
    Test that BrainAPIClient intercepts and logs the payload when DEBUG_IA_TRAFFIC is true.
    """
    with patch.dict(os.environ, {"DEBUG_IA_TRAFFIC": "true"}):
        client = BrainAPIClient(base_url="http://mock-brain")
        
        # Mock httpx.AsyncClient response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"script": "print('ok')", "tokens_used": 100}
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            payload_prompt = "Process data for Juan Pérez with DNI 12345678Z"
            await client.generate_script(
                prompt=payload_prompt,
                output_schema={},
                license_key="TEST-KEY"
            )
            
            captured = capsys.readouterr()
            assert "[AUDITORÍA DE PRIVACIDAD]" in captured.out
            assert "Juan Pérez" in captured.out or "12345678Z" in captured.out
            # This test specifically checks the INTERCEPTOR exists. 
            # The anonymization is tested in the next test.

@pytest.mark.asyncio
async def test_etl_factory_anonymizes_sample_data():
    """
    Test that ETLScriptFactory anonymizes sample data before building the prompt.
    """
    # 1. Setup sample data with PII (using EMAIL which is regex-based and reliable)
    df = pd.DataFrame({
        "Email": ["juan.perez@example.com", "maria.garcia@secret.es"],
        "DNI": ["12345678Z", "87654321X"]
    })
    
    # 2. Mock Brain service
    mock_brain = MagicMock()
    mock_brain.generate_code = AsyncMock(return_value={"code": "def transform(df): return df", "tokens": 10})

    factory = ETLScriptFactory()
    ctx = AnonymizationContext(locale="es_ES")

    # 3. Generate script with anonymization context
    await factory.generate_transformation_script(
        source_sample=df,
        target_spec="Rename columns",
        output_format="csv",
        ctx=ctx,
        client=mock_brain,
        license_key="TEST"
    )
    
    # 4. Verify the prompt sent to Brain does NOT contain the real PII
    args, kwargs = mock_brain.generate_code.call_args
    prompt = kwargs.get("prompt", "")
    
    # Debug print
    print(f"DEBUG PROMPT: {prompt}")
    
    # Ensure real data are NOT in the prompt
    assert "juan.perez@example.com" not in prompt
    assert "12345678Z" not in prompt
    
    # Ensure prompt contains structure
    assert "Sample rows" in prompt
    assert "Email" in prompt
    assert "DNI" in prompt

@pytest.mark.asyncio
async def test_privacy_audit_e2e_no_pii_in_logs(capsys):
    """
    End-to-End simulation: ETL Factory + Brain Client with Debug Mode.
    Verify that the intercepted log contains fakes, not real PII.
    """
    with patch.dict(os.environ, {"DEBUG_IA_TRAFFIC": "true"}):
        # Setup data (Use Email for reliable regex capture)
        df = pd.DataFrame({"PII": ["juan.test@example.com"]})
        
        # Bridge Factory -> Client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": "...", "tokens": 0}
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            client = BrainAPIClient(base_url="http://mock")
            mock_brain_service = MagicMock()
            
            async def mock_gen_code(prompt, language, service_id):
                # Simulate the client call that logs
                await client.generate_script(prompt=prompt, output_schema={}, license_key="KEY")
                return {"code": "...", "tokens": 0}
            
            mock_brain_service.generate_code = AsyncMock(side_effect=mock_gen_code)

            factory = ETLScriptFactory()
            ctx = AnonymizationContext(locale="es_ES")

            await factory.generate_transformation_script(
                source_sample=df,
                target_spec="test",
                output_format="csv",
                ctx=ctx,
                client=mock_brain_service,
                license_key="TEST"
            )
            
            captured = capsys.readouterr()
            assert "[AUDITORÍA DE PRIVACIDAD]" in captured.out
            assert "juan.test@example.com" not in captured.out
            assert "PII" in captured.out # Structure remains

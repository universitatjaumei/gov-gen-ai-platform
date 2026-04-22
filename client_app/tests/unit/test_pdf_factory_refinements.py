import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from client_app.app.services.extraction_service import ExtractionService, FieldDef
from client_app.app.clients.brain_client import BrainAPIClient
from dataclasses import asdict

@pytest.mark.asyncio
async def test_run_factory_pipeline_anonymization_rehydration(tmp_path):
    """
    Verifica que el pipeline de fábrica:
    1. Anonimice el texto de entrada.
    2. Genere el script con texto anonimizado.
    3. Rehidrate el script antes de ejecutarlo en el Sandbox.
    """
    # 1. Preparar Mocks
    mock_brain = AsyncMock()
    # El LLM devuelve un script que usa el placeholder
    mock_brain.generate_extraction_script.return_value = "def extraer_datos(f): return {'field1': 'PLACEHOLDER_VAL'}"
    
    # Mock AnonymizationService
    mock_anon_service = MagicMock()
    # Simulamos que encuentra un dato sensible y lo cambia por PLACEHOLDER_VAL
    mock_anon_service.anonymize_text = AsyncMock(return_value={
        "anonymized_text": "Este es un dato: PLACEHOLDER_VAL", 
        "mapping": {"PLACEHOLDER_VAL": "DATO_REAL_99"}
    })
    
    # Mock Sandbox
    mock_sandbox = AsyncMock()
    mock_sandbox.execute_in_sandbox.return_value = {
        "success": True, 
        "data": [{"data": {"field1": "DATO_REAL_99"}}]
    }
    
    # Mock Path Manager
    mock_path_manager = MagicMock()
    exec_root = tmp_path / "exec_123"
    inputs_dir = exec_root / "inputs"
    inputs_dir.mkdir(parents=True)
    # Crear un PDF de mentira
    (inputs_dir / "test.pdf").write_text("%PDF-1.4 dummy")
    
    mock_path_manager.get_execution_path.return_value = exec_root
    
    # Injectar Mocks
    with patch("client_app.app.services.anonymization_service.AnonymizationService", return_value=mock_anon_service), \
         patch("client_app.app.services.extraction_service.script_library_service", AsyncMock()), \
         patch("client_app.app.services.extraction_service.audit_operation", MagicMock()):
        
        service = ExtractionService()
        service.sandbox = mock_sandbox
        service.path_manager = mock_path_manager
        
        # Forzar un doc1_text_list para saltar la extracción real de PDF
        docs_text = [{"filename": "test.pdf", "fitz": "DATO_REAL_99", "plumber": "DATO_REAL_99"}]
        field_defs = [FieldDef(name="field1", description="", example_value="DATO_REAL_99", is_optional=False)]
        
        # Mock de métodos internos que acceden a disco o red
        with patch.object(service, "_get_brain_client", AsyncMock(return_value=(mock_brain, "KEY"))), \
             patch("client_app.app.services.extraction_service.extraer_texto_dual", MagicMock(return_value=("DATO_REAL_99", "DATO_REAL_99", []))):
            
            # Mock _derive_anchors_from_doc1 AND _sample_texts to avoid hitting disk
            with patch.object(service, "_derive_anchors_from_doc1", AsyncMock(return_value={})), \
                 patch.object(service, "_sample_texts", AsyncMock(return_value=("DATO_REAL_99", "DATO_REAL_99"))):
                # Ejecutar el pipeline
                print("\nRunning pipeline...")
                res = await service.run_factory_pipeline(
                    execution_id="exec_123",
                    field_definitions=field_defs,
                    on_progress=MagicMock()
                )
                print(f"Pipeline finished with status: {res.get('status', 'unknown') if isinstance(res, dict) else 'non-dict result'}")
                if isinstance(res, dict) and res.get('status') == 'error':
                    print(f"Pipeline error message: {res.get('error')}")
            
            # VERIFICACIONES:
            
            # A. Se recordó llamar a anonimizar
            assert mock_anon_service.anonymize_text.called
            
            # B. El LLM recibió el texto anonimizado (PLACEHOLDER_VAL)
            brain_call = mock_brain.generate_extraction_script.call_args
            passed_docs = brain_call.kwargs['docs_text_list']
            assert "PLACEHOLDER_VAL" in passed_docs[0]['fitz']
            assert "DATO_REAL_99" not in passed_docs[0]['fitz']
            
            # C. El Sandbox recibió el código REHIDRATADO (DATO_REAL_99 reemplazado de vuelta)
            sandbox_call = mock_sandbox.execute_in_sandbox.call_args
            code_sent = sandbox_call.kwargs['code']
            assert "DATO_REAL_99" in code_sent
            assert "PLACEHOLDER_VAL" not in code_sent

@pytest.mark.asyncio
async def test_brain_client_escalate_script_payload():
    """Verifica que el cliente API envía el payload correcto para escalación."""
    client = BrainAPIClient(base_url="http://localhost:8080")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success", "escalation_id": 777}
    
    with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_response)) as mock_post:
        res = await client.escalate_script(
            script_name="Factura Robot",
            original_code="import os # error",
            client_notes="No funciona en windows",
            license_key="LIC-PRO-1"
        )
        
        assert res["escalation_id"] == 777
        assert mock_post.called
        _, kwargs = mock_post.call_args
        
        # Verificar URL y Headers
        assert "/api/brain/factory/escalate" in str(mock_post.call_args[0][0])
        assert kwargs["headers"]["X-License-Key"] == "LIC-PRO-1"
        
        # Verificar JSON
        payload = kwargs["json"]
        assert payload["script_name"] == "Factura Robot"
        assert payload["original_code"] == "import os # error"
        assert payload["client_notes"] == "No funciona en windows"

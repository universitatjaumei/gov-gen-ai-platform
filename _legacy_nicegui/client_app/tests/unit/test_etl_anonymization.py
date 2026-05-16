# client_app/tests/unit/test_etl_anonymization.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import pandas as pd
from client_app.app.services.etl_service import ETLService

class TestETLAnonymization:
    
    @pytest.mark.asyncio
    async def test_run_etl_pipeline_with_anonymization(self):
        # Setup Mocks
        mock_session = AsyncMock()
        mock_brain = AsyncMock()
        mock_factory = AsyncMock()
        mock_sandbox = AsyncMock()
        
        service = ETLService(
            session=mock_session,
            factory=mock_factory,
            sandbox=mock_sandbox,
            _test_brain_client=mock_brain
        )
        
        # Mock detections and reads
        service._detect_format = MagicMock(return_value='csv')
        service._read_source_file = AsyncMock(return_value=pd.DataFrame({'col1': ['real']}))
        service._write_output = AsyncMock()
        service._save_job_history = AsyncMock()
        
        # Mock Factory result
        mock_factory.generate_transformation_script.return_value = {
            'script': 'def transform(df):\n    return df',
            'metadata': {}
        }
        
        # Mock Sandbox result (Transform phase)
        # Returns a DF that needs anonymization
        transformed_df = pd.DataFrame({'email': ['real@test.com'], 'other': ['value']})
        mock_sandbox.execute_in_sandbox.return_value = transformed_df
        
        # Anonymization Config
        anon_config = {
            'email': {'type': 'EMAIL', 'mode': 'MASK'}
        }
        
        # Mock Anonymizer Context injection
        with patch('client_app.app.services.etl_service.AnonymizationContext') as MockCtx:
            mock_ctx_instance = MockCtx.return_value
            # Configure anonymize_dataframe to return modified DF
            def side_effect(df, config):
                df = df.copy()
                df['email'] = 'm***@masked.com'
                return df
            mock_ctx_instance.anonymize_dataframe.side_effect = side_effect
            
            # ACTION: Run pipeline
            result = await service.run_etl_pipeline(
                execution_id='test-id',
                source_file='source.csv',
                target_spec={},
                output_file='out.csv',
                output_format='csv',
                anonymization_config=anon_config # NEW PARAM
            )
            
            # ASSERTIONS
            if result['status'] != 'success':
                print(f"ETL Failed with error: {result.get('error')}")
            
            assert result['status'] == 'success'
            
            # Verify anonymizer was called with correct args
            mock_ctx_instance.anonymize_dataframe.assert_called_once()
            call_args = mock_ctx_instance.anonymize_dataframe.call_args
            assert call_args[0][0].equals(transformed_df) # First arg is DF
            assert call_args[0][1] == anon_config # Second arg is config
            
            # Verify output/result contains ANONYMIZED data
            result_df = result['data']
            assert result_df['email'].iloc[0] == 'm***@masked.com'
            
            # Verify _write_output used the anonymized DF
            service._write_output.assert_called_once()
            args = service._write_output.call_args[0]
            assert args[0]['email'].iloc[0] == 'm***@masked.com'


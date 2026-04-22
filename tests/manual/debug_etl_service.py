
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import pandas as pd
from client_app.app.services.etl_service import ETLService

async def main():
    try:
        # Setup Mocks
        mock_session = AsyncMock()
        mock_brain = AsyncMock()
        mock_factory = AsyncMock()
        mock_sandbox = AsyncMock()
        
        service = ETLService(mock_session, mock_brain, mock_factory, mock_sandbox)
        
        # Mock detections and reads
        service._detect_format = MagicMock(return_value='csv')
        service._read_source_file = AsyncMock(return_value=pd.DataFrame({'col1': ['real']}))
        service._write_output = AsyncMock()
        service._save_job_history = AsyncMock()
        
        # Mock Factory result
        mock_factory.generate_transformation_script.return_value = {
            'script': 'print("hello")',
            'metadata': {}
        }
        
        # Mock Sandbox result (Transform phase)
        transformed_df = pd.DataFrame({'email': ['real@test.com'], 'other': ['value']})
        mock_sandbox.execute_in_sandbox.return_value = transformed_df
        
        # Anonymization Config
        anon_config = {
            'email': {'type': 'EMAIL', 'mode': 'MASK'}
        }
        
        print("Starting pipeline...")
        
        # Mock Anonymizer Context injection
        with patch('client_app.app.services.etl_service.AnonymizationContext') as MockCtx:
            mock_ctx_instance = MockCtx.return_value
            # Configure anonymize_dataframe to return modified DF
            def side_effect(df, config):
                print("Anonymizer called!")
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
                anonymization_config=anon_config
            )
            
            print(f"Status: {result.get('status')}")
            if result.get('status') == 'failed':
                print(f"Error: {result.get('error')}")
                
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    asyncio.run(main())

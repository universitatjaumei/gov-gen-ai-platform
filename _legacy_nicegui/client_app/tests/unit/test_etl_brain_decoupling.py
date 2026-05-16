"""
Tests for ETL Service brain client resolution.

The architecture is:
- Production: Always uses BrainAPIClient for API calls to the server
- Tests: Can inject _test_brain_client mock with generate_code method
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from client_app.app.services.etl_service import ETLService
from client_app.app.modules.factory.etl_factory import ETLScriptFactory
from client_app.app.clients.brain_client import BrainAPIClient


@pytest.mark.asyncio
async def test_etl_get_brain_client_returns_api_client():
    """
    Verify that _get_brain_client returns BrainAPIClient for production use.
    """
    mock_session = AsyncMock()

    with patch('client_app.app.services.etl_service.AsyncSession') as mock_session_cls:
        mock_session_inner = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session_inner

        # Mock ServerConnection for URL
        mock_conn = MagicMock()
        mock_conn.brain_url = "http://brain-server:9000"
        mock_session_inner.get.return_value = mock_conn

        service = ETLService(session=mock_session)

        # Patch helper for license key
        with patch.object(service, '_get_active_license_key', return_value="prod_key"):
            client, key = await service._get_brain_client()

            assert isinstance(client, BrainAPIClient)
            assert client.base_url == "http://brain-server:9000"
            assert key == "prod_key"


@pytest.mark.asyncio
async def test_etl_get_brain_client_uses_test_client_when_provided():
    """
    Verify that when _test_brain_client is provided with generate_code method,
    it is used instead of creating a BrainAPIClient.
    """
    mock_session = AsyncMock()

    # Create a mock with generate_code method
    mock_test_client = MagicMock()
    mock_test_client.generate_code = AsyncMock()

    service = ETLService(
        session=mock_session,
        _test_brain_client=mock_test_client
    )

    client, key = await service._get_brain_client()

    assert client is mock_test_client
    assert key == "TEST_LICENSE_KEY"


@pytest.mark.asyncio
async def test_etl_get_brain_client_ignores_test_client_without_generate_code():
    """
    Verify that _test_brain_client is ignored if it doesn't have generate_code method.
    This prevents passing AIBrainService which doesn't have that method.
    """
    mock_session = AsyncMock()

    # Create a mock WITHOUT generate_code method
    mock_invalid_client = MagicMock(spec=[])  # Empty spec means no methods

    with patch('client_app.app.services.etl_service.AsyncSession') as mock_session_cls:
        mock_session_inner = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_session_inner

        mock_conn = MagicMock()
        mock_conn.brain_url = "http://brain-server:9000"
        mock_session_inner.get.return_value = mock_conn

        service = ETLService(
            session=mock_session,
            _test_brain_client=mock_invalid_client
        )

        with patch.object(service, '_get_active_license_key', return_value="prod_key"):
            client, key = await service._get_brain_client()

            # Should fall back to BrainAPIClient since mock doesn't have generate_code
            assert isinstance(client, BrainAPIClient)


@pytest.mark.asyncio
async def test_etl_pipeline_passes_client_to_factory():
    """
    Verify that run_etl_pipeline resolves client and passes it to factory.
    """
    mock_session = AsyncMock()
    mock_client = AsyncMock()
    mock_client.generate_code = AsyncMock()

    service = ETLService(session=mock_session, _test_brain_client=mock_client)

    # Mock factory
    service.factory = MagicMock()
    service.factory.generate_transformation_script = AsyncMock(return_value={
        'script': 'def transform(df): return df',
        'metadata': {}
    })

    # Mock internal methods
    service._read_source_file = AsyncMock(return_value=MagicMock(head=lambda n: "dummy_df"))
    service._write_output = AsyncMock()
    service._save_job_history = AsyncMock()
    service._execute_script_direct = MagicMock(return_value=MagicMock())

    await service.run_etl_pipeline(
        execution_id="123",
        source_file="test.csv",
        target_spec="Transform data",
        user_instructions="Simple transformation",
        output_file="out.csv",
        output_format="csv"
    )

    # Verify factory was called with client/license arguments
    service.factory.generate_transformation_script.assert_called_once()
    kwargs = service.factory.generate_transformation_script.call_args.kwargs

    assert kwargs.get('client') == mock_client
    assert kwargs.get('license_key') == "TEST_LICENSE_KEY"

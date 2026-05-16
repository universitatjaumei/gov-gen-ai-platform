
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import pandas as pd
from client_app.app.services.graphics_service import GraphicsService
from client_app.app.modules.factory.graphics_factory import GraphicsScript

class TestGraphicsService:
    """Tests for the Headless Graphics Service."""

    @pytest.fixture
    def mock_factory(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_factory):
        # We inject the factory or mock the class instantiation
        svc = GraphicsService()
        svc.factory = mock_factory # Inject mock
        return svc

    @pytest.mark.asyncio
    async def test_process_file_success(self, service, mock_factory, tmp_path):
        """Verifies full headless flow execution."""
        # Setup
        dummy_csv = tmp_path / "data.csv"
        dummy_csv.write_text("a,b\n1,2")
        prompt = "Plot it"
        output_path = tmp_path / "output.png"
        
        # Mocks
        mock_factory.analyze_dataframe.return_value = {"columns": ["a", "b"]}
        mock_factory.generate_script = AsyncMock(return_value=GraphicsScript(code="print('plot')", metadata={}))
        mock_factory.execute_script.return_value = b"fake_image_bytes"
        
        # Execute
        result_path = await service.process_file(str(dummy_csv), prompt, str(output_path))
        
        # Verification
        assert result_path == str(output_path)
        assert output_path.exists()
        assert output_path.read_bytes() == b"fake_image_bytes"
        
        mock_factory.analyze_dataframe.assert_called_once()
        mock_factory.generate_script.assert_called_once()
        mock_factory.execute_script.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_dataframe_success(self, service, mock_factory):
        """Verifies flow passing dataframe directly."""
        df = pd.DataFrame({"x": [1]})
        
        mock_factory.analyze_dataframe.return_value = {}
        mock_factory.generate_script = AsyncMock(return_value=GraphicsScript(code="pass", metadata={}))
        mock_factory.execute_script.return_value = b"bytes"
        
        result_bytes = await service.process_dataframe(df, "prompt")
        
        assert result_bytes == b"bytes"

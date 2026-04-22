import pytest
import pandas as pd
import os
from unittest.mock import MagicMock, patch
from client_app.app.modules.factory.report_factory import ReportFactory

# Mock odfpy imports in case it's not installed in the test environment yet
# In a real environment, we would expect these to be available.
# But for the purpose of TDD red-green-refactor, we will rely on the implementation failing
# because the method _generate_with_odfpy doesn't exist yet.

class TestODTGeneration:
    """Test ODT generation functionality in ReportFactory."""

    @pytest.fixture
    def factory(self):
        return ReportFactory(backend="reportlab") # Backend doesn't strictly matter if calling private method directly, or generic generate

    @pytest.fixture
    def sample_context(self):
        return {
            "title": "Test Report",
            "subtitle": "Subtitle Test",
            "date": "2023-10-27",
            "summary": "This is a summary of the report.",
            "sections": [
                {"heading": "Section 1", "content": "Content of section 1."},
                {"heading": "Section 2", "content": "Content of section 2."}
            ],
            "table_data": pd.DataFrame({
                "Name": ["Alice", "Bob"],
                "Age": [30, 25],
                "City": ["New York", "Los Angeles"]
            }),
            "styles": {
                "title_color": "#FF0000",
                "title_size": 24,
                "body_size": 12
            }
        }

    def test_generate_odt_creates_file(self, factory, sample_context, tmp_path):
        """Test that _generate_with_odfpy creates a file at the specified path."""
        output_path = tmp_path / "test_report.odt"
        
        # This method doesn't exist yet, so this test should fail
        if not hasattr(factory, 'generate_odt'):
            pytest.fail("ReportFactory does not have generate_odt method")

        result_path = factory.generate_odt(sample_context, str(output_path))
        
        assert os.path.exists(output_path)
        assert result_path == str(output_path)

    def test_odt_has_valid_structure(self, factory, sample_context, tmp_path):
        """Test that the generated ODT file can be parsed (basic validity check)."""
        output_path = tmp_path / "structure_test.odt"
        
        if not hasattr(factory, 'generate_odt'):
            pytest.fail("ReportFactory does not have generate_odt method")
            
        factory.generate_odt(sample_context, str(output_path))
        
        # Verify it's a valid zip file (ODT is XML in ZIP)
        import zipfile
        assert zipfile.is_zipfile(output_path)
        
        with zipfile.ZipFile(output_path, 'r') as zf:
            assert "content.xml" in zf.namelist()
            assert "mimetype" in zf.namelist()
            with zf.open("mimetype") as f:
                 assert f.read().decode('utf-8') == "application/vnd.oasis.opendocument.text"

    def test_dataframe_to_odt_table(self, factory):
        """Test the helper method _dataframe_to_odt_table."""
        df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        
        if not hasattr(factory, '_dataframe_to_odt_table'):
             pytest.fail("ReportFactory does not have _dataframe_to_odt_table method")

        # We need to mock the document object expected by the method
        mock_doc = MagicMock()
        
        # We can't easily test the internals without odfpy objects if implied imports are missing
        # so this test assumes the method returns an odf.table.Table object
        table = factory._dataframe_to_odt_table(mock_doc, df)
        
        assert table is not None
        # In actual implementation, we'd check if it's an instance of odf.table.Table
        # For now, just checking it returns something is enough for the skeleton

    def test_odt_styles_applied(self, factory, sample_context, tmp_path):
        """Test that styles from context are processed."""
        output_path = tmp_path / "style_test.odt"
        
        if not hasattr(factory, 'generate_odt'):
             pytest.fail("ReportFactory does not have generate_odt method")

        # This is a bit harder to verify without parsing content.xml
        # Ideally we would mock the internal style creation methods to match strict call arguments.
        # For this integration-level unit test, we'll verify it runs without error given styles.
        factory.generate_odt(sample_context, str(output_path))
        assert os.path.exists(output_path)

    def test_generate_report_dispatches_odt(self, factory, sample_context, tmp_path):
        """Test that generate_report calls generate_odt when format is 'odt'."""
        output_path = tmp_path / "dispatch_test.odt"
        
        # Mock generate_odt to verify call
        with patch.object(factory, 'generate_odt', return_value=str(output_path)) as mock_odt:
             result = factory.generate_report(sample_context, str(output_path), format="odt")
             mock_odt.assert_called_once_with(sample_context, str(output_path))
             assert result == str(output_path)
             
        # Test auto-detect by extension
        with patch.object(factory, 'generate_odt', return_value=str(output_path)) as mock_odt:
             result = factory.generate_report(sample_context, str(output_path)) 
             mock_odt.assert_called_once_with(sample_context, str(output_path))

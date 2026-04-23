"""Tests para el procesador Docling."""
import pytest
from unittest.mock import Mock, patch


class TestDoclingProcessor:

    def test_process_pdf_returns_markdown(self) -> None:
        from server.app.modules.agents_hub.ingestion.docling_processor import DoclingProcessor

        with patch('server.app.modules.agents_hub.ingestion.docling_processor.DocumentConverter') as mock_converter:
            mock_result = Mock()
            mock_result.document.export_to_markdown.return_value = "# Título\n\nContenido"
            mock_converter.return_value.convert.return_value = mock_result

            processor = DoclingProcessor()
            result = processor.process_pdf("test.pdf")

            assert "# Título" in result
            assert "Contenido" in result

    def test_process_url_returns_markdown(self) -> None:
        from server.app.modules.agents_hub.ingestion.docling_processor import DoclingProcessor

        with patch('server.app.modules.agents_hub.ingestion.docling_processor.DocumentConverter') as mock_converter:
            mock_result = Mock()
            mock_result.document.export_to_markdown.return_value = "# Web Page\n\nContent"
            mock_converter.return_value.convert.return_value = mock_result

            processor = DoclingProcessor()
            result = processor.process_url("https://example.com")

            assert "# Web Page" in result

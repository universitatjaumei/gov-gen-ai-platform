"""Procesador de documentos usando Docling."""

from pathlib import Path

from docling.document_converter import DocumentConverter


class DoclingProcessor:
    """Convierte PDFs y URLs a Markdown usando Docling."""

    def __init__(self):
        self.converter = DocumentConverter()

    def process_pdf(self, pdf_path: str | Path) -> str:
        """Convierte un PDF a Markdown.

        Args:
            pdf_path: Ruta al archivo PDF

        Returns:
            Contenido en formato Markdown
        """
        result = self.converter.convert(str(pdf_path))
        return result.document.export_to_markdown()

    def process_url(self, url: str) -> str:
        """Convierte una página web a Markdown.

        Args:
            url: URL de la página

        Returns:
            Contenido en formato Markdown
        """
        result = self.converter.convert(url)
        return result.document.export_to_markdown()

    def process(self, source: str) -> str:
        """Procesa automáticamente PDF o URL.

        Args:
            source: Ruta a PDF o URL

        Returns:
            Contenido en formato Markdown
        """
        if source.startswith(("http://", "https://")):
            return self.process_url(source)
        return self.process_pdf(source)

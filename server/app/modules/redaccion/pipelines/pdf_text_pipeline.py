"""PDFTextExtractionPipeline — extracción de texto de PDFs digitales con Docling (9R.5.2).

Usa Docling sin OCR: detecta PDFs sin capa de texto (escaneados o imagen)
emitiendo NON_EXTRACTABLE_PDF. Para PDFs escaneados con OCR, usar en el
futuro un pipeline específico (PDFOCRExtractionPipeline).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from server.app.modules.redaccion.pipelines.contracts import (
    ExtractionInput,
    ExtractionProvenance,
    ExtractionResult,
    ExtractionWarning,
)


class PDFTextExtractionPipeline:
    """Extrae texto plano de PDFs con capa de texto usando Docling (sin OCR).

    La desactivación de OCR y de análisis de tablas hace el pipeline ligero y
    determinista. Un PDF sin texto detectado emite NON_EXTRACTABLE_PDF (error).
    """

    pipeline_id = "pdf_text_pipeline_v1"

    def __init__(self) -> None:
        opts = PdfPipelineOptions()
        opts.do_ocr = False
        opts.do_table_structure = False
        opts.do_picture_classification = False
        opts.generate_page_images = False
        self._converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
        )

    def supports(self, source_kind: str) -> bool:
        return source_kind == "pdf_text"

    def extract(self, inp: ExtractionInput) -> ExtractionResult:
        if inp.file_ref is None:
            raise ValueError("PDFTextExtractionPipeline requiere file_ref en ExtractionInput.")

        file_path = Path(inp.file_ref.bucket) / inp.file_ref.key
        conv = self._converter.convert(str(file_path))

        num_pages = conv.document.num_pages()
        text = conv.document.export_to_text().strip()

        warnings: list[ExtractionWarning] = []
        if not text:
            warnings.append(
                ExtractionWarning(
                    code="NON_EXTRACTABLE_PDF",
                    message=(
                        "El PDF no contiene capa de texto extractable "
                        "(posiblemente imagen escaneada)."
                    ),
                    severity="error",
                )
            )

        provenance = ExtractionProvenance(
            pipeline_id=self.pipeline_id,
            source_ref=str(inp.file_ref),
            extracted_at=datetime.now(timezone.utc),
            pages=list(range(1, num_pages + 1)),
        )

        return ExtractionResult(
            free_text=text or None,
            warnings=warnings,
            provenance=provenance,
        )

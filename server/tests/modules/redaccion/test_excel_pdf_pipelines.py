"""Tests 9R.5.2 — ExcelExtractionPipeline + PDFTextExtractionPipeline (RED → GREEN)."""
from __future__ import annotations

from pathlib import Path


class TestExcelExtractionPipeline:

    def test_excel_pipeline_reads_basic_table(self, sample_xlsx: Path) -> None:
        from server.app.modules.redaccion.pipelines.contracts import ExtractionInput, StorageRef
        from server.app.modules.redaccion.pipelines.excel_pipeline import ExcelExtractionPipeline

        pipeline = ExcelExtractionPipeline()
        ref = StorageRef(bucket=str(sample_xlsx.parent), key=sample_xlsx.name)
        inp = ExtractionInput(source_kind="excel", file_ref=ref)

        result = pipeline.extract(inp)

        assert len(result.tables) == 1
        table = result.tables[0]
        assert "nombre" in table.headers
        assert "valor" in table.headers
        assert "categoria" in table.headers
        assert len(table.rows) == 3

    def test_excel_pipeline_reports_missing_required_columns(self, sample_xlsx: Path) -> None:
        from server.app.modules.redaccion.pipelines.contracts import ExtractionInput, StorageRef
        from server.app.modules.redaccion.pipelines.excel_pipeline import ExcelExtractionPipeline

        pipeline = ExcelExtractionPipeline()
        ref = StorageRef(bucket=str(sample_xlsx.parent), key=sample_xlsx.name)
        inp = ExtractionInput(
            source_kind="excel",
            file_ref=ref,
            options={"required_columns": ["nombre", "columna_inexistente"]},
        )

        result = pipeline.extract(inp)

        warning_codes = [w.code for w in result.warnings]
        assert "MISSING_COLUMN" in warning_codes
        missing = [w for w in result.warnings if w.code == "MISSING_COLUMN"]
        assert "columna_inexistente" in missing[0].message

    def test_excel_pipeline_handles_multiple_sheets(self, multi_sheet_xlsx: Path) -> None:
        from server.app.modules.redaccion.pipelines.contracts import ExtractionInput, StorageRef
        from server.app.modules.redaccion.pipelines.excel_pipeline import ExcelExtractionPipeline

        pipeline = ExcelExtractionPipeline()
        ref = StorageRef(bucket=str(multi_sheet_xlsx.parent), key=multi_sheet_xlsx.name)
        inp = ExtractionInput(source_kind="excel", file_ref=ref, options={"sheet": 1})

        result = pipeline.extract(inp)

        assert len(result.tables) == 1
        headers = result.tables[0].headers
        assert "ciudad" in headers
        assert "poblacion" in headers

    def test_excel_provenance_records_sheet_and_header_row(self, sample_xlsx: Path) -> None:
        from server.app.modules.redaccion.pipelines.contracts import ExtractionInput, StorageRef
        from server.app.modules.redaccion.pipelines.excel_pipeline import ExcelExtractionPipeline

        pipeline = ExcelExtractionPipeline()
        ref = StorageRef(bucket=str(sample_xlsx.parent), key=sample_xlsx.name)
        inp = ExtractionInput(
            source_kind="excel",
            file_ref=ref,
            options={"sheet": 0, "header_row": 0},
        )

        result = pipeline.extract(inp)

        assert result.provenance.pipeline_id == "excel_pipeline_v1"
        assert sample_xlsx.name in result.provenance.source_ref
        assert result.provenance.column_mapping is not None
        assert result.provenance.column_mapping.get("_sheet") == "0"
        assert result.provenance.column_mapping.get("_header_row") == "0"


class TestPDFTextExtractionPipeline:

    def test_pdf_text_pipeline_extracts_paragraphs(self, sample_pdf: Path, pdf_text_pipeline) -> None:
        from server.app.modules.redaccion.pipelines.contracts import ExtractionInput, StorageRef

        ref = StorageRef(bucket=str(sample_pdf.parent), key=sample_pdf.name)
        inp = ExtractionInput(source_kind="pdf_text", file_ref=ref)

        result = pdf_text_pipeline.extract(inp)

        assert result.free_text is not None
        assert len(result.free_text) > 0

    def test_pdf_pipeline_reports_non_extractable_pdf(self, image_only_pdf: Path, pdf_text_pipeline) -> None:
        from server.app.modules.redaccion.pipelines.contracts import ExtractionInput, StorageRef

        ref = StorageRef(bucket=str(image_only_pdf.parent), key=image_only_pdf.name)
        inp = ExtractionInput(source_kind="pdf_text", file_ref=ref)

        result = pdf_text_pipeline.extract(inp)

        warning_codes = [w.code for w in result.warnings]
        assert "NON_EXTRACTABLE_PDF" in warning_codes
        non_extractable = [w for w in result.warnings if w.code == "NON_EXTRACTABLE_PDF"]
        assert non_extractable[0].severity == "error"

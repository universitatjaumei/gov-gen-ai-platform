"""Tests 9R.5.3 — PDFTableExtractionPipeline + ManualInputPipeline (RED → GREEN)."""
from __future__ import annotations

from pathlib import Path

import pytest


class TestPDFTableExtractionPipeline:

    def test_pdf_table_pipeline_detects_tables_with_camelot(self, pdf_with_tables: Path) -> None:
        pytest.importorskip("camelot")
        from server.app.modules.redaccion.pipelines.contracts import ExtractionInput, StorageRef
        from server.app.modules.redaccion.pipelines.pdf_table_pipeline import PDFTableExtractionPipeline

        pipeline = PDFTableExtractionPipeline()
        ref = StorageRef(bucket=str(pdf_with_tables.parent), key=pdf_with_tables.name)
        inp = ExtractionInput(source_kind="pdf_table", file_ref=ref)

        result = pipeline.extract(inp)

        assert len(result.tables) >= 1
        table = result.tables[0]
        assert len(table.headers) == 3
        assert table.source_page == 1
        assert result.provenance.pipeline_id == "pdf_table_pipeline_v1"

    def test_pdf_table_pipeline_warns_when_no_tables_found(self, sample_pdf: Path) -> None:
        pytest.importorskip("camelot")
        from server.app.modules.redaccion.pipelines.contracts import ExtractionInput, StorageRef
        from server.app.modules.redaccion.pipelines.pdf_table_pipeline import PDFTableExtractionPipeline

        pipeline = PDFTableExtractionPipeline()
        ref = StorageRef(bucket=str(sample_pdf.parent), key=sample_pdf.name)
        inp = ExtractionInput(source_kind="pdf_table", file_ref=ref)

        result = pipeline.extract(inp)

        warning_codes = [w.code for w in result.warnings]
        assert "NO_TABLES_FOUND" in warning_codes
        no_tables_warn = next(w for w in result.warnings if w.code == "NO_TABLES_FOUND")
        assert no_tables_warn.severity == "warning"
        assert len(result.tables) == 0


class TestManualInputPipeline:

    def test_manual_pipeline_parses_numbers(self) -> None:
        from server.app.modules.redaccion.pipelines.contracts import ExtractionInput
        from server.app.modules.redaccion.pipelines.manual_pipeline import ManualInputPipeline

        pipeline = ManualInputPipeline()
        inp = ExtractionInput(
            source_kind="manual",
            raw_text="1.234,56",
            options={"slot": {"slot_id": "importe", "kind": "number", "required": True}},
        )

        result = pipeline.extract(inp)

        assert len(result.metrics) == 1
        assert result.metrics[0].name == "importe"
        assert result.metrics[0].value == pytest.approx(1234.56)
        assert not result.warnings

    def test_manual_pipeline_validates_required_slots(self) -> None:
        from server.app.modules.redaccion.pipelines.contracts import ExtractionInput
        from server.app.modules.redaccion.pipelines.manual_pipeline import ManualInputPipeline

        pipeline = ManualInputPipeline()
        inp = ExtractionInput(
            source_kind="manual",
            raw_text="",
            options={"slot": {"slot_id": "campo_obligatorio", "kind": "text", "required": True}},
        )

        result = pipeline.extract(inp)

        warning_codes = [w.code for w in result.warnings]
        assert "REQUIRED_FIELD_EMPTY" in warning_codes
        required_warn = next(w for w in result.warnings if w.code == "REQUIRED_FIELD_EMPTY")
        assert required_warn.severity == "error"
        assert "campo_obligatorio" in required_warn.message

    def test_manual_pipeline_rejects_wrong_type(self) -> None:
        from server.app.modules.redaccion.pipelines.contracts import ExtractionInput
        from server.app.modules.redaccion.pipelines.manual_pipeline import ManualInputPipeline

        pipeline = ManualInputPipeline()
        inp = ExtractionInput(
            source_kind="manual",
            raw_text="no es un numero",
            options={"slot": {"slot_id": "precio", "kind": "number", "required": True}},
        )

        result = pipeline.extract(inp)

        warning_codes = [w.code for w in result.warnings]
        assert "TYPE_MISMATCH" in warning_codes
        type_warn = next(w for w in result.warnings if w.code == "TYPE_MISMATCH")
        assert type_warn.severity == "error"
        assert len(result.metrics) == 0

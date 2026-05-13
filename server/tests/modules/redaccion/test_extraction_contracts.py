"""Tests de contrato del módulo de extracción — 9R.5.1 (RED → GREEN).

Verifican que ExtractionInput, ExtractionResult, ExtractionProvenance,
ExtractionWarning, ExtractedTable, ExtractedMetric y ExtractionPipeline
cumplen el contrato común que todos los pipelines deben respetar.
"""
from __future__ import annotations

import typing
from datetime import datetime, timezone

import pytest


class TestExtractionInput:

    def test_extraction_input_has_required_fields(self):
        from server.app.modules.redaccion.pipelines.contracts import ExtractionInput

        inp = ExtractionInput(source_kind="excel")

        assert inp.source_kind == "excel"
        assert inp.file_ref is None
        assert inp.raw_text is None
        assert isinstance(inp.options, dict)

    def test_extraction_input_accepts_all_source_kinds(self):
        from server.app.modules.redaccion.pipelines.contracts import ExtractionInput

        for kind in ("excel", "pdf_text", "pdf_table", "manual", "admin_script"):
            inp = ExtractionInput(source_kind=kind)
            assert inp.source_kind == kind

    def test_extraction_input_with_file_ref(self):
        from server.app.modules.redaccion.pipelines.contracts import (
            ExtractionInput,
            StorageRef,
        )

        ref = StorageRef(bucket="govgenai-dev", key="uploads/report.xlsx")
        inp = ExtractionInput(source_kind="excel", file_ref=ref, options={"sheet": 0})

        assert inp.file_ref == ref
        assert inp.options["sheet"] == 0

    def test_extraction_input_with_raw_text(self):
        from server.app.modules.redaccion.pipelines.contracts import ExtractionInput

        inp = ExtractionInput(source_kind="manual", raw_text="Texto libre del usuario.")
        assert inp.raw_text == "Texto libre del usuario."


class TestExtractionWarning:

    def test_extraction_warning_has_severity_and_code(self):
        from server.app.modules.redaccion.pipelines.contracts import ExtractionWarning

        w = ExtractionWarning(code="MISSING_COLUMN", message="Columna 'total' no encontrada.", severity="warning")

        assert w.code == "MISSING_COLUMN"
        assert w.severity == "warning"
        assert "total" in w.message

    def test_extraction_warning_accepts_error_severity(self):
        from server.app.modules.redaccion.pipelines.contracts import ExtractionWarning

        w = ExtractionWarning(code="PARSE_ERROR", message="No se pudo parsear la hoja.", severity="error")
        assert w.severity == "error"

    def test_extraction_warning_accepts_info_severity(self):
        from server.app.modules.redaccion.pipelines.contracts import ExtractionWarning

        w = ExtractionWarning(code="EXTRA_COLUMN", message="Columna extra ignorada.", severity="info")
        assert w.severity == "info"


class TestExtractionProvenance:

    def test_extraction_provenance_required_fields(self):
        from server.app.modules.redaccion.pipelines.contracts import ExtractionProvenance

        now = datetime.now(timezone.utc)
        prov = ExtractionProvenance(
            pipeline_id="excel_pipeline_v1",
            source_ref="uploads/report.xlsx",
            extracted_at=now,
        )

        assert prov.pipeline_id == "excel_pipeline_v1"
        assert prov.source_ref == "uploads/report.xlsx"
        assert prov.extracted_at == now
        assert prov.column_mapping is None
        assert prov.pages is None

    def test_extraction_provenance_with_optional_fields(self):
        from server.app.modules.redaccion.pipelines.contracts import ExtractionProvenance

        prov = ExtractionProvenance(
            pipeline_id="pdf_table_v1",
            source_ref="uploads/doc.pdf",
            extracted_at=datetime.now(timezone.utc),
            column_mapping={"A": "metric_name", "B": "value"},
            pages=[1, 3, 5],
        )

        assert prov.column_mapping == {"A": "metric_name", "B": "value"}
        assert prov.pages == [1, 3, 5]


class TestExtractionResult:

    def test_extraction_result_contains_provenance(self):
        from server.app.modules.redaccion.pipelines.contracts import (
            ExtractionProvenance,
            ExtractionResult,
        )

        prov = ExtractionProvenance(
            pipeline_id="excel_pipeline_v1",
            source_ref="uploads/test.xlsx",
            extracted_at=datetime.now(timezone.utc),
        )
        result = ExtractionResult(provenance=prov)

        assert result.provenance == prov
        assert result.tables == []
        assert result.metrics == []
        assert result.free_text is None
        assert result.warnings == []

    def test_extraction_result_serializable_to_openapi(self):
        from server.app.modules.redaccion.pipelines.contracts import (
            ExtractionProvenance,
            ExtractionResult,
            ExtractionWarning,
            ExtractedMetric,
            ExtractedTable,
        )

        prov = ExtractionProvenance(
            pipeline_id="pdf_text_v1",
            source_ref="uploads/informe.pdf",
            extracted_at=datetime.now(timezone.utc),
        )
        table = ExtractedTable(
            name="Tabla de indicadores",
            headers=["Indicador", "Valor"],
            rows=[["Tasa de éxito", "92%"]],
        )
        metric = ExtractedMetric(name="tasa_exito", value=0.92, unit="%")
        warning = ExtractionWarning(code="LOW_CONFIDENCE", message="Baja confianza en OCR.", severity="warning")

        result = ExtractionResult(
            tables=[table],
            metrics=[metric],
            free_text="Texto extraído del informe.",
            warnings=[warning],
            provenance=prov,
        )

        data = result.model_dump()
        assert data["provenance"]["pipeline_id"] == "pdf_text_v1"
        assert data["tables"][0]["name"] == "Tabla de indicadores"
        assert data["metrics"][0]["name"] == "tasa_exito"
        assert data["warnings"][0]["severity"] == "warning"
        assert data["free_text"] == "Texto extraído del informe."


class TestExtractionPipelineProtocol:

    def test_extraction_pipeline_protocol_is_typing_protocol(self):
        from server.app.modules.redaccion.pipelines.contracts import ExtractionPipeline

        assert issubclass(ExtractionPipeline, typing.Protocol) or (
            hasattr(ExtractionPipeline, "__protocol_attrs__")
            or getattr(ExtractionPipeline, "_is_protocol", False)
        )

    def test_extraction_pipeline_protocol_has_required_members(self):
        from server.app.modules.redaccion.pipelines.contracts import ExtractionPipeline

        attrs = getattr(ExtractionPipeline, "__protocol_attrs__", set())
        assert "pipeline_id" in attrs
        assert "extract" in attrs
        assert "supports" in attrs

    def test_concrete_class_satisfies_protocol(self):
        from server.app.modules.redaccion.pipelines.contracts import (
            ExtractionInput,
            ExtractionPipeline,
            ExtractionProvenance,
            ExtractionResult,
        )

        class StubPipeline:
            pipeline_id = "stub_v1"

            def extract(self, inp: ExtractionInput) -> ExtractionResult:
                prov = ExtractionProvenance(
                    pipeline_id=self.pipeline_id,
                    source_ref=inp.file_ref.key if inp.file_ref else "",
                    extracted_at=datetime.now(timezone.utc),
                )
                return ExtractionResult(provenance=prov)

            def supports(self, source_kind: str) -> bool:
                return source_kind == "manual"

        stub = StubPipeline()
        assert isinstance(stub, ExtractionPipeline)

"""ExcelExtractionPipeline — extracción determinista desde .xlsx/.xls (9R.5.2)."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from server.app.modules.redaccion.pipelines.contracts import (
    ExtractionInput,
    ExtractionProvenance,
    ExtractionResult,
    ExtractionWarning,
    ExtractedTable,
)


class ExcelExtractionPipeline:
    """Lee hojas de cálculo con pandas + openpyxl y devuelve ExtractedTable."""

    pipeline_id = "excel_pipeline_v1"

    def supports(self, source_kind: str) -> bool:
        return source_kind == "excel"

    def extract(self, inp: ExtractionInput) -> ExtractionResult:
        if inp.file_ref is None:
            raise ValueError("ExcelExtractionPipeline requiere file_ref en ExtractionInput.")

        file_path = Path(inp.file_ref.bucket) / inp.file_ref.key
        sheet = inp.options.get("sheet", 0)
        header_row = inp.options.get("header_row", 0)
        required_columns: list[str] = inp.options.get("required_columns", [])

        df = pd.read_excel(file_path, sheet_name=sheet, header=header_row, engine="openpyxl")

        warnings: list[ExtractionWarning] = []
        for col in required_columns:
            if col not in df.columns:
                warnings.append(
                    ExtractionWarning(
                        code="MISSING_COLUMN",
                        message=f"Columna requerida '{col}' no encontrada.",
                        severity="warning",
                    )
                )

        table = ExtractedTable(
            name=str(sheet),
            headers=[str(c) for c in df.columns],
            rows=[[str(v) for v in row] for row in df.itertuples(index=False)],
        )

        provenance = ExtractionProvenance(
            pipeline_id=self.pipeline_id,
            source_ref=str(inp.file_ref),
            extracted_at=datetime.now(timezone.utc),
            column_mapping={
                "_sheet": str(sheet),
                "_header_row": str(header_row),
            },
        )

        return ExtractionResult(
            tables=[table],
            warnings=warnings,
            provenance=provenance,
        )

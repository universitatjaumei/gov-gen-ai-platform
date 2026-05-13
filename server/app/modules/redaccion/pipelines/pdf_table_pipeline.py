"""PDFTableExtractionPipeline — extracción de tablas de PDFs con camelot (9R.5.3).

Estrategia: lattice (bordes dibujados, requiere Ghostscript) → stream (alineación de
texto, sin Ghostscript). En entornos sin Ghostscript, lattice falla silenciosamente
y se usa stream como fallback.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from server.app.modules.redaccion.pipelines.contracts import (
    ExtractionInput,
    ExtractionProvenance,
    ExtractionResult,
    ExtractionWarning,
    ExtractedTable,
)


class PDFTableExtractionPipeline:
    """Extrae tablas de PDFs usando camelot (lattice → stream)."""

    pipeline_id = "pdf_table_pipeline_v1"

    def supports(self, source_kind: str) -> bool:
        return source_kind == "pdf_table"

    def extract(self, inp: ExtractionInput) -> ExtractionResult:
        if inp.file_ref is None:
            raise ValueError("PDFTableExtractionPipeline requiere file_ref en ExtractionInput.")

        import camelot  # noqa: PLC0415

        file_path = str(Path(inp.file_ref.bucket) / inp.file_ref.key)
        pages = str(inp.options.get("pages", "1"))

        raw_tables = _read_tables(camelot, file_path, pages)

        warnings: list[ExtractionWarning] = []
        extracted: list[ExtractedTable] = []

        if raw_tables is not None and raw_tables.n > 0:
            for i, tbl in enumerate(raw_tables):
                df = tbl.df
                # Requiere al menos 2 columnas para considerarse tabla real;
                # las detecciones de 1 columna son falsos positivos de texto plano.
                if df.empty or df.shape[1] < 2:
                    continue
                headers = [str(v) for v in df.iloc[0].tolist()]
                rows = [
                    [str(v) for v in row]
                    for row in df.iloc[1:].itertuples(index=False)
                ]
                extracted.append(
                    ExtractedTable(
                        name=f"table_{i + 1}",
                        headers=headers,
                        rows=rows,
                        source_page=tbl.page,
                    )
                )

        if not extracted:
            warnings.append(
                ExtractionWarning(
                    code="NO_TABLES_FOUND",
                    message="No se detectaron tablas en el PDF.",
                    severity="warning",
                )
            )

        page_list = (
            sorted({t.page for t in raw_tables})
            if raw_tables and raw_tables.n > 0
            else None
        )
        provenance = ExtractionProvenance(
            pipeline_id=self.pipeline_id,
            source_ref=str(inp.file_ref),
            extracted_at=datetime.now(timezone.utc),
            pages=page_list,
        )

        return ExtractionResult(
            tables=extracted,
            warnings=warnings,
            provenance=provenance,
        )


def _read_tables(camelot, path: str, pages: str):
    """Intenta lattice (Ghostscript); si falla, usa stream (alineación de texto)."""
    try:
        result = camelot.read_pdf(path, flavor="lattice", pages=pages)
        if result.n > 0:
            return result
    except Exception:
        pass
    try:
        return camelot.read_pdf(path, flavor="stream", pages=pages)
    except Exception:
        return None

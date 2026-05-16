"""PDFTextExtractionPipeline — extracción de texto de PDFs digitales con Docling (9R.5.2 / 9R.5.9).

Usa Docling sin OCR: detecta PDFs sin capa de texto (escaneados o imagen)
emitiendo NON_EXTRACTABLE_PDF. Para PDFs escaneados con OCR, usar en el
futuro un pipeline específico (PDFOCRExtractionPipeline).

9R.5.9: ahora produce ExtractedDocument con páginas ricas (bbox por tabla y celda)
y heurística extraction_strategy (text_linear | complex_tables).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from server.app.modules.redaccion.pipelines.contracts import (
    ExtractedCell,
    ExtractedDocument,
    ExtractedPage,
    ExtractedTableRich,
    ExtractionInput,
    ExtractionProvenance,
    ExtractionResult,
    ExtractionWarning,
)


class PDFTextExtractionPipeline:
    """Extrae texto de PDFs con capa de texto usando Docling (sin OCR).

    9R.5.9: produce un ExtractedDocument con tablas ricas (bbox) y
    heurística extraction_strategy para orientar al AIAssistDraftNode.
    """

    pipeline_id = "pdf_text_pipeline_v1"

    def __init__(self) -> None:
        opts = PdfPipelineOptions()
        opts.do_ocr = False
        opts.do_table_structure = True
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
        doc = conv.document

        num_pages: int = doc.num_pages()
        full_markdown: str = doc.export_to_markdown()

        # Build per-page and rich-table structures
        pages, all_rich_tables = self._build_pages(doc, num_pages)

        # Heuristic: complex_tables if ≥3 tables or table char / total > 0.5
        total_table_chars = sum(len(h) for tbl in all_rich_tables for h in tbl.headers) + sum(
            len(cell.text)
            for tbl in all_rich_tables
            for row in tbl.rows
            for cell in row
        )
        total_chars = max(len(full_markdown), 1)
        is_complex = len(all_rich_tables) >= 3 or (total_table_chars / total_chars) > 0.5
        strategy = "complex_tables" if is_complex else "text_linear"

        document = ExtractedDocument(
            pages=pages,
            markdown=full_markdown,
            extraction_strategy=strategy,
        )

        warnings: list[ExtractionWarning] = []
        if not full_markdown.strip():
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
            free_text=full_markdown.strip() or None,
            warnings=warnings,
            provenance=provenance,
            document=document,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_pages(
        self,
        doc: Any,
        num_pages: int,
    ) -> tuple[list[ExtractedPage], list[ExtractedTableRich]]:
        all_rich_tables: list[ExtractedTableRich] = []
        pages: list[ExtractedPage] = []

        for page_no in range(1, num_pages + 1):
            page_tables: list[ExtractedTableRich] = []

            for tbl_idx, table_item in enumerate(doc.tables):
                prov_list = getattr(table_item, "prov", None) or []
                if not prov_list:
                    continue
                prov = prov_list[0]
                if getattr(prov, "page_no", None) != page_no:
                    continue

                tbl_bbox = self._extract_bbox(prov)
                grid = getattr(getattr(table_item, "data", None), "grid", []) or []
                headers, rich_rows = self._parse_grid(grid)

                rich_tbl = ExtractedTableRich(
                    name=f"table_{tbl_idx + 1}",
                    headers=headers,
                    rows=rich_rows,
                    source_page=page_no,
                    bbox=tbl_bbox,
                )
                page_tables.append(rich_tbl)
                all_rich_tables.append(rich_tbl)

            page_md = self._page_markdown(doc, page_no)
            pages.append(ExtractedPage(
                page_num=page_no,
                markdown=page_md,
                tables=page_tables,
            ))

        return pages, all_rich_tables

    @staticmethod
    def _extract_bbox(prov: Any) -> tuple[float, float, float, float] | None:
        bbox_obj = getattr(prov, "bbox", None)
        if bbox_obj is None:
            return None
        try:
            return (
                float(bbox_obj.l),
                float(bbox_obj.t),
                float(bbox_obj.r),
                float(bbox_obj.b),
            )
        except (AttributeError, TypeError, ValueError):
            return None

    @staticmethod
    def _parse_grid(
        grid: list[list[Any]],
    ) -> tuple[list[str], list[list[ExtractedCell]]]:
        headers: list[str] = []
        rich_rows: list[list[ExtractedCell]] = []

        for row_idx, row in enumerate(grid):
            cells_in_row: list[ExtractedCell] = []
            for cell in row:
                cell_text = str(getattr(cell, "text", "") or "")
                bbox_obj = getattr(cell, "bbox", None)
                cell_bbox: tuple[float, float, float, float] | None = None
                if bbox_obj is not None:
                    try:
                        cell_bbox = (
                            float(bbox_obj.l),
                            float(bbox_obj.t),
                            float(bbox_obj.r),
                            float(bbox_obj.b),
                        )
                    except (AttributeError, TypeError, ValueError):
                        cell_bbox = None
                col_span = int(getattr(cell, "col_span", None) or 1)
                row_span = int(getattr(cell, "row_span", None) or 1)
                cells_in_row.append(ExtractedCell(
                    text=cell_text,
                    bbox=cell_bbox,
                    col_span=col_span,
                    row_span=row_span,
                ))
            if row_idx == 0:
                headers = [c.text for c in cells_in_row]
            else:
                rich_rows.append(cells_in_row)

        return headers, rich_rows

    @staticmethod
    def _page_markdown(doc: Any, page_no: int) -> str:
        try:
            return doc.export_to_markdown(from_page=page_no, to_page=page_no)
        except TypeError:
            pass
        # Fallback: single-page doc → return full markdown; multi-page → empty
        try:
            total = doc.num_pages()
            return doc.export_to_markdown() if total == 1 else ""
        except Exception:
            return ""

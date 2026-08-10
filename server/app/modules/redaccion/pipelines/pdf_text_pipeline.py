"""PDFTextExtractionPipeline — extracción de texto de PDFs digitales (9R.5.2 / 9R.5.9).

Deploy: edge.

**EXT.2**: usa `pdfplumber`. Antes usaba Docling **sin OCR**, así que el alcance no cambia
—PDFs con capa de texto— y el contrato de salida tampoco: mismo `ExtractionResult`, mismas
páginas, mismas tablas con bbox y la misma heurística `extraction_strategy`. Lo que se va son
los modelos de layout, que en una máquina sin GPU eran la parte cara del arranque.

Un PDF escaneado sigue produciendo `NON_EXTRACTABLE_PDF`, y **avisa en vez de fallar**: un
informe puede tener otras fuentes, y perder la ejecución entera por una sola sería peor que
señalar cuál falló. La vía que sí falla en alto es el contexto temporal del usuario, que
ingiere el documento y no tiene nada más de donde tirar.

9R.5.9: produce ExtractedDocument con páginas ricas (bbox por tabla y celda) y heurística
extraction_strategy (text_linear | complex_tables).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from server.app.core.pdf_text import extraer_paginas, hay_capa_de_texto
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
    """Extrae texto y tablas de PDFs con capa de texto usando pdfplumber."""

    pipeline_id = "pdf_text_pipeline_v1"

    def supports(self, source_kind: str) -> bool:
        return source_kind == "pdf_text"

    def extract(self, inp: ExtractionInput) -> ExtractionResult:
        if inp.file_ref is None:
            raise ValueError("PDFTextExtractionPipeline requiere file_ref en ExtractionInput.")

        file_path = Path(inp.file_ref.bucket) / inp.file_ref.key
        datos = file_path.read_bytes()

        textos = extraer_paginas(datos)
        pages, all_rich_tables = self._build_pages(datos, textos)
        num_pages = len(textos)

        full_markdown = "\n\n".join(p.markdown for p in pages if p.markdown.strip())

        # Heurística: complex_tables si ≥3 tablas o si el texto de tabla domina el documento.
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
        if not hay_capa_de_texto(textos):
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
        self, datos: bytes, textos: list[str]
    ) -> tuple[list[ExtractedPage], list[ExtractedTableRich]]:
        """Una pasada por el PDF: texto y tablas de cada página.

        `pdfplumber` da la bbox de la tabla y la de cada celda, que es lo que
        `AIAssistDraftNode` usa para situar un dato en el original.
        """
        import io

        import pdfplumber

        all_rich_tables: list[ExtractedTableRich] = []
        pages: list[ExtractedPage] = []

        with pdfplumber.open(io.BytesIO(datos)) as pdf:
            for indice, pagina in enumerate(pdf.pages):
                page_no = indice + 1
                page_tables: list[ExtractedTableRich] = []

                for tbl_idx, tabla in enumerate(pagina.find_tables()):
                    rica = self._tabla_rica(tabla, page_no, tbl_idx)
                    if rica is None:
                        continue
                    page_tables.append(rica)
                    all_rich_tables.append(rica)

                texto = textos[indice] if indice < len(textos) else ""
                pages.append(
                    ExtractedPage(
                        page_num=page_no,
                        markdown=texto.strip(),
                        tables=page_tables,
                    )
                )

        return pages, all_rich_tables

    @staticmethod
    def _tabla_rica(tabla: Any, page_no: int, tbl_idx: int) -> ExtractedTableRich | None:
        filas = tabla.extract() or []
        if not filas:
            return None

        # La primera fila hace de cabecera, que es la convención con la que se venía
        # trabajando; `pdfplumber` no distingue cabeceras por sí solo.
        cabeceras = [str(c or "") for c in filas[0]]

        celdas_por_fila: list[list[ExtractedCell]] = []
        # `tabla.rows` trae la geometría; `tabla.extract()` el texto. Se recorren en
        # paralelo para no perder la bbox de cada celda.
        geometria = list(getattr(tabla, "rows", []) or [])
        for indice_fila, fila in enumerate(filas[1:], start=1):
            bboxes = []
            if indice_fila < len(geometria):
                bboxes = list(getattr(geometria[indice_fila], "cells", []) or [])
            celdas: list[ExtractedCell] = []
            for indice_col, valor in enumerate(fila):
                bbox = None
                if indice_col < len(bboxes) and bboxes[indice_col]:
                    try:
                        izq, arriba, der, abajo = bboxes[indice_col]
                        bbox = (float(izq), float(arriba), float(der), float(abajo))
                    except (TypeError, ValueError):
                        bbox = None
                celdas.append(ExtractedCell(text=str(valor or ""), bbox=bbox))
            celdas_por_fila.append(celdas)

        try:
            izq, arriba, der, abajo = tabla.bbox
            bbox_tabla = (float(izq), float(arriba), float(der), float(abajo))
        except (AttributeError, TypeError, ValueError):
            bbox_tabla = None

        return ExtractedTableRich(
            name=f"table_{tbl_idx + 1}",
            headers=cabeceras,
            rows=celdas_por_fila,
            source_page=page_no,
            bbox=bbox_tabla,
        )

"""Exportación del WebQualityReport a DOCX y PDF (9Q.8).

Deploy: edge.

Reutiliza el patrón python-docx de ExportService. Para PDF, se intenta
conversión con LibreOffice; si no está disponible, se devuelve el DOCX
con un aviso en los headers (degradación documentada).
"""
from __future__ import annotations

import io
from typing import Any

from server.app.modules.curation.report_contracts import WebQualityReport


class WebQualityReportExporter:
    """Exporta un WebQualityReport a bytes DOCX o PDF."""

    def __init__(self, storage: Any = None) -> None:
        self._storage = storage

    async def to_docx(self, report: WebQualityReport) -> bytes:
        """Genera un DOCX estructurado con los hallazgos del informe."""
        from docx import Document

        doc = Document()

        # Cabecera
        doc.add_heading(f"Informe de Auditoría Web — {report.site_name}", level=1)
        doc.add_paragraph(
            f"Fecha de generación: {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}"
        )
        doc.add_paragraph(f"Sitio ID: {report.site_id}")
        doc.add_paragraph("")

        # Resumen
        doc.add_heading("Resumen de hallazgos", level=2)
        if report.totals_by_type:
            for ft, count in sorted(report.totals_by_type.items()):
                doc.add_paragraph(f"• {ft}: {count}", style="List Bullet")
        else:
            doc.add_paragraph("No se encontraron hallazgos activos.")

        # Secciones por tipo
        for section in report.sections:
            doc.add_heading(f"{section.finding_type.upper()} ({len(section.findings)})", level=2)
            doc.add_paragraph(f"Recomendación: {section.recommendation}")

            for fv in section.findings:
                para = doc.add_paragraph(style="List Bullet")
                para.add_run(f"[{fv.severity.upper()}] ").bold = True
                para.add_run(fv.page_url or "—")
                if fv.related_page_url:
                    para.add_run(f" → {fv.related_page_url}")
                if fv.explanation:
                    doc.add_paragraph(f"    {fv.explanation}")

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    async def to_pdf(self, report: WebQualityReport) -> bytes:
        """Intenta convertir el DOCX a PDF vía LibreOffice.

        Si LibreOffice no está disponible, devuelve el DOCX como fallback
        (el caller debe inspeccionar el Content-Type de la respuesta).
        """
        import subprocess
        import tempfile
        import os

        docx_bytes = await self.to_docx(report)

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                docx_path = os.path.join(tmpdir, "report.docx")
                pdf_path = os.path.join(tmpdir, "report.pdf")

                with open(docx_path, "wb") as fh:
                    fh.write(docx_bytes)

                result = subprocess.run(
                    [
                        "libreoffice",
                        "--headless",
                        "--convert-to", "pdf",
                        "--outdir", tmpdir,
                        docx_path,
                    ],
                    capture_output=True,
                    timeout=30,
                )
                if result.returncode == 0 and os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as fh:
                        return fh.read()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Fallback: devuelve DOCX (degradación documentada — el router añade el header)
        return docx_bytes

import fitz
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class PDFQualityReport:
    """Reporte de calidad de texto en PDF"""
    needs_ocr: bool
    avg_chars_per_page: float
    total_pages: int
    diagnosis: str
    quality_score: float  # 0.0 (malo) - 1.0 (excelente)

def analyze_pdf_quality(
    pdf_path: str,
    min_chars_threshold: int = 50
) -> PDFQualityReport:
    """
    Analiza la calidad del texto embebido en un PDF.
    
    Criterios:
    - Promedio de caracteres/página >= min_chars_threshold → OK
    - Promedio < threshold → Requiere OCR
    
    Args:
        pdf_path: Ruta al archivo PDF
        min_chars_threshold: Mínimo de caracteres por página
    
    Returns:
        PDFQualityReport con diagnóstico y recomendación
    """
    path = Path(pdf_path)
    
    if not path.exists():
        return PDFQualityReport(
            needs_ocr=True,
            avg_chars_per_page=0.0,
            total_pages=0,
            diagnosis="Archivo no encontrado",
            quality_score=0.0
        )
    
    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        total_chars = 0
        
        for page in doc:
            text = page.get_text()
            # Contar solo caracteres alfanuméricos (ignorar espacios/saltos)
            chars = len([c for c in text if c.isalnum()])
            total_chars += chars
        
        doc.close()
        
        avg_chars = total_chars / total_pages if total_pages > 0 else 0
        
        # Calcular score de calidad (0-1)
        quality_score = min(avg_chars / min_chars_threshold, 1.0)
        
        needs_ocr = avg_chars < min_chars_threshold
        
        if needs_ocr:
            diagnosis = (
                f"Densidad de texto muy baja ({avg_chars:.1f} chars/pág). "
                f"Probable documento escaneado. Se recomienda OCR o sustituir por PDF con texto."
            )
        else:
            diagnosis = (
                f"Densidad de texto suficiente ({avg_chars:.1f} chars/pág). "
                f"Documento apto para extracción directa."
            )
        
        return PDFQualityReport(
            needs_ocr=needs_ocr,
            avg_chars_per_page=avg_chars,
            total_pages=total_pages,
            diagnosis=diagnosis,
            quality_score=quality_score
        )
    
    except Exception as e:
        return PDFQualityReport(
            needs_ocr=True,
            avg_chars_per_page=0.0,
            total_pages=0,
            diagnosis=f"Error al analizar PDF: {str(e)}",
            quality_score=0.0
        )

def detect_pdf_text_content(pdf_path: str) -> bool:
    """
    Función simple de detección (legacy compatibility).
    
    Returns:
        True si tiene texto suficiente, False si necesita OCR
    """
    report = analyze_pdf_quality(pdf_path)
    return not report.needs_ocr

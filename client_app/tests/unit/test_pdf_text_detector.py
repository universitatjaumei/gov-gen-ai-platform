import pytest
import fitz
from pathlib import Path
from app.modules.extraction.pdf_text_detector import (
    analyze_pdf_quality,
    PDFQualityReport
)

def test_detects_low_density_pdf(tmp_path: Path):
    """Detectar PDF con muy poco texto (marca de agua o error)"""
    # Crear PDF dummy con solo 1 carácter útil
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((100, 100), "A")  # Solo 1 char
    
    path = tmp_path / "bad.pdf"
    doc.save(path)
    doc.close()
    
    report = analyze_pdf_quality(str(path), min_chars_threshold=50)
    
    assert report.needs_ocr is True
    assert report.avg_chars_per_page < 50
    assert "muy baja" in report.diagnosis.lower()

def test_accepts_good_pdf(tmp_path: Path):
    """Aceptar PDF con texto suficiente"""
    doc = fitz.open()
    page = doc.new_page()
    
    # Insertar texto decente (>50 chars/página)
    text = "Este es un documento con suficiente texto para ser procesado correctamente. "
    text = text * 3  # >150 chars
    page.insert_text((100, 100), text)
    
    path = tmp_path / "good.pdf"
    doc.save(path)
    doc.close()
    
    report = analyze_pdf_quality(str(path), min_chars_threshold=50)
    
    assert report.needs_ocr is False
    assert report.avg_chars_per_page >= 50
    assert "suficiente" in report.diagnosis.lower()

def test_handles_nonexistent_file():
    """Manejar archivo inexistente sin crashear"""
    report = analyze_pdf_quality("nonexistent_12345.pdf")
    
    assert report.needs_ocr is True  # Por defecto asume que necesita OCR
    assert "no encontrado" in report.diagnosis.lower()


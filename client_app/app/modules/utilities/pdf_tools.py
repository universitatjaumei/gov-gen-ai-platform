"""
Módulo de herramientas PDF usando PyMuPDF (fitz).
Operaciones: merge, split, optimize.
"""
import os
import fitz
from pathlib import Path
from typing import List, Dict, Tuple, Optional


def get_size_mb(path: str) -> float:
    """Retorna tamaño de archivo en MB."""
    return os.path.getsize(path) / (1024 * 1024)


def calculate_savings(original_size: float, final_size: float) -> Dict:
    """
    Calcula estadísticas de ahorro de espacio.

    Args:
        original_size: Tamaño original en MB
        final_size: Tamaño final en MB

    Returns:
        Dict con original_mb, final_mb, saved_mb, percentage
    """
    saved = original_size - final_size
    percentage = (saved / original_size * 100) if original_size > 0 else 0
    return {
        "original_mb": round(original_size, 2),
        "final_mb": round(final_size, 2),
        "saved_mb": round(saved, 2),
        "percentage": round(percentage, 1)
    }


def validate_pdf(file_path: str) -> Tuple[bool, str]:
    """
    Valida que el archivo es un PDF válido.

    Args:
        file_path: Ruta al archivo

    Returns:
        Tupla (es_valido, mensaje)
    """
    try:
        if not os.path.exists(file_path):
            return False, "El archivo no existe"

        doc = fitz.open(file_path)
        if doc.page_count == 0:
            doc.close()
            return False, "El PDF no tiene páginas"
        doc.close()
        return True, "OK"
    except Exception as e:
        return False, f"Archivo no válido: {str(e)}"


def get_pdf_info(file_path: str) -> Dict:
    """
    Obtiene información básica de un PDF.

    Args:
        file_path: Ruta al archivo PDF

    Returns:
        Dict con path, name, pages, size_mb
    """
    doc = fitz.open(file_path)
    info = {
        "path": file_path,
        "name": Path(file_path).name,
        "pages": len(doc),
        "size_mb": round(get_size_mb(file_path), 2)
    }
    doc.close()
    return info


def merge_pdfs(
    input_files: List[str],
    output_path: str,
    optimize: bool = True
) -> Dict:
    """
    Une múltiples PDFs en uno solo.

    Args:
        input_files: Lista de rutas de PDFs en orden deseado
        output_path: Ruta del archivo de salida
        optimize: Si True, aplica garbage=3 para optimizar

    Returns:
        Dict con saved_path, original_total_mb, final_mb, savings
    """
    doc_out = fitz.open()
    total_original_size = 0

    for pdf_path in input_files:
        total_original_size += get_size_mb(pdf_path)
        doc_in = fitz.open(pdf_path)
        doc_out.insert_pdf(doc_in)
        doc_in.close()

    # Guardar con o sin optimización
    if optimize:
        doc_out.save(output_path, garbage=3, deflate=True, clean=True)
    else:
        doc_out.save(output_path)
    doc_out.close()

    final_size = get_size_mb(output_path)

    return {
        "saved_path": output_path,
        "original_total_mb": round(total_original_size, 2),
        "final_mb": round(final_size, 2),
        "savings": calculate_savings(total_original_size, final_size) if optimize else None
    }


def split_by_ranges(
    input_file: str,
    ranges: List[Tuple[int, int]],
    output_dir: str,
    optimize: bool = True
) -> List[Dict]:
    """
    Divide PDF por rangos. Cada rango genera un archivo independiente.

    Args:
        input_file: Ruta del PDF original
        ranges: Lista de tuplas (inicio, fin) con páginas 1-indexed
        output_dir: Directorio de salida
        optimize: Si True, aplica garbage=3

    Returns:
        Lista de dicts con información de cada archivo generado
    """
    doc = fitz.open(input_file)
    base_name = Path(input_file).stem
    results = []

    for start, end in ranges:
        # Validar rango
        if start < 1 or end > len(doc) or start > end:
            continue

        doc_out = fitz.open()
        # fitz usa 0-indexed, convertir desde 1-indexed
        doc_out.insert_pdf(doc, from_page=start-1, to_page=end-1)

        output_name = f"{base_name}_p{start}-{end}.pdf"
        output_path = str(Path(output_dir) / output_name)

        if optimize:
            doc_out.save(output_path, garbage=3, deflate=True, clean=True)
        else:
            doc_out.save(output_path)
        doc_out.close()

        results.append({
            "saved_path": output_path,
            "filename": output_name,
            "range": f"{start}-{end}",
            "pages": end - start + 1,
            "size_mb": round(get_size_mb(output_path), 2)
        })

    doc.close()
    return results


def split_specific_pages(
    input_file: str,
    pages: List[int],
    output_dir: str,
    optimize: bool = True
) -> Dict:
    """
    Extrae páginas específicas en un solo PDF.

    Args:
        input_file: Ruta del PDF original
        pages: Lista de números de página 1-indexed (ej: [1, 5, 8, 12])
        output_dir: Directorio de salida
        optimize: Si True, aplica garbage=3

    Returns:
        Dict con información del archivo generado
    """
    doc = fitz.open(input_file)
    doc_out = fitz.open()
    base_name = Path(input_file).stem

    # Filtrar páginas válidas y ordenar
    valid_pages = sorted([p for p in pages if 1 <= p <= len(doc)])

    for page_num in valid_pages:
        doc_out.insert_pdf(doc, from_page=page_num-1, to_page=page_num-1)

    # Generar nombre descriptivo
    if len(valid_pages) <= 5:
        pages_str = "-".join(map(str, valid_pages))
    else:
        pages_str = f"{valid_pages[0]}-etc-{valid_pages[-1]}"

    output_name = f"{base_name}_pages_{pages_str}.pdf"
    output_path = str(Path(output_dir) / output_name)

    if optimize:
        doc_out.save(output_path, garbage=3, deflate=True, clean=True)
    else:
        doc_out.save(output_path)

    doc.close()
    doc_out.close()

    return {
        "saved_path": output_path,
        "filename": output_name,
        "pages_extracted": len(valid_pages),
        "size_mb": round(get_size_mb(output_path), 2)
    }


def split_all_pages(
    input_file: str,
    output_dir: str,
    optimize: bool = True
) -> List[Dict]:
    """
    Divide un PDF en un archivo por cada página.

    Args:
        input_file: Ruta del PDF original
        output_dir: Directorio de salida
        optimize: Si True, aplica garbage=3

    Returns:
        Lista de dicts con información de cada archivo generado
    """
    doc = fitz.open(input_file)
    base_name = Path(input_file).stem
    results = []
    total_pages = len(doc)

    for i in range(total_pages):
        doc_out = fitz.open()
        doc_out.insert_pdf(doc, from_page=i, to_page=i)

        # Padding para ordenación correcta (001, 002, etc.)
        padding = len(str(total_pages))
        output_name = f"{base_name}_page_{str(i+1).zfill(padding)}.pdf"
        output_path = str(Path(output_dir) / output_name)

        if optimize:
            doc_out.save(output_path, garbage=3, deflate=True, clean=True)
        else:
            doc_out.save(output_path)
        doc_out.close()

        results.append({
            "saved_path": output_path,
            "filename": output_name,
            "page": i + 1,
            "size_mb": round(get_size_mb(output_path), 2)
        })

    doc.close()
    return results


def optimize_pdf(
    input_file: str,
    output_path: str,
    level: int = 3
) -> Dict:
    """
    Optimiza un PDF con el nivel especificado.

    Args:
        input_file: Ruta del PDF original
        output_path: Ruta del archivo de salida
        level: Nivel de optimización (1-4)
            1: Limpieza básica (garbage=1)
            2: Limpieza moderada (garbage=2, deflate)
            3: Equilibrado (garbage=3, deflate, clean) - Recomendado
            4: Agresivo (garbage=4, deflate, clean, linear)

    Returns:
        Dict con estadísticas de ahorro
    """
    original_size = get_size_mb(input_file)
    doc = fitz.open(input_file)

    save_params = {
        1: {"garbage": 1},
        2: {"garbage": 2, "deflate": True},
        3: {"garbage": 3, "deflate": True, "clean": True},
        4: {"garbage": 4, "deflate": True, "clean": True, "linear": True}
    }.get(level, {"garbage": 3, "deflate": True, "clean": True})

    doc.save(output_path, **save_params)
    doc.close()

    final_size = get_size_mb(output_path)
    savings = calculate_savings(original_size, final_size)

    return {
        "saved_path": output_path,
        "filename": Path(output_path).name,
        "level": level,
        **savings
    }

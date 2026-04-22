import fitz  # PyMuPDF
import pdfplumber
import pandas as pd
import concurrent.futures

def extraer_texto_pyMuPDF(ruta_pdf):
    """Extrae texto usando PyMuPDF (fitz) añadiendo contexto visual de tablas."""
    texto_pdf = ""
    es_extenso = False
    try:
        with fitz.open(ruta_pdf) as doc:
            for i, page in enumerate(doc):
                content = page.get_text("text")
                if content.strip():
                    import os
                    import sys
                    # PyMuPDF C-level errors write directly to fd 2
                    try:
                        null_fd = os.open(os.devnull, os.O_WRONLY)
                        save_fd = os.dup(2)
                        os.dup2(null_fd, 2)
                        
                        fitz.TOOLS.mupdf_display_errors(False)
                        tabs = page.find_tables()
                        fitz.TOOLS.mupdf_display_errors(True)
                        
                        if tabs and tabs.tables:
                            content += "\n<tablas_detectadas_fitz>\n"
                            for idx, tab in enumerate(tabs.tables):
                                df_tab = tab.to_pandas()
                                content += f"\nTabla {idx+1}:\n{df_tab.to_string(index=False)}\n"
                            content += "</tablas_detectadas_fitz>\n"
                    except Exception:
                        pass
                    finally:
                        try:
                            os.dup2(save_fd, 2)
                            os.close(save_fd)
                            os.close(null_fd)
                        except Exception:
                            pass
                if content:
                    texto_pdf += f"--- PÁGINA {i+1} ---\n{content}\n\n"
        if len(texto_pdf) > 120000:
            es_extenso = True
    except Exception as e:
        raise RuntimeError(f"Error al leer el PDF con PyMuPDF: {e}")
    return texto_pdf, es_extenso

def extraer_texto_pdfplumber(ruta_pdf):
    """Extrae texto y tablas detalladas usando pdfplumber con formato limpio."""
    texto_pdf = ""
    try:
        with pdfplumber.open(ruta_pdf) as pdf:
            for i, page in enumerate(pdf.pages):
                content = page.extract_text() or ""
                tables = page.extract_tables()
                if tables:
                    content += "\n<tablas_estructuradas_pdfplumber>\n"
                    for idx, table in enumerate(tables):
                        content += f"\nTabla {idx+1}:\n"
                        try:
                            rows_str = [" | ".join([str(cell).replace('\n', ' ') if cell is not None else "" for cell in row]) for row in table]
                            content += "\n".join(rows_str) + "\n"
                        except:
                            pass
                    content += "</tablas_estructuradas_pdfplumber>\n"
                if content:
                    texto_pdf += f"--- PÁGINA {i+1} ---\n{content}\n\n"
    except Exception as e:
        raise RuntimeError(f"Error al leer el PDF con pdfplumber: {e}")
    return texto_pdf

def extraer_texto_dual(ruta_pdf):
    """
    Ejecuta ambos motores de extracción de forma concurrente.
    """
    def safe_pymupdf(ruta):
        try: return extraer_texto_pyMuPDF(ruta)
        except Exception as e: return f"[ERROR CRÍTICO FITZ: {str(e)}]", False

    def safe_pdfplumber(ruta):
        try: return extraer_texto_pdfplumber(ruta)
        except Exception as e: return f"[ERROR CRÍTICO PDFPLUMBER: {str(e)}]"

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_pymupdf = executor.submit(safe_pymupdf, ruta_pdf)
        future_pdfplumber = executor.submit(safe_pdfplumber, ruta_pdf)
        
        texto_a, es_extenso = future_pymupdf.result()
        texto_b = future_pdfplumber.result()
        
    return texto_a, texto_b, es_extenso

def obtener_texto_completo(ruta_pdf):
    """Compatibilidad: devuelve PyMuPDF por defecto."""
    texto, _ = extraer_texto_pyMuPDF(ruta_pdf)
    return texto

def extraer_texto_pymupdf_por_pag(ruta_pdf: str) -> list[str]:
    """
    Extrae el texto de un PDF página por página usando PyMuPDF (fitz).
    Retorna una lista donde cada elemento es el texto crudo de una página.
    Útil para navegaciones precisas o búsquedas acotadas (page ±1).
    """
    out = []
    try:
        with fitz.open(ruta_pdf) as doc:
            for page in doc:
                out.append(page.get_text())
    except Exception as e:
        print(f"[Reader] Error leyendo páginas por separado: {e}")
        return []
    return out

# app/core/pdf_reader.py
from __future__ import annotations
import asyncio
import re
from typing import Tuple, List, Dict, Any, Optional

# PyMuPDF
import fitz # pip install pymupdf

class PdfReaderDual:
    """
    Reader de PDFs basado en PyMuPDF (FitZ) que expone:
    - read_dual(doc_path): texto lineal + texto layout-aware del documento completo
    - read_page_dual(doc_path, page): texto lineal + layout de una página 1-based
    - get_pages_and_count(doc_path): lista [1..N], N
    Todas las funciones son async (envuelven IO/bloqueo con asyncio.to_thread)
    """

    def __init__(self,
                 max_chars_lineal: int = 16000,
                 max_chars_layout: int = 16000,
                 layout_join: str = " ",
                 preserve_order: bool = True):
        """
        Inicializa el lector de PDF con límites de extracción para evitar saturar los modelos de lenguaje.

        Args:
            max_chars_lineal: Límite de caracteres para la vista de texto lineal.
            max_chars_layout: Límite de caracteres para la vista de texto layout-aware.
            layout_join: Separador utilizado al concatenar bloques de texto en el layout.
            preserve_order: Si es True, intenta mantener el orden natural de lectura.
        """
        self.max_chars_lineal = max_chars_lineal
        self.max_chars_layout = max_chars_layout
        self.layout_join = layout_join
        self.preserve_order = preserve_order

    # ---------- Público ----------

    async def read_dual(self, doc_path: str) -> Tuple[str, str, Dict[str, Any]]:
        """
        Devuelve (text_lineal, text_layout, meta).
        meta: {'num_pages': N}
        """
        return await asyncio.to_thread(self._read_dual_sync, doc_path)

    async def read_page_dual(self, doc_path: str, page: int) -> Tuple[str, str]:
        """
        Devuelve (text_lineal, text_layout) para una página 1-based.
        """
        return await asyncio.to_thread(self._read_page_dual_sync, doc_path, page)

    async def get_pages_and_count(self, doc_path: str) -> Tuple[List[int], int]:
        """
        Devuelve ([1..N], N)
        """
        return await asyncio.to_thread(self._get_pages_and_count_sync, doc_path)

    async def read_page_kv(self, doc_path: str, page: int) -> List[Dict[str, Any]]:
        """
        Devuelve lista de pares clave-valor en una página (bbox + texto).
        """
        return await asyncio.to_thread(self._read_page_kv_sync, doc_path, page)

    # ---------- Interno (sync) ----------

    def _read_page_kv_sync(self, doc_path: str, page_1based: int) -> List[Dict[str, Any]]:
        """
        Versión síncrona de extracción de pares clave-valor (KV) mediante heurísticas de proximidad.
        """
        if page_1based <= 0:
            raise ValueError("page debe ser 1-based (>=1).")
        with fitz.open(doc_path) as doc:
            if page_1based > doc.page_count:
                raise ValueError(f"page {page_1based} fuera de rango (total={doc.page_count}).")
            page = doc.load_page(page_1based - 1)
            d = _extract_dict(page)
            lines = _lines_from_dict(d)
            kv = _detect_kv_pairs(lines)
            return kv

    def _get_pages_and_count_sync(self, doc_path: str) -> Tuple[List[int], int]:
        """
        Extrae el número total de páginas y genera una lista secuencial.
        """
        with fitz.open(doc_path) as doc:
            n = doc.page_count
            return list(range(1, n + 1)), n

    def _read_dual_sync(self, doc_path: str) -> Tuple[str, str, Dict[str, Any]]:
        """
        Concatena texto lineal y layout de todas las páginas.
        Aplica límites max_chars_* para evitar desbordes de tokens.
        """
        lineal_parts: List[str] = []
        layout_parts: List[str] = []
        with fitz.open(doc_path) as doc:
            n = doc.page_count
            for p_idx in range(n):
                page = doc.load_page(p_idx)
                # Texto lineal simple
                txt_lineal = self._extract_lineal(page)
                # Texto layout-aware (bloques ordenados por coordenadas)
                txt_layout = self._extract_layout(page, join=self.layout_join, preserve_order=self.preserve_order)
                lineal_parts.append(txt_lineal)
                layout_parts.append(txt_layout)

        text_a = self._truncate("\n".join(lineal_parts), self.max_chars_lineal)
        text_b = self._truncate("\n".join(layout_parts), self.max_chars_layout)
        meta = {'num_pages': len(lineal_parts)}
        return text_a, text_b, meta

    def _read_page_dual_sync(self, doc_path: str, page_1based: int) -> Tuple[str, str]:
        """
        Extrae texto lineal y layout de una página específica (1-based).
        """
        if page_1based <= 0:
            raise ValueError("page debe ser 1-based (>=1).")
        with fitz.open(doc_path) as doc:
            if page_1based > doc.page_count:
                raise ValueError(f"page {page_1based} fuera de rango (total={doc.page_count}).")
            page = doc.load_page(page_1based - 1)
            txt_lineal = self._extract_lineal(page)
            txt_layout = self._extract_layout(page, join=self.layout_join, preserve_order=self.preserve_order)
            return (self._truncate(txt_lineal, self.max_chars_lineal),
                    self._truncate(txt_layout, self.max_chars_layout))

    # ---------- Helpers de extracción ----------

    def _extract_lineal(self, page: fitz.Page) -> str:
        """
        Vista A: texto lineal (“text”), útil para prompts que no dependen de coordenadas.
        """
        # 'text' conserva saltos básicos; 'textpage'/'rawdict' son más verbosos
        return page.get_text("text") or ""

    def _extract_layout(self, page: fitz.Page, join: str = " ", preserve_order: bool = True) -> str:
        """
        Vista B: texto layout-aware. Toma bloques con coordenadas y reconstruye en orden de lectura.
        'blocks' devuelve una lista de tuplas: (x0,y0,x1,y1,text, block_no, ...)
        """
        blocks = page.get_text("blocks") or []
        # Ordenar por (y0, x0) para lectura natural (top-left → bottom-right)
        if preserve_order:
            blocks = sorted(blocks, key=lambda b: (round(b[1], 2), round(b[0], 2)))
        parts: List[str] = []
        for b in blocks:
            text = (b[4] or "").strip()
            if text:
                parts.append(text)
        # Unir con separador configurable (evita pegados sin espacios)
        out = join.join(parts)
        # Pequeña limpieza
        out = " ".join(out.split()) # normaliza espacios múltiples
        return out

    def _truncate(self, s: str, max_chars: int) -> str:
        """
        Recorta una cadena si excede el número máximo de caracteres permitidos.
        """
        if not s:
            return ""
        if max_chars and len(s) > max_chars:
            return s[:max_chars]
        return s

# ---------- Helpers de extracción KV ----------

def _extract_dict(page: fitz.Page) -> Dict[str, Any]:
    """Vista C: estructura 'dict' con bloques, líneas y spans (texto + bbox)."""
    return page.get_text("dict") or {"blocks": []}

def _lines_from_dict(d: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Aplana el dict a líneas con texto concatenado y bbox promedio.
    Devuelve [{ 'text': '...', 'bbox': (x0,y0,x1,y1) }]
    """
    out = []
    for b in d.get("blocks", []):
        for l in b.get("lines", []):
            spans = l.get("spans", [])
            txt = " ".join(s.get("text","").strip() for s in spans if s.get("text"))
            if not txt.strip():
                continue
            # bbox aproximada: min/max de spans
            xs = [s.get("bbox",[0,0,0,0])[0] for s in spans]
            ys = [s.get("bbox",[0,0,0,0])[1] for s in spans]
            xe = [s.get("bbox",[0,0,0,0])[2] for s in spans]
            ye = [s.get("bbox",[0,0,0,0])[3] for s in spans]
            bbox = (min(xs or [0]), min(ys or [0]), max(xe or [0]), max(ye or [0]))
            out.append({"text": " ".join(txt.split()), "bbox": bbox})
    # Orden top-left → bottom-right
    out.sort(key=lambda ln: (round(ln["bbox"][1], 2), round(ln["bbox"][0], 2)))
    return out

def _detect_kv_pairs(lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detecta parejas clave-valor en líneas contiguas o separadas por ':'.
    Devuelve [{ 'key': '...', 'value': '...', 'key_bbox':(...), 'value_bbox':(...)}]
    """
    kv = []
    # 1) Inline "key: value"
    for ln in lines:
        m = re.match(r'^([\wÁÉÍÓÚÜÑàèìòùç\-\s]+)\s*[:\-–]\s*(.+)', ln["text"])
        if m:
            key = m.group(1).strip()
            val = m.group(2).strip()
            if _is_plausible_key(key) and _is_plausible_value(val):
                kv.append({"key": key, "value": val, "key_bbox": ln["bbox"], "value_bbox": ln["bbox"]})

    # 2) Vecinos verticales (dos líneas): key en ln[i], value en ln[i+1]
    for i in range(len(lines)-1):
        kln, vln = lines[i], lines[i+1]
        if _is_plausible_key(kln["text"]) and _is_plausible_value(vln["text"]):
            # Misma columna: x diferencia pequeña
            same_col = abs(kln["bbox"][0] - vln["bbox"][0]) < 20
            # Distancia vertical razonable
            near = (vln["bbox"][1] - kln["bbox"][3]) < 25
            if same_col and near:
                kv.append({"key": kln["text"].strip(), "value": vln["text"].strip(),
                           "key_bbox": kln["bbox"], "value_bbox": vln["bbox"]})
    return kv

def _is_plausible_key(s: str) -> bool:
    """
    Heurística para determinar si una cadena de texto es probablemente un campo (Key)
    en un par Clave-Valor administrativo.
    """
    # Claves administrativas típicas (ajustable)
    return bool(re.search(r'(referencia|expediente|título|fecha|nif|iban|importe|total|proveedor|concepto|contrato|factura|base|cuota)', s.lower()))

def _is_plausible_value(s: str) -> bool:
    """
    Heurística para determinar si una cadena de texto contiene un valor válido
    (DNI, IBAN, Importe, Fecha, etc.) que acompañe a una clave.
    """
    # Valores comunes: IBAN, NIF, fechas, importes, textos no vacíos
    if re.search(r'\b([A-Z]{2}\d{2}[A-Z0-9]{10,})\b', s): # IBAN aprox
        return True
    if re.search(r'\b([XYZ]?\d{7}[A-Z])\b', s, re.I): # NIF/NIE simplificado
        return True
    if re.search(r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b', s): # fecha dd/mm/yyyy
        return True
    if re.search(r'\b(\d{1,3}(\.\d{3})*(,\d{2})\s?€?)\b', s): # importe EU
        return True
    return len(s.strip()) >= 2

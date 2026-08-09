"""Spider especializado para el catálogo de procedimientos administrativos de la UJI.

Deploy: edge
"""
from dataclasses import dataclass
from typing import Any

from bs4 import BeautifulSoup


@dataclass
class ProcedimientoDoc:
    nombre: str
    codigo: str
    unidad_responsable: str
    plazo: str
    documentacion_requerida: str
    normativa_aplicable: str
    metadata_json: dict[str, Any]


class ProcedimientosSpider:
    """Extrae fichas de procedimientos administrativos de procedimientos.uji.es."""

    def extract_document(self, url: str, html: str) -> ProcedimientoDoc | None:
        soup = BeautifulSoup(html, "html.parser")

        nombre_tag = soup.select_one("h1.proc-titulo")
        codigo_tag = soup.select_one("span.proc-codigo")
        unidad_tag = soup.select_one("span.proc-unidad")
        plazo_tag = soup.select_one("span.proc-plazo")
        doc_tag = soup.select_one("div.proc-documentacion")
        norm_tag = soup.select_one("div.proc-normativa")

        if not nombre_tag or not codigo_tag:
            return None

        nombre = nombre_tag.get_text(strip=True)
        codigo = codigo_tag.get_text(strip=True)
        unidad = unidad_tag.get_text(strip=True) if unidad_tag else ""
        plazo = plazo_tag.get_text(strip=True) if plazo_tag else ""
        documentacion = doc_tag.get_text(strip=True) if doc_tag else ""
        normativa = norm_tag.get_text(strip=True) if norm_tag else ""

        return ProcedimientoDoc(
            nombre=nombre,
            codigo=codigo,
            unidad_responsable=unidad,
            plazo=plazo,
            documentacion_requerida=documentacion,
            normativa_aplicable=normativa,
            metadata_json={
                "doc_type": "procedimiento",
                "codigo": codigo,
            },
        )

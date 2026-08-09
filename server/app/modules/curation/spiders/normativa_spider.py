"""Spider especializado para normativa institucional (BOE, DOGV, UJI).

Deploy: edge
"""
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from bs4 import BeautifulSoup


SELECTORS: dict[str, dict[str, str]] = {
    "boe": {
        "titulo": "h1.documento-tit",
        "fecha": "span.publicado",
        "texto": "div.texto-articulado",
    },
    "dogv": {
        "titulo": "h1.documento-tit",
        "fecha": "span.publicado",
        "texto": "div.texto-articulado",
    },
    "uji": {
        "titulo": "h1.documento-tit",
        "fecha": "span.publicado",
        "texto": "div.texto-articulado",
    },
}

_NORMA_RE = re.compile(r"\b(\d+/\d{4})\b")


@dataclass
class NormativaDoc:
    titulo: str
    fecha_publicacion: date
    numero_norma: str
    texto: str
    metadata_json: dict[str, Any]


class NormativaSpider:
    """Extrae documentos de normativa de fuentes BOE, DOGV y UJI."""

    def __init__(self, source_type: str, date_from: date | None = None) -> None:
        if source_type not in SELECTORS:
            raise ValueError(f"Unknown source_type: {source_type}")
        self.source_type = source_type
        self.date_from = date_from
        self._sel = SELECTORS[source_type]

    def extract_document(self, url: str, html: str) -> NormativaDoc | None:
        soup = BeautifulSoup(html, "html.parser")

        titulo_tag = soup.select_one(self._sel["titulo"])
        fecha_tag = soup.select_one(self._sel["fecha"])
        texto_tag = soup.select_one(self._sel["texto"])

        if not titulo_tag or not fecha_tag:
            return None

        titulo = titulo_tag.get_text(strip=True)
        fecha_str = fecha_tag.get_text(strip=True)

        try:
            fecha = _parse_date(fecha_str)
        except (ValueError, AttributeError):
            return None

        if self.date_from and fecha < self.date_from:
            return None

        texto = texto_tag.get_text(separator="\n", strip=True) if texto_tag else ""
        norma_match = _NORMA_RE.search(titulo)
        numero_norma = norma_match.group(1) if norma_match else ""

        return NormativaDoc(
            titulo=titulo,
            fecha_publicacion=fecha,
            numero_norma=numero_norma,
            texto=texto,
            metadata_json={
                "source_type": self.source_type,
                "fecha_publicacion": fecha.isoformat(),
                "numero_norma": numero_norma,
            },
        )


def _parse_date(s: str) -> date:
    """Parsea fechas en formato dd/mm/yyyy o yyyy-mm-dd."""
    s = s.strip()
    if "/" in s:
        day, month, year = s.split("/")
        return date(int(year), int(month), int(day))
    return date.fromisoformat(s)

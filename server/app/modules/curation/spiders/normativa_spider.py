"""Spider especializado para boletines de normativa (BOE, DOGV y portales con su marcado).

Deploy: edge

**AIS.2 — aquí había una tercera entrada con el nombre de una institución**, y sus tres
selectores eran un **duplicado exacto** de los de `boe`: no describía otro marcado, describía el
mismo con otra etiqueta. Un tipo de fuente dice qué **forma** tiene el portal —de ahí que `boe` y
`dogv` compartan selectores y sigan siendo dos, porque son dos boletines reconocibles—, no de
quién es; y el portal propio de cada institución es material de fork (`CONTRIBUTING.md`).

Lo que queda pendiente y es más grande que este prompt: **los selectores deberían ser dato del
sitio** (`hub_web_sites`), como ya lo son los criterios de curación desde CUR.2.1. Mientras vivan
aquí, un portal con otro marcado obliga a tocar el principal, que es exactamente lo que la
gobernanza quiere evitar.
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

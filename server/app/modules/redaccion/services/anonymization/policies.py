"""Políticas de anonimización predefinidas (9R.5.5).

Una `AnonymizerPolicy` es la lista declarativa de estrategias a aplicar al
conjunto de columnas de un archivo. Las estrategias siguen la sintaxis
del legacy (`<DETECCION>-><ACCION>`) para preservar compatibilidad con
ficheros de configuración existentes.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


Strategy = Literal[
    "NER_PERSON->INITIALS",
    "NER_PERSON->FAKE_NAME",
    "DNI->CODE",
    "DNI->MASK_LAST4",
    "DNI->AEPD",
    "EMAIL->TOKEN",
    "EMAIL->FAKE",
    "PHONE->FAKE",
    "IBAN->FAKE",
]


class AnonymizerPolicy(BaseModel):
    """Política aplicable a datasets tabulares."""

    strategies: list[Strategy]
    locale: str = "es_ES"

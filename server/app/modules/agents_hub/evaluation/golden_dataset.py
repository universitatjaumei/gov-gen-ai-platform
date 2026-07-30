"""Dataset dorado de recuperación (RAG.1). Deploy: edge.

Un dataset dorado es una lista de consultas reales con **qué documentos deberían salir**.
Es lo que convierte «el retriever va mejor» en una cifra comparable, y la regla del bloque
RAG es dura: ninguna mejora (RAG.3–RAG.8, RAG.10) se cierra sin comparar contra la línea
base medida aquí.

El `documents_fingerprint` es la pieza que evita la comparación sin sentido: un dataset
medido sobre otro corpus produce cifras que no comparan nada, y sin huella nadie se daría
cuenta.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class GoldenQuery(BaseModel):
    """Una consulta con sus objetivos esperados."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str
    language: str = "ca"
    # El objetivo puede expresarse por URL canónica o por id de documento. Al menos uno.
    expected_canonical_urls: tuple[str, ...] = ()
    expected_document_ids: tuple[str, ...] = ()
    # 'sigla', 'conversacional', 'normativa'… sirven para leer el informe por clase de
    # consulta: una mejora del léxico debe verse en las de sigla y no en el resto.
    tags: tuple[str, ...] = ()
    # Turnos anteriores, para el query rewriting de RAG.10.
    history: tuple[str, ...] | None = None
    notes: str | None = None

    @field_validator("query")
    @classmethod
    def _consulta_no_vacia(cls, valor: str) -> str:
        if not valor or not valor.strip():
            raise ValueError("query vacia")
        return valor

    @model_validator(mode="after")
    def _al_menos_un_objetivo(self) -> "GoldenQuery":
        if not self.expected_canonical_urls and not self.expected_document_ids:
            raise ValueError(
                f"{self.query!r}: hace falta expected_canonical_urls o "
                "expected_document_ids; una consulta sin objetivo no mide nada"
            )
        return self

    @property
    def targets(self) -> tuple[str, ...]:
        """Objetivos en el eje que toque, para pasarlos a las métricas."""
        return self.expected_canonical_urls or self.expected_document_ids


class GoldenDataset(BaseModel):
    """Conjunto de consultas doradas medido sobre un corpus concreto."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    documents_fingerprint: str
    chatbot_reference: str | None = None
    queries: tuple[GoldenQuery, ...] = ()

    @model_validator(mode="after")
    def _sin_consultas_repetidas(self) -> "GoldenDataset":
        vistas = [q.query.strip().lower() for q in self.queries]
        repetidas = {q for q in vistas if vistas.count(q) > 1}
        if repetidas:
            raise ValueError(f"consultas repetidas en el dataset: {sorted(repetidas)}")
        return self


def corpus_fingerprint(content_hashes: Sequence[str]) -> str:
    """Huella del corpus a partir de los `content_hash` de sus documentos.

    Independiente del orden: el corpus es un conjunto, no una lista, y ordenarlo distinto
    no lo convierte en otro.
    """
    unidos = "|".join(sorted(content_hashes))
    return hashlib.sha256(unidos.encode("utf-8")).hexdigest()[:32]


def fingerprint_matches(dataset: GoldenDataset, content_hashes: Sequence[str]) -> bool:
    return dataset.documents_fingerprint == corpus_fingerprint(content_hashes)


def load_golden_dataset(path: Path | str) -> GoldenDataset:
    datos = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return GoldenDataset(**datos)

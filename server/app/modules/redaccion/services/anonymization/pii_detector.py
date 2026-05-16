"""PiiDetector — wrapper ligero sobre AnonymizationContext para escaneo (9R.5.5).

Migrado desde client_app/app/utils/pii_detector.py + parte de
client_app/app/services/anonymization_service.py.analyze_dataframe.

Tres operaciones principales:
- `scan_dataframe(df)` → describe columnas (tipo + ejemplos + provider faker sugerido).
- `detect_spans(text)` → spans PII detectados en texto libre (para preview).
- Es lazy en spaCy: si el modelo no carga, degrada a regex + heurísticas.

Reutilizable por:
- TestDataAnonymizerService (Parte 2).
- Fase 13 NER (hooks pre/post-LLM).
"""
from __future__ import annotations

from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field

from server.app.modules.redaccion.services.anonymization.anonymizer import (
    AnonymizationContext,
)


# ---------------------------------------------------------------------------
# Tipos públicos
# ---------------------------------------------------------------------------

FakerProvider = Literal[
    "keep", "name", "first_name", "last_name", "email", "phone",
    "iban", "dni", "nie", "address", "city", "company", "date", "integer",
]


class ColumnInfo(BaseModel):
    """Describe una columna para la UI de configuración de anonimización."""

    name: str
    sample_values: list[str] = Field(default_factory=list)
    inferred_pii_type: str = "NONE"
    inferred_faker_provider: FakerProvider = "keep"
    confidence: float = 0.0


class PiiSpan(BaseModel):
    """Span PII detectado en texto libre (preview previo a aplicar)."""

    start: int
    end: int
    type: str
    original_text: str
    suggested_fake: str


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

_PII_TO_FAKER: dict[str, FakerProvider] = {
    "PERSON_NAME": "name",
    "PERSON": "name",
    "EMAIL": "email",
    "PHONE": "phone",
    "IBAN": "iban",
    "DNI": "dni",
    "NIE": "nie",
    "PASSPORT": "dni",
    "ADDRESS": "address",
    "ORGANIZATION": "company",
    "DATE": "date",
    "CREDIT_CARD": "integer",
    "POSTAL_CODE": "integer",
    "NSS": "integer",
}


class PiiDetector:
    """Wrapper sobre AnonymizationContext para consumo desde servicios y UI."""

    def __init__(self, ctx: AnonymizationContext | None = None) -> None:
        self.ctx = ctx or AnonymizationContext()

    @property
    def spacy_available(self) -> bool:
        return self.ctx.spacy_available

    # ------------------------------------------------------------------
    # DataFrame scan
    # ------------------------------------------------------------------

    def scan_dataframe(self, df: pd.DataFrame, sample_size: int = 50) -> list[ColumnInfo]:
        if df is None or df.empty:
            return []

        # Reaprovecha analyze_fields (heurística + NER + regex sobre 10 filas).
        analysis = self.ctx.analyze_fields(df)
        # Mapa de tipo simplificado → tipo PII detallado: cuando analyze_fields
        # devuelve "ID", usamos las columnas para refinar a DNI/PHONE/IBAN/…
        results: list[ColumnInfo] = []
        for entry in analysis:
            col = entry["field"]
            inferred_type = entry["type"]
            # Refinar ID/PERSON/EMAIL con la heurística de cabecera completa
            refined = self.ctx._analyze_header(str(col)) or inferred_type
            if refined == "NONE" and inferred_type == "NONE":
                pii_type = "NONE"
                provider: FakerProvider = "keep"
            elif inferred_type == "PERSON":
                pii_type = "PERSON_NAME"
                # Diferenciar firstname/lastname por nombre de columna
                col_low = str(col).lower()
                if any(k in col_low for k in ("apellido", "cognom", "surname", "last")):
                    provider = "last_name"
                elif any(k in col_low for k in ("nombre", "nom", "first", "name")):
                    provider = "first_name"
                else:
                    provider = "name"
            else:
                pii_type = refined
                provider = _PII_TO_FAKER.get(refined, "keep")

            sample_values: list[str] = []
            head = df[col].dropna().astype(str).head(min(len(df), sample_size))
            sample_values = [v for v in head.tolist()[:5]]

            results.append(
                ColumnInfo(
                    name=str(col),
                    sample_values=sample_values,
                    inferred_pii_type=pii_type,
                    inferred_faker_provider=provider,
                    confidence=float(entry.get("confidence", 0.0)),
                )
            )
        return results

    # ------------------------------------------------------------------
    # Text scan
    # ------------------------------------------------------------------

    def detect_spans(self, text: str) -> list[PiiSpan]:
        """Detecta spans PII en texto libre y propone reemplazos sintéticos.

        El detector NO muta el contexto de anonimización (usa una instancia
        aislada de FakerGenerator para no contaminar mapas externos).
        """
        if not text:
            return []

        # Detección reutiliza AnonymizationContext pero generamos los fakes
        # con un FakerGenerator desechable para no contaminar mapas externos.
        anchor_entities, anchor_meta = self.ctx._detect_with_anchors(text)
        regex_ner = self.ctx._detect_with_regex(text) + self.ctx._detect_with_ner(text)
        non_overlap = self.ctx._remove_overlapping(anchor_entities, regex_ner)
        entities = anchor_entities + non_overlap
        entities.sort(key=lambda e: e.start)

        from server.app.modules.redaccion.services.anonymization.faker_generator import (
            FakerGenerator,
        )

        preview = FakerGenerator()
        spans: list[PiiSpan] = []
        for entity in entities:
            suggested = preview.generate(entity.type, entity.text, context=entity.context)
            spans.append(
                PiiSpan(
                    start=entity.start,
                    end=entity.end,
                    type=entity.type,
                    original_text=entity.text,
                    suggested_fake=suggested,
                )
            )
        return spans

    def has_form_anchors(self) -> bool:
        """`True` si el último scan/anonymize detectó etiquetas de formulario."""
        return bool(self.ctx.get_detected_anchors())

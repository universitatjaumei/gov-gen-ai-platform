"""ManualInputPipeline — normalización de entrada manual del usuario (9R.5.3).

Sin LLM: parsea y valida tipos (número, fecha, texto) contra el InputSlot
configurado en options["slot"]. Devuelve ExtractedMetric para números y
free_text para texto/fecha.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone

from server.app.modules.redaccion.pipelines.contracts import (
    ExtractionInput,
    ExtractionProvenance,
    ExtractionResult,
    ExtractionWarning,
    ExtractedMetric,
)


class ManualInputPipeline:
    """Convierte texto introducido por el usuario en ExtractionResult normalizado."""

    pipeline_id = "manual_pipeline_v1"

    def supports(self, source_kind: str) -> bool:
        return source_kind == "manual"

    def extract(self, inp: ExtractionInput) -> ExtractionResult:
        raw = (inp.raw_text or "").strip()
        slot_dict: dict = inp.options.get("slot", {})
        kind: str = slot_dict.get("kind") or inp.options.get("kind", "text")
        required: bool = slot_dict.get("required", False)
        validation: dict = slot_dict.get("validation") or {}
        slot_id: str = slot_dict.get("slot_id", "manual_input")

        warnings: list[ExtractionWarning] = []
        metrics: list[ExtractedMetric] = []
        free_text: str | None = None

        if not raw:
            if required:
                warnings.append(
                    ExtractionWarning(
                        code="REQUIRED_FIELD_EMPTY",
                        message=f"El campo '{slot_id}' es obligatorio y está vacío.",
                        severity="error",
                    )
                )
            return ExtractionResult(warnings=warnings, provenance=self._provenance())

        if kind == "number":
            try:
                value = _parse_number(raw)
            except ValueError:
                warnings.append(
                    ExtractionWarning(
                        code="TYPE_MISMATCH",
                        message=f"Se esperaba un número pero se recibió: '{raw}'.",
                        severity="error",
                    )
                )
            else:
                min_val = validation.get("min")
                max_val = validation.get("max")
                if min_val is not None and value < float(min_val):
                    warnings.append(
                        ExtractionWarning(
                            code="VALUE_OUT_OF_RANGE",
                            message=f"El valor {value} es menor que el mínimo permitido ({min_val}).",
                            severity="error",
                        )
                    )
                elif max_val is not None and value > float(max_val):
                    warnings.append(
                        ExtractionWarning(
                            code="VALUE_OUT_OF_RANGE",
                            message=f"El valor {value} es mayor que el máximo permitido ({max_val}).",
                            severity="error",
                        )
                    )
                else:
                    metrics.append(ExtractedMetric(name=slot_id, value=value))

        elif kind == "date":
            try:
                parsed = _parse_date(raw)
                free_text = parsed.isoformat()
            except ValueError:
                warnings.append(
                    ExtractionWarning(
                        code="TYPE_MISMATCH",
                        message=f"Formato de fecha no reconocido: '{raw}'.",
                        severity="error",
                    )
                )

        else:
            free_text = raw
            pattern = validation.get("pattern")
            if pattern and not re.fullmatch(pattern, raw):
                warnings.append(
                    ExtractionWarning(
                        code="VALIDATION_ERROR",
                        message="El valor no cumple el patrón requerido.",
                        severity="error",
                    )
                )

        return ExtractionResult(
            metrics=metrics,
            free_text=free_text,
            warnings=warnings,
            provenance=self._provenance(),
        )

    def _provenance(self) -> ExtractionProvenance:
        return ExtractionProvenance(
            pipeline_id=self.pipeline_id,
            source_ref="manual",
            extracted_at=datetime.now(timezone.utc),
        )


def _parse_number(raw: str) -> float:
    """Parsea número en formato inglés (1,234.56) o español (1.234,56)."""
    text = raw.strip()
    if "," in text and "." in text:
        if text.rindex(",") > text.rindex("."):
            # Español: punto como separador de miles, coma como decimal
            text = text.replace(".", "").replace(",", ".")
        else:
            # Inglés: coma como separador de miles, punto como decimal
            text = text.replace(",", "")
    elif "," in text:
        # Coma como separador decimal (formato español sin miles)
        text = text.replace(",", ".")
    return float(text)


def _parse_date(raw: str) -> date:
    """Parsea fecha en formatos YYYY-MM-DD, DD/MM/YYYY o DD-MM-YYYY."""
    raw = raw.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return date.fromisoformat(raw)
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.fullmatch(r"(\d{1,2})-(\d{1,2})-(\d{4})", raw)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    raise ValueError(f"Formato de fecha no reconocido: {raw!r}")

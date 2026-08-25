"""AnonymizerService — alto nivel async sobre StorageRef (9R.5.5).

Migrado desde client_app/app/modules/privacy/anonymizer_service.py y
client_app/app/services/anonymization_service.py, con dos cambios duros:

- Las firmas reciben `StorageRef` en lugar de rutas; la lectura/escritura
  va por `StorageService` (`fsspec`-agnóstico).
- Sin `EncryptionService` ni `enterprise_audit_service`: el audit se
  delega al llamador (workspace_audit_events) o se ignora en MVP.

`save_state` / `load_state` se mantienen como **no-op opcionales** marcados
para post-MVP, según el contrato del prompt 9R.5.5.
"""
from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from typing import Any

import pandas as pd

from server.app.core.storage import StorageService
from server.app.modules.redaccion.pipelines.contracts import StorageRef
from server.app.modules.redaccion.services.anonymization.anonymizer import (
    AnonymizationContext,
)
from server.app.modules.redaccion.services.anonymization.policies import (
    AnonymizerPolicy,
)


@dataclass
class AnonymizationRule:
    """Regla por columna (método + parámetros) tal como llega desde la UI."""

    method: str
    params: dict[str, Any]
    entity_type_raw: str = "UNKNOWN"


def _suffix_from_key(key: str) -> str:
    return key.rsplit(".", 1)[-1].lower() if "." in key else ""


def _read_dataframe(data: bytes, suffix: str) -> pd.DataFrame:
    if suffix == "csv":
        return pd.read_csv(io.BytesIO(data))
    if suffix in ("xlsx", "xls"):
        return pd.read_excel(io.BytesIO(data), engine="openpyxl")
    if suffix == "json":
        return pd.read_json(io.BytesIO(data))
    if suffix == "parquet":
        return pd.read_parquet(io.BytesIO(data))
    raise ValueError(f"Unsupported tabular format: .{suffix}")


def _write_dataframe(df: pd.DataFrame, suffix: str) -> bytes:
    buffer = io.BytesIO()
    if suffix == "csv":
        df.to_csv(buffer, index=False)
    elif suffix in ("xlsx", "xls"):
        df.to_excel(buffer, index=False, engine="openpyxl")
    elif suffix == "json":
        buffer.write(df.to_json(orient="records", force_ascii=False).encode("utf-8"))
    elif suffix == "parquet":
        df.to_parquet(buffer, index=False)
    else:
        raise ValueError(f"Unsupported tabular format: .{suffix}")
    return buffer.getvalue()


def _method_to_mode(method: str) -> str:
    return {
        "redact": "MASK",
        "initials": "INITIALS",
        "aepd": "AEPD",
        "faker": "FAKER",
    }.get(method, "MASK")


class AnonymizerService:
    """Servicio async sobre StorageRef para flujos batch (extracción + tests)."""

    def __init__(self, storage: StorageService) -> None:
        self._storage = storage

    # ------------------------------------------------------------------
    # Análisis y aplicación sobre archivos tabulares
    # ------------------------------------------------------------------

    async def analyze_file(self, file_ref: StorageRef) -> list[dict[str, Any]]:
        """Carga el archivo y devuelve análisis de columnas (legacy-shape)."""
        data = await self._storage.get(file_ref.key)
        suffix = _suffix_from_key(file_ref.key)
        df = _read_dataframe(data, suffix)
        ctx = AnonymizationContext()
        return ctx.analyze_fields(df)

    async def apply_policy(
        self,
        input_ref: StorageRef,
        policy: AnonymizerPolicy,
        output_bucket: str | None = None,
    ) -> StorageRef:
        """Aplica una `AnonymizerPolicy` y persiste el archivo sintético."""
        data = await self._storage.get(input_ref.key)
        suffix = _suffix_from_key(input_ref.key)
        df = _read_dataframe(data, suffix)
        ctx = AnonymizationContext(locale=policy.locale)

        for col in df.columns:
            series = df[col].fillna("").astype(str)
            for strategy in policy.strategies:
                series = self._apply_strategy_to_series(series, strategy, ctx)
            df[col] = series

        out_bytes = _write_dataframe(df, suffix)
        out_key = f"anonymized/{uuid.uuid4()}.{suffix or 'bin'}"
        await self._storage.put(out_key, out_bytes)
        return StorageRef(bucket=output_bucket or input_ref.bucket, key=out_key)

    async def apply_rules(
        self,
        input_ref: StorageRef,
        config: dict[str, AnonymizationRule],
        output_bucket: str | None = None,
    ) -> tuple[StorageRef, dict[str, str]]:
        """Aplica reglas columna→regla y devuelve (archivo, mapa de anonimización)."""
        data = await self._storage.get(input_ref.key)
        suffix = _suffix_from_key(input_ref.key)
        df = _read_dataframe(data, suffix)
        ctx = AnonymizationContext()

        mapped: dict[str, dict[str, Any]] = {}
        for col, rule in config.items():
            if rule.method == "none":
                continue
            inferred = ctx._analyze_header(col) or rule.entity_type_raw
            mapped[col] = {"mode": _method_to_mode(rule.method), "type": inferred}

        result_df = ctx.anonymize_dataframe(df, mapped)
        out_bytes = _write_dataframe(result_df, suffix)
        out_key = f"anonymized/{uuid.uuid4()}.{suffix or 'bin'}"
        await self._storage.put(out_key, out_bytes)
        return (
            StorageRef(bucket=output_bucket or input_ref.bucket, key=out_key),
            dict(ctx.fake_to_real),
        )

    # ------------------------------------------------------------------
    # Texto libre (reusable por Fase 13: hooks LLM)
    # ------------------------------------------------------------------

    async def anonymize_text(
        self, text: str, allowed_types: list[str] | None = None
    ) -> dict[str, Any]:
        """Anonimiza un bloque de texto y devuelve mapping + estructura formularios."""
        if not text:
            return {
                "anonymized_text": "",
                "mapping": {},
                "detected_anchors": [],
                "form_structure_hint": None,
            }
        ctx = AnonymizationContext()
        anonymized = ctx.anonymize(text, allowed_types=allowed_types)
        return {
            "anonymized_text": anonymized,
            "mapping": dict(ctx.fake_to_real),
            "detected_anchors": ctx.get_detected_anchors(),
            "form_structure_hint": ctx.get_form_structure_hint(),
        }

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_strategy_to_series(
        series: pd.Series, strategy: str, ctx: AnonymizationContext
    ) -> pd.Series:
        if strategy == "NER_PERSON->INITIALS":
            return series.apply(
                lambda x: AnonymizerService._to_initials(x, ctx) if x.strip() else x
            )
        if strategy == "NER_PERSON->FAKE_NAME":
            return series.apply(lambda x: ctx.anonymize(x) if x.strip() else x)
        if strategy == "EMAIL->TOKEN":
            return series.str.replace(
                r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b",
                "EMAIL_TOKEN",
                regex=True,
            )
        if strategy == "EMAIL->FAKE":
            return series.apply(
                lambda x: ctx.anonymize(x) if x.strip() and "@" in x else x
            )
        if strategy == "DNI->MASK_LAST4":
            return series.str.replace(
                r"\b(\d{4})\d{4}([A-Z])\b", r"\1****\2", regex=True
            )
        if strategy == "DNI->CODE":
            return series.str.replace(r"\b\d{8}[A-Z]\b", "DNI_CODE", regex=True)
        if strategy == "DNI->AEPD":
            return series.apply(
                lambda x: ctx.anonymize_document_id(x, mode="AEPD") if x else x
            )
        if strategy == "PHONE->FAKE":
            return series.apply(lambda x: ctx.anonymize(x, allowed_types=["PHONE"]) if x else x)
        if strategy == "IBAN->FAKE":
            return series.apply(lambda x: ctx.anonymize(x, allowed_types=["IBAN"]) if x else x)
        return series

    @staticmethod
    def _to_initials(value: str, ctx: AnonymizationContext) -> str:
        if not value or not value.strip():
            return value
        entities = ctx._detect_with_ner(value)
        if not any(e.type == "PERSON_NAME" for e in entities):
            return value
        parts = [p.strip() for p in value.split() if p.strip()]
        if len(parts) >= 2:
            return " ".join(f"{p[0]}." for p in parts)
        return f"{parts[0][0]}." if parts else value

    # ------------------------------------------------------------------
    # AIS.5 — aquí había `save_state`/`load_state`, dos no-op sin un solo consumidor.
    #
    # Se retiran, no se completan, y la razón es la decisión del usuario del 2026-08-24: el
    # piloto no trata datos de ciudadanos y la anonimización es configurable, así que **no hay
    # bóveda cifrada antes del piloto**. La persistencia del mapa es F2.A.4 (Vault Edge) y se
    # escribirá cuando haya quien la consuma.
    #
    # Se borran en vez de dejarlos marcados porque un método que existe, se puede llamar y no
    # hace nada es peor que su ausencia: invita a creer que el mapa se guardó. El alcance real
    # —la reversión vale dentro de la ejecución y no después— está dicho en el docstring de
    # `AnonymizationMode`, que es donde lo lee quien elige el modo.
    # ------------------------------------------------------------------

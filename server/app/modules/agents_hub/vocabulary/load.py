"""Carga del vocabulario controlado desde CSV (ING.0.1).

Deploy: cloud — escribe configuración institucional.

Uso:
    uv run python -m server.app.modules.agents_hub.vocabulary.load \
        --axis ambit --csv <ruta>/vocabulari/ambits.csv --organizacion-id <uuid>
    uv run python -m server.app.modules.agents_hub.vocabulary.load \
        --axis submateria --csv <ruta>/vocabulari/submateries.csv --organizacion-id <uuid>

Idempotente por la clave natural (organizacion_id, axis, codi): la segunda pasada no
duplica y reporta «sin cambios». Un CSV con un `parent_codi` inexistente se rechaza
ENTERO, sin escribir nada: cargar a medias dejaría el vocabulario incoherente y la
validación de documentos empezaría a fallar de forma aleatoria.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.services.vocabulary_service import (
    VocabularyAxis,
    VocabularyTermDTO,
)

_RESTKEY = "__extra__"

# Columnas de nombre según el eje. El resto del CSV (asistente, propietario,
# recuentos, normas de ejemplo) es documentación del informe de materias y no
# entra en el hub.
_DESCRIPTION_COLUMNS = ("descripcio_router", "abast")


class VocabularyCsvError(Exception):
    """El CSV o la operación de carga no son válidos."""


@dataclass(frozen=True)
class VocabularyLoadReport:
    created: int = 0
    updated: int = 0
    unchanged: int = 0

    def render(self) -> str:
        return (
            f"creados={self.created} actualizados={self.updated} "
            f"sin_cambios={self.unchanged}"
        )


class VocabularyStore(Protocol):
    """Persistencia de términos. Aísla la carga de SQLAlchemy para poder testearla."""

    async def fetch(
        self, axis: str, organizacion_id: uuid.UUID
    ) -> list[VocabularyTermDTO]: ...

    async def create(self, term: VocabularyTermDTO, organizacion_id: uuid.UUID) -> None: ...

    async def update(self, term: VocabularyTermDTO, organizacion_id: uuid.UUID) -> None: ...


# ───────────────────────── Parseo ─────────────────────────


def _pick(row: dict[str, str | None], *names: str) -> str | None:
    for name in names:
        value = row.get(name)
        if value and value.strip():
            return value.strip()
    return None


def parse_vocabulary_csv(path: Path | str, axis: str) -> list[VocabularyTermDTO]:
    """Lee un CSV de vocabulario (`;` como separador) y devuelve los términos.

    El `ordre` sale del orden del fichero: es el que decide cómo se presenta el
    índice del router.
    """
    path = Path(path)
    terms: list[VocabularyTermDTO] = []

    # utf-8-sig: los CSV vienen de Excel y traen BOM.
    # restkey: 'normes_exemple' lleva comas sin comillas en el fichero real, así que
    # la última columna se desborda en campos extra que hay que absorber sin romper.
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";", restkey=_RESTKEY)
        if not reader.fieldnames or "codi" not in reader.fieldnames:
            raise VocabularyCsvError(
                f"{path.name}: falta la columna obligatoria 'codi' "
                f"(cabeceras: {reader.fieldnames})"
            )

        for position, row in enumerate(reader):
            codi = _pick(row, "codi")
            if not codi:
                raise VocabularyCsvError(
                    f"{path.name}: fila {position + 2} sin 'codi'"
                )
            nom_primari = _pick(row, "nom_val", "nom", "nom_primari")
            if not nom_primari:
                raise VocabularyCsvError(
                    f"{path.name}: el término '{codi}' no tiene nombre"
                )
            terms.append(
                VocabularyTermDTO(
                    axis=axis,
                    codi=codi,
                    nom_primari=nom_primari,
                    nom_secundari=_pick(row, "nom_es", "nom_secundari"),
                    parent_codi=_pick(row, "ambit", "parent_codi"),
                    descripcio_router=_pick(row, *_DESCRIPTION_COLUMNS),
                    ordre=position,
                )
            )

    if not terms:
        raise VocabularyCsvError(f"{path.name}: no contiene ningún término")

    duplicados = {t.codi for t in terms if [x.codi for x in terms].count(t.codi) > 1}
    if duplicados:
        raise VocabularyCsvError(
            f"{path.name}: códigos duplicados: {sorted(duplicados)}"
        )
    return terms


# ───────────────────────── Aplicación ─────────────────────────


def _differs(new: VocabularyTermDTO, old: VocabularyTermDTO) -> bool:
    return (
        new.nom_primari != old.nom_primari
        or new.nom_secundari != old.nom_secundari
        or new.parent_codi != old.parent_codi
        or new.descripcio_router != old.descripcio_router
        or new.ordre != old.ordre
    )


async def _assert_parents_exist(
    store: VocabularyStore, terms: list[VocabularyTermDTO], organizacion_id: uuid.UUID
) -> None:
    parents = {t.parent_codi for t in terms if t.parent_codi}
    if not parents:
        return
    known = {t.codi for t in await store.fetch(VocabularyAxis.AMBIT, organizacion_id)}
    dangling = sorted(parents - known)
    if dangling:
        raise VocabularyCsvError(
            "Los siguientes 'parent_codi' no existen en el eje 'ambit' y el CSV se "
            f"rechaza entero: {dangling}. Carga primero los ámbitos."
        )


async def apply_terms(
    store: VocabularyStore,
    terms: list[VocabularyTermDTO],
    organizacion_id: uuid.UUID,
    dry_run: bool = False,
) -> VocabularyLoadReport:
    """Reconcilia los términos del CSV contra los almacenados.

    Valida los padres ANTES de escribir nada: un vocabulario a medias es peor que
    uno no cargado.
    """
    await _assert_parents_exist(store, terms, organizacion_id)

    axis = terms[0].axis
    existing = {t.codi: t for t in await store.fetch(axis, organizacion_id)}

    created = updated = unchanged = 0
    for term in terms:
        current = existing.get(term.codi)
        if current is None:
            created += 1
            if not dry_run:
                await store.create(term, organizacion_id)
        elif _differs(term, current):
            updated += 1
            if not dry_run:
                # Se preserva el estado de vigencia/sustitución: lo gobierna
                # supersede_term, no el CSV.
                await store.update(
                    VocabularyTermDTO(
                        **{
                            **term.__dict__,
                            "vigent": current.vigent,
                            "substituit_per_codi": current.substituit_per_codi,
                        }
                    ),
                    organizacion_id,
                )
        else:
            unchanged += 1

    return VocabularyLoadReport(created=created, updated=updated, unchanged=unchanged)


async def supersede_term(
    store: VocabularyStore,
    axis: str,
    codi_antic: str,
    codi_nou: str,
    organizacion_id: uuid.UUID,
) -> None:
    """Marca `codi_antic` como sustituido por `codi_nou` (renombrado o fusión).

    No toca los documentos: el barrido de `hub_documents` se hace en ING.0.2, que es
    donde existen las columnas `ambit_principal`/`submateries`.
    """
    if codi_antic == codi_nou:
        raise VocabularyCsvError("Un término no puede sustituirse por sí mismo")

    terms = {t.codi: t for t in await store.fetch(axis, organizacion_id)}
    if codi_antic not in terms:
        raise VocabularyCsvError(f"El término '{codi_antic}' no existe en '{axis}'")
    if codi_nou not in terms:
        raise VocabularyCsvError(
            f"El sustituto '{codi_nou}' no existe en '{axis}': créalo antes de "
            "retirar el término antiguo"
        )

    old = terms[codi_antic]
    await store.update(
        VocabularyTermDTO(
            **{**old.__dict__, "vigent": False, "substituit_per_codi": codi_nou}
        ),
        organizacion_id,
    )


# ───────────────────────── Store real ─────────────────────────


class SqlAlchemyVocabularyStore:
    """Implementación de `VocabularyStore` sobre la BD de configuración."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def fetch(
        self, axis: str, organizacion_id: uuid.UUID
    ) -> list[VocabularyTermDTO]:
        from server.app.modules.agents_hub.database.config_models import (
            HubVocabularyTerm,
        )

        result = await self.session.execute(
            select(HubVocabularyTerm).where(
                HubVocabularyTerm.organizacion_id == organizacion_id,
                HubVocabularyTerm.axis == axis,
            )
        )
        return [_to_dto(row) for row in result.scalars().all()]

    async def create(
        self, term: VocabularyTermDTO, organizacion_id: uuid.UUID
    ) -> None:
        from server.app.modules.agents_hub.database.config_models import (
            HubVocabularyTerm,
        )

        self.session.add(
            HubVocabularyTerm(
                organizacion_id=organizacion_id,
                axis=term.axis,
                codi=term.codi,
                nom_primari=term.nom_primari,
                nom_secundari=term.nom_secundari,
                parent_codi=term.parent_codi,
                descripcio_router=term.descripcio_router,
                ordre=term.ordre,
                vigent=term.vigent,
                substituit_per_codi=term.substituit_per_codi,
            )
        )
        await self.session.flush()

    async def update(
        self, term: VocabularyTermDTO, organizacion_id: uuid.UUID
    ) -> None:
        from datetime import datetime, timezone

        from server.app.modules.agents_hub.database.config_models import (
            HubVocabularyTerm,
        )

        result = await self.session.execute(
            select(HubVocabularyTerm).where(
                HubVocabularyTerm.organizacion_id == organizacion_id,
                HubVocabularyTerm.axis == term.axis,
                HubVocabularyTerm.codi == term.codi,
            )
        )
        row = result.scalars().first()
        if row is None:
            raise VocabularyCsvError(f"No existe el término '{term.codi}' a actualizar")

        row.nom_primari = term.nom_primari
        row.nom_secundari = term.nom_secundari
        row.parent_codi = term.parent_codi
        row.descripcio_router = term.descripcio_router
        row.ordre = term.ordre
        row.vigent = term.vigent
        row.substituit_per_codi = term.substituit_per_codi
        row.updated_at = datetime.now(timezone.utc)
        await self.session.flush()


def _to_dto(row) -> VocabularyTermDTO:
    return VocabularyTermDTO(
        axis=row.axis,
        codi=row.codi,
        nom_primari=row.nom_primari,
        nom_secundari=row.nom_secundari,
        parent_codi=row.parent_codi,
        descripcio_router=row.descripcio_router,
        ordre=row.ordre,
        vigent=row.vigent,
        substituit_per_codi=row.substituit_per_codi,
    )


# ───────────────────────── CLI ─────────────────────────


async def _run(args: argparse.Namespace) -> int:
    # Mismo patrón que app/scripts/bootstrap.py (11.3): motor y factoría propios,
    # porque el CLI vive fuera del ciclo de vida de FastAPI.
    from server.app.modules.agents_hub.database.connection import (
        create_async_engine,
        create_session_factory,
    )

    try:
        terms = parse_vocabulary_csv(args.csv, args.axis)
    except VocabularyCsvError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"{Path(args.csv).name}: {len(terms)} términos leídos (eje '{args.axis}')")

    engine = create_async_engine()
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            store = SqlAlchemyVocabularyStore(session)
            try:
                report = await apply_terms(
                    store, terms, args.organizacion_id, dry_run=args.dry_run
                )
            except VocabularyCsvError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 1
            if args.dry_run:
                print(f"[dry-run] {report.render()} (nada escrito)")
            else:
                await session.commit()
                print(report.render())
    finally:
        await engine.dispose()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Carga el vocabulario controlado del corpus desde un CSV."
    )
    parser.add_argument(
        "--axis",
        required=True,
        choices=[a.value for a in VocabularyAxis],
        help="Eje del vocabulario",
    )
    parser.add_argument("--csv", required=True, help="Ruta del CSV")
    parser.add_argument(
        "--organizacion-id",
        required=True,
        type=uuid.UUID,
        dest="organizacion_id",
        help="Organización destino",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Reporta el plan sin escribir"
    )
    args = parser.parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Vocabulario controlado de ámbitos y submaterias (ING.0.1).

Deploy: edge (lado consumidor). Los términos se leen a través del protocolo
`VocabularySource`, que implementa `ConfigProvider`; este módulo NO importa el
modelo ORM, que es configuración cloud.

Regla de diseño, de CLAUDE.md §5 «Corpus normativo»:

- Los EJES son estructura: pocos, estables, y añadir uno exige código que lo
  consuma. Van en `VocabularyAxis`.
- Los TÉRMINOS son dato: cambian sin tocar código, porque el vocabulario está
  pendiente de validación por Secretaría General. Viven en tabla, con `vigent` y
  `substituit_per_codi` para renombrar y fusionar.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class VocabularyAxis(StrEnum):
    """Ejes del vocabulario. Estructura, no dato."""

    AMBIT = "ambit"
    SUBMATERIA = "submateria"
    RANG = "rang"
    COLECTIU = "colectiu"
    TIPUS = "tipus"


@dataclass(frozen=True)
class VocabularyTermDTO:
    """Término del vocabulario visto desde edge. No es el modelo ORM."""

    axis: str
    codi: str
    nom_primari: str
    nom_secundari: str | None = None
    parent_codi: str | None = None
    descripcio_router: str | None = None
    ordre: int = 0
    vigent: bool = True
    substituit_per_codi: str | None = None


class VocabularyError(Exception):
    """Error de vocabulario."""


class VocabularyTermNotFoundError(VocabularyError):
    """El código no existe en el eje y organización consultados."""


class VocabularyCycleError(VocabularyError):
    """La cadena de sustituciones se cierra sobre sí misma."""


class VocabularySource(Protocol):
    """Fuente de términos. `LocalConfigProvider` la satisface."""

    async def list_vocabulary(
        self, axis: str, organizacion_id: uuid.UUID
    ) -> list[VocabularyTermDTO]: ...


class VocabularyService:
    """Valida, resuelve y presenta el vocabulario de UNA organización."""

    def __init__(self, source: VocabularySource, organizacion_id: uuid.UUID) -> None:
        self.source = source
        self.organizacion_id = organizacion_id

    async def _terms_by_codi(self, axis: str) -> dict[str, VocabularyTermDTO]:
        terms = await self.source.list_vocabulary(axis, self.organizacion_id)
        return {t.codi: t for t in terms}

    async def validate(self, axis: str, codis: list[str]) -> list[str]:
        """Códigos no reconocidos o no vigentes, en el orden en que llegaron.

        Devuelve la lista COMPLETA: quien valida un documento necesita ver todos
        los códigos malos de una vez, no ir descubriéndolos de uno en uno.
        """
        if not codis:
            return []
        known = await self._terms_by_codi(axis)
        return [c for c in codis if c not in known or not known[c].vigent]

    async def resolve(self, axis: str, codi: str) -> str:
        """Sigue la cadena de sustituciones hasta el término vigente."""
        terms = await self._terms_by_codi(axis)
        seen: set[str] = set()
        current = codi

        while True:
            if current in seen:
                raise VocabularyCycleError(
                    f"Ciclo de sustituciones en el eje '{axis}': "
                    f"{' → '.join([*seen, current])}"
                )
            seen.add(current)

            term = terms.get(current)
            if term is None:
                raise VocabularyTermNotFoundError(
                    f"El código '{current}' no existe en el eje '{axis}'"
                )
            if term.vigent:
                return term.codi
            if term.substituit_per_codi is None:
                raise VocabularyTermNotFoundError(
                    f"El código '{current}' no está vigente y no declara sustituto"
                )
            current = term.substituit_per_codi

    async def build_router_index(self) -> str:
        """Índice de submaterias agrupado por ámbito, para el system prompt.

        Es el Nivel 0 de la estrategia de recuperación: el router necesita saber
        qué TEMAS existen, no qué normas existen.
        """
        ambits = await self.source.list_vocabulary(
            VocabularyAxis.AMBIT, self.organizacion_id
        )
        submateries = await self.source.list_vocabulary(
            VocabularyAxis.SUBMATERIA, self.organizacion_id
        )

        by_parent: dict[str, list[VocabularyTermDTO]] = {}
        for term in submateries:
            if term.vigent:
                by_parent.setdefault(term.parent_codi or "", []).append(term)

        lines: list[str] = []
        for ambit in sorted(
            (a for a in ambits if a.vigent), key=lambda a: (a.ordre, a.codi)
        ):
            children = by_parent.get(ambit.codi, [])
            if not children:
                continue
            lines.append(f"## {ambit.nom_primari} ({ambit.codi})")
            for child in sorted(children, key=lambda t: (t.ordre, t.codi)):
                descripcio = f" — {child.descripcio_router}" if child.descripcio_router else ""
                lines.append(f"- {child.codi}: {child.nom_primari}{descripcio}")
            lines.append("")

        return "\n".join(lines).rstrip("\n")

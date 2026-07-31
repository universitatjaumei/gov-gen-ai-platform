"""MetadataFilter (VIS.1) — contrato del filtro de recuperacion por metadatos.

Deploy: edge

Traduce la clasificacion del corpus (ambito, submateria, nivel de acceso, uso por
asistentes, version canonica, vigencia de la pagina de origen) a condiciones SQL sobre
`hub_documents`. Las tres estrategias de recuperacion —RAG, MD_LONG_CONTEXT y
MD_AGENT_SELECTOR— lo aplican con el mismo contrato.

Dos reglas del bloque VIS que este modulo hace cumplir:

1. **El filtro va en el WHERE**, antes del ORDER BY / LIMIT. Filtrar en Python despues
   del top_k hace que los documentos excluidos consuman plazas del resultado en vez de
   ser reemplazados.
2. **Fail-closed en el nivel de acceso**: si el nivel del actor no se puede determinar
   —None, cadena vacia, valor fuera del vocabulario— vale 'public'. No es una
   instruccion al modelo: es filtro de recuperacion (CRITERIS §1.4).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement, and_, or_, select

from server.app.modules.agents_hub.database.operational_models import (
    HubCrawledPage,
    HubDocument,
    HubDocumentChunk,
)
from server.app.modules.agents_hub.services.retrieval.vigencia import ESTAT_DEROGAT

# Orden de menos a mas restringido. Un actor de nivel N ve los documentos de nivel <= N.
NIVELLS_ACCES = ("public", "intern", "restringit")


@dataclass(frozen=True)
class MetadataFilter:
    """Subconjunto del corpus que un actor puede recuperar.

    `ambits` y `submateries` vacios significan «sin restringir por ese eje», no «ningun
    resultado»: quien no sabe el ambito recupera de todo el corpus al que tiene acceso.
    `max_nivell_acces` no funciona asi — su valor por defecto es el mas cerrado.
    """

    ambits: tuple[str, ...] = ()
    submateries: tuple[str, ...] = ()
    max_nivell_acces: str = "public"
    include_non_canonical: bool = False
    include_superseded: bool = False

    def __post_init__(self) -> None:
        # La normalizacion vive aqui y no en `for_actor` para que el fail-closed valga
        # sea cual sea la via de construccion.
        if self.max_nivell_acces not in NIVELLS_ACCES:
            object.__setattr__(self, "max_nivell_acces", "public")
        object.__setattr__(self, "ambits", tuple(self.ambits or ()))
        object.__setattr__(self, "submateries", tuple(self.submateries or ()))

    @classmethod
    def for_actor(cls, nivell_acces: str | None = None, **kwargs) -> "MetadataFilter":
        """Filtro para un actor cuyo nivel puede no conocerse todavia."""
        return cls(max_nivell_acces=nivell_acces, **kwargs)  # type: ignore[arg-type]

    @property
    def nivells_permesos(self) -> tuple[str, ...]:
        return NIVELLS_ACCES[: NIVELLS_ACCES.index(self.max_nivell_acces) + 1]

    def document_conditions(self) -> list[ColumnElement[bool]]:
        """Condiciones sobre `hub_documents`. Se combinan con AND."""
        conditions: list[ColumnElement[bool]] = [
            HubDocument.nivell_acces.in_(self.nivells_permesos),
            # Sin puerta trasera: 'no' significa que el documento no alimenta asistentes.
            HubDocument.us_assistents != "no",
        ]
        if self.ambits:
            conditions.append(
                or_(
                    HubDocument.ambit_principal.in_(self.ambits),
                    HubDocument.ambits_secundaris.overlap(list(self.ambits)),
                )
            )
        if self.submateries:
            conditions.append(
                or_(
                    HubDocument.submateries.overlap(list(self.submateries)),
                    HubDocument.submateries_internes.overlap(list(self.submateries)),
                )
            )
        if not self.include_non_canonical:
            conditions.append(HubDocument.canonica.is_(True))
        # Derogado no se recupera nunca, ni con el filtro mas abierto: no es una preferencia
        # de recuperacion sino un hecho sobre la norma (VIS.3). Sigue siendo legible por id
        # explicito con read_document, porque citar la norma que YA no rige es una consulta
        # legitima. Solo excluye 'derogat' exacto: el catalogo real trae 'vigent?' y otros
        # estados dudosos, que se advierten en la respuesta y no se ocultan.
        conditions.append(
            or_(
                HubDocument.estat_vigencia.is_(None),
                HubDocument.estat_vigencia != ESTAT_DEROGAT,
            )
        )
        if not self.include_superseded:
            # Subconsulta correlacionada en vez de un JOIN mas: el llamante solo tiene
            # que unir hub_documents, y esto vale igual en las tres estrategias.
            conditions.append(
                ~select(HubCrawledPage.id)
                .where(HubCrawledPage.id == HubDocument.crawled_page_id)
                .where(HubCrawledPage.superseded.is_(True))
                .exists()
            )
        return conditions

    def chunk_condition(self) -> ColumnElement[bool]:
        """Condicion para un SELECT sobre chunks con OUTER JOIN a `hub_documents`.

        Los chunks sin documento (subidas temporales del propio usuario y chunks
        legados) no se filtran por taxonomia: no tienen metadatos que consultar y ya
        estan acotados por `owner_id`.
        """
        return or_(
            HubDocumentChunk.document_id.is_(None),
            and_(*self.document_conditions()),
        )

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

from dataclasses import dataclass, replace

from sqlalchemy import ColumnElement, and_, or_, select
from sqlalchemy.orm import aliased

from server.app.modules.agents_hub.database.operational_models import (
    HubCrawledPage,
    HubDocument,
    HubDocumentChunk,
)
from server.app.modules.agents_hub.services.retrieval.vigencia import (
    ESTATS_DE_ARTICULO_QUE_NO_RIGEN,
    ESTATS_QUE_NO_RIGEN,
)

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
    include_superseded: bool = False
    #: Lengua de la pregunta, en el codigo del CORPUS (`val`, `es`...). ACT.3: decide cual de
    #: las dos versiones de una norma bilingue se recupera. `None` = sin regla de lengua, que
    #: es lo que significa `language_mode: none`.
    query_language: str | None = None

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
        # ACT.3 — UNA SOLA VERSION POR NORMA: LA DE LA LENGUA DE QUIEN PREGUNTA.
        #
        # Las dos versiones publicadas son OFICIALES: a l'UJI la norma s'aprova en valencia
        # (salvo algun reglament del Consell Social) i el Reglament de Politica Linguistica
        # manda traduir-ne algunes; la traduccio la publica Secretaria General o l'organ que
        # va dictar la resolucio. No hay jerarquia entre ellas, asi que el `canonica` que
        # excluia la castellana SIEMPRE —33 normas, 57 con el corpus del 27-08— se retiro: hacia
        # que preguntar en castellano devolviera el texto valenciano.
        #
        # La regla es: quedate con la version en la lengua de la pregunta; si esa norma no la
        # tiene, quedate con la que existe. Las dos ramas son EXCLUYENTES por construccion, asi
        # que nunca sobreviven las dos y no pueden citarse las dos.
        #
        # Va en el WHERE y no despues del top-k (regla 1 de este modulo): una version descartada
        # en Python ya ha consumido una plaza.
        #
        # «Hermana» se resuelve en los DOS sentidos: el corpus declara `versio_idiomatica_de` en
        # un solo lado y su direccion es un detalle de escritura, no una afirmacion de autoridad.
        if self.query_language:
            hermana = aliased(HubDocument)
            sin_hermana_en_esa_lengua = ~(
                select(hermana.id)
                .where(
                    or_(
                        hermana.id == HubDocument.versio_idiomatica_de,
                        hermana.versio_idiomatica_de == HubDocument.id,
                    ),
                    hermana.language == self.query_language,
                )
                .exists()
            )
            conditions.append(
                or_(HubDocument.language == self.query_language, sin_hermana_en_esa_lengua)
            )
        # ACT.4 — SOLO LO QUE RIGE HOY ENTRA EN LA BUSQUEDA.
        #
        # Antes se excluia `derogat` EXACTO, asi que `no_vigent` se recuperaba —con aviso— sin
        # que nadie lo hubiera decidido, y un documento SIN estado tambien. Con la lectura A
        # (2026-08-28) el estado es uno y la causa va aparte: una norma es `vigent`, `no_vigent`
        # o `futur`, y solo la primera contesta.
        #
        # Es una lista de EXCLUSION y no de admision, y la diferencia importa: un documento sin
        # `estat_vigencia` no es una norma que se haya dejado de aplicar, es un documento que no
        # tiene ese ciclo de vida —una pagina rastreada por el modulo de curacion, un PDF que
        # alguien sube para preguntarle cosas—. Exigir `= 'vigent'` los borraba del indice a
        # todos.
        #
        # `vigent?` y `parcialment_derogat` se quedan dentro: el primero es la duda del catalogo
        # original, que se ADVIERTE y no se oculta, y el segundo dice que una parte si rige.
        #
        # `no_vigent` y `futur` siguen siendo legibles por id con `read_document`: citar la
        # norma que YA no rige es una consulta legitima, y alguien preguntara que se aplicaba en
        # un ejercicio anterior. Lo resuelve el agentico leyendola, no el top-k.
        conditions.append(
            or_(
                HubDocument.estat_vigencia.is_(None),
                HubDocument.estat_vigencia.notin_(list(ESTATS_QUE_NO_RIGEN)),
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
        # ACT.4: un articulo suprimido o derogado DENTRO de una norma vigente no se cita como
        # vigente. El troceador ya escribia `estat` en el fragmento y nadie lo consumia, que es
        # lo que `vigencia.py` documentaba como pendiente. Son 3 fragmentos en Normativa hoy; el
        # coste es una condicion y el beneficio es que el mecanismo exista antes de que sean 300.
        #
        # `.desplacat` y `.transitori` NO se excluyen: esos articulos SI rigen, con matices, y lo
        # que necesitan es el aviso delante (lo pone `hidratar_avisos_de_vigencia`).
        articulo_en_vigor = or_(
            HubDocumentChunk.chunk_metadata["estat"].astext.is_(None),
            ~HubDocumentChunk.chunk_metadata["estat"].astext.in_(
                list(ESTATS_DE_ARTICULO_QUE_NO_RIGEN)
            ),
        )
        return and_(
            articulo_en_vigor,
            or_(
                HubDocumentChunk.document_id.is_(None),
                and_(*self.document_conditions()),
            ),
        )


def con_lengua(filtro: MetadataFilter, language: str | None) -> MetadataFilter:
    """El mismo filtro, acotado a la lengua de ESTA pregunta.

    El `MetadataFilter` se construye una vez, con el actor, cuando todavia no se sabe en que
    lengua se va a preguntar; la lengua es de cada consulta. Por eso se copia en vez de
    guardarse: el filtro es inmutable a proposito, y mutarlo lo compartiria entre consultas.
    """
    if not language:
        return filtro
    return replace(filtro, query_language=language)

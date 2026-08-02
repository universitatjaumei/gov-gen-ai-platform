"""Reconciliador de corpus curado (ING.0.5). Deploy: edge.

**Una sola implementación de la reconciliación, dos fuentes** (`CorpusSource`): la carpeta
local de hoy y el servicio MCP que añade SYNC.1. Si SYNC.1 reimplementa emparejamiento,
deltas o poda, está mal.

Dos ideas gobiernan el módulo:

- **Lo incremental no es un modo: emerge del hash.** El mismo comando sobre la misma
  carpeta omite lo no cambiado, actualiza metadatos sin re-trocear y re-ingiere solo lo
  modificado.
- **El censo sí es un modo, y es peligroso.** Detectar una retirada exige saber que la
  fuente es el corpus COMPLETO; un `--prune` sobre una subcarpeta retiraría cientos de
  normas. De ahí que la poda exija `is_census()`, sea opt-in y lleve salvaguarda de
  proporción. Y **nunca borra**: marca, porque retirada de la fuente ≠ derogación y esa
  distinción la hace una persona.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.operational_models import (
    HubDocument,
    HubIngestionJob,
)
from server.app.modules.agents_hub.ingestion.bilingual_bridge import (
    refrescar_puente_bilingue,
)
from server.app.modules.agents_hub.ingestion.corpus.frontmatter import hash_markdown_body
from server.app.modules.agents_hub.ingestion.corpus.manifest import CorpusDocumentEntry
from server.app.modules.agents_hub.ingestion.corpus.source import CorpusSource

MOTIU_RETIRADA = "retirada_de_la_font"
UMBRAL_PODA_POR_DEFECTO = 0.10
# SYNC.2: cuánto vale una revisión cuando el front-matter no dice otra cosa. Las normas de
# vigencia anual —el Presupuesto— traen la suya, explícita y más corta.
DIAS_REVISION_POR_DEFECTO = 365

# Campos de la entrada que se materializan como columna en HubDocument (ING.0.2).
_COLUMNAS = (
    "content_class",
    "ambit_principal",
    "nivell_acces",
    "us_assistents",
    "canonica",
    "estat_vigencia",
    "revisat_per",
    "revisat_el",
    "vigencia_validada_el",
    "data_revisio_prevista",
    "id_publicacio",
)
_COLUMNAS_ARRAY = ("ambits_secundaris", "submateries", "submateries_internes")
# Campos de la entrada que van a doc_metadata y no a columna.
_A_METADATA = (
    "motiu_exclusio",
    "vigencia_validada_per",
    "original_pdf_sha256",
    "converter",
)


class PruneThresholdExceeded(Exception):
    """La poda afectaría a más documentos de los que el umbral permite sin confirmar."""


@dataclass
class ReconcileReport:
    ingeridos: int = 0
    reingeridos: int = 0
    metadatos_actualizados: int = 0
    omitidos: int = 0
    rechazados: int = 0
    retirados: int = 0
    poda_omitida_por_no_censo: bool = False
    motivos_omision: list[str] = field(default_factory=list)
    detalle: list[str] = field(default_factory=list)

    def render(self) -> str:
        return (
            f"ingeridos={self.ingeridos} reingeridos={self.reingeridos} "
            f"metadatos={self.metadatos_actualizados} omitidos={self.omitidos} "
            f"rechazados={self.rechazados} retirados={self.retirados}"
        )


def _metadata_objetivo(entry: CorpusDocumentEntry) -> dict:
    """`doc_metadata` que le corresponde a la entrada: `extra` + los campos no-columna."""
    salida = dict(entry.extra)
    for campo in _A_METADATA:
        valor = getattr(entry, campo, None)
        if valor is not None:
            salida[campo] = valor.isoformat() if hasattr(valor, "isoformat") else valor
    return salida


def _difiere(doc: HubDocument, entry: CorpusDocumentEntry, title: str) -> bool:
    if doc.title != title:
        return True
    for campo in _COLUMNAS:
        # SYNC.2: si la fuente no declara fecha de revisión, no puede estar en desacuerdo
        # con la que el documento ya tiene. Sin esta excepción, el default que se pone al
        # ingerir haría que cada pasada viera una diferencia, la «corrigiera» renovando la
        # fecha y nada venciera jamás.
        if campo == "data_revisio_prevista" and entry.data_revisio_prevista is None:
            continue
        if getattr(doc, campo) != getattr(entry, campo):
            return True
    for campo in _COLUMNAS_ARRAY:
        if list(getattr(doc, campo) or []) != list(getattr(entry, campo) or []):
            return True
    return (doc.doc_metadata or {}) != _metadata_objetivo(entry)


def _aplicar(doc: HubDocument, entry: CorpusDocumentEntry, title: str) -> None:
    doc.title = title
    for campo in _COLUMNAS:
        setattr(doc, campo, getattr(entry, campo))
    # SYNC.2: sin fecha de revisión no hay caducidad posible y el documento envejecería en
    # silencio, que es el riesgo nº1 del informe (312 de 314 fichas dicen «vigent?»). Se
    # rellena solo si no hay ninguna: renovarla en cada pasada equivaldría a no tenerla.
    if entry.data_revisio_prevista is None:
        doc.data_revisio_prevista = doc.data_revisio_prevista or (
            date.today() + timedelta(days=DIAS_REVISION_POR_DEFECTO)
        )
    for campo in _COLUMNAS_ARRAY:
        setattr(doc, campo, list(getattr(entry, campo) or []))
    doc.doc_metadata = _metadata_objetivo(entry)
    doc.source_kind = entry.extra.get("source_kind", "publicacio")


class CorpusReconciler:
    """Reconcilia una fuente de corpus contra los documentos de un chatbot."""

    def __init__(self, session: AsyncSession, watcher) -> None:
        self._session = session
        self._watcher = watcher

    async def _buscar(
        self, chatbot_id: uuid.UUID, entry: CorpusDocumentEntry, url: str
    ) -> HubDocument | None:
        """Empareja por `id_publicacio`; si no viene, por url oficial + idioma."""
        if entry.id_publicacio:
            stmt = select(HubDocument).where(
                HubDocument.chatbot_id == chatbot_id,
                HubDocument.id_publicacio == entry.id_publicacio,
            )
        else:
            stmt = select(HubDocument).where(
                HubDocument.chatbot_id == chatbot_id,
                HubDocument.canonical_url == url,
                HubDocument.language == entry.language,
            )
        return (await self._session.execute(stmt.limit(1))).scalar_one_or_none()

    async def reconcile(
        self,
        source: CorpusSource,
        chatbot_id: uuid.UUID,
        dry_run: bool = False,
        prune: bool = False,
        force_prune: bool = False,
        prune_threshold: float = UMBRAL_PODA_POR_DEFECTO,
    ) -> ReconcileReport:
        informe = ReconcileReport()

        # list_entries() valida el paquete y aborta ENTERO si algo no cumple el contrato:
        # un corpus a medias hace fallar la validación de documentos de forma aleatoria.
        entradas = await source.list_entries()

        # Los emparejados se llevan en memoria y NO se deducen de last_seen_at: en
        # --dry-run no se estampa nada, y una poda que dependiera del sello creería que
        # no se ha visto ningún documento y propondría retirar el corpus entero.
        emparejados: set[uuid.UUID] = set()
        pendientes_de_enlazar: list[tuple[HubDocument, str]] = []

        for entry in entradas:
            url = entry.source_url
            title = entry.title or entry.relative_path

            if entry.us_assistents == "no":
                informe.omitidos += 1
                informe.motivos_omision.append(
                    f"{entry.relative_path}: us_assistents=no ({entry.motiu_exclusio})"
                )
                continue

            existente = await self._buscar(chatbot_id, entry, url)

            # SYNC.1: si la fuente sabe declarar el hash del cuerpo sin entregarlo —el
            # índice del servicio de publicación lo trae— y coincide con el que ya está
            # guardado, no hay nada que descargar. Es lo que hace que una pasada cueste en
            # proporción a los cambios y no al tamaño del corpus: sin esto, cada sync
            # bajaría los ~10 MB del corpus entero para descubrir que no ha cambiado nada.
            #
            # El atajo es seguro porque compara el hash declarado contra el NUESTRO, que se
            # calculó con `hash_markdown_body`. Un publicador que hashee de otra forma
            # simplemente no acierta nunca: se descarga el cuerpo y se decide con el hash
            # real. Se pierde el ahorro, no la corrección.
            if (
                existente is not None
                and entry.content_hash is not None
                and existente.content_hash == entry.content_hash
            ):
                body, content_hash = None, existente.content_hash
            else:
                body = await source.read_body(entry)
                content_hash = hash_markdown_body(body)

            if existente is None:
                informe.ingeridos += 1
                informe.detalle.append(f"+ {entry.relative_path}")
                if not dry_run:
                    doc = await self._ingerir(entry, chatbot_id, body, title, url)
                    emparejados.add(doc.id)
                    if entry.versio_idiomatica_de:
                        pendientes_de_enlazar.append((doc, entry.versio_idiomatica_de))
                continue

            emparejados.add(existente.id)

            if body is not None and existente.content_hash != content_hash:
                informe.reingeridos += 1
                informe.detalle.append(f"~ {entry.relative_path} (contenido)")
                if not dry_run:
                    doc = await self._ingerir(entry, chatbot_id, body, title, url)
                    emparejados.add(doc.id)
                    if entry.versio_idiomatica_de:
                        pendientes_de_enlazar.append((doc, entry.versio_idiomatica_de))
                continue

            # Hash igual: o solo metadatos, o nada. En ninguno de los dos casos se
            # vuelve a trocear ni a embeber — es el invariante de CLAUDE.md §5.
            if _difiere(existente, entry, title):
                informe.metadatos_actualizados += 1
                informe.detalle.append(f"= {entry.relative_path} (metadatos)")
                if not dry_run:
                    _aplicar(existente, entry, title)
                    # El puente bilingüe vive denormalizado en los chunks (RAG.4). Aquí es
                    # donde se ve que reetiquetar cuesta un UPDATE: ni se trocea ni se
                    # embebe de nuevo.
                    await refrescar_puente_bilingue(self._session, existente)
            else:
                informe.omitidos += 1

            if not dry_run:
                existente.last_seen_at = datetime.now(timezone.utc)
                emparejados.add(existente.id)
                if entry.versio_idiomatica_de:
                    pendientes_de_enlazar.append((existente, entry.versio_idiomatica_de))

        if not dry_run:
            await self._session.flush()
            await self._enlazar_versiones(chatbot_id, pendientes_de_enlazar)

        if prune:
            await self._podar(
                chatbot_id, emparejados, informe, dry_run, force_prune,
                prune_threshold, source,
            )

        if not dry_run:
            self._session.add(
                HubIngestionJob(
                    chatbot_id=chatbot_id,
                    status="completed",
                    source_url=f"corpus:{informe.render()}",
                    chunks_processed=informe.ingeridos + informe.reingeridos,
                    error_message=informe.render(),
                )
            )
            await self._session.flush()

        return informe

    async def _ingerir(
        self,
        entry: CorpusDocumentEntry,
        chatbot_id: uuid.UUID,
        body: str,
        title: str,
        url: str,
    ) -> HubDocument:
        """Passthrough: el cuerpo ya viene sin front-matter y NO se llama a Docling."""
        doc, _ = await self._watcher.process_source(
            source_url=url,
            chatbot_id=chatbot_id,
            language=entry.language,
            citation_url=url,
            prefetched_content=body,
            title=title,
        )
        # Los metadatos se aplican aquí y no en el watcher: el watcher es la tubería
        # compartida con el crawler y no tiene por qué conocer el contrato del corpus.
        _aplicar(doc, entry, title)
        # Y por eso mismo hay que refrescar el puente bilingüe después: al trocear, el
        # documento todavía no tenía `termes_bilingues`, así que los chunks nacieron sin él.
        await self._session.flush()
        await refrescar_puente_bilingue(self._session, doc)
        doc.last_seen_at = datetime.now(timezone.utc)
        return doc

    async def _enlazar_versiones(
        self, chatbot_id: uuid.UUID, pendientes: list[tuple[HubDocument, str]]
    ) -> None:
        """Resuelve `versio_idiomatica_de` de referencia (id_publicacio) a UUID."""
        if not pendientes:
            return
        referencias = {ref for _, ref in pendientes}
        filas = await self._session.execute(
            select(HubDocument).where(
                HubDocument.chatbot_id == chatbot_id,
                HubDocument.id_publicacio.in_(referencias),
            )
        )
        por_id = {d.id_publicacio: d.id for d in filas.scalars().all()}
        for doc, ref in pendientes:
            destino = por_id.get(ref)
            if destino and destino != doc.id:
                doc.versio_idiomatica_de = destino
        await self._session.flush()

    async def _podar(
        self,
        chatbot_id: uuid.UUID,
        emparejados: set[uuid.UUID],
        informe: ReconcileReport,
        dry_run: bool,
        force_prune: bool,
        umbral: float,
        source: CorpusSource,
    ) -> None:
        if not source.is_census():
            # Un delta no puede distinguir «retirada» de «no tocada».
            informe.poda_omitida_por_no_censo = True
            return

        todos = (
            await self._session.execute(
                select(HubDocument).where(HubDocument.chatbot_id == chatbot_id)
            )
        ).scalars().all()
        candidatos = [
            d for d in todos if d.us_assistents != "no" and d.id not in emparejados
        ]
        if not candidatos:
            return

        if not force_prune and len(candidatos) > umbral * max(1, len(todos)):
            raise PruneThresholdExceeded(
                f"La poda afectaria a {len(candidatos)} de {len(todos)} documentos "
                f"({len(candidatos) / len(todos):.0%}), por encima del umbral "
                f"({umbral:.0%}). Si es correcto, repite con --force-prune. Si no lo es, "
                "revisa que --dir apunte al corpus completo."
            )

        informe.retirados = len(candidatos)
        for doc in candidatos:
            informe.detalle.append(f"- {doc.id_publicacio or doc.canonical_url} (retirado)")
            if dry_run:
                continue
            # NUNCA se borra: retirada de la fuente ≠ derogación.
            doc.us_assistents = "no"
            doc.doc_metadata = {**(doc.doc_metadata or {}), "motiu_exclusio": MOTIU_RETIRADA}
        if not dry_run:
            await self._session.flush()

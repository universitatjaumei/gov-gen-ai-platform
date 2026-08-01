"""Puente léxico bilingüe del corpus (RAG.4). Deploy: edge.

El BM25 cross-lingüe no sirve aquí: `despesa` y `gasto` no comparten una letra, así que
ninguna medida de similitud de cadenas las acerca. El informe de materias §6.2 propone pares
bilingües del dominio como puente, y su sitio es el `tsvector` —que se regenera con una
sentencia SQL— y **nunca** el texto embebido, que costaría GPU y horas por cada revisión.

Los términos se denormalizan al chunk (`hub_document_chunks.bilingual_terms`) porque la
columna generada `tsv` solo puede referirse a su propia fila. Esa denormalización es segura
mientras refrescarla siga costando un UPDATE, que es lo que hace `refrescar_puente_bilingue`.

**Por qué existe este módulo y no está en el watcher**: el reconciliador de corpus aplica los
metadatos del front-matter DESPUÉS de llamar al watcher (es deliberado: el watcher es la
tubería compartida con el crawler y no conoce el contrato del corpus). Si el puente solo se
escribiera al trocear, un documento recién ingerido se quedaría sin él —y la búsqueda no
fallaría: dejaría de encontrar `despesa` en silencio, que es la peor forma de fallar—.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.modules.agents_hub.database.operational_models import HubDocumentChunk

CLAVE_METADATO = "termes_bilingues"


def terminos_bilingues(documento: Any) -> str | None:
    """Pares del documento aplanados para el `tsvector`, o None si no declara ninguno.

    `despesa/gasto` entra como dos palabras sueltas: la barra no es un separador que el
    parser de full-text entienda, y lo que hace de puente es que ambas formas queden
    indexadas.
    """
    pares = (getattr(documento, "doc_metadata", None) or {}).get(CLAVE_METADATO)
    if not isinstance(pares, list):
        return None
    palabras = " ".join(str(p).replace("/", " ") for p in pares).strip()
    return palabras or None


async def refrescar_puente_bilingue(session: AsyncSession, documento: Any) -> None:
    """Propaga los pares del documento a sus chunks. Un UPDATE, sin re-trocear ni re-embeber.

    Es el invariante de CLAUDE.md §5 aplicado al puente léxico: cambiar los términos de un
    documento no puede costar una reingesta. La columna `tsv` es generada, así que Postgres
    la recalcula sola con este UPDATE.
    """
    if documento.id is None:
        return
    await session.execute(
        update(HubDocumentChunk)
        .where(HubDocumentChunk.document_id == documento.id)
        .values(bilingual_terms=terminos_bilingues(documento))
    )

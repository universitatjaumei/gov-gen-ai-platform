"""Expansión léxica: del par aprobado al `tsvector`, y de vuelta (RES.3).

Deploy: edge — escribe sobre los trozos del corpus, que son datos del cliente.

**La propiedad que sostiene todo esto es que `bilingual_terms` es DERIVADO.** Se calcula sólo a
partir de los pares aprobados y `proyectar_lexico` lo reconstruye entero, así que quitar un término
cuesta exactamente lo mismo que ponerlo. Sin eso, en seis meses nadie sabe de dónde salió un
término ni cómo sacarlo, y «reclasificar» —que el contrato del proyecto exige que cueste un
`UPDATE`— vuelve a ser «reindexar».

Y no hace falta recalcular ningún embedding: `HubDocumentChunk.tsv` es una columna **generada**
sobre `content || ' ' || bilingual_terms`, así que el índice GIN se regenera solo al escribir. El
léxico **nunca** entra en `embedding_text`; eso es regla dura del proyecto y aquí se respeta por
construcción, porque esta función no toca esa columna.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update

from server.app.modules.agents_hub.database.config_models import HubLexiconPair
from server.app.modules.agents_hub.database.operational_models import HubDocumentChunk


async def proponer_par(
    session,
    *,
    organizacion_id: uuid.UUID,
    document_id: uuid.UUID,
    termino_de_usuario: str,
    termino_normativo: str,
    origen: str = "reformulacion",
) -> HubLexiconPair:
    """Registra un candidato. **No lo aplica**: eso lo decide una persona.

    Si el par ya existía se devuelve el que hay, sin resucitar un rechazo: que la misma consulta
    vuelva a fallar no es un argumento nuevo, y reproponer lo ya descartado convertiría la
    pantalla de revisión en una cinta sin fin.
    """
    existente = (
        await session.execute(
            select(HubLexiconPair).where(
                HubLexiconPair.organizacion_id == organizacion_id,
                HubLexiconPair.document_id == document_id,
                HubLexiconPair.termino_de_usuario == termino_de_usuario,
            )
        )
    ).scalar_one_or_none()
    if existente is not None:
        return existente

    par = HubLexiconPair(
        organizacion_id=organizacion_id,
        document_id=document_id,
        termino_de_usuario=termino_de_usuario,
        termino_normativo=termino_normativo,
        origen=origen,
        estado="propuesto",
    )
    session.add(par)
    await session.commit()
    await session.refresh(par)
    return par


async def aprobar_par(session, par_id: uuid.UUID, *, revisado_por: str) -> HubLexiconPair:
    return await _resolver(session, par_id, "aprobado", revisado_por)


async def rechazar_par(session, par_id: uuid.UUID, *, revisado_por: str) -> HubLexiconPair:
    return await _resolver(session, par_id, "rechazado", revisado_por)


async def _resolver(session, par_id: uuid.UUID, estado: str, revisado_por: str):
    par = await session.get(HubLexiconPair, par_id)
    if par is None:
        raise ValueError(f"Par léxico {par_id} no encontrado")
    par.estado = estado
    par.revisado_por = revisado_por
    par.revisado_el = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(par)
    return par


async def proyectar_lexico(session, *, organizacion_id: uuid.UUID) -> int:
    """Reescribe `bilingual_terms` de los documentos de una organización desde cero.

    Devuelve cuántos trozos quedaron con términos. Es idempotente y **reconstruye**: primero
    vacía lo que hubiera —incluido lo que alguien escribiera a mano, que no debería existir— y
    después escribe lo que dicen los pares aprobados y vigentes. Ése es el punto: la tabla es la
    única fuente, así que la proyección se puede tirar y volver a hacer sin perder nada.
    """
    pares = (
        (
            await session.execute(
                select(HubLexiconPair).where(
                    HubLexiconPair.organizacion_id == organizacion_id,
                    HubLexiconPair.estado == "aprobado",
                    HubLexiconPair.vigent.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )

    # Los documentos alcanzados son los de los pares —aprobados o no— para que vaciar también
    # llegue a un documento cuyo único par acaba de rechazarse. Con sólo los aprobados, un
    # rechazo dejaría el término escrito para siempre.
    todos = (
        (
            await session.execute(
                select(HubLexiconPair.document_id).where(
                    HubLexiconPair.organizacion_id == organizacion_id
                )
            )
        )
        .scalars()
        .all()
    )
    documentos = set(todos)
    if not documentos:
        return 0

    await session.execute(
        update(HubDocumentChunk)
        .where(HubDocumentChunk.document_id.in_(documentos))
        .values(bilingual_terms=None)
    )

    por_documento: dict[uuid.UUID, list[str]] = {}
    for par in pares:
        por_documento.setdefault(par.document_id, []).append(par.termino_de_usuario)

    tocados = 0
    for document_id, terminos in por_documento.items():
        # Orden estable: la proyección tiene que dar el mismo texto en cada regeneración, o el
        # test que compara dos pasadas seguidas fallaría por el orden del `SELECT`.
        texto = " ".join(sorted(set(terminos)))
        resultado = await session.execute(
            update(HubDocumentChunk)
            .where(HubDocumentChunk.document_id == document_id)
            .values(bilingual_terms=texto)
        )
        tocados += resultado.rowcount or 0

    await session.commit()
    return tocados


async def cosechar_de_las_ejecuciones(
    session, *, organizacion_id: uuid.UUID, chatbot_id: uuid.UUID
) -> list[HubLexiconPair]:
    """Propone pares a partir de las respuestas que se rescataron reformulando.

    **Aquí está el giro que distingue esto del intento de los lotes en Excel.** Aquel método pedía
    a los servicios inventar pares en frío, que es trabajo cognitivo alto y sin recompensa visible.
    Esto no inventa nada: cada `HubTestRun` con `reformulada` recuerda la consulta original y la que
    sí funcionó, y esa segunda viene validada por el hecho de haber encontrado el documento. A la
    persona sólo se le pide aprobar o rechazar, que es lo que hizo funcionar la curación del corpus.

    El documento al que se ancla el par es **el primero que se citó**, que es el que la consulta
    reformulada encontró. Si la respuesta no citó nada, no hay par que proponer: sin documento la
    proyección no sabría dónde escribir.
    """
    from server.app.modules.agents_hub.database.operational_models import (
        HubTestRun,
        HubTestScenario,
    )

    filas = (
        (
            await session.execute(
                select(HubTestRun, HubTestScenario)
                .join(HubTestScenario, HubTestScenario.id == HubTestRun.scenario_id)
                .where(
                    HubTestScenario.chatbot_id == chatbot_id,
                    HubTestRun.reformulada.is_(True),
                )
            )
        )
        .all()
    )

    propuestos = []
    for ejecucion, escenario in filas:
        document_id = _documento_citado(ejecucion.sources)
        if document_id is None or not ejecucion.reformulated_query:
            continue
        propuestos.append(
            await proponer_par(
                session,
                organizacion_id=organizacion_id,
                document_id=document_id,
                termino_de_usuario=escenario.prompt,
                termino_normativo=ejecucion.reformulated_query,
                origen="reformulacion",
            )
        )
    return propuestos


def _documento_citado(fuentes) -> uuid.UUID | None:
    for fuente in fuentes or []:
        crudo = (fuente or {}).get("document_id") if isinstance(fuente, dict) else None
        if not crudo:
            continue
        try:
            return uuid.UUID(str(crudo))
        except (TypeError, ValueError):
            continue
    return None

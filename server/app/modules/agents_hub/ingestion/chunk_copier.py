"""HIB.N — copiar los fragmentos ya embebidos de un chatbot a su gemelo, o negarse.

**Por qué copiar.** El corpus **no se comparte** entre chatbots: cada uno tiene sus documentos y
sus fragmentos, y eso es una decisión tomada, no un descuido. Pero cuando dos chatbots tienen el
mismo documento —mismo `content_hash`— el vector del fragmento es el mismo, y volver a
embeberlo cuesta GPU y horas para obtener el mismo número. Medido el 2026-08-27: **los 124
documentos de Gerencia tienen gemelo exacto en Normativa**, así que su corpus entero se puede
trocear a coste cero de embeddings.

**Por qué el permiso es empírico y no de configuración.** La tentación es comparar la
configuración de los dos chatbots —estrategia de troceado y techo del padre— y copiar si
coincide. No sirve: **la configuración deriva de los datos**. Los fragmentos de Normativa se
crearon antes de que HIB.L fijara el techo en 8.000 tokens, así que su configuración dice 8.000
y sus datos tienen padres de 59.172. Comparar configuraciones habría dado luz verde y metido en
el destino padres que su propio techo prohíbe.

Aquí se comprueba **lo que hay dentro de los fragmentos**: que ninguno traiga un padre por
encima del techo del destino, y que la forma del padre —presente o ausente— case con la
estrategia. Es la diferencia entre preguntar qué se pretendía y mirar qué se hizo.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class Veredicto:
    """Si los fragmentos de un documento se pueden copiar, y si no, por qué no.

    El motivo es texto y no un código: quien lanza la copia necesita saber si el arreglo es
    aplicar el techo, re-trocear o nada, y un enumerado obliga a mirar la tabla.
    """

    copiable: bool
    motivo: str | None = None


def _tokens(texto: str | None) -> int:
    """Estimación por caracteres, la misma que usa el troceador (`len // 4`).

    Tiene que ser la misma o el techo significaría una cosa al trocear y otra al copiar, y el
    desacuerdo aparecería justo en los fragmentos del límite.
    """
    return len(texto or "") // 4


def se_puede_copiar(
    *,
    hash_origen: str | None,
    hash_destino: str | None,
    estrategia_destino: str,
    techo_destino: int,
    fragmentos: list[dict],
) -> Veredicto:
    """Las tres condiciones del prompt HIB.N, comprobadas sobre los datos.

    `fragmentos` son los del documento de ORIGEN, cada uno con al menos `parent_content`.
    """
    if not hash_origen or not hash_destino:
        return Veredicto(False, "falta el content_hash de uno de los dos documentos")
    if hash_origen != hash_destino:
        return Veredicto(False, "el content_hash difiere: no son el mismo documento")
    if not fragmentos:
        return Veredicto(False, "el documento de origen no tiene fragmentos que copiar")

    con_padre = sum(1 for f in fragmentos if (f.get("parent_content") or "").strip())
    if estrategia_destino == "parent_child" and con_padre == 0:
        return Veredicto(
            False,
            "el destino trocea con `parent_child` y el origen no guarda ningun padre: "
            "copiarlos dejaria el small-to-big sin la seccion entera",
        )
    if estrategia_destino == "structural" and con_padre:
        return Veredicto(
            False,
            "el destino trocea con `structural` y el origen trae padres: copiarlos cambiaria "
            "la evidencia que se le entrega al modelo sin que nadie lo haya decidido",
        )

    excedidos = [f for f in fragmentos if _tokens(f.get("parent_content")) > techo_destino]
    if excedidos:
        mayor = max(_tokens(f.get("parent_content")) for f in excedidos)
        return Veredicto(
            False,
            f"{len(excedidos)} de {len(fragmentos)} fragmentos traen un padre por encima del "
            f"techo del destino ({techo_destino} tokens; el mayor, {mayor}). El origen se "
            f"troceo antes de que se fijara ese techo: hay que aplicarlo alli primero — es un "
            f"UPDATE, porque `parent_content` no entra en el embedding",
        )
    return Veredicto(True)


def remapea(
    fragmento: dict, *, chatbot_id: uuid.UUID, document_id: uuid.UUID
) -> dict:
    """El fragmento con los tres identificadores del destino.

    **Los tres, y el tercero es el que se olvida.** `chunk_metadata["document_id"]` es el que
    usa la agrupacion por documento del retrieval (`VectorRetrievalStrategy`), que agrupa por
    el metadato y no por la columna. Copiar sin remapearlo deja fragmentos que apuntan al
    documento del chatbot de origen: la agrupacion los junta con los del otro corpus, la cita
    sale con el titulo equivocado y **no salta ningun error**.
    """
    metadatos = dict(fragmento.get("chunk_metadata") or {})
    metadatos["document_id"] = str(document_id)
    return {
        **fragmento,
        "chatbot_id": chatbot_id,
        "document_id": document_id,
        "chunk_metadata": metadatos,
    }


def incoherentes(fragmentos: list[dict]) -> list[dict]:
    """Los fragmentos cuya columna `document_id` no coincide con su metadato.

    Es la consulta de verificación del criterio de done de HIB.N, expresada aquí para que
    pueda comprobarse en un test y no sólo a mano contra la base.
    """
    fuera = []
    for f in fragmentos:
        del_metadato = (f.get("chunk_metadata") or {}).get("document_id")
        if str(f.get("document_id")) != str(del_metadato):
            fuera.append(f)
    return fuera

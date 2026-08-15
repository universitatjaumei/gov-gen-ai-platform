"""Advertencia de vigencia no validada (VIS.3). Deploy: edge.

El riesgo nº1 del corpus, medido en `INFORME_MATERIES_I_METADADES_AGENTS.md`: **312 de 314
fichas declaran «vigent?»**. Citar una de ellas sin decirlo es afirmar como vigente algo que
nadie ha comprobado.

Por qué el aviso no vive en el system prompt: una instruccion al modelo se cumple casi
siempre, y «casi siempre» no es una garantia cuando lo que esta en juego es si una norma
rige. El flag lo pone la capa de recuperacion —que es la que ve el dato— y el texto lo
anade el CoreGraph despues de generar la respuesta.

Un documento necesita aviso si NO ha pasado revision humana de vigencia
(`vigencia_validada_el IS NULL`) o si su estado no es exactamente 'vigent'. El catalogo real
trae valores como 'vigent?', que es precisamente el caso que hay que advertir.
"""
from __future__ import annotations

from typing import Any

ESTAT_VIGENT = "vigent"
ESTAT_DEROGAT = "derogat"

AVISO_VIGENCIA_NO_VALIDADA = (
    "Aviso: la vigencia de la normativa citada no esta validada, asi que puede haber sido "
    "modificada o derogada. Confirmalo en la fuente oficial antes de actuar."
)

CLAVE_METADATO = "vigencia_no_validada"


def vigencia_no_validada(
    estat_vigencia: str | None,
    vigencia_validada_el: Any | None,
) -> bool:
    """True si el documento no puede presentarse como vigente sin advertirlo."""
    if vigencia_validada_el is None:
        return True
    return estat_vigencia != ESTAT_VIGENT


def marca_de_vigencia(documento: Any) -> dict[str, bool]:
    """Metadato listo para incrustar en un `Source` o un `EvidenceItem`."""
    return {
        CLAVE_METADATO: vigencia_no_validada(
            getattr(documento, "estat_vigencia", None),
            getattr(documento, "vigencia_validada_el", None),
        )
    }


CLASE_DESPLACAT = "desplacat"


def _entrada_de_desplazamiento(documento: Any, ancora: str | None) -> dict | None:
    """La entrada de `desplacat_per` que corresponde a esta ancla, si la hay."""
    if documento is None or not ancora:
        return None
    metadatos = getattr(documento, "doc_metadata", None) or {}
    for entrada in metadatos.get("desplacat_per") or ():
        if isinstance(entrada, dict) and entrada.get("ancora") == ancora:
            return entrada
    return None


def aviso_de_desplazamiento(entrada: dict) -> str:
    """Redacta el aviso a partir de lo que declara el corpus. No añade juicio propio."""
    quien = entrada.get("desplacat_per") or {}
    partes = [
        "AVISO DE VIGENCIA: el texto de este articulo sigue aprobado y sin modificar, pero "
        "su contenido esta DESPLAZADO por una norma posterior, asi que no se aplica tal "
        "como se lee."
    ]
    apartado = entrada.get("apartat_afectat")
    if apartado:
        partes.append(f"Apartado afectado: {apartado}.")

    norma = quien.get("norma") or quien.get("id_norma")
    if norma:
        referencia = f"Lo desplaza: {norma}"
        if quien.get("ancora"):
            referencia += f" ({quien['ancora']}"
            if quien.get("apartat"):
                referencia += f", apartado {quien['apartat']}"
            referencia += ")"
        if quien.get("data"):
            referencia += f", de {quien['data']}"
        partes.append(referencia + ".")

    if entrada.get("motiu"):
        partes.append(f"Motivo: {entrada['motiu']}")
    return " ".join(partes)


def hidratar_desplazamiento(
    texto: str, documento: Any, metadatos_del_fragmento: dict | None
) -> str:
    """Antepone el aviso de desplazamiento al texto del fragmento, si le corresponde.

    **Por qué aquí y no en el troceado** (las tres alternativas se evaluaron):

    - La nota `::: nota-vigencia` del corpus cae en UNO de los trozos del artículo. Hidratar
      al montar la evidencia no depende de dónde cayó; las demás soluciones sí.
    - La nota vive en un solo sitio. Reescribirla no obliga a reindexar 290 fragmentos.
    - Propagarla al trocear metería 400-700 caracteres en cada trozo, **y esos caracteres
      entrarían al embedding**: cambiaría el vector de todo artículo desplazado.
    - `parent_child` sólo ayudaría si la respuesta se hace con el padre, y cambiaría el
      troceado de todo el corpus para resolver el caso de 45 documentos.

    Lo que NO resuelve nada, y por eso no se hizo: añadir `desplacat` a
    `ESTADOS_CONSOLIDACION`. Saber el estado no es mostrar el aviso, y hoy nadie consume
    `estat`.
    """
    metadatos = metadatos_del_fragmento or {}
    if CLASE_DESPLACAT not in (metadatos.get("classes") or ()):
        return texto
    entrada = _entrada_de_desplazamiento(documento, metadatos.get("ancora"))
    if entrada is None:
        return texto
    return f"{aviso_de_desplazamiento(entrada)}\n\n{texto}"


def aviso_para(items: list[Any]) -> str | None:
    """Bloque de aviso para la respuesta, o None si no hay nada que advertir.

    Nombra los documentos afectados: un aviso genérico no dice de qué norma se duda, y el
    usuario necesita saber cuál de las citas tiene que confirmar.
    """
    afectados = [
        (getattr(i, "title", None) or getattr(i, "source_id", "?"))
        for i in items
        if (getattr(i, "metadata", None) or {}).get(CLAVE_METADATO)
    ]
    if not afectados:
        return None
    unicos = list(dict.fromkeys(afectados))
    return f"---\n{AVISO_VIGENCIA_NO_VALIDADA}\nDocumentos afectados: {', '.join(unicos)}."

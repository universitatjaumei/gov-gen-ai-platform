"""HIB.S — ¿lo que la respuesta cita sostiene lo que la respuesta afirma?

**Por qué existe.** El contrato de citas de HIB.0 pregunta «¿ha citado algo del conjunto
recuperado?». Es una pregunta buena —sobre el lote de 48 escenarios de Normativa rechazó 7 de los
18 negativos **sin un solo rechazo indebido** sobre 30 contestables, mientras la puerta de calidad
rechazaba cero de 48— pero se queda corta: los 11 negativos que el asistente contesta y no
debería **citan**. Citan normas de la UJI que hablan de contratos para una pregunta de contratos.

Y no hay atajo por el lado de la recuperación. Se midieron cuatro señales y ninguna separa los 11
de los 30: la nota de calidad (0,643-0,787 contra 0,692-0,805, con los fallos de mediana **más
alta**), la brecha entre el primero y el segundo (0,020 contra 0,010, al revés de lo que
convendría), el número de fuentes (3 y 3) y «la mejor evidencia es un documento vetado» (gana en 2
de 8 negativos y en 1 de 6 contestables). La similitud mide parecido, no «este documento contesta
la pregunta».

Así que la comprobación tiene que ser semántica y con el fragmento delante. Este módulo la hace, y
**no decide sola**: devuelve un veredicto que el nodo del grafo usa según su configuración.

**Las tres decisiones de criterio, que son lo que separa esto de una fábrica de rendiciones.**

1. **Se descarta cuando NO sobrevive ninguna afirmación fundamentada**, no cuando falla una. Una
   respuesta con ocho afirmaciones y siete sostenidas es utilizable; exigir las ocho rechazaría
   respuestas buenas por un detalle mal citado, que es el error que HIB.0 ya tuvo que corregir
   una vez —nueve de veinticinco respuestas descartadas, ocho con la mejor recuperación de la
   tanda—.
2. **Si el juez falla, la respuesta pasa.** Un juez caído es un fallo de instrumentación;
   convertirlo en una rendición lo cambia por un fallo de servicio, que es peor y menos visible.
   Queda marcado en el veredicto para poder contarlo en la traza.
3. **La remisión no entra.** HIB.0 legitimó nombrar una norma sin enlazarla («esto lo regula la
   Ley 9/2017, que no está en este corpus»). Si contara, cada respuesta que remite correctamente
   perdería por algo que el contrato permite a propósito.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)

# Enlace markdown, que es la forma que impone el contrato de citas. Una afirmación con enlace es
# **fundamento**; una sin enlace es remisión o prosa, y no entra.
ENLACE = re.compile(r"\[([^\]]{1,300})\]\((https?://[^)\s]+)\)")

# Marca con la que se aparta un enlace antes de partir en frases. Los enlaces llevan puntos
# dentro (`www.uji.es`), así que partir por puntos sin apartarlos primero trocea la cita por la
# mitad y la afirmación se pierde **sin dar ningún error**.
_HUECO = "\x00ENLACE{}\x00"


class Juez(Protocol):
    """Decide si un fragmento sostiene una afirmación. `None` si no pudo decidir."""

    async def __call__(self, afirmacion: str, fragmento: str) -> bool | None: ...


@dataclass(frozen=True)
class Veredicto:
    """Qué se juzgó y qué salió, para que el nodo decida y la traza lo pueda contar."""

    sostenida: bool
    """Si la respuesta se puede emitir. `False` sólo cuando había afirmaciones de fundamento y
    **ninguna** resultó sostenida."""

    juzgadas: int
    """Afirmaciones de fundamento encontradas. Cero significa que no había nada que sostener
    —un saludo, una repregunta— y no que la respuesta esté mal."""

    con_fundamento: int
    juez_fallo: bool
    detalle: list[dict]


def _afirmaciones(texto: str) -> list[tuple[str, str, str]]:
    """Las frases que llevan enlace, con el título y la URL que citan.

    Se aparta cada enlace antes de partir en frases y se devuelve después: es lo que evita que
    un `www.uji.es` parta la frase en dos y deje la afirmación sin su cita.
    """
    enlaces: list[tuple[str, str]] = []

    def _guarda(m: re.Match) -> str:
        enlaces.append((m.group(1), m.group(2)))
        return _HUECO.format(len(enlaces) - 1)

    plano = ENLACE.sub(_guarda, texto)
    salida: list[tuple[str, str, str]] = []
    for frase in re.split(r"(?<=[.?!:;])\s+|\n+", plano):
        indices = [int(i) for i in re.findall(r"\x00ENLACE(\d+)\x00", frase)]
        if not indices:
            continue
        # El texto de la afirmación, con los enlaces devueltos a su sitio: el juez tiene que
        # leer la frase como la lee una persona.
        legible = frase
        for i in indices:
            legible = legible.replace(_HUECO.format(i), enlaces[i][0])
        titulo, url = enlaces[indices[0]]
        salida.append((legible.strip(), titulo, url))
    return salida


def _sin_fragmento(url: str) -> str:
    return url.split("#", 1)[0].rstrip("/")


def _fuente_de(titulo: str, url: str, fuentes: list[dict]) -> dict | None:
    """La fuente recuperada que la afirmación cita, por URL primero y por título después.

    Por URL primero porque es el identificador que el contrato de citas ya validó; por título
    después porque el modelo a veces recorta la URL y el título sigue siendo reconocible.
    """
    objetivo = _sin_fragmento(url)
    for f in fuentes:
        if _sin_fragmento(str(f.get("url") or "")) == objetivo:
            return f
    plano = titulo.strip().lower()
    for f in fuentes:
        t = str(f.get("title") or "").strip().lower()
        if t and (t in plano or plano in t):
            return f
    return None


async def hay_fundamento(
    *, texto: str, fuentes: list[dict], juez: Juez | Any
) -> Veredicto:
    """El veredicto de fundamento de una respuesta ya validada por el contrato de citas."""
    if not fuentes or not (texto or "").strip():
        return Veredicto(True, 0, 0, False, [])

    afirmaciones = _afirmaciones(texto)
    if not afirmaciones:
        # No hay nada que sostener. Sin esta salida la puerta rechazaría la repregunta que
        # ORI-03 exige —la informadora pide explícitamente que se desambigüe antes de
        # contestar— y un saludo.
        return Veredicto(True, 0, 0, False, [])

    con_fundamento = 0
    sin_veredicto = 0
    detalle: list[dict] = []
    for frase, titulo, url in afirmaciones:
        fuente = _fuente_de(titulo, url, fuentes)
        if fuente is None:
            # Cita algo que no está entre lo recuperado: no hay fragmento con el que juzgar, y
            # cuenta como sin fundamento **sin gastar una llamada**. El contrato de citas ya
            # debería haberla despojado, así que llegar aquí es en sí mismo una señal.
            detalle.append({"afirmacion": frase[:200], "sostenida": False,
                            "motivo": "la fuente citada no esta entre las recuperadas"})
            continue
        try:
            veredicto = await juez(frase, str(fuente.get("excerpt") or ""))
        except Exception:  # noqa: BLE001
            veredicto = None
        if veredicto is None:
            sin_veredicto += 1
            detalle.append({"afirmacion": frase[:200], "sostenida": None,
                            "motivo": "el juez no pudo decidir"})
            continue
        if veredicto:
            con_fundamento += 1
        detalle.append({"afirmacion": frase[:200], "sostenida": bool(veredicto)})

    falsos_ciertos = len(afirmaciones) - con_fundamento - sin_veredicto
    # Pasa si alguna se sostiene, o si NINGUNA se rechazó con certeza —es decir, si lo único
    # que hubo fueron fallos del juez—.
    sostenida = con_fundamento > 0 or falsos_ciertos == 0
    if sin_veredicto:
        logger.warning(
            "comprobacion de fundamento incompleta: %d de %d afirmaciones sin veredicto",
            sin_veredicto, len(afirmaciones),
        )
    return Veredicto(
        sostenida=sostenida,
        juzgadas=len(afirmaciones),
        con_fundamento=con_fundamento,
        juez_fallo=sin_veredicto > 0,
        detalle=detalle,
    )


_PLANTILLA_JUEZ = """Decides si una AFIRMACION esta sostenida por el FRAGMENTO que la acompana.

No juzgas si la afirmacion es cierta en el mundo: juzgas si **este fragmento la sostiene**. Una \
afirmacion cierta pero que el fragmento no dice NO esta sostenida — es la diferencia entre citar \
bien y acertar por casualidad.

Sostenida tambien si el fragmento lo dice con otras palabras, o si la afirmacion es una \
consecuencia inmediata y necesaria de lo que dice. NO sostenida si hace falta anadir un dato que \
no esta, o si el fragmento habla de otro ambito (grado cuando la afirmacion es de master, otro \
curso academico, otro colectivo).

AFIRMACION:
{afirmacion}

FRAGMENTO CITADO:
{fragmento}

Responde SOLO con un objeto JSON, sin vallas de codigo:
{{"sostenida": true|false}}"""


def juez_de_modelo(llm: Any, limite_fragmento: int = 8000) -> Juez:
    """Un juez que pregunta al modelo con el fragmento delante.

    La plantilla es la **misma** que se valido en el banco de `_local/golden/`, donde acordo
    **24 de 24** con afirmaciones etiquetadas a mano (intervalo de Wilson al 95 %: 0,86-1,00),
    por encima del 0,80 exigido. Cambiarla aqui invalidaria esa validacion, asi que si se cambia
    hay que volver a medir el acuerdo antes de creer ninguna cifra.

    Ese 1,000 no demuestra tanto como parece: las 24 afirmaciones las escribio quien escribio la
    plantilla, asi que mide consistencia interna y no validez. Y las afirmaciones reales son
    compuestas y matizadas, donde el acuerdo bajara.
    """

    async def juez(afirmacion: str, fragmento: str) -> bool | None:
        from server.app.core.llm_json import extraer_json

        if not fragmento.strip():
            return None
        try:
            salida = await llm.ainvoke(
                _PLANTILLA_JUEZ.format(
                    afirmacion=afirmacion[:2000], fragmento=fragmento[:limite_fragmento]
                )
            )
        except Exception:  # noqa: BLE001 — un juez caido no tumba la respuesta
            return None
        crudo = getattr(salida, "content", salida)
        try:
            datos = json.loads(
                extraer_json(crudo if isinstance(crudo, str) else str(crudo))
            )
        except Exception:  # noqa: BLE001
            return None
        valor = datos.get("sostenida")
        return bool(valor) if isinstance(valor, bool) else None

    return juez


def fuente_desde_evidencia(item: Any) -> dict:
    """Un `EvidenceItem` o un `Source` en la forma que `hay_fundamento` compara.

    Los dos dialectos conviven por debajo —RAG.2 unifico el contrato en `EvidenceItem`
    (`source_url`, `content`) pero las estrategias de `services/retrieval/` siguen devolviendo
    `Source` (`url`, `excerpt`)— y leer solo uno de los dos ya dio, en el banco de evaluacion,
    un **0 de 12 fuentes recuperadas** que parecia un fallo del sistema y era del medidor.
    Aqui el mismo descuido dejaria todas las afirmaciones sin fragmento con el que juzgarlas, y
    la puerta descartaria **todas** las respuestas.
    """
    return {
        "title": getattr(item, "title", None),
        "url": getattr(item, "source_url", None) or getattr(item, "url", None),
        "excerpt": getattr(item, "content", None) or getattr(item, "excerpt", None) or "",
    }

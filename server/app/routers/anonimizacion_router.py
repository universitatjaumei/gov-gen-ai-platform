"""La anonimización como servicio: detectar PII y sustituirla (REG.3).

Deploy: edge
Módulo: —

**Por qué existe.** El motor de anonimización de la plataforma —regex, NER de spaCy y anclajes de
formulario, con el vocabulario de identificadores españoles ya afinado— sólo lo usaba `redaccion`.
Una herramienta externa que necesite limpiar PII antes de mandar texto a un modelo tenía dos
salidas: reimplementarlo peor, o no hacerlo. Estos dos endpoints son la tercera.

**La regla del bloque: el texto no se registra, nunca.** Aquí llega, por definición, el material
más sensible que pasa por la plataforma: nos lo mandan *precisamente porque* lleva datos
personales. Un `logger.debug(text)` puesto de buena fe durante una depuración convertiría el
registro del servidor en el archivo de PII que este servicio existe para evitar. No hay ningún
registro con el texto ni con el resultado, y hay un test con un centinela que lo comprueba a nivel
DEBUG.

**Stateless, y no por elegancia.** El motor guarda el mapa real→ficticio en el `FakerGenerator` de
su contexto para poder deshacer la sustitución. Un detector compartido entre peticiones
acumularía en memoria la PII de todos los que llamaron, y la de una organización quedaría al
alcance de `deanonymize` de otra. Por eso el detector es de una petición y no toca la base.

**Sin parámetro de política.** Se aplica la del motor y no se ofrece elegir: se añadirá cuando un
consumidor real lo pida y diga qué necesita, no antes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from server.app.api.deps import require_pat_scopes
from server.app.core.auth.pat.scopes import ANONIMIZACION_USE
from server.app.modules.redaccion.services.anonymization.anonymizer import (
    TIPOS_ANONIMIZADOS_POR_DEFECTO,
)
from server.app.modules.redaccion.services.anonymization.pii_detector import (
    PiiDetector,
    PiiSpan,
)

#: Tope de tamaño del texto. Sin él, una petición puede tener al proceso detectando durante
#: minutos: el NER de spaCy es lineal en el texto pero con una constante alta.
MAXIMO_CARACTERES = 200_000

router = APIRouter(prefix="/anonimizacion", tags=["anonimizacion"])

_exige_scope = require_pat_scopes(ANONIMIZACION_USE)


def get_detector() -> PiiDetector:
    """Un detector por petición.

    Compartirlo entre peticiones dejaría el mapa real→ficticio acumulando la PII de todos los que
    llamaron. Es lo que hace stateless al servicio, y hay un test que lo fija.
    """
    return PiiDetector()


class TextoAAnalizar(BaseModel):
    """El texto y nada más: el contrato no admite metadatos que luego habría que custodiar."""

    model_config = {"extra": "forbid"}

    text: str = Field(max_length=MAXIMO_CARACTERES)


class SpansDetectados(BaseModel):
    spans: list[PiiSpan]


class TextoAnonimizado(BaseModel):
    text_anonimizado: str
    spans_aplicados: list[PiiSpan]


@router.post(
    "/spans",
    response_model=SpansDetectados,
    operation_id="detectarPii",
)
async def detectar_spans(
    peticion: TextoAAnalizar,
    _=Depends(_exige_scope),
    detector: PiiDetector = Depends(get_detector),
) -> SpansDetectados:
    """Devuelve los tramos de PII con su posición, tipo y un sustituto propuesto.

    Los offsets son sobre el texto recibido tal cual, para que quien integra pueda resaltar o
    cortar sin volver a buscar.
    """
    return SpansDetectados(spans=detector.detect_spans(peticion.text))


@router.post(
    "/replace",
    response_model=TextoAnonimizado,
    operation_id="anonimizarTexto",
)
async def sustituir(
    peticion: TextoAAnalizar,
    _=Depends(_exige_scope),
    detector: PiiDetector = Depends(get_detector),
) -> TextoAnonimizado:
    """Aplica la política por defecto y dice exactamente qué sustituyó.

    Detecta una vez y aplica esa misma detección, en vez de llamar a `AnonymizationContext.
    anonymize()` y detectar aparte para el informe: el sustituto lo genera un `Faker`, así que dos
    pasadas darían un texto y un informe que no se corresponden, y quien integra no podría cotejar
    el resultado.

    Se recorre de derecha a izquierda para que los offsets de los tramos que quedan no se muevan
    al reemplazar los anteriores.
    """
    aplicados = [
        span
        for span in detector.detect_spans(peticion.text)
        if span.type in TIPOS_ANONIMIZADOS_POR_DEFECTO
    ]

    resultado = peticion.text
    for span in sorted(aplicados, key=lambda s: s.start, reverse=True):
        resultado = resultado[: span.start] + span.suggested_fake + resultado[span.end :]

    return TextoAnonimizado(text_anonimizado=resultado, spans_aplicados=aplicados)

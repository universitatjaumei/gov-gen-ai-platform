"""Las verificaciones de la plataforma, como servicio (Bloque VAS).

Deploy: edge
Módulo: —

**Por qué existe.** La posición de desarrollo era «gobernanza y experimentación sí; desarrollar es
cosa nuestra». La respuesta es que, definidos los parámetros de gobernanza de un caso de uso, la
UADTI puede desarrollar fuera **con registro por API dentro** — y para que eso sea literal hacen
falta servicios que hoy sólo existen como función interna. Este router presta tres, y todos son
deterministas: la misma entrada da la misma salida, así que exponerlos no crea una segunda fuente
de verdad.

**La regla dura del bloque: no hay segunda implementación.** Cada endpoint envuelve la función que
ya usa el motor. Si el servicio necesita algo que la función no da, se cambia la función y el motor
lo hereda; nunca una copia «para la API». Un test de paridad por servicio compara el veredicto de
aquí con el de la función directamente.

**El texto no se guarda.** Ni la respuesta que se verifica ni el código que se audita tocan logs ni
base de datos — la misma regla que REG.3 para la anonimización, y por el mismo motivo: aquí llega,
por definición, material que no es nuestro. Este módulo **no recibe sesión de base de datos**, que
es una garantía más fuerte que un cuidado: no hay dónde escribir.

**Y la asimetría del registro, escrita para que nadie la «arregle»**: la auditoría de código sí
deja un evento REG (VAS.3) porque auditar es un acto de gobernanza —la revisión posterior del
nivel 2 de la Instrucció 02/2026—, y verificar citas o consultar vigencia no, porque son
comprobaciones sin estado: la aplicación externa ya registra **su** actividad por REG.2, y un
evento por cada comprobación duplicaría el registro sin decir nada nuevo.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from server.app.api.deps import require_pat_scopes
from server.app.core.auth.pat.scopes import VERIFICACIONES_USE
from server.app.modules.agents_hub.agent.citation_validator import aplicar_contrato

#: Tope del texto que se acepta, en bytes. No hay límite de entrada del sandbox del que heredarlo
#: —FUN.6 aún no existe—, así que se fija aquí y ese bloque lo heredará de este sitio en vez de
#: inventar otro. Sin tope, una petición tiene al proceso analizando megabytes.
MAXIMO_BYTES = 64 * 1024

router = APIRouter(prefix="/verificaciones", tags=["verificaciones"])

_exige_scope = require_pat_scopes(VERIFICACIONES_USE)


class FuenteDeVerificacion(BaseModel):
    """Una fuente que quien llama declara como entregada al modelo.

    Habla el dialecto de la evidencia del motor a propósito: `source_url` y `title` son los
    atributos que `citation_validator` lee, así que este objeto se le pasa **tal cual** y no hay
    conversión que pueda perder algo por el camino.
    """

    model_config = {"extra": "forbid"}

    url: str = Field(min_length=1, max_length=2048)
    titulo: str | None = Field(default=None, max_length=500)

    @property
    def source_url(self) -> str:
        return self.url

    @property
    def title(self) -> str | None:
        return self.titulo


class PeticionDeCitas(BaseModel):
    """El texto a verificar y las fuentes que se le entregaron a quien lo escribió."""

    model_config = {"extra": "forbid"}

    texto: str
    fuentes_permitidas: list[FuenteDeVerificacion] = Field(default_factory=list)
    #: El modo del motor. Se acepta por estabilidad del contrato y porque el grafo lo pasa; hoy
    #: el contrato de citas se comporta igual en los tres, y decirlo aquí es más honesto que
    #: sugerir con un parámetro ausente que no existe la distinción.
    modo: str = "RAG"
    #: El mensaje de rendición del asistente que llama. Si no viene, el del motor. UX.4: el texto
    #: fijo en castellano contestando a una pregunta en valenciano fue un defecto real.
    mensaje_sin_respuesta: str | None = Field(default=None, max_length=2000)


class VeredictoDeCitas(BaseModel):
    """Qué dice el contrato, y qué hizo para decirlo.

    El desglose importa tanto como el veredicto: quien integra necesita saber **por qué** su
    respuesta no cumple para poder arreglar la generación, no sólo que no cumple.
    """

    cumple: bool
    texto_resultante: str
    citas_validas: list[str]
    citas_invalidas: list[str]
    remisiones_despojadas: int
    anclas_degradadas: int


def _dentro_del_limite(texto: str) -> None:
    if len(texto.encode("utf-8")) > MAXIMO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "TEXTO_DEMASIADO_GRANDE",
                "message": f"El texto no puede pasar de {MAXIMO_BYTES} bytes.",
                "maximo_bytes": MAXIMO_BYTES,
            },
        )


@router.post(
    "/citas",
    response_model=VeredictoDeCitas,
    operation_id="verificarCitas",
)
async def verificar_citas(
    peticion: PeticionDeCitas,
    _=Depends(_exige_scope),
) -> VeredictoDeCitas:
    """Aplica el contrato de citas de la plataforma a una respuesta generada fuera.

    La regla es «ninguna afirmación sin fuente resoluble», y tiene tres movimientos que importan
    en este orden: una cita al documento correcto con un ancla que nadie recuperó **baja al
    documento y sobrevive**; lo que apunta fuera del conjunto entregado **pierde el enlace, no la
    mención**; y sólo entonces se comprueba si queda alguna cita válida.

    Si no queda ninguna, se devuelve el mensaje de rendición: es lo que hace el asistente, y el
    sentido de prestar el servicio es que quien desarrolle fuera pueda hacer lo mismo.
    """
    _dentro_del_limite(peticion.texto)

    resultado = aplicar_contrato(
        peticion.texto,
        list(peticion.fuentes_permitidas),
        peticion.modo,
        peticion.mensaje_sin_respuesta,
    )

    return VeredictoDeCitas(
        cumple=resultado.cumple,
        texto_resultante=resultado.texto,
        citas_validas=resultado.citas_validas,
        citas_invalidas=resultado.citas_invalidas,
        remisiones_despojadas=resultado.remisiones_despojadas,
        anclas_degradadas=resultado.anclas_degradadas,
    )

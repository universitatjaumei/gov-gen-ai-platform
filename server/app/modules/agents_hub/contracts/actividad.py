"""El evento de actividad IA: qué se registra de un uso de IA ocurrido fuera de la plataforma.

Deploy: edge

**Registro de gobernanza, no trazado técnico.** Sirve a la conservación de registros del AI Act y
al registro de actividades de tratamiento del RGPD: quién usó qué agente, con qué finalidad y sobre
qué categorías de datos. El detalle token a token de las conversaciones internas ya lo cubre la
observabilidad de la plataforma y no se reconstruye aquí.

Lo registran herramientas de terceros —asistentes de escritorio, agentes de código, integraciones
propias— para que una organización pueda responder «qué IA se usó aquí» sin depender de que cada
herramienta lo cuente a su manera.

**Metadatos sí, payloads no.** No hay ningún campo de contenido, y `extra="forbid"` rechaza los que
lleguen sin declarar en vez de ignorarlos: aceptado en silencio, un campo de contenido haría creer
a quien integra que se guardó algo que no se guardó, y quien audite el registro no sabría si están
todos los datos. Si un caso exige evidencia de lo que se procesó, va `payload_hash` y nunca el
texto. La razón es que el registro existe para dar cuenta del tratamiento de datos personales: si
además los contuviera, sería el problema en vez de la respuesta.

Los nombres de campo son propios y mapeables a las convenciones semánticas OTel GenAI; el mapeo
campo a campo está en `docs/REGISTRO_ACTIVIDAD_IA.md`. Adoptar el estándar entero arrastraría
atributos de observabilidad que aquí no aplican.
"""
from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

#: SHA-256 en hexadecimal minúscula. Se valida la forma porque un hash mal formado no sirve para
#: cotejar nada, y el error tiene que salir al registrar y no el día de la auditoría.
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ActividadIAEvent(BaseModel):
    """Un uso de IA declarado por una herramienta externa.

    La organización **no viaja en el evento**: se deriva del token que autentica la petición. Un
    agente externo no elige en nombre de qué organización registra, igual que no elige qué datos
    puede leer.
    """

    model_config = {"extra": "forbid"}

    #: Cuándo ocurrió el uso, según quien lo declara. Exige zona horaria: sin ella, dos
    #: herramientas en husos distintos producen un registro que no se puede ordenar.
    ocurrido_en: datetime

    #: Identificador **opaco** de la persona en la herramienta externa. Opaco a propósito: para
    #: dar cuenta de un tratamiento basta poder correlacionar, no identificar desde el registro.
    actor: str = Field(min_length=1, max_length=255)

    #: La herramienta: `claude-cowork`, `copilot`, `cursor`… Texto libre porque el catálogo de
    #: herramientas cambia sin que este código tenga nada que decir.
    herramienta: str = Field(min_length=1, max_length=100)

    #: El agente o bot concreto dentro de esa herramienta, cuando lo hay.
    agente: str | None = Field(default=None, max_length=255)

    #: La finalidad declarada, en una línea. Es el único campo de texto libre, y es el que da
    #: sentido al registro: sin finalidad, saber que alguien usó una IA no informa de nada.
    finalidad: str = Field(min_length=1, max_length=500)

    modelo_usado: str | None = Field(default=None, max_length=100)

    #: Categorías de datos declaradas. **Lista libre, sin `Enum`**: es vocabulario, no estructura,
    #: y vale la misma regla que para el vocabulario del corpus — si fuera enumeración cerrada,
    #: una categoría nueva exigiría migración y despliegue del núcleo.
    categorias_datos: list[str] = Field(default_factory=list)

    #: SHA-256 del contenido procesado, si el caso exige poder cotejarlo. **Nunca el contenido.**
    payload_hash: str | None = None

    @field_validator("ocurrido_en")
    @classmethod
    def _con_zona_horaria(cls, valor: datetime) -> datetime:
        if valor.tzinfo is None or valor.utcoffset() is None:
            raise ValueError(
                "`ocurrido_en` tiene que llevar zona horaria: sin ella, dos herramientas en "
                "husos distintos producen un registro que no se puede ordenar."
            )
        return valor

    @field_validator("payload_hash")
    @classmethod
    def _es_un_sha256(cls, valor: str | None) -> str | None:
        if valor is not None and not _SHA256.match(valor):
            raise ValueError(
                "`payload_hash` tiene que ser un SHA-256 en hexadecimal minúscula (64 "
                "caracteres). Un hash mal formado no sirve para cotejar nada."
            )
        return valor

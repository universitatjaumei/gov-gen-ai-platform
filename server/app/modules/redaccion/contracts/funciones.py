"""El contrato de una función del catálogo: qué pide, qué devuelve y qué declara (FUN.2).

Deploy: edge.

Hoy el contrato de un script es **implícito** —«tienes `file_path`, `raw_text` y `options`, asigna
`result`»— y eso aguanta mientras quien escribe el script y quien le pasa los datos son la misma
persona el mismo día. En cuanto una función se comparte entre dos plantillas, dos organizaciones y
una API, el contrato implícito es el sitio por donde se rompe todo: un ERP cambia una columna y el
informe falla con un `KeyError` de pandas dentro del sandbox.

Cuatro decisiones, y ninguna es de comodidad:

1. **Un solo objeto para los dos orígenes.** Este `ContratoFuncion` es lo que declara una función
   de autoservicio *y* lo que exporta el descriptor de una empaquetada (FUN.5). Dos esquemas de
   contrato divergen; uno solo es lo que hace que el formulario, la API y —en Fase 3— la fase de
   expediente traten igual a las dos. Ninguna rama «si es paquete».
2. **La salida es `ExtractionResult`, el que ya existe.** No se inventa un segundo esquema: el que
   hay es el que consumen los nodos.
3. **Los parámetros reutilizan `UIFieldDescriptor`** y los slots `UIDropzoneDescriptor`, los mismos
   tipos que `ReportUIContract`. Así el SDUI pinta el formulario desde el contrato, gratis, y no
   hay dos pantallas pintando formularios distintos para lo mismo.
4. **La declaración responsable forma parte del contrato.** Es lo que la Instrucció 02/2026 exige
   registrar antes de compartir (§8.2) y lo que la revisión posterior lee — también en una función
   corporativa: un paquete también declara finalidad y categorías.

Nada aquí sabe de «informe»: el catálogo es pieza compartida.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from server.app.core.actividad_categorias import CATEGORIAS_INICIALES
from server.app.modules.redaccion.contracts.ui import (
    UIDropzoneDescriptor,
    UIFieldDescriptor,
)

#: El vocabulario de categorías de datos **es el del registro de actividad** (REG). Un solo
#: vocabulario en la plataforma, o el catálogo y el registro no se pueden cruzar en una auditoría.
#: Es una semilla y no una definición: el vocabulario es abierto (I4), así que una categoría fuera
#: de la lista se acepta — rechazarla convertiría «esto no está catalogado todavía» en «esta
#: función no se puede declarar», que es lo que empuja al Shadow IT.
CATEGORIAS_CONOCIDAS: tuple[str, ...] = tuple(codigo for codigo, _ in CATEGORIAS_INICIALES)

#: Las clases de fichero que un slot puede pedir. Estructura con consumidor: cada una tiene un
#: pipeline y unas extensiones detrás.
KindDeSlot = Literal["excel", "pdf", "markdown", "text"]

#: Qué extensiones acepta el navegador para cada clase. Vive aquí y no en React: el cliente lo
#: recibe en el descriptor, no lo deduce.
EXTENSIONES_POR_KIND: dict[str, list[str]] = {
    "excel": [".xlsx", ".xlsm", ".csv"],
    "pdf": [".pdf"],
    "markdown": [".md"],
    "text": [".txt"],
}

#: Los tipos de parámetro que el formulario sabe pintar y el validador sabe comprobar.
TIPOS_DE_PARAMETRO: frozenset[str] = frozenset({"text", "number", "boolean", "date", "select"})


class ContratoIncoherente(ValueError):
    """El contrato de una función no se sostiene: no se registra la versión."""


class EntradaNoCumpleElContrato(ValueError):
    """Lo que se le pasa a una función no encaja con lo que declara pedir.

    Es el error que sustituye al *traceback* de pandas cuando un ERP cambia de formato: dice qué
    slot falta o qué parámetro no es de su tipo, **antes** de pagar un subproceso de sandbox.
    """


class SlotDeFichero(BaseModel):
    """Un fichero que la función pide, con su clase y si es obligatorio."""

    slot_id: str = Field(min_length=1, max_length=60)
    kind: KindDeSlot
    required: bool = False
    label: dict[str, str] = Field(default_factory=dict)


class ParametroDeFuncion(UIFieldDescriptor):
    """Un parámetro tipado. **Es un `UIFieldDescriptor`**: el formulario sale de aquí.

    Heredar en vez de declarar un gemelo es lo que garantiza que el contrato y la pantalla no
    puedan divergir: si mañana el descriptor gana un campo, el contrato lo tiene.
    """

    @model_validator(mode="after")
    def _el_tipo_tiene_que_saberse_pintar(self) -> "ParametroDeFuncion":
        if self.field_type not in TIPOS_DE_PARAMETRO:
            raise ValueError(
                f"«{self.field_type}» no es un tipo de parámetro conocido; los que hay son "
                f"{', '.join(sorted(TIPOS_DE_PARAMETRO))}"
            )
        return self


class ContratoFuncion(BaseModel):
    """Lo que una función pide, lo que devuelve y lo que declara.

    `extra="forbid"` a propósito (la lección de REG.1): un campo de más en el contrato de un
    paquete de un tercero es un malentendido, y aceptarlo en silencio lo convierte en una
    diferencia de comportamiento que aparece meses después.
    """

    model_config = {"extra": "forbid"}

    slots: list[SlotDeFichero] = Field(default_factory=list)
    parametros: list[ParametroDeFuncion] = Field(default_factory=list)
    #: La salida es siempre el esquema que ya consumen los nodos. Se declara para que el
    #: contrato sea legible por sí solo, no para poder cambiarla.
    salida: Literal["ExtractionResult"] = "ExtractionResult"

    # ── Declaración responsable (Instrucció §8.2) ──
    finalidad: str = Field(min_length=1)
    categorias_datos: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _los_nombres_no_se_pisan(self) -> "ContratoFuncion":
        """Slots y parámetros comparten espacio de nombres: la entrada es un solo diccionario."""
        vistos: set[str] = set()
        for cual, elementos in (("slot", self.slots), ("parámetro", self.parametros)):
            for elemento in elementos:
                if elemento.slot_id in vistos:
                    raise ValueError(
                        f"«{elemento.slot_id}» está declarado dos veces: un {cual} no puede "
                        "repetir el identificador de otro, porque la entrada es un solo "
                        "diccionario y el segundo pisaría al primero"
                    )
                vistos.add(elemento.slot_id)
        return self

    @model_validator(mode="after")
    def _la_declaracion_dice_algo(self) -> "ContratoFuncion":
        if not [c for c in self.categorias_datos if c and c.strip()]:
            raise ValueError(
                "hay que declarar las categorías de datos: una lista vacía es ambigua entre "
                "«no hubo datos personales» y «no lo declaré», y el vocabulario tiene un código "
                "para lo primero (`sin_datos_personales`)"
            )
        return self


class EntradaValidada(BaseModel):
    """Lo que se le pasa a una función una vez comprobado contra su contrato."""

    ficheros: dict[str, str] = Field(default_factory=dict)
    parametros: dict[str, Any] = Field(default_factory=dict)


class FormularioDeFuncion(BaseModel):
    """Los descriptores con los que el SDUI pinta la entrada de una función."""

    dropzones: list[UIDropzoneDescriptor] = Field(default_factory=list)
    campos: list[UIFieldDescriptor] = Field(default_factory=list)


def contrato_coherente(contrato: ContratoFuncion, *, exige_entrada: bool = False) -> None:
    """Comprueba lo que Pydantic no puede: que el contrato tenga sentido como contrato.

    `exige_entrada` lo usa el registro de una versión que declara leer ficheros; una función que
    sólo toma parámetros es legítima, así que no se exige siempre.
    """
    if exige_entrada and not contrato.slots and not contrato.parametros:
        raise ContratoIncoherente(
            "el contrato no declara ningún slot ni ningún parámetro: una función que no pide "
            "nada no puede recibir los datos del informe"
        )


def descriptores_de_formulario(contrato: ContratoFuncion) -> FormularioDeFuncion:
    """El formulario que el SDUI pinta, derivado del contrato.

    Aquí es donde se paga el precio de haber declarado el contrato, y donde se cobra: el
    frontend no conoce ni un campo a priori (regla maestra 1).
    """
    return FormularioDeFuncion(
        dropzones=[
            UIDropzoneDescriptor(
                slot_id=slot.slot_id,
                label=slot.label or {"es": slot.slot_id},
                accept=list(EXTENSIONES_POR_KIND.get(slot.kind, [])),
                multiple=False,
                required=slot.required,
            )
            for slot in contrato.slots
        ],
        campos=[
            UIFieldDescriptor(
                slot_id=p.slot_id,
                label=p.label,
                field_type=p.field_type,
                placeholder=p.placeholder,
                required=p.required,
            )
            for p in contrato.parametros
        ],
    )


def validar_entrada(
    contrato: ContratoFuncion,
    *,
    ficheros: dict[str, str] | None = None,
    parametros: dict[str, Any] | None = None,
) -> EntradaValidada:
    """La entrada comprobada contra el contrato, **antes** de invocar nada.

    Levanta `EntradaNoCumpleElContrato` con el nombre de lo que falla. Validar después sería
    pagar un subproceso para obtener un error peor.
    """
    ficheros = dict(ficheros or {})
    parametros = dict(parametros or {})

    declarados = {slot.slot_id: slot for slot in contrato.slots}
    for slot_id, slot in declarados.items():
        if slot.required and not ficheros.get(slot_id):
            raise EntradaNoCumpleElContrato(
                f"falta el slot «{slot_id}», que el contrato declara obligatorio"
            )
    for slot_id in ficheros:
        if slot_id not in declarados:
            raise EntradaNoCumpleElContrato(
                f"el slot «{slot_id}» no está en el contrato de esta función: o alguien lo "
                "cambió sin avisar, o se están mandando datos que la función no pidió"
            )

    for parametro in contrato.parametros:
        presente = parametro.slot_id in parametros
        if parametro.required and not presente:
            raise EntradaNoCumpleElContrato(
                f"falta el parámetro «{parametro.slot_id}», que el contrato declara obligatorio"
            )
        if presente:
            _comprobar_tipo(parametro, parametros[parametro.slot_id])

    return EntradaValidada(ficheros=ficheros, parametros=parametros)


def _comprobar_tipo(parametro: ParametroDeFuncion, valor: Any) -> None:
    """El tipo de un parámetro, comprobado con el mensaje que necesita quien rellena el formulario."""
    tipo = parametro.field_type
    if tipo == "number":
        # `bool` es subclase de `int` en Python y aquí eso sería un sí por un 1.
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise EntradaNoCumpleElContrato(
                f"el parámetro «{parametro.slot_id}» tiene que ser numérico y ha llegado "
                f"«{valor}»"
            )
    elif tipo == "boolean":
        if not isinstance(valor, bool):
            raise EntradaNoCumpleElContrato(
                f"el parámetro «{parametro.slot_id}» tiene que ser un sí o un no"
            )
    elif tipo in {"text", "date", "select"}:
        if not isinstance(valor, str):
            raise EntradaNoCumpleElContrato(
                f"el parámetro «{parametro.slot_id}» tiene que ser texto"
            )

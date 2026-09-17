"""De `funcion@versión` a algo ejecutable, y nunca a nada en silencio (FUN.3).

Deploy: edge.

El nodo de extracción no sabe —ni tiene que saber— de dónde sale el código de una función. Le
pide a este resolutor «lo ejecutable» de una referencia y recibe un objeto que sabe describirse:
qué darle al pipeline y qué anotar en el manifiesto. En FUN.5 este mismo resolutor gana el origen
empaquetado, que devuelve un *callable* en vez de código, **sin tocar el nodo**.

**Falla en alto, siempre.** Una función retirada, una versión que no existe o una suspendida
hacen fallar el bloque con un mensaje que nombra la función y, si está suspendida, el motivo. La
alternativa —devolver vacío— es la lección de los perfiles sin configurar: parecía funcionar y
producía informes sin datos que nadie relacionaba con la causa.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

#: Los estados en los que una versión **no** se ejecuta, con lo que hay que decir de cada uno.
#: `no_instalada` es de FUN.5 y ya está aquí porque el mensaje es el mismo problema.
_POR_QUE_NO: dict[str, str] = {
    "draft": "está en borrador: todavía no se ha registrado",
    "suspendida": "está suspendida",
    "retirada": "está retirada por su autor",
    "no_instalada": "es de un paquete que ya no está instalado en este despliegue",
}


class FuncionNoEjecutable(RuntimeError):
    """La referencia de un bloque no lleva a nada que se pueda ejecutar.

    Se levanta y no se traga: el bloque tiene que fallar en alto, con el nombre de la función y
    el motivo, para que quien mire el informe sepa por qué dejó de funcionar.
    """


@dataclass(frozen=True)
class FuncionEjecutable:
    """Lo que hace falta para ejecutar una versión y para poder decir qué se ejecutó."""

    funcion_id: uuid.UUID
    nombre: str
    version: int
    origen: str
    code: str | None
    code_sha256: str
    contrato_entrada: dict[str, Any]
    #: Sólo en origen `paquete` (FUN.5): la versión semver realmente instalada, que puede no ser
    #: la anclada. En autoservicio es `None` porque el anclaje es exacto.
    version_paquete: str | None = None

    def como_opciones_del_pipeline(self) -> dict[str, Any]:
        """Lo que el pipeline de script espera. **El protocolo no cambia.**

        `approved=True` sigue ahí porque el pipeline lo exige, y ahora significa lo que de verdad
        ocurrió: la versión está **registrada**, o sea auditada sin hallazgos críticos y probada
        en el sandbox. Eso es la puerta del nivel 2 de la Instrucció; la aprobación humana previa
        ya no lo es.
        """
        return {"code": self.code or "", "approved": True}

    def para_el_manifiesto(self) -> dict[str, Any]:
        """Lo que el `RunManifest` anota. Hasta FUN.3 no anotaba nada de esto: el código iba
        incrustado en la plantilla y no tenía identidad, así que «qué corrió» no se podía
        responder."""
        anotacion: dict[str, Any] = {
            "funcion_id": str(self.funcion_id),
            "nombre": self.nombre,
            "version": self.version,
            "origen": self.origen,
            "code_sha256": self.code_sha256,
        }
        if self.version_paquete is not None:
            anotacion["version_paquete"] = self.version_paquete
        return anotacion


class ResolvedorDeFuncion:
    """Resuelve una referencia del catálogo. Un solo método, para que el nodo no sepa de orígenes."""

    def __init__(self, session: Any) -> None:
        self._session = session

    async def resolver(self, funcion_id: uuid.UUID, version: int) -> FuncionEjecutable:
        from sqlalchemy import select

        from server.app.modules.redaccion.database.models import (
            HubFuncion,
            HubFuncionVersion,
        )

        funcion = await self._session.get(HubFuncion, funcion_id)
        if funcion is None:
            raise FuncionNoEjecutable(
                f"la función {funcion_id} no está en el catálogo: la plantilla referencia algo "
                "que no existe"
            )

        fila = (
            await self._session.execute(
                select(HubFuncionVersion)
                .where(HubFuncionVersion.funcion_id == funcion_id)
                .where(HubFuncionVersion.version == version)
            )
        ).scalar_one_or_none()

        if fila is None:
            raise FuncionNoEjecutable(
                f"la función «{funcion.nombre}» no tiene versión {version}: la plantilla está "
                "anclada a una versión que no existe"
            )

        if fila.estado != "registrada":
            motivo = _POR_QUE_NO.get(fila.estado, f"está en estado «{fila.estado}»")
            detalle = ""
            if fila.estado == "suspendida" and fila.motivo_suspension:
                detalle = f" — motivo: {fila.motivo_suspension}"
            raise FuncionNoEjecutable(
                f"la versión {version} de «{funcion.nombre}» no se puede ejecutar: "
                f"{motivo}{detalle}"
            )

        return FuncionEjecutable(
            funcion_id=funcion.id,
            nombre=funcion.nombre,
            version=fila.version,
            origen=funcion.origen,
            code=fila.code,
            code_sha256=fila.code_sha256,
            contrato_entrada=dict(fila.contrato_entrada or {}),
            version_paquete=fila.version_paquete,
        )

"""Con qué credencial habla una organización con un proveedor (MT.2).

Deploy: shared — la resuelve el mismo `model_factory` que ya comparten cloud y edge.

Nace de que `hub_providers` tenía una sola `api_key` para toda la instalación. En el modelo
Diputación→municipios eso significa que el consumo de un ayuntamiento se factura al contrato de
otro y que sus prompts viajan por ese contrato: coste mal atribuido y protección de datos.

**Sin ninguna fila, esto devuelve `None`** y quien llama sigue con la cadena de siempre
—`provider.api_key` → la variable de `api_key_secret_name` → la variable por omisión del
proveedor—. Es lo que hace que el piloto no note la migración: hoy no hay filas.

Los tres métodos son los que ya estaban en uso, sólo que uno de ellos no estaba dicho:

- `clave`: la clave literal. Funciona, y es un secreto en reposo dentro de la base.
- `variable_de_entorno`: la base guarda **el nombre** y el secreto vive fuera. Es el método que
  sirve al despliegue en GCP —Secret Manager monta una variable por organización— y el único que
  permite credenciales por organización sin meter ningún secreto en la base de datos.
- `entorno_de_ejecucion`: sin clave, las credenciales del propio proceso (ADC de Vertex, que es
  lo que Vertex aconseja). Hasta ahora esto no se declaraba en ninguna parte: estaba en el código
  y en la cabeza de quien lo montó, así que «sin clave» era indistinguible de «mal configurado».

**El límite de ADC, dicho en vez de disimulado.** Un proceso tiene una sola identidad ADC. En
`edge` —un despliegue por municipio— eso es exactamente lo que se quiere: el proceso sirve a una
organización, así que su identidad *es* la de esa organización. En cloud-only con varias
organizaciones no puede diferir, y declararlo ahí sería configuración que parece funcionar; se
resuelve con el motivo dicho, no en silencio. Si algún día hace falta, la salida es un cuarto
método —suplantación de cuenta de servicio por organización— que cuesta una columna nullable y
ampliar el CHECK; no se escribe antes de que alguien lo pida.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.core.ambito import de_esta_organizacion, de_plataforma
from server.app.modules.agents_hub.database.config_models import (
    HubProviderCredential,
    MetodoDeCredencial,
)


@dataclass(frozen=True)
class CredencialDeProveedor:
    """La credencial ya resuelta, lista para construir el cliente del proveedor.

    `falta` no es una excepción a propósito: quien llama tiene que poder decidir si degrada, si
    prueba la cadena antigua o si falla, y una excepción aquí le quitaría esa decisión. Lo que
    sí hace es **decir qué falta**, con el nombre concreto: «falta la clave» manda a leer
    código, «falta `GOOGLE_API_KEY_ONDA`» se arregla en el despliegue.
    """

    metodo: MetodoDeCredencial
    api_key: str | None = None
    base_url: str | None = None
    #: Qué impide usar esta credencial, si algo lo impide. `None` = utilizable.
    falta: str | None = None

    @property
    def utilizable(self) -> bool:
        return self.falta is None


async def resolver_credencial(
    session: AsyncSession,
    provider_id: str,
    organizacion_id: uuid.UUID | None,
    *,
    modo_de_despliegue: str | None = None,
) -> CredencialDeProveedor | None:
    """La credencial de esta organización para este proveedor, o la de plataforma, o `None`.

    `None` significa «esta tabla no dice nada de este proveedor», no «no hay credencial»: quien
    llama sigue entonces con la cadena de siempre. Distinguirlo de una credencial declarada y
    rota es justo lo que permite que MT.2 no cambie el comportamiento del piloto.

    Se traen **las dos filas que pueden participar y ninguna más**: la de plataforma y la de esta
    organización. No es una optimización — es la diferencia entre resolver y devolver el secreto
    del municipio de al lado.
    """
    consulta = select(HubProviderCredential).where(
        HubProviderCredential.provider_id == provider_id
    )
    if organizacion_id is None:
        consulta = consulta.where(HubProviderCredential.organizacion_id.is_(None))
    else:
        # `or_` y no `IN (organizacion_id, None)`: en SQL `NULL IN (...)` es **nulo**, no
        # verdadero, así que un `IN` con NULL dentro no trae la fila de plataforma y la herencia
        # no funcionaría — que es justo el caso normal, porque hoy sólo existe ese nivel.
        consulta = consulta.where(
            or_(
                HubProviderCredential.organizacion_id == organizacion_id,
                HubProviderCredential.organizacion_id.is_(None),
            )
        )

    filas = list((await session.execute(consulta)).scalars())
    fila = de_esta_organizacion(filas, organizacion_id) or de_plataforma(filas)
    if fila is None:
        return None

    return _resolver_fila(fila, modo_de_despliegue=modo_de_despliegue)


def _resolver_fila(
    fila: HubProviderCredential, *, modo_de_despliegue: str | None
) -> CredencialDeProveedor:
    metodo = MetodoDeCredencial(fila.metodo)

    if metodo is MetodoDeCredencial.CLAVE:
        return CredencialDeProveedor(
            metodo=metodo,
            api_key=fila.api_key,
            base_url=fila.base_url,
            falta=None if fila.api_key else "la credencial declara una clave y está vacía",
        )

    if metodo is MetodoDeCredencial.VARIABLE_DE_ENTORNO:
        nombre = (fila.secret_env or "").strip()
        valor = os.getenv(nombre) if nombre else None
        if not nombre:
            falta = "la credencial declara una variable de entorno y no dice cuál"
        elif not valor:
            falta = f"la variable de entorno {nombre} no está definida"
        else:
            falta = None
        return CredencialDeProveedor(
            metodo=metodo, api_key=valor or None, base_url=fila.base_url, falta=falta
        )

    # entorno_de_ejecucion: sin clave, y eso no es una carencia.
    falta = None
    if fila.organizacion_id is not None and (modo_de_despliegue or "").lower() == "cloud":
        falta = (
            "las credenciales del entorno de ejecución (ADC) son las del proceso, y un proceso "
            "tiene una sola identidad: una credencial ADC por organización sólo funciona en "
            "modo edge, con un despliegue por organización"
        )
    return CredencialDeProveedor(metodo=metodo, base_url=fila.base_url, falta=falta)

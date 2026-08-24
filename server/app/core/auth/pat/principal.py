"""El alcance de organización de un token de acceso personal (MT.5).

Deploy: shared.

Un PAT **hereda** las organizaciones de su dueño y no las lleva guardadas, y eso lo decidió SEC.2
con buen motivo: guardarlas en la fila las congelaría, así que a un administrador al que se le
retira una organización le seguiría valiendo un token emitido antes — una revocación que no
revoca.

MT.5 no cambia eso. Añade lo contrario: que el token pueda **acotar**. Un token es una credencial
de máquina que vive meses en un fichero de configuración, y «la integración del ERP de Onda» no
tiene por qué poder tocar Nules sólo porque quien lo emitió administre las dos.

Las dos reglas que hacen que esto sea seguro:

- **Acota, nunca amplía.** El alcance del dueño se sigue resolviendo en cada validación y el del
  token se intersecta con él. Un token cuya organización ya no gestiona su dueño se queda sin
  ninguna, que es lo que tiene que pasar.
- **Nulo = donde valga su dueño**, que es lo que significan los tokens que ya existen. Acotarlos
  en la migración habría roto integraciones que funcionan sin avisar a nadie.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from server.app.core.auth.models import UserInfo


def acota_a_la_organizacion(dueno: UserInfo, pat: Any) -> UserInfo:
    """El principal del dueño, acotado a la organización que declare el token.

    Con un token sin organización, el principal sale tal cual. Con una declarada, el resultado
    es la intersección: nunca más de lo que tiene el dueño.

    **El superadministrador es el caso a no equivocar.** Su lista vacía significa «todas» (ver
    `UserInfo.organizacion_ids`), así que intersecarla como si fuera un conjunto vacío dejaría el
    token sin acceso a nada. Un token de superadministrador acotado a una organización vale
    exactamente en ésa, que es acotar de verdad y no anular.
    """
    declarada = getattr(pat, "organizacion_id", None)
    if declarada is None:
        return dueno

    pedida = str(declarada)
    if getattr(dueno, "is_superadmin", False) and not dueno.organizacion_ids:
        alcance: tuple[str, ...] = (pedida,)
    else:
        alcance = (pedida,) if pedida in dueno.organizacion_ids else ()

    return replace(dueno, organizacion_ids=alcance)

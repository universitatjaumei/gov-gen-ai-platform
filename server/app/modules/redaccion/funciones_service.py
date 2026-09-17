"""Las guardas del catálogo de funciones (FUN.1).

Deploy: edge — el código y la declaración de una función de autoservicio son de la organización.

Tres reglas viven aquí y no en la base, y cada una por su motivo:

1. **La coherencia por origen** son cuatro reglas cruzadas entre dos tablas (`autoservicio` exige
   código, finalidad y quién declara; `paquete` exige *entry point* y semver y **prohíbe**
   código). Un `CheckConstraint` podría expresar parte, pero no puede decir *qué falta*, y es
   justo lo que necesita quien está rellenando el formulario.
2. **La inmutabilidad de una versión registrada.** Corregir es publicar otra versión: el código de
   una versión registrada no se edita jamás, por la misma razón que no se edita un registro de
   auditoría. Sin ella, «arreglar una vez» sería «cambiar en silencio informes ya aprobados».
3. **El motivo al suspender.** El bloque anclado a una versión suspendida falla en alto *con el
   motivo* (FUN.3); sin motivo, ese fallo no podría explicarse. Suspender es de quien revisa y
   retirar es de quien escribe: dos responsabilidades distintas de la matriz de la Instrucció §9.

Nada de esto sabe de «informe»: el catálogo es una pieza compartida y en Fase 3 lo consumen las
fases de expediente.
"""
from __future__ import annotations

import hashlib
import uuid
from typing import Any

#: Los campos que **sí** se pueden escribir sobre una versión que ya no es borrador: son de otra
#: persona y de otro momento —la revisión posterior y la suspensión de la Instrucció §8.4— y no
#: cambian lo que se ejecuta.
CAMPOS_POSTERIORES: frozenset[str] = frozenset({
    "estado",
    "revisada_por",
    "revisada_en",
    "revision_resultado",
    "revision_nota",
    "suspendida_por",
    "suspendida_en",
    "motivo_suspension",
})

#: Estados en los que una versión ya no admite cambios de contenido.
ESTADOS_CERRADOS: frozenset[str] = frozenset(
    {"registrada", "suspendida", "retirada", "no_instalada"}
)


class FuncionIncoherente(ValueError):
    """Los datos de una versión no encajan con su origen, o falta la declaración responsable."""


class VersionInmutable(RuntimeError):
    """Se ha intentado cambiar el contenido de una versión que ya no es un borrador."""


def sha256_del_codigo(code: str) -> str:
    """El hash de lo que va a ejecutarse, que es lo que el `RunManifest` registra.

    Se calcula al escribir y no lo aporta quien llama: un hash que viniera de fuera podría no
    corresponder al código, y entonces el manifiesto diría que corrió algo que no corrió.
    """
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def datos_de_version_coherentes(
    *,
    origen: str,
    code: str | None = None,
    finalidad: str | None = None,
    declarada_por: uuid.UUID | None = None,
    categorias_datos: list[str] | None = None,
    version_paquete: str | None = None,
    entry_point: str | None = None,
) -> None:
    """Comprueba la forma de una versión según su origen. Levanta `FuncionIncoherente`.

    El mensaje dice **qué falta**, porque esto se ve en un formulario: «falta el código» es
    accionable y «datos incoherentes» no lo es.
    """
    if origen == "autoservicio":
        if not code or not code.strip():
            raise FuncionIncoherente(
                "una función de autoservicio necesita su código: es lo que se audita y lo que "
                "corre en el sandbox"
            )
        if not finalidad or not finalidad.strip():
            raise FuncionIncoherente(
                "falta la finalidad de la declaración responsable, que la Instrucció 02/2026 "
                "exige registrar antes de compartir (§8.2)"
            )
        if declarada_por is None:
            raise FuncionIncoherente(
                "falta quién declara: una declaración responsable sin responsable no es una "
                "declaración"
            )
        if version_paquete is not None:
            raise FuncionIncoherente(
                "una función de autoservicio no tiene versión de paquete: su versionado es el "
                "ordinal del catálogo"
            )
        return

    if origen == "paquete":
        if code is not None:
            raise FuncionIncoherente(
                "una función empaquetada no guarda su código aquí: vive en el paquete, y una "
                "copia divergiría del `pip install` sin que nada avisara"
            )
        if not version_paquete:
            raise FuncionIncoherente(
                "falta la versión (semver) de la distribución instalada"
            )
        if not entry_point:
            raise FuncionIncoherente(
                "falta el punto de entrada «distribucion:nombre» que identifica la función"
            )
        return

    raise FuncionIncoherente(
        f"«{origen}» no es un origen conocido; los que hay son autoservicio y paquete"
    )


def asegurar_editable(version: Any, cambios: dict[str, Any]) -> None:
    """Deja pasar los cambios admisibles sobre una versión, o levanta.

    Un borrador se edita entero. Una versión cerrada sólo admite los campos de la revisión
    posterior y de la suspensión — y suspender, además, exige motivo.
    """
    estado_actual = getattr(version, "estado", "draft")

    if estado_actual not in ESTADOS_CERRADOS:
        _exigir_motivo_al_suspender(version, cambios)
        return

    de_contenido = sorted(set(cambios) - CAMPOS_POSTERIORES)
    if de_contenido:
        raise VersionInmutable(
            f"una versión en estado «{estado_actual}» no cambia "
            f"{', '.join(de_contenido)}: corregir es publicar una versión nueva"
        )

    _exigir_motivo_al_suspender(version, cambios)


def _exigir_motivo_al_suspender(version: Any, cambios: dict[str, Any]) -> None:
    if cambios.get("estado") != "suspendida":
        return
    motivo = cambios.get("motivo_suspension") or getattr(version, "motivo_suspension", None)
    if not motivo or not str(motivo).strip():
        raise FuncionIncoherente(
            "suspender exige motivo: el bloque anclado a esta versión va a fallar en alto y "
            "tiene que poder decir por qué"
        )


def consulta_de_catalogo(*, organizacion_id: uuid.UUID | None):
    """Las funciones que una organización puede ver: las suyas y las publicadas.

    Nunca las no publicadas de otra. Es la misma frontera de siempre, escrita una vez aquí para
    que el router, el resolutor y el catálogo del panel no la escriban cada uno a su manera.
    """
    from sqlalchemy import or_, select

    from server.app.modules.redaccion.database.models import HubFuncion

    publicadas = or_(
        HubFuncion.publicada_en.isnot(None),
        HubFuncion.organizacion_id.is_(None),
    )
    if organizacion_id is None:
        # Sin organización sólo se ven las de plataforma: es lo que responde la tenencia a un
        # principal sin organización, y no «todas».
        return select(HubFuncion).where(publicadas)

    return select(HubFuncion).where(
        or_(HubFuncion.organizacion_id == organizacion_id, publicadas)
    )

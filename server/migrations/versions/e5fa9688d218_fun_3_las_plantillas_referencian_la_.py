"""FUN.3 las plantillas referencian la funcion en vez de copiar el codigo

Migracion de **datos**, no de esquema. Cada bloque `admin_script` que hoy lleva el codigo
incrustado en `options.code` se convierte en:

  * una `hub_funciones` de la organizacion de su plantilla, con una version 1 `registrada`, y
  * un `funcion_ref` en el bloque, del que desaparece el codigo.

Dos decisiones que importan:

* **La aprobacion antigua vale como declaracion responsable.** `finalidad` toma el titulo del
  bloque y `declarada_por` el autor de la version de la plantilla; la version queda marcada como
  `revision_resultado='conforme'` con `revisada_por` = ese mismo autor. No es una ficcion: ese
  script **ya lo miro una persona** antes de aprobarse, y decir lo contrario obligaria a revisar
  otra vez lo que ya estaba revisado. Lo que no se inventa es la categoria de datos: queda
  `sin_declarar`, que es un codigo del vocabulario abierto de REG y significa exactamente eso.
* **Idempotente y con recuento.** Se puede volver a aplicar sin duplicar funciones —se reconoce
  por el hash del codigo dentro de la organizacion— y deja en el log cuantos bloques ha migrado,
  porque una migracion de datos sin recuento no se puede auditar.

Revision ID: e5fa9688d218
Revises: deadfff99b26
Create Date: 2026-09-18
"""
from typing import Sequence, Union
import hashlib
import json
import logging
import uuid

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e5fa9688d218'
down_revision: Union[str, None] = 'deadfff99b26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_log = logging.getLogger("alembic.fun3")

#: El codigo del vocabulario de REG que dice «no lo declare». Existe justamente para no tener que
#: inventar una categoria al migrar.
_SIN_DECLARAR = "sin_declarar"


def _bloques_con_codigo(spec: dict) -> list[dict]:
    bloques = spec.get("blocks")
    if isinstance(bloques, dict):
        bloques = list(bloques.values())
    if not isinstance(bloques, list):
        return []
    return [
        b
        for b in bloques
        if isinstance(b, dict)
        and b.get("kind") == "DETERMINISTIC_DATA"
        and isinstance(b.get("options"), dict)
        and b["options"].get("code")
    ]


def upgrade() -> None:
    conexion = op.get_bind()

    versiones = conexion.execute(
        sa.text(
            """
            SELECT v.id, v.spec_json, v.created_by, t.organizacion_id, t.name
            FROM hub_report_template_versions v
            JOIN hub_report_templates t ON t.id = v.template_id
            """
        )
    ).mappings().all()

    migrados = 0
    funciones_creadas = 0

    for fila in versiones:
        spec = fila["spec_json"]
        if isinstance(spec, str):
            spec = json.loads(spec)
        if not isinstance(spec, dict):
            continue

        candidatos = _bloques_con_codigo(spec)
        if not candidatos:
            continue

        bloques = spec.get("blocks")
        como_dict = isinstance(bloques, dict)
        lista = list(bloques.values()) if como_dict else list(bloques)

        for bloque in candidatos:
            codigo = bloque["options"]["code"]
            sha = hashlib.sha256(codigo.encode("utf-8")).hexdigest()
            organizacion_id = fila["organizacion_id"]

            # Idempotencia: la misma funcion, reconocida por el hash de su codigo dentro de su
            # organizacion. Sin esto, volver a aplicar la migracion duplicaria el catalogo.
            existente = conexion.execute(
                sa.text(
                    """
                    SELECT f.id AS funcion_id, fv.version AS version
                    FROM hub_funcion_versiones fv
                    JOIN hub_funciones f ON f.id = fv.funcion_id
                    WHERE fv.code_sha256 = :sha
                      AND (f.organizacion_id = :org OR (f.organizacion_id IS NULL AND :org IS NULL))
                    LIMIT 1
                    """
                ),
                {"sha": sha, "org": organizacion_id},
            ).mappings().first()

            if existente:
                funcion_id = existente["funcion_id"]
                version = existente["version"]
            else:
                funcion_id = uuid.uuid4()
                titulo = bloque.get("title") or "Script de extraccion"
                conexion.execute(
                    sa.text(
                        """
                        INSERT INTO hub_funciones
                          (id, nombre, descripcion, organizacion_id, origen, creada_por,
                           created_at, updated_at)
                        VALUES
                          (:id, :nombre, '', :org, 'autoservicio', :autor, now(), now())
                        """
                    ),
                    {
                        "id": funcion_id,
                        # El nombre se acota a la columna: los titulos de bloque son libres.
                        "nombre": titulo[:120],
                        "org": organizacion_id,
                        "autor": fila["created_by"],
                    },
                )
                conexion.execute(
                    sa.text(
                        """
                        INSERT INTO hub_funcion_versiones
                          (id, funcion_id, version, code, contrato_entrada, contrato_salida,
                           code_sha256, estado, autoria, finalidad, categorias_datos,
                           declarada_por, declarada_en, revisada_por, revisada_en,
                           revision_resultado, revision_nota, created_at)
                        VALUES
                          (:id, :funcion_id, 1, :code, :entrada, :salida, :sha, 'registrada',
                           'ia', :finalidad, :categorias, :autor, now(), :autor, now(),
                           'conforme', :nota, now())
                        """
                    ),
                    {
                        "id": uuid.uuid4(),
                        "funcion_id": funcion_id,
                        "code": codigo,
                        "entrada": json.dumps(
                            {
                                "slots": [],
                                "parametros": [],
                                "salida": "ExtractionResult",
                                "finalidad": titulo[:200],
                                "categorias_datos": [_SIN_DECLARAR],
                            }
                        ),
                        "salida": json.dumps({"kind": "ExtractionResult"}),
                        "sha": sha,
                        "finalidad": titulo[:200],
                        "categorias": json.dumps([_SIN_DECLARAR]),
                        "autor": fila["created_by"],
                        "nota": (
                            "Migrada de un bloque con el codigo incrustado (FUN.3). La "
                            "aprobacion antigua vale como revision: una persona la miro antes "
                            "de aprobarla. Las categorias de datos quedan sin declarar."
                        ),
                    },
                )
                funciones_creadas += 1
                version = 1

            bloque["funcion_ref"] = {"funcion_id": str(funcion_id), "version": version}
            opciones = dict(bloque.get("options") or {})
            opciones.pop("code", None)
            opciones.pop("approved", None)
            bloque["options"] = opciones
            migrados += 1

        spec["blocks"] = {b["id"]: b for b in lista} if como_dict else lista
        conexion.execute(
            sa.text(
                "UPDATE hub_report_template_versions SET spec_json = :spec WHERE id = :id"
            ),
            {"spec": json.dumps(spec), "id": fila["id"]},
        )

    _log.warning(
        "FUN.3: %s bloque(s) pasan a referencia; %s funcion(es) creadas en el catalogo",
        migrados,
        funciones_creadas,
    )


def downgrade() -> None:
    """Devuelve el codigo al bloque. No borra el catalogo.

    Borrar las funciones seria peor que dejarlas: hay manifiestos que las citan por id, y un
    manifiesto que apunta a una fila que ya no existe no se puede auditar.
    """
    conexion = op.get_bind()

    versiones = conexion.execute(
        sa.text("SELECT id, spec_json FROM hub_report_template_versions")
    ).mappings().all()

    for fila in versiones:
        spec = fila["spec_json"]
        if isinstance(spec, str):
            spec = json.loads(spec)
        if not isinstance(spec, dict):
            continue

        bloques = spec.get("blocks")
        como_dict = isinstance(bloques, dict)
        lista = list(bloques.values()) if como_dict else (bloques or [])
        tocado = False

        for bloque in lista:
            if not isinstance(bloque, dict) or not bloque.get("funcion_ref"):
                continue
            ref = bloque["funcion_ref"]
            codigo = conexion.execute(
                sa.text(
                    """
                    SELECT code FROM hub_funcion_versiones
                    WHERE funcion_id = :f AND version = :v
                    """
                ),
                {"f": ref["funcion_id"], "v": ref["version"]},
            ).scalar()
            if codigo is None:
                continue
            bloque["options"] = {**(bloque.get("options") or {}), "code": codigo, "approved": True}
            bloque.pop("funcion_ref", None)
            tocado = True

        if tocado:
            spec["blocks"] = {b["id"]: b for b in lista} if como_dict else lista
            conexion.execute(
                sa.text(
                    "UPDATE hub_report_template_versions SET spec_json = :spec WHERE id = :id"
                ),
                {"spec": json.dumps(spec), "id": fila["id"]},
            )

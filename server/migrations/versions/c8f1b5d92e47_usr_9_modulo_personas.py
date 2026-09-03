"""USR.9 — el módulo `personas`, para que un admin llegue a las personas de su organización.

La pantalla vivía bajo el módulo `plataforma`, que es **administración de la plataforma**: los
modelos de LLM, las organizaciones, los tokens, los módulos y la identidad visual. Un
administrador de organización no lo tiene ni debe tenerlo, así que la capacidad que USR.1 le dio
—fijar la contraseña de alguien de su organización— existía por API y no por pantalla.

**Se añade un módulo en vez de un rol** porque es la decisión de INF.7, escrita en
`core/auth/modulos.py`: *por módulos concedidos, no por rol nuevo*. Y el catálogo es tabla y no
`Enum` por el mismo motivo que el vocabulario del corpus, así que la fila entra aquí.

**Y se concede a quien ya tenía `plataforma`**, con el mismo `INSERT ... SELECT` idempotente que
usó PLAT.1: sin esto, mover la pantalla de sitio se la quitaría a quien la usaba.

Revision ID: c8f1b5d92e47
Revises: b7e0a4c81259
"""
from alembic import op
import sqlalchemy as sa

revision = "c8f1b5d92e47"
down_revision = "b7e0a4c81259"
branch_labels = None
depends_on = None

_MODULO = "personas"
_ETIQUETA = "Personas de la organización"
_FIRMA = "migracion:usr9"


def upgrade() -> None:
    conexion = op.get_bind()

    # El catálogo primero: `modulos_del_usuario` cruza las concesiones con los módulos
    # `vigente`, así que sin la fila del catálogo la concesión no daría acceso a nada.
    conexion.execute(
        sa.text(
            "INSERT INTO hub_platform_modules (code, label, vigente)"
            " VALUES (:code, :label, true)"
            " ON CONFLICT (code) DO NOTHING"
        ),
        {"code": _MODULO, "label": _ETIQUETA},
    )

    # El `ON CONFLICT` va **por nombre de restricción** y no por columnas: la de PLAT.1 decía
    # `(subject_id, module_code)` y esa clave ya no existe —MT.5 le añadió `subject_type` y
    # `organizacion_id`, porque la misma persona con el mismo módulo en dos organizaciones son
    # dos concesiones legítimas—. Copiarla tal cual falla en alto con «there is no unique or
    # exclusion constraint matching the ON CONFLICT specification», que al menos es ruidoso.
    #
    # Y por lo mismo se copian los cuatro campos de la clave: conceder `personas` «en todas»
    # a quien tiene `plataforma` en una sola organización sería ampliarle el alcance.
    conexion.execute(
        sa.text(
            "INSERT INTO hub_module_grants"
            " (subject_type, subject_id, module_code, organizacion_id, granted_by)"
            " SELECT DISTINCT g.subject_type, g.subject_id, :modulo, g.organizacion_id, :firma"
            "   FROM hub_module_grants AS g"
            "  WHERE g.module_code = 'plataforma'"
            " ON CONFLICT ON CONSTRAINT uq_grant_subject_type_module DO NOTHING"
        ),
        {"modulo": _MODULO, "firma": _FIRMA},
    )


def downgrade() -> None:
    conexion = op.get_bind()
    # Sólo las concesiones que puso esta migración: una puesta a mano después es de su autor.
    conexion.execute(
        sa.text(
            "DELETE FROM hub_module_grants WHERE module_code = :modulo AND granted_by = :firma"
        ),
        {"modulo": _MODULO, "firma": _FIRMA},
    )
    conexion.execute(
        sa.text("DELETE FROM hub_platform_modules WHERE code = :modulo"),
        {"modulo": _MODULO},
    )

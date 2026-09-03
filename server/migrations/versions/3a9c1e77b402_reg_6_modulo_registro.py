"""REG.6 — el módulo `registro`, para llegar al registro de actividad IA.

**Un módulo y no un rol**, que es la decisión de INF.7 escrita en `core/auth/modulos.py`; y el
catálogo es tabla y no `Enum` por el mismo motivo que el vocabulario del corpus, así que la fila
entra aquí y no en el código.

**Módulo propio y no dentro de `plataforma`**, aunque la pantalla sea de administración. El
criterio está escrito en `PlataformaLayout.tsx`: ahí va la configuración de la plataforma
(`Deploy: cloud`) y el registro es dato **operacional** de la organización (`Deploy: edge`).
Meterlo en `plataforma` obligaría a conceder los modelos de LLM, las organizaciones y los tokens
para poder conceder el registro — que es exactamente el problema que PLAT.2 y USR.9 arreglaron,
en un caso y en el opuesto.

**Y se concede a quien ya tenía `plataforma`**, con el mismo `INSERT ... SELECT` idempotente de
PLAT.1 y USR.9: quien administra hoy la instalación es quien va a mirar este registro, y hacerle
pedir la concesión de un módulo que se estrena con la pantalla no gana nada.

El `ON CONFLICT` va **por nombre de restricción**: la clave lleva `subject_type` y
`organizacion_id` desde MT.5, porque la misma persona con el mismo módulo en dos organizaciones
son dos concesiones legítimas. Y por lo mismo se copian los cuatro campos: conceder `registro`
«en todas» a quien tiene `plataforma` en una sola sería ampliarle el alcance.

Revision ID: 3a9c1e77b402
Revises: 28d7fafbf4af
Create Date: 2026-09-03
"""
from alembic import op
import sqlalchemy as sa

revision = "3a9c1e77b402"
down_revision = "28d7fafbf4af"
branch_labels = None
depends_on = None

_MODULO = "registro"
_ETIQUETA = "Registro de actividad IA"
_FIRMA = "migracion:reg6"


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

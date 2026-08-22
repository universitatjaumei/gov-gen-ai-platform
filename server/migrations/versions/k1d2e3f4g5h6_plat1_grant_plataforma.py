"""PLAT.1 — a quien tenga `chatbots` y no `plataforma`, dale `plataforma`

El Bloque PLAT declara `require_module("plataforma")` en los routers de configuración
(PLAT.5). Hoy la única pantalla que lo exige —`hub_llm_configs`— está montada bajo el módulo
`chatbots`, así que quien administra la plataforma llega ahí con esa concesión. Declarar la
frontera sin repartir antes el módulo deja a esa persona fuera, y el síntoma llega como un 403.

**Es un relleno, no una siembra, y en muchas instalaciones no hará nada.** El prompt del plan
suponía que «nadie tiene `plataforma` salvo los superadmin», y está medido a medias: la migración
de INF.7 (`j0c1d2e3f4g5`) ya concede **los cuatro módulos** a cada fila de `superadminaccount` y
`adminaccount`. Lo que quedó descubierto es lo que INF.7 no podía ver:

- Sujetos a los que se concedió `chatbots` **después** de aquella migración.
- **Usuarios de SSO**: INF.7 solo leyó las dos tablas de cuenta, así que ninguna identidad
  aprovisionada por el IdP recibió nada.

Que no haga nada donde no hace falta es la propiedad que se busca, no un defecto.

**Las filas van firmadas** (`granted_by = 'migracion:plat1'`). Sin firma, `downgrade` no podría
distinguir lo que creó esta migración de una concesión que puso una persona, y revertir se
llevaría por delante un permiso legítimo. Por el mismo motivo el `INSERT` no pisa `granted_by` de
una fila que ya existe: `granted_by` es la auditoría del permiso —«un permiso sin autoría no se
puede auditar», dice el modelo— y sobreescribirla la borra.

Revision ID: k1d2e3f4g5h6
Revises: j0c1d2e3f4g5
Create Date: 2026-08-22
"""
from alembic import op
import sqlalchemy as sa

revision = "k1d2e3f4g5h6"
down_revision = "j0c1d2e3f4g5"
branch_labels = None
depends_on = None

_MODULO = "plataforma"
_ETIQUETA = "Administración de la plataforma"
_FIRMA = "migracion:plat1"


def upgrade() -> None:
    conexion = op.get_bind()

    # El catálogo primero: `modulos_del_usuario` cruza las concesiones con los módulos
    # `vigente`, así que sin la fila del catálogo el relleno sería decorativo. `MODULOS_INICIALES`
    # es semilla y no definición, así que una instalación puede no tenerla.
    conexion.execute(
        sa.text(
            "INSERT INTO hub_platform_modules (code, label, vigente)"
            " VALUES (:code, :label, true)"
            " ON CONFLICT (code) DO NOTHING"
        ),
        {"code": _MODULO, "label": _ETIQUETA},
    )

    # Un solo INSERT ... SELECT: la lista de sujetos sale de la propia tabla, así que no hay
    # que leerla a Python ni depender de qué tablas de identidad existan en este despliegue.
    # `ON CONFLICT DO NOTHING` es lo que lo hace idempotente y lo que respeta la autoría de
    # una concesión anterior.
    conexion.execute(
        sa.text(
            "INSERT INTO hub_module_grants (subject_id, module_code, granted_by)"
            " SELECT DISTINCT g.subject_id, :modulo, :firma"
            "   FROM hub_module_grants AS g"
            "  WHERE g.module_code = 'chatbots'"
            " ON CONFLICT (subject_id, module_code) DO NOTHING"
        ),
        {"modulo": _MODULO, "firma": _FIRMA},
    )


def downgrade() -> None:
    # Solo lo suyo. Una concesión de `plataforma` que puso una persona lleva otra firma —o
    # ninguna— y se queda.
    op.get_bind().execute(
        sa.text(
            "DELETE FROM hub_module_grants"
            " WHERE module_code = :modulo AND granted_by = :firma"
        ),
        {"modulo": _MODULO, "firma": _FIRMA},
    )

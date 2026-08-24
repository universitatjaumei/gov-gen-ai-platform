"""MT.5 — el permiso dice dónde.

Una concesión decía «informes», no «informes en el ayuntamiento de X». Con una organización da
igual; con veinte, conceder un módulo a un grupo del IdP se lo concede **en todas**, y en el
modelo Diputación→municipios eso es dar acceso a los informes de veinte ayuntamientos a la vez.

**La regla que hace segura la migración: nulo sigue significando «en todas».** Las 0 concesiones
y los tokens que existan hoy no nombran organización, y eso es exactamente lo que significan
ahora. Reinterpretarlos en silencio como «en ninguna» le quitaría los permisos a todo el mundo;
como «en la primera» sería inventárselo. Nulo = como hasta ahora, y quien quiera acotar lo dice.

**La unicidad de la concesión pasa de tres columnas a cuatro**, con `NULLS NOT DISTINCT`: la
misma persona con el mismo módulo en dos organizaciones son **dos** concesiones legítimas, pero
dos «en todas» idénticas siguen siendo un duplicado — y en Postgres `NULL != NULL`, así que sin
esa cláusula el nivel donde están todas las filas de hoy se quedaría sin proteger.

En el token, `organizacion_id` **acota y nunca amplía**: el alcance del dueño se sigue
resolviendo en cada validación (SEC.2) y el del token se intersecta con él. Es lo que evita que
un token sobreviva a la retirada de una organización, que sería una revocación que no revoca.

Revision ID: s9l0m1n2o3p4
Revises: r8k9l0m1n2o3
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "s9l0m1n2o3p4"
down_revision = "r8k9l0m1n2o3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_module_grants",
        sa.Column("organizacion_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_grant_organizacion",
        "hub_module_grants",
        "hub_organizaciones",
        ["organizacion_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_hub_module_grants_organizacion_id", "hub_module_grants", ["organizacion_id"]
    )
    # La clave gana la organización. Se retira la de tres columnas y se pone la de cuatro:
    # dejar las dos haría que la vieja siguiera prohibiendo el caso legítimo.
    op.drop_constraint(
        "uq_grant_subject_type_module", "hub_module_grants", type_="unique"
    )
    op.execute(
        "ALTER TABLE hub_module_grants "
        "ADD CONSTRAINT uq_grant_subject_type_module "
        "UNIQUE NULLS NOT DISTINCT (subject_type, subject_id, module_code, organizacion_id)"
    )

    op.add_column(
        "hub_personal_access_tokens",
        sa.Column("organizacion_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_pat_organizacion",
        "hub_personal_access_tokens",
        "hub_organizaciones",
        ["organizacion_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_hub_personal_access_tokens_organizacion_id",
        "hub_personal_access_tokens",
        ["organizacion_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_hub_personal_access_tokens_organizacion_id",
        table_name="hub_personal_access_tokens",
    )
    op.drop_constraint(
        "fk_pat_organizacion", "hub_personal_access_tokens", type_="foreignkey"
    )
    op.drop_column("hub_personal_access_tokens", "organizacion_id")

    # Bajar puede encontrarse con dos concesiones que sólo se distinguen por la organización, y
    # la clave de tres columnas no las admite. Se retiran las acotadas: son las que este eje
    # creó, y conservarlas exigiría elegir cuál sobrevive — una decisión que un `downgrade` no
    # puede tomar en silencio.
    op.execute("DELETE FROM hub_module_grants WHERE organizacion_id IS NOT NULL")
    op.execute(
        "ALTER TABLE hub_module_grants DROP CONSTRAINT uq_grant_subject_type_module"
    )
    op.create_unique_constraint(
        "uq_grant_subject_type_module",
        "hub_module_grants",
        ["subject_type", "subject_id", "module_code"],
    )
    op.drop_index("ix_hub_module_grants_organizacion_id", table_name="hub_module_grants")
    op.drop_constraint("fk_grant_organizacion", "hub_module_grants", type_="foreignkey")
    op.drop_column("hub_module_grants", "organizacion_id")

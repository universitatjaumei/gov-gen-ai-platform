"""MT.4 — Informes gana la dimensión que no tiene, y la procedencia de lo copiado.

`owner_kind` admitía `user`, `platform` y `superadmin`: **no existía `organizacion`**. Una
plantilla era de una persona o de todo el mundo, sin nada en medio. La escalera completa que pidió
el usuario es **usuario → organización → plataforma**, y los dos extremos ya estaban: en esta base
hay 20 plantillas de plataforma, 2 personales de un superadministrador y 1 de un usuario.

**Cuatro cambios.**

1. `organizacion_id` en `hub_report_templates` y en `hub_workspaces`, nullable. Nulo = lo de
   siempre, así que las 23 plantillas y los 29 informes existentes no se tocan.
2. `CheckConstraint` de coherencia: `owner_kind='organizacion'` exige `organizacion_id`. En la
   base y no sólo en el modelo, porque una plantilla «de organización» que no dice de cuál no la
   encuentra ninguna consulta ni la excluye ninguna: se cuela en los dos lados.
3. **`is_global` deja de ser columna.** Se calculaba en el router como `owner_kind == "platform"`,
   así que dos sitios guardaban el mismo hecho. Los datos confirman que coinciden —`platform`↔true
   en las 20, false en las 3 restantes—, así que pasa a `hybrid_property` y la columna se retira.
   Dos columnas para un hecho terminan discrepando, y cuando discrepan no hay cómo saber cuál
   manda.
4. **La procedencia** (`derivado_de`, `version_de_origen`), que el plan tenía como MT.4.2 aparte.
   **Se adelanta aquí a propósito**: MT.4 trae la bifurcación —un administrador tiene que poder
   adaptar la plantilla heredada de la Diputación sin cambiársela a los demás— y ésa es su primera
   consumidora. Meter las columnas en un prompt anterior habría sido dejarlas sin nadie que las
   lea, que es justo el código especulativo que las reglas prohíben.

**`ON DELETE SET NULL` en `derivado_de`, no CASCADE.** Con CASCADE, retirar la plantilla de la
Diputación borraría las de los municipios que la habían adaptado. La procedencia es una anotación
histórica, no una dependencia.

Revision ID: r8k9l0m1n2o3
Revises: q7j8k9l0m1n2
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "r8k9l0m1n2o3"
down_revision = "q7j8k9l0m1n2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_report_templates",
        sa.Column("organizacion_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_hub_report_templates_organizacion_id",
        "hub_report_templates",
        ["organizacion_id"],
    )
    op.add_column(
        "hub_report_templates",
        sa.Column("derivado_de", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_report_template_derivado_de",
        "hub_report_templates",
        "hub_report_templates",
        ["derivado_de"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_hub_report_templates_derivado_de", "hub_report_templates", ["derivado_de"]
    )
    op.add_column(
        "hub_report_templates",
        sa.Column("version_de_origen", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_report_template_organizacion_coherente",
        "hub_report_templates",
        "owner_kind <> 'organizacion' OR organizacion_id IS NOT NULL",
    )
    # `is_global` pasa a derivarse de `owner_kind`. Se comprueba antes de retirarla: si algún día
    # los datos no coincidieran, este `upgrade` tiene que parar en vez de perder la distinción.
    op.execute(
        """
        DO $$
        DECLARE discrepantes int;
        BEGIN
            SELECT count(*) INTO discrepantes
            FROM hub_report_templates
            WHERE is_global <> (owner_kind = 'platform');
            IF discrepantes > 0 THEN
                RAISE EXCEPTION
                    'Hay % plantillas donde is_global y owner_kind no coinciden: '
                    'revísalas antes de retirar la columna', discrepantes;
            END IF;
        END $$;
        """
    )
    op.drop_column("hub_report_templates", "is_global")

    op.add_column(
        "hub_workspaces",
        sa.Column("organizacion_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_hub_workspaces_organizacion_id", "hub_workspaces", ["organizacion_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_hub_workspaces_organizacion_id", table_name="hub_workspaces")
    op.drop_column("hub_workspaces", "organizacion_id")

    op.add_column(
        "hub_report_templates",
        sa.Column("is_global", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Se repuebla desde `owner_kind`, que es de donde salía: bajar no puede dejar la columna a
    # false y esconder las 20 plantillas de plataforma de todas las listas.
    op.execute(
        "UPDATE hub_report_templates SET is_global = (owner_kind = 'platform')"
    )
    op.alter_column("hub_report_templates", "is_global", server_default=None)

    op.drop_constraint(
        "ck_report_template_organizacion_coherente",
        "hub_report_templates",
        type_="check",
    )
    op.drop_column("hub_report_templates", "version_de_origen")
    op.drop_index("ix_hub_report_templates_derivado_de", table_name="hub_report_templates")
    op.drop_constraint(
        "fk_report_template_derivado_de", "hub_report_templates", type_="foreignkey"
    )
    op.drop_column("hub_report_templates", "derivado_de")
    op.drop_index(
        "ix_hub_report_templates_organizacion_id", table_name="hub_report_templates"
    )
    op.drop_column("hub_report_templates", "organizacion_id")

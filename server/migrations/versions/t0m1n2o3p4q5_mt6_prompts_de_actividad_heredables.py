"""MT.6 — un municipio puede escribir su propio prompt.

`HubActivityPrompt.activity` era único **global**: defendible para una actividad de plataforma, y
deja de serlo en cuanto un municipio quiere su propia redacción — que es exactamente lo que esta
tabla existe para permitir, sólo un escalón más arriba de lo que hacía falta.

`organizacion_id` nullable, y **la unicidad pasa de `activity` a (activity, organizacion_id)** con
`NULLS NOT DISTINCT`. Esa cláusula es lo que hace que la protección siga valiendo en el nivel de
plataforma —el de todas las filas de hoy—: en Postgres `NULL != NULL`, así que una unicidad
corriente sobre las dos columnas dejaría meter dos overrides de plataforma para la misma actividad,
que serían dos respuestas a una pregunta con una sola.

Es la misma trampa que el docstring del modelo advertía sobre hacer `chatbot_id` nullable en
`hub_prompt_templates`; aquí se evita con la cláusula en vez de con otra tabla.

Las filas existentes quedan a nulo, que es «de la plataforma», así que el piloto no nota nada.

Revision ID: t0m1n2o3p4q5
Revises: s9l0m1n2o3p4
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "t0m1n2o3p4q5"
down_revision = "s9l0m1n2o3p4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_activity_prompts",
        sa.Column("organizacion_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_activity_prompt_organizacion",
        "hub_activity_prompts",
        "hub_organizaciones",
        ["organizacion_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_hub_activity_prompts_organizacion_id",
        "hub_activity_prompts",
        ["organizacion_id"],
    )
    # La unicidad de `activity` la creó SQLAlchemy con `unique=True`, así que el nombre lo puso
    # él. Se busca en el catálogo en vez de escribirlo: un nombre adivinado que no exista deja
    # la restricción vieja puesta, y entonces la segunda organización seguiría chocando.
    op.execute(
        """
        DO $$
        DECLARE nombre text;
        BEGIN
            SELECT conname INTO nombre
            FROM pg_constraint
            WHERE conrelid = 'hub_activity_prompts'::regclass
              AND contype = 'u'
              AND array_length(conkey, 1) = 1;
            IF nombre IS NOT NULL THEN
                EXECUTE format(
                    'ALTER TABLE hub_activity_prompts DROP CONSTRAINT %I', nombre
                );
            END IF;
        END $$;
        """
    )
    op.execute(
        "ALTER TABLE hub_activity_prompts "
        "ADD CONSTRAINT uq_activity_prompt_scope "
        "UNIQUE NULLS NOT DISTINCT (activity, organizacion_id)"
    )
    op.create_index(
        "ix_hub_activity_prompts_activity", "hub_activity_prompts", ["activity"]
    )


def downgrade() -> None:
    # Bajar puede encontrarse con dos overrides de la misma actividad en distintas
    # organizaciones, y la unicidad de una sola columna no los admite. Se retiran los acotados:
    # son los que este eje creó, y conservarlos exigiría elegir cuál sobrevive — una decisión
    # que un `downgrade` no puede tomar en silencio.
    op.execute("DELETE FROM hub_activity_prompts WHERE organizacion_id IS NOT NULL")
    op.drop_index("ix_hub_activity_prompts_activity", table_name="hub_activity_prompts")
    op.execute(
        "ALTER TABLE hub_activity_prompts DROP CONSTRAINT uq_activity_prompt_scope"
    )
    op.create_unique_constraint(
        "uq_activity_prompt_activity", "hub_activity_prompts", ["activity"]
    )
    op.drop_index(
        "ix_hub_activity_prompts_organizacion_id", table_name="hub_activity_prompts"
    )
    op.drop_constraint(
        "fk_activity_prompt_organizacion", "hub_activity_prompts", type_="foreignkey"
    )
    op.drop_column("hub_activity_prompts", "organizacion_id")

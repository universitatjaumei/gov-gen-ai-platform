"""MT.2 — proveedores y modelos dejan de ser globales.

Dos cambios y ninguno toca comportamiento, que es la condición de la fase 1 del bloque MT: todas
las filas existentes quedan en el nivel de plataforma y el piloto se comporta exactamente como
antes.

**1. `hub_llm_configs.organizacion_id`, nullable.** Nulo = de la plataforma, y lo heredan todas.
Los siete modelos de hoy quedan a nulo sin necesidad de tocarlos.

**2. `hub_provider_credentials`, tabla nueva.** El plan de MT.2 decía «`organizacion_id` nullable
en las dos tablas», y en `hub_providers` no se puede: su clave primaria es el texto `google` /
`vertex`, así que añadir una columna no permitiría dos Googles — haría falta cambiarle la clave
primaria con una clave ajena por medio y romper `/providers/{provider_id}`. Y al mirar las cuatro
filas reales resulta que no hace falta: esa tabla es un **catálogo de tipos** y ninguna de sus
filas tiene `api_key`. Lo que tiene que separarse por organización es la credencial.

La credencial declara **cómo** se obtiene, y los tres métodos son los que ya estaban en uso:
`clave` (literal, en la base), `variable_de_entorno` (la base guarda el **nombre**; es el método
que sirve a Secret Manager y el único que da credenciales por organización sin meter secretos en
la base) y `entorno_de_ejecucion` (ADC de Vertex, sin clave — que hasta ahora no se declaraba en
ninguna parte, así que «sin clave» era indistinguible de «mal configurado»).

**La unicidad va con `NULLS NOT DISTINCT`** (Postgres 15+), y eso es lo que la hace valer también
en el nivel de plataforma: en Postgres `NULL != NULL`, así que una restricción corriente dejaría
meter dos filas de plataforma para el mismo proveedor sin protestar — y ése es el caso más
probable, porque hoy es el único nivel que existe.

Revision ID: q7j8k9l0m1n2
Revises: p6i7j8k9l0m1
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "q7j8k9l0m1n2"
down_revision = "p6i7j8k9l0m1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_llm_configs",
        sa.Column("organizacion_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_llm_config_organizacion",
        "hub_llm_configs",
        "hub_organizaciones",
        ["organizacion_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_hub_llm_configs_organizacion_id", "hub_llm_configs", ["organizacion_id"]
    )

    op.create_table(
        "hub_provider_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_id", sa.String(length=50), nullable=False),
        sa.Column("organizacion_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metodo", sa.String(length=30), nullable=False),
        sa.Column("api_key", sa.String(length=255), nullable=True),
        sa.Column("secret_env", sa.String(length=255), nullable=True),
        sa.Column("base_url", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["provider_id"], ["hub_providers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["organizacion_id"], ["hub_organizaciones.id"], ondelete="CASCADE"
        ),
        sa.CheckConstraint(
            "metodo IN ('clave', 'variable_de_entorno', 'entorno_de_ejecucion')",
            name="ck_provider_credential_metodo",
        ),
    )
    op.create_index(
        "ix_hub_provider_credentials_organizacion_id",
        "hub_provider_credentials",
        ["organizacion_id"],
    )
    # `NULLS NOT DISTINCT` no lo emite `create_unique_constraint`, así que va en SQL crudo.
    op.execute(
        "ALTER TABLE hub_provider_credentials "
        "ADD CONSTRAINT uq_provider_credential_scope "
        "UNIQUE NULLS NOT DISTINCT (provider_id, organizacion_id)"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_hub_provider_credentials_organizacion_id",
        table_name="hub_provider_credentials",
    )
    op.drop_table("hub_provider_credentials")
    op.drop_index("ix_hub_llm_configs_organizacion_id", table_name="hub_llm_configs")
    op.drop_constraint("fk_llm_config_organizacion", "hub_llm_configs", type_="foreignkey")
    op.drop_column("hub_llm_configs", "organizacion_id")

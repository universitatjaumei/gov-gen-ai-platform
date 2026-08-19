"""LEG.4 — borrar las dos tablas de prompts del legacy de AutomatIA

`extraction_service_config` y `system_prompt` vienen del esquema inicial, así que no desaparecen
solas. Su único consumidor (`knowledge_orchestrator_service`) se retiró en LEG.3 y la siembra del
arranque en LEG.2. Dejarlas vacías sería peor que borrarlas: una tabla que existe invita a que
alguien la use.

Lo que decían esos ocho prompts y qué se salvó de ellos está en
`docs/COMPARATIVA_PROMPTS_LEGACY.md`. Los prompts vivos son `hub_prompt_templates` (por asistente) y
`hub_activity_prompts` (por actividad), que esta migración no toca.

Revision ID: h8a9d0e1f2g3
Revises: g7z8c9d0e1f2
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

revision = "h8a9d0e1f2g3"
down_revision = "g7z8c9d0e1f2"
branch_labels = None
depends_on = None


#: Los nombres reales son los que SQLModel deriva de la clase: **sin guiones bajos**. Se comprobó
#: contra `8879cf0a3197_initial_schema`, que las crea así (`extractionserviceconfig`,
#: `systemprompt`). Escribirlos «bonitos» habría dado un `DROP TABLE` de algo que no existe.
_TABLAS = ("extractionserviceconfig", "systemprompt")


def upgrade() -> None:
    # `IF EXISTS`: en las bases donde el esquema se creó con `SQLModel.metadata.create_all` en vez
    # de con Alembic —o donde ya se limpiaron a mano— las tablas pueden no estar, y una migración
    # que revienta por eso bloquea el arranque de ese entorno.
    for tabla in _TABLAS:
        op.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE")


def downgrade() -> None:
    """Recrea las dos tablas con su forma original. Vacías: los datos los sembraba el arranque."""
    op.create_table(
        "systemprompt",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("context_type", sa.String(), nullable=False),
        sa.Column("tier", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_systemprompt_name", "systemprompt", ["name"], unique=True)
    op.create_table(
        "extractionserviceconfig",
        sa.Column("service_id", sa.String(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("module", sa.String(), nullable=False),
        sa.Column("target_function", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("system_prompt_template", sa.Text(), nullable=False),
        sa.Column("expected_schema", JSON(), nullable=True),
        sa.Column("suggested_model", sa.String(), nullable=True),
        sa.Column("tier_override", sa.Integer(), nullable=True),
    )

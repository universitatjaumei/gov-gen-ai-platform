"""RAG.10: reescritura de la consulta con el historial (flag + LLM en la cascada).

Revision ID: l9u0v1w2x3y4
Revises: k8t9u0v1w2x3
Create Date: 2026-08-01

Las tres columnas son **nullable**, y en las dos booleanas eso es deliberado y distinto de
lo que hicieron sus hermanas más antiguas (`reranker_enabled`, `min_retrieval_score`): con
un `False` no nulo, el nivel de abajo pisaría siempre al de arriba y encender la reescritura
en la organización no llegaría nunca a sus chatbots. NULL significa heredar.
"""
from alembic import op
import sqlalchemy as sa

revision = "l9u0v1w2x3y4"
down_revision = "k8t9u0v1w2x3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_chatbots",
        sa.Column("query_rewriting_enabled", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "hub_organizaciones",
        sa.Column("default_query_rewriting_enabled", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "hub_organizaciones",
        sa.Column("rewrite_llm_config_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_organizaciones_rewrite_llm_config",
        "hub_organizaciones",
        "hub_llm_configs",
        ["rewrite_llm_config_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_organizaciones_rewrite_llm_config", "hub_organizaciones", type_="foreignkey"
    )
    op.drop_column("hub_organizaciones", "rewrite_llm_config_id")
    op.drop_column("hub_organizaciones", "default_query_rewriting_enabled")
    op.drop_column("hub_chatbots", "query_rewriting_enabled")

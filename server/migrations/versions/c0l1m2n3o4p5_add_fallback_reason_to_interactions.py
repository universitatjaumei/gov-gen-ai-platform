"""RAG.2: fallback_reason en hub_interactions

Registra por qué una respuesta salió por el camino de fallback en vez del normal:
'quality_gate' (la evidencia no pasó el umbral de calidad) o 'citation' (el modelo
respondió sin citar ninguna fuente recuperada). NULL = camino normal.

Sin CheckConstraint a propósito: los motivos son un vocabulario que crecerá (reranker,
presupuesto de tokens...) y una restricción en la BD obligaría a una migración por cada
motivo nuevo. Indexada porque RAG.14 la consulta para detectar huecos de corpus.

Revision ID: c0l1m2n3o4p5
Revises: b9k0l1m2n3o4
"""
from alembic import op
import sqlalchemy as sa

revision = "c0l1m2n3o4p5"
down_revision = "b9k0l1m2n3o4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_interactions",
        sa.Column("fallback_reason", sa.String(length=32), nullable=True),
    )
    op.create_index(
        "ix_hub_interactions_fallback_reason",
        "hub_interactions",
        ["fallback_reason"],
    )


def downgrade() -> None:
    op.drop_index("ix_hub_interactions_fallback_reason", table_name="hub_interactions")
    op.drop_column("hub_interactions", "fallback_reason")

"""REV.1 — veredicto de quien revisa sobre conversaciones reales.

`feedback_score`/`feedback_text` son la valoración del **usuario final**. Estas cuatro
columnas son otra cosa: lo que dice quien audita, y de quién es esa firma.

`review_verdict` nulo significa **sin revisar**, que es el estado por defecto y el que
alimenta la cola. El CHECK admite NULL por eso, y usa los mismos tres valores que
`ck_test_run_verdict` a propósito: dos vocabularios para la misma idea acaban divergiendo.

Revision ID: v9e0f1g2h3i4
Revises: u8d9e0f1g2h3
"""
from alembic import op
import sqlalchemy as sa

revision = "v9e0f1g2h3i4"
down_revision = "u8d9e0f1g2h3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_interactions", sa.Column("review_verdict", sa.String(length=10), nullable=True)
    )
    op.add_column("hub_interactions", sa.Column("review_note", sa.Text(), nullable=True))
    op.add_column(
        "hub_interactions", sa.Column("review_by", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "hub_interactions", sa.Column("review_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        "ix_hub_interactions_review_verdict", "hub_interactions", ["review_verdict"]
    )
    op.create_check_constraint(
        "ck_interaction_review_verdict",
        "hub_interactions",
        "review_verdict IS NULL OR review_verdict IN ('good', 'bad', 'mixed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_interaction_review_verdict", "hub_interactions", type_="check")
    op.drop_index("ix_hub_interactions_review_verdict", table_name="hub_interactions")
    op.drop_column("hub_interactions", "review_at")
    op.drop_column("hub_interactions", "review_by")
    op.drop_column("hub_interactions", "review_note")
    op.drop_column("hub_interactions", "review_verdict")

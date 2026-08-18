"""RAS.2 — evidencia de que una página necesita renderizado

La recoge el rastreo (es el único momento en que existe el HTML) y la lee el detector, que corre
después: con señales, la página se avisa como `needs_javascript` en lugar de acusarla de estar
vacía, que es lo contrario de la verdad.

Revision ID: f6y7b8c9d0e1
Revises: e5x6a7b8c9d0
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "f6y7b8c9d0e1"
down_revision = "e5x6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_crawled_pages",
        sa.Column("render_signals", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_crawled_pages", "render_signals")

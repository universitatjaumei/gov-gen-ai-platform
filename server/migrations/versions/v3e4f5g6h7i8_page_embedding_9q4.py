"""page_embedding_9q4

Revision ID: v3e4f5g6h7i8
Revises: u2d3e4f5g6h7
Create Date: 2026-06-02
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "v3e4f5g6h7i8"
down_revision: Union[str, None] = "u2d3e4f5g6h7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hub_crawled_pages",
        sa.Column("page_embedding", Vector(1024), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_crawled_pages", "page_embedding")

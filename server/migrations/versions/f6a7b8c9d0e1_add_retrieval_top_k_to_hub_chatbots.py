"""add_retrieval_top_k_to_hub_chatbots

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-01

Cambios:
- Anade columna retrieval_top_k (integer, default 8) a hub_chatbots
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    cols = [c["name"] for c in inspect(op.get_bind()).get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _column_exists("hub_chatbots", "retrieval_top_k"):
        op.add_column(
            "hub_chatbots",
            sa.Column("retrieval_top_k", sa.Integer, nullable=False, server_default="8"),
        )


def downgrade() -> None:
    if _column_exists("hub_chatbots", "retrieval_top_k"):
        op.drop_column("hub_chatbots", "retrieval_top_k")

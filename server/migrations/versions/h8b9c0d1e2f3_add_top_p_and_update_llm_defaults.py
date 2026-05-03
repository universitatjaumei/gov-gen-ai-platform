"""add_top_p_and_update_llm_defaults

Revision ID: h8b9c0d1e2f3
Revises: g7a8b9c0d1e2
Create Date: 2026-05-03

Cambios:
- Añade columna top_p (float, default 1.0) a hub_llm_configs
- Actualiza server_default de temperature a 0.1
- Actualiza server_default de max_tokens a 12000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "h8b9c0d1e2f3"
down_revision: Union[str, None] = "g7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    cols = [c["name"] for c in inspect(op.get_bind()).get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _column_exists("hub_llm_configs", "top_p"):
        op.add_column(
            "hub_llm_configs",
            sa.Column("top_p", sa.Float(), nullable=False, server_default="1.0"),
        )

    op.alter_column(
        "hub_llm_configs",
        "temperature",
        existing_type=sa.Float(),
        server_default=sa.text("0.1"),
    )
    op.alter_column(
        "hub_llm_configs",
        "max_tokens",
        existing_type=sa.Integer(),
        server_default=sa.text("12000"),
    )


def downgrade() -> None:
    op.alter_column(
        "hub_llm_configs",
        "max_tokens",
        existing_type=sa.Integer(),
        server_default=sa.text("2048"),
    )
    op.alter_column(
        "hub_llm_configs",
        "temperature",
        existing_type=sa.Float(),
        server_default=sa.text("0.7"),
    )

    if _column_exists("hub_llm_configs", "top_p"):
        op.drop_column("hub_llm_configs", "top_p")
"""add_prompt_caching_fields_to_hub_chatbots

Revision ID: i9c0d1e2f3a4
Revises: h8b9c0d1e2f3
Create Date: 2026-05-03

Cambios:
- Añade `use_prompt_caching` (bool, default false) a hub_chatbots
- Añade `cache_ttl` (int, default 3600) a hub_chatbots
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "i9c0d1e2f3a4"
down_revision: Union[str, None] = "h8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    cols = [c["name"] for c in inspect(op.get_bind()).get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _column_exists("hub_chatbots", "use_prompt_caching"):
        op.add_column(
            "hub_chatbots",
            sa.Column("use_prompt_caching", sa.Boolean(), nullable=False, server_default="false"),
        )

    if not _column_exists("hub_chatbots", "cache_ttl"):
        op.add_column(
            "hub_chatbots",
            sa.Column("cache_ttl", sa.Integer(), nullable=False, server_default="3600"),
        )


def downgrade() -> None:
    if _column_exists("hub_chatbots", "cache_ttl"):
        op.drop_column("hub_chatbots", "cache_ttl")

    if _column_exists("hub_chatbots", "use_prompt_caching"):
        op.drop_column("hub_chatbots", "use_prompt_caching")
"""add_tier_label_to_llm_configs

Revision ID: g7a8b9c0d1e2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-01

Cambios:
- Anade tier (int, default 1), label (str, default ''), is_default (bool, default false)
  a hub_llm_configs
- Anade default_tier (int, nullable) y override_tier (int, nullable)
  a hub_prompt_templates
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "g7a8b9c0d1e2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    cols = [c["name"] for c in inspect(op.get_bind()).get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _column_exists("hub_llm_configs", "tier"):
        op.add_column(
            "hub_llm_configs",
            sa.Column("tier", sa.Integer, nullable=False, server_default="1"),
        )
    if not _column_exists("hub_llm_configs", "label"):
        op.add_column(
            "hub_llm_configs",
            sa.Column("label", sa.String(255), nullable=False, server_default=""),
        )
    if not _column_exists("hub_llm_configs", "is_default"):
        op.add_column(
            "hub_llm_configs",
            sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        )
    if not _column_exists("hub_prompt_templates", "default_tier"):
        op.add_column(
            "hub_prompt_templates",
            sa.Column("default_tier", sa.Integer, nullable=True),
        )
    if not _column_exists("hub_prompt_templates", "override_tier"):
        op.add_column(
            "hub_prompt_templates",
            sa.Column("override_tier", sa.Integer, nullable=True),
        )


def downgrade() -> None:
    if _column_exists("hub_prompt_templates", "override_tier"):
        op.drop_column("hub_prompt_templates", "override_tier")
    if _column_exists("hub_prompt_templates", "default_tier"):
        op.drop_column("hub_prompt_templates", "default_tier")
    if _column_exists("hub_llm_configs", "is_default"):
        op.drop_column("hub_llm_configs", "is_default")
    if _column_exists("hub_llm_configs", "label"):
        op.drop_column("hub_llm_configs", "label")
    if _column_exists("hub_llm_configs", "tier"):
        op.drop_column("hub_llm_configs", "tier")

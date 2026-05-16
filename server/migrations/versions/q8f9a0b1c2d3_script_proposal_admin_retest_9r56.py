"""Add admin_retest_json to hub_script_proposals — 9R.5.6

Revision ID: q8f9a0b1c2d3
Revises: p7e8f9a0b1c2
Create Date: 2026-05-15
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "q8f9a0b1c2d3"
down_revision = "p7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_script_proposals",
        sa.Column("admin_retest_json", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_script_proposals", "admin_retest_json")

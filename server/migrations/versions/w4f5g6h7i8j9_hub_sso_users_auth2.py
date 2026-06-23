"""hub_sso_users_auth2

Revision ID: w4f5g6h7i8j9
Revises: v3e4f5g6h7i8
Create Date: 2026-06-11
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "w4f5g6h7i8j9"
down_revision: Union[str, None] = "v3e4f5g6h7i8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hub_sso_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("role", sa.String(40), nullable=False, server_default="user"),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("idp_entity_id", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hub_sso_users_email", "hub_sso_users", ["email"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_hub_sso_users_email", "hub_sso_users")
    op.drop_table("hub_sso_users")

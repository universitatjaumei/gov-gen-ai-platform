"""hub_personal_access_tokens_auth3

Revision ID: x5g6h7i8j9k0
Revises: w4f5g6h7i8j9
Create Date: 2026-06-11
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "x5g6h7i8j9k0"
down_revision: Union[str, None] = "w4f5g6h7i8j9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hub_personal_access_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.String(255), nullable=False),
        sa.Column("owner_email", sa.String(320), nullable=False),
        sa.Column("owner_role", sa.String(40), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("token_prefix", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hub_personal_access_tokens_owner_id",
        "hub_personal_access_tokens",
        ["owner_id"],
    )
    op.create_index(
        "ix_hub_personal_access_tokens_token_prefix",
        "hub_personal_access_tokens",
        ["token_prefix"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_hub_personal_access_tokens_token_prefix", "hub_personal_access_tokens"
    )
    op.drop_index(
        "ix_hub_personal_access_tokens_owner_id", "hub_personal_access_tokens"
    )
    op.drop_table("hub_personal_access_tokens")

"""content_findings_9q1

Revision ID: u2d3e4f5g6h7
Revises: t1c2d3e4f5g6
Create Date: 2026-06-01
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "u2d3e4f5g6h7"
down_revision: Union[str, None] = "t1c2d3e4f5g6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hub_content_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_type", sa.String(40), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_page_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("signal_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["hub_web_sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["page_id"], ["hub_crawled_pages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "site_id", "finding_type", "page_id", "related_page_id",
            name="uq_finding_dedup",
        ),
    )
    op.create_index("ix_hub_content_findings_site_id", "hub_content_findings", ["site_id"])
    op.create_index("ix_hub_content_findings_page_id", "hub_content_findings", ["page_id"])
    op.create_index("ix_hub_content_findings_status", "hub_content_findings", ["status"])


def downgrade() -> None:
    op.drop_index("ix_hub_content_findings_status", "hub_content_findings")
    op.drop_index("ix_hub_content_findings_page_id", "hub_content_findings")
    op.drop_index("ix_hub_content_findings_site_id", "hub_content_findings")
    op.drop_table("hub_content_findings")

"""hub_chunk_user_upload — columnas is_temporary y owner_id en hub_document_chunks

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hub_document_chunks",
        sa.Column("is_temporary", sa.Boolean, nullable=False, server_default="false"),
    )
    op.add_column(
        "hub_document_chunks",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_hub_document_chunks_owner_id",
        "hub_document_chunks",
        ["owner_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_hub_document_chunks_owner_id", table_name="hub_document_chunks")
    op.drop_column("hub_document_chunks", "owner_id")
    op.drop_column("hub_document_chunks", "is_temporary")

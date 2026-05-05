"""add_spider_type_to_hub_ingestion_sources

Revision ID: j0d1e2f3a4b5
Revises: i9c0d1e2f3a4
Create Date: 2026-05-05

Cambios:
- Añade `spider_type` (VARCHAR(50), nullable, default 'generic') a hub_ingestion_sources
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "j0d1e2f3a4b5"
down_revision: Union[str, None] = "i9c0d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    cols = [c["name"] for c in inspect(op.get_bind()).get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _column_exists("hub_ingestion_sources", "spider_type"):
        op.add_column(
            "hub_ingestion_sources",
            sa.Column(
                "spider_type",
                sa.String(50),
                nullable=True,
                server_default="generic",
            ),
        )


def downgrade() -> None:
    if _column_exists("hub_ingestion_sources", "spider_type"):
        op.drop_column("hub_ingestion_sources", "spider_type")

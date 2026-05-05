"""add_config_json_to_hub_ingestion_sources

Revision ID: k1e2f3a4b5c6
Revises: j0d1e2f3a4b5
Create Date: 2026-05-05

Cambios:
- Añade `config_json` (JSONB, default '{}') a hub_ingestion_sources
  Permite almacenar selectores CSS propuestos por el asistente HITL y parámetros del spider.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "k1e2f3a4b5c6"
down_revision: Union[str, None] = "j0d1e2f3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    cols = [c["name"] for c in inspect(op.get_bind()).get_columns(table)]
    return column in cols


def upgrade() -> None:
    if not _column_exists("hub_ingestion_sources", "config_json"):
        op.add_column(
            "hub_ingestion_sources",
            sa.Column(
                "config_json",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default="{}",
            ),
        )


def downgrade() -> None:
    if _column_exists("hub_ingestion_sources", "config_json"):
        op.drop_column("hub_ingestion_sources", "config_json")

"""hub_ingestion_language

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table: str) -> bool:
    return table in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    # hub_ingestion_sources no existe en una instalación nueva: la crea código
    # fuera de esta cadena de migraciones y 9Q.0 (t1c2d3e4f5g6) la retira. En
    # instalaciones existentes donde sí está presente, se le añade la columna.
    if _table_exists("hub_ingestion_sources"):
        op.add_column(
            "hub_ingestion_sources",
            sa.Column("language", sa.String(10), nullable=True),
        )
    op.add_column(
        "hub_ingestion_jobs",
        sa.Column("language", sa.String(10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_ingestion_jobs", "language")
    if _table_exists("hub_ingestion_sources"):
        op.drop_column("hub_ingestion_sources", "language")

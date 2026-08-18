"""GUI.1 — archivado de plantillas de informe

Retirar una plantilla es archivarla, no borrarla: un informe ya firmado no puede quedarse sin la
plantilla con la que se hizo. `archived_at` nula significa vigente.

Revision ID: e5x6a7b8c9d0
Revises: d4w5z6a7b8c9
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e5x6a7b8c9d0"
down_revision = "d4w5z6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_report_templates",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_hub_report_templates_archived_at",
        "hub_report_templates",
        ["archived_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_hub_report_templates_archived_at", table_name="hub_report_templates")
    op.drop_column("hub_report_templates", "archived_at")

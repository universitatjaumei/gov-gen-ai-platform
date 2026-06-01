"""workspace_anonymization_mode_13_1

Revision ID: s0b1c2d3e4f5
Revises: r9a0b1c2d3e4
Create Date: 2026-05-18

Cambios (Prompt 13.1 — NER reversible):
Añade `anonymization_mode` (String(40), default 'replace', not null) a hub_workspaces.
Valores válidos: off | detect_only | replace | replace_with_disposition_7.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "s0b1c2d3e4f5"
down_revision: Union[str, None] = "r9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hub_workspaces",
        sa.Column(
            "anonymization_mode",
            sa.String(40),
            nullable=False,
            server_default="replace",
        ),
    )


def downgrade() -> None:
    op.drop_column("hub_workspaces", "anonymization_mode")

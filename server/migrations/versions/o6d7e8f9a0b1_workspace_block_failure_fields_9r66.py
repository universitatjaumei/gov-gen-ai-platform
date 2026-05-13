"""workspace_block_failure_fields_9r66

Revision ID: o6d7e8f9a0b1
Revises: n5c6d7e8f9a0
Create Date: 2026-05-13

Cambios (Prompt 9R.6.6):
Añadir campos de fallo a hub_workspace_blocks:
- failure_kind (str, nullable): subtipo del fallo (extraction_failed, ai_failed, script_failed, validation_failed)
- last_error_message (text, nullable): mensaje de error truncado a 500 chars
- retry_attempts (int, not null, default 0): número de reintentos realizados
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "o6d7e8f9a0b1"
down_revision: Union[str, None] = "n5c6d7e8f9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hub_workspace_blocks",
        sa.Column("failure_kind", sa.String(50), nullable=True),
    )
    op.add_column(
        "hub_workspace_blocks",
        sa.Column("last_error_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "hub_workspace_blocks",
        sa.Column("retry_attempts", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("hub_workspace_blocks", "retry_attempts")
    op.drop_column("hub_workspace_blocks", "last_error_message")
    op.drop_column("hub_workspace_blocks", "failure_kind")

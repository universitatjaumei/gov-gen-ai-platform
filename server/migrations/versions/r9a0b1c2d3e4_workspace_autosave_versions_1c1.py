"""workspace_autosave_versions_1c1

Revision ID: r9a0b1c2d3e4
Revises: q8f9a0b1c2d3
Create Date: 2026-05-18

Cambios (Prompt 1C.1 — Autosave con concurrencia optimista):
Añadir columna `version` (int, default 1, not null) a:
- hub_workspaces:        usada como expected_workspace_version en el PATCH /state.
- hub_workspace_blocks:  usada como expected_block_version por cada BlockUpdate.

Cada UPDATE en estas tablas debe incrementar version en 1; la responsabilidad
de incremento vive en WorkspaceAutosaveService.apply_patch (no es un trigger SQL).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "r9a0b1c2d3e4"
down_revision: Union[str, None] = "q8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hub_workspaces",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "hub_workspace_blocks",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("hub_workspace_blocks", "version")
    op.drop_column("hub_workspaces", "version")

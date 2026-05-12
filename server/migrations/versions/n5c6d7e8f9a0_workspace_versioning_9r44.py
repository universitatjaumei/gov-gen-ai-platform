"""workspace_versioning_9r44

Revision ID: n5c6d7e8f9a0
Revises: m4b5c6d7e8f9
Create Date: 2026-05-12

Cambios (Prompt 9R.4.4):
Añadir columnas de versionado a hub_workspaces:
- parent_workspace_id (UUID, FK self-referencing, nullable)
- archived_reason (str, nullable)

El campo status ya admite "archived" a nivel de app (tipo String, no enum DB).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "n5c6d7e8f9a0"
down_revision: Union[str, tuple] = "m4b5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "hub_workspaces",
        sa.Column("parent_workspace_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "hub_workspaces",
        sa.Column("archived_reason", sa.String(500), nullable=True),
    )
    op.create_foreign_key(
        "fk_hub_workspaces_parent_workspace_id",
        "hub_workspaces",
        "hub_workspaces",
        ["parent_workspace_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_hub_workspaces_parent_workspace_id",
        "hub_workspaces",
        type_="foreignkey",
    )
    op.drop_column("hub_workspaces", "archived_reason")
    op.drop_column("hub_workspaces", "parent_workspace_id")

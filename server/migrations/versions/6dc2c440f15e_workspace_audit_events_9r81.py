"""workspace_audit_events_9r81

Revision ID: 6dc2c440f15e
Revises: a792fdf2fe50
Create Date: 2026-05-13

Cambios (Prompt 9R.8.1):
Añadir tabla hub_workspace_audit_events para registrar transiciones de bloque.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '6dc2c440f15e'
down_revision: Union[str, None] = 'a792fdf2fe50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'hub_workspace_audit_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('block_id', sa.String(length=255), nullable=True),
        sa.Column('event', sa.String(length=50), nullable=False),
        sa.Column('from_status', sa.String(length=30), nullable=True),
        sa.Column('to_status', sa.String(length=30), nullable=True),
        sa.Column('actor', sa.String(length=255), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['hub_workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_hub_workspace_audit_events_block_id'),
        'hub_workspace_audit_events',
        ['block_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_hub_workspace_audit_events_workspace_id'),
        'hub_workspace_audit_events',
        ['workspace_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_hub_workspace_audit_events_workspace_id'), table_name='hub_workspace_audit_events')
    op.drop_index(op.f('ix_hub_workspace_audit_events_block_id'), table_name='hub_workspace_audit_events')
    op.drop_table('hub_workspace_audit_events')

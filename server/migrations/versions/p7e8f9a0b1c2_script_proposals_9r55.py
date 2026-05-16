"""script_proposals_9r55

Revision ID: p7e8f9a0b1c2
Revises: 6dc2c440f15e
Create Date: 2026-05-13

Cambios (Prompt 9R.5.5):
Añadir tabla hub_script_proposals para almacenar propuestas de scripts de
extracción generadas por LLM y auditadas (AST + sandbox test).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'p7e8f9a0b1c2'
down_revision: Union[str, None] = '6dc2c440f15e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'hub_script_proposals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('proposer_user_id', sa.UUID(), nullable=False),
        sa.Column('target_owner_kind', sa.String(length=20), nullable=False),
        sa.Column('target_template_id', sa.UUID(), nullable=True),
        sa.Column('prompt_nl', sa.Text(), nullable=False),
        sa.Column('code', sa.Text(), nullable=False),
        sa.Column('audit_result_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('test_data_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('test_data_is_anonymized', sa.Boolean(), nullable=False),
        sa.Column('test_data_anonymization_map', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('test_data_kind', sa.String(length=20), nullable=True),
        sa.Column('test_result_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('test_result_hash', sa.String(length=128), nullable=True),
        sa.Column('test_validated_by_proposer_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('reviewer_user_id', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('model_used', sa.String(length=120), nullable=True),
        sa.Column('prompt_version', sa.String(length=120), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_hub_script_proposals_proposer_user_id'),
        'hub_script_proposals',
        ['proposer_user_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_hub_script_proposals_target_template_id'),
        'hub_script_proposals',
        ['target_template_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_hub_script_proposals_status'),
        'hub_script_proposals',
        ['status'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_hub_script_proposals_status'), table_name='hub_script_proposals')
    op.drop_index(op.f('ix_hub_script_proposals_target_template_id'), table_name='hub_script_proposals')
    op.drop_index(op.f('ix_hub_script_proposals_proposer_user_id'), table_name='hub_script_proposals')
    op.drop_table('hub_script_proposals')

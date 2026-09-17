"""DIN.6 diario de pasadas de curacion

Una fila por pasada. Tabla nueva y no `hub_ingestion_jobs`: aquella es de UN documento
—`chatbot_id` NOT NULL, `source_url`, `chunks_processed`— y una pasada no tiene chatbot ni URL,
tiene un sitio, una seccion y un diff.

`section_id` es SET NULL y va con `scope_label` al lado: el diario es historia, y una historia
que se reescribe cuando alguien borra una seccion no sirve para auditar nada.

Revision ID: aff38fa79582
Revises: 53bbc4c5d4c5
Create Date: 2026-09-17 18:21:49.362958

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'aff38fa79582'
down_revision: Union[str, None] = '53bbc4c5d4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table('hub_crawl_runs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('site_id', sa.UUID(), nullable=False),
    sa.Column('section_id', sa.UUID(), nullable=True),
    sa.Column('scope_label', sa.String(length=255), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('pages_total', sa.Integer(), nullable=False),
    sa.Column('pages_new', sa.Integer(), nullable=False),
    sa.Column('pages_changed', sa.Integer(), nullable=False),
    sa.Column('pages_gone', sa.Integer(), nullable=False),
    sa.Column('pages_error', sa.Integer(), nullable=False),
    sa.Column('documents_auto_ingested', sa.Integer(), nullable=False),
    sa.Column('documents_reingested', sa.Integer(), nullable=False),
    sa.Column('documents_auto_retired', sa.Integer(), nullable=False),
    sa.Column('pages_blocked_by_findings', sa.Integer(), nullable=False),
    sa.Column('findings_retired', sa.Integer(), nullable=False),
    sa.Column('truncated', sa.Boolean(), nullable=False),
    sa.Column('stop_reason', sa.String(length=40), nullable=True),
    sa.Column('errors', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['section_id'], ['hub_web_sections.id'], name='fk_run_section', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['site_id'], ['hub_web_sites.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hub_crawl_runs_section_id'), 'hub_crawl_runs', ['section_id'], unique=False)
    op.create_index(op.f('ix_hub_crawl_runs_site_id'), 'hub_crawl_runs', ['site_id'], unique=False)
    op.create_index('ix_hub_crawl_runs_site_started', 'hub_crawl_runs', ['site_id', 'started_at'], unique=False)



def downgrade() -> None:

    op.drop_index('ix_hub_crawl_runs_site_started', table_name='hub_crawl_runs')
    op.drop_index(op.f('ix_hub_crawl_runs_site_id'), table_name='hub_crawl_runs')
    op.drop_index(op.f('ix_hub_crawl_runs_section_id'), table_name='hub_crawl_runs')
    op.drop_table('hub_crawl_runs')


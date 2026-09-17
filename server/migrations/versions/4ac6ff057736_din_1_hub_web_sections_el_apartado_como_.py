"""DIN.1 hub_web_sections: el apartado como dato

Sin datos que migrar: los sitios-apartado que existen hoy —un `HubWebSite` por apartado con su
`url_regex_filter`, que es la decisión de RAS.5— siguen sin secciones, y un sitio sin secciones
se comporta exactamente como antes: su ámbito implícito es el sitio entero.

Revision ID: 4ac6ff057736
Revises: 611e53c82fcb
Create Date: 2026-09-17 15:27:17.183529

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4ac6ff057736'
down_revision: Union[str, None] = '611e53c82fcb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table('hub_web_sections',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('site_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('pattern', sa.String(length=2048), nullable=False),
    sa.Column('pattern_kind', sa.String(length=20), nullable=False),
    sa.Column('crawl_interval_hours', sa.Integer(), nullable=True),
    sa.Column('mode', sa.String(length=20), nullable=False),
    sa.Column('criteria_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('owner', sa.String(length=255), nullable=True),
    sa.Column('last_crawled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("mode IN ('manual', 'automatic')", name='ck_section_mode'),
    sa.CheckConstraint("pattern_kind IN ('path_prefix', 'regex')", name='ck_section_pattern_kind'),
    sa.ForeignKeyConstraint(['site_id'], ['hub_web_sites.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', 'name', name='uq_section_site_name')
    )
    op.create_index(op.f('ix_hub_web_sections_site_id'), 'hub_web_sections', ['site_id'], unique=False)



def downgrade() -> None:

    op.drop_index(op.f('ix_hub_web_sections_site_id'), table_name='hub_web_sections')
    op.drop_table('hub_web_sections')


"""DIN.3 la seleccion apunta a una seccion

Nulo = la regla vale por sí misma, que es el camino de siempre: ninguna selección existente
cambia de comportamiento. Con la columna puesta, el patrón efectivo lo manda la sección y
`rule_value` se ignora — dos sitios de verdad de la misma regla divergirían en cuanto alguien
editara uno.

`ondelete='RESTRICT'` y no `CASCADE`: borrar una sección **no** puede llevarse por delante la
selección que apunta a ella. Con la auto-retirada de DIN.4 detrás, perder la selección no es
perder una fila, es dejar de mantener lo que hay en el corpus. El endpoint de borrado responde
409 antes de llegar aquí; esto es lo que lo hace cierto también para quien escriba SQL a mano.

La restricción va con nombre explícito: la autogeneración la dejaba anónima y el `downgrade`
—`drop_constraint(None, ...)`— no habría podido revertirla.

Revision ID: 53bbc4c5d4c5
Revises: 4ac6ff057736
Create Date: 2026-09-17 16:18:56.348912

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '53bbc4c5d4c5'
down_revision: Union[str, None] = '4ac6ff057736'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FK = "fk_selection_section"


def upgrade() -> None:
    op.add_column(
        'hub_corpus_selections', sa.Column('section_id', sa.UUID(), nullable=True)
    )
    op.create_index(
        op.f('ix_hub_corpus_selections_section_id'),
        'hub_corpus_selections',
        ['section_id'],
        unique=False,
    )
    op.create_foreign_key(
        _FK,
        'hub_corpus_selections',
        'hub_web_sections',
        ['section_id'],
        ['id'],
        ondelete='RESTRICT',
    )


def downgrade() -> None:
    op.drop_constraint(_FK, 'hub_corpus_selections', type_='foreignkey')
    op.drop_index(
        op.f('ix_hub_corpus_selections_section_id'), table_name='hub_corpus_selections'
    )
    op.drop_column('hub_corpus_selections', 'section_id')

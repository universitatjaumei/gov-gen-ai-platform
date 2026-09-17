"""FUN.1 catalogo de funciones y sus versiones

Dos tablas nuevas y ningun dato que migrar: las plantillas que hoy llevan el codigo incrustado
en `options.code` se migran en FUN.3, que es donde el bloque gana `funcion_ref` y donde hay algo
a lo que apuntar.

Van al lado **operacional** (edge): el codigo de una funcion de autoservicio y su declaracion
responsable son texto escrito por una persona de la organizacion, que es el criterio con el que
`hub_lexicon_pairs` acabo en ese lado. Ver docs/MULTITENENCIA.md.

Revision ID: deadfff99b26
Revises: aff38fa79582
Create Date: 2026-09-17 23:03:57.110760

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'deadfff99b26'
down_revision: Union[str, None] = 'aff38fa79582'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table('hub_funciones',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('organizacion_id', sa.UUID(), nullable=True),
    sa.Column('origen', sa.String(length=20), nullable=False),
    sa.Column('entry_point', sa.String(length=200), nullable=True),
    sa.Column('promocion_solicitada_por', sa.UUID(), nullable=True),
    sa.Column('promocion_solicitada_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('motivo_promocion', sa.Text(), nullable=True),
    sa.Column('publicada_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('publicada_por', sa.UUID(), nullable=True),
    sa.Column('valoracion_promocion', sa.Text(), nullable=True),
    sa.Column('creada_por', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("origen IN ('autoservicio', 'paquete')", name='ck_funcion_origen'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('entry_point')
    )
    op.create_index(op.f('ix_hub_funciones_organizacion_id'), 'hub_funciones', ['organizacion_id'], unique=False)
    op.create_table('hub_funcion_versiones',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('funcion_id', sa.UUID(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('code', sa.Text(), nullable=True),
    sa.Column('version_paquete', sa.String(length=32), nullable=True),
    sa.Column('contrato_entrada', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('contrato_salida', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('audit_result_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('code_sha256', sa.String(length=64), nullable=False),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('autoria', sa.String(length=20), nullable=True),
    sa.Column('finalidad', sa.Text(), nullable=True),
    sa.Column('categorias_datos', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('declarada_por', sa.UUID(), nullable=True),
    sa.Column('declarada_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revisada_por', sa.UUID(), nullable=True),
    sa.Column('revisada_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revision_resultado', sa.String(length=20), nullable=True),
    sa.Column('revision_nota', sa.Text(), nullable=True),
    sa.Column('suspendida_por', sa.UUID(), nullable=True),
    sa.Column('suspendida_en', sa.DateTime(timezone=True), nullable=True),
    sa.Column('motivo_suspension', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("estado IN ('draft', 'registrada', 'suspendida', 'retirada', 'no_instalada')", name='ck_funcion_version_estado'),
    sa.ForeignKeyConstraint(['funcion_id'], ['hub_funciones.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('funcion_id', 'version', name='uq_funcion_version')
    )
    op.create_index(op.f('ix_hub_funcion_versiones_estado'), 'hub_funcion_versiones', ['estado'], unique=False)
    op.create_index(op.f('ix_hub_funcion_versiones_funcion_id'), 'hub_funcion_versiones', ['funcion_id'], unique=False)



def downgrade() -> None:

    op.drop_index(op.f('ix_hub_funcion_versiones_funcion_id'), table_name='hub_funcion_versiones')
    op.drop_index(op.f('ix_hub_funcion_versiones_estado'), table_name='hub_funcion_versiones')
    op.drop_table('hub_funcion_versiones')
    op.drop_index(op.f('ix_hub_funciones_organizacion_id'), table_name='hub_funciones')
    op.drop_table('hub_funciones')


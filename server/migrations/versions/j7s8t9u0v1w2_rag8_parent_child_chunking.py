"""RAG.8: parent-child y parametros de troceado en la cascada

Tres columnas de configuracion en `hub_chatbots` y sus tres defaults en
`hub_organizaciones`, todas nullable porque NULL significa «heredar»; y `parent_content` en
`hub_document_chunks`.

`parent_content` es columna directa y no un JOIN a una tabla de secciones: el padre ya existe
como texto dentro del documento, y duplicarlo cuesta menos que mantener una tabla
sincronizada con cada re-troceado. Es la misma clase de decision que la denormalizacion del
puente bilingue en RAG.4, y con la misma condicion: refrescarla es re-trocear, que es lo que
hace `corpus_recalculator` al cambiar de estrategia.

El CHECK de `chunking_strategy` admite NULL a proposito: NULL es «heredar», no «valor
invalido». Son dos estrategias estables con consumidor en el chunker, asi que CHECK si —mismo
criterio que `nivell_acces` en ING.0.2 y al contrario que el vocabulario de ambitos, que es
dato revisable.

Revision ID: j7s8t9u0v1w2
Revises: i6r7s8t9u0v1
"""
from alembic import op
import sqlalchemy as sa

revision = "j7s8t9u0v1w2"
down_revision = "i6r7s8t9u0v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("hub_chatbots", sa.Column("chunk_size", sa.Integer(), nullable=True))
    op.add_column("hub_chatbots", sa.Column("chunk_overlap", sa.Integer(), nullable=True))
    op.add_column(
        "hub_chatbots", sa.Column("chunking_strategy", sa.String(length=20), nullable=True)
    )
    op.create_check_constraint(
        "ck_chatbot_chunking_strategy",
        "hub_chatbots",
        "chunking_strategy IS NULL OR chunking_strategy IN ('structural', 'parent_child')",
    )

    op.add_column(
        "hub_organizaciones", sa.Column("default_chunk_size", sa.Integer(), nullable=True)
    )
    op.add_column(
        "hub_organizaciones", sa.Column("default_chunk_overlap", sa.Integer(), nullable=True)
    )
    op.add_column(
        "hub_organizaciones",
        sa.Column("default_chunking_strategy", sa.String(length=20), nullable=True),
    )

    op.add_column(
        "hub_document_chunks", sa.Column("parent_content", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("hub_document_chunks", "parent_content")
    op.drop_column("hub_organizaciones", "default_chunking_strategy")
    op.drop_column("hub_organizaciones", "default_chunk_overlap")
    op.drop_column("hub_organizaciones", "default_chunk_size")
    op.drop_constraint("ck_chatbot_chunking_strategy", "hub_chatbots", type_="check")
    op.drop_column("hub_chatbots", "chunking_strategy")
    op.drop_column("hub_chatbots", "chunk_overlap")
    op.drop_column("hub_chatbots", "chunk_size")

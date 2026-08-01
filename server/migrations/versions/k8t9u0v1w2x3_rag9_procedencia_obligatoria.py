"""RAG.9: procedencia obligatoria del vector, texto embebido e índice de espacio.

Revision ID: k8t9u0v1w2x3
Revises: j7s8t9u0v1w2
Create Date: 2026-08-01

El backfill NO es una suposición. Hasta MOD.2, `get_embedding_service()` devolvía
`LocalEmbeddingService` incondicionalmente y `GoogleEmbeddingService` era código
inalcanzable, así que todo chunk anterior salió de BAAI/bge-m3 a 1024. Se está rellenando un
dato conocido, no adivinándolo — y por eso se puede exigir NOT NULL después.

`embedding_text` se queda NULL en las filas viejas a propósito: eso sí sería adivinar. El
texto embebido de RAG.7 lleva delante título y jerarquía, y reconstruirlo desde `content`
daría un vector que la ingesta nunca produjo. La CLI de re-embedding los cuenta aparte y
remite a `recalculate-corpus`, que re-trocea desde el documento.
"""
from alembic import op
import sqlalchemy as sa

revision = "k8t9u0v1w2x3"
down_revision = "j7s8t9u0v1w2"
branch_labels = None
depends_on = None

MODELO_HISTORICO = "BAAI/bge-m3"
DIMENSION_HISTORICA = 1024


def upgrade() -> None:
    op.add_column(
        "hub_document_chunks", sa.Column("embedding_text", sa.Text(), nullable=True)
    )

    op.execute(
        sa.text(
            "UPDATE hub_document_chunks SET embedding_model = :modelo "
            "WHERE embedding_model IS NULL"
        ).bindparams(modelo=MODELO_HISTORICO)
    )
    op.execute(
        sa.text(
            "UPDATE hub_document_chunks SET embedding_dim = :dim "
            "WHERE embedding_dim IS NULL"
        ).bindparams(dim=DIMENSION_HISTORICA)
    )

    op.alter_column(
        "hub_document_chunks",
        "embedding_model",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.alter_column(
        "hub_document_chunks",
        "embedding_dim",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # La guarda de espacio vectorial corre en cada consulta de chat. Sin este índice, su
    # DISTINCT lee todos los chunks del chatbot para responder "no pasa nada".
    op.create_index(
        "ix_hub_document_chunks_embedding_space",
        "hub_document_chunks",
        ["chatbot_id", "embedding_model", "embedding_dim"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_hub_document_chunks_embedding_space", table_name="hub_document_chunks"
    )
    op.alter_column(
        "hub_document_chunks",
        "embedding_dim",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "hub_document_chunks",
        "embedding_model",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.drop_column("hub_document_chunks", "embedding_text")

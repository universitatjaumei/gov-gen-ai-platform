"""PIL.1 — el propósito del embedding viaja con el vector.

`gemini-embedding-001` produce un vector distinto según el tipo de tarea, y el piloto
indexa con `RETRIEVAL_DOCUMENT` y pregunta con `RETRIEVAL_QUERY` a propósito. Sin esta
columna, embeber un corpus con un tipo y servirlo con otro **no era detectable**: modelo y
dimensión coinciden, y lo único que cambia es que el retriever empeora. Es el mismo agujero
que MOD.1 cerró para el modelo, un nivel más abajo.

**Nullable, y no es un hueco**: el modelo local (BGE-M3) no distingue documento de consulta,
así que `NULL` es la declaración honesta de ese espacio vectorial. Los chunks anteriores a
esta migración también quedan en `NULL`, que es exactamente lo que eran: vectores sin
propósito declarado. `assert_embedding_space_matches` los tratará como espacio distinto del
de Vertex, que es lo correcto — hay que re-embeberlos, no darlos por buenos.

El índice de la guarda se rehace para incluir la columna: si se quedara fuera, el DISTINCT
volvería al heap y la comprobación dejaría de ser barata justo después de hacerla más
estricta.

Revision ID: a1p2i3l4m5n6
Revises: v9e0f1g2h3i4
"""
from alembic import op
import sqlalchemy as sa

revision = "a1p2i3l4m5n6"
down_revision = "v9e0f1g2h3i4"
branch_labels = None
depends_on = None

_INDICE = "ix_hub_document_chunks_embedding_space"


def upgrade() -> None:
    op.add_column(
        "hub_document_chunks",
        sa.Column("embedding_task_type", sa.String(length=40), nullable=True),
    )
    op.drop_index(_INDICE, table_name="hub_document_chunks")
    op.create_index(
        _INDICE,
        "hub_document_chunks",
        ["chatbot_id", "embedding_model", "embedding_dim", "embedding_task_type"],
    )


def downgrade() -> None:
    op.drop_index(_INDICE, table_name="hub_document_chunks")
    op.create_index(
        _INDICE,
        "hub_document_chunks",
        ["chatbot_id", "embedding_model", "embedding_dim"],
    )
    op.drop_column("hub_document_chunks", "embedding_task_type")

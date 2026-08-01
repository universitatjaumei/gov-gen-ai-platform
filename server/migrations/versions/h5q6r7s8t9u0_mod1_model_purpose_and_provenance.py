"""MOD.1: proposito del modelo en la configuracion y procedencia en el vector

Dos cambios que van juntos porque uno sin el otro es peligroso:

- `hub_llm_configs.purpose` ('chat' | 'embedding' | 'rerank') y `output_dimensionality`.
  La tabla era implicitamente de chat —lo delatan temperature, top_p y max_tokens— y los
  modelos de embedding se elegian con un import. Con el proposito explicito se reutiliza el
  panel que ya existe: proveedores con su base_url y su clave, available-models y el test de
  conexion. CHECK sobre purpose porque son tres valores estables con consumidor en el codigo
  (mismo criterio que nivell_acces en ING.0.2), al contrario que el vocabulario de ambitos.

- `hub_document_chunks.embedding_model` y `.embedding_dim`. Misma dimension NO significa
  mismo espacio vectorial: el coseno entre vectores de dos modelos distintos no da error, da
  resultados malos. Sin procedencia, cambiar de modelo es una averia silenciosa.

Las filas existentes quedan con purpose='chat' —que es lo que son— y los chunks ya ingeridos
con procedencia NULL, que se trata como desconocida y no bloquea nada: exigir un dato que no
existia convertiria esta mejora en una migracion forzosa del corpus.

Contexto y verificacion de la API: docs/DECISION_MODELOS_EMBEDDING_RERANKER.md

Revision ID: h5q6r7s8t9u0
Revises: g4p5q6r7s8t9
"""
from alembic import op
import sqlalchemy as sa

revision = "h5q6r7s8t9u0"
down_revision = "g4p5q6r7s8t9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_llm_configs",
        sa.Column(
            "purpose", sa.String(length=20), nullable=False, server_default="chat"
        ),
    )
    op.add_column(
        "hub_llm_configs",
        sa.Column("output_dimensionality", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_llm_config_purpose",
        "hub_llm_configs",
        "purpose IN ('chat', 'embedding', 'rerank')",
    )

    op.add_column(
        "hub_document_chunks",
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "hub_document_chunks",
        sa.Column("embedding_dim", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_document_chunks", "embedding_dim")
    op.drop_column("hub_document_chunks", "embedding_model")
    op.drop_constraint("ck_llm_config_purpose", "hub_llm_configs", type_="check")
    op.drop_column("hub_llm_configs", "output_dimensionality")
    op.drop_column("hub_llm_configs", "purpose")

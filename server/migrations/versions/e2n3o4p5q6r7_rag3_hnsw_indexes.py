"""RAG.3: indices HNSW para la busqueda vectorial

`hub_document_chunks.embedding` (recuperacion del chatbot) y
`hub_crawled_pages.page_embedding` (detector semantico de 9Q). Sin indice ANN, cada consulta
recorre todos los vectores del chatbot calculando la distancia coseno de uno en uno.

`vector_cosine_ops` y no otro opclass: `retriever.py` ordena por `cosine_distance`, y un
indice construido con otra metrica no lo serviria — existiria y no se usaria, que es la peor
de las dos situaciones porque parece resuelto.

Defaults de pgvector (m=16, ef_construction=64): son los que la documentacion recomienda
hasta tener medicion propia, y RAG.1 ya da la via para medir si conviene tocarlos.

Requiere pgvector >= 0.5. Verificado en la imagen de dev y de produccion
(`pgvector/pgvector:pg16`): 0.8.2, asi que no hace falta tocar docker-compose.

Los dos indices estan declarados tambien en el ORM (`operational_models.py`). Ambos sitios a
proposito: las BD de test se construyen con `create_all` desde el metadata, y un indice que
solo viviera aqui no existiria donde se prueba.

Revision ID: e2n3o4p5q6r7
Revises: d1m2n3o4p5q6
"""
from alembic import op

revision = "e2n3o4p5q6r7"
down_revision = "d1m2n3o4p5q6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_hub_document_chunks_embedding_hnsw "
        "ON hub_document_chunks USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_hub_crawled_pages_embedding_hnsw "
        "ON hub_crawled_pages USING hnsw (page_embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_hub_crawled_pages_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_hub_document_chunks_embedding_hnsw")

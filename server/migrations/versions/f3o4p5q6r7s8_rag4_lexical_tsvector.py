"""RAG.4: rama lexica real (tsvector + GIN) y puente bilingue

Sustituye al `ILIKE` del retriever, que no era busqueda lexica sino subcadena: sin stemming
('becas' no encontraba 'beca'), sin orden por relevancia (todo valia 1.0) y con un AND por
palabra, asi que una palabra de mas vaciaba el resultado.

Dos columnas nuevas en `hub_document_chunks`:

- `bilingual_terms`: los pares del dominio ('despesa/gasto') copiados del documento en la
  ingesta. **Se denormalizan al chunk porque una columna generada solo puede referirse a su
  propia fila**, y los terminos viven en `hub_documents.doc_metadata`. Refrescarlos cuando
  cambien es un UPDATE con JOIN —como el de esta misma migracion— y no un re-embedding, que
  es el invariante de CLAUDE.md §5. Aqui va solo el puente lexico: la taxonomia NO entra.
- `tsv`: columna generada `STORED` con `to_tsvector(config, content || bilingual_terms)`.
  Config `spanish` para castellano y `simple` para el resto: PostgreSQL core no trae stemmer
  catalan, asi que en catalan se busca por forma exacta. Un diccionario Snowball catalan es
  mejora de despliegue, no de codigo.

Mas indice GIN sobre `tsv`, que es lo que hace la consulta barata.

Ambas columnas y el indice estan declarados tambien en el ORM: las BD de test se construyen
con `create_all`, y lo que solo viviera aqui no existiria donde se prueba.

Revision ID: f3o4p5q6r7s8
Revises: e2n3o4p5q6r7
"""
from alembic import op
import sqlalchemy as sa

revision = "f3o4p5q6r7s8"
down_revision = "e2n3o4p5q6r7"
branch_labels = None
depends_on = None

_TSV = (
    "to_tsvector("
    "CASE WHEN language = 'es' THEN 'spanish'::regconfig ELSE 'simple'::regconfig END, "
    "coalesce(content, '') || ' ' || coalesce(bilingual_terms, ''))"
)


def upgrade() -> None:
    op.add_column(
        "hub_document_chunks",
        sa.Column("bilingual_terms", sa.Text(), nullable=True),
    )

    # Rellenar lo que ya esta ingerido antes de generar el tsvector, para no dejar el corpus
    # existente sin puente hasta la siguiente reingesta.
    op.execute(
        """
        UPDATE hub_document_chunks c
           SET bilingual_terms = sub.terminos
          FROM (
                SELECT d.id,
                       (SELECT string_agg(replace(t, '/', ' '), ' ')
                          FROM jsonb_array_elements_text(d.doc_metadata->'termes_bilingues') AS t
                       ) AS terminos
                  FROM hub_documents d
                 WHERE jsonb_typeof(d.doc_metadata->'termes_bilingues') = 'array'
               ) AS sub
         WHERE c.document_id = sub.id
           AND sub.terminos IS NOT NULL
        """
    )

    op.execute(
        f"ALTER TABLE hub_document_chunks "
        f"ADD COLUMN tsv tsvector GENERATED ALWAYS AS ({_TSV}) STORED"
    )
    op.execute(
        "CREATE INDEX ix_hub_document_chunks_tsv ON hub_document_chunks USING gin (tsv)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_hub_document_chunks_tsv")
    op.execute("ALTER TABLE hub_document_chunks DROP COLUMN IF EXISTS tsv")
    op.drop_column("hub_document_chunks", "bilingual_terms")

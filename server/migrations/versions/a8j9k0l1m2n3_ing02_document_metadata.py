"""ING.0.2 metadatos del corpus normativo en hub_documents + FK de chunks + fixes

Tres bloques:

1. **Metadatos del corpus** en `hub_documents`. Criterio: columna de primer nivel solo si
   algo la filtra, la ordena o la usa como puerta; el resto del esquema de 56 campos va a
   `doc_metadata` JSONB. Los códigos de vocabulario NO llevan CHECK (son dato revisable,
   CLAUDE.md §5); `nivell_acces`, `us_assistents` y `content_class` sí (enumeraciones
   estables con consumidor).

   Nota de seguridad sobre el relleno de filas existentes: se les pone
   `nivell_acces='public'`, que NO es fail-closed. Es admisible **solo** porque todo el
   corpus cargado hoy proviene del crawler de webs públicas. En cuanto entre corpus
   interno (circulares de Gerencia), el valor debe venir declarado en el front-matter y
   nunca del default.

2. **FK de `hub_document_chunks.document_id`**, que VIS.1 necesita para filtrar los
   chunks por los metadatos de su documento con un JOIN. Se limpian antes los huérfanos.

3. **Dos fixes de esquema hallados al comparar la BD de desarrollo con una instalación
   limpia** (2026-07-28):

   - `hub_ingestion_jobs.canonical_url` y `.original_filename`: el ORM las declara y
     `POST /hub/ingestion/upload` las escribe, pero ninguna migración las creaba
     (`e5f6a7b8c9d0` las trata como opcionales porque las creó código fuera de la
     cadena). En un despliegue limpio la subida de documentos fallaba con
     UndefinedColumn. Misma familia que el fallo de `hub_ingestion_sources` de 11.2.
   - `hub_interactions.metadata`: la creaba `a1b2c3d4e5f6`, pero SQLAlchemy reserva
     `metadata` en las clases declarativas, así que el ORM usa `interaction_metadata` y
     aquella columna era inalcanzable. Se retira (Caso B), verificado con grep que nadie
     la lee.

Revision ID: a8j9k0l1m2n3
Revises: z7i8j9k0l1m2
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

revision = "a8j9k0l1m2n3"
down_revision = "z7i8j9k0l1m2"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            sa.text(
                "select 1 from information_schema.columns "
                "where table_name = :t and column_name = :c"
            ),
            {"t": table, "c": column},
        ).first()
    )


def upgrade() -> None:
    # ── 1. Metadatos del corpus ────────────────────────────────────────────────
    op.add_column(
        "hub_documents",
        sa.Column(
            "content_class", sa.String(20), nullable=False, server_default="generic"
        ),
    )
    op.add_column(
        "hub_documents", sa.Column("ambit_principal", sa.String(80), nullable=True)
    )
    for columna in ("ambits_secundaris", "submateries", "submateries_internes"):
        op.add_column(
            "hub_documents",
            sa.Column(
                columna,
                # ARRAY del dialecto: VIS.1 filtra con el operador de solapamiento `&&`.
                ARRAY(sa.String()),
                nullable=False,
                server_default=sa.text("'{}'::character varying[]"),
            ),
        )
    op.add_column(
        "hub_documents",
        sa.Column("nivell_acces", sa.String(20), nullable=False, server_default="public"),
    )
    op.add_column(
        "hub_documents",
        sa.Column("us_assistents", sa.String(20), nullable=False, server_default="si"),
    )
    op.add_column(
        "hub_documents",
        sa.Column("canonica", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "hub_documents",
        sa.Column(
            "versio_idiomatica_de",
            UUID(as_uuid=True),
            sa.ForeignKey("hub_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "hub_documents", sa.Column("estat_vigencia", sa.String(20), nullable=True)
    )
    op.add_column(
        "hub_documents",
        sa.Column("vigencia_validada_el", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "hub_documents", sa.Column("revisat_per", sa.String(255), nullable=True)
    )
    op.add_column(
        "hub_documents",
        sa.Column("revisat_el", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "hub_documents", sa.Column("data_revisio_prevista", sa.Date(), nullable=True)
    )
    op.add_column(
        "hub_documents", sa.Column("id_publicacio", sa.String(80), nullable=True)
    )
    op.add_column(
        "hub_documents",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "hub_documents",
        sa.Column(
            "doc_metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )

    op.create_check_constraint(
        "ck_document_nivell_acces",
        "hub_documents",
        "nivell_acces IN ('public', 'intern', 'restringit')",
    )
    op.create_check_constraint(
        "ck_document_us_assistents",
        "hub_documents",
        "us_assistents IN ('si', 'restringit', 'no')",
    )
    op.create_check_constraint(
        "ck_document_content_class",
        "hub_documents",
        "content_class IN ('regulation', 'faq', 'generic')",
    )

    op.create_index(
        "ix_hub_documents_chatbot_ambit",
        "hub_documents",
        ["chatbot_id", "ambit_principal"],
    )
    op.create_index(
        "ix_hub_documents_chatbot_nivell",
        "hub_documents",
        ["chatbot_id", "nivell_acces"],
    )
    op.create_index(
        "ix_hub_documents_id_publicacio", "hub_documents", ["id_publicacio"]
    )
    # GIN sobre los arrays: es lo que aprovecha el operador && de VIS.1.
    op.create_index(
        "ix_hub_documents_submateries",
        "hub_documents",
        ["submateries"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_hub_documents_submateries_internes",
        "hub_documents",
        ["submateries_internes"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_hub_documents_doc_metadata",
        "hub_documents",
        ["doc_metadata"],
        postgresql_using="gin",
    )

    # ── 2. FK de document_id (VIS.1 la necesita para el JOIN) ──────────────────
    # Huérfanos primero: sin esto el ADD CONSTRAINT falla en cualquier BD con datos.
    resultado = op.get_bind().execute(
        sa.text(
            "delete from hub_document_chunks c where c.document_id is not null "
            "and not exists (select 1 from hub_documents d where d.id = c.document_id)"
        )
    )
    print(f"[ING.0.2] chunks huerfanos eliminados: {resultado.rowcount}")
    op.create_foreign_key(
        "fk_chunk_document_id",
        "hub_document_chunks",
        "hub_documents",
        ["document_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # ── 3. Fixes de esquema ────────────────────────────────────────────────────
    if not _column_exists("hub_ingestion_jobs", "canonical_url"):
        op.add_column(
            "hub_ingestion_jobs",
            sa.Column("canonical_url", sa.String(2048), nullable=True),
        )
    if not _column_exists("hub_ingestion_jobs", "original_filename"):
        op.add_column(
            "hub_ingestion_jobs",
            sa.Column("original_filename", sa.String(500), nullable=True),
        )
    if _column_exists("hub_interactions", "metadata"):
        op.drop_column("hub_interactions", "metadata")


def downgrade() -> None:
    op.add_column(
        "hub_interactions",
        sa.Column("metadata", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.drop_column("hub_ingestion_jobs", "original_filename")
    op.drop_column("hub_ingestion_jobs", "canonical_url")

    op.drop_constraint("fk_chunk_document_id", "hub_document_chunks", type_="foreignkey")

    for indice in (
        "ix_hub_documents_doc_metadata",
        "ix_hub_documents_submateries_internes",
        "ix_hub_documents_submateries",
        "ix_hub_documents_id_publicacio",
        "ix_hub_documents_chatbot_nivell",
        "ix_hub_documents_chatbot_ambit",
    ):
        op.drop_index(indice, table_name="hub_documents")

    for restriccion in (
        "ck_document_content_class",
        "ck_document_us_assistents",
        "ck_document_nivell_acces",
    ):
        op.drop_constraint(restriccion, "hub_documents", type_="check")

    for columna in (
        "doc_metadata",
        "last_seen_at",
        "id_publicacio",
        "data_revisio_prevista",
        "revisat_el",
        "revisat_per",
        "vigencia_validada_el",
        "estat_vigencia",
        "versio_idiomatica_de",
        "canonica",
        "us_assistents",
        "nivell_acces",
        "submateries_internes",
        "submateries",
        "ambits_secundaris",
        "ambit_principal",
        "content_class",
    ):
        op.drop_column("hub_documents", columna)

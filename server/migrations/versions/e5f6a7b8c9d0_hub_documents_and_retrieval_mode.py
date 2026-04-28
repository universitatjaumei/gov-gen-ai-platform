"""hub_documents_and_retrieval_mode

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-28

Cambios:
- Crea tabla hub_documents (unidad citable del corpus)
- Anade columna document_id (nullable) a hub_document_chunks
- Anade columnas retrieval_mode, kind, parent_chatbot_id a hub_chatbots
- Backfill: crea HubDocument por cada job completado con chunks
- Backfill: vincula chunks a su documento por (chatbot_id, source_url)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Crear tabla hub_documents
    op.create_table(
        "hub_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("chatbot_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("canonical_url", sa.String(2048), nullable=False),
        sa.Column("markdown_content", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("source_kind", sa.String(20), nullable=False),
        sa.Column("section_path", sa.String(1024), nullable=True),
        sa.Column("token_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "chatbot_id", "content_hash", name="uq_document_chatbot_hash"
        ),
    )
    op.create_index("ix_hub_documents_chatbot_id", "hub_documents", ["chatbot_id"])
    op.create_index("ix_hub_documents_content_hash", "hub_documents", ["content_hash"])

    # 2. Anadir document_id a hub_document_chunks
    op.add_column(
        "hub_document_chunks",
        sa.Column("document_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_hub_document_chunks_document_id",
        "hub_document_chunks",
        ["document_id"],
    )

    # 3. Anadir nuevos campos a hub_chatbots
    op.add_column(
        "hub_chatbots",
        sa.Column(
            "retrieval_mode",
            sa.String(20),
            nullable=False,
            server_default="vector",
        ),
    )
    op.add_column(
        "hub_chatbots",
        sa.Column(
            "kind",
            sa.String(20),
            nullable=False,
            server_default="atomic",
        ),
    )
    op.add_column(
        "hub_chatbots",
        sa.Column("parent_chatbot_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_chatbot_parent",
        "hub_chatbots",
        "hub_chatbots",
        ["parent_chatbot_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_hub_chatbots_parent_chatbot_id",
        "hub_chatbots",
        ["parent_chatbot_id"],
    )
    op.create_check_constraint(
        "ck_chatbot_retrieval_mode",
        "hub_chatbots",
        "retrieval_mode IN ('vector', 'long_context', 'agentic')",
    )
    op.create_check_constraint(
        "ck_chatbot_kind",
        "hub_chatbots",
        "kind IN ('atomic', 'router')",
    )

    # 4. Backfill: crear HubDocument por cada job completado con chunks
    op.execute(
        """
        INSERT INTO hub_documents
            (id, chatbot_id, title, canonical_url, markdown_content,
             content_hash, language, source_kind, token_count,
             created_at, updated_at)
        SELECT
            gen_random_uuid(),
            j.chatbot_id,
            COALESCE(j.original_filename, j.canonical_url, j.source_url),
            COALESCE(j.canonical_url, j.source_url),
            '',
            COALESCE(
                (SELECT MIN(c.content_hash)
                 FROM hub_document_chunks c
                 WHERE c.chatbot_id = j.chatbot_id
                   AND c.source_url = COALESCE(j.canonical_url, j.source_url)),
                'backfill'
            ),
            COALESCE(j.language, 'es'),
            CASE WHEN j.source_url LIKE 'http%' THEN 'crawler' ELSE 'upload' END,
            COALESCE(j.chunks_processed * 250, 0),
            j.created_at,
            j.created_at
        FROM hub_ingestion_jobs j
        WHERE j.status = 'completed'
          AND EXISTS (
              SELECT 1 FROM hub_document_chunks c
              WHERE c.chatbot_id = j.chatbot_id
                AND c.source_url = COALESCE(j.canonical_url, j.source_url)
          )
        ON CONFLICT (chatbot_id, content_hash) DO NOTHING;
        """
    )

    # 5. Backfill: vincular chunks a su documento
    op.execute(
        """
        UPDATE hub_document_chunks c
        SET document_id = d.id
        FROM hub_documents d
        WHERE d.chatbot_id = c.chatbot_id
          AND d.canonical_url = c.source_url
          AND c.document_id IS NULL;
        """
    )


def downgrade() -> None:
    op.drop_constraint("ck_chatbot_kind", "hub_chatbots", type_="check")
    op.drop_constraint("ck_chatbot_retrieval_mode", "hub_chatbots", type_="check")
    op.drop_index("ix_hub_chatbots_parent_chatbot_id", table_name="hub_chatbots")
    op.drop_constraint("fk_chatbot_parent", "hub_chatbots", type_="foreignkey")
    op.drop_column("hub_chatbots", "parent_chatbot_id")
    op.drop_column("hub_chatbots", "kind")
    op.drop_column("hub_chatbots", "retrieval_mode")
    op.drop_index(
        "ix_hub_document_chunks_document_id", table_name="hub_document_chunks"
    )
    op.drop_column("hub_document_chunks", "document_id")
    op.drop_index("ix_hub_documents_content_hash", table_name="hub_documents")
    op.drop_index("ix_hub_documents_chatbot_id", table_name="hub_documents")
    op.drop_table("hub_documents")

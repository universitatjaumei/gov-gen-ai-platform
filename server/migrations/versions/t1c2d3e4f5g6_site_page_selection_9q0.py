"""site_page_selection_9q0

Revision ID: t1c2d3e4f5g6
Revises: s0b1c2d3e4f5
Create Date: 2026-06-01

Cambios (Prompt 9Q.0 — modelo sitio/página/selección + retirada HubIngestionSource):

1) Crea las tablas nuevas (todas en HubOperationalBase):
   - hub_web_sites: unidad de crawl + auditoría (propiedad del cliente, no del chatbot).
   - hub_crawled_pages: páginas rastreadas con señales de frescura y flags de higiene.
     UNIQUE(site_id, url) = uq_page_site_url.
   - hub_corpus_selections: mapeo N:M chatbot→sitio (path_prefix | sitemap_section | manual).
2) Añade hub_documents.crawled_page_id (FK → hub_crawled_pages.id ON DELETE SET NULL).
3) Migra los datos existentes: por cada hub_ingestion_sources crea un hub_web_sites +
   un hub_corpus_selections(rule_type='manual'). client_id se deriva del chatbot cuando
   es posible; si no existe el chatbot, el sitio se crea con client_id NULL como fallback
   documentado para datos de desarrollo.
4) DROP hub_ingestion_sources.
"""
from __future__ import annotations

import json
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "t1c2d3e4f5g6"
down_revision: Union[str, None] = "s0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Crear tablas nuevas ────────────────────────────────────────────
    op.create_table(
        "hub_web_sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("root_url", sa.String(2048), nullable=False),
        sa.Column("sitemap_url", sa.String(2048), nullable=True),
        sa.Column("spider_type", sa.String(50), nullable=False, server_default="generic"),
        sa.Column(
            "config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "crawl_interval_hours", sa.Integer(), nullable=False, server_default="24"
        ),
        sa.Column(
            "audit_semantic_scope",
            sa.String(20),
            nullable=False,
            server_default="ingested",
        ),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_hub_web_sites_client_id", "hub_web_sites", ["client_id"]
    )

    op.create_table(
        "hub_crawled_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_web_sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("canonical_url", sa.String(2048), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("markdown_content", sa.Text(), nullable=True),
        sa.Column("http_last_modified", sa.DateTime(timezone=True), nullable=True),
        sa.Column("http_etag", sa.String(255), nullable=True),
        sa.Column("sitemap_lastmod", sa.DateTime(timezone=True), nullable=True),
        sa.Column("declared_canonical_url", sa.String(2048), nullable=True),
        sa.Column("content_year", sa.Integer(), nullable=True),
        sa.Column(
            "superseded",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("superseded_by_page_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.UniqueConstraint("site_id", "url", name="uq_page_site_url"),
    )
    op.create_index(
        "ix_hub_crawled_pages_site_id", "hub_crawled_pages", ["site_id"]
    )
    op.create_index(
        "ix_hub_crawled_pages_superseded", "hub_crawled_pages", ["superseded"]
    )

    op.create_table(
        "hub_corpus_selections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chatbot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_web_sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rule_type", sa.String(20), nullable=False),
        sa.Column("rule_value", sa.String(2048), nullable=True),
        sa.Column(
            "auto_ingest_new",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_hub_corpus_selections_chatbot_id",
        "hub_corpus_selections",
        ["chatbot_id"],
    )
    op.create_index(
        "ix_hub_corpus_selections_site_id",
        "hub_corpus_selections",
        ["site_id"],
    )

    # ── 2. crawled_page_id en hub_documents ──────────────────────────────
    conn2 = op.get_bind()
    inspector2 = sa.inspect(conn2)
    if "hub_documents" in inspector2.get_table_names():
        doc_cols = {c["name"] for c in inspector2.get_columns("hub_documents")}
        if "crawled_page_id" not in doc_cols:
            op.add_column(
                "hub_documents",
                sa.Column(
                    "crawled_page_id", postgresql.UUID(as_uuid=True), nullable=True
                ),
            )
            op.create_index(
                "ix_hub_documents_crawled_page_id",
                "hub_documents",
                ["crawled_page_id"],
            )
            op.create_foreign_key(
                "fk_hub_documents_crawled_page_id",
                "hub_documents",
                "hub_crawled_pages",
                ["crawled_page_id"],
                ["id"],
                ondelete="SET NULL",
            )

    # ── 3. DATA MIGRATION: HubIngestionSource → (site + selection) ───────
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "hub_ingestion_sources" in inspector.get_table_names():
        sources = conn.execute(
            sa.text(
                "SELECT id, chatbot_id, url, label, spider_type, config_json "
                "FROM hub_ingestion_sources"
            )
        ).fetchall()

        for src in sources:
            client_row = conn.execute(
                sa.text("SELECT client_id FROM hub_chatbots WHERE id = :id"),
                {"id": src.chatbot_id},
            ).fetchone()
            # Fallback documentado: client_id nullable cuando no se puede derivar
            # del chatbot (datos de desarrollo huérfanos). La UI exigirá client_id
            # al crear sitios nuevos a partir de 9Q.7.
            client_id = client_row.client_id if client_row else None

            site_id = uuid.uuid4()
            config_value = src.config_json
            if isinstance(config_value, str):
                config_payload = config_value
            elif config_value is None:
                config_payload = "{}"
            else:
                config_payload = json.dumps(config_value)

            conn.execute(
                sa.text(
                    "INSERT INTO hub_web_sites "
                    "(id, client_id, name, root_url, spider_type, config_json, "
                    " audit_semantic_scope, crawl_interval_hours, status, created_at) "
                    "VALUES (:id, :client_id, :name, :url, :spider_type, "
                    " CAST(:config AS jsonb), 'ingested', 24, 'active', CURRENT_TIMESTAMP)"
                ),
                {
                    "id": site_id,
                    "client_id": client_id,
                    "name": src.label or src.url,
                    "url": src.url,
                    "spider_type": src.spider_type or "generic",
                    "config": config_payload,
                },
            )
            conn.execute(
                sa.text(
                    "INSERT INTO hub_corpus_selections "
                    "(id, chatbot_id, site_id, rule_type, rule_value, auto_ingest_new, created_at) "
                    "VALUES (:id, :chatbot_id, :site_id, 'manual', NULL, TRUE, CURRENT_TIMESTAMP)"
                ),
                {
                    "id": uuid.uuid4(),
                    "chatbot_id": src.chatbot_id,
                    "site_id": site_id,
                },
            )

        # ── 4. DROP hub_ingestion_sources ────────────────────────────────
        op.drop_table("hub_ingestion_sources")


def downgrade() -> None:
    # Recrear la tabla retirada (sin datos): permite revertir el esquema,
    # los datos migrados a sitios/selecciones no se rehidratan automáticamente.
    op.create_table(
        "hub_ingestion_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chatbot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("check_interval_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_content_hash", sa.String(64), nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("spider_type", sa.String(50), nullable=True, server_default="generic"),
        sa.Column(
            "config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_hub_ingestion_sources_chatbot_id",
        "hub_ingestion_sources",
        ["chatbot_id"],
    )

    op.drop_constraint(
        "fk_hub_documents_crawled_page_id", "hub_documents", type_="foreignkey"
    )
    op.drop_index("ix_hub_documents_crawled_page_id", table_name="hub_documents")
    op.drop_column("hub_documents", "crawled_page_id")

    op.drop_index(
        "ix_hub_corpus_selections_site_id", table_name="hub_corpus_selections"
    )
    op.drop_index(
        "ix_hub_corpus_selections_chatbot_id", table_name="hub_corpus_selections"
    )
    op.drop_table("hub_corpus_selections")

    op.drop_index("ix_hub_crawled_pages_superseded", table_name="hub_crawled_pages")
    op.drop_index("ix_hub_crawled_pages_site_id", table_name="hub_crawled_pages")
    op.drop_table("hub_crawled_pages")

    op.drop_index("ix_hub_web_sites_client_id", table_name="hub_web_sites")
    op.drop_table("hub_web_sites")

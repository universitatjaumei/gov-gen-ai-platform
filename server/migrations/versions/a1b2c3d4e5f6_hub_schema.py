"""hub_schema — tablas agents_hub con pgvector

Revision ID: a1b2c3d4e5f6
Revises: 8879cf0a3197
Create Date: 2026-04-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "8879cf0a3197"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Habilitar extensión pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # hub_llm_configs — debe crearse antes que hub_chatbots (FK)
    op.create_table(
        "hub_llm_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("temperature", sa.Float, nullable=False, server_default="0.7"),
        sa.Column("max_tokens", sa.Integer, nullable=False, server_default="2048"),
        sa.Column("api_key_secret_name", sa.String(255), nullable=True),
    )

    # hub_clients
    op.create_table(
        "hub_clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("partner_id", sa.String(255), nullable=False, index=True),
        sa.Column("theme_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # hub_chatbots
    op.create_table(
        "hub_chatbots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "llm_config_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_llm_configs.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("system_prompt", sa.Text, nullable=False),
        sa.Column("sources", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("theme_config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # hub_prompt_templates
    op.create_table(
        "hub_prompt_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_chatbots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("template_text", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.UniqueConstraint("chatbot_id", "slug", "language", name="uq_prompt_chatbot_slug_lang"),
    )

    # hub_document_chunks (con columna vector de pgvector)
    op.create_table(
        "hub_document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_chatbots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False, index=True),
        sa.Column("embedding", sa.String),  # placeholder; replaced below
        sa.Column("chunk_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("language", sa.String(10), nullable=False, server_default="es"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    # Reemplazar la columna placeholder por el tipo vector real
    op.execute("ALTER TABLE hub_document_chunks ALTER COLUMN embedding TYPE vector(1536) USING NULL::vector(1536)")

    # hub_interactions
    op.create_table(
        "hub_interactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_chatbots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(255), nullable=False, index=True),
        sa.Column("user_message", sa.Text, nullable=False),
        sa.Column("assistant_message", sa.Text, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("feedback_score", sa.Integer, nullable=True),
        sa.Column("interaction_metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # hub_ingestion_jobs
    op.create_table(
        "hub_ingestion_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_chatbots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("chunks_processed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("hub_ingestion_jobs")
    op.drop_table("hub_interactions")
    op.drop_table("hub_document_chunks")
    op.drop_table("hub_prompt_templates")
    op.drop_table("hub_chatbots")
    op.drop_table("hub_clients")
    op.drop_table("hub_llm_configs")
    op.execute("DROP EXTENSION IF EXISTS vector")

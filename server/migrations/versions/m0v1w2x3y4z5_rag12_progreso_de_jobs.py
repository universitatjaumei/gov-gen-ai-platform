"""RAG.12: progreso y estadísticas por etapa en hub_ingestion_jobs.

Revision ID: m0v1w2x3y4z5
Revises: l9u0v1w2x3y4
Create Date: 2026-08-01

`progress_total` es la única nullable del grupo, y a propósito: el total de fragmentos no
existe hasta después de trocear, y un 0 ahí se leería como «no hay nada que hacer» en vez de
«todavía no se sabe».
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "m0v1w2x3y4z5"
down_revision = "l9u0v1w2x3y4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_ingestion_jobs",
        sa.Column("progress_current", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "hub_ingestion_jobs", sa.Column("progress_total", sa.Integer(), nullable=True)
    )
    op.add_column(
        "hub_ingestion_jobs",
        sa.Column("progress_message", sa.String(255), nullable=False, server_default=""),
    )
    op.add_column(
        "hub_ingestion_jobs",
        sa.Column(
            "processing_stats",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "hub_ingestion_jobs",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "hub_ingestion_jobs",
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    for columna in (
        "processing_completed_at",
        "processing_started_at",
        "processing_stats",
        "progress_message",
        "progress_total",
        "progress_current",
    ):
        op.drop_column("hub_ingestion_jobs", columna)

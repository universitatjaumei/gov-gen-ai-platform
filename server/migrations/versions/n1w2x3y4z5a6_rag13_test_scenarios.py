"""RAG.13: escenarios de prueba por chatbot y sus ejecuciones con veredicto humano.

Revision ID: n1w2x3y4z5a6
Revises: m0v1w2x3y4z5
Create Date: 2026-08-01

Ambas tablas son **operacionales**, no de configuración: son las pruebas del cliente sobre
su propio corpus, así que viven en el edge y no se sincronizan al cloud.

El CHECK de `verdict` admite NULL a propósito: NULL es «sin juzgar todavía», que es el
estado en que nace toda ejecución, no un valor inválido.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "n1w2x3y4z5a6"
down_revision = "m0v1w2x3y4z5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hub_test_scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chatbot_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("history", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expectation_note", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "hub_test_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "scenario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_test_scenarios.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column(
            "sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
            server_default="[]",
        ),
        sa.Column("bypass_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("verdict", sa.String(10), nullable=True),
        sa.Column("verdict_note", sa.Text(), nullable=True),
        sa.Column("verdict_by", sa.String(255), nullable=True),
        sa.CheckConstraint(
            "verdict IS NULL OR verdict IN ('good', 'bad', 'mixed')",
            name="ck_test_run_verdict",
        ),
    )


def downgrade() -> None:
    op.drop_table("hub_test_runs")
    op.drop_table("hub_test_scenarios")

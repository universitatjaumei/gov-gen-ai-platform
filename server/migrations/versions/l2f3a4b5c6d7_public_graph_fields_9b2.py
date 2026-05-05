"""public_graph_fields_9b2

Revision ID: l2f3a4b5c6d7
Revises: k1e2f3a4b5c6
Create Date: 2026-05-05

Cambios (Prompt 9B.2):
- hub_chatbots: migra retrieval_mode ('vector'→'RAG', 'long_context'→'MD_LONG_CONTEXT',
  'agentic'→'MD_AGENT_SELECTOR'), renueva CheckConstraint, añade 7 columnas de grafo público.
- hub_clients: añade 8 columnas de defaults del grafo público.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "l2f3a4b5c6d7"
down_revision: Union[str, None] = "k1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    return column in [c["name"] for c in inspect(op.get_bind()).get_columns(table)]


def upgrade() -> None:
    # ── hub_chatbots ─────────────────────────────────────────────────────────

    # 1. Eliminar constraint antiguo
    op.drop_constraint("ck_chatbot_retrieval_mode", "hub_chatbots", type_="check")

    # 2. Renombrar valores del enum de retrieval_mode
    op.execute("UPDATE hub_chatbots SET retrieval_mode = 'RAG'              WHERE retrieval_mode = 'vector'")
    op.execute("UPDATE hub_chatbots SET retrieval_mode = 'MD_LONG_CONTEXT'  WHERE retrieval_mode = 'long_context'")
    op.execute("UPDATE hub_chatbots SET retrieval_mode = 'MD_AGENT_SELECTOR' WHERE retrieval_mode = 'agentic'")

    # 3. Ampliar String(20)→String(30) y cambiar server_default
    op.alter_column("hub_chatbots", "retrieval_mode",
                    existing_type=sa.String(20),
                    type_=sa.String(30),
                    existing_nullable=False,
                    server_default="RAG")

    # 4. Nuevo constraint
    op.create_check_constraint(
        "ck_chatbot_retrieval_mode",
        "hub_chatbots",
        "retrieval_mode IN ('RAG', 'MD_LONG_CONTEXT', 'MD_AGENT_SELECTOR')",
    )

    # 5. Nuevas columnas en hub_chatbots
    chatbot_cols = [
        ("public_graph_profile",  sa.String(50),  "PUBLIC_KB_RICH"),
        ("language_mode",          sa.String(20),  "prefer"),
        ("quality_threshold",      sa.Float(),     "0.6"),
        ("min_retrieval_results",  sa.Integer(),   "2"),
        ("min_retrieval_score",    sa.Float(),     "0.25"),
        ("reranker_enabled",       sa.Boolean(),   "true"),
        ("answer_template",        sa.String(50),  "generic"),
    ]
    for col_name, col_type, default in chatbot_cols:
        if not _column_exists("hub_chatbots", col_name):
            op.add_column(
                "hub_chatbots",
                sa.Column(col_name, col_type, nullable=False, server_default=default),
            )

    # ── hub_clients ──────────────────────────────────────────────────────────

    client_cols = [
        ("default_public_graph_profile",  sa.String(50),  "PUBLIC_KB_RICH"),
        ("default_retrieval_mode",         sa.String(30),  "RAG"),
        ("default_language_mode",          sa.String(20),  "prefer"),
        ("default_quality_threshold",      sa.Float(),     "0.6"),
        ("default_min_retrieval_results",  sa.Integer(),   "2"),
        ("default_min_retrieval_score",    sa.Float(),     "0.25"),
        ("default_reranker_enabled",       sa.Boolean(),   "true"),
        ("default_answer_template",        sa.String(50),  "generic"),
    ]
    for col_name, col_type, default in client_cols:
        if not _column_exists("hub_clients", col_name):
            op.add_column(
                "hub_clients",
                sa.Column(col_name, col_type, nullable=False, server_default=default),
            )


def downgrade() -> None:
    # hub_clients
    for col in [
        "default_public_graph_profile", "default_retrieval_mode", "default_language_mode",
        "default_quality_threshold", "default_min_retrieval_results", "default_min_retrieval_score",
        "default_reranker_enabled", "default_answer_template",
    ]:
        if _column_exists("hub_clients", col):
            op.drop_column("hub_clients", col)

    # hub_chatbots — nuevas columnas
    for col in [
        "public_graph_profile", "language_mode", "quality_threshold",
        "min_retrieval_results", "min_retrieval_score", "reranker_enabled", "answer_template",
    ]:
        if _column_exists("hub_chatbots", col):
            op.drop_column("hub_chatbots", col)

    # Revertir constraint y valores de retrieval_mode
    op.drop_constraint("ck_chatbot_retrieval_mode", "hub_chatbots", type_="check")
    op.execute("UPDATE hub_chatbots SET retrieval_mode = 'vector'       WHERE retrieval_mode = 'RAG'")
    op.execute("UPDATE hub_chatbots SET retrieval_mode = 'long_context' WHERE retrieval_mode = 'MD_LONG_CONTEXT'")
    op.execute("UPDATE hub_chatbots SET retrieval_mode = 'agentic'      WHERE retrieval_mode = 'MD_AGENT_SELECTOR'")
    op.alter_column("hub_chatbots", "retrieval_mode",
                    existing_type=sa.String(30),
                    type_=sa.String(20),
                    existing_nullable=False,
                    server_default="vector")
    op.create_check_constraint(
        "ck_chatbot_retrieval_mode",
        "hub_chatbots",
        "retrieval_mode IN ('vector', 'long_context', 'agentic')",
    )

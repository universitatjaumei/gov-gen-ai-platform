"""SEC.4: contabilidad de tokens, contadores de consumo y cuotas en cascada.

Revision ID: r5a6b7c8d9e0
Revises: q4z5a6b7c8d9
Create Date: 2026-08-02

Tres bloques y una regla común: **ninguna cuota se activa por migrar**.

1. `hub_interactions` gana `prompt_tokens`, `completion_tokens` y `cost_estimated`, las tres
   **nullable**. Las interacciones anteriores no tienen el dato y no se inventa: un cero
   diría «no gastó nada», que es una afirmación distinta de «no lo sabemos», y sobre esa
   diferencia se apoya cualquier cuota que se quiera defender.

2. `hub_usage_counters` es tabla nueva y **operacional**: consumo del cliente final, no
   configuración, así que no se sincroniza al cloud. La clave única
   (subject_type, subject_id, window_key) es lo que permite el UPSERT atómico; sin ella, dos
   respuestas concurrentes del mismo usuario se pisarían el contador.

3. Los límites entran como columnas **nullable y sin valor por defecto** en
   `hub_organizaciones` y `hub_chatbots`. NULL = heredar del nivel de arriba, y como nadie
   pone nada, nadie tiene límite: una migración no es el sitio donde se decide cuánto puede
   gastar una organización.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "r5a6b7c8d9e0"
down_revision = "q4z5a6b7c8d9"
branch_labels = None
depends_on = None

_CUOTAS_ORGANIZACION = (
    "default_user_daily_token_quota",
    "default_user_monthly_token_quota",
    "monthly_token_quota",
    "default_chatbot_daily_token_quota",
)
_CUOTAS_CHATBOT = (
    "user_daily_token_quota",
    "chatbot_daily_token_quota",
    "anon_ip_daily_token_quota",
)


def upgrade() -> None:
    op.add_column("hub_interactions", sa.Column("prompt_tokens", sa.Integer(), nullable=True))
    op.add_column(
        "hub_interactions", sa.Column("completion_tokens", sa.Integer(), nullable=True)
    )
    op.add_column("hub_interactions", sa.Column("cost_estimated", sa.Float(), nullable=True))

    op.create_table(
        "hub_usage_counters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("subject_type", sa.String(length=20), nullable=False),
        sa.Column("subject_id", sa.String(length=255), nullable=False),
        sa.Column("window_key", sa.String(length=20), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "subject_type", "subject_id", "window_key", name="uq_usage_counter_subject_window"
        ),
        sa.CheckConstraint(
            "subject_type IN ('user', 'chatbot', 'organizacion', 'ip')",
            name="ck_usage_counter_subject_type",
        ),
    )

    for columna in _CUOTAS_ORGANIZACION:
        op.add_column("hub_organizaciones", sa.Column(columna, sa.Integer(), nullable=True))
    for columna in _CUOTAS_CHATBOT:
        op.add_column("hub_chatbots", sa.Column(columna, sa.Integer(), nullable=True))


def downgrade() -> None:
    for columna in _CUOTAS_CHATBOT:
        op.drop_column("hub_chatbots", columna)
    for columna in _CUOTAS_ORGANIZACION:
        op.drop_column("hub_organizaciones", columna)

    op.drop_table("hub_usage_counters")

    op.drop_column("hub_interactions", "cost_estimated")
    op.drop_column("hub_interactions", "completion_tokens")
    op.drop_column("hub_interactions", "prompt_tokens")

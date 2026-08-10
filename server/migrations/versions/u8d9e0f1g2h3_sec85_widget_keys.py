"""SEC.8.5 — credencial de sitio para el widget público.

El widget embebía un JWT de sesión o un PAT completo en el HTML (`data-token`), con el rol y
las organizaciones de su dueño detrás. Esta tabla guarda la credencial que lo sustituye: por
chatbot, con hash, revocable, y sin identidad ninguna — lo único que autoriza es hablar con
su chatbot, y solo si es `public_anon`.

`ondelete="CASCADE"`: una clave sin su chatbot no significa nada.

Revision ID: u8d9e0f1g2h3
Revises: t7c8d9e0f1g2
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "u8d9e0f1g2h3"
down_revision = "t7c8d9e0f1g2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hub_widget_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_chatbots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_hub_widget_keys_chatbot_id", "hub_widget_keys", ["chatbot_id"])
    op.create_index("ix_hub_widget_keys_key_hash", "hub_widget_keys", ["key_hash"])


def downgrade() -> None:
    op.drop_index("ix_hub_widget_keys_key_hash", table_name="hub_widget_keys")
    op.drop_index("ix_hub_widget_keys_chatbot_id", table_name="hub_widget_keys")
    op.drop_table("hub_widget_keys")

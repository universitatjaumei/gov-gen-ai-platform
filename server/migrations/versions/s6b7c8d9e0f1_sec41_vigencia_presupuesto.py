"""SEC.4.1: ventana de vigencia y presupuesto acumulado por chatbot.

Revision ID: s6b7c8d9e0f1
Revises: r5a6b7c8d9e0
Create Date: 2026-08-02

Cuatro columnas de configuración y **ninguna de estado**. El estado —caducado, aún no
abierto, presupuesto agotado— se calcula al preguntarlo: un flag persistido se queda
obsoleto en cuanto pasa la fecha y obligaría a un job que lo refresque, y el consumo
acumulado es dato operacional que no puede vivir en una tabla que se sincroniza al cloud.

Los chatbots existentes quedan con las tres fechas/límites en NULL y el mensaje vacío, o
sea **exactamente como están hoy**: sin ventana, sin techo y sin caducar.
"""
from alembic import op
import sqlalchemy as sa

revision = "s6b7c8d9e0f1"
down_revision = "r5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_chatbots", sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "hub_chatbots", sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("hub_chatbots", sa.Column("total_token_budget", sa.Integer(), nullable=True))
    op.add_column(
        "hub_chatbots",
        sa.Column("unavailable_message", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("hub_chatbots", "unavailable_message")
    op.drop_column("hub_chatbots", "total_token_budget")
    op.drop_column("hub_chatbots", "valid_until")
    op.drop_column("hub_chatbots", "valid_from")

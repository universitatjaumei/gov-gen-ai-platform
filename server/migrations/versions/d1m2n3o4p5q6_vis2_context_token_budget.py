"""VIS.2: presupuesto de contexto en la cascada (organización → chatbot)

`hub_chatbots.context_token_budget` y `hub_organizaciones.default_context_token_budget`.
Ambas nullable, y eso es la decisión de diseño: NULL significa «heredar del nivel
superior», y el default de plataforma (128.000) vive en el `ConfigResolver`, no en la BD.
Con un valor no nulo por defecto en la tabla, cambiar el default de plataforma no llegaría
nunca a las filas ya creadas — que es como se convierte un default en 81 copias.

Lo consume `LongContextRetrievalStrategy` para RECORTAR el subconjunto inyectado. Antes de
VIS.2 lanzaba `ValueError` al pasarse del límite, que en producción es una caída y no un
aviso. RAG.5 usará la misma columna para su packer.

Revision ID: d1m2n3o4p5q6
Revises: c0l1m2n3o4p5
"""
from alembic import op
import sqlalchemy as sa

revision = "d1m2n3o4p5q6"
down_revision = "c0l1m2n3o4p5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_chatbots",
        sa.Column("context_token_budget", sa.Integer(), nullable=True),
    )
    op.add_column(
        "hub_organizaciones",
        sa.Column("default_context_token_budget", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_organizaciones", "default_context_token_budget")
    op.drop_column("hub_chatbots", "context_token_budget")

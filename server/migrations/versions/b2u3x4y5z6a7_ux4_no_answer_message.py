"""UX.4 — qué contesta el asistente cuando no sabe.

Hasta aquí era una constante del módulo (`NO_CITATION_FALLBACK`): «no tengo información
suficiente... ¿podrías reformular?». Correcto y poco útil: deja a quien pregunta en el mismo
sitio en el que estaba.

A quién hay que remitirlo **depende del asistente**. Infocampus atiende al público y al
estudiantado; mandar allí a alguien de Gerencia con una duda de gestión económica sería
mandarlo a la ventanilla equivocada. Por eso es configuración del chatbot y no una constante.

Columna propia y no reutilizar `unavailable_message`: ese es el mensaje de cuando el chatbot
está **cerrado** (SEC.4.1), que es otra situación. Un campo con dos significados acaba
mostrando el texto equivocado en uno de los dos casos.

NULL = el texto genérico de siempre.

Revision ID: b2u3x4y5z6a7
Revises: a1p2i3l4m5n6
"""
from alembic import op
import sqlalchemy as sa

revision = "b2u3x4y5z6a7"
down_revision = "a1p2i3l4m5n6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("hub_chatbots", sa.Column("no_answer_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("hub_chatbots", "no_answer_message")

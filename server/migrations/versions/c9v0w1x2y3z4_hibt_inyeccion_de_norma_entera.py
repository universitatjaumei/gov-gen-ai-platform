"""HIB.T — el mando de inyección del documento entero

El experimento de granularidad midió siete formas de decidir qué texto darle al modelo. La de
**cinco normas enteras elegidas por el top-k vectorial** fue la única que ganó a Gemini de forma
significativa (7 a 0, p=0,016) y quedó segunda de las siete (68 %, empatada con producción). Pero
se midió con una llamada directa al modelo, así que salió con **0 enlaces de 25**: sin contrato de
citas, sin ancla y sin aviso de vigencia. Tal como se midió no era desplegable.

**Y el modo `MD_LONG_CONTEXT` que ya existía no sirve**: selecciona por fecha de creación hasta
llenar el presupuesto e **ignora la consulta**. Para un corpus con leyes estatales de 279.425
tokens, eso es arbitrario.

Lo que faltaba no era una estrategia nueva sino un mando en la que ya hay:
`VectorRetrievalStrategy` ya elige por relevancia, agrupa por documento, construye la URL de cita
con su ancla, hidrata el aviso de desplazamiento y recorta a `top_k` documentos. Sólo cambia qué
texto pone en el `excerpt`.

**Nullable, y nulo significa heredar de la plataforma, que entra en `False`.** Los tres asistentes
en producción siguen inyectando el artículo; el mando existe para el tercer asistente de Gerencia,
creado como banco para comparar las tres estrategias sobre el mismo lote y el mismo corpus.

Revision ID: c9v0w1x2y3z4
Revises: b8u9v0w1x2y3
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = "c9v0w1x2y3z4"
down_revision = "b8u9v0w1x2y3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_chatbots",
        sa.Column("inject_whole_document", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "hub_organizaciones",
        sa.Column("default_inject_whole_document", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_organizaciones", "default_inject_whole_document")
    op.drop_column("hub_chatbots", "inject_whole_document")

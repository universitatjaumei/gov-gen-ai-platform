"""HIB.J — el pool de candidatos se puede configurar sin tocar el reranker

Hasta este prompt el número de fragmentos que se le pedían al híbrido era
`pool_size(top_k) if reranker else top_k`. Apagar el reranker en HIB.A —decisión correcta,
medida en cuatro ejes— encogió por tanto el pool de 30 fragmentos a 3, sin que nadie lo
pidiera y sin que ningún eje de la ablación lo mostrara. Y como justo después se agrupa por
documento, `retrieval_top_k = 3` dejó de significar tres documentos: medido sobre las 25
consultas del lote, 19 recibieron menos documentos que `top_k` y 6 recibieron uno solo.

`candidate_k` separa los dos mandos para siempre: la anchura del pool deja de ser un efecto
lateral de si hay reranker.

**NULL no es cero**: significa «derívalo de `retrieval_top_k`» con `pool_size()`, que es el
comportamiento por omisión y el único configurado hoy. Un defecto numérico congelaría todos
los chatbots existentes en el valor que tuviera esta columna el día de la migración, y ese
número dejaría de seguir a `retrieval_top_k` cuando alguien lo cambiara.

Revision ID: z6s7t8u9v0w1
Revises: y5r6s7t8u9v0
"""
from alembic import op
import sqlalchemy as sa

revision = "z6s7t8u9v0w1"
down_revision = "y5r6s7t8u9v0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_chatbots",
        sa.Column("candidate_k", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_chatbots", "candidate_k")

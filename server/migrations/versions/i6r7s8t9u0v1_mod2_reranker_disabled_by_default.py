"""MOD.2: el reranker queda desactivado por defecto

`reranker_enabled` pasa de True a False en los defaults de columna y en las filas que
todavia tienen el valor antiguo.

Por que, decidido con el usuario el 2026-08-01: con el default en True, en cuanto RAG.6
tenga implementacion el reranker se activa de golpe para TODOS los chatbots existentes. Eso
(a) acopla la disponibilidad del chat a un segundo servicio —el prompt de RAG.6 exige error
explicito y prohibe el fallback silencioso, asi que una caida del proveedor deja los
chatbots sin responder en vez de degradados—, (b) anade latencia y coste por consulta y
(c) no se ha medido que mejore la recuperacion en este corpus.

Es literalmente lo que ya paso con min_retrieval_score: activo por defecto, recortando 24
puntos de recall, y nadie lo habia comprobado. El mecanismo se construye en RAG.6; el
interruptor se enciende por chatbot cuando el gate de RAG.1 lo respalde.

Solo se actualizan las filas que valen True —el default antiguo—: si alguien lo puso a mano,
esa decision no se pisa. (Hoy nadie ha podido ponerlo a mano con intencion, porque no hay
implementacion que activar, pero la regla es la misma que en g4p5q6r7s8t9 y conviene que lo
siga siendo.)

Revision ID: i6r7s8t9u0v1
Revises: h5q6r7s8t9u0
"""
from alembic import op

revision = "i6r7s8t9u0v1"
down_revision = "h5q6r7s8t9u0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE hub_chatbots ALTER COLUMN reranker_enabled SET DEFAULT false")
    op.execute(
        "ALTER TABLE hub_organizaciones "
        "ALTER COLUMN default_reranker_enabled SET DEFAULT false"
    )
    op.execute(
        "UPDATE hub_chatbots SET reranker_enabled = false WHERE reranker_enabled = true"
    )
    op.execute(
        "UPDATE hub_organizaciones SET default_reranker_enabled = false "
        "WHERE default_reranker_enabled = true"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE hub_chatbots ALTER COLUMN reranker_enabled SET DEFAULT true")
    op.execute(
        "ALTER TABLE hub_organizaciones "
        "ALTER COLUMN default_reranker_enabled SET DEFAULT true"
    )
    op.execute(
        "UPDATE hub_chatbots SET reranker_enabled = true WHERE reranker_enabled = false"
    )
    op.execute(
        "UPDATE hub_organizaciones SET default_reranker_enabled = true "
        "WHERE default_reranker_enabled = false"
    )

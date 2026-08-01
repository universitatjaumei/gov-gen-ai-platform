"""RAG.5: el umbral de similitud queda implementado pero desactivado por defecto

`min_retrieval_score` pasa de 0,25 a 0,0 en los defaults de columna y en las filas que
todavia tienen el valor antiguo.

Por que, con la medicion delante: con 0,25 el dataset dorado cae de recall@5 0,960 a 0,720
y MRR 0,861 a 0,693. Ese 0,72 NO prueba que 0,25 sea mal umbral en produccion —el corpus de
fixture usa un embedding determinista cuyas similitudes coseno son estructuralmente bajas, y
BGE-M3 tiene otra distribucion—, pero tampoco se puede dejar activo un filtro que recorta un
24 % de recall en lo unico que hoy se puede medir. Un umbral ABSOLUTO es justo lo que ese
corpus no puede calibrar.

El mecanismo queda listo y la activacion pendiente de medir con el corpus real. Decidido con
el usuario el 2026-08-01.

Solo se actualizan las filas que valen exactamente 0.25 —el default antiguo—: un valor
distinto es una decision de alguien y no se pisa.

Revision ID: g4p5q6r7s8t9
Revises: f3o4p5q6r7s8
"""
from alembic import op

revision = "g4p5q6r7s8t9"
down_revision = "f3o4p5q6r7s8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE hub_chatbots ALTER COLUMN min_retrieval_score SET DEFAULT 0.0")
    op.execute(
        "ALTER TABLE hub_organizaciones "
        "ALTER COLUMN default_min_retrieval_score SET DEFAULT 0.0"
    )
    op.execute(
        "UPDATE hub_chatbots SET min_retrieval_score = 0.0 WHERE min_retrieval_score = 0.25"
    )
    op.execute(
        "UPDATE hub_organizaciones SET default_min_retrieval_score = 0.0 "
        "WHERE default_min_retrieval_score = 0.25"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE hub_chatbots ALTER COLUMN min_retrieval_score SET DEFAULT 0.25")
    op.execute(
        "ALTER TABLE hub_organizaciones "
        "ALTER COLUMN default_min_retrieval_score SET DEFAULT 0.25"
    )
    op.execute(
        "UPDATE hub_chatbots SET min_retrieval_score = 0.25 WHERE min_retrieval_score = 0.0"
    )
    op.execute(
        "UPDATE hub_organizaciones SET default_min_retrieval_score = 0.25 "
        "WHERE default_min_retrieval_score = 0.0"
    )

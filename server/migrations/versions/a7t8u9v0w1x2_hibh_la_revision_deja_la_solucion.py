"""HIB.H — la revisión deja la solución, no sólo el veredicto

REV.1 dio a `hub_interactions` el veredicto de quien revisa. Con eso se puede reformular la FAQ
que produjo una mala respuesta, pero no se puede **volver a medir**: cada conversación revisada
vale una vez, y la siguiente ablación —reranker sí o no, padre sí o no, otro umbral— exige pedir
de nuevo juicio humano sobre las mismas preguntas. Es la razón concreta por la que las ablaciones
no se hacían.

Con la fuente esperada estructurada, tres cosas se calculan solas para siempre: si el documento
que el informador esperaba entró en lo recuperado, si el ancla de la cita abre el artículo
correcto y si un negativo se rechazó como debía. Y el piloto pasa a producir juicios de
relevancia, que es la forma que necesita un banco de recuperación publicable.

**La misma forma en las dos tablas.** `hub_interactions.review_expected_sources` y
`hub_test_scenarios.expected_sources` guardan lo mismo y las valida el mismo modelo Pydantic
(`evaluation/escenario_contrato.py`). Dos formas para la misma idea divergen, y entonces el
instrumental que cruza conversaciones reales con escenarios de prueba deja de poder escribirse.

**NULL es «no anotado», no lista vacía**, y por eso no hay `server_default`. Una lista vacía
afirmaría que el informador miró y decidió que no hay fuente esperada, que es otra cosa; la
diferencia es el denominador de «cuántas están anotadas».

`expectation_note` se conserva: es la nota que lee quien juzga, y su valor —el motivo del fallo,
escrito por el informador— no cabe en un identificador.

Revision ID: a7t8u9v0w1x2
Revises: z6s7t8u9v0w1
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "a7t8u9v0w1x2"
down_revision = "z6s7t8u9v0w1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_interactions",
        sa.Column("review_expected_sources", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "hub_interactions",
        sa.Column("review_reference_answer", sa.Text(), nullable=True),
    )
    op.add_column(
        "hub_test_scenarios",
        sa.Column("expected_sources", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_test_scenarios", "expected_sources")
    op.drop_column("hub_interactions", "review_reference_answer")
    op.drop_column("hub_interactions", "review_expected_sources")

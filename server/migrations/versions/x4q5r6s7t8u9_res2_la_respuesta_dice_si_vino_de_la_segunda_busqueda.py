"""RES.2 — la ejecución dice si la respuesta vino de la segunda búsqueda

Se guarda por el mismo motivo que el aviso de lengua de VIS.5: distingue dos situaciones que quien
revisa necesita distinguir —«el corpus no lo tiene» y «el corpus lo tiene y la pregunta no lo
encontraba tal como se hizo»— y sin el dato las dos se leen igual desde la pantalla de escenarios.

Y es la materia prima de RES.3: el par (lo que escribió la persona, la consulta que funcionó) llega
ya validado por el hecho de haber funcionado, así que nadie tiene que inventarlo.

Revision ID: x4q5r6s7t8u9
Revises: w3p4q5r6s7t8
"""
from alembic import op
import sqlalchemy as sa

revision = "x4q5r6s7t8u9"
down_revision = "w3p4q5r6s7t8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # `server_default` y no sólo el default de Python: las filas que ya existen son de antes de
    # que la segunda búsqueda existiera, y para ellas «no vino de una reformulación» es cierto.
    op.add_column(
        "hub_test_runs",
        sa.Column(
            "reformulada",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "hub_test_runs",
        sa.Column("reformulated_query", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_test_runs", "reformulated_query")
    op.drop_column("hub_test_runs", "reformulada")

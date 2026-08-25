"""VIS.5 — la ejecución de un escenario guarda el aviso de lengua que se dio

El aviso de traducción llega al ciudadano —el widget lo pinta— y **no llegaba a ninguna de las
dos herramientas con las que se revisa si el asistente responde bien**: ni a la pantalla de
escenarios ni al lote. Así que un texto que decía algo equivocado —avisaba de la lengua de la
pregunta en vez de la de la norma, y se callaba justo en el caso más frecuente del corpus— podía
estar años sin que nadie lo viera al revisar.

Se guarda **el texto** y no el booleano: lo que hay que poder revisar es lo que se le mostró a
quien preguntó. El flag sólo dice que hubo aviso, no si decía la verdad.

Nullable porque las ejecuciones anteriores no lo tienen y no se puede reconstruir: el aviso
dependía de la lengua de la evidencia de aquel momento.

Revision ID: w3p4q5r6s7t8
Revises: v2o3p4q5r6s7
Create Date: 2026-08-25
"""
from alembic import op
import sqlalchemy as sa


revision = "w3p4q5r6s7t8"
down_revision = "v2o3p4q5r6s7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_test_runs",
        sa.Column("translation_warning", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_test_runs", "translation_warning")

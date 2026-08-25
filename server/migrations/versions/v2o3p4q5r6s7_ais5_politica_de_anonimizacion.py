"""AIS.5 — la organización fija su política de anonimización

El modo de anonimización vivía sólo en el informe, y la frase del usuario que lo cambia es que
«depende del contrato con el proveedor LLM y del tipo de datos». Ninguna de las dos cosas es una
decisión de quien redacta un informe concreto: el contrato es de la **organización**.

**Nullable y sin valor por omisión, a propósito.** Nulo significa «esta organización no lo ha
fijado», y entonces manda el valor del código (`politica.MODO_POR_DEFECTO`, hoy `replace`) — que
es lo que hacen hoy todos los informes. Así el piloto no nota nada: rellenar la columna con
`'replace'` en la migración diría que alguien decidió, y nadie ha decidido todavía.

No lleva `CheckConstraint` sobre los cuatro valores porque el enum ya lo valida en la aplicación
y la columna admite nulo; añadirlo obligaría a tocar la restricción cada vez que se añada un modo,
que es justo lo que MT.1 evitó para el vocabulario. El orden de protección vive en `politica.py`,
no en la base.

Revision ID: v2o3p4q5r6s7
Revises: u1n2o3p4q5r6
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa


revision = "v2o3p4q5r6s7"
down_revision = "u1n2o3p4q5r6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_organizaciones",
        sa.Column("anonymization_mode", sa.String(length=40), nullable=True),
    )


def downgrade() -> None:
    # Se pierde la política de cada organización, y es inevitable: sin columna no hay dónde
    # guardarla. Los informes vuelven al valor del código, que es el comportamiento anterior.
    op.drop_column("hub_organizaciones", "anonymization_mode")

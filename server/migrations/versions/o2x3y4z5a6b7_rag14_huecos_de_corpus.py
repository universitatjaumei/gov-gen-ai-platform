"""RAG.14: hallazgos a nivel de chatbot para los huecos de corpus.

Revision ID: o2x3y4z5a6b7
Revises: n1w2x3y4z5a6
Create Date: 2026-08-01

Extiende el contrato de hallazgos de 9Q sin romperlo: hasta ahora todo hallazgo colgaba de
un sitio web auditado, y un hueco de corpus nace de conversaciones — forzarle un sitio sería
inventarle un sitio web a una pregunta.

`site_id` pasa a nullable **y a la vez** entra un CHECK que exige exactamente uno de los dos
sujetos. Sin el CHECK, «nullable» se leería como «opcional» y acabaría habiendo hallazgos
sin sujeto, que no se pueden revisar ni atribuir.

`chatbot_id` va **sin FK**: `hub_chatbots` es configuración (cloud) y esta tabla es
operacional (edge). Cruzarlas rompería el split que sostiene el despliegue híbrido.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "o2x3y4z5a6b7"
down_revision = "n1w2x3y4z5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_content_findings",
        sa.Column("chatbot_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_hub_content_findings_chatbot_id", "hub_content_findings", ["chatbot_id"]
    )
    op.alter_column(
        "hub_content_findings",
        "site_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_finding_tiene_un_sujeto",
        "hub_content_findings",
        "(site_id IS NULL) <> (chatbot_id IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_finding_tiene_un_sujeto", "hub_content_findings", type_="check"
    )
    # Los hallazgos de chatbot no tienen sitio al que volver: se van con la columna.
    op.execute("DELETE FROM hub_content_findings WHERE site_id IS NULL")
    op.alter_column(
        "hub_content_findings",
        "site_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_index("ix_hub_content_findings_chatbot_id", table_name="hub_content_findings")
    op.drop_column("hub_content_findings", "chatbot_id")

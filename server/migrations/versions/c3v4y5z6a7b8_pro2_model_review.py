"""PRO.2 — el veredicto del modelo auditor, guardado con la propuesta.

Desde PRO.2 hay dos auditorías sobre el mismo script: la **determinista** (AST + rutas
absolutas), que es la que bloquea y no se puede convencer, y la del **modelo de nivel 3**, que
mira lo que un AST no puede ver —si el script hace lo que se pidió, si asume columnas que no
constan, si devuelve vacío sin fallar—.

Sin esta columna, esa segunda opinión moría en la respuesta HTTP del proponente: el
administrador que revisa la propuesta días después no la veía, y se habría pagado una llamada
a un modelo superior para nada.

Columna propia y **no una clave dentro de `audit_result_json`**: son dos cosas con dos
autoridades distintas. Mezclarlas invita a que algún consumidor lea la opinión del modelo
creyendo que lee la auditoría que de verdad decide.

NULL = no hubo revisión con modelo (no había auditor configurado, o la determinista ya
había encontrado un crítico y no hay semántica que juzgar en un script que no se ejecutará).

Revision ID: c3v4y5z6a7b8
Revises: b2u3x4y5z6a7
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c3v4y5z6a7b8"
down_revision = "b2u3x4y5z6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_script_proposals",
        sa.Column("model_review_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_script_proposals", "model_review_json")

"""PRO.2.1 — el prompt y el nivel de una actividad, sobreescribibles.

Los prompts de las actividades del módulo de Informes —escribir un script, auditarlo,
transformar datos— estaban escritos en Python: nadie podía afinar el texto sin desplegar ni
decidir con qué nivel de modelo corre cada una.

`hub_prompt_templates` no sirve para esto: su `chatbot_id` es NOT NULL, y una actividad de
plataforma no pertenece a ningún chatbot. **Tampoco se hace nullable**: en Postgres una
restricción unique con NULL no colisiona, así que `(chatbot_id, slug, language)` dejaría de ser
única justo para las filas nuevas —dos overrides de la misma actividad conviviendo— y la
pantalla que filtra por chatbot perdería el sentido.

La tabla guarda **sólo excepciones**. Qué actividades existen, con qué nivel corren y qué se
les dice lo dice el código (`modules/redaccion/services/actividades_llm.py`):

- `template_text` NULL o vacío = usa el texto del código.
- `override_tier` NULL = usa el nivel del código.

Por eso no se siembra nada: existir en código ya es existir.

Revision ID: d4w5z6a7b8c9
Revises: c3v4y5z6a7b8
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "d4w5z6a7b8c9"
down_revision = "c3v4y5z6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hub_activity_prompts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("activity", sa.String(length=100), nullable=False, unique=True),
        sa.Column("template_text", sa.Text(), nullable=True),
        sa.Column("override_tier", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("hub_activity_prompts")

"""SEC.8.6 — los temas pasan de ficheros locales a tabla.

Los temas se guardaban como `.json` bajo `data/themes`, ruta relativa al directorio de
trabajo del proceso. En Cloud Run el contenedor es efímero y hay varias instancias: el tema
creado en una no existe para las demás y desaparece al reciclarse. El widget lo heredaba,
porque resuelve su contenido desde el puntero `theme_config` del chatbot.

`organizacion_id` nulo = tema de plataforma (base de la cascada). Los dos FK con
`ondelete="CASCADE"`: un tema sin la organización o el chatbot a los que pertenece no
significa nada.

**No hay backfill.** Los ficheros de `data/themes` viven en el disco de cada instalación y
esta migración corre en la base de datos, que no los ve; en producción no existen todavía
(el despliegue es el primero) y en desarrollo se vuelven a crear desde el panel. Un backfill
tendría que leer un directorio del sistema de ficheros desde una migración, que es
exactamente el acoplamiento que este cambio viene a quitar.

Revision ID: t7c8d9e0f1g2
Revises: s6b7c8d9e0f1
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "t7c8d9e0f1g2"
down_revision = "s6b7c8d9e0f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hub_themes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "organizacion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_organizaciones.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "chatbot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hub_chatbots.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_hub_themes_organizacion_id", "hub_themes", ["organizacion_id"]
    )
    op.create_index("ix_hub_themes_chatbot_id", "hub_themes", ["chatbot_id"])


def downgrade() -> None:
    op.drop_index("ix_hub_themes_chatbot_id", table_name="hub_themes")
    op.drop_index("ix_hub_themes_organizacion_id", table_name="hub_themes")
    op.drop_table("hub_themes")

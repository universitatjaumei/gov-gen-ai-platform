"""PLAT.7: retira hub_organizaciones.theme_config, la copia que nadie leía.

La identidad visual de una organización vive en `hub_themes` y la resuelve la cascada
(plataforma → organización → asistente). Esta columna JSONB tenía un `<textarea>` a la vista
—«Configuración de tema (JSON)»— y **ningún lector**: dos sitios para lo mismo, y el visible era
el que no hacía nada. Se retira ahora y no antes porque PLAT.6 acaba de darle sustituto: sin la
pantalla de identidad visual, quitarla dejaba a la organización sin forma de configurar su tema.

Comprobado antes de borrar, como exige el prompt: las cinco organizaciones de la base de
desarrollo tenían `{}`. Si en otra instalación alguna llevara contenido, el `downgrade` recrea la
columna pero **no** puede devolver lo que hubiera dentro: repítase la consulta antes de aplicar.

    SELECT name, theme_config FROM hub_organizaciones WHERE theme_config <> '{}'::jsonb;

`HubChatbot.theme_config` se queda: ahí sí se lee, guarda `{"theme_id": ...}` y es de donde el
widget saca su tema.

Revision ID: o5h6i7j8k9l0
Revises: n4g5h6i7j8k9
Create Date: 2026-08-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "o5h6i7j8k9l0"
down_revision = "n4g5h6i7j8k9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("hub_organizaciones", "theme_config")


def downgrade() -> None:
    # Vacía y no nula, que es como nacía: el default del modelo era `dict`. El contenido
    # anterior no se recupera —la columna se borró—, y decirlo aquí evita que alguien
    # revierta creyendo que sí.
    op.add_column(
        "hub_organizaciones",
        sa.Column(
            "theme_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

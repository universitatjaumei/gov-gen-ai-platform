"""IDE.3 — quién dio de alta a cada persona

`hub_users` sabía **cuándo** se creó una fila (`created_at`) y no **quién** la creó. Mientras el
único escritor era el ACS de SAML la respuesta era obvia; con el alta manual de IDE.3 deja de
serlo, y un alta sin autoría no se puede auditar — el mismo argumento que `HubModuleGrant` ya
lleva escrito en su `granted_by`.

Nullable porque las filas que ya existen las creó el ACS y no hay a quién atribuirlas: rellenar
con un valor inventado sería peor que dejarlo vacío. `origen = 'sso'` ya dice lo que se sabe de
ellas.

Revision ID: m3f4g5h6i7j8
Revises: l2e3f4g5h6i7
Create Date: 2026-08-22
"""
from alembic import op
import sqlalchemy as sa

revision = "m3f4g5h6i7j8"
down_revision = "l2e3f4g5h6i7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_users",
        sa.Column("created_by", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_users", "created_by")

"""SEC.1: contraseña obligatoria en el login de Admin (hallazgo A1).

Revision ID: p3y4z5a6b7c8
Revises: o2x3y4z5a6b7
Create Date: 2026-08-02

`adminaccount` no tenía columna de hash, así que el login de Admin no comprobaba nada: no era
un descuido de una rama, es que no había contra qué comparar.

La columna entra **nullable y sin valor por defecto**, a propósito. Las cuentas que ya existen
se quedan con NULL, y NULL significa **login local deshabilitado** —entran por SSO o por PAT,
o un superadministrador les fija una contraseña con `PATCH /auth/admins/{id}/password`—.

Lo que NO se hace, y es deliberado:

- **No se inventa una contraseña de oficio** ni se deriva del email. Sembrar un secreto
  adivinable sería cambiar un agujero conocido por otro más difícil de ver.
- **No se pone NOT NULL.** Hacerlo obligaría a rellenar algo para cada fila existente, que es
  justo lo anterior con otro nombre. El NOT NULL solo tendría sentido cuando ninguna cuenta
  dependa de SSO, y ese día no ha llegado.
"""
from alembic import op
import sqlalchemy as sa

revision = "p3y4z5a6b7c8"
down_revision = "o2x3y4z5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "adminaccount",
        sa.Column("hashed_password", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("adminaccount", "hashed_password")

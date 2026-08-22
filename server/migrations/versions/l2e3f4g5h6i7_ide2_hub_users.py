"""IDE.2 — `hub_sso_users` pasa a ser `hub_users`, con el origen de cada persona

La tabla tiene correo único, nombre, rol, organización, activo y último acceso: es una tabla de
usuarios completa. Se llamaba «sso» porque su **único escritor** era el ACS de SAML. Mientras el
nombre dijera eso, nadie iba a escribir ahí una persona dada de alta a mano, y el siguiente que
lo necesitara habría creado una segunda tabla — que es como se llega a las cuatro que ya hay.

**`ALTER TABLE ... RENAME` y no crear-y-copiar**: renombrar no mueve los datos ni pierde las
claves ajenas que apuntan a la tabla. Copiar sí, y con filas dentro no hay motivo para asumir
ese riesgo.

**Los índices y la clave ajena se renombran también.** Postgres los deja funcionando con el
nombre viejo, así que no renombrarlos no rompe nada — pero deja un esquema donde
`ix_hub_sso_users_email` cuelga de `hub_users`, y el siguiente que lo lea tendrá que averiguar
si es un resto o algo vivo.

**`origen`** distingue quién creó la fila: `sso` (el ACS, Just-In-Time) o `manual` (una persona
desde el panel, IDE.3). Las filas que ya existen son `sso` por construcción: no había otro
escritor. Con `CheckConstraint` y no como `Enum` de Python — son dos valores estables, cada uno
con consumidor en el código, mismo criterio que `purpose` en `HubLLMConfig`.

El **defecto de servidor** es `sso` a propósito: el ACS no va a escribir la columna en cada
entrada, y una fila sin origen no puede quedarse en NULL porque la pantalla de IDE.4 distingue
las dos procedencias.

Revision ID: l2e3f4g5h6i7
Revises: k1d2e3f4g5h6
Create Date: 2026-08-22
"""
from alembic import op
import sqlalchemy as sa

revision = "l2e3f4g5h6i7"
down_revision = "k1d2e3f4g5h6"
branch_labels = None
depends_on = None

#: (nombre viejo, nombre nuevo) de lo que cuelga de la tabla y lleva su nombre dentro.
_INDICES = (
    ("ix_hub_sso_users_email", "ix_hub_users_email"),
    ("ix_hub_sso_users_organizacion_id", "ix_hub_users_organizacion_id"),
)
_RESTRICCIONES = (
    ("fk_hub_sso_users_organizacion_id", "fk_hub_users_organizacion_id"),
)

_CHECK_ORIGEN = "ck_hub_users_origen"


def upgrade() -> None:
    op.rename_table("hub_sso_users", "hub_users")

    for viejo, nuevo in _INDICES:
        op.execute(f'ALTER INDEX IF EXISTS "{viejo}" RENAME TO "{nuevo}"')
    for viejo, nuevo in _RESTRICCIONES:
        op.execute(
            f'ALTER TABLE hub_users RENAME CONSTRAINT "{viejo}" TO "{nuevo}"'
        )

    op.add_column(
        "hub_users",
        sa.Column(
            "origen",
            sa.String(length=10),
            nullable=False,
            server_default="sso",
        ),
    )
    op.create_check_constraint(
        _CHECK_ORIGEN, "hub_users", "origen IN ('sso', 'manual')"
    )


def downgrade() -> None:
    op.drop_constraint(_CHECK_ORIGEN, "hub_users", type_="check")
    op.drop_column("hub_users", "origen")

    for viejo, nuevo in _RESTRICCIONES:
        op.execute(
            f'ALTER TABLE hub_users RENAME CONSTRAINT "{nuevo}" TO "{viejo}"'
        )
    for viejo, nuevo in _INDICES:
        op.execute(f'ALTER INDEX IF EXISTS "{nuevo}" RENAME TO "{viejo}"')

    op.rename_table("hub_users", "hub_sso_users")

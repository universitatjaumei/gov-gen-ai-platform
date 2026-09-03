"""USR.5 — `adminaccount.email` único.

Revision ID: b7e0a4c81259
Revises: a6d9893f743a
Create Date: 2026-09-03

Dos sitios consultan ese correo esperando **una** fila —`login_admin` y el ACS de SAML— y la
columna no tenía restricción de unicidad. Con dos filas del mismo correo, cuál contesta depende
del orden que devuelva Postgres, que sin `ORDER BY` no está definido: el síntoma sería un **401
intermitente**, la misma contraseña entrando unas veces y otras no. `SuperAdminAccount` ya lo
tenía único, y por esta misma razón.

**Se hace ahora porque ahora es gratis.** Medido el 2026-09-03: `adminaccount` tiene 1 fila en
desarrollo y **0 en producción**. Con cuentas creadas haría falta decidir qué hacer con los
duplicados antes de poder crear el índice.

---

**La guarda del principio no es adorno.** Esta migración corre también en bases ajenas —cada
organización despliega desde su fork— y ahí puede haber duplicados. Sin la comprobación, el
`upgrade` moriría con el error de Postgres («could not create unique index … Key (email)=(…) is
duplicated»), que dice **qué** ha fallado y no **qué hacer**. Con ella, el mensaje nombra los
correos repetidos y dice que hay que resolverlos antes.
"""
import sqlalchemy as sa
from alembic import op

revision = "b7e0a4c81259"
down_revision = "a6d9893f743a"
branch_labels = None
depends_on = None

_INDICE = "ix_adminaccount_email"


def upgrade() -> None:
    conexion = op.get_bind()

    duplicados = conexion.execute(
        sa.text(
            """
            SELECT email, count(*) AS veces
              FROM adminaccount
             GROUP BY email
            HAVING count(*) > 1
             ORDER BY veces DESC, email
            """
        )
    ).all()
    if duplicados:
        detalle = ", ".join(f"{correo} ({veces} veces)" for correo, veces in duplicados)
        raise RuntimeError(
            "No se puede hacer único `adminaccount.email`: hay correos repetidos. "
            f"Repetidos: {detalle}. "
            "Decide qué cuenta se queda con cada correo y cambia o borra las demás; "
            "hasta entonces, `login_admin` y el ACS de SAML devuelven una fila indeterminada "
            "de las que comparten correo, y eso es un 401 intermitente."
        )

    op.create_index(_INDICE, "adminaccount", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index(_INDICE, table_name="adminaccount")

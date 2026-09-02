"""USR.1 — `hashed_password` en `hub_users`.

Revision ID: a6d9893f743a
Revises: e2b3c4d5f6a7
Create Date: 2026-09-02

La columna que le faltaba a `hub_users` para que una persona pueda entrar con contraseña
mientras el IdP institucional no esté configurado. **Nullable, y NULL significa «login local
deshabilitado»** —entra por SSO, o no entra—, jamás «pasa sin comprobar»: mismo criterio que
`AdminAccount.hashed_password`, y mismo motivo (SEC.1, hallazgo A1).

No hay *backfill* que hacer: todas las filas nacen sin contraseña y se la fija quien administra.

---

**Escrita a mano a partir del autogenerate, y merece decirse por qué**, porque el próximo que
ejecute `alembic revision --autogenerate` se va a encontrar lo mismo:

El autogenerate del 2026-09-02 propuso, además de esta columna, **borrar 40 tablas** —
`flowregistry`, `customscript`, `atom_registry`, `tasklog`, `enterprise_audit_log`,
`report_templates`…— y cambiar tres columnas a `NOT NULL`. Ninguna de esas cosas es de este
prompt:

- **Las 40 tablas son el legado de AutomatIA** que sigue vivo en la base de desarrollo y ya no
  está en el metadata de la aplicación. Borrarlas es una decisión del Bloque NIC, con su
  inventario delante, no un efecto colateral de añadir una columna.
- **Los tres `NOT NULL`** (`hub_content_findings.created_at`,
  `hub_provider_credentials.created_at` y `.updated_at`) son deriva real entre el modelo y la
  base de desarrollo, y arreglarlos en una base ajena con filas nulas rompería el
  `upgrade`. Quedan anotados aquí para que alguien los mire a propósito.

La regla que esto ejemplifica: **el autogenerate propone contra la base que tengas delante**, y
una base de desarrollo con años de historia propone barbaridades. Se lee y se recorta.
"""
import sqlalchemy as sa
from alembic import op

revision = "a6d9893f743a"
down_revision = "e2b3c4d5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_users",
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_users", "hashed_password")

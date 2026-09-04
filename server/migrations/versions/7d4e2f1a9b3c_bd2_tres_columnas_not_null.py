"""BD.2 — las tres columnas donde la migración dijo `nullable=True` y el modelo `NOT NULL`

Revision ID: 7d4e2f1a9b3c
Revises: 5c2e9f4a1b76
Create Date: 2026-09-04

| Columna | Migración que la creó | Base | Modelo |
|---|---|---|---|
| `hub_content_findings.created_at` | `u2d3e4f5g6h7` (9Q.1) | NULL admitido | `NOT NULL` |
| `hub_provider_credentials.created_at` | `q7j8k9l0m1n2` (MT.2) | NULL admitido | `NOT NULL` |
| `hub_provider_credentials.updated_at` | `q7j8k9l0m1n2` (MT.2) | NULL admitido | `NOT NULL` |

**Por qué divergen.** En los modelos la columna es `Mapped[datetime]` con `default=` y **sin
`nullable=` explícito**. SQLAlchemy 2.0 deduce `NOT NULL` de la anotación no opcional; la
migración, escrita a mano, dijo `nullable=True`. Dos fuentes escritas por separado y nadie las
comparó — que es lo que `alembic check` hace ahora en CI (BD.2).

**Ya estaban vistas.** REG.1 (`28d7fafbf4af`) y USR.1 (`a6d9893f743a`) las nombran en sus
docstrings: el `autogenerate` se las propuso, decidieron con razón que no eran suyas y las dejaron
anotadas «para que alguien las mire a propósito». Éste es ese alguien.

**Cuál es la verdad: el modelo.** Las tres tienen `default` en Python, así que todo `INSERT` por el
ORM las rellena. Medido: 292 filas de hallazgos en desarrollo y 292 en producción, **cero nulos** en
las dos; credenciales, cero filas en las dos.

**El backfill va aunque no haga falta aquí**, y es lo que USR.1 pedía: «arreglarlos en una base
ajena con filas nulas rompería el `upgrade`». Un fork de otra organización puede tener hallazgos
insertados a mano. En hallazgos se rellena con `detected_at`, que es `NOT NULL` y la mejor
aproximación honesta al momento de creación; en credenciales, con `now()`.

**`downgrade` vuelve a `nullable=True`**: es reversible de verdad, porque no destruye nada.
"""

from alembic import op

revision = "7d4e2f1a9b3c"
down_revision = "5c2e9f4a1b76"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Primero el relleno, luego la restricción: en este orden un `upgrade` no puede fallar por
    # una fila nula que este entorno no tenga y otro sí.
    op.execute(
        "UPDATE hub_content_findings SET created_at = detected_at WHERE created_at IS NULL"
    )
    op.alter_column("hub_content_findings", "created_at", nullable=False)

    op.execute(
        "UPDATE hub_provider_credentials SET created_at = now() WHERE created_at IS NULL"
    )
    op.execute(
        "UPDATE hub_provider_credentials SET updated_at = now() WHERE updated_at IS NULL"
    )
    op.alter_column("hub_provider_credentials", "created_at", nullable=False)
    op.alter_column("hub_provider_credentials", "updated_at", nullable=False)


def downgrade() -> None:
    op.alter_column("hub_provider_credentials", "updated_at", nullable=True)
    op.alter_column("hub_provider_credentials", "created_at", nullable=True)
    op.alter_column("hub_content_findings", "created_at", nullable=True)

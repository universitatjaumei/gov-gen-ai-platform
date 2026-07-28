"""ING.0.4 retirada de hub_documents.section_path (Caso B)

Declarada desde el esquema inicial y **jamás escrita** en todo `server/app`: solo se leía
en cuatro sitios que la pasaban como `None` a los metadatos de la evidencia. La ruta
estructural del fragmento vive ahora donde tiene sentido —`chunk_metadata['ruta']`, que el
chunker rellena con los encabezados ancestros—, así que la columna no tiene ningún uso
futuro y se retira en lugar de quedarse en el limbo (CLAUDE.md: borra, no comentes).

Revision ID: b9k0l1m2n3o4
Revises: a8j9k0l1m2n3
"""
import sqlalchemy as sa
from alembic import op

revision = "b9k0l1m2n3o4"
down_revision = "a8j9k0l1m2n3"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    return bool(
        bind.execute(
            sa.text(
                "select 1 from information_schema.columns "
                "where table_name = :t and column_name = :c"
            ),
            {"t": table, "c": column},
        ).first()
    )


def upgrade() -> None:
    if _column_exists("hub_documents", "section_path"):
        op.drop_column("hub_documents", "section_path")


def downgrade() -> None:
    op.add_column(
        "hub_documents", sa.Column("section_path", sa.String(1024), nullable=True)
    )

"""CUR.1 — la fecha que publica la página y la unidad que la mantiene

El portal las sirve en el HTML (`<div class="clockBarDate">` → `24/09/2025` | `Escola de Doctorat`) y
las estábamos ignorando: `stale` adivinaba la antigüedad del año más reciente citado en el texto y
marcaba 303 de 400 páginas. Con la fecha real, «desactualizada» es un dato; con el responsable, el
hallazgo dice a quién escribir.

Revision ID: i9b0e1f2g3h4
Revises: h8a9d0e1f2g3
Create Date: 2026-08-19
"""
from alembic import op
import sqlalchemy as sa

revision = "i9b0e1f2g3h4"
down_revision = "h8a9d0e1f2g3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_crawled_pages",
        sa.Column("content_published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "hub_crawled_pages",
        sa.Column("content_owner", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_crawled_pages", "content_owner")
    op.drop_column("hub_crawled_pages", "content_published_at")

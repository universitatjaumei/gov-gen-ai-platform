"""RAS.3 — cola de rastreo reanudable y clasificación del fallo de una página

`hub_web_sites.crawl_frontier` guarda la cola pendiente de una ejecución interrumpida: vivía sólo
en memoria, así que un corte obligaba a empezar por la raíz y, con la pausa de cortesía, a repetir
horas de peticiones contra el mismo servidor.

`hub_crawled_pages.error_kind` / `error_attempts` distinguen un 404 —una respuesta: eso ya no está—
de un 5xx o un `timeout`, del que no se puede concluir nada sobre la página. Los dos producían el
mismo hallazgo crítico.

Revision ID: g7z8c9d0e1f2
Revises: f6y7b8c9d0e1
Create Date: 2026-08-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "g7z8c9d0e1f2"
down_revision = "f6y7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("hub_web_sites", sa.Column("crawl_frontier", JSONB(), nullable=True))
    op.add_column(
        "hub_crawled_pages", sa.Column("error_kind", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "hub_crawled_pages", sa.Column("error_attempts", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("hub_crawled_pages", "error_attempts")
    op.drop_column("hub_crawled_pages", "error_kind")
    op.drop_column("hub_web_sites", "crawl_frontier")

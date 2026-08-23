"""REV.6 — quién firma la validación de vigencia, en su propia columna.

`hub_documents` ya tenía `vigencia_validada_el`, pero **nadie la escribía**: la cola de
validación se podía mirar y no tachar. Al darle un endpoint hacía falta registrar quién la
firma, y el sitio evidente —`revisat_per`— es el equivocado: ese campo viene del frontmatter
del corpus (`CorpusDocumentEntry.revisat_per`) y es la revisión humana del **contenido**, que
el contrato exige para `content_class: regulation`. Escribir ahí al que valida la vigencia
destruiría un dato obligatorio, y la columna «Revisado por» de la pantalla pasaría a enseñar a
quien pulsó el botón en vez del revisor declarado en el documento.

Son dos hechos distintos sobre dos momentos distintos, así que dos columnas.

Nullable sin defecto: las filas existentes no las validó nadie, y ponerles un valor sería
inventar una firma.

Revision ID: p6i7j8k9l0m1
Revises: o5h6i7j8k9l0
"""
from alembic import op
import sqlalchemy as sa

revision = "p6i7j8k9l0m1"
down_revision = "o5h6i7j8k9l0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_documents",
        sa.Column("vigencia_validada_per", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("hub_documents", "vigencia_validada_per")

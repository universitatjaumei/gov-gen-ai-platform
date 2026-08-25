"""RES.3 — pares léxicos revisables, con una persona en medio

La recuperación falla por vocabulario, no por corpus: «quiero tramitar una compra de un equipo de
6.500 euros» puntúa 0,126 contra un corpus que llama a eso «expedients de contractes menors». Esta
tabla guarda el par —lo que dijo la persona, la consulta que funcionó— y su estado de revisión.

Es **operacional**, no configuracion: `termino_de_usuario` es literalmente lo que escribio una
persona, y `HubConfigBase` se sincroniza cloud->edge, asi que ponerla ahi obligaria a que el
texto de las preguntas del cliente existiera en el cloud. Lo cazo el guardarrail de la frontera.

Se proyecta sobre `hub_document_chunks.bilingual_terms`, que ya alimenta el `tsvector` como columna
generada, así que aplicar un par aprobado es un `UPDATE` y no exige recalcular embeddings. Y la
proyección es **derivada**: se reconstruye entera desde aquí, de modo que quitar un término cuesta
lo mismo que ponerlo.

Sin `Enum` ni `CheckConstraint` sobre los términos: son dato y están para revisarse. Los `CHECK`
son sólo para `estado` y `origen`, que tienen consumidor en el código y valores estables.

Revision ID: y5r6s7t8u9v0
Revises: x4q5r6s7t8u9
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "y5r6s7t8u9v0"
down_revision = "x4q5r6s7t8u9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hub_lexicon_pairs",
        # Sin `server_default`: el id lo pone el modelo con `uuid.uuid4`, igual que el resto de
        # las tablas del esquema. `gen_random_uuid()` exigiría pgcrypto y no aporta nada aquí.
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # Sin FK a `hub_organizaciones`: la tabla es OPERACIONAL y los modelos operacionales
        # referencian por id sin FK, para que las dos bases sigan siendo separables.
        sa.Column("organizacion_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Sin FK a `hub_documents` tampoco: los modelos operacionales de este esquema no llevan
        # ninguna FK entre bases, y añadir la primera aquí no es el sitio para estrenarlo.
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("termino_de_usuario", sa.Text(), nullable=False),
        sa.Column("termino_normativo", sa.Text(), nullable=False),
        sa.Column(
            "estado", sa.String(length=20), nullable=False, server_default="propuesto"
        ),
        sa.Column(
            "origen", sa.String(length=20), nullable=False, server_default="reformulacion"
        ),
        sa.Column("vigent", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("substituit_per_codi", sa.String(length=80), nullable=True),
        sa.Column("revisado_por", sa.String(length=255), nullable=True),
        sa.Column("revisado_el", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "organizacion_id",
            "document_id",
            "termino_de_usuario",
            name="uq_lexicon_org_doc_termino",
        ),
        sa.CheckConstraint(
            "estado IN ('propuesto', 'aprobado', 'rechazado')",
            name="ck_lexicon_estado",
        ),
        sa.CheckConstraint(
            "origen IN ('reformulacion', 'manual')", name="ck_lexicon_origen"
        ),
    )
    op.create_index(
        "ix_hub_lexicon_pairs_organizacion_id", "hub_lexicon_pairs", ["organizacion_id"]
    )
    op.create_index(
        "ix_hub_lexicon_pairs_document_id", "hub_lexicon_pairs", ["document_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_hub_lexicon_pairs_document_id", table_name="hub_lexicon_pairs")
    op.drop_index(
        "ix_hub_lexicon_pairs_organizacion_id", table_name="hub_lexicon_pairs"
    )
    op.drop_table("hub_lexicon_pairs")

"""ING.0.1 vocabulario controlado del corpus: hub_vocabulary_terms

Ámbitos y submaterias como DATO versionado, no como enum. Deliberadamente SIN
CheckConstraint sobre `axis` ni `codi`: el vocabulario está pendiente de validación
por Secretaría General y tiene que poder cambiar sin migración (CLAUDE.md §5).

Renombrar o fusionar = fila nueva + la vieja con vigent=False y substituit_per_codi.
La cadena de sustituciones es la traza de auditoría; no hay tabla de historial.

Revision ID: z7i8j9k0l1m2
Revises: y6h7i8j9k0l1
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "z7i8j9k0l1m2"
down_revision = "y6h7i8j9k0l1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hub_vocabulary_terms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organizacion_id",
            UUID(as_uuid=True),
            sa.ForeignKey("hub_organizaciones.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("axis", sa.String(20), nullable=False),
        sa.Column("codi", sa.String(80), nullable=False),
        sa.Column("nom_primari", sa.String(255), nullable=False),
        sa.Column("nom_secundari", sa.String(255), nullable=True),
        sa.Column("parent_codi", sa.String(80), nullable=True),
        sa.Column("descripcio_router", sa.Text(), nullable=True),
        sa.Column("ordre", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vigent", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("substituit_per_codi", sa.String(80), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "organizacion_id", "axis", "codi", name="uq_vocabulary_org_axis_codi"
        ),
    )
    op.create_index(
        "ix_hub_vocabulary_terms_organizacion_id",
        "hub_vocabulary_terms",
        ["organizacion_id"],
    )
    # La consulta caliente es "términos vigentes de un eje de una organización"
    # (validación de documentos e índice del router).
    op.create_index(
        "ix_hub_vocabulary_terms_org_axis",
        "hub_vocabulary_terms",
        ["organizacion_id", "axis"],
    )


def downgrade() -> None:
    op.drop_index("ix_hub_vocabulary_terms_org_axis", table_name="hub_vocabulary_terms")
    op.drop_index(
        "ix_hub_vocabulary_terms_organizacion_id", table_name="hub_vocabulary_terms"
    )
    op.drop_table("hub_vocabulary_terms")

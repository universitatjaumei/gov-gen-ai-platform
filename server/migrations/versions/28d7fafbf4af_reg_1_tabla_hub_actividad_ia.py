"""REG.1 — la tabla del registro de actividad IA.

Revision ID: 28d7fafbf4af
Revises: c8f1b5d92e47
Create Date: 2026-09-03

**Escrita a mano a partir del autogenerate, y hay que decir por qué.** El autogenerate propuso,
además de esta tabla, **borrar cuarenta tablas del legacy de AutomatIA** —`customscript`,
`flowregistry`, `atom_registry`, `tasklog`…— y poner `NOT NULL` en tres columnas de
`hub_content_findings` y `hub_provider_credentials`.

Ninguna de esas cosas es de REG.1. Pasa porque el autogenerate compara los modelos con **la base
que tiene delante**, y la del desarrollador arrastra tablas de una aplicación anterior que el
proyecto ya no declara. Aplicarlo tal cual habría borrado cuarenta tablas con sus datos en la
primera máquina donde se ejecutara.

Es la misma trampa que el bloque USR dejó anotada, y la regla que sale de ella es que **una
migración se lee antes de aplicarla**, siempre: lo que el autogenerate propone es un borrador, no
un resultado. La retirada de esas tablas, si procede, es trabajo del bloque NIC con su inventario
delante.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "28d7fafbf4af"
down_revision: Union[str, None] = "c8f1b5d92e47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hub_actividad_ia",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organizacion_id", sa.UUID(), nullable=False),
        sa.Column("ocurrido_en", sa.DateTime(timezone=True), nullable=False),
        # Lo pone la base de datos, no el proceso que inserta: es la única marca de tiempo del
        # registro que no elige quien registra.
        sa.Column(
            "registrado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("herramienta", sa.String(length=100), nullable=False),
        sa.Column("agente", sa.String(length=255), nullable=True),
        sa.Column("finalidad", sa.String(length=500), nullable=False),
        sa.Column("modelo_usado", sa.String(length=100), nullable=True),
        # JSONB y sin CheckConstraint: las categorías son vocabulario revisable, no estructura.
        sa.Column(
            "categorias_datos",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("payload_hash", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        # Sin FK a `hub_organizaciones`, como el resto de las tablas operacionales: es lo que
        # mantiene separables la base de configuración y la operacional.
    )
    op.create_index(
        op.f("ix_hub_actividad_ia_organizacion_id"),
        "hub_actividad_ia",
        ["organizacion_id"],
        unique=False,
    )
    # Los dos filtros de la lectura del registro (REG.5): rango de fechas y herramienta.
    op.create_index(
        op.f("ix_hub_actividad_ia_ocurrido_en"),
        "hub_actividad_ia",
        ["ocurrido_en"],
        unique=False,
    )
    op.create_index(
        op.f("ix_hub_actividad_ia_herramienta"),
        "hub_actividad_ia",
        ["herramienta"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_hub_actividad_ia_herramienta"), table_name="hub_actividad_ia")
    op.drop_index(op.f("ix_hub_actividad_ia_ocurrido_en"), table_name="hub_actividad_ia")
    op.drop_index(
        op.f("ix_hub_actividad_ia_organizacion_id"), table_name="hub_actividad_ia"
    )
    op.drop_table("hub_actividad_ia")

"""IDE.5 — el sujeto de una concesión puede ser una persona o un grupo del IdP

`hub_module_grants.subject_id` era siempre una persona, así que conceder módulos era insertar
una fila por cabeza. Lo que el usuario quiere para el futuro —los permisos repartidos desde el
ERP a través de un atributo del IdP— tiene el transporte ya construido: `saml_groups` viaja en el
claim `groups` del JWT y el modo `restricted` de un chatbot ya lo consume.

Tres cambios, y los tres hacen falta:

1. **`subject_type`** (`usuario` | `grupo`) con `CheckConstraint`. Las filas que ya existen son
   `usuario`: no había otra cosa que pudieran ser.

2. **La restricción única pasa a incluir el tipo.** Sin eso, un grupo cuyo nombre coincidiera con
   el UUID de una persona no podría convivir con la concesión de esa persona — y peor, la clave
   dejaría de describir lo que identifica una concesión.

3. **`subject_id` se ensancha de 36 a 255.** Estaba dimensionado para un UUID. Un nombre de
   grupo de un IdP institucional no cabe ahí de forma fiable: sin esto, el primer grupo con
   nombre largo revienta el `INSERT` — y eso ocurre en producción, no aquí.

Revision ID: n4g5h6i7j8k9
Revises: m3f4g5h6i7j8
Create Date: 2026-08-22
"""
from alembic import op
import sqlalchemy as sa

revision = "n4g5h6i7j8k9"
down_revision = "m3f4g5h6i7j8"
branch_labels = None
depends_on = None

_UNICA_VIEJA = "uq_grant_subject_module"
_UNICA_NUEVA = "uq_grant_subject_type_module"
_CHECK = "ck_grant_subject_type"


def upgrade() -> None:
    op.add_column(
        "hub_module_grants",
        sa.Column(
            "subject_type",
            sa.String(length=10),
            nullable=False,
            server_default="usuario",
        ),
    )
    op.create_check_constraint(
        _CHECK, "hub_module_grants", "subject_type IN ('usuario', 'grupo')"
    )

    op.alter_column(
        "hub_module_grants",
        "subject_id",
        existing_type=sa.String(length=36),
        type_=sa.String(length=255),
        existing_nullable=False,
    )

    op.drop_constraint(_UNICA_VIEJA, "hub_module_grants", type_="unique")
    op.create_unique_constraint(
        _UNICA_NUEVA,
        "hub_module_grants",
        ["subject_type", "subject_id", "module_code"],
    )


def downgrade() -> None:
    op.drop_constraint(_UNICA_NUEVA, "hub_module_grants", type_="unique")

    # Las concesiones de grupo no caben en el modelo anterior: si se dejaran, la restricción
    # única vieja podría fallar y, peor, quedarían leyéndose como concesiones de persona con un
    # `subject_id` que no es ningún UUID. Se retiran, que es lo que significa revertir esto.
    op.execute("DELETE FROM hub_module_grants WHERE subject_type = 'grupo'")

    op.create_unique_constraint(
        _UNICA_VIEJA, "hub_module_grants", ["subject_id", "module_code"]
    )
    op.alter_column(
        "hub_module_grants",
        "subject_id",
        existing_type=sa.String(length=255),
        type_=sa.String(length=36),
        existing_nullable=False,
    )
    op.drop_constraint(_CHECK, "hub_module_grants", type_="check")
    op.drop_column("hub_module_grants", "subject_type")

"""SEC.2.1: modo de acceso por chatbot + organización del usuario SSO.

Revision ID: q4z5a6b7c8d9
Revises: p3y4z5a6b7c8
Create Date: 2026-08-02

Dos columnas nuevas y una decisión en cada una, ambas **fail-closed**:

1. `hub_chatbots.access_mode` entra como `'authenticated'` para **todos** los chatbots
   existentes. NO se usa `'public_anon'` como valor de migración: hoy no existe endpoint
   anónimo —llega en D.1— y abrirlo por migración expondría el corpus de cada organización
   sin que nadie lo haya decidido. Un cambio de esquema no es el sitio donde se toman
   decisiones de publicación.

2. `hub_sso_users.organizacion_id` entra **vacía y nullable**. No se rellena por defecto:
   la organización de un usuario SAML sale de la configuración del IdP
   (`SAML_ORGANIZACION_ID`) y se le asigna en su siguiente entrada, no de una suposición
   escrita aquí. Mientras tanto no accede a recursos de organización, que es la regla de
   SEC.2 aplicada sin excepciones.

Las dos listas de autorización (`allowed_roles`, `allowed_saml_groups`) entran vacías, y en
modo `restricted` una lista vacía significa «solo el superadministrador»: no hay forma de
que esta migración abra nada.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "q4z5a6b7c8d9"
down_revision = "p3y4z5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hub_chatbots",
        sa.Column(
            "access_mode",
            sa.String(length=20),
            nullable=False,
            server_default="authenticated",
        ),
    )
    op.add_column(
        "hub_chatbots",
        sa.Column(
            "allowed_roles",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "hub_chatbots",
        sa.Column(
            "allowed_saml_groups",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.create_check_constraint(
        "ck_chatbot_access_mode",
        "hub_chatbots",
        "access_mode IN ('public_anon', 'authenticated', 'restricted')",
    )

    op.add_column(
        "hub_sso_users",
        sa.Column("organizacion_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_hub_sso_users_organizacion_id", "hub_sso_users", ["organizacion_id"]
    )
    op.create_foreign_key(
        "fk_hub_sso_users_organizacion_id",
        "hub_sso_users",
        "hub_organizaciones",
        ["organizacion_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_hub_sso_users_organizacion_id", "hub_sso_users", type_="foreignkey"
    )
    op.drop_index("ix_hub_sso_users_organizacion_id", table_name="hub_sso_users")
    op.drop_column("hub_sso_users", "organizacion_id")

    op.drop_constraint("ck_chatbot_access_mode", "hub_chatbots", type_="check")
    op.drop_column("hub_chatbots", "allowed_saml_groups")
    op.drop_column("hub_chatbots", "allowed_roles")
    op.drop_column("hub_chatbots", "access_mode")

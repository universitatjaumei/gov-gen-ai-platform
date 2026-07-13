"""ROL.1 renombrado institucional: admin->superadmin, partner->admin, HubClient->HubOrganizacion

Renombra tablas y columnas preservando datos (ALTER ... RENAME, nunca drop+create):
- adminaccount        -> superadminaccount   (cuenta SuperAdmin)
- partneraccount      -> adminaccount         (ex-Partner pasa a Admin)  [tras el anterior]
- hub_clients         -> hub_organizaciones
- hub_chatbots.client_id   -> organizacion_id
- hub_web_sites.client_id  -> organizacion_id

Las FK en Postgres siguen a la tabla por OID, así que el renombrado de tablas no
rompe las referencias de clientaccount/billingrecord/... a partneraccount.

Revision ID: y6h7i8j9k0l1
Revises: x5g6h7i8j9k0
"""
from alembic import op

revision = "y6h7i8j9k0l1"
down_revision = "x5g6h7i8j9k0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Cuentas (orden importa para no colisionar en 'adminaccount').
    op.rename_table("adminaccount", "superadminaccount")
    op.execute("ALTER INDEX ix_adminaccount_email RENAME TO ix_superadminaccount_email")
    op.rename_table("partneraccount", "adminaccount")

    # 2) Organización (ex-cliente del Hub).
    op.rename_table("hub_clients", "hub_organizaciones")
    op.execute(
        "ALTER INDEX ix_hub_clients_partner_id RENAME TO ix_hub_organizaciones_partner_id"
    )

    # 3) client_id -> organizacion_id en las tablas del Hub.
    op.alter_column("hub_chatbots", "client_id", new_column_name="organizacion_id")
    op.execute(
        "ALTER TABLE hub_chatbots RENAME CONSTRAINT hub_chatbots_client_id_fkey "
        "TO hub_chatbots_organizacion_id_fkey"
    )
    op.alter_column("hub_web_sites", "client_id", new_column_name="organizacion_id")
    op.execute(
        "ALTER INDEX ix_hub_web_sites_client_id RENAME TO ix_hub_web_sites_organizacion_id"
    )


def downgrade() -> None:
    op.execute(
        "ALTER INDEX ix_hub_web_sites_organizacion_id RENAME TO ix_hub_web_sites_client_id"
    )
    op.alter_column("hub_web_sites", "organizacion_id", new_column_name="client_id")
    op.execute(
        "ALTER TABLE hub_chatbots RENAME CONSTRAINT hub_chatbots_organizacion_id_fkey "
        "TO hub_chatbots_client_id_fkey"
    )
    op.alter_column("hub_chatbots", "organizacion_id", new_column_name="client_id")

    op.execute(
        "ALTER INDEX ix_hub_organizaciones_partner_id RENAME TO ix_hub_clients_partner_id"
    )
    op.rename_table("hub_organizaciones", "hub_clients")

    op.rename_table("adminaccount", "partneraccount")
    op.execute("ALTER INDEX ix_superadminaccount_email RENAME TO ix_adminaccount_email")
    op.rename_table("superadminaccount", "adminaccount")

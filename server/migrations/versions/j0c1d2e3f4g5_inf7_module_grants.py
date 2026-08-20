"""INF.7 — módulos de la plataforma y concesiones por usuario

Hasta aquí no había control de acceso por función: `App.tsx` metía todas las rutas bajo un
`PrivateRoute` que solo comprobaba que hubiera sesión, y los routers de `redaccion` usaban
`get_current_user` a secas. Con el módulo de informes abierto a toda la organización, cualquier
trabajador con cuenta podía listar y editar los chatbots institucionales.

El catálogo va en tabla y no como `Enum`/`CheckConstraint`: los módulos son dato, igual que el
vocabulario del corpus. Y los administradores que ya existen reciben los cuatro módulos, para
que nadie se quede fuera de lo que hoy usa.

Revision ID: j0c1d2e3f4g5
Revises: i9b0e1f2g3h4
Create Date: 2026-08-20
"""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "j0c1d2e3f4g5"
down_revision = "i9b0e1f2g3h4"
branch_labels = None
depends_on = None

#: Semilla del catálogo. La misma lista que `core/auth/modulos.py`, aquí porque una migración no
#: debe importar código de la aplicación: si mañana cambia la constante, esta migración tiene
#: que seguir describiendo lo que hizo el día que se aplicó.
_MODULOS = (
    ("chatbots", "Chatbots y asistentes"),
    ("curacion", "Curación de contenido"),
    ("informes", "Informes"),
    ("plataforma", "Administración de la plataforma"),
)


def upgrade() -> None:
    op.create_table(
        "hub_platform_modules",
        sa.Column("code", sa.String(length=50), primary_key=True),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("vigente", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "hub_module_grants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subject_id", sa.String(length=36), nullable=False, index=True),
        sa.Column("module_code", sa.String(length=50), nullable=False, index=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("granted_by", sa.String(length=36), nullable=True),
        # Conceder dos veces el mismo módulo no significa nada distinto de concederlo una.
        sa.UniqueConstraint("subject_id", "module_code", name="uq_grant_subject_module"),
    )

    catalogo = sa.table(
        "hub_platform_modules",
        sa.column("code", sa.String),
        sa.column("label", sa.String),
    )
    op.bulk_insert(
        catalogo,
        [{"code": code, "label": label} for code, label in _MODULOS],
    )

    # Los administradores que ya existen conservan todo lo que hoy usan. El superadmin no
    # necesita fila —entra en todo por su rol—, pero se le siembra igual para que la tabla
    # cuente la verdad de quién tiene acceso a qué.
    #
    # La clave del sujeto se calcula **en Python** con `uuid.uuid5(NAMESPACE_DNS, id)`, que es
    # exactamente lo que hace `_actor.user_to_uuid`. En SQL haría falta la extensión
    # `uuid-ossp`, que no se puede dar por instalada, y además las tablas de cuenta no tienen
    # una columna `id`: son `superadminaccount.admin_id` (entero) y `adminaccount.partner_id`
    # (texto). Eso es justo por lo que existe `user_to_uuid`.
    conexion = op.get_bind()
    codigos = [codigo for codigo, _ in _MODULOS]

    sujetos: list[str] = []
    for tabla, clave in (("superadminaccount", "admin_id"), ("adminaccount", "partner_id")):
        for (valor,) in conexion.execute(sa.text(f"SELECT {clave} FROM {tabla}")):
            bruto = str(valor)
            try:
                sujetos.append(str(uuid.UUID(bruto)))
            except ValueError:
                sujetos.append(str(uuid.uuid5(uuid.NAMESPACE_DNS, bruto)))

    if sujetos:
        conexion.execute(
            sa.text(
                "INSERT INTO hub_module_grants (subject_id, module_code, granted_by)"
                " VALUES (:sujeto, :modulo, 'migracion:inf7')"
                " ON CONFLICT (subject_id, module_code) DO NOTHING"
            ),
            [
                {"sujeto": sujeto, "modulo": codigo}
                for sujeto in sujetos
                for codigo in codigos
            ],
        )


def downgrade() -> None:
    op.drop_table("hub_module_grants")
    op.drop_table("hub_platform_modules")

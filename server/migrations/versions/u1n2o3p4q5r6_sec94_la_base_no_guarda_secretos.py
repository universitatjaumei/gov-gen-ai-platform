"""SEC.9.4 — la credencial de un proveedor deja de poder guardar el secreto

MT.2 dejó tres métodos y uno de ellos, `clave`, guardaba la clave literal en texto plano en
`hub_provider_credentials.api_key`. No estaba expuesto por HTTP —esa tabla no tiene router—, así
que el riesgo era el otro: un volcado, una copia de seguridad, una réplica de lectura o el payload
de la sincronización cloud→edge.

Decisión del usuario (2026-08-24): **restringir el método en vez de cifrar**. Cifrar mueve el
secreto al entorno del mismo proceso que lo descifra y añade gestión de clave para siempre —rotar
obliga a recifrar, perderla es perder todas las credenciales, la copia sólo se restaura con ella—.
Restringir deja en la base un **puntero** (el nombre de la variable) o nada (ADC), y entonces los
volcados dejan de ser sensibles por construcción.

**Se puede hacer sin migrar datos porque la tabla está vacía.** Se comprueba antes de borrar: si
hubiera filas con `metodo='clave'`, la migración se detiene en vez de tirar credenciales por la
ventana. El `downgrade` devuelve la columna y el CHECK anterior; los valores no vuelven, porque
esta migración no los guarda en ningún sitio — y guardarlos «por si acaso» sería dejar el secreto
en la base con otro nombre.

Revision ID: u1n2o3p4q5r6
Revises: t0m1n2o3p4q5
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa


revision = "u1n2o3p4q5r6"
down_revision = "t0m1n2o3p4q5"
branch_labels = None
depends_on = None

_CHECK = "ck_provider_credential_metodo"


def upgrade() -> None:
    conexion = op.get_bind()

    # No borrar a ciegas: si alguien creó credenciales con clave literal entre MT.2 y aquí, hay
    # que enterarse antes de perderlas, no después.
    pendientes = conexion.execute(
        sa.text("SELECT count(*) FROM hub_provider_credentials WHERE metodo = 'clave'")
    ).scalar_one()
    if pendientes:
        raise RuntimeError(
            f"{pendientes} credencial(es) con metodo='clave'. Antes de aplicar esta migración, "
            "muévelas a 'variable_de_entorno': crea la variable con el valor actual y pon su "
            "NOMBRE en secret_env. Esta migración borra la columna api_key y no guarda copia."
        )

    op.drop_constraint(_CHECK, "hub_provider_credentials", type_="check")
    op.create_check_constraint(
        _CHECK,
        "hub_provider_credentials",
        "metodo IN ('variable_de_entorno', 'entorno_de_ejecucion')",
    )
    op.drop_column("hub_provider_credentials", "api_key")


def downgrade() -> None:
    op.add_column(
        "hub_provider_credentials",
        sa.Column("api_key", sa.String(length=255), nullable=True),
    )
    op.drop_constraint(_CHECK, "hub_provider_credentials", type_="check")
    op.create_check_constraint(
        _CHECK,
        "hub_provider_credentials",
        "metodo IN ('clave', 'variable_de_entorno', 'entorno_de_ejecucion')",
    )

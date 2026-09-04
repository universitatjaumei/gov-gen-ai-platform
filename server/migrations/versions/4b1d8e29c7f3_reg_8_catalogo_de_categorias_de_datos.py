"""REG.8 — el catálogo de categorías de datos, sembrado por organización.

**No crea ninguna tabla**: los términos van a `hub_vocabulary_terms` con el eje nuevo
`categoria_dades`. Un catálogo de protección de datos necesita exactamente lo que esa tabla ya
da —`vigent` para retirar sin borrar el histórico, `substituit_per_codi` para renombrar dejando
la traza, y el par de nombres para las dos lenguas—, y una tabla propia habría tenido que
reinventarlo; lo probable es que hubiera empezado borrando filas.

**Por qué se siembra en vez de dejarlo vacío.** El `POST` acepta cualquier código a propósito,
porque rechazar uno no catalogado convertiría «esta categoría todavía no está dada de alta» en
«este uso de IA no queda registrado». Pero un catálogo vacío no lo rellena nadie: el primer
integrador inventa sus códigos, el segundo inventa otros, y el registro deja de poder agregarse.
Con un punto de partida, las herramientas convergen desde el primer día.

**Por organización, y una fila por cada una.** `hub_vocabulary_terms` tiene `organizacion_id` NOT
NULL desde ING.0.1: no hay vocabulario de plataforma que heredar, porque cada administración
clasifica a su manera. Así que se siembra con un `INSERT ... SELECT` sobre las organizaciones que
existan, y `ON CONFLICT` por la restricción única `(organizacion_id, axis, codi)` para que
volver a aplicarla no duplique nada.

**Las organizaciones que se creen después no quedan cubiertas por esta migración.** Es asumido y
no un olvido: el catálogo está pendiente de validación por quien lleve el registro de actividades
de tratamiento, así que la alternativa —sembrarlo en el alta de organización— fijaría en el código
un vocabulario que va a cambiar. Una organización sin catálogo recibe una lista vacía, que el
endpoint responde sin fallar.

Revision ID: 4b1d8e29c7f3
Revises: 3a9c1e77b402
Create Date: 2026-09-04
"""
from alembic import op
import sqlalchemy as sa

revision = "4b1d8e29c7f3"
down_revision = "3a9c1e77b402"
branch_labels = None
depends_on = None

_EJE = "categoria_dades"

# Copiadas de `core/actividad_categorias.py` **a propósito**: una migración es un hecho histórico
# y tiene que seguir haciendo lo mismo dentro de un año, aunque la semilla del código cambie. Un
# import aquí ataría el pasado al presente. El guardarraíl de REG.8 comprueba que hoy coinciden.
_CATEGORIAS: tuple[tuple[str, str], ...] = (
    ("datos_identificativos", "Datos identificativos"),
    ("datos_de_contacto", "Datos de contacto"),
    ("caracteristicas_personales", "Características personales"),
    ("datos_academicos_y_profesionales", "Datos académicos y profesionales"),
    ("datos_economicos_y_financieros", "Datos económicos y financieros"),
    ("datos_de_trafico_y_conexion", "Datos de tráfico y de conexión"),
    ("datos_de_categoria_especial", "Datos de categoría especial (art. 9 RGPD)"),
    ("sin_datos_personales", "Sin datos personales"),
)


def upgrade() -> None:
    conexion = op.get_bind()

    for orden, (codi, nom) in enumerate(_CATEGORIAS):
        conexion.execute(
            sa.text(
                "INSERT INTO hub_vocabulary_terms"
                " (id, organizacion_id, axis, codi, nom_primari, ordre, vigent)"
                " SELECT gen_random_uuid(), o.id, :eje, :codi, :nom, :ordre, true"
                "   FROM hub_organizaciones AS o"
                " ON CONFLICT ON CONSTRAINT uq_vocabulary_org_axis_codi DO NOTHING"
            ),
            {"eje": _EJE, "codi": codi, "nom": nom, "ordre": orden},
        )


def downgrade() -> None:
    conexion = op.get_bind()
    # Sólo los códigos que sembró esta migración: uno dado de alta después es de su autor, y
    # borrarlo dejaría eventos apuntando a una categoría que nadie puede leer.
    conexion.execute(
        sa.text(
            "DELETE FROM hub_vocabulary_terms"
            " WHERE axis = :eje AND codi = ANY(:codis)"
        ),
        {"eje": _EJE, "codis": [codi for codi, _nom in _CATEGORIAS]},
    )

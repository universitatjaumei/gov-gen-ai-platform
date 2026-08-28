"""ACT.3 — retirar `canonica`: el emparejamiento se queda, la jerarquia no

Las dos versiones publicadas de una norma son OFICIALES. A l'UJI la normativa s'aprova en
valencia —salvo algun reglament del Consell Social— i el Reglament de Politica Linguistica
manda traduir-ne algunes; la traduccio la publica Secretaria General o l'organ que va dictar
la resolucio. No hay jerarquia entre ellas, y llamar «canonica» a una invitaba a leer que la
otra vale menos.

El campo, ademas, hacia dano: era un FILTRO DURO en la recuperacion, asi que la version
castellana de una norma bilingue no se recuperaba nunca y preguntar en castellano devolvia el
texto valenciano. Con el corpus del 27-08-2026 eso pasaba de 33 normas a 57.

Lo que la recuperacion necesita es saber que dos documentos son la MISMA norma, y eso ya esta
en `versio_idiomatica_de`, que no se toca. La regla nueva vive en `metadata_filter`: quedate
con la version en la lengua de la pregunta; si esa norma no la tiene, quedate con la que hay.

Tampoco sostenia a VIS.3, que es lo que parecia: medido sobre el corpus real, de las 57 parejas
**47 tienen url_oficial distinta** —cada lengua su PDF— y solo 5 comparten URL. La guarda se
reescribio para decir lo que de verdad detecta (dos documentos que reclaman la misma URL sin ser
hermanas idiomaticas) y ya no se puede silenciar marcando algo como no canonico.

La bajada rehace la columna con su valor por defecto. No reconstruye que era `false` en cada
fila: eso se deriva del corpus en una pasada del reconciliador, que es de donde salio.

Revision ID: d1a2b3c4e5f6
Revises: c9v0w1x2y3z4
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = "d1a2b3c4e5f6"
down_revision = "c9v0w1x2y3z4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("hub_documents", "canonica")


def downgrade() -> None:
    op.add_column(
        "hub_documents",
        sa.Column(
            "canonica",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

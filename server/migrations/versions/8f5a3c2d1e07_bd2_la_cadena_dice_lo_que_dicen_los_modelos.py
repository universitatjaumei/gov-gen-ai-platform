"""BD.2 — la cadena de migraciones pasa a decir lo mismo que los modelos

Revision ID: 8f5a3c2d1e07
Revises: 7d4e2f1a9b3c
Create Date: 2026-09-04

**Cómo apareció esto.** BD.2 puso `alembic check` a comparar los modelos con una base recién
creada por la cadena, y en su primera ejecución encontró siete diferencias que el censo de tablas
de BD.1 no podía ver. Desarrollo no las tenía —sus tablas nacieron de `create_all`, con la forma
del modelo—; **producción sí, porque nació sólo de Alembic**. Comprobado allí en solo lectura
antes de escribir esto.

| Diferencia | En la cadena | En el modelo | Verdad |
|---|---|---|---|
| FK `hub_document_chunks.chatbot_id → hub_chatbots` (CASCADE) | existe (`a1b2c3d4e5f6`) | no | **modelo** |
| FK `hub_interactions.chatbot_id → hub_chatbots` (CASCADE) | existe (`a1b2c3d4e5f6`) | no | **modelo** |
| FK `hub_ingestion_jobs.chatbot_id → hub_chatbots` (CASCADE) | existe (`a1b2c3d4e5f6`) | no | **modelo** |
| índice `ix_hub_document_chunks_chatbot_id` | falta en dos entornos, existe en prod | `index=True` | **modelo** |
| índice `ix_hub_interactions_chatbot_id` | falta | `index=True` | **modelo** |
| índice `ix_hub_ingestion_jobs_chatbot_id` | falta | `index=True` | **modelo** |
| índice `ix_hub_vocabulary_terms_org_axis` | existe (`z7i8j9k0l1m2`) | no | **modelo** |

**Las tres FK cruzadas, y por qué se retiran.** `hub_chatbots` es `HubConfigBase` (se sincroniza
cloud→edge) y las tres tablas son `HubOperationalBase` (viven sólo en el edge). `AGENTS.md`
prohíbe cruzar las dos bases, y el código ya vive así: `corpus_purge.py` dice que la FK de
`hub_documents` «se cayó con el split y la frontera pide que no vuelva», y PIL.2 borra el corpus a
mano por eso. Estas tres se quedaron en la cadena porque la primera migración del Hub las creó y
nadie las quitó cuando los modelos dejaron de declararlas.

**Y una de ellas hacía daño de verdad.** `corpus_purge.py` decide que **las interacciones no se
borran** al borrar un chatbot: «son el registro de lo que el asistente contestó, no su corpus, y
desde REV.1 son material de revisión. Borrar un chatbot no reescribe la historia de lo que dijo».
En desarrollo eso se cumple. **En producción no**: `hub_interactions_chatbot_id_fkey` tiene
`ON DELETE CASCADE`, así que borrar un chatbot allí destruía sus interacciones en silencio, contra
la decisión escrita. Retirar la FK hace que producción haga lo que el código dice que hace.

**Los índices sobre `chatbot_id`.** Los tres modelos los declaran (`index=True`) y la cadena nunca
los creó, salvo el de `chunks`, que alguna migración posterior añadió. Son la clave de todas las
consultas por chatbot, y `hub_document_chunks` tiene 164.000 filas en producción.

**El índice `ix_hub_vocabulary_terms_org_axis`.** ING.0.1 lo creó para «términos vigentes de un
eje de una organización». Es redundante: la restricción única `(organizacion_id, axis, codi)`
es un B-tree cuyo prefijo `(organizacion_id, axis)` sirve exactamente esa consulta. El modelo no lo
declara y desarrollo lleva meses sin él. Se quita, y si alguna vez mide mal, vuelve **con su
declaración en el modelo**, que es lo que faltó.

**Idempotente a propósito.** `IF EXISTS` / `IF NOT EXISTS` en todo: en desarrollo, que ya tiene la
forma del modelo, esta migración no hace nada; en producción hace las siete cosas. La misma
revisión tiene que valer en las dos.

**`downgrade` no recrea las FK cruzadas**, y está razonado: recrearlas volvería a violar la
frontera edge/cloud y, además, fallaría en cualquier base que tenga interacciones de chatbots ya
borrados — que es la situación normal por diseño desde PIL.2. Sí deshace los índices.
"""

from alembic import op

revision = "8f5a3c2d1e07"
down_revision = "7d4e2f1a9b3c"
branch_labels = None
depends_on = None


#: (tabla, nombre de la FK). Los nombres son los que genera Postgres por defecto y los que
#: `alembic check` reportó; se comprobó en producción que existen con esos nombres.
FK_CRUZADAS = (
    ("hub_document_chunks", "hub_document_chunks_chatbot_id_fkey"),
    ("hub_interactions", "hub_interactions_chatbot_id_fkey"),
    ("hub_ingestion_jobs", "hub_ingestion_jobs_chatbot_id_fkey"),
)

#: (índice, tabla). Los que el modelo declara con `index=True` sobre `chatbot_id`.
INDICES_QUE_FALTAN = (
    ("ix_hub_document_chunks_chatbot_id", "hub_document_chunks"),
    ("ix_hub_interactions_chatbot_id", "hub_interactions"),
    ("ix_hub_ingestion_jobs_chatbot_id", "hub_ingestion_jobs"),
)


def upgrade() -> None:
    for tabla, fk in FK_CRUZADAS:
        op.execute(f'ALTER TABLE "{tabla}" DROP CONSTRAINT IF EXISTS "{fk}"')

    for indice, tabla in INDICES_QUE_FALTAN:
        op.execute(f'CREATE INDEX IF NOT EXISTS "{indice}" ON "{tabla}" (chatbot_id)')

    op.execute('DROP INDEX IF EXISTS "ix_hub_vocabulary_terms_org_axis"')


def downgrade() -> None:
    op.execute(
        'CREATE INDEX IF NOT EXISTS "ix_hub_vocabulary_terms_org_axis" '
        'ON "hub_vocabulary_terms" (organizacion_id, axis)'
    )
    for indice, _tabla in INDICES_QUE_FALTAN:
        op.execute(f'DROP INDEX IF EXISTS "{indice}"')
    # Las FK cruzadas no se recrean: ver la docstring.

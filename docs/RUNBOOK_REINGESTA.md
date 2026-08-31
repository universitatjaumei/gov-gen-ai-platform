# Runbook — reingerir el corpus en el despliegue

> **Entregable de D.6-VM (2026-08-31).** Nace de una pregunta concreta del usuario: la curación
> del corpus corre en local y la ingesta va a correr en el cloud, y eso «se puede complicar».
> Esto es lo que hace que no se complique: los comandos exactos, en orden, con la puerta de
> comprobación delante.

## La regla que gobierna todo lo demás

**Desde el despliegue, la base de datos del cloud es la única fuente de verdad del corpus del
piloto. La local es sólo desarrollo.**

El pipeline de curación sigue produciendo los `.md` validados en local —eso no cambia—, pero
**la única ingesta que cuenta se ejecuta contra el cloud**. Ingerir en las dos «para probar» es
la forma segura de que divergan, y entonces una respuesta distinta entre local y producción no
se puede explicar sin comparar documento a documento. El bloque DER existe porque la deriva
entre copias del corpus ya está identificada como riesgo; este runbook es su prevención barata.

## Antes de tocar nada

```bash
# 1. Que la base responde y qué revisión tiene
gcloud sql instances describe govgenai-prod --project=uji-teclab --format='value(state)'

# 2. Una copia a mano ANTES de una reingesta grande. Las automáticas son de las 03:00;
#    una reingesta no es un cambio de esquema, pero mueve miles de filas.
gcloud sql backups create --instance=govgenai-prod --project=uji-teclab --async
```

## Cómo llegan los `.md` a la máquina

Mientras el servicio de publicación no exista (bloque SYNC), la fuente es una carpeta:

```bash
# Desde la máquina de quien cura, con el corpus ya validado
gcloud compute scp --recurse \
    "<corpus>/generat/ingesta/normatiu" \
    govgenai-vm:/tmp/corpus \
    --zone europe-southwest1-b --tunnel-through-iap --project uji-teclab
```

Cuando exista el servicio de publicación, esto se sustituye por `sync.py` contra
`PUBLICATION_MCP_URL` y no hay que copiar nada.

## La ingesta, siempre en dos pasos

**Primero el plan, después aplicar.** El `--dry-run` no es una precaución opcional: es la
puerta que el 2026-08-27 destapó 292 falsos cambios que tapaban 24 reales.

```bash
gcloud compute ssh govgenai-vm --zone europe-southwest1-b --tunnel-through-iap \
  --project uji-teclab --command "sudo docker compose \
    --env-file /opt/govgenai/.env.despliegue -f /opt/govgenai/docker-compose.vm.yml \
    run --rm --entrypoint python app \
    -m server.app.modules.agents_hub.ingestion.corpus.load \
    --dir /tmp/corpus --chatbot-id <UUID> --dry-run"
```

Se lee el plan —`+N ~M =K`— y **sólo entonces** se repite sin `--dry-run`.

> El vocabulario va **antes** que el corpus, o la carga aborta. Ver `docs/CARGA_VOCABULARIO.md`.

## Cómo saber que ha ido bien

Dos comprobaciones, y las dos son invariantes que este proyecto ya se ha ganado a base de
fallos:

1. **Segunda pasada a cero.** Repetir la ingesta sin cambios tiene que dar `metadatos=0` y
   ningún documento nuevo. Es el invariante de idempotencia que cerró el bloque ACT; si la
   segunda pasada mueve algo, hay un campo que se está reescribiendo solo.
2. **Cero documentos sin fragmentos.** Es la fuga que destapó ACT.8: un asistente puede recibir
   un documento y quedarse con cero fragmentos, y el informe dice `ingeridos=1` sin mentir.

```sql
-- Documentos sin fragmentos, por chatbot. Tiene que devolver 0 filas.
SELECT d.chatbot_id, count(*)
FROM hub_documents d
LEFT JOIN hub_document_chunks c ON c.document_id = d.id
WHERE c.id IS NULL
GROUP BY d.chatbot_id;
```

## Cuándo se reingiere

**A mano, cuando la curación entrega una versión nueva.** No hay planificador y es deliberado:
es la misma decisión de SYNC.1 y RAG.14 —cuándo se sincroniza es operativa, no consecuencia
técnica de que el mecanismo exista—. Este runbook documenta el **cómo**, no automatiza el
**cuándo**.

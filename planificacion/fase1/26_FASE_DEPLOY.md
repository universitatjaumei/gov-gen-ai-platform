## Fase Deploy — Paso a producción en GCP

> ## ⚠️ BLOQUE REESCRITO EL 2026-08-10 — el destino es una **VM**, no Cloud Run
>
> Decisión y razones en `docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md` §2. En resumen: el
> planificador de calidad es un APScheduler dentro del `lifespan` y el rastreo de curación se
> encola con `BackgroundTasks`; **en Cloud Run con escalado a cero el scheduler no dispara y
> un rastreo largo muere a media ejecución**. Con CPU siempre asignada se arregla, pero
> entonces se paga lo mismo que una VM con más restricciones — o sea que el descuento que
> justificaba Cloud Run no era cobrable aquí.
>
> **Forma del despliegue**: VM con `docker-compose.prod.yml` (que ya describe la aplicación,
> el sandbox aislado y el resto), **Cloud SQL** para Postgres y **GCS** para documentos. El
> estado sigue gestionado: lo que hay en la base es el corpus curado y conversaciones de
> ciudadanos, y ahí las copias y el *point-in-time recovery* se pagan solos.
>
> **Lo que cambia respecto a lo que sigue escrito abajo**, prompt a prompt:
>
> | Prompt | Estado |
> |---|---|
> | **D.0** | Vigente, con la **lista de servicios recortada** (ver nota dentro) |
> | **D.1** | ✅ **YA HECHO** — lo resolvió **SEC.8.5** con la credencial de sitio (`HubWidgetKey`), que además es mejor que la API key por chatbot que este prompt describía: se guarda con hash, es revocable y no abre nada que no sea `public_anon`. **No ejecutar**; queda como registro |
> | **D.2** | Vigente. Secret Manager sigue siendo el sitio; cambia **quién los lee** (la VM al arrancar, no el servicio de Cloud Run) |
> | **D.3** | Vigente casi sin cambios. Cloud SQL se conserva; la conexión es por Auth Proxy **desde la VM** |
> | **D.4** | **REESCRITO** — era «tres servicios en Cloud Run» (API + embedding-service + docling-service). Con embeddings por API y **Docling retirado en EXT.3**, es **una sola máquina**. Ver D.4-VM |
> | **D.5** | **REESCRITO** — CI/CD que despliega a la VM, no a Cloud Run. Ver D.5-VM |
> | **D.6** | **NUEVO** — lo que una VM sí te hace dueño: copias, arranque tras reinicio y vigilancia. Ver D.6-VM |
>
> **Deja de existir como problema**: el ejecutor de trabajos duradero que SEC.8.8 aplazó para
> el rastreo. En una VM el proceso vive y no hace falta.
>
> **Prerrequisito**: el bloque **EXT** va antes. D.4 necesita la huella medida en EXT.3 para
> dimensionar la máquina, y ese número se mide — no se estima.

> ## Decisiones del usuario (2026-08-31), al arrancar el bloque
>
> | Qué | Decidido |
> |---|---|
> | Proyecto GCP | `<PROYECTO_GCP>` (los 14 servicios ya habilitados por D.0) |
> | Región y zona | **`europe-southwest1`** (Madrid) — latencia y el dato en España |
> | Tipo de VM | **`e2-small`** (2 GB), que la medición de D.4.0 dejó holgado (345 MB de RSS) |
> | Cloud SQL | **`db-g1-small`** (1,7 GB), elegido por el agente: los ~14.500 fragmentos a 1.024 dimensiones son unos 60 MB de vectores y el índice HNSW cabe de sobra, mientras `db-f1-micro` (0,6 GB) iría al límite. Subir de nivel es un reinicio, así que empezar pequeño no cierra ninguna puerta |
> | Dominio | **Ninguno de momento** |
> | Dónde viven el buscador y las 313 normas | **Un bucket** (o cualquier alojamiento estático fuera de GCP): son HTML ya generados y no necesitan cómputo |
>
> **Consecuencia técnica que la decisión de «sin dominio» NO puede saltarse, y que cambia D.4-VM
> y D.6.1**: las páginas en un bucket se sirven por **HTTPS**, y el widget que se incrusta en
> ellas llama a la API con `data-api-url` absoluto (`frontend/src/widget/main.tsx:23`, cuyo
> defecto `/api/v1` sólo vale si la página y la API comparten origen). Una página HTTPS que
> llame a `http://IP` la bloquea el navegador por contenido mixto, y un `https://IP` **no puede
> tener certificado válido**: Let's Encrypt no emite para direcciones IP desnudas. Es decir: las
> páginas no necesitan dominio, **la API sí necesita un nombre**.
>
> Salidas, en el orden en que conviene tomarlas:
>
> 1. **Subdominio institucional** (p. ej. `assistent-normativa.uji.es`) con registro A a la IP
>    estática de la VM. Es la buena a medio plazo: estable, y la URL sobrevive al piloto.
> 2. **`sslip.io` mientras llegue ese subdominio**: `34-175-x-y.sslip.io` resuelve solo a esa IP
>    y Let's Encrypt emite con normalidad, sin trámite ninguno. El nombre sólo aparece dentro de
>    `data-api-url`; nadie lo lee. Cambiar de la 2 a la 1 es una variable de entorno y un
>    certificado.
> 3. Servir también las páginas desde la VM en HTTP plano. Funciona porque el origen coincide,
>    pero tira por la borda el bucket sin cómputo y deja el piloto sin cifrar. Descartada salvo
>    que las otras dos fallen.
>
> **Y en los dos primeros casos hace falta CORS**: el origen del bucket entra en `CORS_ORIGINS`
> (`server/app/core/cors.py`), porque página y API dejan de compartir origen. La credencial del
> widget viaja en el HTML **a propósito** — es de sitio y sólo abre chatbots `public_anon`
> (SEC.8.5).

Esta fase no añade funcionalidad nueva: convierte la pila de desarrollo (Docker Compose local) en un sistema desplegado en Google Cloud Platform. El codebase ya está diseñado para ello (ver sección "Infraestructura objetivo" en CLAUDE.md); estos prompts completan la configuración y documentan el proceso operativo.

**Requisito previo**: acceso a un proyecto GCP con **facturación activa**. Los servicios ya no se dan por habilitados a mano: los habilita **D.0**, que es un paso del despliegue y no una nota en prosa (enmienda del 2026-08-01, a petición del usuario de habilitarlo todo de una vez en el deploy).

```
Fase Deploy
  ├── D.0  Habilitación de servicios del proyecto — gcloud services enable, versionado
  ├── D.1  Autenticación pública del widget — API key por chatbot
  ├── D.2  Secrets y variables de entorno — migración a Secret Manager
  ├── D.3  Base de datos en producción — Cloud SQL + migraciones Alembic
  ├── D.4  Imágenes Docker — Artifact Registry + Cloud Run
  ├── D.5  CI/CD — pipeline GitHub Actions → Cloud Build → Cloud Run
  └── D.6  Edge node — despliegue híbrido cloud/edge en GCP
```

---

### Prompt D.0.doc (RED/GREEN) — La documentación no puede prometer lo que la VM no da

**Modelo sugerido**: **Sonnet** — alcance cerrado: ocho menciones que revisar y una corrección
con consecuencia.

```
# PROMPT D.0.doc (RED/GREEN) — Repasar lo que la documentacion supone de Cloud Run
# Deploy: n/a (documentacion)

## Por que
El destino paso a ser una **VM con Docker Compose** y no Cloud Run
(`docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md` §2). Ocho documentos de `docs/` siguen mencionando
Cloud Run, y la mayoria lo hace bien —registran el cambio o lo citan de pasada—, pero **uno
afirma una proteccion que la VM no trae**:

    docs/SANDBOX_SECURITY.md:114
    ### Capa 8 — gVisor en GCP (despliegue Cloud Run)
    Cloud Run ejecuta los contenedores sobre gVisor (runtime runsc), que intercepta las
    llamadas al sistema y las emula en espacio de usuario.

Esa capa la daba **la plataforma**, no el codigo. En una VM con Docker Compose no esta salvo
que se configure. Un documento de seguridad que cuenta una capa inexistente no es desorden
documental: es la clase de cosa que alguien lee justo antes de desplegar, y decide con ella.

## Que hacer
1. Repasar las ocho menciones (`grep -ril "cloud run" docs/`) y clasificarlas: las que
   registran historia se quedan como estan; las que razonan **sobre el destino actual** se
   corrigen.
2. `SANDBOX_SECURITY.md`, capa 8: decir la verdad. O se configura gVisor en la VM —y entonces
   se documenta como configuracion, con su comprobacion—, o la capa **no existe** y hay que
   decir cuantas quedan y si eso cambia el juicio sobre el aislamiento del sandbox.
   **Decidir, no dejarlo ambiguo**: el sandbox ejecuta codigo generado por un LLM.
3. Si alguna correccion cambia el juicio de seguridad, decirlo en el informe de cierre y no
   solo en el documento.

## Tests (RED primero)
- RED: un test de infra falla si `docs/` afirma que el despliegue corre sobre Cloud Run
  —distinto de mencionarlo como historia o como alternativa descartada—.
- RED: el numero de capas que declara `SANDBOX_SECURITY.md` coincide con las que existen.

## Criterio de done
- [ ] Las ocho menciones clasificadas, con la lista en el commit
- [ ] La capa 8 resuelta en un sentido o en el otro, no matizada
- [ ] Guardarrail que impide volver a prometer una capa que no esta
```

### Prompt D.0 — Habilitación de servicios del proyecto GCP

**Modelo sugerido**: **Sonnet** — script idempotente y lista versionada; sin decisiones abiertas.

> **Ajuste 2026-08-10 (VM).** La lista de abajo se recorta y se amplía:
> - **Fuera**: `run.googleapis.com` y `artifactregistry.googleapis.com` si la imagen se
>   construye en la propia VM. Si el CI la publica (D.5), Artifact Registry **se queda**.
> - **Dentro**: `compute.googleapis.com` (la VM) y `oslogin.googleapis.com` (acceso por SSH
>   gobernado por IAM en vez de claves sueltas en metadatos).
> - **Se quedan** `sqladmin`, `secretmanager`, `storage`, y los de modelo —`aiplatform`,
>   `generativelanguage`— más `discoveryengine` para el Ranking API de RAG.6b.
> - **Ya no hace falta** ningún servicio para embeddings locales ni para Docling: EXT.3 lo
>   retira y MOD.2 deja los embeddings por API.

> **Añadido el 2026-08-01**, a petición del usuario: habilitar todos los servicios de una vez
> durante el despliegue en vez de irlos encendiendo a mano según hagan falta. Hasta ahora esto
> era una frase de «requisito previo» en prosa, con una lista **incompleta** —no incluía Vertex
> AI ni Discovery Engine— y nadie la ejecutaba: los cinco prompts de deploy daban por hecho que
> las APIs ya estaban encendidas.

```
# PROMPT D.0 — Los servicios se habilitan con un script, no con clics
# Deploy: cloud

## Script (scripts/gcp_enable_services.sh)
- `gcloud services enable` con la lista COMPLETA, idempotente (volver a ejecutarlo no rompe) y
  con el proyecto como parametro, no cableado.
- Lista minima a partir de lo que el sistema usa hoy; verificar contra el codigo antes de
  darla por buena, porque una API que falta se manifiesta como un 403 en produccion:
    run.googleapis.com                  Cloud Run (la aplicacion)
    sqladmin.googleapis.com             Cloud SQL (Postgres + pgvector)
    secretmanager.googleapis.com        secretos (D.2)
    artifactregistry.googleapis.com     imagenes (D.4)
    cloudbuild.googleapis.com           build (D.5)
    storage.googleapis.com              GCS via StorageService
    aiplatform.googleapis.com           Vertex AI
    generativelanguage.googleapis.com   Gemini API con API key (embeddings de MOD.2)
    discoveryengine.googleapis.com      Ranking API del reranker (RAG.6b)
- Documentar QUE prompt necesita cada servicio, para que quien lo lea sepa que se rompe si
  quita uno.

## Comprobacion, no solo habilitacion
- El script termina LISTANDO los servicios habilitados y marcando los que faltan. Habilitar y
  no comprobar deja el mismo agujero que habia: creer que estan.
- Anotar la cuota por defecto de discoveryengine, que puede ser baja.

## Tests
# should_list_every_service_the_codebase_needs   (la lista del script cubre lo que se usa)
# should_be_idempotent                            (segunda ejecucion, exit 0)
```

---

### Prompt D.1 ✅ — Autenticación pública del widget: API key por chatbot

> **HECHO EL 2026-08-10 POR SEC.8.5. No ejecutar este prompt.**
>
> El agujero que lo motivaba era peor de lo que este prompt suponía: el widget no es que
> careciera de credencial propia, es que embebía un **JWT de sesión o un PAT completo** en el
> HTML de la página (`data-token`), con el rol y las organizaciones de su dueño detrás.
>
> Lo resuelto en SEC.8.5 es un superconjunto de lo que aquí se pedía: `HubWidgetKey` es por
> chatbot, se guarda con **hash SHA-256**, se compara en tiempo constante, es **revocable**, y
> —por `assert_chatbot_access` con `via=VIA_WIDGET`, que SEC.2.1 ya había dejado escrito sin
> llamante— **solo abre chatbots `public_anon`**. La cabecera es `X-Widget-Key`. Alta, listado
> y revocación en `/hub/chatbots/{id}/widget-keys`.
>
> Lo único que este prompt aportaba y no está: la **documentación de incrustación** para quien
> publique el widget en una web (el `<script>` y el `data-widget-key`). Va a D.6-VM, con el
> resto de lo operativo.

**Modelo sugerido**: **Sonnet** — auth con X-Api-Key header; decisiones de diseño documentadas en el prompt.

**Objetivo**: el widget embebido en webs externas (UJI, ayuntamientos) no puede requerir login de usuario. Sustituir el mecanismo `data-token` JWT (solo válido para pruebas locales) por una **API key pública por chatbot** que identifica el bot sin exponer credenciales de usuario.

**Contexto y decisiones de diseño**:

- El widget se incrusta con un simple `<script>` en cualquier web. El usuario final es un ciudadano o alumno sin cuenta en la plataforma.
- La autenticación no es de usuario sino de **despliegue**: "este widget está autorizado a hablar con el chatbot X".
- La API key se genera al publicar un chatbot (campo `public_api_key` en `HubChatbot`), se muestra una sola vez en el panel admin y se puede revocar.
- El endpoint de chat del widget **no usa JWT**; usa `X-Api-Key` header. El endpoint del panel admin sigue usando JWT.

**Cambios en el modelo**:

```python
# HubChatbot — añadir campo
public_api_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
```

Migración Alembic: `alter table hub_chatbot add column public_api_key varchar(64) unique`.

**Nuevo endpoint público**:

```
POST /api/v1/widget/chat/{chatbot_id}
  Header: X-Api-Key: <public_api_key>
  Body: { "message": "...", "lang": "ca" }
  → StreamingResponse SSE (mismo protocolo que hub_chat)

Deploy: edge
```

El handler valida que `public_api_key` coincide con el `chatbot_id` en la tabla. No crea `HubInteraction` con `user_id` (usuario anónimo); genera un UUID de sesión efímero.

**Ampliación 2026-07-27 — la API key no basta: hay que comprobar el modo de acceso.**

Tal como estaba escrito este prompt, generar una `public_api_key` bastaría para exponer **cualquier** chatbot, incluido uno de gestión interna. Con SEC.2.1 en el plan, el handler del widget debe pasar por las tres guardas compartidas, en este orden y sin reimplementar ninguna:

```
1. assert_chatbot_access(actor=None, chatbot, via='widget_api_key')   # SEC.2.1
     -> 403 ACCESS_MODE_FORBIDDEN si access_mode != 'public_anon',
        aunque la API key sea válida y corresponda al chatbot.
2. assert_chatbot_available(session, chatbot, now)                    # SEC.4.1
     -> 403 CHATBOT_UNAVAILABLE (caducado / fuera de ventana / presupuesto agotado),
        con el unavailable_message del admin.
3. assert_within_quota(session, actor=None, chatbot, via='widget_api_key')  # SEC.4
     -> 429 con la cuota anon_ip_daily_token_quota, sujeto = IP.
```

La contabilidad de tokens (SEC.4) también aplica al camino anónimo: el `HubUsageCounter` se
actualiza con `subject_type='ip'` y con `subject_type='chatbot'`, y el `HubInteraction`
anónimo guarda `prompt_tokens`/`completion_tokens` igual que el autenticado.

**Dependencias nuevas**: D.1 pasa a requerir **SEC.2.1**, **SEC.4** y **SEC.4.1** cerrados.

**Tests añadidos**:
```python
# should_403_widget_when_chatbot_is_authenticated_mode   (API key válida, modo incorrecto)
# should_403_widget_when_chatbot_expired
# should_429_widget_when_ip_daily_quota_exceeded
# should_record_anonymous_usage_under_ip_subject
```

**Cambios en el widget**:

- `main.tsx`: leer `data-api-key` en lugar de `data-token`
- `useChat.ts`: enviar `X-Api-Key` header en lugar de `Authorization: Bearer`
- `widget.html` de producción: solo necesita `data-chatbot-id` y `data-api-key`

```html
<div id="govgenai-widget"
     data-chatbot-id="<uuid>"
     data-api-key="<public_api_key>"
     data-lang="ca"
     data-api-url="https://api.govgenai.com/api/v1">
</div>
```

**UI admin** (panel de publicación del chatbot):
- Botón "Publicar widget" → genera `public_api_key` aleatoria (32 bytes hex), la guarda hasheada en BD, la muestra en claro UNA sola vez.
- Botón "Revocar" → pone `public_api_key = null`.
- Snippet HTML copiable con el `data-api-key` ya relleno.

**Tests requeridos**:
```python
# unit
# should_reject_request_with_invalid_api_key → 401
# should_reject_request_with_api_key_for_wrong_chatbot → 401
# should_accept_request_with_valid_api_key → 200 SSE
# should_not_require_jwt_on_widget_endpoint
# should_create_anonymous_interaction_without_user_id

# integration
# should_generate_api_key_via_admin_endpoint
# should_revoke_api_key_and_reject_subsequent_widget_requests
```

**CORS**: el endpoint `/api/v1/widget/*` debe permitir cualquier origen (`*`) ya que se llama desde webs externas. El endpoint `/api/v1/hub/*` (admin) solo permite el origen del panel admin.

---

### Prompt D.2 — Secrets y variables de entorno: migración a Secret Manager

**Modelo sugerido**: **Sonnet** — migración de .env a GCP Secret Manager. Comandos gcloud + wiring en Cloud Run.

**Objetivo**: eliminar el fichero `server/.env` en producción. Todas las credenciales y configuración sensible viven en **GCP Secret Manager**; el contenedor las recibe como variables de entorno inyectadas por Cloud Run.

**Inventario de secrets** (lo que hay en `server/.env` y su destino en GCP):

| Variable local | Secret Manager name | Quién lo consume |
|---|---|---|
| `JWT_SECRET_KEY` | `govgenai-jwt-secret` | API principal |
| `DATABASE_URL` | `govgenai-db-url-async` | API principal |
| `DATABASE_URL_SYNC` | `govgenai-db-url-sync` | Alembic (Cloud Build step) |
| `LANGFUSE_PUBLIC_KEY` | `govgenai-langfuse-pub` | API principal |
| `LANGFUSE_SECRET_KEY` | `govgenai-langfuse-sec` | API principal |
| `STORAGE_BUCKET` | variable de entorno pública (no secret) | API principal |

**Variables de entorno no-secretas** (se definen directamente en la configuración de Cloud Run, no en Secret Manager):

```
ENVIRONMENT=production
STORAGE_BACKEND=gcs
STORAGE_BUCKET=<BUCKET_DOCS>
DEPLOY_MODE=all   # o edge / cloud según el nodo
```

**Configuración de Cloud Run** (extracto `cloudbuild.yaml` o CLI):

```yaml
- name: 'gcr.io/cloud-builders/gcloud'
  args:
    - run
    - deploy
    - govgenai-api
    - --set-secrets=JWT_SECRET_KEY=govgenai-jwt-secret:latest
    - --set-secrets=DATABASE_URL=govgenai-db-url-async:latest
    - --set-secrets=LANGFUSE_PUBLIC_KEY=govgenai-langfuse-pub:latest
    - --set-secrets=LANGFUSE_SECRET_KEY=govgenai-langfuse-sec:latest
    - --set-env-vars=ENVIRONMENT=production,STORAGE_BACKEND=gcs,STORAGE_BUCKET=<BUCKET_DOCS>
```

**Checklist de seguridad**:
- [ ] `server/.env` añadido a `.gitignore` (ya debe estarlo)
- [ ] `JWT_SECRET_KEY` en producción: mínimo 64 bytes aleatorios (`openssl rand -hex 64`)
- [ ] `JWT_EXPIRATION_MINUTES` en producción: volver a 60 (el valor `10080` es solo para desarrollo local)
- [ ] La cuenta de servicio de Cloud Run tiene rol `roles/secretmanager.secretAccessor` solo para los secrets que necesita

**Tests requeridos**:
```python
# should_read_jwt_secret_from_environment_variable
# should_fail_fast_if_jwt_secret_not_set
# should_read_database_url_from_environment_variable
```
(La mayoría ya existen; este prompt verifica que no hay credenciales hardcodeadas en código.)

---

### Prompt D.3 — Base de datos en producción: Cloud SQL + migraciones Alembic

**Modelo sugerido**: **Sonnet** — provisioning Cloud SQL + estrategia de migración Alembic. Comandos documentados.

**Objetivo**: documentar y automatizar el proceso de aprovisionamiento de Cloud SQL y la ejecución de migraciones Alembic como paso pre-deploy, garantizando que la BD nunca queda en un estado intermedio si el despliegue falla.

**Configuración de Cloud SQL**:

```bash
# Crear instancia (una sola vez)
gcloud sql instances create <INSTANCIA_SQL> \
  --database-version=POSTGRES_16 \
  --tier=db-g1-small \
  --region=europe-southwest1 \
  --enable-google-private-path

# Crear BD y usuario
gcloud sql databases create govgenai --instance=<INSTANCIA_SQL>
gcloud sql users create govgenai --instance=<INSTANCIA_SQL> --password=<secret>

# Habilitar extensión pgvector (ejecutar en psql conectado vía Cloud SQL Auth Proxy)
CREATE EXTENSION IF NOT EXISTS vector;
```

**Cloud SQL Auth Proxy en Cloud Run**: Cloud Run conecta a Cloud SQL vía socket Unix automáticamente si se especifica `--add-cloudsql-instances`. La `DATABASE_URL` usa el formato:

```
postgresql+asyncpg:///govgenai?host=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME
```

**Estrategia de migraciones** (sin downtime):

1. Las migraciones se ejecutan como un **Cloud Build step** ANTES del despliegue del nuevo contenedor.
2. Solo se permiten migraciones `ADD COLUMN ... DEFAULT NULL` o `CREATE TABLE` en el step automático.
3. Migraciones con `ALTER COLUMN NOT NULL` o `DROP` requieren aprobación manual y ventana de mantenimiento.
4. El comando:

```yaml
# En cloudbuild.yaml, antes del step de deploy
- name: 'gcr.io/$PROJECT_ID/govgenai-api:$COMMIT_SHA'
  entrypoint: 'uv'
  args: ['run', 'alembic', 'upgrade', 'head']
  env:
    - 'DATABASE_URL_SYNC=$$DATABASE_URL_SYNC'
  secretEnv: ['DATABASE_URL_SYNC']
```

**Backup antes de migrar**:

```bash
gcloud sql backups create --instance=<INSTANCIA_SQL> --async
```

**Tests requeridos**:
```python
# should_run_all_migrations_without_error_on_clean_database
# should_be_idempotent_running_migrations_twice
# should_not_lose_data_on_add_column_migration
```

---

### Prompt D.4.0 (RED/GREEN) — Los modelos locales pasan a ser un extra de instalación

**Modelo sugerido**: **Sonnet** — cambio de empaquetado con criterio cerrado; la parte fina
(importación perezosa y mensaje de error) está especificada abajo.

**Objetivo**: `torch`, `transformers` y `sentence-transformers` son dependencias obligatorias
y están ahí por `LocalEmbeddingService` (BGE-M3) y `LocalReranker`. Con embeddings de Vertex y
el reranker apagado —el plan de despliegue— **no se usan en ejecución, pero se pagan enteros**
en memoria y arranque.

Medido en EXT.3: `sentence-transformers` 216 MB, `torch` 172 MB, y entre los tres se llevan
prácticamente todo el tiempo de import; `pdfplumber`, que es lo que sí se usa, cuesta 5 MB.
La aplicación en reposo son 627 MB, y la mayor parte es esa pila.

**Va antes de D.4-VM** porque cambia el tamaño de la máquina a la mitad, y ese es el número
que D.4 tiene que fijar.

```
# PROMPT D.4.0 (RED/GREEN) — Instalar los modelos locales solo cuando se van a usar
# Deploy: shared (empaquetado)

## Lo que NO cambia, y es la condición del prompt
- **El modo edge sigue pudiendo usar modelos locales.** Esto no retira una capacidad: la
  hace opcional. `LocalEmbeddingService` y `LocalReranker` se conservan íntegros, y un
  despliegue edge los instala con el extra.
- La cascada de selección (`resolve_embedding_service`, `resolve_reranker`) no cambia: se
  sigue eligiendo por fila de configuración, no por lo que haya instalado.

## Cambios
- `server/pyproject.toml`: mover `torch`, `torchvision`, `transformers` y
  `sentence-transformers` de las dependencias base a un extra `[project.optional-dependencies]`
  llamado `local-models`. Regenerar el lock.
- Importación **perezosa** en `LocalEmbeddingService` y `LocalReranker`: el import va dentro
  del método que lo necesita, no en la cabecera del módulo. Hoy `reranker.py` ya lo hace
  ("import perezoso"); replicar el patrón en el servicio de embeddings.
- **El fallo tiene que explicarse.** Si se resuelve un proveedor `local` sin el extra
  instalado, el error debe decir QUÉ falta y CÓMO instalarlo (`uv sync --extra local-models`),
  no un `ModuleNotFoundError: torch` a secas. Es el mismo criterio que
  `EmbeddingProviderNotSupported`, que ya falla con un mensaje que se entiende.
- Documentar el extra en el README de despliegue y en `.env.example`, junto a la elección de
  proveedor de embeddings.

## Tests (RED primero)
# should_not_import_torch_at_module_import_time      (importar la app no carga torch)
# should_explain_how_to_install_the_extra_when_local_embedding_is_selected
# should_explain_how_to_install_the_extra_when_local_reranker_is_selected
# should_still_resolve_google_embeddings_without_the_extra
# should_keep_local_services_working_when_the_extra_IS_installed   (no se retira capacidad)

## Cierre
- [ ] `python -c "import server.app.main; import sys; assert 'torch' not in sys.modules"`
- [ ] Medir de nuevo el RSS en reposo y anotarlo en
      `docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md` §Dimensionado, junto a la cifra de 627 MB
      que sustituye
- [ ] Suite completa en verde CON el extra instalado (es como corre CI hoy)
```

---

### Prompt D.4-VM (REESCRITO) — La máquina: aprovisionamiento, Compose y TLS

**Modelo sugerido**: **Sonnet** — infraestructura con pasos conocidos; la única decisión
abierta (el tamaño) la cierra la medición de EXT.3.

**Objetivo**: una VM que sirva la aplicación de forma estable, con el estado fuera de ella.
Sustituye al despliegue de tres servicios en Cloud Run: con embeddings por API y Docling
retirado en EXT.3, no hay nada que escalar por separado.

**Dependencias**: EXT.3 (la huella medida), D.2 (secretos), D.3 (Cloud SQL).

```
# PROMPT D.4-VM — Una máquina, el estado fuera
# Deploy: cloud (infraestructura)

## Tamaño — MEDIDO (EXT.3 y D.4.0, 2026-08-11)
- **Sin el extra `local-models`, que es este despliegue: 345 MB y 9,4 s de arranque**, con la
  pila de modelos sin cargar. Eran 627 MB antes de D.4.0.
- Pico extrayendo un PDF de 40 páginas (medido antes de D.4.0): **968 MB**. Conviene volver a
  medirlo, porque parte de ese pico venía de la pila que ya no está.
- Con el extra instalado (edge con modelos locales): 559 MB.
- **`e2-small` (2 GB) es holgado** para el despliegue estándar. `e2-medium` solo si se
  instala el extra.
- **La memoria es trasladable; los TIEMPOS no del todo** —Windows, caché de disco y
  antivirus—. Volver a medir el arranque en la propia máquina.
- **Docling ya no manda: manda `torch`.** Medido por librería, `pdfplumber` cuesta 0,09 s y
  5 MB, mientras que `transformers` (142 s), `sentence-transformers` (75 s / 216 MB) y
  `torch` (52 s / 172 MB) se llevan el arranque entero. Están por `LocalEmbeddingService`
  (BGE-M3) y `LocalReranker`, no por la extracción.
- **D.4.0 lo resuelve y hay que ejecutarlo ANTES**: mueve esa pila a un extra
  `[local-models]`. Con ella, la aplicación pide ~2 GB; sin ella, se espera ~150-250 MB. El
  tamaño se fija con la cifra que D.4.0 vuelva a medir, no con la de 627 MB.
- Si el despliegue usa embeddings de Vertex y el reranker apagado —el plan—, la VM **no
  instala el extra**. Un edge con modelos locales sí, y entonces vuelve a hacer falta el
  presupuesto grande.
- El disco no guarda nada que duela perder (ver abajo), así que el margen se pone en memoria.
- Disco: solo sistema, imágenes y logs. Los documentos van a GCS y la base a Cloud SQL, así
  que el disco de la VM no guarda nada que duela perder — y eso es deliberado.

## Aprovisionamiento (script idempotente, versionado; nada de clics)
- VM en europe-southwest1 (misma región que Cloud SQL: la latencia de cada consulta del
  retriever la paga el usuario esperando).
- SIN IP pública para la base: Cloud SQL Auth Proxy como servicio en la VM.
- Cuenta de servicio propia con lo mínimo: cliente de Cloud SQL, lectura de los secretos que
  necesita y acceso al bucket. No la cuenta por defecto de Compute, que viene con más de lo
  que hace falta.
- Cortafuegos: 80/443 abiertos; SSH por IAP u OS Login, nunca 22 abierto al mundo.

## Servicio
- `docker compose -f docker-compose.prod.yml up -d` gobernado por una unidad **systemd** con
  `Restart=always`, para que un reinicio de la máquina levante el sistema solo. Sin esto, la
  VM tiene una avería que Cloud Run no tenía.
- Proxy inverso (Caddy o nginx) con TLS y renovación automática. Caddy si se quiere el
  certificado sin ceremonia.
- ENVIRONMENT=production. Recordar que a partir de SEC.8.3/SEC.8.4 el arranque FALLA —a
  propósito— si SANDBOX_MODE=local o si JWT_SECRET_KEY es el de ejemplo o mide menos de 32
  caracteres. Es la comprobación funcionando, no un problema del despliegue.
- TRUSTED_PROXY_HOPS=1 (SEC.8.4): hay un proxy inverso delante, así que la IP con la que se
  limita el login se cuenta un salto desde la derecha. Con 0 se ignoraría la cabecera y todo
  el tráfico compartiría cubo.

## Verificación de cierre
- [ ] `curl https://<dominio>/health` responde por TLS válido
- [ ] `/docs` NO responde (SEC.7 lo apaga en producción)
- [ ] Reiniciar la VM y comprobar que el sistema vuelve solo
- [ ] El scheduler de calidad dispara (es la razón de elegir VM: verificarlo, no suponerlo)
- [ ] Un rastreo de sitio termina y deja páginas — lo que moría en Cloud Run
```

---

### Prompt D.4-CR (SUPERSEDIDO) — Imágenes Docker: Artifact Registry y Cloud Run

> **No ejecutar.** Reemplazado por D.4-VM. Se conserva porque su `Dockerfile` multi-stage y la
> configuración de Artifact Registry siguen sirviendo si el CI construye la imagen (D.5-VM);
> lo que ya no aplica es el despliegue a Cloud Run y los tres servicios —`embedding-service`
> y `docling-service` no existen: los embeddings van por API desde MOD.2 y Docling se retira
> en EXT.3—.

**Modelo sugerido**: **Sonnet** — Dockerfiles multi-stage + Artifact Registry + Cloud Run config (3 servicios).

**Objetivo**: construir imágenes Docker de producción (API principal, embedding-service, docling-service), publicarlas en Artifact Registry y desplegarlas en Cloud Run con la configuración de recursos adecuada.

**Repositorio en Artifact Registry**:

```bash
gcloud artifacts repositories create govgenai \
  --repository-format=docker \
  --location=europe-southwest1

# Configurar Docker para autenticar
gcloud auth configure-docker europe-southwest1-docker.pkg.dev
```

**`Dockerfile` de producción para la API** (ubicación: raíz del proyecto):

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY server/ server/
COPY pyproject.toml uv.lock ./

RUN pip install uv && uv sync --frozen --no-dev

ENV PYTHONPATH=/app
CMD ["uv", "run", "uvicorn", "server.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Configuración de Cloud Run por servicio**:

| Servicio | CPU | RAM | Min instances | Max instances | Notas |
|---|---|---|---|---|---|
| `govgenai-api` | 2 | 1 GB | 1 | 10 | Chat + admin |
| `embedding-service` | 4 | 4 GB | 1 | 3 | BGE-M3 cargado permanentemente |
| `docling-service` | 2 | 2 GB | 0 | 5 | Escala a 0 entre ingestas |

**Deploy**:

```bash
# Build y push
docker build -t europe-southwest1-docker.pkg.dev/PROJECT/govgenai/api:SHA .
docker push europe-southwest1-docker.pkg.dev/PROJECT/govgenai/api:SHA

# Deploy Cloud Run
gcloud run deploy govgenai-api \
  --image=europe-southwest1-docker.pkg.dev/PROJECT/govgenai/api:SHA \
  --region=europe-southwest1 \
  --min-instances=1 \
  --max-instances=10 \
  --memory=1Gi \
  --cpu=2 \
  --add-cloudsql-instances=PROJECT:europe-southwest1:<INSTANCIA_SQL> \
  --no-allow-unauthenticated  # el API no es público; el widget usa API key
```

**Frontend (widget + panel admin)**:

El frontend React se construye con `npm run build` y se sirve desde **Cloud Storage + Cloud CDN** (sitio estático), no desde Cloud Run:

```bash
npm run build
gsutil -m rsync -r dist/ gs://govgenai-static/
gcloud compute backend-buckets update govgenai-cdn --enable-cdn
```

El `widget.iife.js` se publica en `https://cdn.govgenai.com/widget/widget.iife.js` — los partners lo referencian con una URL versionada para evitar breaking changes.

**Checklist pre-deploy**:
- [ ] `npm run build` y `npm run build:widget` sin errores
- [ ] `docker build` sin errores en modo producción
- [ ] `uv run pytest tests/ -v` con todas las suites verdes
- [ ] Migración Alembic ejecutada y verificada en staging antes de prod

---

### Prompt D.5-VM (REESCRITO) — CI/CD: GitHub Actions → la VM

**Modelo sugerido**: **Sonnet** — workflow con pasos conocidos; la decisión de autenticación
(Workload Identity) está cerrada en el prompt.

```
# PROMPT D.5-VM — Desplegar sin claves de larga vida ni migraciones a ciegas
# Deploy: cloud (CI)

## Autenticación
- **Workload Identity Federation**, no una clave de cuenta de servicio en los secretos de
  GitHub: una clave JSON en un repositorio es una credencial permanente que nadie rota.

## Flujo
- Construir la imagen en CI y publicarla en Artifact Registry con el SHA del commit como
  etiqueta. `latest` no sirve para saber qué está corriendo ni para volver atrás.
- Desplegar por SSH (IAP): `docker compose pull` + `up -d` con la etiqueta nueva.
- **Migraciones antes de cambiar la imagen**, en un paso propio y visible. Alembic aplicado
  desde el contenedor nuevo contra Cloud SQL, con la salida en el log del workflow: una
  migración que falla dentro del arranque deja el sistema a medias sin decir por qué.
- Comprobación posterior: `/health` y una consulta real al retriever. Si falla, revertir a la
  etiqueta anterior.

## Lo que NO se hace
- Desplegar solo con `git pull` en la VM: eso hace que lo que corre dependa del estado del
  disco de la máquina y no de un artefacto identificable.
- Ejecutar la suite en el despliegue. Corre en CI antes; repetirla aquí alarga el despliegue
  sin añadir información.

## Cierre
- [ ] Un push a main despliega y la versión servida es la del commit
- [ ] Un despliegue con migración deja constancia de qué revisión se aplicó
- [ ] Existe y está probado el camino de vuelta a la etiqueta anterior
```

---

### Prompt D.6-VM (NUEVO) — De lo que una VM te hace dueño: copias, vigilancia y publicación

**Modelo sugerido**: **Sonnet** — operativa con decisiones cerradas.

**Objetivo**: Cloud Run traía gratis el reinicio, el registro y la salud. En una VM eso hay
que ponerlo, y es la contrapartida honesta de la decisión. Recoge además la documentación de
incrustación del widget que D.1 dejó pendiente.

```
# PROMPT D.6-VM — Que sobrevivir a un incidente no dependa de acordarse
# Deploy: cloud (operación)

## Copias
- Cloud SQL: copias automáticas + point-in-time recovery. **Y una restauración de prueba**:
  una copia que nadie ha restaurado nunca es una hipótesis, no una copia.
- GCS: versionado en el bucket de documentos.
- La VM NO se respalda a propósito: no guarda nada que no se pueda reconstruir con el script
  de aprovisionamiento y la imagen. Si algo de la VM hiciera falta respaldar, es que se ha
  colado estado donde no debía.

## Vigilancia
- Uptime check contra /health con aviso.
- Alertas de memoria y disco: el disco lleno por logs es la avería más aburrida y más común
  de una VM.
- Logs de los contenedores a Cloud Logging con rotación local.

## Publicación del widget (lo que quedó de D.1)
- Documentar la incrustación: `<script>` + `data-chatbot-id` + `data-widget-key`, con el
  aviso de que la credencial es de SITIO: aparece en el HTML de quien la publique, y por eso
  no abre nada que no sea un chatbot `public_anon`.
- Documentar la revocación y la rotación.

## Runbook de reingesta del corpus (añadido 2026-08-31: curación en local, ingesta en el cloud)
- docs/RUNBOOK_REINGESTA.md con los comandos EXACTOS en la VM, no una descripción:
  - Cómo llegan los .md validados a la VM mientras no exista el servicio de publicación
    (scp/rsync de la carpeta curada) y el comando de `load.py` dentro del contenedor;
    y la variante `sync.py` contra PUBLICATION_MCP_URL para cuando D.6.1 lo despliegue.
  - Siempre en dos pasos: `--dry-run` primero (leer el plan `+N ~M =K` ANTES de aplicar,
    que es la puerta que destapó los 292 falsos cambios del 27-08), aplicar después.
  - Verificación de cierre de cada pasada: segunda pasada a cero (`metadatos=0` en los
    cuatro asistentes, el invariante que dejó el bloque ACT) y cero documentos sin
    fragmentos (la fuga que destapó ACT.8).
- La regla de fuente única, escrita donde se opera: desde el despliegue, la BD del cloud
  es la única fuente de verdad del corpus del piloto; la local es solo desarrollo. La
  única ingesta que cuenta se ejecuta contra el cloud. (El bloque DER existe porque la
  deriva entre copias ya es un riesgo identificado; este runbook es su prevención barata.)
- Cuándo se sincroniza sigue siendo decisión operativa manual, sin scheduler — la misma
  decisión de SYNC.1 y RAG.14; el runbook documenta el CÓMO, no automatiza el CUÁNDO.

## Cierre
- [ ] Restauración de la base probada de verdad, con el tiempo que costó anotado
- [ ] El aviso de caída llega a alguien (probarlo apagando el servicio)
- [ ] La guía de incrustación permite a alguien de fuera publicar el widget sin preguntar
- [ ] Una reingesta real ejecutada en la VM siguiendo el runbook tal cual está escrito,
      con el plan del dry-run y el `metadatos=0` final pegados en el propio documento
```

---

### Prompt D.6.1 (NUEVO) — El buscador y las normas publicadas, servidos desde el mismo sitio

**Modelo sugerido**: **Sonnet** — despliegue de estáticos y una variable de entorno; las
decisiones están cerradas.

**Objetivo**: hoy `CORPUS_SITE_BASE_URL` apunta a `http://127.0.0.1:4174`, así que **las citas
del asistente sólo funcionan en la máquina de quien lo desarrolla**. Medido el 2026-08-24
sobre el lote ujirag: 16 de 25 respuestas llevaban enlaces a localhost. Es bloqueante para
cualquier prueba con personas reales, y el asistente sin cita verificable no es el producto.

Lo que falta no es sólo cambiar la variable: hay que **publicar a dónde apunta**. El buscador
(`cercador.html`) y los HTML por norma —los que producen las anclas `#art-N` que el contrato
de citas exige— viven hoy en la carpeta de curación de un portátil.

**Decisión del usuario (2026-08-24)**: el buscador y los HTML de las normas se sirven desde la
**misma VM** del despliegue, y los enlaces apuntan al **bucket** donde estén las normas. En el
buscador y/o en los HTML se **incrusta el widget** de los chatbots, para que distintas personas
los prueben sobre la norma que están leyendo.

```
# PROMPT D.6.1 — Publicar el corpus navegable y llevar el widget hasta él
# Deploy: cloud

## Publicación de los estáticos
- El paquete publicable es el que ya produce la curación: `cercador.html`, `html/<slug>.html`
  y los PDF. NO se regenera aquí ni se cambia su formato: este prompt lo publica, no lo
  produce. La frontera sigue siendo `docs/CONTRATO_MD_CORPUS.md`.
- Suben a un bucket de GCS con versionado (el mismo criterio de D.6-VM para documentos).
- Se sirven por HTTPS bajo un dominio estable. La URL de una norma NO puede cambiar entre
  publicaciones: es la que el asistente cita y la que la gente guarda.
- Subida idempotente y con `Cache-Control` explícito: un HTML de norma cambia cuando cambia
  la norma, no cada día.

## La variable deja de ser un apaño local
- `CORPUS_SITE_BASE_URL` pasa a la URL pública en el despliegue, y se documenta junto a las
  demás variables de entorno.
- Comprobación de humo tras desplegar: pedir al asistente una consulta cuya respuesta cite un
  artículo y **abrir el enlace**. El ancla tiene que llevar al artículo, no a la portada.

## El widget, dentro del corpus navegable
- Incrustar el widget en `cercador.html` y en la plantilla de `html/<slug>.html`, con
  `data-chatbot-id` y `data-widget-key` — la credencial de SITIO de SEC.8.5, que sólo abre
  chatbots `public_anon`.
- **La dirección de la API se lee de UN sitio, no se incrusta 316 veces.** Las páginas
  referencian un único fichero del bucket (el guion de arranque del widget, o un
  `widget-config.json` que él lea) y de ahí sale `data-api-url`. Es lo que hace que cambiar
  `sslip.io` por el subdominio institucional cueste editar un fichero en vez de republicar
  las 313 normas: el nombre de la API es infraestructura, y la infraestructura no se copia
  en cada página. La URL de cada norma sí es identidad pública y esa no cambia nunca
  (es la que cita el asistente).
- Poder incrustar **más de un chatbot** para comparar: es el escenario de prueba que pidió el
  usuario, gente distinta probando sobre la misma norma.
- El widget NO puede romper la página si el servidor no responde: la lectura de la norma es
  el servicio principal y el asistente es un añadido.

## Tests
# should_publish_every_html_the_manifest_declares   (nada se queda sin subir)
# should_keep_canonical_urls_stable_between_publications
# should_read_corpus_site_base_url_from_the_environment  (sin valor por defecto de localhost)
# should_embed_the_widget_without_blocking_page_render

## Cierre
- [ ] Una cita del asistente abre el artículo correcto en el sitio público
- [ ] `CORPUS_SITE_BASE_URL` no contiene `127.0.0.1` en ningún entorno desplegado
- [ ] El widget responde desde una norma abierta en el buscador
- [ ] Documentado cómo se republica el corpus cuando la curación entrega una versión nueva
```

---

### Prompt D.7 (NUEVO) — Qué datos pasan al piloto, y por qué casi ninguno

**Modelo sugerido**: **Opus** — la decisión está tomada (ver abajo), pero el exportador toca
tres módulos y la guarda que impide llevarse datos de otra organización es de las que, si se
escriben mal, no fallan: dejan pasar.

**Objetivo**: hoy **no hay ningún mecanismo de selección**. `bootstrap.py` es el único camino de
instalación nueva y crea lo mínimo (superadmin, organización de ejemplo, chatbot de ejemplo,
prompts de bienvenida). No hay exportador, ni marca de «demo», ni lista de qué se lleva. Así que
la pregunta «¿qué pasa al piloto?» sólo tiene hoy dos respuestas posibles, y las dos son malas:
un volcado completo —que arrastra 29 informes de prueba y toda la basura de test— o empezar de
cero, tirando el corpus de 548 documentos y 288 hallazgos de curación ya revisados.

**Lo que este prompt separa, y es el fondo del asunto**: se están confundiendo dos cosas que
viajan de forma distinta.

1. **El catálogo que acompaña al producto** — las plantillas demo. **No se copian de la BD de
   desarrollo**: se exportan a ficheros versionados en el repositorio y los siembra
   `bootstrap.py --con-demo`. Así la demo es reproducible, se revisa en un diff y es la misma en
   todos los despliegues. Es la misma regla que ya rige el vocabulario del corpus: lo que define
   el producto es dato versionado, no una fila que alguien tenía en su portátil.
2. **Los datos operativos que sí viajan** — corpus, vigencia, chatbots, curación. Eso es un
   `pg_dump` **con lista explícita de tablas y filtrado por organización**, nunca completo.

#### Decisiones ya tomadas por el usuario (2026-08-23), que este prompt NO vuelve a abrir

- **Única organización que pasa: `Universitat Jaume I`.** Las otras cuatro de desarrollo
  —`Organización Demo`, `Organizacion Camino 1`, `Organización de ejemplo`, `Organización
  MAN.2`— no. Con ellas se quedan fuera el `Chatbot Demo` y sus 7 documentos.
- **Pasan los tres asistentes de la UJI**, incluido `Gerència — assistent agèntic (proves)`
  (127 docs, `MD_AGENT_SELECTOR`), **renombrado** para quitarle el «(proves)»: es el único sitio
  donde se ejercita esa vía de recuperación.
- **Pasa el corpus entero de la UJI** (548 documentos con sus fragmentos) y **la vigencia**
  (`vigencia_validada_el`, `revisat_per`, `data_revisio_prevista`).
- **Pasa el resultado de la curación.** El único sitio que existe, `Escola de Doctorat (RAS.5)`
  —351 páginas y 288 hallazgos—, tiene **`organizacion_id` a NULO**, así que el filtro por
  organización lo dejaría fuera: hay que **asignarlo a la UJI antes del volcado**. Es contenido
  de la UJI (`www.uji.es/centres/escola-doctorat/`) y ese nulo es un descuido del alta, no una
  decisión.
- **No pasa ningún informe de prueba**: las 29 filas de `hub_workspaces` con sus bloques,
  manifiestos y eventos de auditoría se quedan.
- **No pasa ninguna persona.** `hub_users` se recrea por SSO al primer acceso, más el
  superadministrador que crea `setup.sh`. (Las 97 filas `ada-*` que había las borró REV.1.)

#### Las tres plantillas demo

| # | Plantilla | Estado |
|---|-----------|--------|
| 1 | `Informe anual de seguimiento — Doctorado (criterios 1 y 2)` | Existe, v2, spec de 7.114 B. Se exporta tal cual |
| 2 | Económica — saldo de cuentas de tesorería | **No existe.** La prepara el usuario en pruebas manuales y se exporta después |
| 3 | Ejecución presupuestaria | Ver la corrección de abajo. Su juego de datos **ya está hecho** |

> **Corrección que hay que tener presente al ejecutar esto.** Se eligió
> `Ejecucion presupuestaria trimestral` por tener el nombre más limpio, y **está vacía**: su
> `spec_json` son 2 bytes (`{}`). La que tiene el informe de verdad es
> **`GUI3 ejecucion presupuestaria`** (5.242 B): hueco `budget_data` de tipo `excel`, conversión
> de importes en formato español, columna calculada de porcentaje, orden descendente, tabla,
> gráfico `barh` y resumen de IA con revisión obligatoria. Es la que se exporta, **renombrada**
> —el prefijo `GUI3` es el nombre de un prompt de verificación, no de un producto—, y la vacía
> se borra. La tercera candidata, `VER3 Informe presupuestario` (3.436 B), se descarta.
>
> Su juego de datos ficticio ya existe y está verificado contra las transformaciones reales de
> la plantilla: `pruebas_manuales/datos/ejecucion_presupuestaria_demo.xlsx`, con su generador al
> lado. Tres columnas —`Concepto`, `Credito Inicial`, `Obligaciones Reconocidas`—, doce
> conceptos e importes **como texto en formato español con `€`**, a propósito: generarlos ya
> numéricos no ejercitaría la conversión, que es la parte que se rompe en silencio con una hoja
> real.

```
# PROMPT D.7 — Que lo que llega al piloto sea una decisión y no un descuido
# Deploy: cloud (operación) + edge (los datos que viajan son del cliente)

## RED — los tests primero

### 1. El exportador de plantillas demo
- `test_should_export_a_template_with_all_its_versions`: exporta a JSON el `spec_json` de cada
  versión, no sólo la vigente. Una plantilla sin historial no se puede revertir.
- `test_should_not_export_anything_that_is_not_on_the_demo_list`: la lista de plantillas demo es
  **explícita y vive en el repositorio**, no se deduce de `is_global` ni de la fecha.
- `test_should_refuse_to_export_a_template_with_an_empty_spec`: es exactamente el caso de
  `Ejecucion presupuestaria trimestral`. Un `{}` exportado siembra una plantilla que se abre y
  no tiene nada dentro, y el fallo aparece en el piloto y no aquí.
- `test_should_round_trip`: exportar → sembrar en una BD limpia → el `spec_json` es idéntico.

### 2. La siembra de la demo
- `test_bootstrap_con_demo_seeds_the_three_templates` y su recíproco: **sin** `--con-demo` no se
  siembra ninguna. Un piloto que no quiera las demos no debe tener que borrarlas.
- `test_bootstrap_con_demo_is_idempotent`: dos ejecuciones no duplican. Misma regla que el resto
  de `bootstrap.py`.

### 3. El volcado operativo, que es donde está el riesgo
- `test_should_dump_only_the_listed_tables`: lista explícita. Un `pg_dump` completo se lleva los
  29 informes de prueba, y el día que alguien añada una tabla nueva se la llevaría también sin
  que nadie lo decida.
- `test_should_refuse_a_dump_containing_rows_of_another_organisation`: **la guarda que importa**.
  Se comprueba sobre el volcado ya generado, no sobre la consulta que lo generó: un filtro mal
  escrito produce un `WHERE` que pasa los tests de la consulta y datos de más en el fichero.
- `test_should_carry_the_curation_site_once_it_belongs_to_the_organisation` y
  `test_should_leave_out_a_site_with_no_organisation`: las dos caras del nulo de `Escola de
  Doctorat`, para que asignarlo sea un paso consciente y no un efecto colateral.
- `test_should_not_carry_any_workspace_or_person`: por nombre de tabla, y que falle si alguien
  las añade a la lista.

## GREEN — lo que hay que escribir

- `server/app/scripts/exportar_plantillas_demo.py` → `server/app/data/plantillas_demo/*.json`,
  con la lista de las tres en el propio módulo y el porqué de cada una.
- `bootstrap.py --con-demo`, que las lee de ahí. **No** de la base de datos de nadie.
- `scripts/volcado_piloto.sh`: la lista de tablas, el filtro por organización y la verificación
  posterior sobre el fichero. Que imprima el recuento por tabla antes de escribir nada.
- El renombrado de `GUI3 ejecucion presupuestaria` y el borrado de la plantilla vacía, como
  migración de datos o como paso documentado del volcado — **no a mano en producción**.

## Cierre
- [ ] Las tres plantillas se siembran en una BD limpia y las tres **se abren y ejecutan**, la de
      presupuesto con el `.xlsx` de `pruebas_manuales/datos/`
- [ ] El volcado, restaurado en una BD limpia, deja exactamente: 1 organización, 3 chatbots,
      548 documentos, 1 sitio, 351 páginas, 288 hallazgos, **0 informes y 0 personas**
- [ ] `docs/DATOS_DEL_PILOTO.md` con la lista de tablas y el criterio, porque la próxima vez
      que alguien migre no va a leer este prompt
```

---

### Prompt D.5-CR (SUPERSEDIDO) — CI/CD: pipeline GitHub Actions → Cloud Run

> **No ejecutar.** Reemplazado por D.5-VM. Se conserva por los pasos de build y autenticación,
> que siguen valiendo; lo que cambia es el destino del despliegue.

**Modelo sugerido**: **Sonnet** — GitHub Actions workflow + secrets + deploy steps. Patrón conocido.

**Objetivo**: automatizar el ciclo completo (test → build → migrate → deploy) con GitHub Actions. Cada push a `main` despliega a producción; cada PR despliega a staging.

**Estructura del pipeline** (`.github/workflows/deploy.yml`):

```
on: push (main) / pull_request

jobs:
  test:
    - uv run pytest server/tests/ -v
    - npm test (frontend)

  build:
    needs: test
    - docker build API, embedding-service, docling-service
    - docker push a Artifact Registry con tag=$COMMIT_SHA

  migrate:
    needs: build
    - Cloud Build step: uv run alembic upgrade head (via Cloud SQL Auth Proxy)

  deploy:
    needs: migrate
    - gcloud run deploy govgenai-api --image=...:$COMMIT_SHA
    - gcloud run deploy embedding-service --image=...:$COMMIT_SHA
    - gcloud run deploy docling-service --image=...:$COMMIT_SHA
    - gsutil rsync frontend/dist/ → Cloud Storage (panel admin)
    - gsutil rsync frontend/dist/widget/ → Cloud Storage CDN (widget público)
```

**Autenticación GCP desde GitHub Actions**:

Usar **Workload Identity Federation** (no service account keys en secretos de GitHub):

```yaml
- uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: 'projects/NUMBER/locations/global/workloadIdentityPools/github/providers/github'
    service_account: 'github-deploy@PROJECT.iam.gserviceaccount.com'
```

**Entornos**:

| Branch | Entorno | Cloud Run service | BD |
|---|---|---|---|
| `main` | production | `govgenai-api` | Cloud SQL prod |
| `staging` | staging | `govgenai-api-staging` | Cloud SQL staging (misma instancia, BD distinta) |
| PR | preview | no despliega (solo tests) | — |

**Tests requeridos** (smoke tests post-deploy):

```bash
# Ejecutar tras cada deploy exitoso en CI
curl -f https://api.govgenai.com/health → 200
curl -f https://api.govgenai.com/api/v1/hub/chatbots \
     -H "Authorization: Bearer $SMOKE_TEST_TOKEN" → 200
```

---


---

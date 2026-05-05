# Instrucciones para agentes de programación

## Contexto del proyecto

Gov Gen AI Platform es el resultado de integrar **AI Agents Hub** (chatbots RAG, LangGraph) y **AutomatIA**
(automatización, scripts, RPA) en un monorepo. El plan de desarrollo completo está en `PLAN_DESARROLLO.md`.

El cliente NiceGUI (`client_app/`) está siendo migrado progresivamente al servidor FastAPI y al frontend React.
**El código NiceGUI es legacy y debe eliminarse** a medida que cada módulo quede cubierto en el nuevo sistema.

---

## Regla crítica: migración = código nuevo + borrado del legacy

Una tarea de migración **no está completa** hasta que se elimine el código original.
No dejes código muerto, imports sin usar, archivos vacíos ni comentarios `# TODO: migrate`.

### Definición de "migración completa" (checklist obligatorio)

Antes de cerrar cualquier tarea de migración, verifica y ejecuta cada punto:

- [ ] La nueva implementación tiene tests que pasan (`pytest` o equivalente)
- [ ] El endpoint o servicio nuevo está integrado y verificado end-to-end
- [ ] El archivo o módulo legacy correspondiente está **eliminado** (no comentado, no archivado)
- [ ] Los imports del legacy han sido eliminados de todos los ficheros que los referenciaban
- [ ] No quedan referencias al código eliminado en ningún fichero del proyecto (`grep -r` antes de cerrar)
- [ ] El `docker compose up` + suite de tests completa sigue pasando tras el borrado

---

## Normas generales de limpieza

**Borra, no comentes.**
Si el código ya no se usa, elimínalo. Los comentarios `# deprecated`, `# old version` o `# legacy`
son deuda técnica disfrazada. El historial de git es la fuente de verdad del pasado.

**Borra, no archives.**
El directorio `_legacy_archive/` existe por razones históricas. No añadas nada nuevo ahí.
Si hay algo en `_legacy_archive/` que ya esté migrado, bórralo también.

**Sin backwards-compatibility shims.**
No renombres variables a `_old_foo`, no re-exportes símbolos eliminados, no añadas
comentarios `# removed` donde había código. Si algo se elimina, se elimina limpiamente.

**Sin código muerto especulativo.**
No dejes funciones, clases o módulos "por si acaso se necesitan en el futuro".
Si no se usa ahora, no existe.

---

## Estructura de módulos y dónde vive cada cosa

```
server/app/modules/automation/   ← lógica de flows, ETL, PDF, scripts (migrado desde client_app)
server/app/modules/agents_hub/   ← RAG, LangGraph, chatbots, Docling
server/app/core/                 ← servicios compartidos: LLM gateway, auth, tenancy, MCP
frontend/src/automation/         ← UI de flujos y scripts (reemplaza vistas NiceGUI)
frontend/src/widget/             ← chatbot público embebible
frontend/src/agent/              ← modo agente expandido
frontend/src/admin/              ← panel admin hub + plataforma
client_app/                      ← SOLO agente de ejecución local (RPA, folder watcher)
                                    Todo lo demás aquí es legacy pendiente de migrar
```

Si estás escribiendo código nuevo en `client_app/` fuera del agente de ejecución local,
para y consulta si pertenece al servidor o al frontend.

---

## Pruebas manuales después de cada prompt

Genera pruebas manuales **únicamente cuando el prompt incluye cambios que exigen interacción humana con la interfaz de usuario** (navegador). Si el prompt es exclusivamente backend — tests, servicios, modelos, migraciones, infraestructura, endpoints de API — no generes ningún archivo `.bat` ni bloque de instrucciones.

### Qué exige pruebas manuales

Solo estas situaciones justifican un archivo `.bat` e instrucciones:

- Flujos de usuario en el frontend (navegación, formularios, visualización de datos).
- Comportamiento visual: que algo aparece, desaparece, muestra el texto correcto.
- Interacciones end-to-end que cruzan frontend + API + BD y no tienen test de integración.

### Qué NO necesita pruebas manuales

- Código exclusivamente backend: tests unitarios, tests de integración, servicios, modelos ORM, workers, migraciones de BD, endpoints de API sin UI asociada.
- Comprobaciones que ya cubren los tests automáticos.
- Infraestructura, configuración o scripts sin impacto visual.

### Archivo .bat

- **Nombre**: `pruebas_manuales_promptXX.bat` donde `XX` es el identificador del prompt (p. ej. `pruebas_manuales_prompt9_10.bat`).
- **Ubicación**: en el directorio desde el que deben ejecutarse los comandos (normalmente la raíz del proyecto o el subdirectorio correspondiente).
- **Contenido mínimo obligatorio**:
  - Línea `@echo off` al inicio y `chcp 65001 > nul` para codificación UTF-8.
  - Bloques `echo` que muestren por pantalla cada sección: requisitos previos, comandos a ejecutar, qué comprobar, cómo terminar.
  - Solo los comandos que no pueden automatizarse: `curl` de smoke check, `alembic upgrade head` si hay migración, instrucciones de pasos en la UI.
  - Mensaje final con `echo PRUEBAS COMPLETADAS` y `pause`.
- El `.bat` **no levanta** Docker ni el servidor automáticamente (son pasos previos manuales); sí puede comprobar con `curl` o comandos similares que los servicios estén respondiendo antes de continuar.

> **IMPORTANTE — codificación del archivo `.bat`**
> El tool `Write` guarda en UTF-8, pero CMD de Windows requiere ANSI sin BOM.
> Un archivo `.bat` con BOM hace que CMD interprete los primeros bytes de cada comando
> como el nombre del programa (`echo` → `ho`, `curl` → `rl`, `pause` → `ause`).
> **Siempre** usa PowerShell para escribir los `.bat`:
>
> ```powershell
> [System.IO.File]::WriteAllText(
>     'ruta\absoluta\archivo.bat',
>     $content,
>     [System.Text.Encoding]::GetEncoding(1252)
> )
> ```
>
> Verifica que los primeros bytes son `0x40 0x65 0x63 0x68` (`@ech`) y no un BOM
> (`0xEF 0xBB 0xBF` para UTF-8, `0xFF 0xFE` para UTF-16 LE).

### Instrucciones para el usuario

Tras generar el `.bat`, muestra en la respuesta un bloque con instrucciones sencillas, sin jerga técnica, con este formato:

```
## Pruebas manuales — Prompt X.Y

### Antes de empezar
1. Abre Docker Desktop y asegúrate de que está en marcha (icono verde en la barra de tareas).
2. <paso concreto adicional, p. ej. "Abre una terminal y ejecuta: docker compose up -d">
3. <si el prompt incluye migración: "Ejecuta en una terminal: cd server && uv run alembic upgrade head">

### Ejecuta el archivo
- Haz doble clic en `pruebas_manuales_promptXY.bat` (está en la carpeta <ruta relativa>).
- El script irá mostrando los pasos; pulsa cualquier tecla para avanzar entre ellos.

### Pasos en la interfaz
1. <acción concreta en el frontend: URL exacta, qué hacer, qué debe pasar>
2. <siguiente acción>

### Qué debes ver
- <resultado visual o de comportamiento esperado, con URL, texto o dato concreto>

### Casos límite
- [ ] <escenario edge case + resultado esperado>

### Para terminar
- <cómo detener los servicios si es necesario>
```

Las instrucciones deben ser **accionables y específicas**: rutas reales, valores de ejemplo, resultados esperados. No sirve "comprobar que funciona".

---

## Migraciones Alembic: aplicar automáticamente

Cuando un prompt cree o modifique ficheros en `server/migrations/versions/`, **aplica la migración
al terminar** ejecutando desde `server/`:

```
uv run alembic upgrade <revision_id>
```

donde `<revision_id>` es el ID de la última migración creada en ese prompt.

**Si la BD no está arrancada** (error de conexión), detente y pide al usuario que la encienda
antes de continuar:

> "La base de datos no responde. Arranca Docker Desktop y ejecuta `docker compose up -d db`
> (o el servicio equivalente), y dime cuando esté lista para aplicar la migración."

Una vez la BD responda, aplica la migración y muestra el resultado de `alembic current`
para confirmar que la revisión ha quedado registrada.

---

## Estándares de desarrollo

- **TDD obligatorio**: escribe el test antes del código de producción. No hay PR sin tests.
- **Asincronía total**: prohibidos métodos síncronos para I/O en el servidor. Usa `async/await`.
- **Sin instanciar servicios manualmente**: usa inyección de dependencias (FastAPI `Depends`).
- **i18n obligatorio en el frontend**: ningún string hardcodeado en la UI. Usa `i18next`.
- **Sin features no pedidas**: no añadas manejo de errores, validaciones, flags ni abstracciones
  para escenarios que no están en la tarea actual.

---

## Frontera Edge-Cloud (preparación del despliegue híbrido)

El sistema se despliega en dos modos:

1. **Cloud-only** — toda la lógica corre en el servidor del partner/admin; los
   datos se anonimizan antes de enviarse al LLM. Protección de datos por contrato.
2. **Edge + Cloud** — la lógica operacional (RAG, grafos, ingesta, automation,
   tratamiento de expedientes) corre en un **edge node** dentro de la nube del
   cliente; el **cloud** (admin/partner) sólo conserva configuración
   administrativa y métricas anonimizadas. Requisito regulatorio estricto.

El mismo codebase sirve a ambos modos. Para que eso siga siendo cierto, respeta
**dos fronteras** a la vez: la de datos (modelos ORM) y la de aplicación
(routers y módulos). La línea base de este split se establece en los prompts
**9.6.5** (capa ORM, `ConfigProvider`, sync API) y **9.6.6** (`DEPLOY_MODE`,
clasificación de routers/módulos) del `PLAN_TDD_DETALLADO.md`.

### 1. Frontera de datos (modelos ORM)

Dos `DeclarativeBase` separadas:

- **`HubConfigBase`** → se sincroniza cloud→edge. Modelos: `HubClient`,
  `HubChatbot`, `HubLLMConfig`, `HubPromptTemplate`.
- **`HubOperationalBase`** → vive sólo en el edge. Modelos: `HubDocumentChunk`,
  `HubInteraction`, `HubIngestionJob`.

**Reglas duras**:

- **Sin `relationship()` cross-base**. Si un modelo operacional necesita un
  chatbot, consulta por `chatbot_id` con un query explícito — no navegues por
  `.chatbot`. Las FK con `ondelete="CASCADE"` se conservan; la navegación ORM
  no.
- **Los servicios edge no importan modelos de config directamente**. El acceso
  a configuración pasa por `ConfigProvider` (protocolo con `LocalConfigProvider`
  por defecto; `RemoteConfigProvider` llegará cuando se implemente la sync API
  real).
- **El router `edge_sync`** (`/api/v1/edge/config`, `/api/v1/edge/telemetry`)
  es la única superficie que ve ambos mundos.

### 2. Frontera de aplicación (routers y módulos)

Clasificación, regulada en runtime por `DEPLOY_MODE=cloud|edge|all` (default
`all`, comportamiento actual):

| Capa | Cloud (admin/partner) | Edge (cliente) | Compartidos |
|---|---|---|---|
| **Routers HTTP** | `auth_router`, `hub_chatbots_router`, `hub_clients_router`, `library_router`, futuros `/hub/prompts`, `/hub/themes` | `hub_chat_router`, `ingestion_router`, `hub_tasks_router`, `hub_feedback_router`, futuros `/automation/*` | `edge_sync_router` (servido por cloud, consumido por edge) |
| **Módulos lógica** | `services/prompt_service` (CRUD), gestión partners / billing | `agents_hub/agent/` (graph, task_runner, tools, hitl), `agents_hub/ingestion/`, `agents_hub/services/retriever`, `agents_hub/evaluation/`, **`modules/automation/` íntegro** | `core/auth`, `services/model_factory`, `services/embedding_service`, `services/config_provider` |

**Reglas duras**:

- **Un módulo edge no puede importar** desde un módulo cloud (ni routers ni
  servicios admin/billing/partners). La configuración se lee vía
  `ConfigProvider`.
- **Los grafos LangGraph, el task runner y los tools** son edge: no leen
  `HubChatbot` ni `HubPromptTemplate` directamente.
- **El módulo `modules/automation/` es edge**: factories, flows, ETL, PDF y
  scripts procesan documentos/expedientes del cliente. No importa routers
  cloud ni gestión admin.
- **Al registrar un router nuevo** en `main.py`, **etiquétalo** en su docstring
  (`Deploy: cloud|edge|shared`) y regístralo en la función `_register_cloud`,
  `_register_edge` o ambas.
- **La anonimización previa al LLM** es responsabilidad edge: los servicios
  edge entregan datos ya anonimizados a `model_factory`; el factory no
  anonimiza.

### Si dudas dónde va algo nuevo

Pregunta:

- ¿Toca datos del cliente final (conversaciones, documentos, expedientes,
  chunks, embeddings)? → **edge**.
- ¿Sólo toca configuración, prompts, chatbots, clientes, partners, billing,
  usuarios? → **cloud**.
- ¿Ambos? Probablemente hay que partir la responsabilidad en dos servicios.

Si violas estas reglas, bloqueas el despliegue edge. Para, reconsidera, o
razona en el PR por qué es inevitable.

---

## Infraestructura objetivo y portabilidad

El primer despliegue de producción usa **Google Cloud Platform**:

- **Base de datos**: Cloud SQL (PostgreSQL 16 + pgvector). Conexión vía Cloud SQL Auth Proxy.
- **Aplicación**: Cloud Run (FastAPI). Sin estado local: el contenedor puede destruirse en cualquier momento.
- **Almacenamiento de documentos**: Google Cloud Storage (GCS).

El codebase debe funcionar sin cambios en un segundo backend (MinIO + PostgreSQL local, AWS S3 + RDS,
etc.) cambiando solo variables de entorno. **No acoples el código a ningún proveedor concreto.**

### Reglas duras de portabilidad

#### 1. Almacenamiento de ficheros: `fsspec` obligatorio

**Prohibido** acceder directamente al sistema de archivos para guardar o leer documentos
que pertenecen al negocio (PDFs subidos, resultados de procesamiento, adjuntos).
**Usa siempre `StorageService`** (wrapper sobre `fsspec`) inyectado vía `Depends`.

```python
# CORRECTO
async def upload_pdf(file: UploadFile, storage: StorageService = Depends(get_storage)):
    await storage.put(f"ingestion/{job_id}.pdf", file)

# PROHIBIDO — rompe Cloud Run (efímero) y acopla al SO local
with open(f"/tmp/{job_id}.pdf", "wb") as f:
    shutil.copyfileobj(file.file, f)
```

El backend se configura por variable de entorno:

| Variable | Desarrollo (local/Docker) | Producción GCP |
|---|---|---|
| `STORAGE_BACKEND` | `file` o `s3` (MinIO) | `gcs` |
| `STORAGE_BUCKET` | `/tmp/govgenai` o `govgenai-dev` | `govgenai-prod` |
| `STORAGE_ENDPOINT` | `http://minio:9000` (solo S3) | — |

El `StorageService` vive en `server/app/core/storage.py`. Si no existe aún, créalo antes de
escribir cualquier código que necesite persistir ficheros.

#### 2. Sin escrituras efímeras fuera del procesamiento en streaming

Cloud Run no garantiza disco persistente entre peticiones. Las escrituras en `/tmp` solo están
permitidas como buffer **temporal dentro de una misma petición/tarea** y deben borrarse
explícitamente al finalizar. Nunca asumas que `/tmp` sobrevive entre llamadas.

#### 3. Base de datos: DSN siempre por variable de entorno

La URL de conexión a la base de datos se lee **únicamente** de `DATABASE_URL` (async) y
`DATABASE_URL_SYNC` (Alembic). No hardcodees host, puerto, usuario ni contraseña en código.
Cloud SQL usa el patrón de socket Unix vía Cloud SQL Auth Proxy:

```
postgresql+asyncpg:///govgenai?host=/cloudsql/PROJECT:REGION:INSTANCE
```

---

## Servicios de computación pesada: microservicios separados

BGE-M3 (~1.1 GB de modelo) y Docling (CPU-intensivo) **no deben ejecutarse in-process
dentro del servidor FastAPI principal** cuando se despliegue en Cloud Run. Los motivos:

- Cold start de 30–90 s al cargar el modelo → inaceptable para el chatbot.
- 3–4 GB de RAM por instancia → coste 3–4× mayor en Cloud Run.
- Escala conjunta: si el chat tiene picos, también se escalan las instancias con el modelo cargado.

### Arquitectura objetivo

```
Cloud Run: govgenai-api   →  HTTP  →  Cloud Run: embedding-service  (min 1 instancia)
(FastAPI, ~512 MB RAM)    →  HTTP  →  Cloud Run: docling-service    (escala a 0)
          │
          └──────────────────────────→  Cloud SQL
          └──────────────────────────→  GCS (via StorageService / fsspec)
```

### Reglas de implementación

- **`EmbeddingService`** ya es un protocolo con `LocalEmbeddingService` y `GoogleEmbeddingService`.
  Cuando se implemente el microservicio, añade `HttpEmbeddingService` que llame a
  `POST /embed` del servicio separado. El resto del código no cambia.
- **`DoclingProcessor`** se extrae a su propio servicio con un endpoint
  `POST /process-pdf` que devuelve Markdown. El cliente HTTP queda en `ingestion/`.
- **Mientras tanto** (fase de desarrollo sin Cloud Run real): `LocalEmbeddingService` y
  `DoclingProcessor` in-process siguen siendo válidos. La abstracción ya existe;
  solo se cambia la implementación concreta que inyecta `Depends`.
- **No mezcles**: si un servicio llama al embedding service via HTTP, no puede también
  importar `LocalEmbeddingService` como fallback silencioso. El fallback se configura
  en el `Depends`, no en la lógica de negocio.

### Cuándo extraer a microservicio (criterio)

Extrae a microservicio separado en el sprint en que cualquiera de estas condiciones se cumpla:

1. El cold start del servidor API supera 15 s en Cloud Run.
2. La memoria del contenedor principal supera 2 GB.
3. Se necesita escalar embedding/Docling de forma independiente al API.

Hasta entonces, la abstracción existente es suficiente. **No anticipes la extracción**
antes de que el problema aparezca en métricas reales.

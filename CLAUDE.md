# Instrucciones para agentes de programación

## Contexto del proyecto

Gov Gen AI Platform es el resultado de integrar **AI Agents Hub** (chatbots RAG, LangGraph) y **AutomatIA**
(automatización, scripts, RPA) en un monorepo. El plan de desarrollo completo está en `planificacion/PLAN_DESARROLLO.md`.

El cliente NiceGUI (`client_app/`) está siendo migrado progresivamente al servidor FastAPI y al frontend React.
**El código NiceGUI es legacy y debe eliminarse** a medida que cada módulo quede cubierto en el nuevo sistema.

---

## Ejecución agéntica por bloques

El desarrollo se ejecuta **de forma autónoma y secuencial, por bloques de prompts**.
Un bloque es una fila de la tabla de planes activos de `planificacion/PROJECT_STATE.md`
(Fase 11 = 11.1→11.3; Bloque SEC = SEC.1→SEC.7; Bloque RAG = RAG.1→RAG.14...).

**El bloque es la unidad de interacción: una vez arrancado, no informes hasta cerrarlo.**
No pidas confirmación entre prompts. Detalle completo en `docs/METODOLOGIA_AGENTICA.md`.

### Bucle por prompt (sin interacción)

RED → GREEN → REFACTOR → verificaciones de cierre (suite verde, migración aplicada,
contrato regenerado si cambió la API, retirada del legacy con `grep -r` a cero,
verificación en navegador si toca UI) → actualizar `planificacion/PROJECT_STATE.md` →
**un commit Conventional por prompt** con el identificador del prompt en el asunto,
sin `Co-Authored-By` y **sin push** → siguiente prompt.

El commit por prompt es lo que hace reversible un bloque largo: si el prompt 5 rompe
el 3, hay un punto exacto al que volver.

### Qué tests ejecutar y cuándo (escalonado)

Ejecutar la suite entera después de cada prompt cuesta minutos y no aporta información nueva
la mayoría de las veces. Tres niveles:

| Cuándo | Qué | Coste |
|---|---|---|
| **Durante el prompt** (bucle RED→GREEN) | Solo el fichero de tests que estás escribiendo | segundos |
| **Al cerrar el prompt** | Los directorios que el prompt toca + `tests/infra/test_suite_hygiene.py` | segundos a 1 min |
| **Al cerrar el bloque** | `uv run pytest tests` completo, **desde Git Bash** | 1-3 min |

`test_suite_hygiene.py` entra en el nivel intermedio porque tarda medio segundo y caza justo
lo que se escapa de un subconjunto: mocks sobre clases, `create_all` sobre la BD del
desarrollador, imports a módulos que ya no existen.

**Desde Git Bash, no desde PowerShell.** `tests/infra/test_setup_script.py` invoca `bash`, que
en PowerShell resuelve al lanzador de WSL y da 10 rojos de entorno. Ver la nota del historial
del 2026-07-31 en `planificacion/PROJECT_STATE.md`.

La suite corre en paralelo (`-n auto` en `addopts`) y sin cobertura; para depurar un fallo con
la salida en orden, `-n0`, y para medir cobertura en local, `--cov=app`. **Si una cifra de
tests no se ha medido, no se reporta como medida**: dilo como lo que es.

**CI corre con `-n0`, a propósito.** El paralelismo reparte los tests entre 16 procesos, y eso
esconde el estado filtrado entre tests —un mock asignado a una clase, un singleton
contaminado—, que es justo lo que TST.1 unificó CI para cazar. En local manda la velocidad;
en CI manda la detección. No añadas `-n auto` a los pasos de CI.

### Cuándo SÍ interrumpir a mitad de bloque

Solo por estas cuatro causas:

1. **Operación de riesgo** — la detecta la guarda (`.claude/hooks/guard_operaciones_riesgo.ps1`)
   y genera un prompt de permiso. No la fuerces ni busques rodeos.
2. **Decisión de criterio** — ambigüedad del plan que llevaría a productos distintos,
   arquitectura que el plan no cierra, o alcance que excede el bloque. Usa
   `AskUserQuestion` con opciones y recomendación.
3. **Fallo persistente** — un RED que no llega a GREEN, o suite en rojo por causa no
   atribuible al prompt. Para y reporta **con el output real**; no marques el prompt
   como cerrado.
4. **Prerrequisito externo ausente** — BD apagada, Docker cerrado, corpus no entregado,
   credencial que falta.

### Cuándo NO interrumpir

- **Desviaciones entre el plan y el código real.** Aplica la interpretación más fiel al
  espíritu del prompt, sin inventar infraestructura inexistente ni añadir features no
  pedidas; regístralo como *"Desviación documentada"* en el historial de
  `planificacion/PROJECT_STATE.md` y sigue. Se resume en el informe de cierre.
- Fallos de test preexistentes ya inventariados.
- Dudas de estilo o estructura resolubles con las reglas de este documento.

### Al arrancar y al cerrar

- **Al arrancar**: lee el cursor de `planificacion/PROJECT_STATE.md`, lee los prompts verbatim del plan,
  comprueba los prerrequisitos, y si algún prompt del bloque sugiere un modelo más capaz
  que el de la sesión, dilo **una sola vez antes de empezar**.
- **Al cerrar**: un solo informe con prompts cerrados + commits, cifras reales de tests,
  migraciones aplicadas, qué verificaste en navegador con qué evidencia, desviaciones
  documentadas, pendientes, y las instrucciones de pruebas manuales del bloque.
  Después **espera**: el siguiente bloque no arranca solo.

---

## Regla crítica: migración = código nuevo + retirada del legacy

Una tarea de migración **no está completa** hasta que el código original quede retirado.
No dejes código muerto, imports sin usar, archivos vacíos ni comentarios `# TODO: migrate`.

La retirada sigue un proceso de **dos pasos** según el tipo de código:

### Caso A — Código NiceGUI con migración activa en curso

El código NiceGUI se mueve a `_legacy_nicegui/` cuando se completa su migración, manteniendo la ruta relativa. Sirve como referencia durante el resto de la Fase 1, mientras el código nuevo se va estabilizando contra escenarios reales.

1. **Al cerrar el prompt de implementación** (GREEN): mover el fichero a `_legacy_nicegui/` manteniendo la ruta relativa.
2. **No borres `_legacy_nicegui/` automáticamente al cerrar una subfase**. El borrado definitivo lo hace **el usuario manualmente** al cierre de la **Fase 1 completa**, una vez verificado que todo lo migrado funciona en producción.

`_legacy_nicegui/` acumula ficheros a lo largo de Fase 1. No la consideres "zona temporal corta": es cuarentena de larga duración hasta el cierre de Fase 1.

Lo que sí debes hacer al mover algo a `_legacy_nicegui/`:
- Asegurarte de que ningún import activo apunta ya al fichero migrado (`grep -r` antes de cerrar el prompt).
- No volver a importar desde `_legacy_nicegui/` en código nuevo. Ese directorio es **solo lectura** para los agentes; queda como referencia documental.
- No reintroducir código desde ahí. Si el código migrado tiene un bug, se arregla en la nueva ubicación; el fichero en `_legacy_nicegui/` no se toca.

### Caso B — Código huérfano sin migración activa

Código que ya no se usa y no tiene una migración en curso asociada: **borrar directamente**, sin pasar por `_legacy_nicegui/`. El historial de git es la fuente de verdad del pasado.

### Definición de "migración completa" (checklist obligatorio)

Antes de cerrar cualquier tarea de migración, verifica y ejecuta cada punto:

- [ ] La nueva implementación tiene tests que pasan (`pytest` o equivalente)
- [ ] El endpoint o servicio nuevo está integrado y verificado end-to-end
- [ ] El archivo o módulo legacy está en `_legacy_nicegui/` (Caso A) o **eliminado** (Caso B)
- [ ] Los imports del legacy han sido eliminados de todos los ficheros que los referenciaban
- [ ] No quedan referencias al código eliminado en ningún fichero del proyecto (`grep -r` antes de cerrar)
- [ ] El `docker compose up` + suite de tests completa sigue pasando tras la retirada

---

## Normas generales de limpieza

**Borra, no comentes.**
Si el código ya no se usa, elimínalo. Los comentarios `# deprecated`, `# old version` o `# legacy`
son deuda técnica disfrazada. El historial de git es la fuente de verdad del pasado.

**`_legacy_archive/` no recibe nada nuevo.**
El directorio `_legacy_archive/` existe por razones históricas. No añadas nada nuevo ahí.
El único directorio de cuarentena válido durante migraciones activas es `_legacy_nicegui/`.
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
server/app/modules/agents_hub/   ← RAG, LangGraph, chatbots, ingesta del corpus
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

## Verificación de UI: navegador primero, humano al final del bloque

Cuando un prompt toca frontend, **el agente lo verifica él mismo en el navegador** con la extensión de Chrome (`mcp__claude-in-chrome__*`), dentro del bloque y sin pedir permiso: navega a la URL, comprueba el contenido con `read_page`/`find`, interactúa con `computer`/`form_input`, y revisa `read_console_messages` y `read_network_requests` en busca de errores que los tests unitarios no ven. Detalle del protocolo en `docs/METODOLOGIA_AGENTICA.md` §4.

Las **pruebas manuales humanas se reservan para el cierre del bloque** y se limitan a lo imprescindible: SSO SAML real, sistemas externos no simulables (G400, ENI, APIs UJI), juicio subjetivo de identidad visual, accesibilidad con lector de pantalla real y cualquier cosa con datos personales o credenciales reales.

### Qué exige pruebas manuales humanas

Solo lo que el agente **no puede** verificar con el navegador:

- Flujos con credenciales reales o IdP institucional.
- Integración con sistemas externos no disponibles en local.
- Valoración subjetiva: identidad visual, tipografía, tono del texto institucional.
- Accesibilidad con lector de pantalla real.

### Qué NO necesita pruebas manuales

- Código exclusivamente backend: tests unitarios, tests de integración, servicios, modelos ORM, workers, migraciones de BD, endpoints de API sin UI asociada.
- Comprobaciones que ya cubren los tests automáticos.
- **Todo lo que el agente ya verificó en navegador**: no se repite en el `.bat`; se menciona como verificado en el informe de cierre.
- Infraestructura, configuración o scripts sin impacto visual.

### Archivo .bat

- **Uno por bloque, no por prompt.** Se genera al cerrar el bloque.
- **Nombre**: `pruebas_manuales_bloque<NOMBRE>.bat` (p. ej. `pruebas_manuales_bloqueSEC.bat`). Para prompts sueltos fuera de un bloque: `pruebas_manuales_promptXX.bat`.
- **Ubicación**: `pruebas_manuales/`. Los comandos siguen ejecutándose desde la raíz del
  proyecto: el `.bat` lleva `cd /d "%~dp0.."` justo tras el `chcp`, así que las rutas relativas
  (`frontend\.env.local`, `cd server`) funcionan aunque el guion viva en un subdirectorio.
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
## Pruebas manuales — Bloque <NOMBRE>

### Ya verificado por el agente en navegador
- <flujo comprobado + evidencia: URL, texto encontrado, consola limpia>

### Antes de empezar
1. Abre Docker Desktop y asegúrate de que está en marcha (icono verde en la barra de tareas).
2. <paso concreto adicional, p. ej. "Abre una terminal y ejecuta: docker compose up -d">
3. <si el bloque incluye migración: "Ejecuta en una terminal: cd server; uv run alembic upgrade head">

### Ejecuta el archivo
- Haz doble clic en `pruebas_manuales_bloque<NOMBRE>.bat` (está en la carpeta <ruta relativa>).
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

# 🏛️ REGLAS MAESTRAS DE ARQUITECTURA Y TDD

Este proyecto (Gov Gen AI Platform) sigue una arquitectura estrictamente "Contract-First". La ÚNICA fuente de verdad es el backend. El frontend es completamente "tonto" y reactivo. 

Bajo NINGUNA circunstancia generarás código en React que contenga lógica de negocio, reglas de estado, o interfaces de datos *hardcodeadas* que no provengan del contrato del servidor.

Al implementar tests (TDD) o escribir código, DEBES aplicar las siguientes restricciones por módulo:

## 1. AutomatIA (Scripts y Flujos) - Contrato SDUI (Server-Driven UI)
* **Regla:** El frontend NO conoce los campos de un script a priori. 
* **Implementación:** El backend debe devolver un `ui_contract` (JSON Schema o similar). El frontend debe construir los formularios dinámicamente iterando sobre ese contrato.
* **TDD:** Los tests de React deben fallar si intentan buscar un campo hardcodeado (ej. `input name="email"`). Deben probar que el componente se renderiza basándose en el JSON recibido.

## 2. Gestor de Expedientes - Contrato de Estado (HATEOAS)
* **Regla:** El frontend NUNCA calcula qué acciones están permitidas (ej. no debe existir código como `if (fase === 'revision') mostrarBoton()`).
* **Implementación:** El backend es la máquina de estado. El DTO de respuesta del expediente debe incluir un array `acciones_permitidas: list[str]`, calculado en el servidor evaluando fase, estado y rol del usuario.
* **TDD:** Los tests de backend deben verificar que los usuarios sin permisos reciben un array de acciones vacío. Los tests de frontend deben verificar que los botones se generan iterando sobre `acciones_permitidas`.

## 3. LangGraph y Malla Agéntica
* **Regla de Estado:** El `ExpedienteState` o `WorkspaceState` es inmutable fuera de los contratos tipados. Los nodos solo leen y escriben sobre los campos explícitamente definidos en el `TypedDict` o Pydantic.
* **Regla de Ejecución (Invariante):** Cualquier ejecución determinista (extracción, scripts) orquestada por el grafo en el cloud DEBE delegarse al Edge Node vía WebSocket. El cloud orquesta, el Edge ejecuta.

## 4. Frontend y OpenAPI
* Usa siempre los tipos y hooks generados por Orval a partir de `openapi.json`. 
* Usa `react-hook-form` y `zodResolver`. La validación del cliente debe derivarse o estar estrictamente alineada con el contrato del backend.

## 5. Corpus normativo: clasificación revisable y coste de reindexado

El corpus del asistente normativo se clasifica por **ámbito** y **submaterias** (vocabulario en
`Descarregar_pdf\normativa_propia\vocabulari\`), y ese vocabulario **está pendiente de validación
por Secretaría General**: va a cambiar. Dos reglas lo mantienen revisable. Violar cualquiera de
las dos convierte «reclasificar el corpus» en «reindexar el corpus», y a partir de ahí el
vocabulario deja de revisarse en la práctica.

* **El vocabulario es dato, no código.** Los términos (ámbitos, submaterias, rangos, colectivos)
  viven en tabla versionada, con `vigent` y `substituit_per_codi` para renombrar y fusionar.
  **Prohibido** expresarlos como `Enum` de Python, `CheckConstraint` de Postgres o lista literal
  en el código. Los **ejes** sí son estructura (pocos y estables): esos van en `StrEnum`, porque
  añadir un eje exige de todos modos código que lo consuma.

* **La taxonomía NUNCA entra en el texto que se embebe.** En `embedding_text` solo va contexto
  **estructural** —título del documento y jerarquía de encabezados (título / capítulo / artículo)—,
  que es estable. Nunca `ambit_principal`, `submateries`, `submateries_internes` ni ninguna etiqueta
  del vocabulario, ni el ancla del artículo. Los pares bilingües del dominio (`despesa`/`gasto`)
  son puente **léxico** y van al `tsvector` de la búsqueda de texto completo, que se regenera con
  una sentencia SQL; un embedding necesita GPU y horas.

  Corolario operativo: reclasificar debe costar un `UPDATE` sobre `hub_documents`. Si un cambio de
  etiqueta te obliga a re-embeber, algo se ha colado en el texto embebido.

Contexto completo de la estrategia de recuperación en tres niveles: bloques **ING.0**, **VIS** y
**SYNC** de `planificacion/Plan_TDD_Fase1.md`.

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
clasificación de routers/módulos) del `planificacion/PLAN_TDD_DETALLADO.md`.

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
- **El módulo `modules/redaccion/` es edge**: contratos de plantilla, pipelines de
  extracción, DraftingCoreGraph, LLMSpecService y RunManifest procesan documentos y
  expedientes del cliente. Los routers se etiquetan `Deploy: edge` y no importan
  módulos cloud. Ver `docs/REDACCION_CONTRACT_FIRST.md`.
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

## Servicios de computación pesada

> **Actualizado el 2026-08-11 (bloque EXT + decisión de despliegue).** Esta sección decía que
> Docling y BGE-M3 debían extraerse a servicios separados de Cloud Run. **Docling ya no
> existe** en el servidor y **el despliegue ya no es Cloud Run**, así que la mitad del
> problema desapareció en vez de resolverse. Ver `docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md`.

**Docling: retirado (EXT.3).** Al corpus solo entra `.md` conforme a
`docs/CONTRATO_MD_CORPUS.md`, producido por el pipeline de curación que vive **fuera** de la
aplicación; el contexto temporal —el PDF que alguien aporta para preguntarle cosas, o la
fuente de un informe— se extrae con **pdfplumber**. No reintroduzcas un conversor de
documentos en el servidor: si algo hay que convertir, se convierte antes de llegar.

**Lo que pesa hoy es `torch`**, no la extracción. Medido en EXT.3: la aplicación en reposo
son 627 MB y el arranque lo dominan `transformers` (142 s), `sentence-transformers` (75 s /
216 MB) y `torch` (52 s / 172 MB) — todo ello por `LocalEmbeddingService` (BGE-M3) y
`LocalReranker`. `pdfplumber` cuesta 0,09 s y 5 MB.

### Regla vigente

- **`EmbeddingService`** sigue siendo un protocolo con `LocalEmbeddingService` y
  `GoogleEmbeddingService`. Con embeddings por API (el plan de despliegue) la pila local no
  se usa en ejecución pero se paga entera en memoria y arranque: **hacerla un extra de
  instalación opcional está anotado como candidato en D.4**, no hecho.
- **No mezcles**: si un servicio llama al embedding service via HTTP, no puede también
  importar `LocalEmbeddingService` como fallback silencioso. El fallback se configura
  en el `Depends`, no en la lógica de negocio.
- **El modo edge sigue necesitando los modelos locales**: lo que se decida sobre el
  empaquetado no puede quitar esa capacidad, solo hacerla opcional.

Hasta entonces, la abstracción existente es suficiente. **No anticipes la extracción**
antes de que el problema aparezca en métricas reales.

---

## Modelo por prompt

Cada prompt activo en `planificacion/Plan_TDD_Fase1.md` (y subsiguientes) lleva una etiqueta `**Modelo sugerido**: Opus | Sonnet — <razón corta>` justo bajo el título. La etiqueta es **una recomendación informada**, no un requisito: el usuario decide al abrir sesión qué modelo usar con `/model opus` o `/model sonnet`.

Heurística usada para etiquetar:

- **Opus** se sugiere cuando el prompt concentra **decisiones de diseño embebidas** (qué preservar de un legacy masivo, cómo discriminar uniones, cómo afinar prompts del sistema LLM), **migra >800 LOC ajeno**, o requiere **debugging cruzado multi-módulo** donde Sonnet suele pegarse.
- **Sonnet** se sugiere cuando el alcance está **explícitamente cerrado en el prompt** (endpoints concretos, tests enumerados, fixtures dadas) y las **decisiones abiertas son pocas**.

Una segunda referencia rápida vive en `planificacion/PROJECT_STATE.md`:
- Columna **Modelo sugerido siguiente** en la tabla de bloques activos.
- Línea **"Modelo sugerido para el próximo prompt: ..."** junto al "Cursor actual".

Cómo actúa un agente al abrir una sesión:

1. Lee `planificacion/PROJECT_STATE.md` y localiza el cursor + el modelo sugerido para el próximo prompt.
2. Si el modelo de la sesión actual coincide con el sugerido → procede.
3. Si NO coincide → menciona la discrepancia en una sola línea al inicio de la respuesta ("El cursor sugiere Opus para este prompt; estoy en Sonnet. ¿Continúo o prefieres cambiar con `/model opus`?") y espera decisión del usuario antes de ejecutar.
4. No intentes auto-cambiar de modelo. La elección es del usuario por motivos de coste/disponibilidad.

En **ejecución por bloques**, esta comprobación se hace **una sola vez, al arrancar el bloque**, sobre el conjunto de sus prompts: si alguno sugiere un modelo más capaz que el de la sesión, dilo antes de empezar y espera decisión. Dentro del bloque no se vuelve a interrumpir por este motivo.

Cuándo delegar a un sub-agente con modelo distinto:

- Tareas **autocontenidas** dentro de un prompt mayor (auditoría de un diff, búsqueda compleja, revisión de seguridad sobre código generado): se pueden delegar via tool `Agent` con `model: "opus"` aunque la sesión esté en Sonnet.
- **No** delegar un prompt entero de implementación a un sub-agente: pierde el historial conversacional y no puede pedirte clarificaciones.

---

## Seguimiento del estado del proyecto

El archivo `planificacion/PROJECT_STATE.md` es la fuente de verdad del progreso de los planes de desarrollo.

### Regla obligatoria: actualizar planificacion/PROJECT_STATE.md al terminar cada prompt

**Al finalizar cualquier prompt que implemente o avance un paso de un plan de desarrollo**
(`planificacion/Plan_TDD_Fase1.md`, `Plan_Contrato_OpenAPI.md`, `planificacion/Plan_TDD_Fase2.md`, `planificacion/Plan_TDD_Fase3.md`
o cualquier plan futuro), actualiza `planificacion/PROJECT_STATE.md` antes de cerrar la respuesta:

1. **Marca el paso completado** con ✅ y mueve el cursor al siguiente.
2. **Si el paso es parcial** (p. ej. RED escrito pero GREEN pendiente), márcalo con ▶ y anota qué falta.
3. **Añade una fila arriba de la tabla de `planificacion/HISTORIAL.md`** con la fecha de hoy, el identificador del prompt y una descripción de una línea. El historial se separó de `planificacion/PROJECT_STATE.md` el 2026-08-21: eran 535 de sus 626 KB, y este fichero se lee entero al arrancar cada sesión.
4. **Si un bloque entero queda completo**, actualiza la columna Estado del bloque a ✅ Completo.

Esta actualización es **obligatoria** incluso en prompts pequeños o de corrección.
No omitirla aunque el cambio sea un fix puntual que avanza el cursor.

### Cuándo NO actualizar planificacion/PROJECT_STATE.md

- Prompts de configuración de herramientas (permisos, settings, hooks).
- Prompts de consulta o explicación sin cambios de código.
- Refactors internos sin relación con un paso numerado de un plan.

---

## Reglas de comandos de shell

El entorno de ejecución es **Windows con PowerShell 5.1**. El operador `&&` no existe en PowerShell y provoca un error de parseo.

### Prohibido: `&&` en cualquier comando

**Nunca** uses `&&` para encadenar comandos, ni en la herramienta Bash ni en PowerShell.

```powershell
# PROHIBIDO — falla en PowerShell
cd frontend && npm test

# CORRECTO — encadenamiento incondicional
cd C:/Users/fabra/Documents/AI_agents_hub/frontend; npm test

# CORRECTO — encadenamiento condicional (ejecuta B solo si A tiene éxito)
cd C:/Users/fabra/Documents/AI_agents_hub/frontend; if ($?) { npm test }
```

Si necesitas encadenar comandos en la herramienta Bash, usa también `;` en lugar de `&&` para mantener consistencia y evitar errores si el contexto cambia a PowerShell.

### Navegación de directorios

- Usa siempre **rutas absolutas** al cambiar de directorio: `cd C:/Users/fabra/Documents/AI_agents_hub/frontend`
- No uses `cd` para salir del directorio raíz del proyecto (`C:/Users/fabra/Documents/AI_agents_hub`).
- Para inspeccionar estructura de carpetas, prefiere las herramientas `Glob` y `Read` antes que `ls` o `dir`.

# Especificaciones de Gov Gen AI Platform

> **Lo vigila un test.** `server/tests/infra/test_especificaciones_no_miente.py` comprueba que
> todo lo que este documento nombra existe y que los vocabularios que enumera son los que el
> código declara. Si algo de aquí deja de ser verdad, la suite se pone roja. Ver §11.

## 1. Qué es y qué no es este documento

Es la **especificación por capacidad**: para cada cosa que la plataforma sabe hacer, qué garantiza,
dónde se hace cumplir esa garantía, qué la demuestra, y qué queda abierto.

Existe porque faltaba una frase que no está escrita en ningún otro sitio: **«el sistema garantiza
Y»**. Los planes de `planificacion/` dicen «haz X» —son *prompts*, ordenados por ejecución—, y de
ahí no se deduce qué se puede cambiar sin romper nada. Esa deducción es justo lo que necesita quien
llega de fuera a continuar un desarrollo.

**Qué no es, y dónde está en su lugar:**

| No es | Está en |
|---|---|
| Una presentación del proyecto | [`PRESENTACION_PROYECTO.md`](PRESENTACION_PROYECTO.md) |
| El diseño y sus principios | [`Arquitectura.md`](Arquitectura.md) |
| El estado del desarrollo hoy | [`../planificacion/PROJECT_STATE.md`](../planificacion/PROJECT_STATE.md) |
| Por qué algo se hizo así | [`../planificacion/HISTORIAL.md`](../planificacion/HISTORIAL.md) y los docstrings |
| Las reglas de cómo se trabaja | [`../AGENTS.md`](../AGENTS.md), [`../CONTRIBUTING.md`](../CONTRIBUTING.md) |
| El plan de lo que falta | `planificacion/Plan_TDD_Fase1.md` y siguientes |

**Este documento apunta, no copia.** La regla es dura y tiene motivo: el proyecto persigue las
dobles fuentes de verdad —el vocabulario del corpus es dato y no `Enum`, el inventario de
multitenencia lo vigila un test— y un documento que repitiera el estado del desarrollo divergiría
en semanas y mentiría con autoridad. Aquí va lo **estable**: capacidades, contratos, invariantes.
Lo **volátil** —qué bloque está en curso, qué prompt viene— vive en `PROJECT_STATE.md` y aquí sólo
se enlaza.

---

## 2. Cómo leer una capacidad

Cada capacidad de §5 a §7 se describe con el mismo esqueleto:

- **Qué hace** — en una o dos frases, sin jerga.
- **Garantiza** — las afirmaciones que se pueden dar por ciertas al construir encima. Si una es
  falsa, es un defecto, no una decisión.
- **Superficie** — endpoints, tablas y componentes por los que se toca.
- **Invariantes** — lo que no se puede romper, con el sitio donde se hace cumplir.
- **Madurez** — `producción` (desplegado y en uso), `construido` (completo y probado, sin uso
  real todavía), `parcial` (funciona con límites conocidos) o `previsto` (especificado, sin
  construir).
- **Abierto** — lo que falta o está decidido a medias, con el bloque del plan que lo aborda.

**La madurez es deliberadamente gruesa.** El detalle fino (qué prompt, qué fecha) está en
`PROJECT_STATE.md`, que es lo que se actualiza a diario; si se repitiera aquí, este documento sería
viejo la semana que viene.

---

## 3. El sistema en una página

Gov Gen AI Platform da a una administración pública cuatro cosas sobre una misma base:

1. **Asistentes informativos** que responden sobre su normativa **citando la norma**, y que
   **callan** cuando no tienen fundamento.
2. **Curación de contenido**: rastrear su portal, revisar qué ha cambiado y decidir qué entra al
   corpus.
3. **Informes y automatización**: plantillas con datos deterministas y valoración de la IA sujeta
   a aprobación humana.
4. **Administración multiorganización**: una instalación sirve a varias organizaciones sin que se
   vean entre ellas.

```
┌─ frontend/src ────────────────────────────────────────────────┐
│  admin · curation · redaccion · widget                        │
└───────────────────────┬───────────────────────────────────────┘
                        │  contrato OpenAPI → cliente generado (Orval)
┌───────────────────────┴───────────────────────────────────────┐
│  server/app/routers · api/v1        registrados en main.py     │
├───────────────────────────────────────────────────────────────┤
│  server/app/modules/                                          │
│    agents_hub   asistentes, corpus, ingesta, evaluación       │
│    curation     rastreo de portales y revisión                │
│    redaccion    informes, plantillas, scripts, sandbox        │
│    automation   flujos, ETL, PDF                              │
├───────────────────────────────────────────────────────────────┤
│  server/app/core/    auth · tenancy · ámbito · storage ·      │
│                      llm gateway · language_mode · llm_text   │
├───────────────────────────────────────────────────────────────┤
│  PostgreSQL 16 + pgvector   ·   almacenamiento vía fsspec     │
└───────────────────────────────────────────────────────────────┘
```

**Dos fronteras estructurales** que condicionan cualquier código nuevo, y que están explicadas en
`AGENTS.md`:

- **Cloud / Edge.** La configuración administrativa vive en el cloud; los datos del cliente
  —conversaciones, documentos, expedientes— pueden vivir en un *edge node* dentro de su nube. Dos
  `DeclarativeBase` separadas (`HubConfigBase`, `HubOperationalBase`), sin `relationship()` que
  las cruce, y `ConfigProvider` como único camino del edge a la configuración.
- **Organización.** Toda tabla de configuración declara su ámbito en `__ambito__`, y hay
  **cuatro** posibles: `plataforma`, `organizacion`, `heredable` (nulo = plataforma, y se hereda)
  y `derivada` (la organización se alcanza por otra tabla). Son cuatro y no tres porque tres
  serían una mentira. El inventario tabla por tabla está en
  [`MULTITENENCIA.md`](MULTITENENCIA.md), y lo vigila su propio test.

---

## 4. Invariantes de plataforma

Lo que no se puede romper. Cada uno dice **dónde se hace cumplir**, porque un invariante que sólo
vive en un documento no es un invariante: es una intención.

| # | Invariante | Se hace cumplir en |
|---|---|---|
| I1 | **Una respuesta sin cita válida no se entrega.** Si no hay fundamento en el corpus recuperado, el asistente se rinde con el mensaje del chatbot | `agent/citation_validator.py` (`enforce_citation_contract`) |
| I2 | **Sólo se cita lo que se recuperó.** Un ancla que no se recuperó se degrada al documento; lo que apunta fuera del conjunto pierde el enlace, no la mención | `degradar_anclas` + `despojar_remisiones`, en ese orden |
| I3 | **La taxonomía nunca entra en el texto que se embebe.** En `embedding_text` sólo va contexto estructural. Reclasificar tiene que costar un `UPDATE`, no un reindexado | contrato del corpus + guardarraíles de ingesta |
| I4 | **El vocabulario es dato, no código.** Ámbitos, submaterias y módulos viven en tabla versionada; prohibido `Enum` de Python o `CheckConstraint` para ellos | `core/auth/modulos.py`, vocabulario del corpus |
| I5 | **Quien no gestiona una organización no ve sus datos.** Y una lista de organizaciones vacía significa «ninguna», no «todas» | `core/auth/tenancy.py`; `test_tenant_isolation.py` |
| I6 | **El frontend no calcula permisos.** El servidor manda `acciones_permitidas` o banderas por fila; React itera | reglas maestras de `AGENTS.md`; DTOs de cada router |
| I7 | **El frontend no define tipos de datos a mano.** Todo sale del contrato OpenAPI vía Orval | job `API Contract` de CI |
| I8 | **Ningún router sirve datos sin acotar por tenencia, o declara por qué no.** | `test_router_inventory_is_walked.py` |
| I9 | **Un docstring no autoriza nada.** Declarar un módulo obliga a exigirlo con `require_module` | el mismo test |
| I10 | **El contenido del modelo se lee con `texto_de`.** Gemini devuelve `content` como lista de bloques en cuanto hay más de una parte, y quien asume `str` falla más tarde y en otro sitio | `core/llm_text.py` + guardarraíl de USR.8 |
| I11 | **Los ficheros de negocio se guardan por `StorageService`**, nunca con `open()`: el contenedor es efímero y el proveedor, cambiable | `core/storage.py`; regla de portabilidad |
| I12 | **Todo lo que va al LLM desde el edge va anonimizado**, y el `model_factory` no anonimiza: recibe datos ya limpios | frontera edge/cloud de `AGENTS.md` |
| I13 | **Código no aprobado no se ejecuta.** Auditoría AST + sandbox + aprobación humana antes de que un script corra | `redaccion/services/script_auditor.py`, `SANDBOX_SECURITY.md` |

**Cómo se usa esta tabla.** Al escribir código nuevo, si tocas algo que aparece en la columna
derecha, el test correspondiente es el que te dirá si te has pasado. Si crees que un invariante
debe cambiar, es una decisión de arquitectura: va con su documento en `docs/`, no con un *commit*.

---

## 5. Capacidades — Fase 1

### 5.1 Asistentes informativos

**Qué hace.** Responde preguntas sobre la normativa de una organización citando el artículo, y
declina cuando no tiene con qué responder.

**Garantiza.**
- Toda afirmación entregada lleva cita a un documento **efectivamente recuperado** (I1, I2).
- La respuesta no presenta como vigente lo que no lo está; la preferencia de lengua opera
  **dentro** de la misma vigencia, nunca por encima.
- El flujo termina siempre: o `done` con `interaction_id`, o `error`. Nunca silencio.
- Cada turno queda registrado con su consumo, y es valorable por `interaction_id`.

**Superficie.** `POST /api/v1/hub/chat/{chatbot_id}` (SSE: `status`, `token`, `discard`, `done`,
`error`) · `hub_feedback_router` · `HubChatbot`, `HubInteraction`, `HubDocumentChunk`.

**Cómo está construido.** Un `CoreGraph` de LangGraph con cuatro estrategias enchufables por eje:
recuperación, fusión, plantilla y **política de lengua**. Dos modos de recuperación en uso: `RAG`
(híbrido vectorial + texto completo, con desempate determinista) y `MD_AGENT_SELECTOR` (el modelo
lee documentos enteros con *tools*).

**Invariantes.** I1, I2, I10.

**Madurez**: `producción` — cuatro asistentes sirviendo en el piloto.

**Abierto.**
- **Declinar es el hueco medido**, no recuperar: 21 de 21 escenarios bien anotados recuperan la
  norma correcta, y el umbral de calidad no arregla la abstención. Bloque **RHR** (revisión humana
  de respuestas) es el camino elegido.
- La comprobación de fundamento está **apagada por medición**: rechazaba 10 de 30 respuestas
  buenas. Reactivarla exige otro mecanismo, no otro número.
- Perfiles `router` y `aggregator` declarados y **sin implementar**: sus factorías lanzan
  `NotImplementedError` a propósito, para no construir un grafo que recuperaría vacío en silencio.

---

### 5.2 Política de lengua

**Qué hace.** Decide en qué lengua responde un asistente y qué versión de una norma bilingüe
prefiere.

**Garantiza.** Tres modos y sólo tres, configurables en cascada y validados al escribirse:

| Modo | Qué hace |
|---|---|
| `prefer` | Detecta la lengua de la pregunta, responde en ella y prefiere esa versión. **Es el defecto** |
| `none` | Sin política: ni detección, ni orden por lengua, ni instrucción en el prompt |
| `fixed:<código>` | Responde siempre en esa lengua, pregunten como pregunten |

- Un valor que no sea uno de los tres da **422 con los modos enumerados**. Antes era texto libre y
  un typo caía a `prefer` sin avisar a nadie.
- El panel **no escribe la lista**: la pide a `GET /api/v1/hub/opciones/lengua`.
- Los códigos que ofrece el catálogo son los **del corpus** (`val`, no `ca`). Un `fixed:ca` pasaría
  la validación de forma y daría una preferencia que no prefiere ninguna versión de ninguna norma,
  en silencio.

**Superficie.** `core/language_mode.py` · `hub_opciones_router` · `HubOrganizacion.default_language_mode`
· `HubChatbot.language_mode`.

**Madurez**: `construido` (bloque LANG, 2026-09-03; sin desplegar al escribir esto).

**Abierto.** Ningún despliegue monolingüe real lo ha usado todavía; el juicio sobre si el
castellano de una respuesta fijada suena institucional o a traducción automática está pendiente de
una persona (`pruebas_manuales/pruebas_manuales_bloqueLANG.bat`).

---

### 5.3 Corpus normativo y su ciclo de vida

**Qué hace.** Mantiene el cuerpo normativo que citan los asistentes: qué entra, en qué lengua, con
qué clasificación y hasta cuándo vale.

**Garantiza.**
- Al corpus **sólo entra `.md`** conforme a [`CONTRATO_MD_CORPUS.md`](CONTRATO_MD_CORPUS.md). La
  conversión ocurre **fuera** de la aplicación; el servidor no lleva conversor de documentos.
- Clasificación por **ámbito** y **submaterias** desde vocabulario en tabla, con `vigent` y
  `substituit_per_codi` para renombrar y fusionar sin reindexar (I3, I4).
- **Una versión por norma y lengua**; `ca` ≡ `val`; la vigencia se expresa con un eje, y la
  validación y la caducidad se comparten entre versiones.
- Reingesta **idempotente**: volver a ingerir lo mismo no duplica ni reembebe.
- Recuperación en **tres niveles** (fragmento, documento, índice), ya implementada.

**Superficie.** `agents_hub/ingestion/` · `services/retrieval/` · `HubDocument`, `HubDocumentChunk`
· `ingestion_router`, `hub_tasks_router`.

**Invariantes.** I3, I4.

**Madurez**: `producción` — corpus real de normativa propia ingerido en los cuatro asistentes.

**Abierto.**
- **Catálogo de procedimientos** (bloque **PRC**): el piloto no contesta plazos, silencio ni canal
  porque eso no está en la normativa. Bloqueado por dos prerrequisitos externos —fichas validadas
  por los servicios y una consulta de descarga que debe habilitar el equipo del catálogo—.
- El vocabulario **está pendiente de validación por Secretaría General**: va a cambiar, y por eso
  I3 y I4 no son negociables.

---

### 5.4 Curación de portales

**Qué hace.** Rastrea un portal institucional real, detecta qué ha cambiado y presenta hallazgos
para que una persona decida qué entra al corpus.

**Garantiza.**
- Rastreo con cadencia, alta automática de páginas nuevas y reingesta de las cambiadas.
- Los hallazgos se revisan **uno a uno**; nada entra al corpus sin decisión humana.
- Salvaguardas contra el vaciado: una pasada parcial no puede dar de baja el resto del portal.

**Superficie.** `modules/curation/` (`site_crawler.py`) · `curation_router` · pantallas
`/curation/*`.

**Madurez**: `producción` — el portal real de la UJI, con sus trampas inventariadas (conmutador de
idioma, http+https duplicados, la misma sección bajo dos prefijos, archivo por curso académico).

**Abierto.** Bloque **DIN**: parametrizar apartados como *secciones* dentro del proceso de
curación, con censo acotado por sección. La trampa que el bloque evita está medida:
`site_crawler.py` compara contra las páginas de **todo** el sitio, así que una pasada de sección
completa declararía baja el resto del portal.

---

### 5.5 Informes, scripts y ejecución determinista

**Qué hace.** Compone informes con tablas deterministas por plantilla y valoración de la IA sujeta
a aprobación o edición humana.

**Garantiza.**
- **Las tablas las calcula código, no el modelo.** La IA valora; no inventa cifras.
- Ningún script se ejecuta sin **auditoría AST + sandbox + aprobación** (I13).
- El formulario de un script se pinta desde un `ui_contract` que manda el servidor: el frontend no
  conoce los campos a priori (I6).
- Toda ejecución deja `RunManifest`: qué se ejecutó, con qué versión y con qué datos.

**Superficie.** `modules/redaccion/` · `redaccion_*_router` (plantillas, workspaces, scripts,
gráficos, manifiestos) · [`REDACCION_CONTRACT_FIRST.md`](REDACCION_CONTRACT_FIRST.md).

**Invariantes.** I13, I6.

**Madurez**: `construido` — utilizable de punta a punta; el caso guía es el informe de seguimiento.

**Abierto.** Bloque **FUN**, el más grande del plan: hoy el código aprobado **se incrusta copiado**
en cada plantilla (`scripts_router.py`), así que dos plantillas con la misma extracción son dos
copias y dos aprobaciones, y un bug se arregla N veces. El bloque lo convierte en catálogo
versionado con referencia `funcion_id@versión`, con **doble origen** (autoservicio y paquete por
*entry point*), y se alinea con el nivel 2 de la Instrucció 02/2026 de desarrollo ciudadano
gobernado.

---

### 5.6 Identidad, roles y multitenencia

**Qué hace.** Dice quién es cada quien, qué puede hacer y a qué organización pertenece.

**Garantiza.**
- Cuatro roles: `superadmin` (plataforma), `admin` (una organización), `informer` (valida
  respuestas), `user`.
- **La identidad de administración es `HubUser` con `role='admin'`**, con lo que varias personas
  pueden administrar la misma organización. `AdminAccount` se queda con el partner y la
  facturación. Decisión escrita en [`DECISION_IDENTIDAD_DE_ADMINISTRACION.md`](DECISION_IDENTIDAD_DE_ADMINISTRACION.md).
- **Acceso por módulos concedidos, no por roles nuevos**: `chatbots`, `curacion`, `informes`,
  `personas`, `plataforma`. El catálogo es tabla (I4). El superadmin no necesita concesión.
- Toda consulta que sirva datos de inquilino se acota con `scope_query_to_orgs`, y **la lista vacía
  significa «ninguna»** (I5, I8).
- Contraseña local para personas, con interruptor `LOCAL_USER_LOGIN_ENABLED` para apagarla cuando
  llegue el SSO. Cualquiera puede cambiar la suya, exigiendo siempre la actual.

**Superficie.** `core/auth/` (`tenancy.py`, `modulos.py`, `pat/`) · `core/ambito.py` ·
`auth_router`, `hub_users_router`, `hub_modulos_router` · `saml_auth_router`.

**Invariantes.** I5, I6, I8, I9.

**Madurez**: `producción`.

**Abierto.**
- **El SSO institucional no tiene fecha.** El mecanismo está (`resolve_role` con tres niveles,
  grupos en el claim), pero sin IdP configurado no se puede cerrar.
- **Una persona administrando varias organizaciones** no es representable hoy: `organizacion_id`
  es una columna. El camino está escrito (tabla puente que la sustituya), y nadie lo pide aún.
- **Cuatro tablas de identidad sin unificar** (`SuperAdminAccount`, `AdminAccount`,
  `ClientAccount`, `HubUser`). Merece bloque propio con inventario delante; es la parte con riesgo
  real.

---

### 5.7 Administración de plataforma y cascada de configuración

**Qué hace.** Permite configurar la plataforma sin acceso a la base de datos, que es lo que no se
le puede pedir a otra administración que despliegue esto.

**Garantiza.**
- Cascada **plataforma → organización → chatbot → configuración efectiva**. En una tabla
  `heredable`, **nulo significa «hereda de plataforma»**, y se puede **volver a heredar** por API.
- `core/auth/tenancy.py` decide **quién puede ver qué**; `core/ambito.py` decide **qué fila gana**.
  Son dos capas y no se confunden.
- El panel ofrece siempre lo que el contrato declara (I7), y las acciones que el servidor concede
  (I6).

**Superficie.** `hub_organizaciones_router` (valores por defecto), `hub_llm_configs_router`,
`hub_prompts_catalog_router`, `hub_themes_router`, `hub_opciones_router` · pantallas
`/plataforma/*`.

**Madurez**: `producción`.

**Abierto.** Bloque **PLG**: los perfiles de grafo son un `Enum` cerrado, así que **un perfil de
terceros no cabe por construcción** —contradice I4—, y las estrategias no son seleccionables por
configuración. El bloque las abre por *entry points*, con el núcleo entrando por el mismo
mecanismo, y declara los protocolos **inestables (0.x)** a propósito: han cambiado dos veces en un
mes por medición, y congelarlos hoy sería congelar errores conocidos.

---

### 5.8 Publicación, despliegue y operación

**Qué hace.** Sirve lo público en un dominio institucional y despliega sin intervención manual.

**Garantiza.**
- Reparto de rutas en un solo fragmento de Caddy: `/` portada del corpus, `/cercador` y
  `/gerencia` los buscadores, `/html/<norma>.html#art-63` sin cambiar de forma, `/api/*` y
  `/health` la aplicación, `/panel/` el panel y su login.
- **El despliegue sólo dispara con `push` a `main`.** El trabajo va en `desarrollo`; CI y DCO
  corren en las dos ramas.
- Las migraciones se aplican **antes** de cambiar la imagen, con `alembic current` en el log, y hay
  vuelta atrás si el servicio no responde.
- **Portabilidad**: el DSN por variable de entorno y los ficheros por `fsspec` (I11), así que el
  mismo código sirve en GCP, en MinIO local o en AWS cambiando variables.

**Superficie.** `deploy/vm/Caddyfile` · `.github/workflows/ci.yml`, `.github/workflows/deploy.yml` y `.github/workflows/dco.yml` ·
[`DESPLIEGUE_PROTOTIPO_GCP.md`](DESPLIEGUE_PROTOTIPO_GCP.md).

**Madurez**: `producción` — sirviendo desde el 2026-08-31; dominio institucional desde el
2026-09-02.

**Abierto.**
- El certificado caduca el **19-03-2027** y no se renueva solo.
- **Dominio y sitio de corpus por organización**: hoy es un despliegue, un dominio, un sitio
  (`CORPUS_SITE_BASE_URL` es global). Sería una columna anulable con la cascada existente.
- La pila local de `torch` se paga entera en memoria y arranque aunque se usen embeddings por API;
  hacerla extra opcional está anotado como candidato, no hecho. **El modo edge sigue
  necesitándola**, así que puede volverse opcional pero no desaparecer.

---

## 6. Fase 2 — Automatización documental

**Propósito.** Llevar la automatización de AutomatIA al servidor: extracción de documentos,
puentes semánticos, fábricas como nodos de LangGraph y el sandbox distribuido edge ↔ *thin client*.

**Lo que ya está especificado** en `planificacion/Plan_TDD_Fase2.md`: extracción con estrategias
enchufables, `RunManifest` + `AuditService` + registro unificado de scripts, principio
**determinista-first** (las fábricas son nodos del grafo, no llamadas al modelo), y puentes
semánticos multicontexto.

**Lo que está diferido a propósito.** RPA web: se movió a v2 porque exige navegador en el edge y su
superficie de riesgo es de otro orden.

**Madurez**: `previsto`. Partes ya construidas en Fase 1 —el sandbox, la auditoría AST, el
`RunManifest`, la extracción con `pdfplumber`— y **no hay que reimplementarlas**: el plan lo dice
explícitamente en su sección de reutilización.

**Lo que hay que decidir antes de ejecutar.** La frontera exacta entre `modules/automation/` y
`modules/redaccion/`: hoy comparten la idea de «ejecutar algo determinista sobre un documento» y
dos catálogos de scripts sería el defecto de FUN otra vez, un nivel más arriba.

---

## 7. Fase 3 — Expedientes y malla agéntica

**Propósito.** Gestor de expedientes integrado por MCP, agente analista sobre base vectorial de
normativa, adaptadores institucionales (Gestión 400, capa ENI/ENS) y el **edge node híbrido**.

**Garantías que la fase debe cumplir**, ya escritas y que condicionan el diseño de Fase 1:

- **HATEOAS estricto en expedientes**: el frontend **nunca** calcula qué acciones caben. El backend
  es la máquina de estado y devuelve `acciones_permitidas` evaluando fase, estado y rol (I6). Un
  usuario sin permisos recibe un array vacío.
- **El cloud orquesta, el edge ejecuta**: cualquier ejecución determinista orquestada por el grafo
  se delega al edge node por WebSocket. No es una optimización, es el requisito regulatorio.
- **Las fases de expediente referencian `plantilla@versión` y `función@versión`**, nunca código
  incrustado. Esta restricción se escribió el mismo día que el bloque FUN y por eso se retiró
  `ejecuciones_accion.codigo_ejecutado`, que duplicaba sandbox, auditoría y aprobación.

**Madurez**: `previsto`. Prerrequisito externo: la integración con sistemas institucionales
(G400, ENI) no se puede simular en local.

**Lo que aún no tiene TDD desarrollado**: la subfase 3.B entera. Está enumerada, no especificada.

---

## 8. Lo pendiente, y por qué está donde está

El detalle vivo —qué bloque, qué prompt, qué modelo sugerido— está en
[`PROJECT_STATE.md`](../planificacion/PROJECT_STATE.md), que es la fuente de verdad del progreso.
Aquí sólo el mapa, para que quien llegue sepa dónde puede aportar:

| Bloque | Qué resuelve | Depende de |
|---|---|---|
| **REG** | La plataforma como registro de actividad IA, con API y MCP remoto | Nada; ya desplegado el servidor |
| **VAS** | Verificaciones como servicio: citas, vigencia y auditoría de código por API | REG (scopes y evento) |
| **NIC** | Retirada del legacy NiceGUI, con inventario delante | Nada |
| **REPO** | Repositorio limpio, sin objetos huérfanos. **Ventana: antes del primer fork** | Después de NIC |
| **PLG** | Perfiles y estrategias por *entry points* | Después de LANG (misma factoría) |
| **DIN** | Secciones parametrizables y ciclo de vida de la ingesta | Nada |
| **FUN** | Catálogo de funciones deterministas versionadas | FUN.6 necesita REG |
| **RHR** | Revisión humana de respuestas — **el hueco medido de la abstención** | Anotación por lotes |
| **PRC** | El catálogo de procedimientos en el asistente | **Bloqueado**: fichas validadas + consulta de descarga |

**Los mejores puntos de entrada para alguien de fuera**, por criterio de alcance cerrado y riesgo
bajo: **VAS** (los tres candidatos ya existen como función interna y sólo necesitan superficie) y
**DIN** (independiente de todo, y su premisa resultó falsa en dos tercios, así que hay menos por
construir de lo que parece).

---

## 9. Cómo se prueba lo que aquí se afirma

**TDD obligatorio**: el test antes del código de producción. Y una jerarquía deliberada:

| Nivel | Qué corre | Cuándo |
|---|---|---|
| Ficheros de test tocados | segundos | durante el desarrollo |
| Directorios tocados + `tests/infra/test_suite_hygiene.py` | segundos a 1 min | al cerrar un cambio |
| `uv run pytest tests` completo | 15-100 min | al cerrar un bloque |

**Guardarraíles que hacen cumplir los invariantes**, y que son la parte de la suite que más protege
a quien llega de fuera:

- `tests/api/test_router_inventory_is_walked.py` — I8 e I9: ningún router sirve datos sin acotar ni
  declara un módulo que no exige.
- `tests/api/test_tenant_isolation.py` y `test_mt16_aislamiento_dos_organizaciones.py` — I5.
- `tests/core/test_mt7_el_inventario_esta_escrito.py` — el inventario de multitenencia no puede
  quedarse viejo.
- `tests/infra/test_suite_hygiene.py` — mocks sobre clases, `create_all` sobre la base del
  desarrollador, imports a módulos que ya no existen.
- El guardarraíl de I10 en `test_usr8_el_flujo_del_chat_siempre_termina.py`.
- `test_profile_contract.py` — todo perfil que no esté declarado sin configurar tiene que compilar
  y ejecutar.
- Gate de regresión de recuperación: falla si `recall@5`, `recall@10` o `MRR` bajan más de 0,02
  respecto a la línea base versionada.

**Dos trampas del entorno que cuestan una tarde si nadie las dice:**

- La suite se ejecuta **desde Git Bash**, no desde PowerShell: `test_setup_script.py` invoca `bash`,
  que en PowerShell resuelve al lanzador de WSL y da diez rojos de entorno.
- **CI corre con `-n0` a propósito.** El paralelismo esconde el estado filtrado entre tests, que es
  justo lo que se quiere cazar. En local manda la velocidad; en CI, la detección.

**Y una lección del proyecto que conviene leer antes de reportar un hallazgo**: en varias ocasiones
una cifra extrema resultó ser un defecto del instrumento y no del sistema, y un guardarraíl llegó a
pasar en verde **recorriendo un directorio inexistente**. Ante un 0, un 100 % o un verde
sospechoso, primero se comprueba que el test mide lo que dice medir.

---

## 10. Qué NO hace la plataforma

Límites deliberados. Están aquí para que nadie los implemente por iniciativa propia creyendo que
faltan:

- **No da asesoramiento jurídico.** Informa citando la norma; la interpretación es de quien tiene
  competencia.
- **No decide.** La IA propone y valora; aprobar es de una persona, y eso es estructural.
- **No genera código de motor en runtime.** Se descartó explícitamente: las estrategias son
  enchufes y los perfiles colecciones, pero el código llega por instalación, no por formulario.
- **No comparte corpus entre chatbots.** Está decidido y no hay que volver a proponerlo.
- **No lleva conversor de documentos en el servidor.** Al corpus entra `.md` conforme al contrato;
  si algo hay que convertir, se convierte antes de llegar.
- **No hay shims de compatibilidad.** Si una ruta o un símbolo se retira, se retira: el historial
  de git es la fuente de verdad del pasado.

---

## 11. Cómo mantener este documento honesto

Un documento de especificaciones que envejece es peor que no tenerlo, porque miente con autoridad.
Tres mecanismos, en orden de fuerza:

1. **Un test lo comprueba**: `server/tests/infra/test_especificaciones_no_miente.py`. Verifica
   que todos los ficheros y tests que este documento nombra existen, y que los vocabularios que
   enumera —los cuatro ámbitos, los cuatro roles, los tres modos de lengua, los módulos del
   catálogo, los modos de recuperación, los módulos de negocio— son **exactamente** los que el
   código declara. Un valor nuevo o renombrado pone la suite roja, y entonces alguien actualiza
   la única página donde esto se puede consultar. Es el patrón de
   `test_mt7_el_inventario_esta_escrito.py`, y es lo que convierte este documento en verdad
   comprobable en vez de en una foto vieja.

   **Lo que el test no comprueba es la prosa**, y eso hay que decirlo: puede garantizar que
   `enforce_citation_contract` existe, no que siga rindiéndose sin cita. Para eso están los
   tests de cada capacidad, que §9 enumera.
2. **La regla de qué va aquí.** Si un cambio altera lo que el sistema **garantiza**, se actualiza
   este documento en el mismo *commit*. Si sólo altera **el estado del desarrollo**, no se toca:
   eso es `PROJECT_STATE.md`.
3. **Nada de fechas incrustadas** salvo las que son un hecho (un certificado que caduca, una
   medición). La madurez se expresa en cuatro palabras, no con un porcentaje que hay que revisar.

---

## 12. Glosario

| Término | Qué es |
|---|---|
| **Organización** | El inquilino: una universidad, una diputación, un ayuntamiento. `HubOrganizacion` |
| **Partner** | Quien despliega y factura. Puede tener varias organizaciones |
| **Ámbito** (`__ambito__`) | De qué nivel es una tabla: `plataforma`, `organizacion`, `heredable` o `derivada` |
| **Cascada** | Plataforma → organización → chatbot → configuración efectiva. Nulo hereda |
| **Perfil de grafo** | Qué composición de estrategias monta un asistente (`PUBLIC_KB_RICH`…) |
| **Estrategia** | Un enchufe por eje: recuperación, fusión, plantilla, lengua |
| **Modo de recuperación** | `RAG`, `MD_LONG_CONTEXT` o `MD_AGENT_SELECTOR` |
| **Edge node** | Despliegue en la nube del cliente que ejecuta lo operacional |
| **Curación** | Decidir qué contenido de un portal entra al corpus, y cuándo |
| **`RunManifest`** | El registro de qué se ejecutó, con qué versión y sobre qué datos |
| **Bloque** | Unidad de trabajo del plan: una fila de la tabla de `PROJECT_STATE.md` |

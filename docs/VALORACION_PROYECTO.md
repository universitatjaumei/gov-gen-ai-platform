# Valoración del proyecto — Gov Gen AI Platform

> Informe de valoración global: estado de la Fase 1, calidad del desarrollo, seguridad,
> sentido del producto y análisis de la planificación pendiente (Fases 2 y 3).
> Fecha: 2026-07-11. Basado en `PROJECT_STATE.md`, los tres planes TDD, `Arquitectura.md`,
> `PLAN_DESARROLLO.md`, los documentos de cambios y una auditoría del código actual
> (backend, frontend y seguridad).

---

## 1. Resumen ejecutivo

El proyecto está en un estado **notablemente maduro para un desarrollo en solitario**: la
Fase 1 está funcionalmente completa salvo dos bloques (Autoinstalación y Deploy GCP), con
~943 tests backend y ~209 tests frontend en verde, disciplina TDD real, contrato OpenAPI +
Orval operativo, frontera edge/cloud implementada en código (no solo en papel) y bloques
avanzados que no estaban en el plan original (SSO SAML, PAT, servidor MCP, calidad de
contenido web, sandbox de scripts).

Las dos conclusiones principales de esta valoración son:

1. **La seguridad es el bloqueante real antes de cualquier despliegue**, no la
   funcionalidad pendiente. Se han encontrado dos fallos graves (login de partner sin
   contraseña y ausencia de aislamiento multi-tenant en los endpoints) que invalidan la
   promesa central de la plataforma —multi-tenancy para administraciones públicas— hasta
   que se corrijan. Recomiendo insertar un **Bloque SEC** de endurecimiento entre el
   cursor actual (11.1) y el Deploy GCP.

2. **La planificación de Fases 2 y 3 es sólida en diseño pero optimista en volumen**:
   `client_app/` conserva 489 ficheros Python (~6,2 MB) sin migrar, mientras el plan de
   Fase 2 enumera explícitamente solo una fracción. Conviene hacer un inventario de
   migración medible antes de arrancar la Fase 2 y decidir de forma definitiva la
   nomenclatura de roles (SuperAdmin/Admin/Organización), que la documentación da por
   aplicada pero el código no refleja.

---

## 2. Fase 1 — Qué se ha construido y valoración

### 2.1 Completado (según PROJECT_STATE.md, verificado contra el código)

| Bloque | Contenido | Valoración |
|---|---|---|
| 9B — Chatbots públicos | RAG híbrido, LangGraph, chat SSE, widget embebible, spiders | Núcleo del MVP, operativo |
| 9R — Redacción Contract-First | `ReportTemplateSpec`, SDUI, DraftingCoreGraph, pipelines | El mejor código del proyecto: SDUI real con Zod dinámico y tests de contrato |
| Fase 10 — Temas | Cascada Plataforma→Cliente→Chatbot, presets, editor | Completo |
| 1C — Privacidad/Export | Exportación DOCX, políticas | Completo con salvedad (§4, anonimización no persiste el mapa) |
| Fase 13 — NER reversible | Hook pre/post-LLM en redacción | Completo (motor); Vault Edge queda para F2.A |
| Fase 20 — WCAG | 9/9 tests a11y, gate CI, checklist | Buen nivel para esta etapa |
| SBX — Sandbox scripts | Microservicio aislado (read-only, cap_drop ALL, no-root) | Bien endurecido; referencia a seguir |
| 9Q — Calidad contenido web | Crawler, detectores, RAG consciente de calidad, informes | Diferenciador de producto valioso |
| AUTH — SAML + PAT | SP SAML 2.0 (python3-saml), provisioning JIT, PAT con scopes | Implementación correcta (sha256, compare_digest, revocación) |
| MCP — Servidor stdio | 16 tools + 5 resources, gating HITL con `confirm`/`dry_run` | Muy bien diseñado (paquete aislado, 0 imports de server/app) |

### 2.2 Pendiente dentro de Fase 1

- **Fase 11 — Autoinstalación** (cursor actual: 11.1): generador `.env`, compose de
  producción, init script. Prerrequisito de la distribución como software libre.
- **Deploy GCP (D.1–D.5)**: primer despliegue real.
- **Bloque ING — Ingesta multi-formato** (backlog, bloqueado por la curación del corpus
  de normativa por parte del usuario). Ojo: sin este bloque el piloto no tiene su corpus
  real de ~300 documentos; es backlog en el plan pero es **crítico para el valor del
  piloto**. La Fase 0 (script de carga masiva) es barata y desbloquea todo.

### 2.3 Divergencias documentación ↔ código detectadas

1. **Nomenclatura de roles no aplicada.** `Arquitectura.md` §5 y `PLAN_DESARROLLO.md`
   ("refactor de nomenclatura aplicado en Fase 1") dan por hecho el renombrado
   Partner→Admin, Client→Organización. El código sigue usando `PartnerAccount`,
   `HubClient` y roles `admin`/`partner`. No es un problema en sí, pero **hay que decidir
   ya**: o se ejecuta el renombrado (Bloque 2 de `CAMBIOS_ARQUITECTURA.md`) antes de la
   Fase 2 —cuando el coste es mínimo—, o se actualiza la documentación para reflejar la
   nomenclatura real. Renombrar después de construir Expedientes (Fase 3, que introduce
   `responsable_rol` por todas partes) multiplicará el coste.
2. **`frontend/src/agent/` no existe** y `frontend/src/automation/` son carpetas vacías;
   en cambio existe `frontend/src/redaccion/` (el módulo más desarrollado) que no figura
   en el mapa de módulos de `CLAUDE.md`. Actualizar `CLAUDE.md` evita que futuros agentes
   de programación coloquen código en el sitio equivocado.
3. **OIDC no existe**; solo SAML. Los planes de F3 citan "Auth OIDC/SAML" como
   prerrequisito — con SAML+JWT es suficiente, pero conviene ajustar el texto.

---

## 3. Calidad del desarrollo

### 3.1 Fortalezas

- **Frontera edge/cloud real**: `DEPLOY_MODE` con `_register_cloud`/`_register_edge`,
  routers etiquetados, doble `DeclarativeBase` (`HubConfigBase`/`HubOperationalBase`) sin
  ningún `relationship()` cross-base, y tests de frontera (`test_deploy_mode`,
  `edge_boundary`). Es raro ver esta disciplina mantenida durante 60+ prompts.
- **Contract-First operativo**: OpenAPI exportado (109 paths), Orval con `tags-split`,
  SDUI en redacción verificado por tests ("el test falla si busca un campo hardcodeado").
- **StorageService/fsspec bien diseñado** (Protocol + `asyncio.to_thread`), portable a GCS.
- **Suite de tests amplia**: ~943 backend + ~209 frontend + a11y con axe-core, con
  separación unit/integration/e2e.

### 3.2 Problemas principales (backend)

1. **`api/v1/automation.py` (1.189 LOC, 19 endpoints) instancia `AIBrainService()` a mano
   en ~18 endpoints y llama a métodos privados** (`_validate_license`,
   `_resolve_server_config`) a través de la frontera HTTP. Viola las dos reglas de
   `CLAUDE.md` (DI obligatoria; sin acceso a internos). Además **este router y
   `telemetry_router` no están registrados en `main.py`**: son 1.200+ líneas de
   superficie muerta. Decisión pendiente: registrarlos como edge (la tabla de CLAUDE.md
   dice que `/automation/*` es edge) tras refactorizarlos, o retirarlos hasta la Fase 2.
2. **`server/app/ui/` contiene 21 ficheros NiceGUI** (p. ej. `admin_security.py`, 1.035
   LOC) dentro del árbol activo del servidor, sin importadores, pero con tests
   (`test_admin_*_ui.py`) que los mantienen vivos. Según las propias reglas del proyecto
   deberían ir a `_legacy_nicegui/` (o borrarse, Caso B) junto con sus tests.
3. **`AIBrainService` monolítico (1.082 LOC)** con responsabilidades mezcladas (RPA,
   visión, generación de scripts, forensics) y prácticamente sin tests funcionales. Igual
   `cortex.py` y `extraction_strategies.py` (767 LOC). Este código es justo el que la
   Fase 2 va a tocar: partir el servicio ANTES de migrar la UI sobre él ahorrará dolor.
4. **Shims prohibidos por CLAUDE.md**: `init_db = init_server_db` (`db.py:31-32`) y alias
   "legacy" en `seeds.py:174-176`. Menor, pero contradice la norma "borra, no comentes".
5. **Bloqueo del event loop**: `subprocess.run(["libreoffice", ...])` síncrono dentro de
   `async def to_pdf` (`report_exporter.py:84`); envolver en `asyncio.to_thread`. Nota
   adicional: LibreOffice no existirá en Cloud Run — la degradación a DOCX ya prevista
   será el camino real; considerar un microservicio de conversión si el PDF importa.
6. **Higiene menor**: `print()` como logging en `ai_brain.py`/`main.py` (sin logging
   estructurado), fallback de `DATABASE_URL` con credenciales en `db.py:15`,
   `create_all` en el lifespan en lugar de confiar solo en Alembic, ~99 `except Exception`
   con algunos swallows silenciosos (scheduler de calidad incluido), y scripts ad-hoc
   sueltos en `tests/` (`reproduce_client_id.py`).

### 3.3 Problemas principales (frontend)

1. **Capa API manual paralela a Orval**: `shared/api/{ingestion,clients,feedback,llmConfigs,promptTemplates}.ts`
   con `fetch` crudo, `API_BASE` hardcodeado a `localhost:8000`, tipos escritos a mano
   (`IngestionJob`, `HubDocument`) y un `// TODO CF.4: migrar` literal. Es la principal
   violación de la regla Contract-First y afecta a la página más grande
   (`DocumentsPage.tsx`). Migrar estos 5 módulos a hooks Orval debería ser un prompt
   propio antes de seguir añadiendo pantallas.
2. **Lógica de autorización replicada en cliente**: `AccessTokensPage.tsx:25-28` calcula
   scopes con `if (role === 'admin')` ("espejo del backend"). Contradice la regla
   HATEOAS del proyecto; el backend debería servir los scopes permitidos.
3. **Strings hardcodeados en español** en `LLMConfigsPage` (~22), `ChatbotsPage` (~12),
   `DocumentsPage` (constantes con etiquetas), pese al mandato i18n. Y el **catalán del
   namespace admin está al ~25 %** (34 líneas vs 130 es/en) — relevante siendo la UJI el
   piloto.
4. **Componentes gigantes**: `DocumentsPage.tsx` 1.019 líneas (upload + fuentes + spiders
   + jobs en un componente). Descomponer antes de que el Bloque ING Fase 3 lo haga crecer.
5. **Bundle admin monolítico de ~927 KB** sin code-splitting (imports estáticos en
   `App.tsx`, sin `React.lazy`). Barato de arreglar con lazy routes.
6. **Widget**: errores silenciosos en `useChat.ts` (fallo de red = mensaje vacío sin
   aviso), sin Shadow DOM (los estilos del host pueden romper el widget), input sin
   `aria-label`. El feedback hace POST sin cabecera de autorización contra un endpoint
   que exige auth — o está roto o acabará abierto; alinear (ver §4, M-widget).

---

## 4. Seguridad — hallazgos priorizados

> La base es mejor que la media (bcrypt, PAT correcto, ORM parametrizado, DOMPurify,
> JWT sin secreto por defecto, sandbox de scripts ejemplar), pero hay dos fallos que
> **deben corregirse antes de cualquier despliegue con datos reales**.

### Críticos (bloqueantes de despliegue)

- **A1 — Login de partner sin contraseña.** `auth_router.py:59-82`: `login_partner` emite
  JWT comprobando solo que el partner existe y está activo; `PartnerAccount` ni siquiera
  tiene campo de contraseña. Conocer un email de partner basta para obtener un token de
  rol `partner`. Corregir (hash bcrypt como en admin) o deshabilitar el endpoint y forzar
  SAML/PAT.
- **A2 — Sin aislamiento multi-tenant.** El JWT (`UserInfo`) no lleva `partner_id`/
  `client_id`, y los endpoints no filtran por tenant: `list_chatbots` devuelve todos los
  chatbots de todos los clientes; update/delete/corpus-stats operan sobre cualquier
  `chatbot_id`; `hub_feedback` permite a un partner leer conversaciones (posible PII
  ciudadana) de otro; `hub_themes` filtra por un `client_id` que envía el propio cliente.
  Mitigación: claims de tenant en el token + filtro obligatorio en una capa de
  repositorio común + **test de regresión de aislamiento como gate de CI** (un partner A
  no puede leer/escribir recursos del partner B).
- **A3 — Secretos vivos en `.env` del árbol de trabajo**: `GOOGLE_API_KEY`,
  `OPENROUTER_API_KEY` y la clave RSA privada de firma de scripts. No está en git (bien),
  pero deben **rotarse** y pasar a un gestor de secretos; verificar el historial
  (`git log --all -- .env`). La clave de firma debe regenerarse.

### Altos

- **A4 — CORS `allow_origins=["*"]`** sin distinción por entorno (`main.py:190-196`).
- **A5 — Sin rate limiting** en login, chat (coste LLM) e ingesta. Para un chatbot
  público esto es además control de coste: cuotas por chatbot/IP son imprescindibles
  antes del piloto.

### Medios

- **Widget**: el token bearer va en `data-token` visible en el HTML del host y es
  reutilizable contra toda la API (agravado por A2); el scope usado es `chat:test`.
  Diseñar **tokens efímeros por dominio y chatbot** con scope `chat:public` (el plan de
  Deploy ya menciona `data-api-key` en D.1 — adelantar su diseño).
- **Temas**: `GET /hub/themes/{theme_id}` sin auth y `theme_id` sin validar usado para
  construir rutas de fichero (posible traversal; el DELETE hace `unlink`). Validar como
  UUID + `resolve()` bajo `THEMES_DIR`.
- **Chat**: mensajes y respuestas se persisten en claro y van a Langfuse con `user_id`;
  no hay minimización de PII en el flujo de chat (la decisión 12 excluye el chatbot
  público de la anonimización, pero conviene política de retención y aviso, y valorar
  detección básica de PII en logs).
- **Uploads**: validación solo por `content-type` (spoofeable) y `file.read()` sin límite
  de tamaño → DoS de memoria. El propio análisis del Bloque ING ya prevé validación por
  magic bytes compartida: adelantarla.
- **Prompt injection indirecta vía RAG**: contenido crawleado se inyecta sin delimitación
  de confianza. Delimitar el contexto como no confiable y reforzar `citation_validator`.
- **Docs FastAPI expuestas** y sin cabeceras de seguridad (HSTS, X-Frame-Options/CSP).
- **Anonimización sin persistencia del mapa** (`anonymization/service.py:232,236`, no-op
  MVP): la reversibilidad prometida no sobrevive a la sesión; enlazar con Vault Edge (F2.A.4).

### Bajos

Defaults débiles en `docker-compose.yml` (minioadmin, `admin123`, `ENCRYPTION_KEY` de
ceros con `${VAR:-default}`), JWT sin revocación (valorar `jti` + denylist o refresh
cortos; recordar volver `JWT_EXPIRATION_MINUTES` a 60 en prod), PAT sin caducidad máxima.

**Recomendación concreta: crear un Bloque SEC (6–8 prompts TDD) e insertarlo entre 11.x y
D.1**, con este orden: A1 → A2 (+test de aislamiento en CI) → A3 (rotación) → A5/A4 →
token de widget → uploads/headers/docs. El Deploy GCP sin esto publicaría los fallos.

---

## 5. Valoración de la planificación pendiente

### 5.1 Fase 2 — Automatización, Thin Client y migración NiceGUI

**Lo que está bien planteado:**

- La **Guía 9C.0** (tabla de clasificación NiceGUI→FastAPI/React + checklist de cierre)
  es excelente: convierte cada migración en un procedimiento repetible.
- La secuencia del extractor PDF (9.12b.0 auditoría → 9.12b backend → 9.13 UI, con la
  Guía 9C.1 de 12 pasos bloqueantes) gestiona bien el riesgo de la migración más densa
  (2.370 líneas). El aviso de que 9.12b quedó casi vacío tras 9R.5.9 demuestra que el
  plan se mantiene vivo.
- El patrón GitLab Runner para el Thin Client y la separación firma-en-Edge /
  ejecución-en-local (FASE 14) son la decisión arquitectónica correcta.
- Diferir RPA web (FASE 21) y microservicios (FASE 22 con criterios de activación
  medibles) es buena disciplina anti-sobreingeniería.

**Riesgos y mejoras propuestas:**

1. **Volumen infraestimado.** El plan enumera ~5.000 LOC de servicios legacy a migrar,
   pero `client_app/` tiene 489 ficheros (~6,2 MB). Antes de arrancar F2, generar un
   **inventario de migración** (fichero → destino → fase → LOC) y añadirlo a
   `PROJECT_STATE.md`; lo que no tenga destino es Caso B (borrar). Sin inventario, el
   "criterio de éxito 2.B" (client_app/app/ui vacío) no es verificable de forma incremental.
2. **Prerrequisito de calidad**: refactorizar `AIBrainService`/`automation.py` (DI,
   partición, registro del router) como prompt 0 de la Fase 2, antes de construir UI
   React encima. Migrar UI sobre un backend que viola DI consolida el problema.
3. **FASE 14/15/16/18 sin TDD detallado** (reconocido en el plan). El prompt 2A.2
   (Secure Pairing) debe considerarse **bloqueante de 9.16 en producción**, no opcional:
   un thin client que ejecuta scripts con un `AGENT_TOKEN` estático de `.env` reproduce a
   escala local el problema A1. Diseñar el enrolment de un solo uso desde el principio.
4. **El esqueleto de 9.16** (`websockets.connect` en bucle simple) necesita reconexión
   con backoff, heartbeat y cola de jobs pendientes; conviene decirlo en el prompt para
   que el agente no entregue el happy path.
5. **Dependencia cruzada**: 2C.0 (MCP Client) es prerrequisito bloqueante de la Fase 3
   (adaptadores) — está bien señalado; sugiero moverlo al principio de 2.C para
   des-arriesgar F3.
6. La decisión de Zustand para Focus Mode (9.12a) está bien justificada; nótese que
   `CAMBIOS_PLANIFICACION.md` lo reubicaba en `frontend/src/shared/layout/` como
   infraestructura transversal — el plan de F2 aún lo sitúa en `src/automation/state/`;
   unificar antes de implementar.

### 5.2 Fase 3 — Gestor de Expedientes

**Lo que está bien planteado:**

- Las **directrices HATEOAS** (acciones_permitidas calculadas en servidor, tests RED que
  prohíben `if (fase === ...)` en el frontend) son exactamente la lección aprendida del
  hallazgo 3.3.2 de este informe — aplicarlas retroactivamente a AccessTokensPage.
- La cadena de auditoría SHA-256 encadenada (E3), los Snapshots con `as_of_date` (3B.5,
  fundamentación jurídica Ley 39/2015 impecable) y el Fairness Audit (3B.6, RIA Art. 13)
  son diferenciadores regulatorios reales frente a cualquier alternativa comercial.
- Exponer los sistemas legacy (UJI, G400) como **servidores MCP** aísla bien la
  plataforma; la experiencia ya ganada con el Bloque MCP de F1 reduce el riesgo.

**Riesgos y mejoras propuestas:**

1. **El multi-tenant roto (A2) es incompatible con expedientes.** Los expedientes
   contienen datos personales sensibles; llegar a F3 sin aislamiento por Organización y
   sin claims de tenant en el token sería inaceptable. Otro motivo para el Bloque SEC.
2. **Checkpointing LangGraph**: E2 propone tabla propia `langgraph_checkpoints`; valorar
   `langgraph-checkpoint-postgres` oficial antes de implementarlo a mano (menos código,
   compatibilidad con `interrupt`/resume de NodoHuman).
3. **El log "inmutable"** de `audit_expediente` se protege solo por ausencia de endpoints
   UPDATE/DELETE; para valor probatorio real, añadir además privilegios de BD (rol de app
   sin UPDATE/DELETE sobre esa tabla) y/o anclaje periódico del hash de cabeza.
4. **E4 (frontend, 3 semanas) depende de "OIDC/SAML activo"** — ya cubierto por el
   Bloque AUTH, actualizar el prerrequisito.
5. La capa **ENI/ENS (E5)** es la de mayor incertidumbre externa (DIR3, eEMGDE, CSV,
   validación XSD): recomendo un spike temprano de acceso real a las APIs de UJI y G400
   (credenciales, entornos de prueba) al inicio de F3, no al final, porque el riesgo no
   es de código sino de dependencia institucional.
6. **3B.6 Fairness**: el test propuesto (umbral 0.7) es un buen inicio, pero definir qué
   metadatos de colectivo se capturan (y su base jurídica RGPD para capturarlos) antes de
   implementar el scorer; de lo contrario el dashboard no tendrá datos que agrupar.

### 5.3 Cambios propuestos en CAMBIOS_ARQUITECTURA.md — estado

| Bloque | Estado real | Recomendación |
|---|---|---|
| 1. Filosofía Hermes (Skill Library, SkillExtractor, memoria de estilo) | Recogido en Arquitectura §2.4/§3.4 y en F2.C.3/2.C.7; no implementado | Mantener en F2.C; activar cache semántico solo con métricas (como ya prevé el plan) |
| 2. Renombrado de roles | **No aplicado en código**; sí en documentación | Decidir antes de F2 (ver §2.3) |
| 3. Delimitación Cloud/Local de ejecución | Invariantes documentados en ambos planes (2.C nota, 3C.0) | Correcto; convertir el invariante en test automático cuando exista el Thin Client |
| 4. Anonimización selectiva por políticas | Modelado previsto (1C.2); motor NER migrado; **vault/persistencia del mapa pendiente** | Cerrar la persistencia cifrada del mapa en F2.A.4; hasta entonces documentar la limitación |
| 5. Spider Skills modulares | Parcialmente cubierto por 9Q (sites/selecciones); el registro `BaseSpiderSkill`+`SpiderRegistry` como tal no existe | Reevaluar si sigue siendo necesario tras 9Q o si se funde con el Bloque ING |

---

## 6. Sentido y utilidad del producto

**La propuesta de valor es sólida y está bien diferenciada** para el nicho de
administraciones públicas españolas:

- Chatbots RAG multilingües (CA/ES/EN) con **citas trazables** — la trazabilidad es lo
  que separa un chatbot institucional defendible de un juguete.
- Redacción asistida con contrato SDUI, anonimización y exportación editable — encaja con
  el flujo real del empleado público (revisar en Word/Drive, no en la plataforma).
- Expedientes con HITL, explicabilidad y auditoría encadenada — el enfoque RIA/ENS/ENI es
  una barrera de entrada frente a competidores genéricos y el argumento de venta a
  cualquier AAPP.
- Soberanía del dato (edge/cloud, vault en Edge, determinista-first) — coherente con el
  requisito regulatorio y creíble porque la frontera ya existe en código.
- Dual-license AGPLv3 — apropiado para subvención y adopción institucional.

**Sugerencias de producto** (más allá del código):

1. **Priorizar el corpus real (Bloque ING Fase 0) por encima de casi todo lo demás no-SEC**:
   un piloto con la normativa UJI real ingerida vale más que cualquier feature nueva, y
   la Fase 0 (script de carga) es un día de trabajo una vez curada la carpeta.
2. **Métricas de calidad visibles desde el día 1 del piloto**: RAGAS ya existe; añadir un
   panel simple de "tasa de respuesta con cita válida / feedback medio / preguntas sin
   respuesta" dará el argumento cuantitativo para la fase de difusión (paper, agosto 2026).
3. **Kit de adopción**: cuando se abra el repo (AGPLv3, sept. 2026), la Fase 11 debería
   incluir además un `INSTALL.md` de 15 minutos y un chatbot demo con corpus público de
   ejemplo; la barrera de adopción de otras instituciones será la instalación, no la
   funcionalidad.
4. **Retención y aviso legal del chat público**: definir política de retención de
   `HubInteraction` y texto informativo RGPD en el widget antes del piloto.
5. El roadmap (piloto sept. 2026, F2 en 2027, F3 en 2027-28) es realista **si** la Fase 2
   se acota con el inventario de migración; el patrón observado en F1 (63 prompts frente
   a 55 planificados, con bloques nuevos insertados) sugiere reservar ~20 % de margen.

---

## 7. Plan de acción recomendado (priorizado)

**Inmediato (antes de continuar con 11.1):**
1. Corregir **A1** (login partner) — medio día, riesgo crítico.
2. Rotar credenciales del `.env` y regenerar la clave RSA de firma (**A3**).

**Bloque SEC (nuevo, entre Fase 11 y Deploy GCP):**
3. Claims de tenant en JWT + filtrado obligatorio por tenant + test de aislamiento en CI (**A2**).
4. Rate limiting + cuotas LLM por chatbot (**A5**); CORS por entorno (**A4**).
5. Token efímero de widget por dominio/chatbot (`chat:public`), alineado con D.1.
6. Uploads (magic bytes + límite de tamaño), auth y validación en `GET /hub/themes/{id}`,
   docs off en prod + cabeceras de seguridad.

**Deuda de calidad (intercalable, prompts pequeños):**
7. Retirar `server/app/ui/` + sus tests a `_legacy_nicegui/`; borrar `app/modules/extraccion/`
   huérfano; eliminar shims `init_db`/seeds.
8. Migrar los 5 módulos API manuales del frontend a Orval (cierra el TODO CF.4);
   descomponer `DocumentsPage`; completar `ca/admin.json`; lazy routes.
9. Decidir y ejecutar (o descartar formalmente) el renombrado de roles; actualizar
   `CLAUDE.md` con `src/redaccion/`.

**Preparación de Fase 2:**
10. Inventario de migración de `client_app/` (fichero→destino→LOC) en `PROJECT_STATE.md`.
11. Prompt 0 de F2: refactor DI/partición de `AIBrainService` + registro (o retirada) de
    `automation.py`/`telemetry_router`.
12. Detallar TDD de FASE 14 con Secure Pairing (2A.2) como parte del scaffolding, no como
    añadido posterior.

**Fase 3 (cuando llegue):**
13. Spike temprano de acceso real a APIs UJI/G400/DIR3; valorar
    `langgraph-checkpoint-postgres`; inmutabilidad de `audit_expediente` también a nivel
    de privilegios de BD.

---

## Anexo — Referencias de código citadas

Los hallazgos de seguridad y calidad referencian ficheros concretos, entre otros:
`server/app/routers/auth_router.py:59-82` (A1), `server/app/routers/hub_chatbots_router.py:125-268`
y `server/app/api/v1/hub_feedback.py:48-66` (A2), `server/app/main.py:190-196` (CORS),
`server/app/routers/hub_themes_router.py:113-184` (temas), `server/app/api/v1/ingestion.py:31-43`
(uploads), `server/app/api/v1/automation.py` (DI/router muerto), `server/app/ui/` (NiceGUI
en árbol activo), `frontend/src/shared/api/ingestion.ts` (API manual),
`frontend/src/admin/pages/AccessTokensPage.tsx:25-28` (scopes en cliente),
`frontend/src/widget/hooks/useChat.ts` (errores silenciosos + token),
`server/app/modules/redaccion/services/anonymization/service.py:232,236` (mapa no persistido).

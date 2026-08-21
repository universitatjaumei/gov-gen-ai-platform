# Decisión de arquitectura: Open WebUI como carcasa de chat desechable

> **Fecha**: 2026-07-24
> **Estado**: Aceptada
> **Fuentes**: `MARCO_GOBERNANZA_IA.md` (P1–P11), `planificacion/PROJECT_STATE.md` (estado Fase 1),
> `docs/COMPARATIVA_RAG_LAMB.md`, arquitectura LAMB sobre Open WebUI
> (`C:\Users\fabra\Documents\LAMB_MOODLE\lamb`), evaluación de Open WebUI en el workspace
> `C:\Users\fabra\Documents\openwebui-gerencia`.
> **Finalidad**: fijar el papel de Open WebUI en la plataforma y zanjar la disyuntiva
> "app propia vs. Open WebUI vs. extensiones de Open WebUI", de forma vinculante para las
> fases siguientes.

---

## Veredicto

**Open WebUI se adopta como carcasa de chat *desechable e intercambiable* para la capa
conversacional. El backend de gobernanza (Gov Gen AI Platform) es el producto real e
independiente y sigue siendo la única fuente de verdad. La tramitación de expedientes
mantiene interfaz propia.**

La regla de acoplamiento que resume la decisión: **Open WebUI llama *hacia* nuestro backend;
nunca nuestra lógica de gobernanza vive *dentro* de Open WebUI.** Open WebUI es un cliente de
nuestra API compatible-OpenAI, no un contenedor de nuestra lógica.

Esta es la lección de `COMPARATIVA_RAG_LAMB.md` aplicada a la arquitectura completa, y no solo
al RAG: LAMB no mete su lógica pedagógica ni de gobernanza dentro de Open WebUI; mantiene su
backend como fuente de verdad y usa Open WebUI como frontend de chat + pasarela de modelos.

---

## 1. Contexto

La plataforma tiene tres familias de casos de uso con naturalezas distintas:

1. **Conversacional** — asistentes RAG ciudadanos, redacción asistida en modo diálogo. Tienen
   "forma de chat".
2. **Generación de informes** — apartados deterministas (gráficos, tablas) a partir de datos de
   API o de Excel/CSV subidos, más apartados de literatura asistida por LLM.
3. **Tramitación de expedientes** (Fase 3) — flujo con estado, competencias por rol y fase,
   puertas de revisión. Tiene "forma de flujo", no de chat.

En paralelo, la Fase 1 está casi cerrada (chatbots públicos, redacción Contract-First, AUTH
SAML+PAT, servidor MCP, ingesta, RAG en curso) con deploy previsto en septiembre de 2026. La
duda planteada fue si conviene reconducir el esfuerzo hacia Open WebUI —como app, como
extensiones, o como motor bajo una capa de gobernanza al estilo de LAMB sobre Moodle— para
ganar mantenibilidad.

El criterio de decisión **no es la comodidad, sino el propio marco de gobernanza**: para cada
capa, ¿puede Open WebUI (o Open WebUI + extensiones) sostener P1–P11, o la interacción misma
está regulada y exige interfaz propia?

## 2. Decisión

Open WebUI adopta **tres papeles diferenciados según la capa**:

| Capa | Papel de Open WebUI | Interfaz de la interacción |
|---|---|---|
| Conversacional (RAG, redacción-chat) | **Carcasa de chat + pasarela**, reemplazable | Open WebUI (frontend), backend propio detrás |
| Informes | **Según naturaleza** (ver §5) | Chat en OWUI *o* app propia con revisión |
| Tramitación de expedientes (Fase 3) | **Ninguno** | App propia (Contract-First / SDUI) |

Y una regla transversal e innegociable: **la gobernanza-como-código
(RunManifest, contrato de citas, anonimización, frontera edge-cloud, model_factory, audit
append-only) vive siempre en código propio, nunca como plugin dentro de Open WebUI.**

## 3. Opciones consideradas

### Opción A — Seguir con app propia también para la capa de chat *(statu quo)*
Mantener el frontend React propio como interfaz de chat, además del backend.

- **A favor**: control total; ya está construido; coherencia Contract-First de extremo a extremo.
- **En contra**: obliga a mantener indefinidamente capa *commodity* (UI de chat, streaming,
  selección de modelo, plumbing RAG básico) que no es diferencial y que consume esfuerzo que
  debería ir a la gobernanza y a los expedientes.

### Opción B — Reconducir a extensiones/scripts *dentro* de Open WebUI *(descartada)*
Implementar la gobernanza como Pipes/Filters/Functions ejecutándose en el proceso de Open WebUI.

- **A favor**: aprovecha toda la maquinaria de OWUI; arranque rápido.
- **En contra (decisivo)**: convierte la gobernanza —que debe producir **evidencia jurídica**—
  en rehén del ciclo de releases de un tercero. Cada actualización de Open WebUI puede romper
  los Filters/Pipes. P6 (audit append-only), P8 (frontera edge-cloud) y P11 (sandbox) quedan
  sujetos a las fronteras de proceso y al modelo de datos de OWUI, que no controlamos. Es
  además la opción que **viola P10** (independencia de proveedor): ata el activo diferencial al
  proveedor. Es la peor de las tres para el marco.

### Opción C — Open WebUI como carcasa desechable, backend de gobernanza independiente *(elegida)*
Open WebUI como frontend de chat y pasarela; nuestro backend como fuente de verdad, invocado
vía API compatible-OpenAI. Patrón LAMB-sobre-Moodle, aplicado con Open WebUI como motor.

- **A favor**: dejamos de mantener el *commodity* sin ceder el diferencial; la gobernanza se
  ejecuta en nuestro perímetro; Open WebUI queda intercambiable, lo que **satisface P10** en
  lugar de violarlo; encaja con la evidencia empírica ya recogida sobre LAMB.
- **En contra**: introduce una pieza de infraestructura más que operar y desplegar dentro del
  perímetro edge (ver §6, riesgo P8); parte de la personalización de UI queda limitada a lo que
  Open WebUI permite.

## 4. Justificación contra el marco (P1–P11)

Por qué la capa conversacional tolera la carcasa y la de expedientes no:

| Principio | ¿Open WebUI como carcasa lo sostiene? | Dónde se ejecuta realmente |
|---|---|---|
| P1 Determinismo | ✅ | Cómputo determinista en el backend, antes/fuera del LLM |
| P2 Frugalidad (escalera de recursos) | 🟡 | `model_factory` propio decide el modelo; OWUI solo presenta |
| P3 Supervisión (review gates + ApprovalRecord) | ❌ para flujos | OWUI no expresa puertas de revisión → **expedientes en app propia** |
| P4 Legalidad por diseño (HATEOAS `acciones_permitidas`) | ❌ | No hay máquina de estados de expediente en OWUI → **app propia** |
| P5 Transparencia (Contract-First / SDUI) | ❌ | OWUI no es contract-first → contrato en backend; SDUI en app propia |
| P6 Trazabilidad (RunManifest, citas, audit append-only) | ✅ *si* se ejecuta en backend | Backend emite manifiesto y valida contrato de citas; OWUI no audita |
| P7 Anonimización NER pre/post-LLM | ✅ | Hooks pre/post-LLM en el backend, antes de que el dato cruce |
| P8 Soberanía edge-cloud | ✅ *con condición de despliegue* | OWUI se despliega **dentro del edge** (ver §6) |
| P9 Calidad del corpus | ✅ | Motor de auditoría de contenido en el backend |
| P10 Portabilidad / no-lock-in | ✅ **reforzado** | OWUI intercambiable como frontend; el diferencial no se ata |
| P11 Sandbox de ejecución | ✅ | Microservicio sandbox propio (SBX), no el code-interpreter de OWUI |

**Lectura.** Todos los principios que Open WebUI *no* puede sostener (P3, P4, P5) son
exactamente los que gobiernan la interacción de **flujo** (expedientes). Los que sí sostiene lo
hacen porque **la ejecución real ocurre en el backend** y OWUI solo presenta. En cuanto la
lógica de gobernanza se movería *dentro* de OWUI (Opción B), P6/P8/P10/P11 se degradan. Eso es
lo que fija la regla de acoplamiento del veredicto.

## 5. Alcance en la capa de informes

Los informes se deciden **por naturaleza del artefacto**, no en bloque:

- **Informe como salida de chat** (exploratorio, sin efecto en procedimiento) → admisible en
  Open WebUI, con las partes deterministas calculadas en el backend y solo la redacción
  delegada al LLM.
- **Informe como artefacto de procedimiento** (con puerta de revisión P3, destino a un
  expediente, exportación DOCX/PDF con plantilla fiel) → app propia. La generación determinista
  (gráficos/tablas) y la redacción asistida ya viven en el módulo de redacción Contract-First
  (`docs/REDACCION_CONTRACT_FIRST.md`); OWUI no aporta aquí y añadiría un camino no auditado.

Regla operativa: si el informe alimenta o acompaña una actuación administrativa, va por la app
propia con revisión humana; si es consulta/borrador sin efecto, puede salir por la carcasa.

## 6. Alcance en la capa de recuperación (RAG e ingesta)

**La recuperación y la ingesta NO se externalizan a Open WebUI. Se quedan en el backend, por la
misma regla que el resto de la gobernanza.** Es el caso *opuesto* al de la UX de chat, y conviene
no confundirlos:

- La **UX de chat** es *commodity*: no lleva gobernanza dentro → se externaliza (§2).
- La **recuperación/ingesta** es *portadora de gobernanza*: contrato de citas verificable (P6),
  auditoría de calidad del corpus (P9), anonimización (P7) y frontera edge-cloud (P8 — el corpus
  es dato de cliente final) → se queda en el perímetro.

Delegar el RAG en Open WebUI sería la **Opción B ya descartada** (§3): su RAG es básico —sin
reranker, sin BM25 real, sin MMR, sin contrato de citas ni higiene de corpus, según
`docs/COMPARATIVA_RAG_LAMB.md`—, de modo que mover el corpus allí **regresaría en P6/P9** y
recoplaría la gobernanza al ciclo de releases de un tercero. Además es innecesario por
construcción: con el adaptador compatible-OpenAI (§8), **Open WebUI nunca ejecuta RAG** — el
backend recupera y devuelve respuesta + `sources`, y Open WebUI solo presenta.

**El alivio de mantenimiento del RAG existe, pero por otra palanca**: apoyarse en librerías e
infraestructura madura *dentro* del backend (reranker, índice HNSW, parsers de ingesta tipo
Docling/MarkItDown) en lugar de matemática de retrieval y parsing artesanales. Es "reducir
mantenimiento vía dependencias", no "mover a Open WebUI". Es exactamente el objetivo del
**bloque RAG.1–14** (`planificacion/Plan_TDD_Fase1.md`) y del bloque **ING** de ingesta multi-formato.

> **Lectura.** El instinto de "que OWUI se lleve también la carga del RAG" es comprensible pero
> apunta al activo que *más* hay que proteger dentro del perímetro. La carga que sí se puede ceder
> es la de las *primitivas* (parsers, chunkers, índice, reranker), y se cede a librerías, no a
> Open WebUI.

## 7. Consecuencias

**Positivas**
- Se deja de mantener la capa *commodity* de chat; el esfuerzo se concentra en gobernanza y
  expedientes, que son el diferencial.
- P10 reforzado: Open WebUI es sustituible sin tocar el backend.
- Coherencia con la evidencia ya recogida sobre LAMB.

**Negativas / coste**
- Una pieza más de infraestructura (Open WebUI) a desplegar, versionar y monitorizar.
- La personalización de la UI conversacional queda acotada a lo que Open WebUI ofrece.

**Riesgos y mitigaciones**
- *P8 (soberanía del dato)*: Open WebUI persiste conversaciones y ficheros. **Mitigación**: se
  despliega **dentro del perímetro edge**, su base de datos se trata como dato operacional edge
  y no se sincroniza al cloud. Ningún dato de cliente final sale de OWUI hacia terceros salvo el
  tráfico ya anonimizado que emite nuestro backend.
- *Deriva de upstream*: aunque OWUI no aloja gobernanza, cambios en su API de Pipes podrían
  afectar a la integración. **Mitigación**: la superficie de contacto se limita a un Pipe
  delgado y a la API compatible-OpenAI del backend; se fija versión de OWUI y se prueba antes de
  actualizar.
- *Doble interfaz*: usuarios en OWUI (chat) y en app propia (expedientes/informes formales).
  **Mitigación**: SSO SAML común (bloque AUTH ya cerrado) y criterio claro de §5 sobre qué va
  dónde.

## 8. Implicaciones de implementación

- **Integración**: un **Pipe** delgado de Open WebUI que reenvía a la API compatible-OpenAI del
  backend. La anonimización (P7) y la validación del contrato de citas (P6) se ejecutan en el
  backend, en el trayecto de la petición, no en el Pipe. El Pipe no debe contener lógica de
  gobernanza: solo transporte y presentación.
- **Autenticación**: OWUI detrás del SSO SAML institucional (AUTH ya implementado); el backend
  sigue exigiendo su propia autorización usuario↔organización↔chatbot (bloque SEC).
- **Autorización por chatbot y cuotas de consumo** *(añadido 2026-07-27)*: **no se delegan en
  Open WebUI**, ni siquiera donde OWUI tiene función equivalente. Dos razones y un hecho:
  1. *No es una frontera de seguridad.* Si el gate vive en OWUI, el backend sigue sirviendo ese
     chatbot a cualquier PAT, API key de widget, frontend React o cliente MCP. La autorización
     es gobernanza → código propio (regla del veredicto).
  2. *Su modelo de permisos no alcanza.* El RBAC de OWUI es **aditivo y sin "deny"**, y su
     "public" significa *todos los usuarios autenticados de la plataforma*, no visitantes
     anónimos — así que no puede expresar un `restricted` fail-closed ni gobernar el widget
     anónimo, que además nunca pasa por OWUI.
  3. *Hecho verificado:* las **cuotas por usuario no existen de forma nativa en OWUI** (es su
     petición de administración más votada, aún abierta upstream). Los despliegues grandes las
     resuelven con **LiteLLM de sidecar** o con plugins de token-tracking de terceros. Ambas se
     descartan aquí: LiteLLM duplicaría `model_factory` y sacaría el control de gasto del
     perímetro auditado (roza P2 y P10); el plugin es la **Opción B** ya descartada en §3.

  Implementación: `access_mode` + `assert_chatbot_access` (SEC.2.1), contabilidad de tokens y
  cuotas en cascada (SEC.4), vigencia y presupuesto por chatbot (SEC.4.1). OWUI solo **refleja**
  el resultado: `/v1/models` le devuelve lo que el actor puede usar y los 429/403 se traducen a
  errores OpenAI legibles.
- **Identidad del usuario a través del Pipe** *(añadido 2026-07-27)*: el Pipe usa un **PAT de
  servicio**, de modo que sin más información el backend solo vería al dueño del PAT y la cuota
  por persona sería inaplicable. Se adopta la **propagación de identidad por cabecera firmada**
  (`X-GovGenAI-Actor`, JWT de vida corta, scope `chat:onbehalf`), descartando un PAT por usuario
  —que no escala a cientos de personas ni sobrevive a las bajas—. La cabecera declara *quién*
  pregunta; el backend decide *qué puede hacer* y *cuánto le queda*. Los `organizacion_ids`
  se heredan siempre del PAT, nunca de la cabecera, para que el cliente delegante no pueda
  escalar de organización.
- **Despliegue**: Open WebUI en el edge, con su almacenamiento clasificado como operacional edge
  (P8). No se registra en trazas enviadas al cloud ningún mapa de reversión de anonimización.
- **Expedientes (Fase 3)**: sin cambios respecto al plan; interfaz propia Contract-First/SDUI.

## 9. Secuenciación y timing

**La adopción de Open WebUI no es una fase posterior a la Fase 1: es una carcasa paralela sobre
el mismo backend.** Por tanto no se secuencia como "terminar Fase 1 y luego migrar para
comparar" — esa lectura descansa en una premisa falsa (que la adopción de OWUI y el trabajo
restante de Fase 1 están en la misma capa; no lo están).

Dos hechos del estado actual lo fundamentan:

1. **Lo que queda de Fase 1 es casi todo backend/infra** (SEC, RAG, ING, Fase 11, CAL, Deploy),
   no chat-UI. La interfaz de chat React —chatbots públicos y widget— **ya está construida**: es
   coste hundido, no coste futuro. Lo pendiente es precisamente el sustrato compartido que esta
   decisión conserva.
2. **El endpoint de chat actual NO es compatible-OpenAI**: es un SSE propio
   (`POST /api/v1/hub/chat/{chatbot_id}`, eventos `status`/`token`/`done`) con el contrato de
   citas en el `done` (`sources: [...]`). Open WebUI no puede consumirlo tal cual; falta un
   adaptador `/v1/chat/completions` que mapee ese contrato a las citas de OWUI. **Esa es la
   costura real, pequeña y localizada — y el prerrequisito de cualquier comparación.**

**Secuencia acordada:**

1. **Terminar la vía backend de Fase 1** (SEC → RAG → ING → Deploy). Necesaria en cualquier
   escenario: es el sustrato que comparten la carcasa OWUI y el frontend React.
2. **Congelar la inversión *neta* en la chat-UI React** — dejarla "suficiente como referencia y
   fallback del piloto", sin pulido adicional. Aquí es donde "acabarlo todo primero" quemaría
   esfuerzo desechable.
3. **Adelantar el spike de OWUI** (adaptador compatible-OpenAI + Pipe delgado + mapeo de citas)
   en lugar de diferirlo, porque decidir la carcasa *antes* de rematar el frontend permite
   **descartar** trabajo de frontend en CAL (p. ej. partes de "migrar API manual a Orval", pulido
   de la superficie de chat) en vez de terminarlo y luego tirarlo.
4. **Comparar ambas carcasas contra el mismo backend** en el piloto de septiembre. La línea de
   comparación (frontend React) **ya existe**: no hace falta "acabar la Fase 1" para tenerla.

**Qué se compara.** UX de React-chat vs. OWUI-chat sobre idéntico backend. Terminar más features
de frontend no mejora la comparación; solo añade coste hundido. El criterio decisivo del spike no
es la estética sino la **gobernanza**: ¿preserva OWUI el contrato de citas (P6) y deja la
anonimización (P7) en el trayecto del backend? Eso pesa más que la UX.

**Qué no se tira.** Aunque OWUI gane para el chat, se conserva frontend propio para
redacción/informes formales (§5) y expedientes (Fase 3). Terminar la Fase 1 no es "construir para
tirar": casi todo sobrevive; lo único potencialmente desechable es pulido de chat ya hecho.

## 10. Criterios de reversión

Esta decisión se revisa si: (a) Open WebUI deja de poder desplegarse dentro del perímetro edge
sin fuga de datos; (b) el coste de operar OWUI supera el ahorro de no mantener UI de chat
propia; o (c) aparece la necesidad de una experiencia conversacional tan específica que Open
WebUI la impida y justifique reconstruir la carcasa. En los tres casos, el backend de gobernanza
—al ser independiente— sobrevive a la reversión sin reescritura.

## 11. Documentos relacionados

- `MARCO_GOBERNANZA_IA.md` — principios P1–P11 que fundamentan esta decisión.
- `docs/COMPARATIVA_RAG_LAMB.md` — evidencia del patrón LAMB (backend propio + Open WebUI).
- `docs/REDACCION_CONTRACT_FIRST.md` — módulo de redacción/informes en la app propia (§5).
- `planificacion/PROJECT_STATE.md` — estado de Fase 1 y planificación del deploy.
- `planificacion/Plan_TDD_Fase3.md` — gestor de expedientes (capa que mantiene interfaz propia).

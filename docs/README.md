# Índice de la documentación

Esta carpeta tiene tres clases de documento y conviene distinguirlas antes de leer, porque no
todas envejecen igual:

- **Referencia viva** — describe cómo es la plataforma hoy. Si contradice al código, es un fallo
  del documento y hay que arreglarlo.
- **Decisión** — por qué algo se hizo así, con fecha. No se actualiza: se sustituye por otra
  decisión posterior que la cite.
- **Instantánea** — una valoración, una auditoría o una comparativa en una fecha concreta. Es
  cierta *para esa fecha*, y se lee como historia, no como estado.

> **El índice anterior era el de AutomatIA**, la aplicación NiceGUI de la que nace este proyecto,
> y con él diecisiete documentos que describían aquel producto: el *Client Node*, el *Brain*, su
> `brain_server.db`. El 2026-08-22 pasaron a la cuarentena `_legacy_nicegui/docs/` a esperar
> justo lo que hizo el Bloque NIC: inventariar qué de `client_app/` estaba cubierto. Hecho el
> inventario —`INVENTARIO_RETIRADA_LEGACY.md`, que es el que sobrevive y es el mapa—, **el
> 2026-09-04 se retiraron con la cuarentena entera**. Se leen en el historial de git.

---

## Empezar por aquí

| Documento | Qué es |
|---|---|
| [`MARCO_DESARROLLO_AGENTICO.md`](MARCO_DESARROLLO_AGENTICO.md) | **El método** con el que se desarrolla esto, escrito para poder aplicarse a otros proyectos: principios, permisos de autoaceptación, TDD, guardarraíles, y cómo montarlo en un proyecto nuevo. Con bibliografía y comparación con los marcos publicados |
| [`ESPECIFICACIONES.md`](ESPECIFICACIONES.md) | **Qué garantiza el sistema**, capacidad por capacidad, con sus invariantes y dónde se hacen cumplir. El documento para quien va a escribir código |
| [`PRESENTACION_PROYECTO.md`](PRESENTACION_PROYECTO.md) | Qué hace la plataforma, qué está construido y verificado, y qué está previsto. El documento para quien llega de fuera |
| [`Arquitectura.md`](Arquitectura.md) | Qué es la plataforma y qué principios la rigen: módulos, roles, privacidad, frontera cloud/edge, stack |
| [`../AGENTS.md`](../AGENTS.md) | Las reglas duras para agentes de programación, y de paso el contrato de estilo del proyecto |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Cómo se trabaja aquí |

## Gobernanza, conformidad y licencia

| Documento | Clase |
|---|---|
| [`MARCO_GOBERNANZA_IA.md`](MARCO_GOBERNANZA_IA.md) | Referencia viva — gobernanza, trazabilidad y protección de datos; los dos planos y qué obligación vive en cada uno |
| [`GOVERNANCA_PER_API.md`](GOVERNANCA_PER_API.md) | Inventario de lo que la plataforma comprueba y registra (compliance as code) y qué de ello es accesible por API para aplicaciones desarrolladas fuera; seis candidatos no planificados (en valenciano) |
| [`LICENCIA_ES.md`](LICENCIA_ES.md) | Referencia viva — la AGPL explicada en español: qué permite, qué obliga, qué **no** obliga, y qué significa para un pliego |
| [`REQUISITOS_PUBLICACION_PLATAFORMA.md`](REQUISITOS_PUBLICACION_PLATAFORMA.md) | Referencia viva — qué hace falta para publicar la plataforma |
| [`EU_GOVERNANCE_CONCEPT_NOTE.md`](EU_GOVERNANCE_CONCEPT_NOTE.md) · [`EU_GOVERNANCE_TOPICS.md`](EU_GOVERNANCE_TOPICS.md) | Referencia viva — encaje europeo del proyecto |

## Chatbots y corpus normativo

| Documento | Clase |
|---|---|
| [`CONTRATO_MD_CORPUS.md`](CONTRATO_MD_CORPUS.md) | Referencia viva — el contrato que cumple todo `.md` que entra al corpus. Lo consume la ingesta |
| [`CARGA_VOCABULARIO.md`](CARGA_VOCABULARIO.md) | Referencia viva — cómo se carga el vocabulario de ámbitos y submaterias |
| [`GRAPH_PROFILES.md`](GRAPH_PROFILES.md) | Referencia viva — los perfiles de grafo público y qué hace cada uno |
| [`NIVELES_DE_MODELO.md`](NIVELES_DE_MODELO.md) | Referencia viva — los niveles (*tiers*) de modelo y qué actividad usa cada uno |
| [`DEPURAR_CONTEXTO_RAG.md`](DEPURAR_CONTEXTO_RAG.md) | Referencia viva — cómo depurar qué contexto llegó al modelo |
| [`CURACION_MULTIORGANIZACION.md`](CURACION_MULTIORGANIZACION.md) | Referencia viva — la curación con varias organizaciones |
| [`CASO_CURACION_ESCOLA_DOCTORAT.md`](CASO_CURACION_ESCOLA_DOCTORAT.md) | Referencia viva — caso guía de curación, extremo a extremo |

## Informes, scripts y sandbox

| Documento | Clase |
|---|---|
| [`REDACCION_CONTRACT_FIRST.md`](REDACCION_CONTRACT_FIRST.md) | Referencia viva — el contrato del módulo de Informes: plantillas, extracción, `DraftingCoreGraph`, `RunManifest` |
| [`CASO_INFORME_SEGUIMIENTO.md`](CASO_INFORME_SEGUIMIENTO.md) | Referencia viva — el caso guía del módulo, con las dos reglas duras que salieron de él |
| [`SANDBOX_SECURITY.md`](SANDBOX_SECURITY.md) | Referencia viva — las ocho capas de aislamiento del código generado. La capa 8 (gVisor) **la pone el aprovisionamiento de la VM** desde D.0.doc, con el comando que comprueba que está: la daba la plataforma y ahora es configuración nuestra |

## Plataforma y operación

| Documento | Clase |
|---|---|
| [`MCP_SERVER.md`](MCP_SERVER.md) | Referencia viva — el servidor MCP, sus dos transportes y su toolset |
| [`A11Y_GUIDELINES.md`](A11Y_GUIDELINES.md) · [`A11Y_CHECKLIST.md`](A11Y_CHECKLIST.md) | Referencia viva — accesibilidad: criterios y lista de comprobación |
| [`PRUEBAS_MANUALES.md`](PRUEBAS_MANUALES.md) | Referencia viva — qué se prueba a mano y qué no, con la matriz por módulo |
| [`METODOLOGIA_AGENTICA.md`](METODOLOGIA_AGENTICA.md) | Referencia viva — cómo se ejecuta el desarrollo por bloques |
| [`GESTOR_EXPEDIENTES.md`](GESTOR_EXPEDIENTES.md) | Referencia viva — el módulo previsto para 2027-2028; todavía no existe |
| [`DESPLIEGUE_PROTOTIPO_GCP.md`](DESPLIEGUE_PROTOTIPO_GCP.md) | Referencia viva — el despliegue mínimo del prototipo. No sustituye al bloque Deploy |
| [`chatbots-publicos/`](chatbots-publicos/) | Referencia viva — cómo se embebe el widget: plantilla CSS, tema de ejemplo y página de demostración |
| [`ejemplos/`](ejemplos/) | Referencia viva — ficheros de ejemplo (FAQ del corpus) |

## Decisiones

El registro con número y estado está en [`DECISIONES.md`](DECISIONES.md), que también dice
**cuándo hace falta un ADR** y cuándo basta con una fila en el historial. Las decisiones
sueltas, en orden de aparición:

Se leen por su fecha. Ninguna se actualiza: si una decisión cambia, la sustituye otra que la cite.

| Documento | Decidió |
|---|---|
| [`DECISION_EXTRACCION_Y_DESPLIEGUE.md`](DECISION_EXTRACCION_Y_DESPLIEGUE.md) | Retirar Docling y desplegar en **VM y no en Cloud Run** |
| [`DECISION_MODELOS_EMBEDDING_RERANKER.md`](DECISION_MODELOS_EMBEDDING_RERANKER.md) | Qué modelo de embedding y de reordenación, y cuándo extraerlos a un servicio |
| [`DECISION_CURACION_SEPARADA.md`](DECISION_CURACION_SEPARADA.md) | La curación como módulo propio |
| [`DECISION_RENDERIZADO_RASTREO.md`](DECISION_RENDERIZADO_RASTREO.md) | Cómo se renderiza al rastrear un portal |
| [`DECISION_OPENWEBUI_CARCASA_CHAT.md`](DECISION_OPENWEBUI_CARCASA_CHAT.md) | **Descartar** OpenWebUI como carcasa de chat |
| [`RAG_SUSTITUCION_DEPENDENCIAS.md`](RAG_SUSTITUCION_DEPENDENCIAS.md) | Qué dependencias de recuperación se sustituyeron y por qué |

## Instantáneas

Ciertas en su fecha. Se leen como historia del proyecto, no como estado.

| Documento | Fecha del corte |
|---|---|
| [`VALORACION_PROYECTO.md`](VALORACION_PROYECTO.md) | 2026-08-24 — Valoración del proyecto. Lleva **dos notas de estado**: su §3 y su §2.3 describen fallos y deudas ya cerrados |
| [`AUDITORIA_PRE_DEPLOY.md`](AUDITORIA_PRE_DEPLOY.md) | 2026-08-10 — Auditoría previa al despliegue. Sus nueve hallazgos los cerró el bloque SEC.8 |
| [`COMPARATIVA_ETL_LEGACY.md`](COMPARATIVA_ETL_LEGACY.md) · [`COMPARATIVA_LEGACY_INFORMES.md`](COMPARATIVA_LEGACY_INFORMES.md) · [`COMPARATIVA_PROMPTS_LEGACY.md`](COMPARATIVA_PROMPTS_LEGACY.md) | Qué hacía el legacy NiceGUI frente a lo nuevo, módulo a módulo. **Se conservan porque ese código ya no está en el árbol**: son el único registro dentro del repositorio de las decisiones que el legacy tenía mejor resueltas |
| [`COMPARATIVA_RAG_LAMB.md`](COMPARATIVA_RAG_LAMB.md) | 2026-07-15 — Comparativa de la recuperación frente a otra implementación real |

> **Cuatro instantáneas se retiraron en REPO.3 (2026-09-07)**, con la razón de cada una en su
> commit y el resumen en [`../planificacion/HISTORIAL.md`](../planificacion/HISTORIAL.md):
> `CAMBIOS_ARQUITECTURA.md` y `CAMBIOS_PLANIFICACION.md` —encargos escritos *a* un agente, cuyo
> resultado es la arquitectura construida—, `PRUEBAS_PENDIENTES.md` —sustituido por el `.bat` por
> bloque de `pruebas_manuales/`— y `PLAN_CHATBOTS_E_INGESTA_LOCAL.md` —el corpus ya está
> ingerido—. Lo único que seguía abierto en ellas, la verificación manual del Camino 3, está
> trasladado a `PROJECT_STATE.md`. Los cuatro siguen en el historial de git.

## Dónde está el estado del desarrollo

No aquí. El cursor, los bloques y el historial viven en [`../planificacion/`](../planificacion/):
`PROJECT_STATE.md` para dónde está el trabajo ahora mismo, `HISTORIAL.md` para por qué cada cosa
se hizo como se hizo.

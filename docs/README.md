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
> `brain_server.db`. El 2026-08-22 pasaron a `_legacy_nicegui/docs/`, que es la cuarentena de la
> migración —sólo lectura, y los borra una persona al cerrar la Fase 1—. No se borraron todavía
> porque el Bloque NIC tiene que inventariar qué de `client_app/` está cubierto, y esos documentos
> son la descripción de lo que había.

---

## Empezar por aquí

| Documento | Qué es |
|---|---|
| [`PRESENTACION_PROYECTO.md`](PRESENTACION_PROYECTO.md) | Qué hace la plataforma, qué está construido y verificado, y qué está previsto. El documento para quien llega de fuera |
| [`Arquitectura.md`](Arquitectura.md) | Qué es la plataforma y qué principios la rigen: módulos, roles, privacidad, frontera cloud/edge, stack |
| [`../AGENTS.md`](../AGENTS.md) | Las reglas duras para agentes de programación, y de paso el contrato de estilo del proyecto |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Cómo se trabaja aquí |

## Gobernanza, conformidad y licencia

| Documento | Clase |
|---|---|
| [`MARCO_GOBERNANZA_IA.md`](MARCO_GOBERNANZA_IA.md) | Referencia viva — gobernanza, trazabilidad y protección de datos; los dos planos y qué obligación vive en cada uno |
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
| [`MCP_SERVER.md`](MCP_SERVER.md) · [`mcp.md`](mcp.md) | Referencia viva — el servidor MCP. **Se solapan**: pendiente de unificar |
| [`A11Y_GUIDELINES.md`](A11Y_GUIDELINES.md) · [`A11Y_CHECKLIST.md`](A11Y_CHECKLIST.md) | Referencia viva — accesibilidad: criterios y lista de comprobación |
| [`PRUEBAS_MANUALES.md`](PRUEBAS_MANUALES.md) | Referencia viva — qué se prueba a mano y qué no, con la matriz por módulo |
| [`METODOLOGIA_AGENTICA.md`](METODOLOGIA_AGENTICA.md) | Referencia viva — cómo se ejecuta el desarrollo por bloques |
| [`GESTOR_EXPEDIENTES.md`](GESTOR_EXPEDIENTES.md) | Referencia viva — el módulo previsto para 2027-2028; todavía no existe |
| [`DESPLIEGUE_PROTOTIPO_GCP.md`](DESPLIEGUE_PROTOTIPO_GCP.md) | Referencia viva — el despliegue mínimo del prototipo. No sustituye al bloque Deploy |
| [`chatbots-publicos/`](chatbots-publicos/) | Referencia viva — cómo se embebe el widget: plantilla CSS, tema de ejemplo y página de demostración |
| [`ejemplos/`](ejemplos/) | Referencia viva — ficheros de ejemplo (FAQ del corpus) |

## Decisiones

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
| [`VALORACION_PROYECTO.md`](VALORACION_PROYECTO.md) | Valoración del proyecto, con hallazgos y decisiones pendientes anotadas |
| [`AUDITORIA_PRE_DEPLOY.md`](AUDITORIA_PRE_DEPLOY.md) | Auditoría previa al despliegue |
| [`PRUEBAS_PENDIENTES.md`](PRUEBAS_PENDIENTES.md) | Pruebas pendientes en su momento |
| [`CAMBIOS_ARQUITECTURA.md`](CAMBIOS_ARQUITECTURA.md) · [`CAMBIOS_PLANIFICACION.md`](CAMBIOS_PLANIFICACION.md) | Registro de cambios de arquitectura y de planificación |
| [`COMPARATIVA_ETL_LEGACY.md`](COMPARATIVA_ETL_LEGACY.md) · [`COMPARATIVA_LEGACY_INFORMES.md`](COMPARATIVA_LEGACY_INFORMES.md) · [`COMPARATIVA_PROMPTS_LEGACY.md`](COMPARATIVA_PROMPTS_LEGACY.md) | Qué hacía el legacy NiceGUI frente a lo nuevo, módulo a módulo |
| [`COMPARATIVA_RAG_LAMB.md`](COMPARATIVA_RAG_LAMB.md) | Comparativa de la recuperación frente a otra implementación |
| [`PLAN_CHATBOTS_E_INGESTA_LOCAL.md`](PLAN_CHATBOTS_E_INGESTA_LOCAL.md) | El plan de carga del corpus en local |

## Dónde está el estado del desarrollo

No aquí. El cursor, los bloques y el historial viven en [`../planificacion/`](../planificacion/):
`PROJECT_STATE.md` para dónde está el trabajo ahora mismo, `HISTORIAL.md` para por qué cada cosa
se hizo como se hizo.

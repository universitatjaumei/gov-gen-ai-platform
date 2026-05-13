# Módulo: Chatbots Públicos

**Gov Gen AI Platform · Bloque 9B**

---

## Qué hace este módulo

Permite que cualquier institución (universidad, ayuntamiento, entidad pública) despliegue un **asistente conversacional de base documental** accesible desde su portal web sin necesidad de código propio. El módulo cubre:

- Ingestión y vectorización de documentos (PDF, URL, Markdown).
- Recuperación semántica de evidencias en tres modos.
- Generación de respuestas con un LLM sobre las evidencias recuperadas.
- Widget embebible con streaming en tiempo real, fuentes citadas y valoración.
- Arquitectura de perfiles intercambiables (sin tocar el motor central).
- Cascada de configuración plataforma → organización → chatbot (ver sección Arquitectura).

---

## Arquitectura

### Motor central: CoreGraph

El `CoreGraph` es el orquestador común a todos los chatbots. Ejecuta siempre el mismo flujo:

```
detect_language → retrieve → merge → quality_gate
                                         ↓ ok          ↓ score bajo
                                  generate_answer     fallback
                                         ↓
                                        log → END
```

No contiene lógica de dominio. Toda la variación se inyecta mediante cuatro **estrategias** intercambiables:

| Estrategia | Responsabilidad |
|---|---|
| `RetrievalStrategy` | De dónde y cómo recuperar evidencias |
| `MergeStrategy` | Cómo fusionar los buckets de evidencia |
| `TemplateStrategy` | Cómo construir el prompt para el LLM |
| `LanguagePolicy` | Idioma, filtros y warnings de traducción |

### Perfiles

Un **perfil** es un bundle de las cuatro estrategias registrado en `GraphProfileRegistry`. Los tres disponibles:

| Perfil | Caso de uso |
|---|---|
| `PUBLIC_KB_RICH` | Chatbot genérico: grupos, FAQs, oferta académica, procedimientos sencillos |
| `PUBLIC_PORTAL_AGGREGATOR` | Portal que agrega dos fuentes (p. ej. procedimientos + normativa) |
| `PUBLIC_PORTAL_ROUTER` | Portal que enruta entre chatbots hijos por dominio temático |

### Modos de retrieval (`retrieval_mode`)

| Modo | Cuándo usarlo |
|---|---|
| `RAG` | KBs medianas-grandes. Recupera los `retrieval_top_k` fragmentos más relevantes por búsqueda vectorial (BGE-M3, dim 1024). |
| `MD_LONG_CONTEXT` | Corpus pequeño (≤ ~100 documentos). Mete el corpus completo en el contexto del LLM. Sin pérdida de información. |
| `MD_AGENT_SELECTOR` | Selección agéntica (stub en desarrollo). El grafo decide qué documentos leer. |

### Cascada de configuración

```
Plataforma (defaults del sistema)
    ↓ si el campo no es null en HubClient
Organización (HubClient.default_*)
    ↓ si el campo no es null en HubChatbot
Chatbot (HubChatbot.public_graph_profile, retrieval_mode, ...)
    ↓
PublicGraphConfig efectiva → GraphFactory → CoreGraph
```

---

## Funcionalidades detalladas

### 1. Gestión de chatbots (panel admin)

- **CRUD completo** vía `/api/v1/hub/chatbots`.
- Cada chatbot pertenece a una organización (modelo interno: `HubClient`).
- Campos de configuración del grafo que se pueden fijar por chatbot:
  - `retrieval_mode` — RAG / MD_LONG_CONTEXT / MD_AGENT_SELECTOR
  - `public_graph_profile` — perfil de grafo
  - `language_mode` — prefer / strict / none
  - `quality_threshold` — score mínimo promedio (default 0.6)
  - `min_retrieval_results` — fragmentos mínimos para no caer a fallback (default 2)
  - `min_retrieval_score` — score mínimo por fragmento (default 0.25)
  - `retrieval_top_k` — cuántos chunks recuperar en modo RAG (default 8)
  - `answer_template` — plantilla de respuesta (generic / uji_portal)
  - `reranker_enabled` — activar reranking futuro
- **Chatbots jerárquicos**: un chatbot de tipo `router` puede tener hijos atómicos; el router selecciona el hijo apropiado antes de responder.
- **Estadísticas de corpus**: endpoint `/corpus-stats` devuelve número de documentos, chunks, tokens totales y recomienda el modo de retrieval más adecuado.
- **Regeneración de chunks**: útil si cambia el modelo de embedding o los parámetros de chunking.

### 2. Ingestión de documentos

- **Ingestión por URL**: el `IngestionScheduler` rastrea periódicamente las URLs registradas en `HubIngestionSource` y actualiza el corpus si el contenido cambia (por hash).
- **Ingestión por archivo**: subida de PDF directa vía `/api/v1/hub/ingestion/{chatbot_id}/documents` con procesado Docling → Markdown → chunks.
- **Temporal (upload de usuario)**: un usuario final puede subir un PDF que se chunkeará como contexto temporal (`is_temporary=True`) ligado a su `owner_id`.
- Cada documento se almacena en `HubDocument` (Markdown completo) y sus fragmentos en `HubDocumentChunk` (con embedding vectorial pgvector dim 1024).

### 3. Chat con streaming SSE

**Endpoint**: `POST /api/v1/hub/chat/{chatbot_id}`

**Protocolo de eventos**:

| Evento | Cuándo | Payload |
|---|---|---|
| `status` | Al entrar en cada nodo del grafo | `{ node, msg }` |
| `token` | Por cada fragmento de texto generado | `{ delta }` |
| `done` | Al completar la respuesta | `{ interaction_id, sources, language_fallback, translation_warning }` |
| `error` | Si se produce una excepción | `{ message }` |

El evento `done` incluye las **fuentes citadas** (document_id, title, url, score) que el frontend muestra como píldoras clicables con enlace al documento original.

### 4. Política de idioma

- **prefer** (default): detecta el idioma de la consulta con langdetect. Si hay evidencias en el idioma del usuario, las prioriza; no lanza búsqueda secundaria innecesaria.
- **strict**: filtra evidencias al idioma del usuario; si no hay suficientes, cae a fallback.
- **none**: sin filtros de idioma.

Se emite un `translation_warning` cuando el idioma del contexto recuperado difiere del idioma de la consulta. Este aviso es **independiente** del fallback de calidad.

### 5. Widget embebible

El widget se construye como bundle JavaScript autocontenido que puede embeberse en cualquier portal con un solo `<div>`:

```html
<div
  id="govgenai-widget"
  data-chatbot-id="UUID-DEL-CHATBOT"
  data-api-url="https://api.tudominio.es/api/v1"
  data-lang="es"
  data-token="JWT-OPCIONAL"
></div>
<script src="widget.js"></script>
```

**Funcionalidades del widget**:
- Burbuja flotante colapsable (💬 → panel expandido).
- Historial de conversación en sesión.
- Indicador de nodo activo durante el streaming ("Buscando en la base de conocimiento…").
- Renderizado de Markdown en respuestas del asistente.
- Píldoras de fuentes citadas con enlace al documento original.
- Aviso de traducción cuando el contexto está en otro idioma.
- Valoración por estrellas (1–5) tras cada respuesta.
- Idioma configurable vía `data-lang` o mensaje `postMessage({ type: 'govgenai:setLang', lang: 'ca' })`.
- Autenticación opcional con JWT en header `Authorization: Bearer`.

### 6. Feedback

- `POST /api/v1/hub/feedback/{interaction_id}` — registra puntuación (1–5) y comentario opcional.
- `GET /api/v1/hub/feedback/{chatbot_id}/review` — devuelve interacciones pendientes de revisión humana (para panel admin/partner).

### 7. Configuración del LLM

- Cada chatbot se asocia a una `HubLLMConfig` (modelo + temperatura + max_tokens + proveedor).
- Proveedores disponibles: Anthropic (Claude), OpenAI, Ollama local.
- Prompt caching configurable por chatbot (`use_prompt_caching`, `cache_ttl`).
- El `ModelFactory` resuelve el modelo en cascada según la config del chatbot.

---

## API pública resumida

| Endpoint | Método | Quién lo llama |
|---|---|---|
| `/api/v1/hub/chat/{chatbot_id}` | POST | Widget del portal (usuario final) |
| `/api/v1/hub/feedback/{interaction_id}` | POST | Widget del portal (usuario final) |
| `/api/v1/hub/chatbots` | GET/POST | Panel admin |
| `/api/v1/hub/chatbots/{id}` | PATCH/DELETE | Panel admin |
| `/api/v1/hub/chatbots/{id}/corpus-stats` | GET | Panel admin |
| `/api/v1/hub/chatbots/{id}/regenerate-chunks` | POST | Panel admin |
| `/api/v1/hub/clients` | GET/POST/PATCH | Panel admin/partner (organizaciones) |
| `/api/v1/hub/ingestion/{chatbot_id}/documents` | POST | Panel admin |

---

## Variables CSS del widget

El widget expone variables CSS para personalización sin recompilar:

| Variable | Por defecto | Dónde se aplica |
|---|---|---|
| `--source-pill-bg` | `#e0f2fe` | Fondo de píldoras de fuentes |
| `--source-pill-fg` | `#0369a1` | Texto de píldoras de fuentes |
| `--source-pill-border` | `#7dd3fc` | Borde de píldoras de fuentes |
| `--widget-bottom` | `1.5rem` | Posición inferior de la burbuja flotante |
| `--widget-right` | `1.5rem` | Posición derecha de la burbuja flotante |

Las variables para colores del chatbox, burbujas de mensajes, fuentes y botones se definen en la hoja de estilo de la institución (ver `docs/chatbots-publicos/css-template.md`).

---

## Despliegue

El módulo es **edge** (corre en la nube del cliente). Depende de:

- PostgreSQL 16 + pgvector (vectores dim 1024 para BGE-M3).
- BGE-M3 in-process (LocalEmbeddingService) durante el desarrollo; se externaliza cuando el cold start supere 15 s en Cloud Run.
- Variables de entorno: `DATABASE_URL`, `DATABASE_URL_SYNC`, `STORAGE_BACKEND`, `STORAGE_BUCKET`.

---

## Tests

```
server/tests/public_graphs/
├── test_retrieval_contract.py        # Contrato EvidenceItem / RetrievalResult
├── test_retrieval_strategy_protocols.py # PipelineRetrievalStrategy + RetrievalOutput
├── test_core_graph.py                # CoreGraph: compile, fallback, modos
├── test_public_kb_rich.py            # Perfil PUBLIC_KB_RICH × 3 modos
├── test_public_portal_router.py      # PortalRouterRetrievalStrategy
├── test_uji_aggregator.py            # UJI: retrieve dual, merge, template, warning
├── test_language_policy.py           # prefer / strict / none + warnings
├── test_graph_factory.py             # GraphFactory: cascada de config
├── test_profile_contract.py          # Contrato por perfil (compile + smoke run)
└── test_pipeline_contract_suite.py   # Contrato por pipeline (EvidenceItem output)
```

**Total: 80 tests · 100% verdes.**

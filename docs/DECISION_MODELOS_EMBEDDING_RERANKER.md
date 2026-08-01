# Decisión — Modelos de embedding y reranker: local en edge, API en cloud

**Fecha**: 2026-08-01 · **Estado**: aceptada · **Origen**: pregunta del usuario antes de ejecutar RAG.6

## El problema

BGE-M3 (1,1 GB) y, si RAG.6 se implementa como estaba escrito, BGE-reranker-v2-m3 (~600 MB)
son 3-4 GB de RAM por instancia de Cloud Run. `CLAUDE.md` ya fija ese umbral como criterio de
extracción a microservicio, pero la conclusión real es anterior: **en cloud no queremos esos
modelos, queremos una API**; en edge sí los queremos, porque el dato no puede salir.

El mismo codebase tiene que servir a los dos, y hoy no puede.

## Lo que había (verificado el 2026-08-01)

| Pieza | Estado |
|---|---|
| Panel de proveedores y modelos (`HubProvider` + `HubLLMConfig`, CRUD, `available-models`, test de conexión, `LLMConfigsPage.tsx`) | Existe y funciona — **solo para el modelo de chat** |
| `GoogleEmbeddingService` | Escrito y **nunca usado**: `get_embedding_service()` devuelve incondicionalmente el local |
| Dimensión del vector | `Vector(1024)` fija en `hub_document_chunks.embedding` y `hub_crawled_pages.page_embedding` |
| Procedencia del vector | **No se registra**: ninguna fila dice con qué modelo se embebió |
| Guarda de dimensión en `recalculate-corpus` | Existe y **no puede saltar nunca**: compara `getattr(..., "dimensions", 1024)` con `getattr(..., "embedding_dimensions", 1024)`, y ninguno de los dos atributos existe |

La consecuencia que no estaba escrita en ningún sitio: cambiar de modelo de embeddings no es
un cambio de configuración. Es migración de esquema + re-embeber el corpus + riesgo de
**mezcla silenciosa** — el coseno entre vectores de dos espacios distintos no da error, da
resultados malos.

## Verificación de la API de Google (2026-08-01)

- `gemini-embedding-001`: dimensión **flexible de 128 a 3072** (MRL), recomendadas 768 / 1536 /
  3072. **1024 es válido aunque no esté en la lista recomendada.**
- **Las dimensiones distintas de 3072 no vienen normalizadas**: la documentación dice
  literalmente «you must manually normalize non-3072 dimensions».
- `gemini-embedding-2`: GA desde abril de 2026, multimodal, mismo rango 128-3072.
- Precio: $0,15/MTok (001) y $0,20/MTok texto (2).

## Decisiones

1. **La dimensión de la plataforma es 1024, y no se toca.** Es el único valor que sirve a la
   vez a BGE-M3 en edge y a Google en cloud, y mantenerlo salva la columna, el índice HNSW y
   el corpus ya cargado. Cambiar de proveedor pasa a ser re-embeber; nunca migrar esquema.

2. **Normalizamos nosotros, siempre.** El adaptador L2-normaliza la salida venga como venga
   del proveedor. Depender de que el modelo lo haga es depender de una nota al pie que cambia
   entre versiones, y el síntoma de equivocarse son scores que parecen válidos.

3. **El propósito entra en el modelo de datos**: `HubLLMConfig.purpose`
   (`chat` | `embedding` | `rerank`) y `output_dimensionality`. Se reutiliza el panel que ya
   existe —proveedores, claves, test de conexión— en vez de construir uno nuevo.

4. **La procedencia se graba con el vector**: cada chunk registra modelo y dimensión. Sin
   esto, la decisión 3 es un interruptor que rompe cosas en silencio.

5. **El reranker nace por API, no local.** RAG.6 se reordena: la implementación por API es la
   de referencia y `LocalReranker` queda como opción de edge, detrás del mismo protocolo.
   Meter un segundo modelo local ahora es construir el problema que este documento evita.

## Calidad en castellano y valenciano: se mide, no se supone

`gemini-embedding-001` declara **más de 100 idiomas** y lidera MMTEB (250+ lenguas), pero la
documentación **no publica lista por idioma y el catalán no aparece mencionado**. «100+
idiomas» sin lista es una estadística, no un compromiso, y el corpus es **valenciano** con
consultas que llegarán en las dos lenguas — que es justo donde más varía la calidad entre
modelos.

**No hace falta decidirlo por reputación.** RAG.1 dejó `run_golden.py`, que mide recall@5 y
MRR del retriever real con el servicio de embeddings real contra un dataset dorado escrito en
valenciano con el vocabulario del usuario. Cuando el corpus v1 esté cargado: dos ejecuciones,
BGE-M3 y Google a 1024, y se compara con datos propios. Cuesta un par de horas y ~1 $ de API.

La cascada por chatbot y la procedencia de MOD.1 permiten tener **dos chatbots sobre el mismo
corpus**, uno por modelo, midiéndose en paralelo sin riesgo de mezclar espacios vectoriales.

Un matiz para esa medición: truncar a 1024 con MRL pierde algo de calidad frente a los 3072
nativos. Si la diferencia saliera grande, la decisión de «1024 en toda la plataforma» habría
que revisarla, al precio de romper la compatibilidad de esquema con BGE-M3 en edge.

## Lo que NO se decide aquí

- **Qué proveedor de reranking** (Vertex AI Ranking, Cohere Rerank u otro): hay que
  contrastar precio y latencia con datos, y no los tenemos.
- **Si el default de plataforma pasa a Google.** Hoy sigue siendo BGE-M3 local, que es lo que
  funciona en desarrollo. Cambiarlo es un `UPDATE` de configuración una vez exista MOD.2.
- **La extracción a microservicio** de BGE-M3/Docling: sigue rigiendo el criterio de
  `CLAUDE.md` (cold start > 15 s, RAM > 2 GB o necesidad de escalar por separado).

## Orden de ejecución

1. ~~Verificar la API de Google~~ ✅ (arriba).
2. **MOD.1** — propósito en la configuración + procedencia en el vector. **Antes de cargar el
   corpus v1**: hacerlo después cuesta re-embeber las ~380 normas.
3. **MOD.2** — selección del servicio por configuración (`get_embedding_service` resuelve
   contra la cascada) y `HttpEmbeddingService` para el microservicio.
4. **RAG.6 reordenado** — reranker por API detrás del protocolo, `LocalReranker` para edge.

## Por qué ahora y no después del deploy

El corpus v1 está sin cargar. Cargarlo con BGE-M3 y cambiar después cuesta re-embeber las
~380 normas con su índice detrás. Es el momento más barato que va a existir para decidirlo, y
por eso se altera la planificación en vez de arrastrarlo.

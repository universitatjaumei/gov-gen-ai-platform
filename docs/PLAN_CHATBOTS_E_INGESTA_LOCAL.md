# Los dos asistentes del piloto: análisis, configuración e ingesta en local

> **Reescrito el 2026-08-15.** La versión del 2026-08-11 daba por pendiente casi todo lo que
> ahora está hecho —el corpus ya viene desdoblado en dos paquetes, la FAQ ya está convertida,
> la clasificación ya se emite— y daba por resuelto lo único que no lo está: **Vertex**. Se
> conserva el nombre del fichero porque el asunto es el mismo; el contenido está verificado
> contra el código y contra las carpetas reales el 2026-08-15.
>
> El plan ejecutable vive en `Plan_TDD_Fase1.md` §Bloque PIL. Esto es el análisis que lo
> sostiene.

---

## 1. Qué hay, exactamente

**El corpus ya está empaquetado para dos asistentes.** Lo hace el pipeline de curación
(`passa_el_pipeline.py`, paso 8) y la pertenencia vive en su `assistents.json`, no en el
`.md`: los identificadores de los asistentes son internos y esa relación cambia más a menudo
que las normas.

| Paquete | Documentos | Tamaño | Qué contiene |
|---|---|---|---|
| `generat/ingesta/normatiu` | **298** `.md` | ~16,9 MB (~4,2M tokens) | Todo: `md_contracte` + el paquete de Gerencia + los 27 sin ficha |
| `generat/ingesta/gerencia` | **124** `.md` | ~10,5 MB (~2,6M tokens) | Subconjunto por materia: gestión económica, RRHH, contratación, convenios, cátedras |

No son corpus disjuntos: `gerencia` es un subconjunto orientado por materia del mismo fondo.
Pesa más de lo que su recuento sugiere porque se lleva los documentos gordos —presupuesto,
bases de ejecución, plan antifraude, PES—.

Comprobado en los dos paquetes: **los 422 ficheros llevan `ambit_principal` y `submateries`
en campos reales** (ya no en `extra`), **2 documentos con `content_class: faq`** en cada uno,
1 derogado, y 33 / 7 versiones no canónicas de parejas bilingües.

Las instrucciones vivas de ingesta son
`Descarregar_pdf/normativa_propia/publicacio_transparencia_2026-07/INGESTA.md`, revisión del
14-08-2026.

## 2. Cuatro hallazgos que hay que resolver antes de ingerir

### 2.1 El vocabulario dejó de ser opcional

`docs/CARGA_VOCABULARIO.md` promete que «hoy los documentos aún no emiten esos campos, así que
la validación pasa trivialmente». **Ya no.** Con `ambit_principal` y `submateries` emitidos en
los 422 ficheros, `assert_vocabulary` valida de verdad contra `hub_vocabulary_terms` y
**aborta la ingesta entera** si falta un código. Cargar el vocabulario (5 ámbitos, 58
submaterias, en ese orden) pasa de recomendación a prerrequisito. El documento hay que
corregirlo: hoy engaña a quien lo siga.

### 2.2 No existe adaptador de Vertex

`GoogleEmbeddingService` (`services/embedding_service.py:86`) construye
`GoogleGenerativeAIEmbeddings` con `GOOGLE_API_KEY`: eso es la API de AI Studio, no Vertex.
`embedding_resolver.py:86-94` solo conoce `google_genai` y `local`, y
`langchain-google-vertexai` no está en `server/pyproject.toml`.

**Configurar Vertex es desarrollo**, no una fila de configuración: dependencia, adaptador,
`provider_type`, credenciales ADC y proyecto/región. Es PIL.1, y va antes de cualquier carga
porque el proveedor con que se embebe manda durante toda la vida del corpus:
`assert_embedding_space_matches` devuelve 409 en cada consulta si luego no coincide.

### 2.3 Ningún adaptador por API embebe por lotes

`watcher.py:270` hace `getattr(self._embedding, "embed_batch", None)` y cae, si no existe, a
una llamada por fragmento. `LocalEmbeddingService` lo expone; **el de Google no**. Con la
medida del corpus (~50 fragmentos por documento) son **~15.100 + ~6.300 llamadas
secuenciales**. El coste en dinero es despreciable —~6,8M tokens, del orden de un euro—; el
problema es el tiempo de pared y el límite de tasa. El lote entra en PIL.1 con el resto.

### 2.4 Borrar un chatbot no borra su corpus

`hub_documents.chatbot_id` **no tiene FK** (`operational_models.py:212`): se cayó al separar
`HubConfigBase` de `HubOperationalBase`, y la frontera edge-cloud pide que no vuelva.
`hub_document_chunks → hub_documents` sí cascadea (`fk_chunk_document_id`, ING.0.2). Resultado:
`DELETE /hub/chatbots/{id}` deja documentos y embeddings sin dueño. Se descubre justo al
limpiar los chatbots de prueba, y se arregla con un borrado explícito en la misma transacción
(PIL.2). Las interacciones **no** se borran: son registro de lo que se contestó, y con REV.1
encima son material de revisión.

## 3. Un defecto del corpus que se resuelve de nuestro lado

45 documentos tienen artículos **vigentes cuyo contenido está desplazado** por los Estatutos
de 2025. El corpus lo marca con `::: nota-vigencia` dentro del texto del artículo, pero un
artículo se parte en 3-6 fragmentos y la nota cae físicamente en uno: **de 86 unidades
desplazadas, 83 tienen trozos sin el aviso**. Quien recupere uno de esos trozos contesta un
texto que no se aplica, sin ninguna señal.

La curación no puede arreglarlo sin escribir el aviso en la rúbrica del artículo, que es texto
aprobado. Sí nos da todo lo necesario: `desplacat_per` por ancla en el front-matter, y
`desplacat` en las `classes` de los 290 fragmentos afectados. **La nota se hidrata al montar
la evidencia** (PIL.3): no depende de dónde cayó el texto, vive en un solo sitio, y es texto
de la evidencia y no una instrucción al modelo —que es lo que CRITERIS §1.4 prohíbe para algo
resoluble antes de llegar al modelo—.

Entra antes de las pruebas por una razón de método: si durante el piloto sale una respuesta
con texto desplazado, con el fallo sin arreglar no se puede distinguir de uno nuevo.

## 4. Los dos asistentes

|  | **Normativa UJI** (público) | **Gerència** (interno) |
|---|---|---|
| A quién sirve | Ciudadanía y comunidad universitaria, sin identificar | Personal de Gerencia, identificado |
| Corpus | `ingesta/normatiu`, 298 documentos | `ingesta/gerencia`, 124 documentos |
| Coste de equivocarse | **Alto**: una cita errónea sale con autoridad de norma ante un tercero | Medio: quien lee tiene criterio y contrasta |
| Superficie | Widget embebido, con credencial de sitio | Panel interno |
| Revisión | Detector de huecos (RAG.14) | **REV.1**, el veredicto humano sobre respuestas reales |

### Configuración

| Campo | Público | Gerencia | Por qué |
|---|---|---|---|
| `access_mode` | `public_anon` | `authenticated` en local, **`restricted` + `allowed_saml_groups` al desplegar** | En local no hay IdP; la pertenencia al grupo es lo único que queda sin probar, y es configuración pura |
| `retrieval_mode` | `RAG` | `RAG` | Ver §5 |
| `public_graph_profile` | `PUBLIC_KB_RICH` | `PUBLIC_KB_RICH` | El perfil genérico con KB enriquecida es el que corresponde a los dos |
| `chunking_strategy` | `structural` | `structural` | El `.md` ya trae jerarquía y anclas de artículo; el troceador las respeta |
| `language_mode` | `prefer` | `prefer` | Corpus bilingüe (193 val / 78 es) |
| `quality_threshold` | **0,7** | **0,5** | El mando que decide cuándo el asistente dice que no sabe |
| `min_retrieval_score` | **0,3** | **0,25** | El default (0,0) acepta lo que devuelva la búsqueda, por flojo que sea |
| `min_retrieval_results` | 2 | 1 | Una sola fuente para una respuesta normativa ante un tercero es poco margen; una FAQ que responde sola, no |
| `reranker_enabled` | `false` | `false` | RAG.6b va detrás del bloque Deploy; el reranker local se fue con D.4.0 |
| `query_rewriting_enabled` | `false`, y medir | `false` | El ciudadano no usa las palabras de la norma: candidato claro, pero cuesta latencia y una llamada |
| `anon_ip_daily_token_quota` | fijado | — | Es público y anónimo: el sujeto de la cuota es la IP |

**La asimetría de umbrales es la decisión de fondo, no un ajuste fino**: ante el ciudadano,
callar cuesta menos que citar mal; ante el funcionario, una respuesta parcial con su fuente ya
es útil.

## 5. Estrategia de recuperación

Para los dos, **`RAG` con troceado estructural en la primera pasada**. El corpus está partido
por encabezado con anclas de artículo, que es exactamente lo que la búsqueda vectorial
aprovecha, y usar la misma configuración en ambos hace comparables las dos pruebas: si una va
mejor, se sabrá que es por el corpus y el umbral, no por el mecanismo.

Lo interesante viene después y **solo en Gerencia**: `MD_AGENT_SELECTOR` (VIS.2, nivel 1) es
ahí un candidato serio y en el público no. Con 124 documentos el índice de submaterias cabe en
~2.300 tokens —el catálogo de fichas entero son ~72k y no cabría—, el front-matter trae
`resum_router` y `preguntes_tipus` escritos justo para que un encaminador decida, y el
funcionario pregunta por procedimiento («cómo justifico una dieta de un curso con ingresos
externos»), donde leer el documento entero responde mejor que ocho fragmentos sueltos.

Lo que hace la comparación barata: **cambiar de modo es una columna del chatbot, no una
reingesta**. Se ingiere una vez y se miden las dos configuraciones con el mismo dorado.

## 6. Orden de ejecución

| # | Qué | Prompt | Bloquea a |
|---|---|---|---|
| 1 | Adaptador de Vertex + lote por API | PIL.1 | Toda la ingesta |
| 2 | Borrar chatbot retira su corpus | PIL.2 | La limpieza de los de prueba |
| 3 | Aviso de vigencia desplazada | PIL.3 | La validez de las pruebas |
| 4 | Vocabulario + validación de los dos paquetes | PIL.4 | La ingesta |
| 5 | Alta de los dos asistentes + credencial de widget | PIL.5 | La ingesta |
| 6 | Carga real, con medición | PIL.6 | Las pruebas |
| 7 | Pruebas, ajuste y decisión de modo | PIL.7 | — |

**Prerrequisitos externos**, que aporta el usuario: Docker arrancado, migraciones al día, y
proyecto/región de GCP con la Vertex AI API habilitada y credenciales ADC en la máquina.

## 7. Lo que este piloto NO cubre

- **La pertenencia al grupo SAML de Gerencia**: sin IdP en local, `restricted` se prueba al
  desplegar. Lo demás de la cadena de identidad sí se ejercita con `authenticated`.
- **El reranker**: RAG.6b necesita el Ranking API de Vertex, que habilita D.0.
- **La vigencia validada jurídicamente**: 43 de los 298 no llevan `vigencia_validada_per`, y
  219 defectos siguen pendientes de Secretaría General. No impiden la ingesta —son desfases
  del texto normativo, no de la conversión— pero el asistente avisará en esas respuestas.
- **Las 5 tablas de tarifas de `PRE-001` que siguen como texto corrido**: llevan importes y el
  texto no dice cuál es con IVA y cuál sin.

## 8. Dónde viven los datos, comprobado

- El contenedor de la aplicación **no monta ningún volumen** en `docker-compose.prod.yml`: es
  desechable por diseño.
- Los datos viven en volúmenes con nombre —`postgres_data_prod`, `minio_data_prod`— que
  sobreviven a `docker compose down`, al `pull` y a la reconstrucción de imágenes.
- Los documentos no tocan el disco del contenedor: `StorageService` (fsspec) escribe en MinIO
  en local y en GCS en producción.

⚠️ `docker compose down -v` **sí** borra los volúmenes. Es la única forma de perder el corpus
por accidente, y basta con no usar `-v`. Reingerirlo cuesta el tiempo y el coste de embedding
de §2.3, no una restauración.

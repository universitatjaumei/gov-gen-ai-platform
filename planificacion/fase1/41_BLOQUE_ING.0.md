## Bloque ING.0 — Fundamentos del corpus normativo (Subfase 1.A, PENDIENTE)

> **Contexto**: replanificado el 2026-07-28 tras la valoración cruzada con la estrategia de recuperación de `openwebui-gerencia` (`INFORME_ESTRATEGIA_ASISTENTE_GERENCIA.md`) y, sobre todo, con `Descarregar_pdf\normativa_propia\INFORME_MATERIES_I_METADADES_AGENTS.md`, que es donde la clasificación está cerrada: **5 ámbitos, 58 submaterias, esquema de 56 campos** (`vocabulari/ambits.csv`, `vocabulari/submateries.csv`, `vocabulari/esquema_metadades.yaml`).
>
> **Qué sustituye**: los antiguos ING.0.1 (`CorpusManifest`) e ING.0.2 (CLI de carga), que no llegaron a ejecutarse. Su contenido se conserva ampliado en ING.0.3 e ING.0.5. El contrato anterior era incompatible con la estrategia por tres motivos medidos: un `category: str` único donde hacen falta tres ejes; ningún sitio en `HubDocument` donde persistir los metadatos (no hay columna JSON ni `content_class` ni `reviewer`); y ningún filtrado por metadatos en la capa de recuperación, que es exactamente el Nivel 1 de la estrategia y lo que `CRITERIS` §1.4 exige para el control de acceso.
>
> **Estrategia de recuperación objetivo** (informe §6.1), que este bloque + el Bloque VIS habilitan:
> ```
> NIVEL 0  índice de las 58 submaterias en el system prompt      2.307 tokens (medido)
> NIVEL 1  router: pregunta → 1-3 submaterias → fichas filtradas ~1.500 tokens
> NIVEL 2  inyección de 1-3 normas completas                     ~25k tokens
> NIVEL 3  RAG por artículos, SOLO para las 22 leyes externas    (Bloque RAG)
> ```
> El 99,7 % de la normativa propia se inyecta entera (131 docs < 6k tokens, 170 entre 6k y 25k, 1 por encima de 78k). El RAG por fragmentos solo es imprescindible para LCSP (~352k tokens), Ley 6/2024 (~303k) y Decreto-ley 14/2025 (~283k).
>
> **Origen del corpus (decidido 2026-07-28)**: la UJI está definiendo el modelo de publicación normativa. El `.md` autoritativo vivirá **en la BD de publicación**, y de ahí se generarán el PDF y el HTML consultable. **Las circulares de Gerencia pasan por el mismo circuito de publicación**, con `nivell_acces: intern`. Consecuencias duras:
> - **Un solo maestro para el corpus propio**: la BD de publicación. El hub es réplica de solo lectura (`source_kind='publicacio'`). No se construye UI de edición de metadatos en el hub (regla de CLAUDE.md: sin código especulativo); la carga manual queda cubierta por el CLI de ING.0.5 para emergencias.
> - **El crawler queda desactivado para este corpus.** Dos rutas de entrada para la misma norma producirían dos conversiones del mismo texto compitiendo en el top-k. `CRITERIS` §3.2: declarar fuente autoritativa antes de indexar y retirar las redundantes.
> - **Los `.md` llegan con jerarquía real de encabezados (5 niveles) y ancla estable por unidad citable** — confirmado que se aplica tanto a las normas nuevas como retroactivamente al corpus histórico. Especificación cerrada en **`docs/CONTRATO_MD_CORPUS.md`**. Por tanto el parser estructural de la tarea 8 del informe **no se implementa en el hub**: el hub consume la jerarquía, no la reconstruye.
>
> **Dos transportes, un solo reconciliador (decidido 2026-07-28)**: el pipeline de publicación **no estará hasta dentro de unos meses**, así que durante ese tiempo la actualización del corpus se hace **por CLI sobre una carpeta de `.md`**, y no como carga inicial de una sola vez: es el mecanismo de mantenimiento en funcionamiento. Después se le añade el transporte programático (MCP o export incremental). Regla dura para que eso no produzca dos pipelines divergentes:
> - **La lógica de reconciliación se escribe UNA vez**, en ING.0.5, detrás de un protocolo `CorpusSource`. La carpeta local y el servicio MCP son dos **fuentes** del mismo reconciliador; SYNC.1 añade una fuente, no un pipeline.
> - **Lo incremental no es un modo**: emerge del hash. El mismo comando sobre la misma carpeta omite lo no cambiado, actualiza metadatos sin re-chunk y re-ingiere solo lo modificado.
> - **Lo que sí es un modo, y es peligroso, es el censo.** Detectar retiradas exige saber que la fuente es el corpus COMPLETO. Un `--prune` sobre una subcarpeta retiraría cientos de normas. Por eso el censo es opt-in explícito y va con salvaguarda de proporción.
> - **Identidad estable desde el primer día**: `id_publicacio` en el contrato aunque hoy venga vacío, para que el día que llegue el transporte programático sea una continuación y no una recarga del corpus.
>
> **Vocabulario revisable (requisito, decidido 2026-07-28)**: los 5 ámbitos y las 58 submaterias son una **propuesta pendiente de validar por SG** y deben poder cambiar después. Eso impone dos reglas que atraviesan este bloque y el Bloque RAG:
> 1. El vocabulario es **dato versionado en tabla**, nunca `Enum` de Python ni `CheckConstraint`.
> 2. **La taxonomía no entra JAMÁS en el texto que se embebe.** Si `submateria` acabara dentro del chunk embebido, cada revisión del vocabulario costaría un re-embedding del corpus completo y la promesa del informe §3.3 («RRHH sale al coste de un campo») dejaría de ser cierta. Ver enmiendas a RAG.4 y RAG.7.
>
> **Posición en el orden**: ING.0.1→ING.0.5 → carga del corpus v1 → RAG.1 (baseline) → RAG.2 (consolidación) → VIS.1→VIS.3 → resto del Bloque RAG → Bloque SYNC.

---

### Prompt ING.0.1 (RED/GREEN) — Vocabulario controlado como dato versionado

**Modelo sugerido**: **Sonnet** — modelo + servicio + CLI con alcance cerrado; la decisión de diseño (ejes en código, términos en tabla) viene dada aquí.

```
# PROMPT ING.0.1 (RED/GREEN) — Ámbitos y submaterias como dato, no como enum
# Deploy: cloud  (HubConfigBase: es configuración institucional, se sincroniza cloud→edge)

## Decisión de diseño que gobierna el prompt
Los EJES son estructura (pocos, estables, y añadir uno exige código que lo consuma) → StrEnum
en código. Los TÉRMINOS son dato (cambian sin tocar código) → filas en tabla. No hay
CheckConstraint sobre los códigos de término: sería exactamente lo que impide revisar el
vocabulario.

## Modelo (database/config_models.py — HubConfigBase)
- VocabularyAxis (StrEnum en código): 'ambit' | 'submateria' | 'rang' | 'colectiu' | 'tipus'.
- HubVocabularyTerm:
    id, organizacion_id (FK hub_organizaciones ondelete CASCADE), axis String(20) NOT NULL,
    codi String(80) NOT NULL, nom_primari String(255), nom_secundari String(255) | None,
    parent_codi String(80) | None      # submateria → su ámbito; jerarquía en la misma tabla
    descripcio_router Text | None      # el texto que ve el router en el índice del Nivel 0
    ordre Integer default 0,
    vigent Boolean NOT NULL default True,
    substituit_per_codi String(80) | None,
    created_at, updated_at
  UniqueConstraint(organizacion_id, axis, codi) — clave natural, base de la idempotencia.
- Renombrar / fusionar un término = fila nueva + la vieja a vigent=False con
  substituit_per_codi apuntando a la nueva. **La cadena de substituit_per_codi ES la traza de
  auditoría**: no se crea tabla de historial aparte.
- Migración Alembic + sembrado NO incluido aquí (lo hace el CLI).

## Servicio (services/vocabulary_service.py)
- validate(axis, codis) -> list[str]: devuelve los códigos DESCONOCIDOS o no vigentes (vacío = OK).
- resolve(axis, codi) -> str: sigue la cadena substituit_per_codi hasta el término vigente
  (con corte por ciclo → error explícito, no bucle infinito).
- build_router_index(organizacion_id) -> str: el índice de submaterias del Nivel 0, agrupado por
  ámbito, con descripcio_router. Debe caber en el orden de magnitud medido (~2.3k tokens para 58).
- reclassify(axis, codi_antic, codi_nou): UPDATE de los documentos afectados siguiendo la
  substitución. **No re-embebe nada** (ver regla 2 del bloque) — devuelve el recuento tocado.

## Frontera edge/cloud (regla dura de CLAUDE.md)
El módulo de ingesta es edge y NO puede importar HubVocabularyTerm. Se amplía el protocolo
ConfigProvider (services/config_provider.py:16-23) con:
    async def list_vocabulary(self, axis: str, organizacion_id: uuid.UUID) -> list[VocabularyTermDTO]
implementado en LocalConfigProvider. El DTO es un dataclass del lado edge, no el modelo ORM.

## CLI (python -m ...vocabulary.load)
- Argumentos: --axis, --csv, --organizacion-id, --dry-run.
- Carga ambits.csv (columnas code/nom/…) y submateries.csv (codi;ambit;nom_val;nom_es;abast;…)
  del directorio vocabulari/ del proyecto de normativa. Idempotente por (organizacion_id, axis, codi):
  segunda pasada no duplica y reporta "sin cambios".
- Un CSV con un parent_codi inexistente se rechaza ENTERO (no carga a medias).

## Tests (RED primero) — tests/modules/agents_hub/test_vocabulary_service.py
# should_reject_unknown_submateria_codes
# should_accept_codes_present_and_vigent
# should_reject_code_marked_not_vigent
# should_resolve_renamed_code_to_its_replacement
# should_raise_on_substitution_cycle
# should_build_router_index_grouped_by_ambit
# should_scope_vocabulary_by_organizacion          (dos orgs, taxonomías distintas)
# should_be_idempotent_on_second_csv_load
# should_reject_csv_with_dangling_parent_codi
# should_expose_vocabulary_through_config_provider (frontera: sin import del modelo en edge)
# should_not_declare_check_constraint_on_codi      (guardarraíl del diseño: inspección de metadata)

## Criterio de done
- [ ] Migración aplicada (adjuntar `alembic current`)
- [ ] Los 5 ámbitos y las 58 submaterias cargados desde vocabulari/*.csv, con recuentos reales
- [ ] Índice del Nivel 0 generado y su tamaño en tokens medido y anotado en el cierre
```

---

### Prompt ING.0.2 (RED/GREEN) — Modelo de datos del documento normativo

**Modelo sugerido**: **Sonnet** — migración con criterio explícito de qué es columna y qué es JSONB; sin decisiones abiertas.

```
# PROMPT ING.0.2 (RED/GREEN) — Metadatos del corpus en HubDocument
# Deploy: edge

## Regla que decide el esquema (evita las 56 columnas)
Una columna de primer nivel SOLO si algo la filtra, la ordena o la usa como puerta.
Todo lo demás va a doc_metadata JSONB. Se documenta en el docstring del modelo.

## Migración sobre hub_documents (operational_models.py:142-173)
Columnas nuevas de primer nivel:
- content_class String(20) NOT NULL default 'generic'   # gate de revisión (era del viejo ING.0.1)
- ambit_principal String(80) | None                     # filtro del Nivel 1
- ambits_secundaris ARRAY(String) default []            # amplía alcance (informe §2.3)
- submateries ARRAY(String) default []                  # el filtro propiamente dicho
- submateries_internes ARRAY(String) default []          # contenido disperso (informe §5.2)
- nivell_acces String(20) NOT NULL default 'public'     # 'public'|'intern'|'restringit'
- us_assistents String(20) NOT NULL default 'si'        # 'si'|'restringit'|'no'
- canonica Boolean NOT NULL default True                # una sola versión indexada (informe §6.3)
- versio_idiomatica_de UUID | None                      # la otra lengua, recuperable por id
- estat_vigencia String(20) | None
- vigencia_validada_el DateTime(tz) | None              # NULL ⇒ el asistente ADVIERTE (VIS.3)
- revisat_per String(255) | None, revisat_el DateTime(tz) | None   # revisión de conversión
- data_revisio_prevista Date | None                     # caducidad activa (SYNC.2)
- id_publicacio String(80) | None, indexada              # id estable del registro de publicación.
    Se rellena cuando exista; hoy puede venir vacío. Es la clave de emparejamiento del sync
    (SYNC.1) para que el cambio de transporte NO sea una recarga del corpus. Fallback
    documentado: doc_metadata->>'url_oficial' + language.
- last_seen_at DateTime(tz) | None                       # última vez que la fuente lo declaró.
    Lo estampa cada pasada de censo (ING.0.5). Es el mecanismo que hace segura la detección de
    retiradas: se marca lo que el último censo NO vio, no lo que "falta" en una carga parcial.
- doc_metadata JSONB NOT NULL default '{}'              # rang, aplica_a, resum_router,
    preguntes_tipus, termes_bilingues, tipus_font, font_autoritativa, deroga, derogat_per,
    url_oficial, motiu_exclusio, original_pdf_sha256, converter/docling_version…
- ARRAY y no tabla de relación: mismo criterio ya adoptado en SEC.2.1 para allowed_roles.

Sin columna 'origen' nueva: se REUTILIZA source_kind (ya existe, String(20)) ampliando sus
valores documentados a 'crawler'|'upload'|'publicacio'|'boe'. Duplicar el eje sería deuda.

Índices: btree (chatbot_id, ambit_principal), btree (chatbot_id, nivell_acces),
GIN (submateries), GIN (submateries_internes), GIN (doc_metadata).

## FK que falta y que VIS.1 necesita
hub_document_chunks.document_id existe pero NO tiene FK (operational_models.py:185-187).
VIS.1 filtra los chunks por los metadatos de su documento mediante JOIN — se elige JOIN y no
denormalizar sobre el chunk porque así reclasificar es UN UPDATE sobre hub_documents y no hay
dos copias que divergir. La migración: limpiar huérfanos (document_id que no existe) y añadir
FK → hub_documents.id ondelete CASCADE. Los chunks temporales (document_id NULL, subida de
usuario) siguen siendo válidos y se tratan aparte en VIS.1.

## section_path
Declarada (línea 160) y JAMÁS escrita en todo server/app; solo se lee en 4 sitios. Si ING.0.4
no la puebla con la ruta estructural, se retira por Caso B (borrado directo) con el checklist
de CLAUDE.md. Decidirlo dentro de ING.0.4, no dejarla en el limbo.

## Fallo de despliegue que se arregla aquí (hallado el 2026-07-28)
El ORM declara HubIngestionJob.canonical_url y .original_filename (operational_models.py:237-238)
pero NINGUNA migración las crea: e5f6a7b8c9d0 las trata como opcionales (`if _column_exists`)
porque las creó código fuera de la cadena. En una instalación limpia no existen, y
POST /hub/ingestion/upload las escribe (hub_ingestion_router.py:228, watcher.py:266,277) ⇒ la
subida de documentos falla con UndefinedColumn en un despliegue nuevo. Misma familia que el fallo
de hub_ingestion_sources que arregló 11.2.
- La migración de este prompt añade ambas columnas a hub_ingestion_jobs, guardadas por
  _column_exists (el patrón ya usado en la cadena) para no chocar donde ya estén.
- Test: should_have_ingestion_job_columns_on_fresh_install, sobre el esquema resultante de
  `alembic upgrade head` en BD limpia (reusar el harness de tests/infra/test_migrations_fresh_install.py).
- La columna hub_interactions.metadata existe en instalación limpia y el ORM no la declara: se
  RETIRA en esta misma migración (columna muerta, Caso B) tras comprobar con grep que nadie la lee.

## Tests (RED primero) — tests/modules/agents_hub/test_document_metadata_model.py
# should_default_new_document_to_public_and_canonical
# should_persist_and_read_back_submateries_array
# should_persist_arbitrary_schema_fields_in_doc_metadata
# should_reject_chunk_with_dangling_document_id      (la FK nueva muerde)
# should_cascade_chunk_deletion_when_document_deleted
# should_allow_null_document_id_for_temporary_chunks
# should_have_gin_index_on_submateries               (inspección de índices)
# should_migrate_existing_rows_with_safe_defaults    (fail-closed: nivell_acces='public' solo
#                                                     porque hoy todo el corpus cargado es público;
#                                                     documentarlo en la migración)

## Criterio de done
- [ ] Migración aplicada (`alembic current`) y reversible (downgrade probado)
- [ ] Recuento de huérfanos limpiados por la migración, anotado en el cierre
```

---

### Prompt ING.0.3 (RED/GREEN) — Front-matter como portador + manifiesto derivado

**Modelo sugerido**: **Sonnet** — contratos Pydantic + validación contra vocabulario; alcance cerrado.

```
# PROMPT ING.0.3 (RED/GREEN) — Contrato de metadatos del .md curado
# Deploy: edge

## Decisión de diseño: el portador es el front-matter, el manifiesto se deriva
El .md es autodescriptivo (es lo que hace posible el sync de SYNC.1 y la carga manual con el
mismo contrato). El manifiesto sigue existiendo para corpus SIN front-matter (histórico, BOE):
si un documento trae front-matter, MANDA el front-matter; si no, manda la entrada del manifiesto.

## Parser (ingestion/corpus/frontmatter.py)
- parse(raw_md) -> (metadata: dict, body: str). Front-matter YAML delimitado por '---'.
- **El hash y el chunking se calculan SOBRE EL BODY, nunca sobre el front-matter.** Es la
  decisión con más consecuencias del prompt: así un cambio SOLO de metadatos no altera
  content_hash → no dispara re-chunk ni re-embedding, y un cambio de texto sí. Hoy
  hash_content() recibiría el front-matter como parte del contenido (watcher.py:94-95) y
  cualquier reetiquetado costaría reindexar el corpus entero.
- Un .md sin front-matter no es error: devuelve ({}, raw_md).

## Contratos (ingestion/corpus/manifest.py)
- CorpusDocumentEntry (Pydantic frozen): relative_path (.md), source_url, language,
  id_publicacio | None (id estable del registro de publicación; hoy puede ir vacío, ver ING.0.2),
  content_class ('regulation'|'faq'|'generic'), title | None, original_pdf_sha256 | None,
  converter/docling_version | None, revisat_per | None, revisat_el | None,
  ambit_principal | None, ambits_secundaris: list[str] = [], submateries: list[str] = [],
  submateries_internes: list[str] = [], nivell_acces = 'public', us_assistents = 'si',
  canonica: bool = True, versio_idiomatica_de | None, estat_vigencia | None,
  vigencia_validada_per | None, vigencia_validada_el | None, data_revisio_prevista | None,
  motiu_exclusio | None, extra: dict = {}  (→ doc_metadata).
- CorpusManifest: chatbot/organizacion destino, created_at, documents: list[...].
- Validación:
  * rutas relativas, sin absolutas ni '..';
  * content_class 'regulation' EXIGE revisat_per + revisat_el (revisión obligatoria, se
    conserva del contrato anterior);
  * ambit_principal y submateries se validan contra VocabularyService vía ConfigProvider;
    término desconocido ⇒ error que ENUMERA los códigos no reconocidos (no falla en el primero);
  * us_assistents == 'no' EXIGE motiu_exclusio (informe §4: convierte «no se publica» en
    decisión auditable en vez de silencio);
  * nivell_acces y us_assistents contra sus listas cerradas (sí son enumeraciones estables).
- El mapeo de normativa_uji_log.json a este contrato se DOCUMENTA (docstring o docs/) sin
  acoplar el loader a ese formato.

## Tests (RED primero) — tests/modules/agents_hub/ingestion/test_corpus_manifest.py
# should_reject_absolute_or_parent_paths
# should_require_review_for_regulation_class
# should_allow_missing_review_for_faq_class
# should_parse_frontmatter_and_strip_it_from_body
# should_hash_body_without_frontmatter               (el test central del prompt)
# should_not_change_hash_when_only_metadata_changes
# should_change_hash_when_body_changes
# should_treat_md_without_frontmatter_as_empty_metadata
# should_reject_unknown_submateria_against_vocabulary
# should_list_all_unknown_codes_not_just_the_first
# should_require_motiu_exclusio_when_us_assistents_is_no
# should_prefer_frontmatter_over_manifest_entry
# should_roundtrip_manifest_json
```

---

### Prompt ING.0.4 (RED/GREEN) — Chunker jerárquico de 5 niveles + anclas de artículo

**Modelo sugerido**: **Sonnet** — cambio acotado en el chunker con efecto medible en las citas.

> **Especificación del formato: `docs/CONTRATO_MD_CORPUS.md`** (2026-07-28). Es el contrato que
> aplica el conversor del corpus y el generador de publicación; este prompt implementa el lado
> consumidor. Corrección respecto a la primera versión de este plan: **son 5 niveles, no 4** —
> faltaba la Sección, que aparece en 280 casos del corpus medido.

```
# PROMPT ING.0.4 (RED/GREEN) — Jerarquía real y cita por artículo
# Deploy: edge

## Contexto medido
El corpus tiene 4.649 artículos, 685 capítulos, 432 títulos, 280 secciones y 675 disposiciones
marcados como encabezado, pero HOY casi todos aplanados en '##'. El corpus convertido y el
modelo de publicación nuevo emiten jerarquía real y ancla estable por unidad citable, según
docs/CONTRATO_MD_CORPUS.md:

    #      documento (uno por fichero)
    ##     preámbulo | título | grupo de disposiciones | anexo | división (docs sin articulado)
    ###    capítulo
    ####   sección
    #####  UNIDAD CITABLE: artículo | disposición | apartado de resolución | unidad ordinal

**Contrato v2 (2026-07-29)**: las anclas son **oportunistas, no obligatorias**, y las divisiones
estructurales (título/capítulo/sección) NO llevan ancla. El hub reconstruye la ruta del TEXTO del
encabezado, no del ancla, así que no pierde nada. El chunker debe degradar sin ruido cuando no hay
ancla: verificado sobre el corpus real (12.044 fragmentos, ancla presente en una parte).

El nivel lo determina el TIPO de elemento, no su anidamiento: un artículo es '#####' también en
una norma sin títulos ni capítulos. Por eso el chunker PUEDE fiarse del nivel, y por eso hay
saltos de nivel legítimos ('#####' bajo '##' en las disposiciones) que no debe tratar como error.
El chunker solo sigue 3 niveles hoy (chunker.py:27-31), así que artículos y secciones se
perderían como nivel.

## Cambios en ingestion/chunker.py
- headers_to_split pasa a 5 niveles: header_1..header_5.
- Extracción del ancla del propio encabezado, sintaxis de atributos Pandoc/kramdown
  ('##### Article 14. Import de la dieta {#art-14}'):
  * 'ancora' va a chunk_metadata;
  * el token '{#...}' se ELIMINA del texto del chunk (es ruido para el embedding y para el
    usuario); el resto del encabezado se conserva (strip_headers=False sigue vigente: RAG.7 lo
    necesita).
- 'ruta': lista de encabezados ancestros (['Títol I','Capítol III','Secció 2a']) en
  chunk_metadata, para que un artículo recuperado aislado no pierda el contexto que le da su
  capítulo (informe §5.2).
- Un .md sin anclas ni jerarquía sigue funcionando: ancora=None, ruta con lo que haya. Los
  documentos sin articulado (41 de 226: protocolos, planes, anexos de tablas) son válidos.
- Las anclas son las MISMAS en las dos versiones idiomáticas de una norma (prefijo neutro:
  'art-14' vale para «Article 14» y «Artículo 14»), lo que permite que una cita resuelva contra
  cualquiera de las dos. VIS.3 lo aprovecha.

## Cita verificable (el pago de este prompt)
Cuando el chunk tiene 'ancora', la URL de la evidencia es canonical_url + '#' + ancora. Se
aplica en el punto donde se construye la evidencia, para las tres estrategias.

## section_path (deuda heredada, se cierra aquí)
Poblarla con la ruta estructural del documento; si no encaja, retirarla por Caso B con el
checklist completo de CLAUDE.md (grep de los 4 lectores: long_context_strategy.py:65,
agentic_strategy.py:33, list_documents.py:28, md_agent_selector_pipeline.py:54).

## Troceado consciente de tablas (añadido el 2026-07-28, medido sobre el corpus convertido)
El corpus trae las tablas en bloques delimitados y autodescriptivos:

    <!-- TABLA-TEXT: t01.png | pàg. 21 | 2x6 | markdown -->
    | Sou | Complement de destinació (CD) | ... |
    | --- | --- | ... |
    | 1.288,31 € | 924,48 € | ... |
    <!-- /TABLA-TEXT -->

Medido: 54 bloques en 13 de los 226 documentos, 49 en markdown (pipe) y 5 en html (los de
colspan/rowspan, que los pipes no pueden expresar). **30 de los 54 superan los 1.000 caracteres
del chunk_size**, mediana 1.161, máximo 11.886.

Sin tratamiento especial, RecursiveCharacterTextSplitter los parte por '\n' —frontera de fila,
que está bien— pero **todos los fragmentos menos el primero pierden la fila de cabecera**: quedan
importes sin nombre de columna. Es peor que no tener el dato, porque se recuperan igual y
sostienen una respuesta segura y falsa sobre una cuantía.

- Detectar el bloque TABLA-TEXT y tratarlo como unidad: si cabe en el presupuesto del chunk, NO
  se parte aunque supere chunk_size (una tabla partida vale menos que una tabla larga).
- Si no cabe, partir **por filas** y **repetir la fila de cabecera** (y el separador '| --- |')
  al principio de cada fragmento. Para los bloques 'html', repetir el <thead> y cerrar/reabrir
  <table> en cada fragmento.
- Llevar a chunk_metadata la procedencia de la cabecera del marcador: 'taula_origen' (PNG),
  'pagina', 'dimensions'. Permite que una cita diga de qué tabla y de qué página sale un importe.
- El formato se lee del ÚLTIMO campo del marcador, no se adivina del contenido.

## Regla dura que hereda el Bloque RAG
Solo se embebe contexto ESTRUCTURAL (título/capítulo/artículo), que es estable. La taxonomía
(ámbito, submaterias) NO entra nunca en el texto embebido. Ver enmienda a RAG.7.

## Tests (RED primero) — tests/modules/agents_hub/ingestion/test_chunker_hierarchy.py
# should_split_on_five_heading_levels
# should_treat_article_as_level_five_without_intermediate_divisions  (norma sin títulos)
# should_handle_level_jump_from_group_to_citable_unit                (disposiciones: ## → #####)
# should_extract_article_anchor_into_metadata
# should_extract_anchor_from_disposicio_and_annex
# should_strip_anchor_token_from_chunk_text
# should_keep_heading_text_in_chunk_content
# should_record_ancestor_route_in_metadata
# should_include_seccio_in_the_route
# should_handle_md_without_anchors_or_hierarchy
# should_handle_document_without_articulado
# should_build_citation_url_with_anchor_fragment
# should_not_include_taxonomy_in_embedded_text     (guardarraíl de la regla dura)
# --- troceado de tablas ---
# should_keep_small_table_block_in_one_chunk
# should_not_split_table_block_that_fits_even_over_chunk_size
# should_repeat_header_row_in_every_chunk_of_a_split_pipe_table
# should_repeat_thead_and_reopen_table_tag_for_split_html_table
# should_split_pipe_table_on_row_boundaries_never_mid_row
# should_record_table_provenance_in_chunk_metadata   (taula_origen, pagina, dimensions)
# should_read_format_from_marker_not_from_content
# should_handle_table_block_without_declared_format  (degradación: tratar como markdown)

## Criterio de done
- [ ] Chunks regenerados con corpus_recalculator sobre el corpus de prueba
- [ ] Una cita real con fragmento #art-N verificada extremo a extremo
- [ ] section_path poblada o retirada; grep limpio si se retira
- [ ] Comprobado contra los 30 bloques de tabla que superan chunk_size: ningún fragmento con
      importes sin fila de cabecera (adjuntar un fragmento real de la tabla de retribuciones del
      Convenio colectivo, que es el caso canónico)
```

---

### Prompt ING.0.5 (RED/GREEN) — Reconciliador de corpus + CLI sobre carpeta local

**Modelo sugerido**: **Opus** — es el prompt con más decisiones embebidas del bloque: semántica de censo, salvaguarda de poda y el protocolo que evita que SYNC.1 duplique el pipeline.

```
# PROMPT ING.0.5 (RED/GREEN) — Un reconciliador, dos fuentes (la segunda llega en SYNC.1)
# Deploy: edge

## Por qué este prompt es el reconciliador y no "el cargador"
El pipeline de publicación no existirá hasta dentro de meses. Durante ese tiempo el CLI **es** el
mecanismo de mantenimiento del corpus, no una carga inicial. Cuando llegue el transporte
programático, debe añadirse una FUENTE, no un segundo pipeline. Por tanto la reconciliación se
escribe aquí, una sola vez, detrás de un protocolo.

## Protocolo de fuente (ingestion/corpus/source.py)
class CorpusSource(Protocol):
    def is_census(self) -> bool                      # ¿declara el corpus COMPLETO?
    async def list_entries(self) -> list[CorpusDocumentEntry]
    async def read_body(self, entry) -> str          # el .md ya sin front-matter (ING.0.3)
- LocalDirectorySource(dir, manifest | None) en este prompt.
- PublicationMcpSource en SYNC.1. Nada más cambia allí.

## Reconciliador (ingestion/corpus/reconciler.py)
Por cada entrada, contra hub_documents del chatbot destino. Emparejamiento: id_publicacio si
viene; si no, url_oficial + language (fallback documentado en ING.0.2).
- ausente en el hub                → ingerir
- hash del body distinto           → re-ingerir solo ese documento
- hash igual, metadatos distintos  → **UPDATE de metadatos SIN re-chunk ni re-embedding**
- hash y metadatos iguales         → omitido
- us_assistents == 'no'            → no se ingiere; omitido con su motiu_exclusio
- content_class 'regulation' sin revisión → rechazado antes de tocar la BD
Toda entrada vista, cambiada o no, estampa last_seen_at.

## Censo y poda: el modo peligroso
- Sin --prune (default) el reconciliador NO retira nada. Una carga parcial nunca puede
  interpretarse como censo.
- Con --prune, y SOLO si source.is_census() es True: los documentos del chatbot cuyo
  last_seen_at es anterior a esta pasada se marcan (us_assistents='no',
  motiu_exclusio='retirada_de_la_font') y emiten HubContentFinding para la cola del admin.
  **Nunca se borran.** Retirada de la fuente ≠ derogación: la distinción la hace una persona.
- **Salvaguarda de proporción**: si la poda afectaría a más del N % del corpus (default 10 %),
  ABORTA y exige --force-prune con el recuento por delante. Es la red que evita convertir un
  `--dir` mal escrito en la retirada del corpus entero.

## CLI (python -m ...ingestion.corpus.load)
- Argumentos: --dir, --manifest (opcional si hay front-matter), --chatbot-id, --dry-run,
  --census, --prune, --force-prune, --prune-threshold.
- Por cada .md: parse de front-matter (ING.0.3) → passthrough del body (NO reconvierte, NO
  llama a Docling) → IngestionWatcher.process_source, que ya hace hash → detect_language →
  MarkdownChunker → embedding → HubDocumentChunk.
- language del front-matter/manifiesto MANDA sobre detect_language cuando viene dado.
- source_kind = 'publicacio' | 'boe' | 'upload' según el origen declarado.
- Persiste TODOS los campos de ING.0.2, incluidos los ARRAY y doc_metadata.
- Reutiliza validate_upload(file, kind=UploadKind.TEXT) de SEC.6 (core/uploads.py) — no
  reimplementar validación de extensión ni de binario disfrazado.
- **Un HubIngestionJob por ejecución**, con los seis recuentos (ingeridos / re-ingeridos /
  metadatos actualizados / omitidos / rechazados / retirados). Si el CLI va a ser el mecanismo
  de mantenimiento durante meses, el historial tiene que estar en la BD y visible en el admin,
  no solo en la consola de quien lo ejecutó.
- --dry-run: el plan completo, incluido lo que se podaría, sin escribir.

## Watcher: la ampliación que esto exige
Hoy, en el acierto de hash, el watcher solo refresca canonical_url/title/updated_at
(watcher.py:101-114). Debe además refrescar los metadatos de ING.0.2. Es la ruta que hará barata
la reclasificación cuando SG revise el vocabulario, así que tiene test propio.

## Tests (RED primero) — test_corpus_reconciler.py + test_corpus_loader.py
# should_ingest_markdown_passthrough_without_docling
# should_persist_all_metadata_fields_on_hub_document
# should_prefer_declared_language_over_detection
# should_skip_unchanged_document_by_content_hash
# should_update_metadata_without_rechunking_when_only_metadata_changed
# should_reingest_only_changed_document
# should_match_existing_document_by_id_publicacio
# should_fall_back_to_url_and_language_when_id_publicacio_missing
# should_stamp_last_seen_at_on_every_entry_including_unchanged
# should_refuse_regulation_entry_without_review
# should_skip_documents_marked_us_assistents_no_with_reason
# should_not_prune_anything_without_the_prune_flag
# should_not_prune_when_source_is_not_a_census
# should_mark_and_emit_finding_for_pruned_document_without_deleting
# should_abort_prune_above_proportion_threshold
# should_prune_above_threshold_only_with_force
# should_record_one_ingestion_job_per_run_with_counters
# should_report_plan_in_dry_run_without_writing

## Cierre del bloque ING.0
- [ ] Cargar el corpus curado contra el chatbot destino y **congelar el manifiesto como
      `corpus v1`** (versionado), para que la baseline de RAG.1 no se mueva después
- [ ] Cifras reales del HubIngestionJob de la carga
- [ ] Segunda pasada sobre la misma carpeta: todo omitido, cero chunks nuevos (idempotencia real,
      no solo en test)
- [ ] Tercera pasada con un `.md` reetiquetado: metadatos actualizados y **cero re-embeddings**
- [ ] Verificar una cita trazable (source_url + ancla) en una consulta de prueba
- [ ] Confirmar que el crawler está desactivado para este chatbot (fuente autoritativa única)
- [ ] Documentar en `docs/` el procedimiento de actualización por CLI, que es el que estará en
      uso hasta que exista el pipeline de publicación
```

---

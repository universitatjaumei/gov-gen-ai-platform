## Bloque 9Q — Motor de auditoría de sitios web (Subfase 1.A → 1.C, COMPLETO 9Q.0–9Q.9)

> ### ⚠ ALCANCE REESCRITO EL 2026-08-02 — leer antes que nada de lo que sigue
>
> **El código de 9Q no cambia; cambia de qué es parte.** Ver `docs/DECISION_CURACION_SEPARADA.md`.
>
> Este bloque se escribió bajo la hipótesis de una **ingesta más o menos automatizada** de
> información pública: apuntar el spider a un sitio, ingerir lo descubierto y arreglar la calidad
> después con detectores. **Preparar el corpus normativo de la UJI ha falsado esa hipótesis.**
> Ese corpus era el mejor caso posible —PDFs de normas con filtro previo de Secretaría General,
> catálogo y numeración estable— y aun así dejarlo ingerible exigió front-matter derivado del
> catálogo, decisión humana de consolidación norma a norma, un panel de revisión construido para
> eso y un parche al generador de HTML para tener anclas por artículo. Si el mejor caso exige
> todo eso, un conjunto de páginas rastreadas —sin versión canónica declarada, sin distinción
> entre vigente y derogado— **no es un corpus: es materia prima**.
>
> **Cómo se lee ahora este bloque.** 9Q no es «calidad del contenido web ingerido al servicio del
> RAG». Es **el motor de la herramienta de curación**, que es una actividad *previa* al asistente
> y con producto propio. En concreto:
>
> - **La salida principal es el informe de auditoría**, dirigido al equipo web de la
>   administración. Tiene valor por sí solo, sin que exista ningún chatbot: auditar la coherencia
>   de lo publicado es una necesidad de transparencia. La higiene del retriever (`superseded`,
>   `quality_score`) pasa a ser el **efecto secundario útil**, no la razón de ser.
> - **No hay ingesta automática de web a corpus.** Que una página sea nueva o haya cambiado es
>   **una señal para el curador**, nunca un disparador de ingesta. Donde el texto de abajo dice
>   «auto-encoladas si casan con una `HubCorpusSelection`», léase «propuestas al curador».
> - **`CorpusSelectionService` es el paso de publicación**, no un detalle de la ingesta: es el
>   punto exacto en que un humano decide que una página entra. Hoy está enterrado en
>   `ingestion/quality/selection_service.py` y debe ser explícito y visible en la UI de curación.
> - **La frontera con el asistente es `docs/CONTRATO_MD_CORPUS.md`**, no una interfaz de código.
>
> **Esto ya estaba latente en el modelo de datos que 9Q construyó**: `HubWebSite` cuelga de
> `organizacion_id` y **no tiene `chatbot_id`** —«propiedad de la organización, no del chatbot»,
> dice su propio docstring—, y `HubContentFinding` admite dos sujetos con un `CHECK` que exige
> exactamente uno. El diseño ya separaba las dos mitades; lo que faltaba era decirlo.
>
> **Lo que se conserva y se refuerza**: el bucle de RAG.14 (preguntas sin responder → huecos de
> corpus). Es la conexión legítima entre asistente y curación, y la razón por la que **no** se
> parte el sistema en dos aplicaciones: el corpus no se cura una vez, se cura continuamente
> contra el uso real.
>
> **Movimiento de código**: no se hace aquí. Va en el **Bloque CUR**, entre CAL y Deploy.

**Objetivo del bloque (redacción original, 2026-05-27)**: separar dos conceptos que hoy el modelo funde, y construir sobre esa separación un **motor de detección de calidad a nivel de sitio**. Hoy todo cuelga de `chatbot_id` y no existe ninguna entidad "sitio"; `HubIngestionSource` es solo un monitor de **una URL suelta por chatbot**. Eso impide (a) escanear todo un sitio para auditar calidad mientras se ingiere solo una parte, (b) que una misma página alimente varios chatbots, y (c) un único crawl por sitio (hoy N chatbots = N crawls del mismo servidor público).

El bloque introduce tres entidades y dos salidas:

**Entidades nuevas** (operacionales, edge, en `operational_models.py`):
- **`HubWebSite`** — propiedad del cliente/administración, **no** del chatbot. URL raíz, sitemap, config de crawl, cadencia, `audit_semantic_scope`. Unidad de **crawl + auditoría**.
- **`HubCrawledPage`** — propiedad del sitio. Cada URL descubierta en el crawl, con sus señales (Last-Modified/ETag/sitemap lastmod/canonical/año) y flags de calidad (`superseded`, `quality_score`, `superseded_by_page_id`). Los `HubContentFinding` referencian **páginas**, no chatbots.
- **`HubCorpusSelection`** — propiedad del chatbot, referencia un sitio + regla de selección (prefijo de path / sección de sitemap / manual). Realiza el mapeo **N:M** página→chatbot: promociona páginas rastreadas a `HubDocument` del/los chatbots.
- `HubDocument` gana `crawled_page_id` (FK opcional a `HubCrawledPage`, `ondelete=SET NULL`, sin `relationship()`). Los PDFs subidos siguen con `crawled_page_id=None`.

**Dos salidas independientes** sobre el mismo análisis:
1. **Higiene del RAG** — flags `superseded`/`quality_score` sobre `HubCrawledPage`; el retriever excluye por defecto los `HubDocument` cuya página de origen esté superseded, en **todos** los chatbots que la ingirieron.
2. **Informe de auditoría web por sitio** — documento estructurado (JSON + visor admin + export DOCX/PDF) dirigido al **equipo web de la administración** para que mejore su propio sitio público.

**Justificación de la ubicación (antes de Fase 11)**:
- Es una mejora de **correctitud del producto central** (calidad de las respuestas del chatbot), de mayor prioridad que la distribución (Fase 11) o el deploy (D.1–D.5).
- Reutiliza crawler, embeddings y retriever ya completados en Subfases 1.A/9B.
- Introduce nuevos servicios y un scheduler; Fase 11.2 debe poder incluirlos en el `docker-compose.prod.yml` público; por eso se cierra antes.

**Decisión arquitectónica (2026-05-27, revisada)**: **split sitio/corpus con motor de detección a nivel sitio**, frente al diseño anterior per-chatbot. Razones:
1. **No rastrear dos veces.** Son webs de administración pública: varios crawlers golpeando los mismos servidores es impolite, dispara rate limits y parece abuso. Un único crawl por sitio que emite hallazgos estructurados es lo correcto técnica y éticamente. El modelo per-chatbot anterior **no cumplía esto** en cuanto dos chatbots bebían del mismo sitio.
2. **El alcance del crawl ≠ el alcance de la ingesta.** La administración quiere auditar **todo** su sitio pero ingerir solo **partes** seleccionadas, posiblemente repartidas entre **varios** chatbots. Eso exige una entidad sitio por encima del chatbot y una capa de selección N:M.
3. **El informe es otro consumidor** de la misma tabla de hallazgos (no otro motor): reutiliza `HybridRetriever` (similitud pgvector) para clustering y el patrón de `source_scheduler` para la cadencia.

**Reemplazo de `HubIngestionSource` (decisión 2026-05-27)**: `HubWebSite` + `HubCorpusSelection` **sustituyen** al monitor de URL suelta. Las fuentes existentes se migran a (sitio + selección) y `HubIngestionSource`, su scheduler (`source_scheduler.py`) y sus endpoints se **eliminan** (CLAUDE.md: sin mecanismos paralelos ni shims). **La ingesta de PDF subido (`POST /hub/ingestion/upload` → `HubIngestionJob` → `HubDocument`) es un flujo independiente y se mantiene intacta**: un chatbot se alimenta de PDFs subidos (`crawled_page_id=None`) **+** páginas seleccionadas del sitio (`crawled_page_id` poblado).

**Actualización periódica**: el recrawl programado hace **diff de sitemap** — páginas **nuevas** → candidatas a ingesta (auto-encoladas si casan con una `HubCorpusSelection`, si no afloran en el informe como "nuevas sin clasificar"); **cambiadas** → re-embed; **desaparecidas** → finding + retirada del corpus.

**Cobertura de la auditoría semántica (`audit_semantic_scope`, por sitio)**: las páginas rastreadas pero no ingeridas no tienen embeddings.
- `ingested` (default, híbrido): el detector determinista corre sobre **todo** el sitio (gratis); el semántico (juez LLM) solo sobre páginas ya ingeridas. Para sitios grandes.
- `full`: se embeben todas las páginas rastreadas y el semántico cubre el sitio completo. Para sitios pequeños donde interesa cobertura total. El administrador lo elige por sitio.

**Frontera edge-cloud**: todo el bloque **es edge**. El motor procesa documentos/chunks/páginas del cliente; el informe es inherentemente sobre el contenido concreto del cliente y **no se puede anonimizar de forma útil**, por lo que se sirve desde el edge node. El cloud, como mucho, vería métricas agregadas anonimizadas vía la sync API — backlog post-MVP, **no entra en 9Q**.

**Lo que NO incluye este bloque**:
- **Accesibilidad / WCAG** del sitio público (backlog v2; la del propio frontend ya está en Fase 20).
- Reescritura/corrección automática del contenido del sitio (el informe es de **diagnóstico**; la acción correctiva la realiza el equipo web humano).
- Sync de métricas agregadas hacia el cloud (backlog post-MVP de la sync API).
- Validación exhaustiva de enlaces rotos mediante recrawl dedicado (el MVP detecta huérfanos/errores a partir de las señales del crawl y del diff de sitemap, no lanza un recrawl de validación de enlaces).

**Reglas duras del bloque 9Q**:
- Todo el módulo de calidad vive en `server/app/modules/agents_hub/ingestion/quality/` y **es edge**. Las entidades nuevas (`HubWebSite`, `HubCrawledPage`, `HubCorpusSelection`) viven en `operational_models.py` sobre `HubOperationalBase`.
- Los routers nuevos se etiquetan `Deploy: edge` y se registran en `_register_edge` de `main.py`.
- **El análisis nunca bloquea el crawl ni la ingesta.** La detección corre como job asíncrono post-crawl o bajo demanda; el crawl/indexado sigue su curso aunque el análisis falle.
- **El LLM solo se invoca sobre clusters ya filtrados por similitud de embeddings** (control de coste). Jamás se llama al LLM por cada par de páginas.
- El motor **lee** modelos operacionales (`HubWebSite`, `HubCrawledPage`, `HubDocument`, `HubDocumentChunk`) y **escribe** `HubContentFinding` + los flags `superseded`/`quality_score` en `HubCrawledPage`. No toca modelos de configuración. **Sin `relationship()` cross-base**; las FK a chatbot/documento se resuelven por id con query explícito.
- **La anonimización previa al LLM es responsabilidad del módulo edge** (reutiliza el `AnonymizerService`/hooks de 9R.5.5/Fase 13 si el contenido a juzgar puede contener PII antes de enviarse al juez LLM).

---

### Prompt 9Q.0 (RED/GREEN) — Modelo sitio/página/selección + reemplazo de `HubIngestionSource`

**Modelo sugerido**: **Opus** — define todo el modelo de datos nuevo y la relación página↔documento↔chatbot, decide la migración que retira `HubIngestionSource` sin romper la ingesta de PDF, y establece las invariantes cross-base. Decisiones de diseño embebidas y refactor de código ya en verde.

**Objetivo**: crear las tres entidades que separan crawl/auditoría (sitio) de ingesta (corpus de chatbot), sus repos, la FK `crawled_page_id` en `HubDocument`, y **retirar `HubIngestionSource`** migrando las fuentes existentes a (sitio + selección). No incluye crawl ni detección todavía (eso es 9Q.2+).

**Contexto**: `operational_models.py` (sobre `HubOperationalBase`). Hoy `HubIngestionSource` (monitor de 1 URL/chatbot) se usa en `hub_ingestion_router.py`, `source_scheduler.py`, `spider_factory.py` y tests de integración. El upload de PDF (`POST /hub/ingestion/upload` → `HubIngestionJob` → `IngestionWatcher`) **no** usa `HubIngestionSource` y no se toca. Sin `relationship()` cross-base (regla edge-cloud de CLAUDE.md).

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.0 (RED/GREEN) — Entidades sitio/página/selección

Deploy: edge.

## ORM — operational_models.py (HubOperationalBase)

class HubWebSite:
  __tablename__ = "hub_web_sites"
  id, client_id UUID (index, dueño = administración, NO chatbot), name str(255),
  root_url str(2048), sitemap_url str(2048)|None, spider_type str(50) default "generic",
  config_json JSONB default dict, crawl_interval_hours int default 24,
  audit_semantic_scope str(20) default "ingested"  # "ingested" | "full"
  last_crawled_at datetime|None, status str(20) default "active", error_message Text|None,
  created_at.

class HubCrawledPage:
  __tablename__ = "hub_crawled_pages"
  id, site_id UUID (index, FK hub_web_sites.id ondelete=CASCADE — NO relationship()),
  url str(2048), canonical_url str(2048)|None, content_hash str(64)|None,
  title str(512)|None, token_count int|None, language str(10)|None,
  markdown_content Text|None,   # texto rastreado de la página; necesario para empty/thin (9Q.3)
                                # y para embeber páginas no ingeridas en modo full (9Q.4)
  # señales de actualidad (las pobla 9Q.2):
  http_last_modified datetime|None, http_etag str(255)|None, sitemap_lastmod datetime|None,
  declared_canonical_url str(2048)|None, content_year int|None,
  # flags de higiene (los consolida 9Q.5):
  superseded bool default False (index), quality_score Float|None,
  superseded_by_page_id UUID|None,
  first_seen_at, last_seen_at, last_crawled_at datetime|None,
  status str(20) default "active"  # "active" | "gone" (fuera del sitemap) | "error" (fetch falló)
  error_message Text|None,         # mensaje del fallo de fetch de ESTA página (si status=="error")
  UniqueConstraint(site_id, url) name="uq_page_site_url".

class HubCorpusSelection:
  __tablename__ = "hub_corpus_selections"
  id, chatbot_id UUID (index), site_id UUID (index, FK hub_web_sites.id ondelete=CASCADE),
  rule_type str(20)  # "path_prefix" | "sitemap_section" | "manual"
  rule_value str(2048)|None  # p.ej. "/tramites/" para path_prefix; None para manual
  auto_ingest_new bool default True  # encolar automáticamente páginas nuevas que casen
  created_at.
  # El mapeo N:M efectivo página→documento se materializa en HubDocument.crawled_page_id;
  # una selección manual puede tener su propia tabla de enlaces si 9Q.7 lo necesita.

## FK nueva en HubDocument (mismo fichero)
  crawled_page_id UUID|None (index, FK hub_crawled_pages.id ondelete=SET NULL — NO relationship())
  # PDFs subidos => None. Documentos de crawl => apuntan a su página de origen.

## Repos — ingestion/quality/site_repo.py
WebSiteRepo(session): create, get, list_by_client, update, delete (cascade páginas).
CrawledPageRepo(session): upsert(site_id, url, ...) (respeta uq_page_site_url),
  list_by_site(site_id, status?), get, mark_gone(page_ids), get_by_canonical(site_id, canonical).
CorpusSelectionRepo(session): create, list_by_chatbot, list_by_site, delete,
  matches(selection, page_url) -> bool  # evalúa la regla contra una URL.

## Migración Alembic — retirada de HubIngestionSource
1. Crea hub_web_sites, hub_crawled_pages, hub_corpus_selections; añade crawled_page_id a hub_documents.
2. DATA MIGRATION: por cada HubIngestionSource existente, crea un HubWebSite (root_url=url,
   client_id derivado del chatbot) + un HubCorpusSelection(chatbot_id, site_id, rule_type="manual").
   (Si no hay forma de derivar client_id en datos de dev, documenta el fallback y créalo nullable.)
3. DROP table hub_ingestion_sources.
Aplica con `uv run alembic upgrade <rev>`. Si la BD no responde, detente y pide arrancarla.

## Retirada de código (CLAUDE.md — borra, no comentes)
- Elimina la clase HubIngestionSource de operational_models.py.
- Elimina source_scheduler.py (check_source/check_all_sources/create_scheduler) y su arranque
  en main.py/lifespan. El scheduler nuevo lo crea 9Q.5.
- Elimina del hub_ingestion_router.py los endpoints de "Fuentes web monitorizadas"
  (list/create/update/delete/check sources). Los endpoints de sitio los crea 9Q.7.
- Ajusta spider_factory.py y los tests de integración que referencian HubIngestionSource.
- grep -r "HubIngestionSource" debe quedar a 0 antes de cerrar.

## Tests (mínimo 12) — tests/modules/agents_hub/integration/test_site_model.py
- CRUD de HubWebSite/HubCrawledPage/HubCorpusSelection vía repos.
- upsert de página respeta uq_page_site_url (2ª llamada actualiza).
- CorpusSelectionRepo.matches: path_prefix casa/no casa; manual siempre False salvo enlace explícito.
- HubDocument.crawled_page_id default None; FK SET NULL al borrar página.
- Borrar sitio cascada páginas (y selecciones).
- audit_semantic_scope default "ingested"; HubCrawledPage default status "active", markdown_content/error_message None.
- Tras la migración: no queda HubIngestionSource importable (import error esperado en test).
```

**Verificación**: `uv run pytest tests/modules/agents_hub/` verde (incluidos los tests de ingestión adaptados a la retirada de `HubIngestionSource`); migración aplicada (`alembic current`); `grep -r HubIngestionSource` a 0.

---

### Prompt 9Q.1 (RED/GREEN) — Contratos de hallazgos + `HubContentFinding` (clave sitio/página) + repo

**Modelo sugerido**: **Sonnet** — alcance cerrado: contratos Pydantic enumerados, un modelo ORM, un repo CRUD, una migración. Sin decisiones de diseño abiertas (el modelo base ya lo fijó 9Q.0).

**Objetivo**: la taxonomía de hallazgos y el modelo ORM `HubContentFinding`, ahora **rekeyed a sitio/página** (no a chatbot), con su repo. Los flags de higiene ya viven en `HubCrawledPage` (9Q.0).

**Contexto**: usa las entidades de 9Q.0. Un hallazgo es un hecho sobre el **sitio** (páginas), independiente de qué chatbots ingirieron esas páginas.

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.1 (RED/GREEN) — Contratos y modelo de hallazgos de calidad

Deploy: edge.

## Contratos Pydantic — ingestion/quality/contracts.py

- FindingType: Literal[
    "superseded",      # versión más antigua de un proceso con versión nueva detectada
    "duplicate",       # mismo contenido en >1 URL
    "contradiction",   # mismo proceso, datos divergentes
    "empty",           # sin contenido útil (markdown vacío / token_count 0)
    "thin",            # contenido por debajo de umbral mínimo
    "stale",           # no revisada/actualizada en > umbral de días
    "crawl_error",     # la página falló al rastrearse (HubCrawledPage.status/error)
    "orphan_page",     # página marcada gone que aún tiene documentos ingeridos
  ]
- FindingSeverity: Literal["info", "warning", "critical"]
- FindingStatus: Literal["new", "confirmed", "dismissed", "resolved"]
- ContentFinding (Pydantic, frozen=True): id, site_id: UUID, finding_type, severity,
  confidence: float (0..1), page_id: UUID|None, related_page_id: UUID|None,
  source_url: str|None, signal: dict (evidencia: fechas comparadas, score de similitud,
  longitudes, etc.), status, detected_at, reviewed_at: datetime|None, reviewed_by: UUID|None,
  resolution_note: str|None
- _VALID_FINDING_TRANSITIONS + InvalidFindingTransitionError (new→confirmed/dismissed,
  confirmed→resolved/dismissed, dismissed→new; resolved es terminal).

## ORM — operational_models.py (HubOperationalBase)

class HubContentFinding:
  __tablename__ = "hub_content_findings"
  id, site_id UUID (index, FK hub_web_sites.id ondelete=CASCADE — NO relationship()),
  finding_type str(40), severity str(20), confidence Float,
  page_id UUID|None (index, FK hub_crawled_pages.id ondelete=SET NULL — NO relationship()),
  related_page_id UUID|None, source_url str(2048)|None, signal_json JSONB,
  status str(20) default "new" (index), detected_at, reviewed_at|None, reviewed_by|None,
  resolution_note Text|None, created_at.
  UniqueConstraint(site_id, finding_type, page_id, related_page_id) name="uq_finding_dedup".

## Repo — ingestion/quality/findings_repo.py

ContentFindingRepo(session):
  async upsert(finding) -> HubContentFinding   # respeta uq_finding_dedup (ON CONFLICT update)
  async list_by_site(site_id, status?, finding_type?) -> list[HubContentFinding]
  async transition(finding_id, new_status, reviewed_by, resolution_note?) -> HubContentFinding
        # valida contra _VALID_FINDING_TRANSITIONS, lanza InvalidFindingTransitionError
  async get(finding_id) -> HubContentFinding|None

## Migración Alembic
Crea hub_content_findings. Aplica con `uv run alembic upgrade <rev>`. Si la BD no responde,
detente y pide arrancarla.

## Tests (mínimo 12) — tests/modules/agents_hub/unit/test_content_findings.py
- ContentFinding congelado, validación de rangos de confidence.
- Transiciones válidas e inválidas (cada arista + terminal resolved).
- Repo.upsert idempotente bajo uq_finding_dedup (2ª llamada actualiza, no duplica).
- Repo.list_by_site filtra por status y finding_type.
- Repo.transition aplica reviewed_at/reviewed_by y rechaza transición inválida.
- FK page_id SET NULL al borrar la página; site_id CASCADE al borrar el sitio.
```

**Verificación**: `uv run pytest tests/modules/agents_hub/unit/test_content_findings.py` verde; migración aplicada (`alembic current`).

---

### Prompt 9Q.2 (RED/GREEN) — Crawl a nivel sitio + señales en páginas + diff de sitemap

**Modelo sugerido**: **Opus** — desacopla el crawl del modelo per-chatbot al modelo de sitio (refactor de `IngestionWatcher`/spider ya en verde), diseña el diff de sitemap (alta/cambio/baja de páginas) y la captura de señales sobre `HubCrawledPage`. Decisiones de diseño embebidas.

**Objetivo**: rastrear un **sitio completo** una sola vez poblando `HubCrawledPage`, capturar las **señales gratuitas** de actualidad sobre cada página, y producir el **diff de sitemap** que detecta páginas nuevas, cambiadas y desaparecidas. No ingiere todavía en chatbots (eso lo dispara la selección de 9Q.7); aquí solo se materializa el mapa del sitio.

**Contexto**: el crawler vive en `ingestion/spider.py` (`GenericSpider._fetch`, `_extract_links`); el indexado en `ingestion/watcher.py`. 9Q.0 retiró `HubIngestionSource`. Las páginas y sus señales viven en `HubCrawledPage` (9Q.0). El crawl debe recorrer el sitemap/enlaces del sitio, no una URL suelta.

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.2 (RED/GREEN) — Crawl de sitio + señales + diff de sitemap

Deploy: edge.

## Servicio de señales — ingestion/quality/signal_extractor.py
class CrawlSignalExtractor:
  extract_from_headers(headers: dict) -> {http_last_modified, http_etag}  # RFC 7231; tolera ausencia
  extract_canonical(html: str) -> str|None        # <link rel="canonical" href="...">
  extract_content_year(url: str, text: str) -> int|None
        # prioridad: año en path (/2024/) > año más reciente plausible en texto (1990..año+1)
  async fetch_sitemap(base_url|sitemap_url, fetch_fn) -> dict[str,datetime|None]
        # descarga el sitemap.xml una vez, parsea <url><loc><lastmod>; mapea url->lastmod.
        # Soporta sitemap index (múltiples <sitemap>). Falla en silencio ({}) si no hay/no parsea.

## Servicio de crawl de sitio — ingestion/quality/site_crawler.py
class SiteCrawler(session, spider, signal_extractor, page_repo):
  async def crawl_site(site_id) -> SiteCrawlSummary:
    1. Lee HubWebSite. Obtiene el conjunto de URLs objetivo:
       union(sitemap urls, enlaces descubiertos por el spider dentro del dominio raíz).
    2. Por cada URL: _fetch (body + headers), extrae señales, upsert HubCrawledPage
       (markdown_content, content_hash, title, token_count, language + las 5 señales).
       last_crawled_at/last_seen_at=now, status "active".
       Si el fetch de ESA URL falla: upsert la página con status "error" + error_message
       (no aborta el resto del crawl).
    3. DIFF DE SITEMAP:
       - nuevas: URL en el crawl que no existía como HubCrawledPage → status "active", first_seen_at=now.
       - cambiadas: content_hash distinto al previo → marca para re-embed (signal en summary).
       - desaparecidas: páginas activas en BD que ya NO aparecen en este crawl → status "gone".
    4. Actualiza HubWebSite.last_crawled_at; HubWebSite.status "error"+error_message si el crawl
       falla globalmente (los fallos de página concreta van en la página, no en el sitio).
  SiteCrawlSummary: pages_new, pages_changed, pages_gone, pages_error, pages_total, errors.

## Refactor del spider (sin HubIngestionSource)
- GenericSpider._fetch devuelve body + headers (adapta tipo de retorno y call-sites/tests).
- El recorrido del sitio se acota al dominio de root_url; respeta robots si ya se respetaba.
- El sitemap se consulta una vez por sitio, no por página.

## Tests (mínimo 12) — test_site_crawler.py + test_crawl_signals.py
- Parseo Last-Modified válido / ausente / malformado; canonical con/sin tag (primero gana).
- extract_content_year: año en path gana al texto; sin año → None; descarta años absurdos.
- fetch_sitemap parsea XML (fixture) y sitemap index; ausente → {}.
- crawl_site upsert páginas con markdown_content + las 5 señales; segundo crawl idempotente sobre uq_page_site_url.
- diff: URL nueva → page nueva; content_hash cambiado → pages_changed; URL ausente → status "gone".
- fallo de fetch de una URL → esa página status="error"+error_message, el resto del crawl continúa.
- crawl con fallo global deja HubWebSite.status="error" sin crashear.
```

**Verificación**: `uv run pytest tests/modules/agents_hub/` verde (incluidos los tests de spider adaptados a la nueva firma de `_fetch` y a la retirada de `HubIngestionSource`).

---

### Prompt 9Q.3 (RED/GREEN) — Detector determinista: vacías, finas, stale, errores y supersesión por URL+fecha

**Modelo sugerido**: **Sonnet** — reglas deterministas enumerables; sin LLM. La normalización de URL y la precedencia de fechas se especifican explícitamente en el prompt.

**Objetivo**: primera pasada del motor —sin coste de LLM, sobre **todo el sitio**— que emite hallazgos a partir de las señales de `HubCrawledPage`: páginas vacías/finas, stale, con error de crawl, huérfanas, y **supersesión temporal por patrón de URL + fecha**.

**Contexto**: usa los contratos de 9Q.1 (`HubContentFinding`, claves sitio/página) y las señales de 9Q.2 sobre `HubCrawledPage`. Lee `HubCrawledPage` (y `HubDocument` solo para detectar páginas `gone` con documentos aún ingeridos). Escribe hallazgos vía `ContentFindingRepo`.

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.3 (RED/GREEN) — Detector determinista de calidad

Deploy: edge.

## Servicio — ingestion/quality/deterministic_detector.py
class DeterministicQualityDetector(session, *, thin_token_threshold=120, stale_days=365):
  async def analyze(site_id) -> list[ContentFinding]:
    Sobre las HubCrawledPage del sitio, emite (vía ContentFindingRepo.upsert):
      - empty: página con markdown_content vacío/None o token_count==0 → severity critical.
      - thin: token_count < thin_token_threshold (y > 0)            → severity warning.
      - stale: página cuya frescura de CONTENIDO
               max(sitemap_lastmod, http_last_modified, content_year-as-date) sea anterior a
               now-stale_days → severity info. NO incluir last_crawled_at (es siempre ≈ahora tras
               el crawl y anularía la regla). Si las tres señales son None, no se evalúa stale.
               signal incluye la fecha que disparó la regla.
      - crawl_error: HubCrawledPage.status=="error" (error_message poblado) → critical.
      - orphan_page: página status=="gone" que aún tiene HubDocument con crawled_page_id apuntándola
               (query explícito por id, sin relationship)            → warning.
      - superseded (determinista): ver algoritmo abajo.

## Algoritmo de supersesión determinista
  1. Agrupar páginas del sitio por "clave de proceso" = path normalizado de canonical_url
     SIN el segmento de año (quita /2023/, /2024/, query string, fragmentos, trailing slash).
  2. Dentro de cada grupo con >1 página, ordenar por fecha efectiva =
     max(sitemap_lastmod, http_last_modified, content_year-as-date, first_seen_at).
  3. La más reciente es la vigente; las demás → finding superseded con
     related_page_id = id de la vigente, signal = {fechas comparadas, clave de proceso}.
     NO muta todavía HubCrawledPage.superseded (eso lo hace el job 9Q.5 al consolidar);
     aquí solo se emite el hallazgo.
  El detector es idempotente: re-ejecutar no duplica (uq_finding_dedup).

## Tests (mínimo 11) — test_deterministic_detector.py
- empty (markdown_content None/vacío) / thin (justo por encima y por debajo del umbral) / token_count 0.
- stale por señal de contenido antigua; página con señal reciente no marca stale; página con las
  tres señales None NO marca stale (aunque last_crawled_at sea viejo).
- crawl_error desde status=="error" de página.
- orphan_page: página gone con documento aún ingerido.
- supersesión: 3 versiones mismo proceso distinto año → 2 superseded apuntando a la vigente.
- normalización de URL: /proc/2023/x y /proc/2024/x agrupan; /proc/x y /otro/x no.
- idempotencia: segunda pasada no crea hallazgos nuevos.
```

**Verificación**: `uv run pytest tests/modules/agents_hub/unit/test_deterministic_detector.py` verde.

---

### Prompt 9Q.4 (RED/GREEN) — Detector semántico site-scoped: clustering pgvector + juez LLM + `audit_semantic_scope`

**Modelo sugerido**: **Opus** — decisiones de diseño embebidas: estrategia de clustering por similitud, umbral, control de coste, la lógica de cobertura `ingested`/`full` (qué páginas tienen embedding y cuáles se embeben on-demand), diseño del prompt del juez LLM y discriminación duplicado-vs-contradicción con confianza calibrada.

**Objetivo**: segunda pasada, **selectiva y con LLM, a nivel sitio**, que detecta duplicados y contradicciones semánticas entre páginas. Respeta `HubWebSite.audit_semantic_scope`: `ingested` (solo páginas ya ingeridas en algún chatbot, que ya tienen embeddings) o `full` (embebe todas las páginas rastreadas).

**Contexto**: la similitud pgvector y los embeddings de chunks viven en `ingestion/retriever.py` / `HubDocumentChunk`. Una página ingerida tiene embeddings vía su `HubDocument`→chunks (`crawled_page_id`). Una página no ingerida no los tiene. El juez LLM se inyecta como `LLMService` (Protocol, igual que 9R.6.3); el `EmbeddingService` también se inyecta. La anonimización pre-LLM reutiliza los hooks de Fase 13.

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.4 (RED/GREEN) — Detector semántico con juez LLM (site-scoped)

Deploy: edge.

## Migración — embedding de página para modo full
Añade a HubCrawledPage: page_embedding Vector(D)|None (pgvector, None = sin embedding), donde D
es la MISMA dimensión que usa HubDocumentChunk.embedding (BGE-M3 = 1024); si no coinciden, la
similitud coseno no cruza. Aplica con `uv run alembic upgrade <rev>`.

## Servicio — ingestion/quality/semantic_detector.py
class SemanticContradictionDetector(session, llm: LLMService, embedding_service, *,
        similarity_threshold=0.92, max_pairs_per_run=200, anonymizer=None):
  async def analyze(site_id) -> list[ContentFinding]:
    0. COBERTURA según HubWebSite.audit_semantic_scope:
       - "ingested": conjunto = páginas del sitio con al menos un HubDocument ingerido. Reusa el
         embedding del chunk representativo (mayor token_count). Si la página está ingerida en
         varios chatbots (varios HubDocument), el contenido es idéntico → toma cualquiera (p.ej. el
         primer document_id) sin recomputar.
       - "full": conjunto = todas las páginas activas. Para las que no tengan page_embedding,
         embeber HubCrawledPage.markdown_content vía embedding_service y persistir page_embedding
         (idempotente: no re-embeber si content_hash no cambió).
    1. CLUSTERING (sin LLM): por cada página del conjunto, vecinos por coseno >= similarity_threshold.
       Forma pares candidatos (page_a, page_b) DISTINTO id dentro del MISMO sitio.
    2. CONTROL DE COSTE: descarta pares de la MISMA canonical (eso es 9Q.3 superseded).
       Limita a max_pairs_per_run, priorizando mayor similitud. 0 pares → return [] sin LLM.
    3. ANONIMIZACIÓN: si anonymizer no es None, anonimiza ambos textos antes del LLM.
    4. JUEZ LLM: por par, JSON estricto
       {"relation":"duplicate"|"contradiction"|"unrelated","confidence":0..1,"explanation":"..."}.
       - duplicate → finding duplicate (warning); contradiction → critical; unrelated → nada.
       confidence del finding = confidence del juez. signal = {similarity, explanation, textos truncados}.
    El prompt del juez es robusto a fences markdown (reutiliza _extract_json de 9R.4.1).

## Reglas
- NUNCA llamar al LLM por cada par del producto cartesiano: solo pares filtrados por umbral y dedup.
- En modo "ingested" jamás se embebe de más (coste 0 de embedding).
- LLM y embedding_service inyectados; tests con fakes deterministas (no red).

## Tests (mínimo 11) — test_semantic_detector.py
- Cobertura "ingested": solo páginas con documento; las no ingeridas se ignoran (0 embeds).
- Cobertura "full": páginas sin embedding se embeben y persisten; segundo run no re-embebe.
- Clustering: solo pares >= umbral; por debajo no.
- Control de coste: 0 pares → 0 llamadas al LLM (spy).
- Pares de la misma canonical se descartan.
- Juez contradiction → critical con confidence propagada; duplicate → warning; unrelated → nada.
- max_pairs_per_run respetado; anonimizador invocado cuando se inyecta; JSON con fences.
```

**Verificación**: `uv run pytest tests/modules/agents_hub/unit/test_semantic_detector.py` verde; cero llamadas al LLM cuando no hay clusters; cero embeddings en modo `ingested`; migración aplicada.

---

### Prompt 9Q.5 (RED/GREEN) — Job asíncrono por sitio + scheduler + consolidación + auto-ingesta de candidatas

**Modelo sugerido**: **Sonnet** — orquestación con patrón de scheduler conocido; alcance cerrado (crawl + detectores + consolidación + auto-ingest ya están especificados por 9Q.2–9Q.4 y la selección de 9Q.7).

**Objetivo**: orquestar **por sitio** el crawl (9Q.2) + ambas pasadas de detección (9Q.3/9Q.4) en un job asíncrono que **nunca bloquea**, consolidar los `superseded` en `HubCrawledPage` y propagarlos a los `HubDocument` ingeridos, **auto-ingerir las páginas nuevas** que casen con una `HubCorpusSelection(auto_ingest_new=True)`, y programar la cadencia con un scheduler propio.

**Contexto**: reutiliza el patrón APScheduler del difunto `source_scheduler.py` (eliminado en 9Q.0; entre 9Q.0 y este prompt no hay scheduler de crawl). Los detectores son 9Q.3/9Q.4; el crawler 9Q.2; la ingesta de una página la realiza `IngestionWatcher`; las selecciones las resuelve `CorpusSelectionRepo` (9Q.0/9Q.7).

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.5 (RED/GREEN) — SiteQualityJob + scheduler

Deploy: edge.

## Servicio — ingestion/quality/quality_job.py
class SiteQualityAnalysisJob(session_factory, site_crawler, detectors, watcher, selection_repo,
        *, run_semantic=True):
  async def run_for_site(site_id) -> SiteQualitySummary:
    1. CRAWL: site_crawler.crawl_site(site_id) → diff (nuevas/cambiadas/desaparecidas).
    2. DETECCIÓN: DeterministicQualityDetector.analyze(site_id) SIEMPRE;
       SemanticContradictionDetector.analyze(site_id) si run_semantic y hay LLM.
       Cada detector en try/except aislado: si uno falla, el otro y el crawl siguen (summary.errors).
    3. CONSOLIDACIÓN: por cada finding superseded en new|confirmed, fija
       HubCrawledPage.superseded=True + superseded_by_page_id. PROPAGACIÓN: los HubDocument con
       crawled_page_id de esa página NO se borran; el flag de página basta (el retriever de 9Q.6
       filtra por la página). quality_score por página = heurística documentada
       (1.0 menos penalizaciones por findings críticos/warning sobre esa página).
    4. AUTO-INGESTA: por cada página NUEVA del diff, para cada HubCorpusSelection del sitio con
       auto_ingest_new=True cuya regla case (selection_repo.matches), encola IngestionWatcher
       para crear el HubDocument(crawled_page_id=page.id) en ese chatbot. Páginas CAMBIADAS ya
       ingeridas → re-ingesta (re-embed). Páginas GONE → marca sus documentos para retirada
       (finding orphan_page; la retirada efectiva la decide el equipo vía 9Q.7).
    El job NUNCA propaga excepción que tumbe el scheduler.
  SiteQualitySummary: diff counts, counts por finding_type, páginas marcadas superseded,
    documentos auto-ingeridos, errores.

## Scheduler — ingestion/quality/quality_scheduler.py (patrón APScheduler)
  create_quality_scheduler(session_factory) -> AsyncIOScheduler
    - Job maestro check_all_sites cada N horas (default 24, UTC) que selecciona los HubWebSite
      activos cuyo crawl_interval_hours haya vencido y lanza run_for_site.
  Arranque en main.py / lifespan (sustituye al arranque del antiguo source_scheduler).

## Settings (core/config.py)
  CONTENT_QUALITY_ENABLED: bool = True
  CONTENT_QUALITY_INTERVAL_HOURS: int = 24
  CONTENT_QUALITY_SEMANTIC_ENABLED: bool = True   # apaga el juez LLM si se quiere coste 0

## Tests (mínimo 10) — test_quality_job.py
- run_for_site encadena crawl + ambos detectores y agrega summary.
- Fallo del detector semántico NO impide consolidación determinista (summary.errors).
- Consolidación fija superseded=True + superseded_by_page_id en la página antigua.
- Auto-ingesta: página nueva que casa una selección auto → watcher invocado con crawled_page_id.
- Página nueva sin selección que case → NO se ingiere (queda candidata para 9Q.7).
- quality_score baja con findings críticos; run_semantic=False salta el LLM.
- Scheduler filtra sitios por crawl_interval_hours vencido (mock de tiempo).
- Idempotencia: segunda ejecución no duplica findings ni re-ingiere sin cambios.
```

**Verificación**: `uv run pytest tests/modules/agents_hub/` verde; un fallo simulado del detector semántico deja la suite verde y la consolidación + auto-ingesta intactas.

---

### Prompt 9Q.6 (RED/GREEN) — RAG consciente de calidad: el retriever excluye páginas `superseded`

**Modelo sugerido**: **Sonnet** — modificación acotada del retriever con filtro por flag de página; tests de regresión claros.

**Objetivo**: cerrar el primer canal de salida (higiene RAG): el retriever deja de servir chunks cuyos documentos provengan de una **página** marcada `superseded`, con opción explícita de incluirlos para auditoría. Como el flag vive en la página, el filtrado afecta a **todos** los chatbots que ingirieron esa página.

**Contexto**: `ingestion/retriever.py` (`HybridRetriever.vector_search`/`keyword_search`/`hybrid_search`) y `retrieval/vector_strategy.py`. El flag de supersesión está en `HubCrawledPage` (9Q.0); `HubDocument.crawled_page_id` enlaza chunk→documento→página. El filtro se aplica por defecto sin romper los contratos existentes.

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.6 (RED/GREEN) — Retrieval que excluye páginas superseded

Deploy: edge.

## Cambios en HybridRetriever (retriever.py)
- vector_search / keyword_search / hybrid_search aceptan include_superseded: bool = False.
- Por defecto (False), las queries excluyen chunks cuyo document_id apunte a un HubDocument
  cuyo crawled_page_id apunte a una HubCrawledPage con superseded=True.
  Implementar con JOIN/subquery hub_document_chunks → hub_documents → hub_crawled_pages.
- include_superseded=True restaura el comportamiento anterior (para el visor de auditoría).
- Chunks cuyo HubDocument tenga crawled_page_id=None (PDFs subidos, legacy) NO se excluyen
  (no hay página de origen, no hay info de supersesión).

## VectorRetrievalStrategy
- Propaga el filtro por defecto (las respuestas del chatbot nunca usan páginas superseded).

## Tests (mínimo 8) — test_retrieval_quality_filter.py
- Página superseded → los chunks de sus documentos NO aparecen en vector/keyword/hybrid_search.
- include_superseded=True → reaparecen.
- Página no superseded → sin cambios (regresión de los tests de retriever existentes).
- HubDocument con crawled_page_id None (PDF subido) → nunca filtrado.
- Misma página ingerida por 2 chatbots → ambos la excluyen al marcarse superseded.
- hybrid_search mantiene el orden RRF tras excluir superseded.
```

**Verificación**: `uv run pytest tests/modules/agents_hub/` verde, incluidos los tests de retriever previos sin regresión.

---

### Prompt 9Q.7 (RED/GREEN) — Capa de selección: gestión de sitios + mapeo sitio→chatbots + candidatas

**Modelo sugerido**: **Sonnet** — servicio de selección + endpoints con alcance cerrado (las entidades y reglas ya las fijó 9Q.0). Sustituye la superficie de "fuentes" que retiró 9Q.0.

**Objetivo**: dar la superficie HTTP que materializa el split: gestionar **sitios** (CRUD + disparo de crawl), definir **selecciones** que mapean secciones del sitio a chatbots (N:M), y revisar/ejecutar la **ingesta de páginas candidatas** (nuevas o seleccionadas aún no ingeridas).

**Contexto**: repos de 9Q.0 (`WebSiteRepo`, `CrawledPageRepo`, `CorpusSelectionRepo`). La ingesta de una página la realiza `IngestionWatcher` creando `HubDocument(crawled_page_id=...)`. El job de calidad es 9Q.5. Router nuevo `Deploy: edge`, en `_register_edge`.

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.7 (RED/GREEN) — Selección y gestión de sitios

Deploy: edge.

## Servicio — ingestion/quality/selection_service.py
class CorpusSelectionService(session, page_repo, selection_repo, watcher):
  async def candidates(site_id, chatbot_id) -> list[CandidatePageView]:
    # páginas activas del sitio que (casan alguna selección del chatbot O son nuevas) y
    # NO tienen aún HubDocument(crawled_page_id) para ese chatbot.
  async def ingest_page(chatbot_id, page_id) -> HubDocument
    # ingesta manual de una página concreta en un chatbot (idempotente: no duplica).
  async def retire_page(chatbot_id, page_id) -> int
    # retira los HubDocument(crawled_page_id) de esa página para ese chatbot (borra chunks).

## Contratos — ingestion/quality/selection_contracts.py
SiteView, SiteCreate (name, root_url, sitemap_url?, audit_semantic_scope?, crawl_interval_hours?),
  # SiteCreate NO incluye client_id: el servidor lo deriva del usuario autenticado (current_user)
  # al crear el HubWebSite. El cliente nunca lo envía.
SelectionView, SelectionCreate (site_id, rule_type, rule_value?, auto_ingest_new?),
CandidatePageView (page_id, url, title, matched_rule?, is_new: bool).

## Router — routers/hub_sites_router.py (Deploy: edge)
- POST/GET/PATCH/DELETE /api/v1/hub/sites                         → CRUD de HubWebSite (por client)
- POST /api/v1/hub/sites/{site_id}/crawl                          → 202, dispara SiteQualityAnalysisJob.run_for_site
- GET  /api/v1/hub/sites/{site_id}/pages?status=                  → páginas rastreadas
- POST/GET/DELETE /api/v1/hub/chatbots/{chatbot_id}/selections    → CRUD de HubCorpusSelection
- GET  /api/v1/hub/sites/{site_id}/candidates?chatbot_id=         → CorpusSelectionService.candidates
- POST /api/v1/hub/chatbots/{chatbot_id}/pages/{page_id}/ingest   → 202, ingest_page (manual)
- DELETE /api/v1/hub/chatbots/{chatbot_id}/pages/{page_id}        → retire_page
Permisos: 403 si el usuario no es owner del chatbot/admin del client. operation_id explícito (Orval).
Registrar en _register_edge (main.py) con docstring `Deploy: edge`.

## Tests (mínimo 10) — test_selection_service.py + test_hub_sites_router.py
- candidates devuelve páginas que casan una selección path_prefix y no están ingeridas; excluye ya ingeridas.
- ingest_page crea HubDocument(crawled_page_id) y es idempotente (2ª llamada no duplica).
- retire_page borra documentos+chunks de esa página para el chatbot y devuelve el count.
- CRUD de sitio y de selección; POST crawl responde 202 y encola run_for_site (spy).
- 403 para usuario no autorizado; edge boundary (router no importa módulos cloud).
```

**Verificación**: `uv run pytest tests/modules/agents_hub/` verde; OpenAPI regenerado; `_register_edge` incluye el router.

---

### Prompt 9Q.8 (RED/GREEN) — Informe de auditoría web por sitio: builder + export DOCX/PDF + endpoints

**Modelo sugerido**: **Sonnet** — agregación de datos + reutilización de `ExportService`; endpoints con alcance cerrado.

**Objetivo**: cerrar el segundo canal de salida (informe humano): un builder que agrega los hallazgos de un **sitio** en un informe estructurado por tipo con recomendaciones, su exportación a DOCX/PDF descargable, y los endpoints HTTP (cola de revisión, informe, disparo de análisis) **keyed por sitio**.

**Contexto**: el patrón de export DOCX existe en `modules/agents_hub/services/export_service.py` (python-docx). Para PDF, reutilizar el mismo patrón o conversión documentada (sin añadir dependencias pesadas nuevas sin justificar). Router nuevo `Deploy: edge`, en `_register_edge`. Los hallazgos los provee `ContentFindingRepo.list_by_site` (9Q.1).

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.8 (RED/GREEN) — WebQualityReport builder + export + endpoints

Deploy: edge.

## Contrato del informe — ingestion/quality/report_contracts.py
WebQualityReport (Pydantic): site_id, site_name, generated_at, totals_by_type: dict[FindingType,int],
  totals_by_severity, sections: list[FindingTypeSection].
FindingTypeSection: finding_type, findings: list[ContentFindingView],
  recommendation: str  # texto accionable para el equipo web (p.ej. "3 páginas obsoletas:
  considere despublicar /proc/2022/x sustituida por /proc/2024/x").
ContentFindingView: tipo, severidad, urls implicadas (page/related), fechas, explicación.

## Builder — ingestion/quality/report_builder.py
class WebQualityReportBuilder(findings_repo, site_repo):
  async def build(site_id, *, status_filter=("new","confirmed")) -> WebQualityReport
    - list_by_site → agrupa por finding_type, genera recommendation por sección
      (plantillas i18n-izables; texto base en español, claves para traducir en UI).
    - Caso vacío: informe con totals a 0 y sections=[].

## Export — ingestion/quality/report_exporter.py
class WebQualityReportExporter(storage):
  async def to_docx(report) -> bytes      # reutiliza patrón de ExportService (python-docx)
  async def to_pdf(report) -> bytes       # conversión ya disponible; si requiere LibreOffice/headless,
                                          # degradar con skip condicional como en 9R.9.2.

## Router — routers/hub_content_quality_router.py (Deploy: edge)
- GET   /api/v1/hub/sites/{site_id}/findings?status=&type=        → lista (cola de revisión)
- PATCH /api/v1/hub/sites/{site_id}/findings/{finding_id}         → transición de estado
         (confirm/dismiss/resolve; 422 transición inválida; 403 si no autorizado)
- GET   /api/v1/hub/sites/{site_id}/report                        → WebQualityReport JSON
- GET   /api/v1/hub/sites/{site_id}/report/export?format=docx|pdf → descarga binaria
- POST  /api/v1/hub/sites/{site_id}/analyze                       → 202, dispara
          SiteQualityAnalysisJob.run_for_site en background.
Registrar en _register_edge (main.py) con docstring `Deploy: edge`. operation_id explícito (Orval).

## Tests (mínimo 10) — test_content_quality_report.py + test_content_quality_router.py
- build agrupa por finding_type y genera recommendation; caso vacío → totals 0.
- Exporter DOCX produce bytes no vacíos con secciones; PDF con skip condicional documentado.
- GET findings filtra por status/type; PATCH aplica transición y 422 en inválida; 403 no-autorizado.
- GET report devuelve el contrato; export?format=docx devuelve content-type correcto.
- POST analyze responde 202 y encola el job (spy).
- Edge boundary: el router no importa módulos cloud (test_edge_boundary actualizado).
```

**Verificación**: `uv run pytest tests/modules/agents_hub/` verde; OpenAPI regenerado; `_register_edge` incluye el router.

---

### Prompt 9Q.9 (RED/GREEN) — Frontend: sitios + mapeo de selección + candidatas + auditoría + pruebas manuales

**Modelo sugerido**: **Sonnet** — UI React con hooks Orval generados, i18n, patrones ya establecidos en el admin hub.

**Objetivo**: cerrar el bloque con la interfaz admin organizada **en torno al sitio**: gestión de sitios y disparo de crawl, mapeo de secciones del sitio a chatbots (selecciones), revisión de páginas candidatas a ingesta, cola de hallazgos del sitio, visor del informe de auditoría y descarga DOCX/PDF. Todo i18n y derivado del contrato OpenAPI.

**Contexto**: frontend admin en `frontend/src/admin/`; hooks generados por Orval desde `openapi.json` (endpoints de 9Q.7 sitios/selecciones/candidatas y de 9Q.8 hallazgos/informe). i18n con i18next (es/ca/en). Este prompt **sí requiere pruebas manuales** (navegador) según CLAUDE.md → genera el `.bat`.

**Instrucciones al agente**:
```markdown
# PROMPT 9Q.9 (RED/GREEN) — UI de calidad de contenido web (centrada en sitio)

## Regenerar Orval
Tras 9Q.7/9Q.8, regenerar hooks (useListSites / useCreateSite / useCrawlSite /
useListSelections / useCreateSelection / useListCandidates / useIngestPage /
useListSiteFindings / usePatchFinding / useGetWebQualityReport / useAnalyzeSite).
Verificar tsc --noEmit limpio.

## Páginas (frontend/src/admin/pages/)
- SitesPage.tsx: lista de sitios (alta con root_url/sitemap/audit_semantic_scope),
  botón "Rastrear ahora" → useCrawlSite (toast de encolado), estado last_crawled_at.
- SiteMappingPanel.tsx: dado un sitio, gestiona selecciones (regla path_prefix/section/manual,
  toggle auto_ingest_new) y muestra páginas candidatas (useListCandidates) con acción
  "Ingerir en chatbot X" (useIngestPage). Selector de chatbot destino.
- ContentQualityPage.tsx: selector de sitio; "Analizar ahora" → useAnalyzeSite; tabla de
  hallazgos (badge por severidad, URLs, fecha, explicación, Confirmar/Descartar/Resolver via
  usePatchFinding); filtros por status y finding_type.
- WebQualityReportViewer.tsx: useGetWebQualityReport → totales por tipo/severidad + secciones
  por finding_type con recomendación; "Descargar DOCX"/"Descargar PDF" → GET export?format=.
- Rutas /hub/sites y /hub/content-quality en App.tsx + entradas en la navegación de HubLayout.

## i18n (namespace nuevo `contentQuality`, es/en/ca)
  Etiquetas de finding_type, severidad, estados, acciones, reglas de selección, recomendaciones,
  títulos de tabla, botones. NINGÚN string hardcodeado.

## Tests Vitest (mínimo 7) — SitesPage / SiteMappingPanel / ContentQualityPage / WebQualityReportViewer
- SitesPage: alta de sitio invoca useCreateSite; "Rastrear ahora" invoca useCrawlSite.
- SiteMappingPanel: crear selección invoca useCreateSelection; candidatas se listan; "Ingerir" invoca useIngestPage.
- Tabla de hallazgos renderiza con badge de severidad correcto; Confirmar invoca usePatchFinding.
- Filtro por finding_type re-consulta con el parámetro; "Analizar ahora" invoca useAnalyzeSite.
- Visor muestra totales y secciones; caso vacío → mensaje "sin hallazgos".
- Accesibilidad: expectNoA11yViolations sobre las páginas nuevas (helper de 20.1).

## Pruebas manuales (CLAUDE.md — requiere navegador)
Genera `pruebas_manuales_prompt9Q_9.bat` (encoding ANSI 1252, sin BOM, vía PowerShell
[System.IO.File]::WriteAllText con Encoding 1252; primeros bytes @ech) con: arranque Docker,
migración si aplica, smoke `curl` a /hub/sites/{id}/analyze, y pasos en la UI: dar de alta un
sitio, rastrearlo, crear una selección por prefijo, ingerir una candidata en un chatbot,
analizar el sitio, ver hallazgos (duplicados/obsoletas), confirmar uno, abrir el informe,
descargar el DOCX. Casos límite: sitio sin hallazgos; página candidata sin selección que case.
Acompaña la respuesta con el bloque de instrucciones para el usuario (formato CLAUDE.md).
```

**Verificación**: `npm test` (Vitest) verde; `tsc --noEmit` limpio; `.bat` con bytes correctos; bloque de instrucciones manuales en la respuesta. **Cierra el bloque 9Q.**

---

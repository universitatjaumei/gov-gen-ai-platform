## BLOQUE 9A — Admin Hub

*Objetivo: panel de administración unificado operativo con CRUD de chatbots, clientes y documentos.*

---

### Prompt 9.1 - Scaffolding: Vite + shadcn/ui + i18n ✅ COMPLETADO

### Prompt 9.2 - i18n: locales es / ca / en ✅ COMPLETADO

### Prompt 9.3 - Auth: contexto JWT y rutas protegidas ✅ COMPLETADO

### Prompt 9.4 - Layout: sidebar seccional y header ✅ COMPLETADO

### Prompt 9.5 - Hub > Pantalla de Chatbots ✅ COMPLETADO

### Prompt 9.6 - Hub > Pantalla de Clientes ✅ COMPLETADO

### Prompt 9.6.5 - Frontera Edge-Cloud (preparación del despliegue híbrido) ✅ COMPLETADO

### Prompt 9.6.6 - Frontera Edge-Cloud en la capa de aplicación (routers y módulos) ✅ COMPLETADO

### Prompt 9.7 - Hub > Pantalla de Documentos ✅ COMPLETADO

### Prompt 9.7.1 - Hub > Fuentes web monitorizadas (crawler de ingestión) ✅ COMPLETADO (2026-04-25)

### Prompt 9.8 - Hub > Pantalla de Informes ✅ COMPLETADO (2026-04-26)

### Prompt 9.8.1 - Etiquetado de idioma en la ingestión ✅ COMPLETADO (2026-04-26)

### Prompt 9.8.2 - SSE streaming en el endpoint de chat (backend) ✅ COMPLETADO (2026-04-26)

### Prompt 9.9 - Widget: bundle embebible ✅ COMPLETADO (2026-04-26)

### Prompt 9.10 - Widget: chat SSE y feedback ✅ COMPLETADO (2026-04-26)

---


## ~~Subfase 1.A — Spider Skills y Asistente HITL de Ingestión~~ — COMPLETADA ✅

**Objetivo**: Implementar las capacidades de indexación web necesarias para que el chatbot informativo sirva respuestas con datos reales de webs institucionales. Esta subfase es **prerrequisito para la puesta en marcha del chatbot UJI** con datos actualizados.

**Dependencias**: Prompt 9.7.1 (crawler base ✅ completado).

**Entregable**: Sistema capaz de indexar cualquier web institucional con control de profundidad, filtros y selectores CSS, apoyado por un asistente que propone selectores automáticamente al Admin.

---

### Prompt 1A.1 — Spider Genérico: crawl_depth, filtros regex y límite de páginas (TDD RED/GREEN)

**Objetivo**: Extender el crawler base (Prompt 9.7.1) con control de profundidad BFS, filtros regex de URL y límite de páginas, para indexar jerarquías web institucionales de forma controlada y predecible.

**Contexto**: El spider base existe en `server/app/modules/agents_hub/ingestion/spider.py`. Sin `crawl_depth` ni `max_pages` el spider puede indexar sitios enteros. Estos parámetros se leen de `HubWebSource.config_json` y extienden el comportamiento existente sin romperlo.

**Instrucciones al agente**:
```text
Actúa como experto en Python y scraping web. Extiende el spider existente en
server/app/modules/agents_hub/ingestion/spider.py.

NUEVOS PARÁMETROS leídos de HubWebSource.config_json:
  crawl_depth (int, default 1): niveles de links internos a seguir desde la URL raíz.
  url_regex_filter (str, nullable): si se proporciona, solo se indexan URLs que machan la regex.
  max_pages (int, default 50): límite absoluto de páginas procesadas por ejecución.

LÓGICA BFS:
1. Cola de pares (url, depth). Raíz comienza con depth=0.
2. Solo se encolan links del mismo dominio base (sin subdominios externos).
3. Si depth >= crawl_depth: procesar el nodo pero NO encolar sus hijos.
4. Si url_regex_filter existe: descartar la URL si no macha.
5. Al alcanzar max_pages: detener el BFS, marcar CrawlResult.status = COMPLETED_PARTIAL,
   incrementar pages_skipped con los que quedaban en cola.

TIPOS NUEVOS (añadir al módulo):
  class CrawlStatus(Enum): COMPLETED = "completed"; COMPLETED_PARTIAL = "completed_partial"
  @dataclass class CrawlResult:
      crawled_urls: list[str]
      pages_crawled: int
      pages_skipped: int
      status: CrawlStatus

INTERFAZ GenericSpider:
  Constructor acepta fetch_fn: Callable[[str], Awaitable[str]] para testing sin red.
  Método: async def crawl(source: HubWebSource) -> CrawlResult

TESTS REQUERIDOS:
- test_spider_respects_crawl_depth_zero
- test_spider_respects_crawl_depth_one
- test_spider_url_regex_filter_excludes_non_matching_urls
- test_spider_stops_at_max_pages_and_marks_partial
- test_spider_does_not_revisit_urls
```

**Tests RED — tests/modules/agents_hub/unit/test_spider_generic.py**:
```python
"""Tests para el spider genérico con crawl_depth, regex y max_pages — TDD RED."""
import pytest
from dataclasses import dataclass, field


@dataclass
class FakeWebSource:
    url: str
    config_json: dict = field(default_factory=dict)


class TestGenericSpider:

    @pytest.mark.asyncio
    async def test_spider_respects_crawl_depth_zero(self) -> None:
        """Con crawl_depth=0 solo procesa la URL raíz, sin seguir ningún link."""
        from server.app.modules.agents_hub.ingestion.spider import GenericSpider

        fetched_urls: list[str] = []

        async def fake_fetch(url: str) -> str:
            fetched_urls.append(url)
            return '<html><body><a href="/pagina2">enlace</a></body></html>'

        spider = GenericSpider(fetch_fn=fake_fetch)
        source = FakeWebSource(
            url="https://ejemplo.uji.es",
            config_json={"crawl_depth": 0, "max_pages": 10},
        )
        result = await spider.crawl(source)

        assert fetched_urls == ["https://ejemplo.uji.es"]
        assert result.pages_crawled == 1

    @pytest.mark.asyncio
    async def test_spider_respects_crawl_depth_one(self) -> None:
        """Con crawl_depth=1 procesa raíz + links de primer nivel, sin bajar más."""
        from server.app.modules.agents_hub.ingestion.spider import GenericSpider

        pages = {
            "https://ejemplo.uji.es": '<html><a href="/a">A</a><a href="/b">B</a></html>',
            "https://ejemplo.uji.es/a": '<html><a href="/c">C</a></html>',
            "https://ejemplo.uji.es/b": "<html>contenido b</html>",
        }

        async def fake_fetch(url: str) -> str:
            return pages.get(url, "<html></html>")

        spider = GenericSpider(fetch_fn=fake_fetch)
        source = FakeWebSource(
            url="https://ejemplo.uji.es",
            config_json={"crawl_depth": 1, "max_pages": 50},
        )
        result = await spider.crawl(source)

        crawled = set(result.crawled_urls)
        assert "https://ejemplo.uji.es" in crawled
        assert "https://ejemplo.uji.es/a" in crawled
        assert "https://ejemplo.uji.es/b" in crawled
        assert "https://ejemplo.uji.es/c" not in crawled  # nivel 2, no debe llegar

    @pytest.mark.asyncio
    async def test_spider_url_regex_filter_excludes_non_matching_urls(self) -> None:
        """Con url_regex_filter, solo se indexan las URLs que machan la expresión."""
        from server.app.modules.agents_hub.ingestion.spider import GenericSpider

        pages = {
            "https://ejemplo.uji.es": (
                '<html><a href="/normativa/ley1">Ley</a>'
                '<a href="/noticias/nota">Noticia</a></html>'
            ),
            "https://ejemplo.uji.es/normativa/ley1": "<html>normativa</html>",
            "https://ejemplo.uji.es/noticias/nota": "<html>noticia</html>",
        }

        async def fake_fetch(url: str) -> str:
            return pages.get(url, "<html></html>")

        spider = GenericSpider(fetch_fn=fake_fetch)
        source = FakeWebSource(
            url="https://ejemplo.uji.es",
            config_json={"crawl_depth": 1, "url_regex_filter": r"/normativa/", "max_pages": 50},
        )
        result = await spider.crawl(source)

        assert "https://ejemplo.uji.es/normativa/ley1" in result.crawled_urls
        assert "https://ejemplo.uji.es/noticias/nota" not in result.crawled_urls

    @pytest.mark.asyncio
    async def test_spider_stops_at_max_pages_and_marks_partial(self) -> None:
        """Al alcanzar max_pages, el resultado se marca COMPLETED_PARTIAL."""
        from server.app.modules.agents_hub.ingestion.spider import GenericSpider, CrawlStatus

        async def fake_fetch(url: str) -> str:
            links = "".join(f'<a href="/p{i}">p{i}</a>' for i in range(20))
            return f"<html>{links}</html>"

        spider = GenericSpider(fetch_fn=fake_fetch)
        source = FakeWebSource(
            url="https://ejemplo.uji.es",
            config_json={"crawl_depth": 2, "max_pages": 3},
        )
        result = await spider.crawl(source)

        assert result.pages_crawled <= 3
        assert result.status == CrawlStatus.COMPLETED_PARTIAL
        assert result.pages_skipped > 0

    @pytest.mark.asyncio
    async def test_spider_does_not_revisit_urls(self) -> None:
        """Una URL no se procesa dos veces aunque aparezca en múltiples páginas."""
        from server.app.modules.agents_hub.ingestion.spider import GenericSpider

        call_counts: dict[str, int] = {}

        async def fake_fetch(url: str) -> str:
            call_counts[url] = call_counts.get(url, 0) + 1
            return '<html><a href="https://ejemplo.uji.es">inicio</a></html>'

        spider = GenericSpider(fetch_fn=fake_fetch)
        source = FakeWebSource(
            url="https://ejemplo.uji.es",
            config_json={"crawl_depth": 1, "max_pages": 10},
        )
        await spider.crawl(source)

        assert call_counts.get("https://ejemplo.uji.es", 0) == 1
```

**Criterios de aceptación**:
- `GenericSpider` acepta `crawl_depth`, `url_regex_filter` y `max_pages` desde `config_json`.
- `CrawlResult` expone `crawled_urls`, `pages_crawled`, `pages_skipped`, `status`.
- Los 5 tests pasan en verde sin regresión en los tests del spider existente.

---

### Prompt 1A.2 — Spiders Especializados UJI: Normativa y Procedimientos (TDD RED/GREEN)

**Objetivo**: Implementar dos extractores especializados para las fuentes institucionales de la UJI: normativa académica (BOE/DOGV/normativa.uji.es) y catálogo de procedimientos administrativos. Producen `HubDocument` con metadatos estructurados que enriquecen las respuestas del chatbot.

**Contexto**: El spider genérico (1A.1) proporciona la infraestructura BFS. Los especializados la extienden con lógica de extracción de contenido estructurado por fuente. Implementan `SpiderProtocol` para poder ser seleccionados por `SpiderFactory` según el campo `spider_type` de `HubWebSource`.

**Instrucciones al agente**:
```text
Actúa como experto en Python y extracción de datos de webs institucionales. Implementa los
spiders especializados en server/app/modules/agents_hub/ingestion/spiders/.

SPIDER 1 — NormativaSpider (fuentes: boe | dogv | uji):
  Parámetros constructor: source_type (str), date_from (date | None).
  Método: extract_document(url: str, html: str) -> NormativaDoc | None
  Extrae: titulo, fecha_publicacion (date), numero_norma (str), texto (str).
  Filtra: si date_from y fecha_publicacion < date_from -> devuelve None.
  Genera HubDocument con metadata_json = {source_type, fecha_publicacion ISO, numero_norma}.
  Los selectores CSS por fuente se configuran en un dict SELECTORS[source_type].

SPIDER 2 — ProcedimientosSpider (fuente: procedimientos.uji.es):
  Método: extract_document(url: str, html: str) -> ProcedimientoDoc | None
  Extrae: nombre, codigo, unidad_responsable, plazo, documentacion_requerida, normativa_aplicable.
  Genera HubDocument con metadata_json = {doc_type: "procedimiento", codigo}.

FACTORY — SpiderFactory en server/app/modules/agents_hub/ingestion/spider_factory.py:
  Método: get_spider(source_type: str) -> SpiderProtocol
  Mapeo: "boe" | "dogv" | "uji" -> NormativaSpider; "procedimientos" -> ProcedimientosSpider;
         "generic" -> GenericSpider.
  Lanza ValueError("Unknown spider type: {source_type}") para tipos desconocidos.

MIGRACIÓN Alembic: añadir columna spider_type (VARCHAR, nullable) a hub_web_sources.
  Default: "generic". El IngestionWatcher usa SpiderFactory para seleccionar el spider.

TESTS REQUERIDOS:
- test_normativa_spider_extracts_titulo_and_fecha_from_boe_html
- test_normativa_spider_skips_documents_before_date_from
- test_normativa_spider_builds_hub_document_with_metadata
- test_procedimientos_spider_extracts_ficha_completa
- test_procedimientos_spider_builds_hub_document_with_type
- test_spider_factory_returns_correct_spider_by_source_type
- test_spider_factory_raises_for_unknown_type
```

**Tests RED — tests/modules/agents_hub/unit/test_spiders_especializados.py**:
```python
"""Tests para spiders especializados UJI (normativa + procedimientos) — TDD RED."""
import pytest
from datetime import date


SAMPLE_BOE_HTML = """
<html><head><title>BOE núm. 123</title></head>
<body>
  <h1 class="documento-tit">Real Decreto 456/2025, de 15 de marzo, sobre universidades</h1>
  <span class="publicado">15/03/2025</span>
  <div class="texto-articulado">
    <p>Artículo 1. Los organismos universitarios deberán adaptar sus procedimientos.</p>
    <p>Artículo 2. El plazo de adaptación será de seis meses desde la publicación.</p>
  </div>
</body></html>
"""

SAMPLE_PROCEDIMIENTO_HTML = """
<html><body>
  <h1 class="proc-titulo">Solicitud de título universitario oficial</h1>
  <span class="proc-codigo">PROC-042</span>
  <span class="proc-unidad">Secretaría General</span>
  <span class="proc-plazo">3 meses desde la finalización de estudios</span>
  <div class="proc-documentacion">Expediente académico, DNI, justificante de pago de tasas</div>
  <div class="proc-normativa">RD 1027/2011, Estatuts UJI art. 56</div>
</body></html>
"""


class TestNormativaSpider:

    def test_normativa_spider_extracts_titulo_and_fecha_from_boe_html(self) -> None:
        from server.app.modules.agents_hub.ingestion.spiders.normativa_spider import NormativaSpider

        spider = NormativaSpider(source_type="boe")
        doc = spider.extract_document(url="https://boe.es/doc", html=SAMPLE_BOE_HTML)

        assert doc is not None
        assert "Real Decreto 456/2025" in doc.titulo
        assert doc.fecha_publicacion == date(2025, 3, 15)
        assert "Artículo 1" in doc.texto

    def test_normativa_spider_skips_documents_before_date_from(self) -> None:
        from server.app.modules.agents_hub.ingestion.spiders.normativa_spider import NormativaSpider

        spider = NormativaSpider(source_type="boe", date_from=date(2026, 1, 1))
        doc = spider.extract_document(url="https://boe.es/doc", html=SAMPLE_BOE_HTML)

        assert doc is None

    def test_normativa_spider_builds_hub_document_with_metadata(self) -> None:
        from server.app.modules.agents_hub.ingestion.spiders.normativa_spider import NormativaSpider

        spider = NormativaSpider(source_type="boe")
        doc = spider.extract_document(url="https://boe.es/doc", html=SAMPLE_BOE_HTML)

        assert doc is not None
        assert doc.metadata_json["source_type"] == "boe"
        assert doc.metadata_json["fecha_publicacion"] == "2025-03-15"


class TestProcedimientosSpider:

    def test_procedimientos_spider_extracts_ficha_completa(self) -> None:
        from server.app.modules.agents_hub.ingestion.spiders.procedimientos_spider import ProcedimientosSpider

        spider = ProcedimientosSpider()
        doc = spider.extract_document(url="https://procedimientos.uji.es/proc/042", html=SAMPLE_PROCEDIMIENTO_HTML)

        assert doc is not None
        assert "PROC-042" in doc.codigo
        assert "Secretaría General" in doc.unidad_responsable
        assert "DNI" in doc.documentacion_requerida

    def test_procedimientos_spider_builds_hub_document_with_type(self) -> None:
        from server.app.modules.agents_hub.ingestion.spiders.procedimientos_spider import ProcedimientosSpider

        spider = ProcedimientosSpider()
        doc = spider.extract_document(url="https://procedimientos.uji.es/proc/042", html=SAMPLE_PROCEDIMIENTO_HTML)

        assert doc is not None
        assert doc.metadata_json["doc_type"] == "procedimiento"
        assert doc.metadata_json["codigo"] == "PROC-042"


class TestSpiderFactory:

    def test_spider_factory_returns_correct_spider_by_source_type(self) -> None:
        from server.app.modules.agents_hub.ingestion.spider_factory import SpiderFactory
        from server.app.modules.agents_hub.ingestion.spiders.normativa_spider import NormativaSpider
        from server.app.modules.agents_hub.ingestion.spiders.procedimientos_spider import ProcedimientosSpider
        from server.app.modules.agents_hub.ingestion.spider import GenericSpider

        factory = SpiderFactory()
        assert isinstance(factory.get_spider("boe"), NormativaSpider)
        assert isinstance(factory.get_spider("dogv"), NormativaSpider)
        assert isinstance(factory.get_spider("procedimientos"), ProcedimientosSpider)
        assert isinstance(factory.get_spider("generic"), GenericSpider)

    def test_spider_factory_raises_for_unknown_type(self) -> None:
        from server.app.modules.agents_hub.ingestion.spider_factory import SpiderFactory

        factory = SpiderFactory()
        with pytest.raises(ValueError, match="Unknown spider type"):
            factory.get_spider("tipo_inexistente")
```

**Criterios de aceptación**:
- `NormativaSpider` extrae título, fecha y texto; filtra por `date_from`; produce `HubDocument` con metadatos.
- `ProcedimientosSpider` extrae la ficha completa y produce `HubDocument` con `doc_type=procedimiento`.
- `SpiderFactory` selecciona el spider correcto por `source_type`; lanza `ValueError` para tipos desconocidos.
- Migración Alembic añade `spider_type` a `hub_web_sources`.
- Los 7 tests pasan en verde.

---

### Prompt 1A.3 — Asistente HITL de Ingestión: Propuesta Automática de Selectores CSS (TDD RED/GREEN)

**Objetivo**: Implementar el asistente de ingestión que, dado el HTML de una página web (pegado por el Admin), propone automáticamente los selectores CSS del contenido principal. El Admin revisa y valida la propuesta antes de que se persista en `HubWebSource`.

**Contexto**: Elimina la necesidad de que el Admin conozca CSS. Patrón HITL estricto: la IA propone, el humano aprueba, nunca se persiste sin clic explícito. El HTML se trunca antes de enviarlo al LLM para controlar el coste.

**Instrucciones al agente**:
```text
Actúa como experto en FastAPI y LLMs. Implementa el asistente HITL de ingestión.

BACKEND — HtmlAnalyzerService en server/app/modules/agents_hub/services/html_analyzer_service.py:
  Constructor: __init__(self, llm_service: LLMServiceProtocol)
  Método principal: async analyze(html: str, url_hint: str) -> AnalysisResult
  Lanza EmptyHtmlError si html está vacío o solo contiene espacios.

LÓGICA:
1. Truncar el HTML a 10.000 caracteres (preservar inicio del body para capturar estructura).
2. Enviar al LLM con un prompt que solicita un JSON {"content": "...", "title": "...", "date": "..."}.
3. Parsear la respuesta JSON del LLM. Si falla el parse, devolver confidence=0.0 y selectores vacíos.
4. Validar cada selector contra el HTML real con BeautifulSoup. Eliminar los que no machan ningún elemento.
5. Para los selectores válidos, extraer sample_extraction (primeros 200 chars del texto encontrado).
6. Calcular confidence como ratio de selectores válidos / selectores propuestos.

TIPOS:
  @dataclass class AnalysisResult:
      proposed_selectors: dict[str, str | None]  # clave -> selector CSS o None si no validó
      confidence: float
      sample_extraction: dict[str, str]  # clave -> texto extraído

ENDPOINT — añadir a hub_ingestion_router.py:
  POST /api/v1/hub/ingestion/analyze-html
  Request: { "html": "...", "url_hint": "..." }
  Response: AnalysisResult serializado como JSON

FRONTEND — AdminIngestionAssistant.tsx en frontend/src/admin/pages/:
  - Textarea para pegar HTML (o URL para fetch desde backend).
  - Botón "Analizar" -> llama al endpoint.
  - Preview: muestra selectores propuestos + sample_extraction por cada campo.
  - Botón "Guardar Fuente" (deshabilitado hasta que se haya mostrado la preview al menos una vez).
  - Al guardar: POST /api/v1/hub/sources con config_json = {proposed_selectors, ...otros campos}.

TESTS REQUERIDOS:
- test_html_analyzer_returns_proposed_selectors_as_json
- test_html_analyzer_validates_selectors_against_html
- test_html_analyzer_includes_sample_extraction
- test_endpoint_rejects_empty_html
- test_html_is_truncated_before_sending_to_llm
```

**Tests RED — tests/modules/agents_hub/unit/test_html_analyzer.py**:
```python
"""Tests para el asistente HITL de análisis HTML — TDD RED."""
import pytest
from unittest.mock import AsyncMock


SAMPLE_INSTITUTIONAL_HTML = """
<html><head><title>Normativa - UJI</title></head>
<body>
  <header class="site-header"><nav>Menu</nav></header>
  <main>
    <h1 class="page-title">Reglamento de Doctorado</h1>
    <span class="pub-date">Aprobado: 20/02/2024</span>
    <article class="entry-content">
      <p>El presente reglamento regula los estudios de doctorado en la UJI.</p>
      <p>Artículo 1. El programa de doctorado tendrá una duración máxima de tres años.</p>
    </article>
  </main>
  <footer>Universitat Jaume I</footer>
</body></html>
"""


class TestHtmlAnalyzerService:

    @pytest.mark.asyncio
    async def test_html_analyzer_returns_proposed_selectors_as_json(self) -> None:
        from server.app.modules.agents_hub.services.html_analyzer_service import HtmlAnalyzerService

        llm_mock = AsyncMock()
        llm_mock.generate.return_value = (
            '{"content": "article.entry-content", "title": "h1.page-title", "date": "span.pub-date"}'
        )

        service = HtmlAnalyzerService(llm_service=llm_mock)
        result = await service.analyze(html=SAMPLE_INSTITUTIONAL_HTML, url_hint="https://www.uji.es/normativa")

        assert "content" in result.proposed_selectors
        assert "title" in result.proposed_selectors
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_html_analyzer_validates_selectors_against_html(self) -> None:
        """Los selectores que no machan elementos reales se eliminan de la propuesta."""
        from server.app.modules.agents_hub.services.html_analyzer_service import HtmlAnalyzerService

        llm_mock = AsyncMock()
        llm_mock.generate.return_value = (
            '{"content": "article.entry-content", "title": "h1.page-title", "date": "span.nonexistent"}'
        )

        service = HtmlAnalyzerService(llm_service=llm_mock)
        result = await service.analyze(html=SAMPLE_INSTITUTIONAL_HTML, url_hint="")

        assert result.proposed_selectors.get("content") == "article.entry-content"
        assert result.proposed_selectors.get("title") == "h1.page-title"
        assert result.proposed_selectors.get("date") is None  # no macha -> eliminado

    @pytest.mark.asyncio
    async def test_html_analyzer_includes_sample_extraction(self) -> None:
        """sample_extraction contiene el texto real extraído con los selectores válidos."""
        from server.app.modules.agents_hub.services.html_analyzer_service import HtmlAnalyzerService

        llm_mock = AsyncMock()
        llm_mock.generate.return_value = '{"content": "article.entry-content", "title": "h1.page-title"}'

        service = HtmlAnalyzerService(llm_service=llm_mock)
        result = await service.analyze(html=SAMPLE_INSTITUTIONAL_HTML, url_hint="")

        assert "Reglamento de Doctorado" in result.sample_extraction.get("title", "")
        assert "doctorado" in result.sample_extraction.get("content", "").lower()

    @pytest.mark.asyncio
    async def test_endpoint_rejects_empty_html(self) -> None:
        from server.app.modules.agents_hub.services.html_analyzer_service import (
            HtmlAnalyzerService,
            EmptyHtmlError,
        )

        service = HtmlAnalyzerService(llm_service=AsyncMock())
        with pytest.raises(EmptyHtmlError):
            await service.analyze(html="", url_hint="")

    @pytest.mark.asyncio
    async def test_html_is_truncated_before_sending_to_llm(self) -> None:
        """El fragmento enviado al LLM no supera 10.000 caracteres."""
        from server.app.modules.agents_hub.services.html_analyzer_service import HtmlAnalyzerService

        captured_prompts: list[str] = []

        async def fake_generate(prompt: str) -> str:
            captured_prompts.append(prompt)
            return '{"content": "p", "title": "h1"}'

        llm_mock = AsyncMock()
        llm_mock.generate.side_effect = fake_generate

        service = HtmlAnalyzerService(llm_service=llm_mock)
        large_html = "<html><body>" + "x" * 50_000 + "</body></html>"
        await service.analyze(html=large_html, url_hint="")

        assert len(captured_prompts[0]) <= 12_000
```

**Tests Vitest (frontend) — frontend/src/admin/pages/__tests__/AdminIngestionAssistant.test.tsx**:
```typescript
// Tests a implementar (RED antes de escribir el componente):
// - should_disable_save_button_until_preview_is_shown
// - should_enable_save_button_after_analyze_response_is_rendered
// - should_call_analyze_endpoint_with_pasted_html
// - should_persist_proposed_selectors_on_save_click
```

**Criterios de aceptación**:
- `POST /api/v1/hub/ingestion/analyze-html` devuelve `proposed_selectors`, `confidence` y `sample_extraction`.
- Los selectores se validan contra el HTML con BeautifulSoup; los que no machan se devuelven como `null`.
- El HTML se trunca a 10.000 caracteres antes de enviarlo al LLM.
- El botón "Guardar Fuente" permanece deshabilitado hasta que el Admin ha visto la previsualización.
- Los 5 tests Python y los 4 tests Vitest pasan en verde.

---

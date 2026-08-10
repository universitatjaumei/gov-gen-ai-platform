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
        from server.app.modules.curation.spiders.normativa_spider import NormativaSpider

        spider = NormativaSpider(source_type="boe")
        doc = spider.extract_document(url="https://boe.es/doc", html=SAMPLE_BOE_HTML)

        assert doc is not None
        assert "Real Decreto" in doc.titulo
        assert doc.fecha_publicacion == date(2025, 3, 15)
        assert "Artículo 1" in doc.texto

    def test_normativa_spider_skips_documents_before_date_from(self) -> None:
        from server.app.modules.curation.spiders.normativa_spider import NormativaSpider

        spider = NormativaSpider(source_type="boe", date_from=date(2026, 1, 1))
        doc = spider.extract_document(url="https://boe.es/doc", html=SAMPLE_BOE_HTML)

        assert doc is None

    def test_normativa_spider_builds_hub_document_with_metadata(self) -> None:
        from server.app.modules.curation.spiders.normativa_spider import NormativaSpider

        spider = NormativaSpider(source_type="boe")
        doc = spider.extract_document(url="https://boe.es/doc", html=SAMPLE_BOE_HTML)

        assert doc is not None
        assert doc.metadata_json["source_type"] == "boe"
        assert doc.metadata_json["fecha_publicacion"] == "2025-03-15"


class TestProcedimientosSpider:

    def test_procedimientos_spider_extracts_ficha_completa(self) -> None:
        from server.app.modules.curation.spiders.procedimientos_spider import ProcedimientosSpider

        spider = ProcedimientosSpider()
        doc = spider.extract_document(url="https://procedimientos.uji.es/proc/042", html=SAMPLE_PROCEDIMIENTO_HTML)

        assert doc is not None
        assert "Solicitud de título" in doc.nombre
        assert "DNI" in doc.documentacion_requerida

    def test_procedimientos_spider_builds_hub_document_with_type(self) -> None:
        from server.app.modules.curation.spiders.procedimientos_spider import ProcedimientosSpider

        spider = ProcedimientosSpider()
        doc = spider.extract_document(url="https://procedimientos.uji.es/proc/042", html=SAMPLE_PROCEDIMIENTO_HTML)

        assert doc is not None
        assert doc.metadata_json["doc_type"] == "procedimiento"
        assert doc.metadata_json["codigo"] == "PROC-042"


class TestSpiderFactory:

    def test_spider_factory_returns_correct_spider_by_source_type(self) -> None:
        from server.app.modules.curation.spider_factory import SpiderFactory
        from server.app.modules.curation.spiders.normativa_spider import NormativaSpider
        from server.app.modules.curation.spiders.procedimientos_spider import ProcedimientosSpider
        from server.app.modules.curation.spider import GenericSpider

        factory = SpiderFactory()
        assert isinstance(factory.get_spider("boe"), NormativaSpider)
        assert isinstance(factory.get_spider("dogv"), NormativaSpider)
        assert isinstance(factory.get_spider("procedimientos"), ProcedimientosSpider)
        assert isinstance(factory.get_spider("generic"), GenericSpider)

    def test_spider_factory_raises_for_unknown_type(self) -> None:
        from server.app.modules.curation.spider_factory import SpiderFactory

        factory = SpiderFactory()
        with pytest.raises(ValueError, match="Unknown spider type"):
            factory.get_spider("tipo_inexistente")

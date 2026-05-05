"""Factory que selecciona el spider adecuado según el tipo de fuente web.

Deploy: edge
"""
from server.app.modules.agents_hub.ingestion.spider import GenericSpider
from server.app.modules.agents_hub.ingestion.spiders.normativa_spider import NormativaSpider
from server.app.modules.agents_hub.ingestion.spiders.procedimientos_spider import ProcedimientosSpider

_NORMATIVA_SOURCE_TYPES = frozenset({"boe", "dogv", "uji"})


class SpiderFactory:
    """Devuelve el spider correcto según spider_type de HubIngestionSource."""

    def get_spider(
        self, source_type: str
    ) -> NormativaSpider | ProcedimientosSpider | GenericSpider:
        if source_type in _NORMATIVA_SOURCE_TYPES:
            return NormativaSpider(source_type=source_type)
        if source_type == "procedimientos":
            return ProcedimientosSpider()
        if source_type == "generic":
            return GenericSpider()
        raise ValueError(f"Unknown spider type: {source_type}")

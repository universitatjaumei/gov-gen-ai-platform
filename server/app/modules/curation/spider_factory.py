"""Factory que selecciona el spider adecuado según el tipo de fuente web.

Deploy: edge
"""
from server.app.modules.curation.spider import GenericSpider
from server.app.modules.curation.spiders.normativa_spider import NormativaSpider
from server.app.modules.curation.spiders.procedimientos_spider import ProcedimientosSpider

# AIS.2 — sin el nombre de ninguna institución. El tipo describe la **forma** del portal y no de
# quién es: la entrada que se retiró tenía los mismos tres selectores que `boe`, así que no
# añadía un marcado, añadía un alias. El portal propio de una institución se rastrea con
# `generic` —o con su tipo en el fork—, que es lo que `CONTRIBUTING.md` pide.
_NORMATIVA_SOURCE_TYPES = frozenset({"boe", "dogv"})


class SpiderFactory:
    """Devuelve el spider correcto según `spider_type` (campo de HubWebSite)."""

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

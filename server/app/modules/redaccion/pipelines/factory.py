"""ExtractionPipelineFactory — registro y selección de pipelines por source_kind (9R.5.4)."""
from __future__ import annotations

from server.app.modules.redaccion.pipelines.contracts import (
    ExtractionPipeline,
    ExtractionPipelineId,
)


class UnknownSourceKindError(ValueError):
    """No hay pipeline registrado para el source_kind solicitado."""


class ExtractionPipelineFactory:
    """Registro centralizado de pipelines de extracción.

    - register(pipeline)          → añade un pipeline al registro.
    - get(source_kind)            → devuelve el primer pipeline que lo soporta.
    - list()                      → lista los pipeline_id registrados.

    El orden de registro determina la prioridad cuando varios pipelines
    declaran soportar el mismo source_kind.
    """

    def __init__(self) -> None:
        self._pipelines: list[ExtractionPipeline] = []

    def register(self, pipeline: ExtractionPipeline) -> None:
        self._pipelines.append(pipeline)

    def get(self, source_kind: str) -> ExtractionPipeline:
        for pipeline in self._pipelines:
            if pipeline.supports(source_kind):
                return pipeline
        raise UnknownSourceKindError(
            f"No hay pipeline registrado para source_kind='{source_kind}'. "
            f"Disponibles: {[p.pipeline_id for p in self._pipelines]}"
        )

    def list(self) -> list[ExtractionPipelineId]:
        return [p.pipeline_id for p in self._pipelines]


def build_default_factory() -> ExtractionPipelineFactory:
    """Construye un factory con todos los pipelines concretos registrados.

    Las importaciones son tardías para evitar cargar Docling u otras
    dependencias pesadas en el momento de importar este módulo.
    """
    from server.app.modules.redaccion.pipelines.admin_script_pipeline import (
        AdminScriptExtractionPipeline,
    )
    from server.app.modules.redaccion.pipelines.excel_pipeline import ExcelExtractionPipeline
    from server.app.modules.redaccion.pipelines.manual_pipeline import ManualInputPipeline
    from server.app.modules.redaccion.pipelines.md_table_pipeline import (
        MarkdownTableExtractionPipeline,
    )
    from server.app.modules.redaccion.pipelines.pdf_table_pipeline import (
        PDFTableExtractionPipeline,
    )
    from server.app.modules.redaccion.pipelines.pdf_text_pipeline import (
        PDFTextExtractionPipeline,
    )

    factory = ExtractionPipelineFactory()
    factory.register(ExcelExtractionPipeline())
    factory.register(PDFTextExtractionPipeline())
    factory.register(PDFTableExtractionPipeline())
    factory.register(ManualInputPipeline())
    factory.register(AdminScriptExtractionPipeline())
    factory.register(MarkdownTableExtractionPipeline())
    return factory

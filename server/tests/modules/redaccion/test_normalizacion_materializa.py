"""VER.4 — el fichero subido tiene que llegar al pipeline de extracción.

`FileNormalizationNode` copiaba el `storage_path` tal cual a `artifacts_normalized`, y
`ExcelExtractionPipeline` hace `Path(bucket) / key`: es decir, **abre una ruta del sistema de
archivos**. Con `StorageService` escribiendo bajo `STORAGE_BUCKET`, el pipeline buscaba
`redaccion/<id>/inputs/...` relativo al directorio de trabajo y no encontraba nada:

    [Errno 2] No such file or directory: 'redaccion\\<id>\\inputs\\budget_data_file\\...xlsx'

Además de romper aquí, eso viola la regla de portabilidad del proyecto: los documentos de
negocio se leen por `StorageService`, no del disco. Con el backend en GCS no habría fichero
que abrir.

La solución no es reescribir los cinco pipelines: es que el nodo de **normalización** —que
para eso recibe el `storage_service` y para eso se llama así— materialice el artefacto en un
fichero temporal de la ejecución y publique **esa** ruta.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from server.app.modules.redaccion.contracts.runtime import InputArtifact, WorkspaceState
from server.app.modules.redaccion.graph.nodes.file_normalization import FileNormalizationNode


class _Almacen:
    """Doble de `StorageService`: guarda en memoria, como haría GCS."""

    def __init__(self, contenido: bytes = b"datos binarios") -> None:
        self.contenido = contenido
        self.leidos: list[str] = []

    async def get(self, key: str) -> bytes:
        self.leidos.append(key)
        return self.contenido


def _estado(**extra) -> WorkspaceState:
    return WorkspaceState(
        workspace_id=uuid.uuid4(),
        template_version_id=uuid.uuid4(),
        report_profile="GENERIC_REPORT",
        inputs={
            "datos_excel": InputArtifact(
                slot_id="datos_excel",
                filename="ejecucion.xlsx",
                storage_path="redaccion/w1/inputs/datos_excel/ejecucion.xlsx",
                size_bytes=10,
                uploaded_at=datetime.now(timezone.utc),
            )
        },
        blocks={},
        status="drafting",
        warnings=[],
        **extra,
    )


class TestLaNormalizacion:

    @pytest.mark.asyncio
    async def test_should_read_the_artifact_through_the_storage_service(self):
        almacen = _Almacen()

        await FileNormalizationNode(almacen).__call__(_estado())

        assert almacen.leidos == ["redaccion/w1/inputs/datos_excel/ejecucion.xlsx"]

    @pytest.mark.asyncio
    async def test_should_publish_a_path_that_actually_exists_on_disk(self):
        """Es lo que el pipeline abre. Si no existe, la extracción falla con Errno 2."""
        almacen = _Almacen(b"contenido de prueba")

        salida = await FileNormalizationNode(almacen).__call__(_estado())

        ruta = Path(salida["artifacts_normalized"]["datos_excel"])
        assert ruta.exists()
        assert ruta.read_bytes() == b"contenido de prueba"

    @pytest.mark.asyncio
    async def test_should_keep_the_original_extension(self):
        """`ExcelExtractionPipeline` abre por extensión: sin `.xlsx` no sabe qué es."""
        salida = await FileNormalizationNode(_Almacen()).__call__(_estado())

        assert Path(salida["artifacts_normalized"]["datos_excel"]).suffix == ".xlsx"

    @pytest.mark.asyncio
    async def test_should_not_fail_the_whole_run_when_one_artifact_is_missing(self):
        """Un slot cuyo fichero ya no está en el almacén no puede impedir que se genere el
        resto del informe: el bloque que lo necesitaba avisará por su cuenta."""
        class _Vacio:
            async def get(self, key: str) -> bytes:
                raise FileNotFoundError(key)

        salida = await FileNormalizationNode(_Vacio()).__call__(_estado())

        assert salida["artifacts_normalized"] == {}

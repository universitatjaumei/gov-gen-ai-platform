"""Tests para ExportService (DOCX/ODT) — TDD 1C.4."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass, field


@dataclass
class FakeChunk:
    source_url: str
    page: int | None
    text: str


@dataclass
class FakeRunManifest:
    retrieved_chunks: list[FakeChunk] = field(default_factory=list)


SAMPLE_MARKDOWN = """# Informe de Análisis Normativo

## 1. Introducción
El presente informe analiza la normativa vigente [^1].

## 2. Marco Legal
Las obligaciones se recogen en el artículo 15 [^2].

## 3. Conclusiones
El cumplimiento es obligatorio desde enero de 2025.
"""


class TestExportService:

    @pytest.fixture
    def storage_mock(self):
        mock = AsyncMock()
        mock.put.return_value = None
        mock.get_url.return_value = "https://storage.example.com/exports/ws-1/informe.docx"
        return mock

    @pytest.fixture
    def run_manifest(self):
        return FakeRunManifest(retrieved_chunks=[
            FakeChunk(source_url="https://boe.es/doc/1", page=3, text="normativa vigente"),
            FakeChunk(source_url="https://normativa.uji.es/art15", page=None, text="artículo 15"),
        ])

    @pytest.mark.asyncio
    async def test_export_service_generates_docx_file(self, storage_mock, run_manifest) -> None:
        from server.app.modules.agents_hub.services.export_service import ExportService

        service = ExportService(storage=storage_mock)
        result = await service.export(
            workspace_id="ws-1",
            final_document=SAMPLE_MARKDOWN,
            run_manifest=run_manifest,
            format="docx",
            theme=None,
        )

        assert result.format == "docx"
        assert result.file_path.endswith(".docx")
        assert result.size_bytes > 0
        storage_mock.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_service_generates_odt_file(self, storage_mock, run_manifest) -> None:
        from server.app.modules.agents_hub.services.export_service import ExportService

        service = ExportService(storage=storage_mock)
        result = await service.export(
            workspace_id="ws-1",
            final_document=SAMPLE_MARKDOWN,
            run_manifest=run_manifest,
            format="odt",
            theme=None,
        )

        assert result.format == "odt"
        assert result.file_path.endswith(".odt")

    @pytest.mark.asyncio
    async def test_export_includes_footnotes_from_run_manifest(self, storage_mock, run_manifest) -> None:
        """El documento exportado contiene las referencias del RunManifest como notas a pie."""
        from server.app.modules.agents_hub.services.export_service import ExportService
        import io
        from docx import Document

        written_bytes: list[bytes] = []

        async def capture_put(path: str, data: bytes) -> None:
            written_bytes.append(data)

        storage_mock.put.side_effect = capture_put

        service = ExportService(storage=storage_mock)
        await service.export(
            workspace_id="ws-1",
            final_document=SAMPLE_MARKDOWN,
            run_manifest=run_manifest,
            format="docx",
            theme=None,
        )

        assert len(written_bytes) == 1
        doc = Document(io.BytesIO(written_bytes[0]))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "boe.es" in full_text or "boe.es" in str(doc.element.xml)

    @pytest.mark.asyncio
    async def test_export_includes_table_of_contents(self, storage_mock, run_manifest) -> None:
        """El documento contiene una entrada de índice por cada H2 del Markdown."""
        from server.app.modules.agents_hub.services.export_service import ExportService
        import io
        from docx import Document

        written_bytes: list[bytes] = []

        async def capture_put(path: str, data: bytes) -> None:
            written_bytes.append(data)

        storage_mock.put.side_effect = capture_put

        service = ExportService(storage=storage_mock)
        await service.export(
            workspace_id="ws-1",
            final_document=SAMPLE_MARKDOWN,
            run_manifest=run_manifest,
            format="docx",
            theme=None,
        )

        doc = Document(io.BytesIO(written_bytes[0]))
        headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
        assert any("Introducción" in h for h in headings)
        assert any("Marco Legal" in h for h in headings)
        assert any("Conclusiones" in h for h in headings)

    @pytest.mark.asyncio
    async def test_export_applies_theme_colors_if_provided(self, storage_mock, run_manifest) -> None:
        """Cuando se proporciona ThemeConfig, el documento usa los colores institucionales."""
        from server.app.modules.agents_hub.services.export_service import ExportService

        theme_mock = MagicMock()
        theme_mock.colors = {"primary": "#003366", "secondary": "#FFFFFF"}
        theme_mock.typography = {"font_family": "Arial"}

        service = ExportService(storage=storage_mock)
        result = await service.export(
            workspace_id="ws-1",
            final_document=SAMPLE_MARKDOWN,
            run_manifest=run_manifest,
            format="docx",
            theme=theme_mock,
        )

        assert result.size_bytes > 0

    @pytest.mark.asyncio
    async def test_endpoint_returns_download_url(self, storage_mock) -> None:
        import httpx
        from server.app.main import app

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/hub/agents/workspaces/ws-nonexistent/export",
                json={"format": "docx"},
                headers={"Authorization": "Bearer test-token"},
            )
        assert response.status_code != 405

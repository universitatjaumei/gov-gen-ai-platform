"""VER.7 — un PDF que no es un PDF no puede llamarse PDF.

`to_pdf` cae a DOCX cuando LibreOffice no está disponible —degradación razonable— pero el
router respondía igualmente `content-type: application/pdf` y
`Content-Disposition: filename="informe_calidad_<id>.pdf"`. Medido en vivo: los dos bytes
iniciales del supuesto PDF eran `PK`, la firma de un ZIP.

Quien lo descarga se lleva un fichero que Adobe no abre y que no dice por qué. El fallback
tiene que **verse**: el tipo y la extensión son los del fichero que de verdad se está
sirviendo.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

DOCX = b"PK\x03\x04 contenido docx"
PDF = b"%PDF-1.4 contenido"


class _Constructor:
    async def build(self, site_id):
        return object()


def _exportador(salida: bytes):
    exportador = AsyncMock()
    exportador.to_pdf = AsyncMock(return_value=salida)
    exportador.to_docx = AsyncMock(return_value=DOCX)
    return exportador


async def _exportar(salida: bytes):
    from server.app.core.auth.models import UserInfo
    from server.app.routers.hub_content_quality_router import export_site_report

    async def _sin_comprobar(*_args, **_kwargs):
        return None

    import server.app.routers.hub_content_quality_router as modulo

    original = modulo.assert_site_org_access
    modulo.assert_site_org_access = _sin_comprobar
    try:
        return await export_site_report(
            site_id=uuid.uuid4(),
            report_format="pdf",
            current_user=UserInfo(user_id="1", email="admin@example.local", role="superadmin"),
            builder=_Constructor(),
            exporter=_exportador(salida),
            session=AsyncMock(),
        )
    finally:
        modulo.assert_site_org_access = original


class TestLaExportacion:

    @pytest.mark.asyncio
    async def test_should_serve_a_real_pdf_as_a_pdf(self):
        respuesta = await _exportar(PDF)

        assert respuesta.media_type == "application/pdf"
        assert ".pdf" in respuesta.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_should_not_call_a_docx_a_pdf(self):
        """Sin LibreOffice el contenido es un DOCX: decirlo es la diferencia entre una
        degradación y un fichero roto."""
        respuesta = await _exportar(DOCX)

        assert respuesta.media_type != "application/pdf"
        assert ".docx" in respuesta.headers["content-disposition"]
        assert ".pdf" not in respuesta.headers["content-disposition"]


# ───────── CUR.8 — o el boton hace PDF o no esta ─────────
#
# Del usuario, tras descargar: «al darle a descargar al pdf descarga un word. No es mucho problema.
# Podría descargarse solo word pero o se quita el botón o se permite que la descarga sea en pdf».
# Tiene razón: un botón que promete PDF y entrega DOCX es una promesa incumplida aunque el fichero
# esté bien etiquetado. La respuesta honesta es ofrecerlo **sólo cuando se puede cumplir**, y para
# eso hace falta que el servidor diga si puede.


class TestSiSePuedeHacerPdf:

    def test_dice_que_no_cuando_libreoffice_no_esta(self, monkeypatch):
        from server.app.modules.curation import report_exporter

        monkeypatch.setattr(report_exporter.shutil, "which", lambda _nombre: None)

        assert report_exporter.se_puede_convertir_a_pdf() is False

    def test_dice_que_si_cuando_libreoffice_esta(self, monkeypatch):
        from server.app.modules.curation import report_exporter

        monkeypatch.setattr(
            report_exporter.shutil, "which", lambda nombre: "/usr/bin/soffice" if nombre else None
        )

        assert report_exporter.se_puede_convertir_a_pdf() is True

    def test_busca_los_dos_nombres_del_ejecutable(self, monkeypatch):
        """En Linux es `libreoffice` y en Windows `soffice`: buscar solo uno diria que no puede
        cuando si puede."""
        from server.app.modules.curation import report_exporter

        buscados: list[str] = []

        def _which(nombre: str):
            buscados.append(nombre)
            return None

        monkeypatch.setattr(report_exporter.shutil, "which", _which)
        report_exporter.se_puede_convertir_a_pdf()

        assert "soffice" in buscados
        assert "libreoffice" in buscados


class TestElInformeDiceQueFormatosTiene:

    @pytest.mark.asyncio
    async def test_el_informe_declara_si_el_pdf_esta_disponible(self):
        """La pantalla no puede adivinarlo, y preguntarlo aparte seria una peticion mas por
        informe."""
        from server.app.modules.curation.report_contracts import WebQualityReport

        assert "pdf_available" in WebQualityReport.model_fields

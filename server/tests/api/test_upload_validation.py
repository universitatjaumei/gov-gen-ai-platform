"""Tests SEC.6 — validación robusta de subidas (core/uploads.py).

El `content_type` de un multipart lo fija el cliente, así que es spoofeable: la
validación real tiene que mirar la extensión y los *magic bytes*. Y el corte por
tamaño debe ocurrir mientras se lee, no después de haberse tragado el fichero
entero en memoria.

La validación es compartida: la reutilizará el Bloque ING para .md/.txt.
"""
from __future__ import annotations

import io

import pytest
from fastapi import HTTPException, UploadFile

from server.app.core.uploads import (
    MAGIC_PDF,
    UploadKind,
    validate_upload,
)

PDF_VALIDO = MAGIC_PDF + b"1.7\n%%EOF\n"


def _upload(nombre: str, contenido: bytes, content_type: str = "application/pdf") -> UploadFile:
    return UploadFile(
        filename=nombre,
        file=io.BytesIO(contenido),
        headers={"content-type": content_type},
    )


async def _leer(buffer) -> bytes:
    buffer.seek(0)
    return buffer.read()


# ---------------------------------------------------------------------------
# Tipo real: extensión + magic bytes, no content_type
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_should_accept_valid_pdf() -> None:
    buffer = await validate_upload(_upload("informe.pdf", PDF_VALIDO), kind=UploadKind.PDF)
    assert await _leer(buffer) == PDF_VALIDO


@pytest.mark.asyncio
async def test_should_reject_pdf_content_type_with_non_pdf_magic_bytes() -> None:
    """Un ejecutable renombrado a .pdf y anunciado como application/pdf."""
    disfrazado = _upload("malicioso.pdf", b"MZ\x90\x00falso ejecutable")

    with pytest.raises(HTTPException) as exc:
        await validate_upload(disfrazado, kind=UploadKind.PDF)

    assert exc.value.status_code == 415
    assert "contenido" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_should_reject_disallowed_extension() -> None:
    with pytest.raises(HTTPException) as exc:
        await validate_upload(_upload("script.exe", PDF_VALIDO), kind=UploadKind.PDF)

    assert exc.value.status_code == 415
    assert "extens" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_should_not_trust_a_correct_content_type_alone() -> None:
    """Extensión buena + content_type bueno + contenido falso -> rechazo."""
    with pytest.raises(HTTPException):
        await validate_upload(
            _upload("bueno.pdf", b"no soy un pdf", content_type="application/pdf"),
            kind=UploadKind.PDF,
        )


@pytest.mark.asyncio
async def test_should_reject_file_without_filename() -> None:
    with pytest.raises(HTTPException) as exc:
        await validate_upload(_upload("", PDF_VALIDO), kind=UploadKind.PDF)
    assert exc.value.status_code == 415


# ---------------------------------------------------------------------------
# Límite de tamaño, cortando durante la lectura
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_should_reject_upload_exceeding_max_size() -> None:
    grande = _upload("grande.pdf", PDF_VALIDO + b"x" * 5_000)

    with pytest.raises(HTTPException) as exc:
        await validate_upload(grande, kind=UploadKind.PDF, max_bytes=1_000)

    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_should_stop_reading_once_the_limit_is_exceeded() -> None:
    """No basta con devolver 413: hay que dejar de leer. Si el validador se
    tragase el fichero entero, una subida de 2 GB tumbaría el proceso aunque la
    respuesta fuese correcta."""
    leidos = {"total": 0}

    class _ContadoraDeLecturas(io.BytesIO):
        def read(self, size: int = -1) -> bytes:  # type: ignore[override]
            datos = super().read(size)
            leidos["total"] += len(datos)
            return datos

    enorme = UploadFile(
        filename="enorme.pdf",
        file=_ContadoraDeLecturas(PDF_VALIDO + b"x" * 2_000_000),
        headers={"content-type": "application/pdf"},
    )

    with pytest.raises(HTTPException):
        await validate_upload(enorme, kind=UploadKind.PDF, max_bytes=10_000)

    assert leidos["total"] < 200_000, (
        f"se leyeron {leidos['total']} bytes para un límite de 10 000: "
        "el corte debe ocurrir durante la lectura"
    )


@pytest.mark.asyncio
async def test_should_accept_a_file_exactly_at_the_limit() -> None:
    relleno = b"x" * (1_000 - len(PDF_VALIDO))
    justo = _upload("justo.pdf", PDF_VALIDO + relleno)

    buffer = await validate_upload(justo, kind=UploadKind.PDF, max_bytes=1_000)
    assert len(await _leer(buffer)) == 1_000


@pytest.mark.asyncio
async def test_should_reject_empty_file() -> None:
    with pytest.raises(HTTPException) as exc:
        await validate_upload(_upload("vacio.pdf", b""), kind=UploadKind.PDF)
    assert exc.value.status_code == 415


# ---------------------------------------------------------------------------
# Reutilización por el Bloque ING: markdown y texto plano
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_should_accept_markdown_for_the_ingestion_block() -> None:
    contenido = "# Normativa\n\nTexto de ejemplo.\n".encode("utf-8")
    buffer = await validate_upload(
        _upload("norma.md", contenido, content_type="text/markdown"),
        kind=UploadKind.TEXT,
    )
    assert await _leer(buffer) == contenido


@pytest.mark.asyncio
async def test_should_reject_binary_content_disguised_as_markdown() -> None:
    """Los formatos de texto no tienen magic bytes. Decodificar no basta: bytes
    de control como \\x00\\x01\\x02 son UTF-8 válido. La señal es el byte NUL,
    que el texto legítimo no contiene."""
    with pytest.raises(HTTPException) as exc:
        await validate_upload(
            _upload("falso.md", b"\x00\x01\x02\x03binario", content_type="text/markdown"),
            kind=UploadKind.TEXT,
        )
    assert exc.value.status_code == 415


@pytest.mark.asyncio
async def test_pdf_kind_must_not_accept_markdown_extension() -> None:
    with pytest.raises(HTTPException):
        await validate_upload(_upload("norma.md", PDF_VALIDO), kind=UploadKind.PDF)


# ---------------------------------------------------------------------------
# Límite configurable por entorno
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_default_max_bytes_comes_from_settings() -> None:
    from server.app.core.config import get_settings
    from server.app.core.uploads import default_max_bytes

    ajustes = get_settings()
    assert default_max_bytes() == ajustes.max_upload_mb * 1024 * 1024
    assert ajustes.max_upload_mb > 0


# ---------------------------------------------------------------------------
# Cuota de documentos por chatbot
# ---------------------------------------------------------------------------

def test_quota_allows_when_limit_is_zero(monkeypatch) -> None:
    """0 significa 'sin límite', no 'bloqueado'."""
    from server.app.core import uploads as mod

    monkeypatch.setattr(mod, "get_settings", lambda: _ajustes(max_documents_per_chatbot=0))
    mod.assert_within_document_quota(9_999)  # no debe lanzar


def test_quota_rejects_when_limit_reached(monkeypatch) -> None:
    from server.app.core import uploads as mod

    monkeypatch.setattr(mod, "get_settings", lambda: _ajustes(max_documents_per_chatbot=3))
    with pytest.raises(HTTPException) as exc:
        mod.assert_within_document_quota(3)

    assert exc.value.status_code == 429
    assert "3" in str(exc.value.detail)


def test_quota_allows_below_the_limit(monkeypatch) -> None:
    from server.app.core import uploads as mod

    monkeypatch.setattr(mod, "get_settings", lambda: _ajustes(max_documents_per_chatbot=3))
    mod.assert_within_document_quota(2)


def _ajustes(**kwargs):
    from server.app.core.config import get_settings

    base = get_settings()

    class _Falsos:
        def __getattr__(self, nombre):
            return kwargs.get(nombre, getattr(base, nombre))

    return _Falsos()

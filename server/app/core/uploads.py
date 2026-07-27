"""Validación de ficheros subidos (SEC.6).

Un multipart trae el `content_type` que decida el cliente, así que no vale como
control: hay que mirar la **extensión** y los **magic bytes** del contenido real.
Y el límite de tamaño tiene que cortar *mientras* se lee — comprobarlo después de
`await file.read()` ya implica haberse tragado el fichero entero en memoria, que
es justamente el problema.

La validación es compartida a propósito: el Bloque ING la reutilizará para
`.md`/`.txt` sin duplicar reglas.

Deploy: edge
"""
from __future__ import annotations

import tempfile
from enum import Enum
from typing import IO

from fastapi import HTTPException, UploadFile, status

from server.app.core.config import get_settings

MAGIC_PDF = b"%PDF-"

# Tamaño de lectura y umbral a partir del cual el buffer temporal pasa de RAM a
# disco. Mantiene el consumo acotado sea cual sea el tamaño del fichero.
_CHUNK_BYTES = 64 * 1024
_SPOOL_BYTES = 1024 * 1024


class UploadKind(Enum):
    """Familias admitidas. Cada una fija extensiones y firma esperada."""

    PDF = "pdf"
    TEXT = "text"


_REGLAS: dict[UploadKind, dict] = {
    UploadKind.PDF: {
        "extensiones": (".pdf",),
        "magic": (MAGIC_PDF,),
    },
    UploadKind.TEXT: {
        # Los formatos de texto no tienen firma; se validan decodificando.
        "extensiones": (".md", ".markdown", ".txt"),
        "magic": (),
    },
}


def default_max_bytes() -> int:
    return get_settings().max_upload_mb * 1024 * 1024


def assert_within_document_quota(documentos_actuales: int) -> None:
    """Cuota de documentos por chatbot (SEC.6).

    Recibe el recuento ya calculado en lugar de consultarlo: `core/` es capa
    compartida y no debe importar modelos operacionales de `agents_hub`, que son
    dato del cliente final (frontera edge/cloud).

    `MAX_DOCUMENTS_PER_CHATBOT = 0` significa sin límite.
    """
    limite = get_settings().max_documents_per_chatbot
    if limite and documentos_actuales >= limite:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Este chatbot ha alcanzado el límite de {limite} documentos. "
                "Elimina alguno antes de subir más."
            ),
        )


def _rechazar(detalle: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=detalle
    )


def _validar_extension(filename: str | None, extensiones: tuple[str, ...]) -> None:
    if not filename:
        _rechazar("El fichero debe tener nombre y una extensión admitida.")

    nombre = filename.lower()
    if not any(nombre.endswith(ext) for ext in extensiones):
        _rechazar(
            f"Extensión no admitida. Se aceptan: {', '.join(extensiones)}."
        )


def _validar_contenido(cabecera: bytes, kind: UploadKind, magic: tuple[bytes, ...]) -> None:
    if not cabecera:
        _rechazar("El fichero está vacío.")

    if magic:
        if not any(cabecera.startswith(firma) for firma in magic):
            _rechazar(
                "El contenido del fichero no corresponde a su extensión "
                "(firma de tipo incorrecta)."
            )
        return

    # Sin firma que comprobar (texto). Decodificar no basta: bytes de control
    # como \x00\x01\x02 son UTF-8 perfectamente válido y colarían un binario.
    # El byte NUL es la señal que usa todo el mundo (git incluido) para decidir
    # que un fichero es binario; el texto legítimo no lo contiene.
    if b"\x00" in cabecera:
        _rechazar(
            "El contenido del fichero no es texto válido "
            "(parece binario disfrazado)."
        )

    try:
        cabecera.decode("utf-8")
    except UnicodeDecodeError:
        # El corte de la cabecera puede partir un carácter multibyte; se
        # descarta esa posibilidad antes de rechazar.
        try:
            cabecera[: len(cabecera) - 3].decode("utf-8")
        except UnicodeDecodeError:
            _rechazar(
                "El contenido del fichero no es texto válido "
                "(parece binario disfrazado)."
            )


async def validate_upload(
    file: UploadFile,
    *,
    kind: UploadKind,
    max_bytes: int | None = None,
) -> IO[bytes]:
    """Valida extensión, tipo real y tamaño, y devuelve el contenido validado.

    Devuelve un buffer temporal posicionado al inicio (en RAM hasta 1 MB, en
    disco a partir de ahí), **no** un `bytes`: así el consumo de memoria no
    depende del tamaño de lo que suban.

    Lanza 415 si la extensión o el contenido no cuadran, y 413 si se supera el
    límite — cortando la lectura en ese punto.
    """
    reglas = _REGLAS[kind]
    limite = max_bytes if max_bytes is not None else default_max_bytes()

    _validar_extension(file.filename, reglas["extensiones"])

    buffer = tempfile.SpooledTemporaryFile(max_size=_SPOOL_BYTES)
    escritos = 0
    cabecera = b""

    while True:
        trozo = await file.read(_CHUNK_BYTES)
        if not trozo:
            break

        if not cabecera:
            cabecera = trozo[:_CHUNK_BYTES]

        escritos += len(trozo)
        if escritos > limite:
            # Cortar aquí es el punto del ejercicio: no se sigue leyendo ni se
            # retiene lo ya leído.
            buffer.close()
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=(
                    f"El fichero supera el límite de "
                    f"{limite // (1024 * 1024)} MB."
                ),
            )

        buffer.write(trozo)

    try:
        _validar_contenido(cabecera, kind, reglas["magic"])
    except HTTPException:
        buffer.close()
        raise

    buffer.seek(0)
    return buffer

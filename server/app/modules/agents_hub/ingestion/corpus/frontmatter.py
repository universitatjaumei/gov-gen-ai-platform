"""Front-matter YAML del `.md` curado (ING.0.3). Deploy: edge.

**El hash se calcula sobre el CUERPO, nunca sobre el front-matter.** Es la decisión con
más consecuencias del contrato: reetiquetar una norma —añadir una submateria, corregir
el ámbito— no cambia el `content_hash`, así que no dispara re-troceado ni re-embedding;
cambiar el texto sí. Sin esto, cada revisión del vocabulario costaría reindexar el
corpus completo y la promesa de CLAUDE.md §5 sería falsa.

Corolario que también hay que preservar: un `.md` que **gana** front-matter después
tiene el mismo hash que antes, así que no se reingiere.
"""
from __future__ import annotations

import re

import yaml

from server.app.modules.agents_hub.ingestion.hasher import hash_content

# El front-matter tiene que abrir en la PRIMERA línea del fichero. Un '---' suelto más
# abajo es un separador horizontal, que aparece a menudo en el corpus convertido.
_DELIMITADOR = re.compile(r"^---[ \t]*\r?\n(?P<yaml>.*?)^---[ \t]*(?:\r?\n|$)", re.DOTALL | re.MULTILINE)


class FrontmatterError(Exception):
    """El front-matter existe pero no es YAML válido o no es un mapa."""


def _normalizar_cuerpo(cuerpo: str) -> str:
    """Salto de línea a LF y sin líneas en blanco iniciales.

    Las dos normalizaciones existen para que el hash sea estable:

    - **CRLF → LF**: el corpus se produce en Windows y puede entregarse con LF por el
      sync. El mismo documento con distinto final de línea no debe reingerirse.
    - **Líneas en blanco iniciales**: la línea que separa el front-matter del cuerpo es
      formato del bloque, no contenido, así que un `.md` que gana front-matter conserva
      su hash.
    """
    return cuerpo.replace("\r\n", "\n").replace("\r", "\n").lstrip("\n")


def parse_frontmatter(raw_md: str) -> tuple[dict, str]:
    """Separa el front-matter del cuerpo.

    Devuelve `({}, cuerpo_normalizado)` si el documento no trae front-matter: no es un
    error, el corpus histórico y el del BOE no lo tienen.
    """
    # BOM de Excel/Windows: si sobrevive, el delimitador no casa en la primera línea.
    texto = raw_md.lstrip("﻿")

    if not texto.startswith("---"):
        return {}, _normalizar_cuerpo(texto)

    match = _DELIMITADOR.match(texto)
    if match is None:
        return {}, _normalizar_cuerpo(texto)

    bruto = match.group("yaml")
    try:
        datos = yaml.safe_load(bruto) if bruto.strip() else None
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"Front-matter con YAML invalido: {exc}") from exc

    if datos is None:
        datos = {}
    if not isinstance(datos, dict):
        raise FrontmatterError(
            f"El front-matter debe ser un mapa de clave/valor, no {type(datos).__name__}"
        )

    return datos, _normalizar_cuerpo(texto[match.end():])


def hash_markdown_body(raw_md: str) -> str:
    """SHA-256 del cuerpo, con el front-matter fuera.

    Único punto donde se calcula el hash de un `.md` curado: si alguien llama a
    `hash_content(raw_md)` directamente, el invariante se rompe en silencio.
    """
    _, body = parse_frontmatter(raw_md)
    return hash_content(body)

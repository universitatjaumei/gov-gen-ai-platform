"""Fuentes de corpus curado (ING.0.5). Deploy: edge.

El reconciliador (`reconciler.py`) no sabe de dónde viene el corpus: consume este
protocolo. Hoy hay una implementación —una carpeta local de `.md`, que es el mecanismo
de mantenimiento mientras no exista el pipeline de publicación— y SYNC.1 añadirá la
segunda, contra el servicio MCP de datasets. **Añadir una fuente no debe tocar el
reconciliador.**

`is_census()` es la pieza delicada: declara si la fuente entrega el corpus **completo**.
Solo con un censo se puede detectar una retirada, porque solo entonces «ausente» significa
algo. Una carga parcial que se interpretara como censo retiraría cientos de normas.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from server.app.modules.agents_hub.ingestion.corpus.faq import (
    FaqFormatoInvalido,
    assert_formato_faq,
    debe_validarse_como_faq,
)
from server.app.modules.agents_hub.ingestion.corpus.frontmatter import parse_frontmatter
from server.app.modules.agents_hub.ingestion.corpus.manifest import (
    CorpusDocumentEntry,
    CorpusManifest,
    CorpusValidationError,
    entry_from_frontmatter,
    merge_frontmatter,
)

EXTENSIONES = (".md", ".markdown")


@runtime_checkable
class CorpusSource(Protocol):
    """Origen de un paquete de corpus.

    `runtime_checkable` para que la fuente de SYNC.1 pueda comprobarse con `isinstance`
    en su propio test en lugar de descubrir el desajuste en ejecución.
    """

    def is_census(self) -> bool:
        """True si estas entradas son el corpus COMPLETO."""
        ...

    async def list_entries(self) -> list[CorpusDocumentEntry]: ...

    async def read_body(self, entry: CorpusDocumentEntry) -> str:
        """Markdown sin front-matter, tal como se hashea y se trocea."""
        ...


class LocalDirectorySource:
    """Carpeta de `.md` en disco, con manifiesto opcional.

    El front-matter del fichero **manda** sobre la entrada del manifiesto; el manifiesto
    existe para los corpus que no lo traen (histórico sin convertir, consolidados del BOE).
    """

    def __init__(
        self,
        directory: Path | str,
        manifest: CorpusManifest | None = None,
        is_census_declared: bool = False,
        default_source_url: str = "",
    ) -> None:
        self.directory = Path(directory)
        self.manifest = manifest
        self._is_census = is_census_declared
        self.default_source_url = default_source_url
        if not self.directory.is_dir():
            raise CorpusValidationError(f"No es un directorio: {self.directory}")

    def is_census(self) -> bool:
        return self._is_census

    def _ruta(self, entry: CorpusDocumentEntry) -> Path:
        return self.directory / entry.relative_path.replace("\\", "/")

    def _ficheros(self) -> list[str]:
        rutas = [
            p for p in sorted(self.directory.rglob("*"))
            if p.is_file() and p.suffix.lower() in EXTENSIONES
        ]
        return [p.relative_to(self.directory).as_posix() for p in rutas]

    async def list_entries(self) -> list[CorpusDocumentEntry]:
        """Una entrada por `.md`, con el front-matter aplicado sobre el manifiesto.

        Recorre el **manifiesto** si lo hay —así una carga acotada es explícita— y en su
        defecto todos los `.md` del directorio.
        """
        del_manifiesto = {
            e.relative_path.replace("\\", "/"): e
            for e in (self.manifest.documents if self.manifest else ())
        }
        rutas = list(del_manifiesto) if del_manifiesto else self._ficheros()

        entradas: list[CorpusDocumentEntry] = []
        errores: list[str] = []
        for ruta in rutas:
            fichero = self.directory / ruta
            if not fichero.is_file():
                errores.append(f"  {ruta}: el manifiesto lo declara y no existe")
                continue
            metadata, cuerpo = parse_frontmatter(
                fichero.read_text(encoding="utf-8-sig", errors="replace")
            )

            # FAQ.1: una FAQ mal formateada se ingiere sin protestar y responde peor a
            # partir de entonces. Se comprueba aquí, con el resto del contrato, para que el
            # paquete falle ENTERO y con la lista completa de lo que hay que corregir —el
            # mismo criterio que el resto de este método.
            if debe_validarse_como_faq(metadata):
                try:
                    assert_formato_faq(cuerpo)
                except FaqFormatoInvalido as mal_formada:
                    errores.append(f"  {ruta}: {mal_formada}")
                    continue

            try:
                base = del_manifiesto.get(ruta)
                if base is not None:
                    entradas.append(merge_frontmatter(base, metadata))
                else:
                    entradas.append(
                        entry_from_frontmatter(
                            metadata,
                            relative_path=ruta,
                            source_url=metadata.get("url_oficial")
                            or self.default_source_url
                            or ruta,
                        )
                    )
            except Exception as exc:  # ValidationError y CorpusValidationError
                errores.append(f"  {ruta}: {exc}")

        if errores:
            raise CorpusValidationError(
                "El paquete no cumple el contrato y no se ingiere nada "
                f"({len(errores)} de {len(rutas)} entradas):\n" + "\n".join(errores)
            )
        return entradas

    async def read_body(self, entry: CorpusDocumentEntry) -> str:
        _, body = parse_frontmatter(
            self._ruta(entry).read_text(encoding="utf-8-sig", errors="replace")
        )
        return body

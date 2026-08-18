"""MarkdownTableExtractionPipeline — las tablas de un `.md`, literales (SEG.3).

Los informes de seguimiento de titulaciones y programas de doctorado se preparan como un
documento Markdown con una treintena de tablas, uno por programa, y ya existen. Mañana la misma
información llegará como JSON o como consulta a una API; la abstracción de pipeline lo absorbe sin
tocar el resto.

**Este pipeline reproduce, no interpreta.** No convierte tipos, no calcula, no normaliza y no
rellena huecos: una celda que dice «No hay valor» sale diciendo «No hay valor», porque la
diferencia entre *no hay dato* y *el dato es cero* es información y perderla es el fallo más caro
de un informe. Si hay que calcular algo, lo hace después una operación declarativa, que es
auditable.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from server.app.modules.redaccion.pipelines.contracts import (
    ExtractedTable,
    ExtractionInput,
    ExtractionProvenance,
    ExtractionResult,
    ExtractionWarning,
)

#: `| :---- | ---: |` es sintaxis de Markdown, no una fila de datos. Colarla ensuciaría con una
#: fila de guiones la primera línea de las treinta tablas del informe.
_SEPARADORA = re.compile(r"^[\s|:\-]+$")

#: El código de la tabla va **debajo** de ella en este formato: «Tabla 1.4.2 Satisfacción…».
#: Es lo que permite que una plantilla diga «valora la Tabla 1.2» y que el informe final las
#: reproduzca con su numeración original.
_PIE_DE_TABLA = re.compile(r"^\s*(Tabla|Taula|Table)\s+[\d.]+", re.IGNORECASE)


def _celdas(linea: str) -> list[str]:
    """Parte una fila de Markdown por `|`, sin comerse el contenido de las celdas.

    Se quitan el primer y el último delimitador —una fila bien formada empieza y acaba en `|`— y
    lo de dentro se conserva tal cual, sólo con los espacios de los bordes recortados.
    """
    cuerpo = linea.strip()
    if cuerpo.startswith("|"):
        cuerpo = cuerpo[1:]
    if cuerpo.endswith("|"):
        cuerpo = cuerpo[:-1]
    return [c.strip() for c in cuerpo.split("|")]


class MarkdownTableExtractionPipeline:
    """Extrae las tablas de un documento Markdown conservando cabeceras, filas y huecos."""

    pipeline_id = "md_table_pipeline_v1"

    def supports(self, source_kind: str) -> bool:
        return source_kind == "md_table"

    def extract(self, inp: ExtractionInput) -> ExtractionResult:
        if inp.file_ref is None:
            raise ValueError(
                "MarkdownTableExtractionPipeline requiere file_ref en ExtractionInput."
            )

        ruta = self._ruta_de(inp)
        texto = ruta.read_text(encoding="utf-8")
        tablas = self._tablas_de(texto)

        warnings: list[ExtractionWarning] = []
        if not tablas:
            # Cero tablas no es un resultado neutro: casi siempre significa que el fichero no es
            # el que se creía, o que el formato cambió. Callarlo produce un informe vacío sin
            # explicación.
            warnings.append(ExtractionWarning(
                code="NO_TABLES_FOUND",
                message=f"No se ha encontrado ninguna tabla Markdown en «{ruta.name}».",
                severity="warning",
            ))

        return ExtractionResult(
            tables=tablas,
            metrics=[],
            free_text=texto if inp.options.get("include_free_text") else None,
            warnings=warnings,
            provenance=ExtractionProvenance(
                pipeline_id=self.pipeline_id,
                source_ref=str(inp.file_ref),
                extracted_at=datetime.now(timezone.utc),
            ),
        )

    @staticmethod
    def _ruta_de(inp: ExtractionInput) -> Path:
        """Convención de VER.4: `bucket` vacío y ruta completa en `key` = ya está en disco."""
        assert inp.file_ref is not None
        if not inp.file_ref.bucket:
            return Path(inp.file_ref.key)
        return Path(inp.file_ref.bucket) / inp.file_ref.key

    def _tablas_de(self, texto: str) -> list[ExtractedTable]:
        """Recorre el documento agrupando bloques de líneas que empiezan por `|`."""
        tablas: list[ExtractedTable] = []
        lineas = texto.splitlines()
        bloque: list[str] = []

        for indice, linea in enumerate(lineas):
            if linea.strip().startswith("|"):
                bloque.append(linea)
                continue
            if bloque:
                tabla = self._tabla_de_bloque(bloque, lineas, indice)
                if tabla is not None:
                    tablas.append(tabla)
                bloque = []

        if bloque:
            tabla = self._tabla_de_bloque(bloque, lineas, len(lineas))
            if tabla is not None:
                tablas.append(tabla)

        return tablas

    def _tabla_de_bloque(
        self, bloque: list[str], lineas: list[str], indice_tras_el_bloque: int
    ) -> ExtractedTable | None:
        filas = [_celdas(linea) for linea in bloque if not _SEPARADORA.match(linea)]
        if len(filas) < 2:
            # Una sola fila no es una tabla: es una línea que empieza por `|` por casualidad.
            return None

        cabeceras, *datos = filas
        return ExtractedTable(
            name=self._nombre_de(lineas, indice_tras_el_bloque, len(tuple(datos))),
            headers=cabeceras,
            rows=datos,
        )

    @staticmethod
    def _nombre_de(lineas: list[str], indice: int, num_filas: int) -> str:
        """El pie de tabla si está justo debajo; si no, algo que al menos identifique.

        Se miran las tres líneas siguientes porque entre la tabla y su pie suele haber una vacía.
        """
        for salto in range(0, 3):
            posicion = indice + salto
            if posicion >= len(lineas):
                break
            candidata = lineas[posicion].strip()
            if _PIE_DE_TABLA.match(candidata):
                return candidata
        return f"Tabla sin código ({num_filas} filas)"

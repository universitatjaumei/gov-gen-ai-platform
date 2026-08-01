"""Chunker para documentos Markdown (ING.0.4).

Consume el formato de `docs/CONTRATO_MD_CORPUS.md`:

    #      documento (uno por fichero)
    ##     preámbulo | título | grupo de disposiciones | anexo
    ###    capítulo
    ####   sección
    #####  UNIDAD CITABLE: artículo | disposición concreta   → ancla obligatoria

**El nivel lo determina el TIPO de elemento, no su anidamiento**, así que el chunker puede
fiarse de él. De ahí que haya saltos de nivel legítimos —`#####` justo bajo `##` en las
disposiciones— que no son errores y que el splitter trata bien: registra los encabezados
que ve y descarta los niveles intermedios que quedaron atrás.

Dos cosas que este módulo garantiza y de las que depende el resto:

- **La taxonomía nunca entra en el texto** (CLAUDE.md §5). Solo contexto estructural.
- **Las tablas no se parten dejando fragmentos sin cabecera.** Medido sobre el corpus
  convertido: 30 de los 54 bloques `TABLA-TEXT` superan `chunk_size`, y sin tratamiento
  especial todo fragmento menos el primero queda con importes sin nombre de columna. Eso
  es peor que no tener el dato, porque se recupera igual y sostiene una respuesta segura
  y falsa sobre una cuantía.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

# Ancla de atributos Pandoc/kramdown al final del encabezado: '{#art-14}'.
# Bloque de atributos Pandoc/kramdown al final del encabezado. Admite clases junto al
# ancla —`{#art-14 .modificat}`— porque el estado de consolidación del elemento viaja ahí:
# es el mismo token que el ancla, así que sobrevive al troceado y queda pegado al artículo.
# Sin este soporte, un `{#art-14 .modificat}` perdía el ancla EN SILENCIO.
_ANCORA = re.compile(
    r"\s*\{#(?P<ancora>[A-Za-z0-9][A-Za-z0-9._-]*)(?P<atributos>[^}]*)\}\s*$"
)
_CLASE = re.compile(r"\.([A-Za-z][A-Za-z0-9_-]*)")
# Estados de consolidación conocidos. Se nombran para que un filtro pueda usarlos; el
# resto de clases se conserva en `classes` sin interpretarlas.
ESTADOS_CONSOLIDACION = ("suprimit", "modificat", "afegit")
# Ancla vacía o mal formada: se limpia del texto pero no produce ancla.
_ANCORA_ROTA = re.compile(r"\s*\{#[^}]*\}")

_BLOQUE_TABLA = re.compile(
    r"<!--\s*TABLA-TEXT:(?P<cabecera>[^>]*?)-->\s*\n"
    r"(?P<cuerpo>.*?)"
    r"\n?\s*<!--\s*/TABLA-TEXT\s*-->",
    re.DOTALL,
)
_MARCADOR_IMAGEN = re.compile(r"^\s*<!--\s*TABLE-IMG:.*?-->\s*$", re.MULTILINE)
_FORMATOS_TABLA = ("markdown", "html")

_NIVELES = 5


@dataclass
class Chunk:
    """Representa un chunk de documento.

    `embedding_text` (RAG.7) es lo que se embebe; `content` es lo que se almacena y se
    muestra como evidencia. **Son distintos a propósito**: un fragmento que dice «L'import
    es de 53,34 euros» no dice de qué importe habla ni de qué norma sale, y embebido asi
    compite contra cualquier otro importe del corpus. Con su jerarquia delante queda anclado
    a su contexto sin cambiar ni una letra de lo que lee el usuario.

    No se persiste: se calcula al trocear y se consume en la ingesta.
    """

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding_text: str = ""

    def __post_init__(self) -> None:
        if not self.embedding_text:
            self.embedding_text = self.content


@runtime_checkable
class ContextEnricher(Protocol):
    """Nivel 2 de contextual retrieval: una frase de contexto generada en la ingesta.

    Se define el protocolo y se deja `NoopEnricher` por defecto. La implementacion con LLM
    —que redacta «este fragmento trata de X» leyendo el documento entero— queda como
    candidata para cuando el corpus definitivo este cargado: cuesta una llamada por chunk en
    la ingesta y no tiene sentido pagarla contra un corpus que aun va a cambiar.
    """

    def enrich(self, document: str, chunk: str) -> str: ...


class NoopEnricher:
    """No enriquece. El default, y el unico que existe hoy."""

    def enrich(self, document: str, chunk: str) -> str:
        return ""


def strip_anchor_tokens(texto: str) -> str:
    """Quita los tokens `{#...}` del texto visible.

    Se usa también al inyectar documentos completos (long context): el token es ruido
    tanto para el modelo como para quien lee la respuesta.
    """
    return _ANCORA_ROTA.sub("", texto)


def _extraer_ancora(encabezado: str) -> tuple[str, str | None, list[str]]:
    """Devuelve (encabezado_limpio, ancora, clases)."""
    match = _ANCORA.search(encabezado)
    if match:
        clases = _CLASE.findall(match.group("atributos") or "")
        return encabezado[: match.start()].rstrip(), match.group("ancora"), clases
    return _ANCORA_ROTA.sub("", encabezado).rstrip(), None, []


class MarkdownChunker:
    """Divide documentos Markdown en chunks semánticos.

    `table_chunk_size` es el presupuesto de atomicidad de una tabla: un bloque que quepa
    en él NO se parte, aunque supere `chunk_size`. El default de 4.000 caracteres deja
    enteros 51 de los 54 bloques del corpus medido.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        table_chunk_size: int = 4000,
        enricher: ContextEnricher | None = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.table_chunk_size = table_chunk_size
        self.enricher = enricher or NoopEnricher()

        self.headers_to_split = [("#" * n, f"header_{n}") for n in range(1, _NIVELES + 1)]

        self.md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split,
            strip_headers=False,
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    # ───────────────────────── Encabezados ─────────────────────────

    def _limpiar_encabezados(
        self, doc_metadata: dict
    ) -> tuple[dict, list[str], str | None, list[str]]:
        """Separa los encabezados en ruta de ancestros + ancla y clases de la unidad."""
        limpios: dict[str, str] = {}
        ancora: str | None = None
        clases: list[str] = []
        presentes: list[str] = []

        for nivel in range(1, _NIVELES + 1):
            clave = f"header_{nivel}"
            if clave not in doc_metadata:
                continue
            texto, ancora_nivel, clases_nivel = _extraer_ancora(str(doc_metadata[clave]))
            limpios[clave] = texto
            presentes.append(clave)
            if ancora_nivel:
                # El ancla del nivel más profundo es la que cita el fragmento, y sus
                # clases son el estado de consolidación de ese elemento.
                ancora = ancora_nivel
                clases = clases_nivel

        # La ruta son los ancestros: todo menos el encabezado más profundo.
        ruta = [limpios[c] for c in presentes[:-1]] if len(presentes) > 1 else []
        return limpios, ruta, ancora, clases

    # ───────────────────────── Tablas ─────────────────────────

    @staticmethod
    def _metadatos_tabla(cabecera: str) -> dict[str, Any]:
        """Lee la procedencia del marcador: origen, página, dimensiones y formato."""
        campos = [c.strip() for c in cabecera.split("|")]
        datos: dict[str, Any] = {
            "es_taula": True,
            "taula_origen": campos[0] if campos else None,
            "pagina": None,
            "dimensions": None,
            # Sin formato declarado se asume markdown, que es el del contrato.
            "taula_format": "markdown",
        }
        for campo in campos[1:]:
            bajo = campo.lower()
            if bajo in _FORMATOS_TABLA:
                datos["taula_format"] = bajo
            elif re.fullmatch(r"\d+x\d+", bajo):
                datos["dimensions"] = campo
            elif datos["pagina"] is None and re.search(r"\d", campo):
                datos["pagina"] = campo
        return datos

    @staticmethod
    def _es_separador(linea: str) -> bool:
        limpia = linea.replace("|", "").replace(" ", "")
        return bool(limpia) and set(limpia) <= {"-", ":"}

    def _partir_tabla_pipe(self, cuerpo: str) -> list[str]:
        """Parte por filas repitiendo el prefijo (leyenda + cabecera) en cada fragmento.

        La fila de cabecera es la que **precede al separador** `| --- |`, no la primera
        línea del bloque: el corpus curado mete la leyenda de la tabla dentro del bloque
        («**Retribucions del professorat…**»), y tomarla por cabecera dejaría la cabecera
        real convertida en una fila de datos.
        """
        lineas = [ln for ln in cuerpo.splitlines() if ln.strip()]
        if not lineas:
            return []

        separador = next(
            (i for i, ln in enumerate(lineas) if self._es_separador(ln)), None
        )
        if separador is not None:
            # Todo hasta el separador (leyenda + cabecera) se repite en cada fragmento.
            cabecera = lineas[: separador + 1]
            resto = lineas[separador + 1 :]
        else:
            cabecera = lineas[:1]
            resto = lineas[1:]

        prefijo = "\n".join(cabecera)
        fragmentos: list[str] = []
        actual: list[str] = []
        for fila in resto:
            candidato = "\n".join([prefijo, *actual, fila])
            if actual and len(candidato) > self.table_chunk_size:
                fragmentos.append("\n".join([prefijo, *actual]))
                actual = [fila]
            else:
                actual.append(fila)
        if actual:
            fragmentos.append("\n".join([prefijo, *actual]))
        return fragmentos or [prefijo]

    def _partir_tabla_html(self, cuerpo: str) -> list[str]:
        """Parte por `<tr>` del cuerpo, repitiendo apertura y `<thead>`."""
        apertura = re.search(r"<table[^>]*>", cuerpo)
        thead = re.search(r"<thead>.*?</thead>", cuerpo, re.DOTALL)
        filas = re.findall(r"<tr>(?!.*?</thead>).*?</tr>", cuerpo, re.DOTALL)
        if thead:
            filas = [f for f in filas if f not in thead.group(0)]
        if not filas:
            return [cuerpo]

        prefijo = (apertura.group(0) if apertura else "<table>") + (
            "\n" + thead.group(0) if thead else ""
        )
        fragmentos: list[str] = []
        actual: list[str] = []
        for fila in filas:
            candidato = f"{prefijo}\n<tbody>\n" + "\n".join([*actual, fila]) + "\n</tbody>\n</table>"
            if actual and len(candidato) > self.table_chunk_size:
                fragmentos.append(
                    f"{prefijo}\n<tbody>\n" + "\n".join(actual) + "\n</tbody>\n</table>"
                )
                actual = [fila]
            else:
                actual.append(fila)
        if actual:
            fragmentos.append(
                f"{prefijo}\n<tbody>\n" + "\n".join(actual) + "\n</tbody>\n</table>"
            )
        return fragmentos

    def _trocear_tabla(self, cabecera: str, cuerpo: str) -> list[tuple[str, dict]]:
        metadatos = self._metadatos_tabla(cabecera)
        cuerpo = cuerpo.strip()

        if len(cuerpo) <= self.table_chunk_size:
            return [(cuerpo, metadatos)]

        partes = (
            self._partir_tabla_html(cuerpo)
            if metadatos["taula_format"] == "html"
            else self._partir_tabla_pipe(cuerpo)
        )
        total = len(partes)
        return [
            (parte, {**metadatos, "taula_part": i + 1, "taula_parts": total})
            for i, parte in enumerate(partes)
        ]

    # ───────────────────────── Troceado de una sección ─────────────────────────

    def _trocear_seccion(self, contenido: str) -> list[tuple[str, dict]]:
        """Devuelve [(texto, metadatos_extra)] separando prosa y bloques de tabla."""
        piezas: list[tuple[str, dict]] = []
        posicion = 0

        for match in _BLOQUE_TABLA.finditer(contenido):
            prosa = contenido[posicion : match.start()]
            piezas.extend((t, {}) for t in self._trocear_prosa(prosa))
            piezas.extend(self._trocear_tabla(match.group("cabecera"), match.group("cuerpo")))
            posicion = match.end()

        piezas.extend((t, {}) for t in self._trocear_prosa(contenido[posicion:]))
        return piezas

    def _trocear_prosa(self, texto: str) -> list[str]:
        # El marcador de imagen no aporta nada al índice y ensucia el fragmento.
        limpio = _MARCADOR_IMAGEN.sub("", texto).strip()
        if not limpio:
            return []
        if len(limpio) <= self.chunk_size:
            return [limpio]
        return self.text_splitter.split_text(limpio)

    # ───────────────────────── API ─────────────────────────

    @staticmethod
    def _texto_embebible(
        titulo: str | None, encabezados: dict[str, str], contenido: str, prefacio: str
    ) -> str:
        """Jerarquía estructural + contenido (RAG.7).

        Solo entra el título del documento y sus encabezados. **Nunca taxonomía ni ancla**:
        la taxonomía porque el vocabulario está pendiente de validar y debe seguir siendo
        revisable —embebida, cada revisión costaría re-embeber el corpus (CLAUDE.md §5)—; el
        ancla porque es ruido para el vector y su sitio es la URL de la cita.

        El encabezado más profundo no se repite si el contenido ya empieza por él: duplicar
        la misma frase sesga el vector hacia ella.
        """
        # El contenido conserva sus encabezados (`strip_headers=False` desde ING.0.4), así
        # que el PRIMER fragmento de una sección ya los lleva dentro y prefijarlos otra vez
        # solo sesgaría el vector hacia ellos. Los que ganan contexto son los fragmentos
        # SIGUIENTES de una sección larga, que se quedaron sin encabezado al trocear.
        ya_presentes = set()
        for linea in contenido.lstrip().splitlines():
            if not linea.lstrip().startswith("#"):
                break
            ya_presentes.add(linea.lstrip("#").strip())

        niveles: list[str] = []
        for nivel in ([titulo] if titulo else []) + [
            encabezados[c] for c in sorted(encabezados) if encabezados[c]
        ]:
            if nivel and nivel not in ya_presentes and nivel not in niveles:
                niveles.append(nivel)

        partes = [p for p in (prefacio.strip(), " > ".join(niveles)) if p]
        return f"{chr(10).join(partes)}\n\n{contenido}" if partes else contenido

    def split(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        document_title: str | None = None,
    ) -> list[Chunk]:
        """Divide el contenido en chunks.

        Args:
            content: Contenido Markdown
            metadata: Metadatos adicionales (document_id, source_url…). **No se copia
                al texto**: si trajera taxonomía, entraría en el embedding.
            document_title: título del documento, que encabeza el `embedding_text`. Va como
                parámetro y no dentro de `metadata` justamente para que quede claro que no
                es un metadato del chunk: es contexto de embedding y no se persiste.

        Returns:
            Lista de chunks
        """
        base_metadata = metadata or {}

        chunks: list[Chunk] = []
        for doc in self.md_splitter.split_text(content):
            encabezados, ruta, ancora, clases = self._limpiar_encabezados(doc.metadata)
            estado = next((c for c in clases if c in ESTADOS_CONSOLIDACION), None)
            comun = {
                **base_metadata,
                **encabezados,
                "ruta": ruta,
                "ancora": ancora,
                # Estado de consolidación del elemento, del bloque de atributos del
                # encabezado. Pegado al artículo y sobreviviendo al troceado, es lo que
                # evita citar un artículo suprimido como si estuviera en vigor.
                "estat": estado,
                "classes": clases,
            }

            piezas = self._trocear_seccion(strip_anchor_tokens(doc.page_content))
            for indice, (texto, extra) in enumerate(piezas):
                chunks.append(
                    Chunk(
                        content=texto,
                        metadata={**comun, **extra, "chunk_index": indice},
                        embedding_text=self._texto_embebible(
                            document_title,
                            encabezados,
                            texto,
                            self.enricher.enrich(content, texto),
                        ),
                    )
                )

        return chunks

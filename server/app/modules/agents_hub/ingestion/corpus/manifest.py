"""Contrato del paquete de corpus curado (ING.0.3). Deploy: edge.

**El portador de los metadatos es el front-matter del `.md`**; el manifiesto se deriva de
él y existe para los corpus que no lo traen (histórico sin convertir, consolidados del
BOE). Cuando los dos hablan del mismo campo, manda el front-matter: el fichero es la
fuente que viaja con el contenido, y es lo que hace posibles la carga por CLI y el sync
con el mismo contrato.

Las claves del front-matter que este contrato no enumera **no son un error**: van a
`extra`, y de ahí a `HubDocument.doc_metadata`. Es lo que permite que los 56 campos del
esquema (`vocabulari/esquema_metadades.yaml`) fluyan sin que el contrato los liste.

---

## Mapeo desde el catálogo existente

**Desviación documentada respecto al prompt.** El prompt decía que
`Descarregar_pdf/normativa_uji_log.json` «se puede transformar a este formato»; no es
cierto: ese fichero es un **log de ejecución** del conversor (recuentos de ok/skipped/
errores y rutas de los PDF que fallaron), sin un solo metadato por documento. El
catálogo real por documento es `normativa_propia/cataleg_metadades_amb_resum.csv`, con
columnas `id;fitxer;titol;tipus;materia;categoria_actual;idioma;organ_emissor;
data_aprovacio;estat_vigencia;n_caracters;resum_abstractiu;resum_extractiu_suport`.

| Columna del catálogo | Campo de la entrada |
|---|---|
| `id` | `id_publicacio` |
| `fitxer` | `relative_path` |
| `titol` | `title` |
| `idioma` | `language` |
| `estat_vigencia` | `estat_vigencia` (tal cual, incluido `vigent?`) |
| `tipus`, `organ_emissor`, `data_aprovacio`, `resum_abstractiu` | `extra` |
| `n_caracters` | se descarta (derivado) |
| `materia`, `categoria_actual` | **`extra`, NUNCA `ambit_principal`/`submateries`** |

La última fila es la importante. El eje `materia` actual mezcla cuatro ejes distintos
—colectivo, función, unidad orgánica e instrumento— y por eso «Gestió econòmica» tiene 3
documentos de 314 cuando la vicegerencia seleccionó 121 (§1.2 del informe de materias).
Mapearlo automáticamente a `ambit_principal` importaría esa incoherencia al corpus
indexado. Se conserva en `extra` como `materia_antiga` para trazabilidad, y la
clasificación nueva entra etiquetada aparte.
"""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from pathlib import PurePosixPath, PureWindowsPath
from pathlib import Path
from typing import Any, Literal, Protocol

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EXTENSIONES_MARKDOWN = (".md", ".markdown")


class CorpusValidationError(Exception):
    """El paquete de corpus no cumple el contrato."""


class VocabularyValidator(Protocol):
    """Lo único que este módulo necesita de VocabularyService."""

    async def validate(self, axis: str, codis: list[str]) -> list[str]: ...


class CorpusDocumentEntry(BaseModel):
    """Un documento del paquete de corpus."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    relative_path: str
    source_url: str
    language: str
    id_publicacio: str | None = None
    # --- Transporte, no metadato del documento (SYNC.1) ---
    # Hash del cuerpo tal como lo declara la fuente, cuando puede declararlo sin entregarlo.
    # El servicio de publicación lo trae en el índice, y con él una pasada sin cambios no
    # descarga ni un byte de contenido. La carpeta local lo deja en None: tiene el fichero
    # delante, así que declararlo no le ahorraría nada.
    # NO se persiste como columna ni entra en `doc_metadata`: describe el viaje, no la norma.
    content_hash: str | None = None
    content_class: Literal["regulation", "faq", "generic"] = "generic"
    title: str | None = None
    original_pdf_sha256: str | None = None
    converter: str | None = None
    revisat_per: str | None = None
    revisat_el: datetime | None = None
    # --- Clasificación. Los códigos se validan contra el vocabulario aparte, porque
    # exige consultar la BD y Pydantic no valida de forma asíncrona.
    ambit_principal: str | None = None
    ambits_secundaris: tuple[str, ...] = ()
    submateries: tuple[str, ...] = ()
    submateries_internes: tuple[str, ...] = ()
    # --- Acceso y uso
    nivell_acces: Literal["public", "intern", "restringit"] = "public"
    us_assistents: Literal["si", "restringit", "no"] = "si"
    motiu_exclusio: str | None = None
    # --- Versión idiomática. Es la REFERENCIA de la canónica (id_publicacio o ruta), no
    # un UUID: al escribir el .md no se conoce el id que tendrá en la BD. Lo resuelve
    # el cargador (ING.0.5).
    canonica: bool = True
    versio_idiomatica_de: str | None = None
    # --- Vigencia
    estat_vigencia: str | None = None
    vigencia_validada_per: str | None = None
    vigencia_validada_el: datetime | None = None
    data_revisio_prevista: date | None = None
    # --- El resto del esquema de 56 campos
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("relative_path")
    @classmethod
    def _ruta_relativa_de_markdown(cls, valor: str) -> str:
        if not valor or not valor.strip():
            raise ValueError("relative_path vacio")
        normalizada = valor.replace("\\", "/")

        if PurePosixPath(normalizada).is_absolute() or PureWindowsPath(valor).is_absolute():
            raise ValueError(f"relative_path debe ser relativa: {valor!r}")
        if normalizada.startswith("//"):
            raise ValueError(f"relative_path no puede ser una ruta de red: {valor!r}")
        if ".." in PurePosixPath(normalizada).parts:
            raise ValueError(f"relative_path no puede salir del paquete: {valor!r}")
        if not normalizada.lower().endswith(EXTENSIONES_MARKDOWN):
            raise ValueError(
                f"relative_path debe apuntar a un {' o '.join(EXTENSIONES_MARKDOWN)}: {valor!r}"
            )
        return valor

    @model_validator(mode="after")
    def _reglas_cruzadas(self) -> "CorpusDocumentEntry":
        if self.content_class == "regulation" and not (self.revisat_per and self.revisat_el):
            raise ValueError(
                f"{self.relative_path}: content_class 'regulation' exige revisat_per y "
                "revisat_el (la revisión humana es obligatoria para normativa)"
            )
        if self.us_assistents == "no" and not self.motiu_exclusio:
            raise ValueError(
                f"{self.relative_path}: us_assistents 'no' exige motiu_exclusio, para que "
                "quedar fuera del índice sea una decisión auditable y no un silencio"
            )
        return self


class CorpusManifest(BaseModel):
    """Paquete de corpus: destino + documentos."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    chatbot_id: uuid.UUID
    organizacion_id: uuid.UUID | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    documents: tuple[CorpusDocumentEntry, ...] = ()

    @model_validator(mode="after")
    def _sin_rutas_repetidas(self) -> "CorpusManifest":
        vistas: set[str] = set()
        repetidas: set[str] = set()
        for documento in self.documents:
            clave = documento.relative_path.replace("\\", "/").lower()
            if clave in vistas:
                repetidas.add(documento.relative_path)
            vistas.add(clave)
        if repetidas:
            raise ValueError(f"rutas repetidas en el manifiesto: {sorted(repetidas)}")
        return self

    @model_validator(mode="after")
    def _una_sola_canonica_por_norma(self) -> "CorpusManifest":
        """VIS.3: dos versiones canónicas de la misma norma es un error, no una elección.

        Medido en el informe: 233 fichas en valenciano y 81 en castellano, muchas la misma
        norma. Si el paquete declara canónicas las dos, elegir por orden de aparición
        indexaría el mismo contenido dos veces —ocupando dos plazas del top-k— sin que nadie
        lo hubiera decidido. Falla aquí, antes de tocar la BD, y nombra las dos rutas para
        que se sepa cuál hay que corregir.
        """
        por_url: dict[str, list[str]] = {}
        for documento in self.documents:
            if not documento.canonica:
                continue
            clave = (documento.source_url or "").strip().lower()
            if not clave:
                continue
            por_url.setdefault(clave, []).append(documento.relative_path)

        conflictos = {url: rutas for url, rutas in por_url.items() if len(rutas) > 1}
        if conflictos:
            detalle = "; ".join(
                f"{url} → {sorted(rutas)}" for url, rutas in sorted(conflictos.items())
            )
            raise ValueError(
                "dos o mas versiones declaradas canonicas para la misma norma: "
                f"{detalle}. Declara canonica solo una y enlaza la otra con "
                "versio_idiomatica_de"
            )
        return self


# ───────────────────────── Front-matter → entrada ─────────────────────────

_CAMPOS = set(CorpusDocumentEntry.model_fields) - {"extra"}


def entry_from_frontmatter(
    frontmatter: dict, *, relative_path: str, source_url: str
) -> CorpusDocumentEntry:
    """Construye una entrada desde el front-matter de un `.md`.

    Las claves que el contrato no declara van a `extra` en lugar de romper la carga: es
    lo que permite que el esquema de 56 campos crezca sin tocar este módulo.
    """
    conocidas = {k: v for k, v in frontmatter.items() if k in _CAMPOS}
    desconocidas = {k: v for k, v in frontmatter.items() if k not in _CAMPOS}

    conocidas.setdefault("relative_path", relative_path)
    conocidas.setdefault("source_url", source_url)
    if desconocidas:
        conocidas["extra"] = {**conocidas.get("extra", {}), **desconocidas}

    return CorpusDocumentEntry(**conocidas)


def merge_frontmatter(
    entry: CorpusDocumentEntry, frontmatter: dict
) -> CorpusDocumentEntry:
    """Aplica el front-matter sobre una entrada del manifiesto. **Manda el front-matter.**

    Solo pisa los campos que el front-matter menciona; el resto se conserva.
    """
    if not frontmatter:
        return entry

    valores = entry.model_dump()
    for clave, valor in frontmatter.items():
        if clave in _CAMPOS:
            valores[clave] = valor
        else:
            valores["extra"] = {**valores.get("extra", {}), clave: valor}
    return CorpusDocumentEntry(**valores)


# ───────────────────────── Carga del manifiesto ─────────────────────────


def load_manifest(path: Path | str) -> CorpusManifest:
    """Lee un manifiesto en JSON o YAML."""
    path = Path(path)
    texto = path.read_text(encoding="utf-8-sig")
    try:
        datos = (
            json.loads(texto)
            if path.suffix.lower() == ".json"
            else yaml.safe_load(texto)
        )
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise CorpusValidationError(f"{path.name}: no se puede leer: {exc}") from exc

    if not isinstance(datos, dict):
        raise CorpusValidationError(f"{path.name}: el manifiesto debe ser un mapa")
    return CorpusManifest(**datos)


# ───────────────────────── Validación contra el vocabulario ─────────────────────────

# Eje del vocabulario → campos de la entrada que lo usan.
_CAMPOS_POR_EJE: dict[str, tuple[str, ...]] = {
    "ambit": ("ambit_principal", "ambits_secundaris"),
    "submateria": ("submateries", "submateries_internes"),
}


def _codigos(entry: CorpusDocumentEntry, campo: str) -> tuple[str, ...]:
    valor = getattr(entry, campo)
    if valor is None:
        return ()
    return (valor,) if isinstance(valor, str) else tuple(valor)


async def assert_vocabulary(
    entries: list[CorpusDocumentEntry] | tuple[CorpusDocumentEntry, ...],
    vocabulary: VocabularyValidator,
) -> None:
    """Valida los códigos de clasificación de TODAS las entradas de una vez.

    Reporta todos los códigos desconocidos con el fichero en que aparecen, no el primero
    que falla: quien prepara un paquete de 380 normas necesita la lista completa para
    corregirla en una pasada.
    """
    por_eje: dict[str, set[str]] = {}
    origen: dict[tuple[str, str], set[str]] = {}

    for entry in entries:
        for eje, campos in _CAMPOS_POR_EJE.items():
            for campo in campos:
                for codigo in _codigos(entry, campo):
                    por_eje.setdefault(eje, set()).add(codigo)
                    origen.setdefault((eje, codigo), set()).add(entry.relative_path)

    problemas: list[str] = []
    for eje, codigos in por_eje.items():
        if not codigos:
            continue
        desconocidos = await vocabulary.validate(eje, sorted(codigos))
        for codigo in desconocidos:
            ficheros = sorted(origen[(eje, codigo)])
            mostrados = ", ".join(ficheros[:3])
            if len(ficheros) > 3:
                mostrados += f" (+{len(ficheros) - 3} mas)"
            problemas.append(f"  [{eje}] '{codigo}' en: {mostrados}")

    if problemas:
        raise CorpusValidationError(
            "Codigos de clasificacion no reconocidos o no vigentes en el vocabulario:\n"
            + "\n".join(sorted(problemas))
            + "\n\nO se corrigen en el front-matter, o se dan de alta en el vocabulario "
            "(SG los valida) con `python -m ...vocabulary.load`."
        )

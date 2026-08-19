"""Que «Completo» signifique algo: el detector semántico corre de verdad (CUR.7).

El sitio de la Escuela de Doctorado está guardado con `audit_semantic_scope='full'` y **no cambia
nada**. El detector semántico —duplicados y contradicciones por significado— existe desde 9Q.4, tiene
sus tests y **no lo ejecuta nadie**: el job del arranque recibe `detectors=[determinista]`. Es el
mismo patrón que el watcher de RAS.5 y que el bloque `TABLE` de SEG.5, la tercera vez en este
proyecto: la capacidad construida detrás de una puerta que nadie abrió.

Dos cosas que salieron al cablearlo y que ningún test cubría:

* **El job no persiste los hallazgos.** Los cuenta, marca supersesiones y calcula `quality_score`,
  pero guardarlos lo hace cada detector con su repositorio. El determinista lo tiene; el semántico
  dice en su docstring que «no persiste, eso es del job», y el job no lo hace. Sin esto, el detector
  correría, llamaría al LLM y sus hallazgos **se perderían al cerrar la sesión**.
* **El flag `run_semantic` nunca se aplicaba**, porque el job lo mira con
  `getattr(detector, "_is_semantic", False)` y ningún detector declaraba el atributo.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest

from server.app.modules.curation.contracts import ContentFinding
from server.app.modules.curation.site_crawler_dispatcher import (
    SemanticDetectorDispatcher,
    detectores_de_calidad,
)


class _SesionFalsa:
    def __init__(self, sitio: Any) -> None:
        self._sitio = sitio
        self.commits = 0

    async def get(self, modelo: Any, ident: Any) -> Any:
        return self._sitio

    async def commit(self) -> None:
        self.commits += 1

    async def __aenter__(self) -> "_SesionFalsa":
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None


class _Sitio:
    def __init__(self, **config: Any) -> None:
        self.id = uuid.uuid4()
        self.audit_semantic_scope = config.pop("audit_semantic_scope", "full")
        self.config_json = config


class _RepoFalso:
    def __init__(self) -> None:
        self.guardados: list[ContentFinding] = []

    async def upsert(self, hallazgo: ContentFinding) -> Any:
        self.guardados.append(hallazgo)
        return hallazgo


class _DetectorFalso:
    """Doble del detector semántico: registra con qué se construyó."""

    ultimo: dict = {}

    def __init__(self, session: Any, llm: Any, embedding: Any, **opciones: Any) -> None:
        _DetectorFalso.ultimo = {
            "session": session, "llm": llm, "embedding": embedding, **opciones
        }
        self.hallazgos: list[ContentFinding] = []

    async def analyze(self, site_id: uuid.UUID) -> list[ContentFinding]:
        return self.hallazgos


def _hallazgo(site_id: uuid.UUID) -> ContentFinding:
    return ContentFinding(
        id=uuid.uuid4(),
        site_id=site_id,
        finding_type="duplicate",
        severity="warning",
        confidence=0.9,
        page_id=uuid.uuid4(),
        related_page_id=uuid.uuid4(),
        source_url="https://www.uji.es/a/",
        signal={"similarity": 0.95},
        detected_at=datetime(2026, 8, 19, tzinfo=timezone.utc),
    )


def _despachador(sitio: _Sitio, repo: _RepoFalso, hallazgos: list | None = None) -> Any:
    sesion = _SesionFalsa(sitio)

    def fabrica_de_sesiones() -> Any:
        return sesion

    def detector_falso(*args: Any, **kw: Any) -> Any:
        d = _DetectorFalso(*args, **kw)
        d.hallazgos = hallazgos or []
        return d

    return SemanticDetectorDispatcher(
        fabrica_de_sesiones,
        llm_factory=lambda _s: _Llamable("modelo-de-prueba"),
        embedding_factory=lambda _s, _sitio: "embeddings-de-prueba",
        finding_repo_factory=lambda _s: repo,
        detector_factory=detector_falso,
    )


class _Llamable:
    def __init__(self, nombre: str) -> None:
        self.model_name = nombre

    async def generate(self, prompt: str, context: str) -> str:
        return "{}"


# ───────────────────────── El cableado ─────────────────────────


def test_el_detector_semantico_se_declara_como_tal():
    """El job mira `_is_semantic` para respetar el flag; sin el atributo, el flag no existía."""
    assert SemanticDetectorDispatcher._is_semantic is True


@pytest.mark.asyncio
async def test_analiza_el_sitio_con_sesion_propia_y_sus_dependencias():
    sitio = _Sitio()
    repo = _RepoFalso()
    despachador = _despachador(sitio, repo)

    await despachador.analyze(sitio.id)

    assert _DetectorFalso.ultimo["embedding"] == "embeddings-de-prueba"
    assert _DetectorFalso.ultimo["llm"].model_name == "modelo-de-prueba"


@pytest.mark.asyncio
async def test_los_hallazgos_se_guardan_o_se_pierden_al_cerrar_la_sesion():
    """El detector no persiste y el job tampoco: si no los guarda el despachador, no los guarda nadie."""
    sitio = _Sitio()
    repo = _RepoFalso()
    hallazgo = _hallazgo(sitio.id)
    despachador = _despachador(sitio, repo, hallazgos=[hallazgo])

    devueltos = await despachador.analyze(sitio.id)

    assert repo.guardados == [hallazgo]
    assert devueltos == [hallazgo]


@pytest.mark.asyncio
async def test_el_umbral_de_similitud_es_del_sitio():
    """CUR.2.1 — «el criterio es dato»: qué se parece bastante depende del portal, no del código."""
    sitio = _Sitio(semantic_similarity_threshold=0.85, semantic_max_pairs=50)
    despachador = _despachador(sitio, _RepoFalso())

    await despachador.analyze(sitio.id)

    assert _DetectorFalso.ultimo["similarity_threshold"] == 0.85
    assert _DetectorFalso.ultimo["max_pairs_per_run"] == 50


@pytest.mark.asyncio
async def test_un_sitio_que_no_existe_no_llama_a_ningun_modelo():
    despachador = _despachador(None, _RepoFalso())  # type: ignore[arg-type]

    assert await despachador.analyze(uuid.uuid4()) == []


@pytest.mark.asyncio
async def test_un_sitio_con_alcance_apagado_no_gasta_una_llamada():
    """`off` es una decisión de quien cura, y tiene que costar cero antes de embeber nada."""
    sitio = _Sitio(audit_semantic_scope="off")
    _DetectorFalso.ultimo = {}

    despachador = _despachador(sitio, _RepoFalso())
    hallazgos = await despachador.analyze(sitio.id)

    assert hallazgos == []
    assert _DetectorFalso.ultimo == {}


# ───────────────────────── El prompt del juez, literal ─────────────────────────


@pytest.mark.asyncio
async def test_el_prompt_del_juez_llega_al_modelo_sin_tocar():
    """Casi se cablea aquí el adaptador equivocado.

    `RedactorDeBloques` cumple este mismo protocolo, y su primer argumento es el **identificador**
    de una plantilla de prompt: al no estar en el catálogo lo sustituye por «la plantilla de prompt
    "…" no está en el catálogo del módulo». O sea, el juez habría recibido cualquier cosa menos la
    pregunta, y habría devuelto `unrelated` para todo sin que nada fallara.
    """
    from server.app.modules.curation.semantic_detector import JuezDeContenidoWeb

    class _Modelo:
        def __init__(self) -> None:
            self.recibido: list = []

        async def ainvoke(self, mensajes: list) -> Any:
            self.recibido = mensajes
            return type("R", (), {"content": '{"relation": "unrelated"}'})()

    modelo = _Modelo()
    juez = JuezDeContenidoWeb(modelo, "gemini-de-prueba")

    await juez.generate("Eres un auditor de contenido web. Compara A y B.", "")

    assert modelo.recibido[0]["content"].startswith("Eres un auditor de contenido web.")
    assert "catálogo" not in modelo.recibido[0]["content"]


# ───────────────────────── El registro en el arranque ─────────────────────────


def test_el_arranque_registra_los_dos_detectores():
    """El job se construía con un solo detector, así que `run_semantic=True` no significaba nada."""
    detectores = detectores_de_calidad(lambda: None)

    assert any(getattr(d, "_is_semantic", False) for d in detectores)
    assert any(not getattr(d, "_is_semantic", False) for d in detectores)


def test_con_el_flag_apagado_el_semantico_no_se_registra():
    """Apagarlo tiene que quitar la pieza, no dejarla dentro confiando en un `if` de más adentro."""
    detectores = detectores_de_calidad(lambda: None, run_semantic=False)

    assert not any(getattr(d, "_is_semantic", False) for d in detectores)


# ───────── Lo que no se juzga: pares que ya sabemos qué son (CUR.7) ─────────
#
# Los diez primeros hallazgos del detector semántico contra el apartado real eran el mismo falso
# positivo que CUR.2 quitó del determinista: el archivo de formación transversal publica una página
# por curso académico y el juez las declaraba «contradicción» porque las fechas no coinciden. No se
# contradicen: son ediciones distintas. Pagar una llamada al modelo para producir un hallazgo que ya
# hemos decidido que es falso es gasto y ruido a la vez.


@pytest.mark.asyncio
async def test_dos_ediciones_de_la_misma_serie_no_se_juzgan():
    from server.app.modules.curation.semantic_detector import (
        SemanticContradictionDetector,
    )

    base = "https://www.uji.es/estudis/centres/escola-doctorat/base/arxiu/Formacio-transversal"

    class _Pag:
        def __init__(self, url: str) -> None:
            self.id = uuid.uuid4()
            self.url = url
            self.canonical_url = None
            self.markdown_content = "Curs d'anàlisi multivariant. " * 20

    a = _Pag(f"{base}/23-24/recerca/multivariant/")
    b = _Pag(f"{base}/24-25/recerca/multivariant/")
    otra = _Pag(f"{base}/24-25/practiques/lideratge/")

    detector = SemanticContradictionDetector(session=None, llm=None, embedding_service=None)
    vector = [1.0, 0.0, 0.0]

    pares = detector._candidate_pairs([(a, vector), (b, vector), (otra, vector)])

    juzgados = {(p[0].url, p[1].url) for p in pares}
    assert (a.url, b.url) not in juzgados
    # Y lo que no es la misma serie sí se juzga: el filtro no puede vaciar la pasada.
    assert any(otra.url in par for par in juzgados)


# ───────── La segunda pasada (CUR.7) ─────────
#
# La primera pasada real guardó sus diez hallazgos y la segunda **falló al guardar**:
# `Object of type float32 is not JSON serializable`. La diferencia entre las dos: en la primera los
# vectores venían del servicio de embeddings (floats de Python) y en la segunda de pgvector, que los
# devuelve como `float32` de numpy. La similitud acaba dentro de `signal_json`, y ahí no cabe.
#
# O sea: el detector funcionaba exactamente una vez por sitio. No lo caza ningún test con vectores
# escritos a mano.


def test_la_similitud_del_hallazgo_es_un_numero_que_se_puede_guardar():
    import numpy

    from server.app.modules.curation.semantic_detector import (
        SemanticContradictionDetector,
    )

    class _Pag:
        def __init__(self, url: str) -> None:
            self.id = uuid.uuid4()
            self.site_id = uuid.uuid4()
            self.url = url
            self.canonical_url = None
            self.markdown_content = "x" * 100

    detector = SemanticContradictionDetector(session=None, llm=None, embedding_service=None)
    hallazgo = detector._to_finding(
        _Pag("https://www.uji.es/a/"),
        _Pag("https://www.uji.es/b/"),
        numpy.float32(0.987),
        {"relation": "duplicate", "confidence": 0.9, "explanation": "lo mismo"},
        datetime(2026, 8, 19, tzinfo=timezone.utc),
    )

    import json

    assert type(hallazgo.signal["similarity"]) is float
    json.dumps(hallazgo.signal)  # lo que hace SQLAlchemy al escribir el JSONB


def test_el_coseno_devuelve_un_float_de_python_aunque_entren_vectores_de_numpy():
    import numpy

    from server.app.modules.curation.semantic_detector import _cosine

    a = list(numpy.array([1.0, 0.0], dtype=numpy.float32))
    b = list(numpy.array([1.0, 0.0], dtype=numpy.float32))

    assert type(_cosine(a, b)) is float


# ───────── Lo que el juez tiene que saber del dominio (CUR.7) ─────────
#
# Nueve de los once hallazgos de la pasada real eran «contradicción» entre dos **ediciones** del
# mismo curso archivado: `23-24/recerca/programacio-r/` contra `25-26/tecniques/programacio-r/`. El
# filtro de series no los caza porque el portal reorganizó la ruta, así que la única forma de que el
# juez no se equivoque es **decírselo**: es el mismo dato del dominio que el usuario dio en CUR.2
# —«se publica por años pero todos son válidos»—, y sin él el modelo concluye lo esperable, que dos
# fechas distintas para el mismo curso se contradicen.


def test_el_prompt_del_juez_dice_que_dos_ediciones_no_se_contradicen():
    from server.app.modules.curation.semantic_detector import _build_judge_prompt

    prompt = _build_judge_prompt("Curs 23-24", "Curs 25-26")

    assert "edici" in prompt.lower()  # ediciones / edicions
    # Y lo que sí es contradicción se sigue diciendo: el prompt no puede quedarse sin el caso.
    assert "contradiction" in prompt

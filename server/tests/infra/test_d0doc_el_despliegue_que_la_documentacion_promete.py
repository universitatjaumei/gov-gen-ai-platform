"""La documentación no puede prometer un despliegue que no es el nuestro (D.0.doc).

El destino pasó a ser una **VM con Docker Compose** y no Cloud Run
(`docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md` §2). Nueve documentos de `docs/` seguían
mencionando Cloud Run y la mayoría lo hacía bien —registrar la decisión exige nombrar lo
que se descartó—, pero cuatro razonaban **sobre el destino actual**, y uno de ellos
afirmaba una protección que la VM no trae:

    docs/SANDBOX_SECURITY.md
    ### Capa 8 — gVisor en GCP (despliegue Cloud Run)

Esa capa la daba **la plataforma**, no el código. Un documento de seguridad que cuenta
una capa inexistente no es desorden documental: es la clase de cosa que alguien lee justo
antes de desplegar, y decide con ella. El sandbox ejecuta código generado por un LLM y el
propio modelo de amenazas supone que la auditoría AST es *bypassable*, así que la capa que
mitiga la fuga del kernel no es decorativa.

**Cómo se distingue la historia de la promesa**: por inventario, no por adivinar el tono
de cada frase. Los documentos de decisión tienen que poder nombrar Cloud Run —es lo que
descartaron— y están enumerados abajo con su razón. Cualquier otro documento que lo
mencione es un descuido, y este test lo dice con el fichero en la mano. Es el mismo patrón
que `docs/MULTITENENCIA.md` y su test: un inventario que una persona mantiene y un
guardarraíl que impide que envejezca en silencio.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
DOCS = RAIZ / "docs"

_CLOUD_RUN = re.compile(r"cloud\s+run", re.IGNORECASE)

#: Documentos que SÍ pueden nombrar Cloud Run, y por qué. Añadir uno exige escribir la
#: razón: si la razón no se puede escribir, la mención sobra.
MENCIONES_LEGITIMAS: dict[str, str] = {
    "DECISION_EXTRACCION_Y_DESPLIEGUE.md": (
        "Es la decisión que descartó Cloud Run; su razonamiento tiene que nombrarlo."
    ),
    "DECISION_MODELOS_EMBEDDING_RERANKER.md": (
        "Registro de decisión: la premisa de entonces era el límite de RAM por instancia."
    ),
    "DECISION_CURACION_SEPARADA.md": (
        "Registro de decisión anterior al cambio de destino; su argumento no depende de él."
    ),
    "README.md": (
        "El índice describe qué decidió cada documento, y uno decidió «VM y no Cloud Run»."
    ),
}

#: Capas declaradas en la prosa del modelo de seguridad, p. ej. «con 8 capas independientes».
_CAPAS_DECLARADAS = re.compile(r"con\s+(\d+)\s+capas\s+independientes", re.IGNORECASE)
_CABECERA_DE_CAPA = re.compile(r"^###\s+Capa\s+(\d+)\s+—", re.MULTILINE)


def _documentos() -> list[Path]:
    return sorted(p for p in DOCS.rglob("*") if p.suffix in {".md", ".html"} and p.is_file())


def test_ningun_documento_promete_que_el_despliegue_corra_en_cloud_run() -> None:
    """Sólo los documentos inventariados pueden nombrar Cloud Run."""
    infractores: list[tuple[str, int, str]] = []

    for documento in _documentos():
        if documento.name in MENCIONES_LEGITIMAS:
            continue
        texto = documento.read_text(encoding="utf-8")
        for numero, linea in enumerate(texto.splitlines(), start=1):
            if _CLOUD_RUN.search(linea):
                relativa = documento.relative_to(RAIZ).as_posix()
                infractores.append((relativa, numero, linea.strip()[:120]))

    assert not infractores, (
        "El despliegue es una VM con Docker Compose, no Cloud Run "
        "(docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md §2), y estos documentos siguen "
        "nombrándolo fuera del inventario de menciones legítimas:\n"
        + "\n".join(f"  {f}:{n}  {t}" for f, n, t in infractores)
        + "\n\nSi la mención registra historia, añade el documento a MENCIONES_LEGITIMAS "
        "con su razón. Si razona sobre el destino actual, corrígela."
    )


def test_el_numero_de_capas_que_declara_el_sandbox_es_el_que_hay() -> None:
    """La prosa dice cuántas capas hay; las cabeceras dicen cuáles. Tienen que cuadrar."""
    documento = DOCS / "SANDBOX_SECURITY.md"
    texto = documento.read_text(encoding="utf-8")

    declarado = _CAPAS_DECLARADAS.search(texto)
    assert declarado, (
        "SANDBOX_SECURITY.md tiene que declarar en prosa cuántas capas independientes "
        "hay («con N capas independientes»): es la cifra con la que alguien juzga el "
        "aislamiento sin leerse las ocho secciones."
    )

    capas = [int(n) for n in _CABECERA_DE_CAPA.findall(texto)]
    assert capas, "No se ha encontrado ninguna cabecera «### Capa N — …»."

    assert int(declarado.group(1)) == len(capas), (
        f"SANDBOX_SECURITY.md declara {declarado.group(1)} capas y describe {len(capas)}. "
        "Una capa que se retira o se añade cambia el juicio sobre el aislamiento del "
        "sandbox, que ejecuta código generado por un LLM."
    )

    assert capas == list(range(1, len(capas) + 1)), (
        f"Las capas tienen que ir numeradas de 1 a {len(capas)} sin huecos ni repeticiones; "
        f"están: {capas}."
    )


def test_la_capa_de_gvisor_se_declara_como_configuracion_de_la_vm() -> None:
    """Si la capa 8 sigue existiendo, tiene que decir quién la pone y cómo se comprueba.

    La versión anterior la daba por puesta porque la ponía Cloud Run. En una VM la pone
    el aprovisionamiento, así que el documento tiene que nombrar el runtime y dejar el
    comando que prueba que está — una capa que no se puede comprobar no se puede contar.
    """
    texto = (DOCS / "SANDBOX_SECURITY.md").read_text(encoding="utf-8")
    if "gvisor" not in texto.lower():
        return  # La capa se retiró; lo cuadra el test del número de capas.

    assert "runsc" in texto, (
        "La capa de gVisor tiene que nombrar el runtime (`runsc`) que hay que configurar "
        "en la VM: sin el nombre, no es una instrucción, es una aspiración."
    )
    assert re.search(r"runtime\s*[:=]\s*runsc", texto), (
        "Falta cómo se activa para el sandbox (`runtime: runsc` en el servicio de "
        "`docker-compose.prod.yml`)."
    )
    assert "dmesg" in texto or "/proc/version" in texto, (
        "Falta el comando que comprueba que el sandbox corre bajo gVisor. Una capa que "
        "nadie verifica es la misma que no estar, y ésta ya se contó una vez sin estar."
    )

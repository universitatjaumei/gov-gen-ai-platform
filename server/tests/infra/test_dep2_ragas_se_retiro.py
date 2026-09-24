"""RAGAS se retiró entero el 2026-09-24, y volver tiene que ser una decisión.

**Qué se fue.** `ragas`, y detrás de él `datasets` y `diskcache`. Con ellos se fue el módulo
`agents_hub/evaluation/rag_metrics.py`, que ofrecía `calculate_faithfulness` y
`calculate_answer_relevance`.

**Por qué, y el orden importa.** No fue por los avisos de seguridad, aunque se llevó los cuatro
—los dos únicos del repositorio **sin versión corregida publicada**, y con el proveedor de
`ragas` sin responder a la comunicación del fallo, de modo que la corrección no iba a llegar—.
Lo que lo justificó es una medición más simple: **las dos funciones no tenían ningún llamador
fuera de los tests**, y esos tests *simulaban* la llamada a RAGAS. Era una capacidad que figuraba
en el manifiesto, tenía su módulo y su docstring, y no se ejecutaba en ninguna parte. Encajaba
con lo que el bloque HIB ya había decidido por medición: apagar la comprobación de fundamento.

**Lo que NO se fue, porque es lo que de verdad mide.** La calidad de la recuperación sigue
instrumentada y sin depender de ningún LLM: `retrieval_metrics.py` (recall@k y MRR, funciones
puras), el dataset dorado con su `documents_fingerprint`, la línea base y su gate de CI, y las
tres comprobaciones de cita de `escenario_metricas.py`. Lo que no hay —medición **automática** de
la calidad de la respuesta— tampoco lo había con RAGAS instalado.

**Por qué un guardarraíl y no sólo un commit.** Porque el camino de vuelta es plausible y barato:
alguien busca «cómo medimos fidelidad», encuentra RAGAS, lo añade al manifiesto y el repositorio
recupera en silencio dos avisos sin corrección. Que vuelva puede estar bien —si alguien lo va a
llamar— pero entonces es una decisión, y una decisión se toma borrando un test y escribiendo por
qué, no añadiendo una línea a un fichero de dependencias.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[3]
MANIFIESTO = RAIZ / "server" / "pyproject.toml"
LOCK = RAIZ / "server" / "uv.lock"
MODULO = RAIZ / "server" / "app" / "modules" / "agents_hub" / "evaluation" / "rag_metrics.py"

#: Los tres paquetes que se fueron juntos. `diskcache` sólo entraba como transitiva de `ragas`,
#: así que su vuelta significaría que el padre ha vuelto también.
RETIRADOS = ("ragas", "datasets", "diskcache")


@pytest.fixture(scope="module")
def manifiesto() -> dict:
    return tomllib.loads(MANIFIESTO.read_text(encoding="utf-8"))


def test_el_medidor_lee_el_manifiesto(manifiesto: dict) -> None:
    # Si el TOML dejara de parsearse como se espera, los test de abajo compararían conjuntos
    # vacíos contra conjuntos vacíos y pasarían en verde sin mirar nada.
    assert manifiesto["project"]["dependencies"], "no se han leído las dependencias base"


def test_no_estan_en_las_dependencias_base(manifiesto: dict) -> None:
    declarados = " ".join(manifiesto["project"]["dependencies"]).lower()
    vueltos = [p for p in RETIRADOS if p in declarados]
    assert not vueltos, (
        f"{vueltos} ha vuelto a las dependencias base. Se retiraron porque nadie llamaba a lo "
        f"que lo usaba, y traen consigo dos avisos de seguridad sin corrección publicada. Si "
        f"vuelve porque alguien va a usarlo, borra este test y escribe por qué."
    )


def test_no_hay_ningun_extra_que_los_traiga(manifiesto: dict) -> None:
    extras = manifiesto["project"].get("optional-dependencies", {})
    culpables = {
        nombre: [p for p in RETIRADOS if p in " ".join(paquetes).lower()]
        for nombre, paquetes in extras.items()
        if any(p in " ".join(paquetes).lower() for p in RETIRADOS)
    }
    assert not culpables, (
        f"un extra vuelve a declararlos: {culpables}. Un extra que nadie instala parece "
        f"inofensivo, pero sus paquetes entran en el `uv.lock` y desde ahí en las alertas de "
        f"dependencias del repositorio — que es exactamente como llegaron las dos que había."
    )


def test_no_estan_en_el_lock() -> None:
    """El manifiesto es la intención; el lock es lo que de verdad se resuelve.

    Van los dos porque no dicen lo mismo: un paquete puede desaparecer del manifiesto y seguir
    en el lock como transitiva de otro. Si eso pasara, las alertas seguirían ahí y el test del
    manifiesto estaría pasando en verde.
    """
    texto = LOCK.read_text(encoding="utf-8")
    presentes = [p for p in RETIRADOS if f'name = "{p}"' in texto]
    assert not presentes, (
        f"{presentes} sigue(n) en `server/uv.lock`. Si ya no está(n) en el manifiesto, es que "
        f"llega(n) como transitiva de otro paquete: averigua de cuál con `uv tree`, porque las "
        f"alertas de seguridad se calculan sobre el lock y no sobre el manifiesto."
    )


def test_el_modulo_no_ha_vuelto() -> None:
    assert not MODULO.exists(), (
        f"{MODULO.relative_to(RAIZ).as_posix()} ha vuelto. Su contenido está en el historial de "
        f"git; recrearlo sin que nadie llame a sus funciones repetiría exactamente la situación "
        f"que se retiró: un módulo con docstring, con tests que simulan su dependencia, y sin un "
        f"solo llamador en producción."
    )

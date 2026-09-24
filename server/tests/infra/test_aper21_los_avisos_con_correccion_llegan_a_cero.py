"""APER.21 — los dos avisos que quedaban con corrección publicada, cerrados.

Después de APER.19 (retirar el agente de navegador) y APER.20 (subir `torch` y con él
`setuptools`), en el lock quedaban **siete** avisos, todos fuera del conjunto que se despliega.
Cuatro de ellos no tienen corrección publicada —`diskcache` y `ragas`, dos cada uno— y por eso
informan y no bloquean: subir no es una opción, así que el sitio de esa conversación es
`avisos_aceptados.toml` o retirar quien los trae.

Los otros tres **sí tienen corrección**, y ésos no tenían excusa:

* `pytest` 9.0.2 → **9.1.1** (GHSA-6w46-j5rx-g56g y PYSEC-2026-1845), que es `dev`. La
  corrección estaba en la 9.0.3; `uv` resolvió la 9.1.1 porque nada la acota, y se deja así en
  vez de fijarla a la 9.0.3: pinchar una versión para que la cifra cuadre con el aviso es la
  clase de acotación que luego nadie recuerda por qué está.
* `datasets` 4.8.4 → 5.0.1 (PYSEC-2026-3716), que entraba por `ragas` en el extra `evaluacion`.
  Cruzaba un mayor, y `ragas` 0.4.3 lo aceptaba: la resolución no movió ningún otro paquete.

**Por qué merece un prompt propio en vez de ir con APER.20.** Los dos tocan cómo se comprueba
todo lo demás: `pytest` **es** el que ejecuta la suite, y `datasets` cruzaba un mayor. Meterlos
en el mismo commit que la subida de `torch` habría hecho que un rojo no dijese cuál de las dos
cosas lo causó. Es la misma razón por la que este proyecto hace un commit por prompt.

**Y el 2026-09-24 los cuatro sin corrección se fueron con su paquete.** `ragas` se retiró entero
—con `datasets` y `diskcache` detrás— porque sus dos funciones no tenían ningún llamador fuera de
los tests. Los tests que vigilaban `datasets` y el extra `evaluacion` se han borrado aquí, que es
lo que ellos mismos pedían que se hiciera si eso pasaba. Lo que impide que vuelvan es
`test_dep2_ragas_se_retiro.py`.

**Lo que este fichero vigila no es «estar al día», que sería una carrera imposible de ganar**:
es que **ningún aviso con corrección publicada se quede sin decidir**. Un aviso corregible tiene
exactamente dos finales legítimos —se sube, o se acepta con motivo, firma y fecha— y el que no
vale es el tercero, quedarse quieto porque nadie lo mira.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
LOCK = RAIZ / "server" / "uv.lock"


def _version_en_el_lock(paquete: str) -> str | None:
    texto = LOCK.read_text(encoding="utf-8")
    m = re.search(
        rf'^name = "{re.escape(paquete)}"\nversion = "([^"]+)"', texto, re.MULTILINE
    )
    return m.group(1) if m else None


def _tupla(version: str) -> tuple[int, ...]:
    return tuple(int(p) for p in re.findall(r"\d+", version.split("+")[0])[:3])


class TestLosDosQueSePodianSubir:

    def test_pytest_esta_al_menos_en_9_0_3(self) -> None:
        version = _version_en_el_lock("pytest")
        assert version is not None, "`pytest` ha desaparecido del lock"
        assert _tupla(version) >= (9, 0, 3), (
            f"`pytest` está en {version}. Sus dos avisos se corrigen en la 9.0.3, y es una "
            "dependencia de `dev`: no llega al despliegue, pero sí a cada ejecución de CI."
        )

    # `test_datasets_esta_al_menos_en_5_0_1` y la clase `TestLoQueSiguePendienteEstaDicho`
    # estuvieron aquí y se fueron el 2026-09-24, que es exactamente lo que sus propios mensajes
    # de fallo pedían: «si es porque se retiró el extra `evaluacion`, el aviso también se fue y
    # este test sobra; bórralo diciendo por qué».
    #
    # El porqué: `ragas` se retiró entero, y con él `datasets` y `diskcache`. No fue por los
    # avisos —aunque se llevó los cuatro, los dos únicos sin corrección publicada del
    # repositorio—, sino porque **sus dos funciones no tenían ningún llamador fuera de los
    # tests**, y esos tests simulaban la llamada. Era una capacidad que parecía estar y no se
    # ejecutaba en ninguna parte.
    #
    # Lo que impide que vuelvan sin decidirlo es `test_dep2_ragas_se_retiro.py`.

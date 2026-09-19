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
* `datasets` 4.8.4 → 5.0.1 (PYSEC-2026-3716), que entra por `ragas` en el extra `evaluacion`.
  Cruza un mayor, y `ragas` 0.4.3 lo acepta: la resolución no movió ningún otro paquete.

**Por qué merece un prompt propio en vez de ir con APER.20.** Los dos tocan cómo se comprueba
todo lo demás: `pytest` **es** el que ejecuta la suite, y `datasets` cruza un mayor. Meterlos en
el mismo commit que la subida de `torch` habría hecho que un rojo no dijese cuál de las dos cosas
lo causó. Es la misma razón por la que este proyecto hace un commit por prompt.

**Lo que este fichero vigila no es «estar al día», que sería una carrera imposible de ganar**:
es que **ningún aviso con corrección publicada se quede sin decidir**. Un aviso corregible tiene
exactamente dos finales legítimos —se sube, o se acepta con motivo, firma y fecha— y el que no
vale es el tercero, quedarse quieto porque nadie lo mira.
"""

from __future__ import annotations

import re
import tomllib
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


def _nombre(requisito: str) -> str:
    """`ragas>=0.2.0` → `ragas`. Sin marcadores, extras ni comparadores."""
    return re.split(r"[\[<>=!~; ]", requisito, maxsplit=1)[0].strip().lower()


class TestLosDosQueSePodianSubir:

    def test_pytest_esta_al_menos_en_9_0_3(self) -> None:
        version = _version_en_el_lock("pytest")
        assert version is not None, "`pytest` ha desaparecido del lock"
        assert _tupla(version) >= (9, 0, 3), (
            f"`pytest` está en {version}. Sus dos avisos se corrigen en la 9.0.3, y es una "
            "dependencia de `dev`: no llega al despliegue, pero sí a cada ejecución de CI."
        )

    def test_datasets_esta_al_menos_en_5_0_1(self) -> None:
        version = _version_en_el_lock("datasets")
        assert version is not None, (
            "`datasets` ha desaparecido del lock. Si es porque se retiró el extra `evaluacion`, "
            "el aviso también se fue y este test sobra; bórralo diciendo por qué."
        )
        assert _tupla(version) >= (5, 0, 1), (
            f"`datasets` está en {version}, y PYSEC-2026-3716 se corrige en la 5.0.1."
        )


class TestLoQueSiguePendienteEstaDicho:
    """`diskcache` y `ragas` se quedan, y la diferencia importa.

    No es lo mismo «no lo hemos mirado» que «no hay nada que aplicar». Estos cuatro avisos no
    tienen versión corregida publicada, así que la puerta los informa a propósito. Este test
    existe para que, el día que **sí** la tengan, alguien tenga que venir aquí y decidir: si se
    corrigen y nadie sube, el rojo aparece en la puerta, no aquí.
    """

    def test_los_dos_paquetes_sin_correccion_siguen_siendo_del_extra(self) -> None:
        """Se lee el TOML, no se parte el texto.

        La primera versión de este test buscaba `ragas` en la mitad del fichero anterior a
        `[project.optional-dependencies]`, y se puso roja: ahí hay **dos comentarios** que
        nombran a `ragas` explicando precisamente que se fue al extra. El test afirmaba lo
        contrario de lo que pasaba, y el defecto era del medidor.
        """
        manifiesto = tomllib.loads(
            (RAIZ / "server" / "pyproject.toml").read_text(encoding="utf-8")
        )
        base = {_nombre(d) for d in manifiesto["project"]["dependencies"]}
        extras = manifiesto["project"].get("optional-dependencies", {})
        del_extra = {_nombre(d) for d in extras.get("evaluacion", [])}

        assert "ragas" in del_extra, (
            "`ragas` ya no está en el extra `evaluacion`. Si se ha retirado entero, sus cuatro "
            "avisos sin corrección se fueron con él y esta clase entera sobra; bórrala diciendo "
            "por qué."
        )
        assert "ragas" not in base, (
            "`ragas` ha pasado a las dependencias base. Entonces `diskcache` y sus dos avisos "
            "**sin corrección publicada** entran en el conjunto que se despliega, y la puerta "
            "pasa de informar a tener que bloquear."
        )

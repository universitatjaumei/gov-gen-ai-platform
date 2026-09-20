"""Las PR contra `desarrollo` también pasan por CI y por el DCO.

**Veinte PR de Dependabot abiertas y cero comprobaciones en todas ellas.** Medido el 2026-09-20
sobre la #72: `check-runs: 0`, `estado combinado: pending`, cero contextos. Ninguna había
ejecutado un solo test.

No es un fallo de nadie: son **dos decisiones correctas que juntas dejan un hueco**.

1. `dependabot.yml` apunta sus siete objetivos a `target-branch: desarrollo`, para que un robot
   no abra PR contra la rama que despliega.
2. `ci.yml` y `dco.yml` escuchan `pull_request` **sólo sobre `main`**, porque el trabajo humano
   se empuja directamente a `desarrollo` y el disparador de `push` ya lo cubre.

Para una persona eso funciona: su código pasa por CI al empujarlo. Para Dependabot no, porque su
código **sólo existe en la rama de la PR** hasta que alguien la mezcla. O sea que el verde que se
mira antes de mezclar no era verde: era **vacío**, que se parece bastante en la pantalla.

**Esto no duplica ejecuciones.** Las PR contra `desarrollo` son hoy exclusivamente las del robot;
lo que una persona abre es `desarrollo → main`, que ya estaba cubierto. Y el grupo de
concurrencia lleva `github.ref`, que en una PR es `refs/pull/N/merge` y en un empujón
`refs/heads/desarrollo`: son grupos distintos, así que tampoco se cancelan entre sí.

La lista de ramas **no se escribe a mano**: sale de `dependabot.yml`. Si mañana alguien apunta un
objetivo a otra rama y nadie toca los workflows, este guardarraíl lo dice.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[3]
DEPENDABOT = RAIZ / ".github" / "dependabot.yml"
WORKFLOWS = {
    "ci.yml": RAIZ / ".github" / "workflows" / "ci.yml",
    "dco.yml": RAIZ / ".github" / "workflows" / "dco.yml",
}


def _ramas_objetivo() -> set[str]:
    """Las ramas contra las que Dependabot abre PR, según su propia configuración."""
    datos = yaml.safe_load(DEPENDABOT.read_text(encoding="utf-8"))
    return {
        objetivo.get("target-branch", "main") for objetivo in datos.get("updates", [])
    }


def _ramas_de_pull_request(ruta: Path) -> set[str]:
    """Las ramas que el workflow escucha en `pull_request`.

    `on` se lee del YAML crudo con una vuelta: en YAML 1.1 la palabra `on` **es un booleano**,
    así que `yaml.safe_load` devuelve la clave `True` y no `"on"`. Un guardarraíl que buscara
    `datos["on"]` daría `KeyError` o, peor, un valor por defecto que lo pondría en verde.
    """
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    disparadores = datos.get("on", datos.get(True))
    assert disparadores, f"no encuentro los disparadores de {ruta.name}"
    pr = disparadores.get("pull_request") or {}
    return set(pr.get("branches") or [])


def test_dependabot_apunta_a_donde_creemos() -> None:
    """Si esto cambia, lo de abajo deja de tener sentido y hay que releerlo."""
    ramas = _ramas_objetivo()
    assert ramas, "`dependabot.yml` no declara objetivos"
    assert "desarrollo" in ramas, (
        f"Dependabot ya no apunta a `desarrollo`, sino a {sorted(ramas)}. Eso cambia la razón "
        "de este fichero: hay que comprobar que los workflows cubran las ramas nuevas."
    )


@pytest.mark.parametrize("nombre", sorted(WORKFLOWS))
def test_cada_rama_objetivo_dispara_el_workflow(nombre: str) -> None:
    objetivo = _ramas_objetivo()
    escuchadas = _ramas_de_pull_request(WORKFLOWS[nombre])
    sin_cubrir = sorted(objetivo - escuchadas)
    assert not sin_cubrir, (
        f"`{nombre}` no escucha las PR contra {sin_cubrir}, y Dependabot abre las suyas ahí. "
        "El resultado no es un rojo: es que **no corre nada**, y una PR sin comprobaciones se "
        "parece mucho a una PR en verde cuando se mira por encima. El 2026-09-20 había veinte "
        "así."
    )

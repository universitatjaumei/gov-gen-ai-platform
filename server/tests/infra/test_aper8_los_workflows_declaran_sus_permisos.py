"""APER.8 — cada workflow declara qué permisos necesita, y por qué si pide escritura.

**Hallazgo B3 de la auditoría previa a abrir el repositorio.** `ci.yml` y `dco.yml` no declaraban
`permissions` en la raíz: sólo un job de `ci.yml` lo hacía. Sin declaración, el alcance del
`GITHUB_TOKEN` lo decide **la configuración de la organización**, no el repositorio — y por
omisión en muchas organizaciones eso es permisivo.

**Por qué importa ahora y no antes.** Con el repositorio privado, quien abre una *pull request*
es alguien de dentro. En público, **cualquiera** puede abrir una desde un *fork*, y con ella
ejecutar CI. Un token con más alcance del necesario en ese contexto es la diferencia entre un
trabajo que lee el código y uno que puede escribir en el repositorio.

`deploy.yml` ya lo hacía bien —y es el que más lo necesita—: `contents: read` más
`id-token: write`, que lo exige la federación de identidad con GCP. Esa es la forma que este test
convierte en obligatoria para los demás: **declararlo siempre, y razonar cada escritura**.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[3]
WORKFLOWS = RAIZ / ".github" / "workflows"

#: Escrituras legítimas, con su razón. **Esta lista sólo puede encoger.** Es el mismo patrón que
#: las exenciones del inventario de routers: olvidarse de añadir aquí falla del lado seguro.
_ESCRITURAS_CON_RAZON = {
    ("deploy.yml", "id-token"): (
        "la federación de identidad con GCP (Workload Identity) firma el token de OIDC con el "
        "que se autentica el despliegue; sin escritura no hay forma de obtenerlo"
    ),
}


def _workflows() -> list[Path]:
    ficheros = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    assert ficheros, "no hay workflows en .github/workflows"
    return ficheros


@pytest.mark.parametrize("ruta", _workflows(), ids=lambda p: p.name)
def test_cada_workflow_declara_permisos_en_la_raiz(ruta: Path) -> None:
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    assert "permissions" in datos, (
        f"{ruta.name} no declara `permissions` en la raíz. Sin eso, el alcance del "
        "GITHUB_TOKEN lo decide la configuración de la organización y no este repositorio — y "
        "en un repositorio público cualquiera puede ejecutar este workflow desde un fork."
    )


@pytest.mark.parametrize("ruta", _workflows(), ids=lambda p: p.name)
def test_ninguna_escritura_sin_razon_escrita(ruta: Path) -> None:
    permisos = yaml.safe_load(ruta.read_text(encoding="utf-8"))["permissions"]
    if not isinstance(permisos, dict):
        # `permissions: read-all` o `{}` son declaraciones válidas y no conceden escritura.
        assert permisos in ("read-all", None, {}), f"{ruta.name}: `permissions: {permisos}`"
        return

    for alcance, valor in permisos.items():
        if valor != "write":
            continue
        razon = _ESCRITURAS_CON_RAZON.get((ruta.name, alcance))
        assert razon, (
            f"{ruta.name} concede `{alcance}: write` y no hay razón escrita para ello. "
            "Si de verdad hace falta, añádela a `_ESCRITURAS_CON_RAZON` diciendo qué paso la "
            "necesita; si no, ponla en `read`."
        )


def test_el_contenido_se_lee_pero_no_se_escribe() -> None:
    """La escritura de `contents` es la que permitiría empujar a una rama.

    Se comprueba aparte porque es la que importa en este repositorio: `main` despliega, así que
    un token que pueda escribir contenido desde un workflow es un camino al despliegue que no
    pasa por una persona.
    """
    for ruta in _workflows():
        permisos = yaml.safe_load(ruta.read_text(encoding="utf-8"))["permissions"]
        if isinstance(permisos, dict):
            assert permisos.get("contents", "read") != "write", (
                f"{ruta.name} puede escribir contenido. En este repositorio `main` despliega: "
                "eso es un camino al despliegue que no pasa por una persona."
            )

"""MT.7 — que la próxima auditoría dure diez minutos y no dos días.

La auditoría que originó el Bloque MT consistió en reconstruir a mano, leyendo 31 tablas y 32
routers, qué está acotado por organización y qué no. El resultado de esa lectura es el documento
`docs/MULTITENENCIA.md`; este test es lo que evita que se convierta en una foto vieja.

**No comprueba prosa.** Comprueba que el documento nombra **todas** las tablas de
`HubConfigBase` con el ámbito que el código declara. Una tabla nueva, o una que cambie de ámbito,
pone el test rojo — y entonces alguien actualiza la única página donde esto se puede consultar.
"""
from __future__ import annotations

import re
from pathlib import Path

from server.app.core.ambito import Ambito, ambito_de
from server.app.modules.agents_hub.database.base import HubConfigBase

DOCUMENTO = Path(__file__).resolve().parents[2].parent / "docs" / "MULTITENENCIA.md"


def _tablas_declaradas() -> dict[str, Ambito]:
    import server.app.modules.agents_hub.database.config_models  # noqa: F401

    return {
        mapper.class_.__tablename__: ambito_de(mapper.class_).ambito
        for mapper in HubConfigBase.registry.mappers
    }


def test_should_exist_where_someone_would_look_for_it():
    assert DOCUMENTO.exists(), f"falta {DOCUMENTO}"


def test_should_name_every_config_table():
    """Cada tabla de configuración, en el documento. Una que falte es una que la próxima
    auditoría tendría que volver a descubrir leyendo el modelo."""
    texto = DOCUMENTO.read_text(encoding="utf-8")

    ausentes = sorted(t for t in _tablas_declaradas() if t not in texto)

    assert ausentes == [], (
        "Estas tablas de configuración no aparecen en docs/MULTITENENCIA.md: "
        + ", ".join(ausentes)
    )


def test_should_say_the_same_scope_as_the_code():
    """**El test que importa.** Un inventario que nombre las tablas pero les asigne otro ámbito
    del que declara el código es peor que no tenerlo: se lee como verdad y manda a decidir con
    un dato falso.

    Se busca en la **fila del inventario** y no en la primera línea que mencione el nombre:
    varias tablas se citan antes en la prosa que las explica, y quedarse con esa coincidencia
    daba un falso rojo — lo dio, de hecho, la primera vez que corrió este test.
    """
    lineas = [
        linea
        for linea in DOCUMENTO.read_text(encoding="utf-8").splitlines()
        if linea.startswith("| `")
    ]

    discrepantes: list[str] = []
    for tabla, ambito in sorted(_tablas_declaradas().items()):
        fila = next((linea for linea in lineas if re.search(rf"`{re.escape(tabla)}`", linea)), None)
        if fila is None:
            continue  # lo cubre el test de arriba
        if ambito.value not in fila:
            discrepantes.append(f"{tabla}: el código dice «{ambito.value}» y la fila no")

    assert discrepantes == [], discrepantes


def test_should_be_linked_from_the_rules_agents_read():
    """El documento sirve si se encuentra. `AGENTS.md` es lo que lee un agente al arrancar, y
    ahí es donde ya vive la frontera edge/cloud: al lado."""
    reglas = (DOCUMENTO.parent.parent / "AGENTS.md").read_text(encoding="utf-8")

    assert "MULTITENENCIA.md" in reglas

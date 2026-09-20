"""El recorrido de rutas encuentra todo lo que el contrato declara.

`server/tests/rutas.py` camina la estructura **interna** de `fastapi` —`_IncludedRouter`,
`original_router`, el prefijo de cada inclusión— y esa estructura **no es un contrato**: ya
cambió una vez, al pasar de 0.136 a 0.141, y dejó catorce tests comprobando un conjunto de siete
rutas mientras la aplicación servía ciento setenta y ocho.

Así que el ayudante se comprueba contra lo único que sí es contrato en este proyecto: **el
esquema OpenAPI**. Si una subida futura vuelve a reorganizar los tipos internos, este fichero se
pone rojo **aquí**, en un sitio que explica qué pasó, en vez de repartir el desconcierto por
catorce tests que dirán que un endpoint no existe cuando sí existe.

Lo que no puede hacer el esquema es sustituir al recorrido, y conviene tenerlo escrito: `fastapi`
**inventa** un `operationId` cuando el router no lo declara, así que en el esquema siempre hay
uno. Comprobar contra él que «el endpoint tiene identificador explícito» daría verde siempre.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("TESTING", "1")


@pytest.fixture(scope="module")
def aplicacion():
    from server.app.main import app

    return app


def test_el_recorrido_ve_lo_que_el_contrato_declara(aplicacion) -> None:
    from server.tests.rutas import caminos

    del_recorrido = caminos(aplicacion)
    del_contrato = set(aplicacion.openapi().get("paths", {}))

    assert del_contrato, "el esquema OpenAPI no declara ninguna ruta"
    faltan = sorted(del_contrato - del_recorrido)
    assert not faltan, (
        f"el recorrido no encuentra {len(faltan)} rutas que el contrato declara, empezando por "
        f"{faltan[:5]}. Es la señal de que `fastapi` ha vuelto a reorganizar su estructura "
        "interna: la aplicación sigue sirviéndolas y lo que hay que arreglar es "
        "`server/tests/rutas.py`, no los tests que lo usan."
    )


def test_el_recorrido_no_se_queda_en_la_primera_capa(aplicacion) -> None:
    """La comprobación que habría cazado el cambio de 0.141 el día que ocurrió.

    Con la enumeración plana, `app.routes` daba siete entradas. Una cota baja y explícita vale
    más que un número exacto: lo que se vigila es que no se vuelva a comprobar un puñado de
    rutas creyendo que se comprueban todas.
    """
    from server.tests.rutas import caminos

    assert len(caminos(aplicacion)) > 100, (
        f"el recorrido sólo ve {len(caminos(aplicacion))} rutas. La aplicación sirve más de "
        "ciento cincuenta, así que algo ha dejado de descender."
    )


def test_el_esquema_no_sirve_para_el_identificador_explicito(aplicacion) -> None:
    """Por qué el ayudante mira los objetos de ruta y no el esquema, comprobado y no supuesto.

    Si algún día `fastapi` dejara de inventar `operationId`, este test se pondría rojo y el
    ayudante podría simplificarse usando el contrato. Mientras invente, no.
    """
    from server.tests.rutas import operaciones

    declarados = {c: o for c, o in operaciones(aplicacion).items() if o}
    esquema = aplicacion.openapi().get("paths", {})
    del_esquema = {
        camino
        for camino, verbos in esquema.items()
        for detalle in verbos.values()
        if isinstance(detalle, dict) and detalle.get("operationId")
    }

    assert len(del_esquema) > len(declarados), (
        "el esquema ya no trae más `operationId` que los declarados en el código, así que "
        "`fastapi` ha dejado de inventarlos. Si es así, `rutas.py` puede leerse del contrato."
    )

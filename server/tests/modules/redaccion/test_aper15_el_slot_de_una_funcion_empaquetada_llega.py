"""APER.15 — el fichero de un bloque llega al slot que la función declara.

**El defecto.** `_ficheros_del_bloque` buscaba el nombre del slot en `block_contract.slot` o en
`options["slot"]`. Ninguno de los dos sirve:

* `blocks.py` **no tiene** campo `slot`.
* `options["slot"]` **ya está ocupado**: `manual_pipeline` lo usa como diccionario, y el ayudante
  exigía `isinstance(slot, str)`.

Así que devolvía `{}` **siempre**, y una función empaquetada con slot obligatorio fallaba la
validación antes de ejecutarse. O sea: FUN.5 resolvía la función, enrutaba bien, y no le llegaba
la entrada.

**Y por qué no lo cazó el test de FUN.5**: llamaba a `_ejecutar_ejecutable` pasándole `ficheros`
a mano. Probaba la pieza, no el camino desde un bloque. Éste va por el camino.

**El fondo era peor que el nombre perdido.** El slot de la **especificación** (`datos_del_script`)
y el del **contrato de la función** (`gastos`) son espacios de nombres distintos, y nada los
mapeaba: propagar el de la especificación habría fallado igual, con otro mensaje. Lo que decide es
el contrato de la función, que el resolutor ya trae en `contrato_entrada`.

**La regla, y su límite dicho en voz alta**: un bloque tiene **un** fichero —así está montado el
nodo desde 9R—, así que si la función declara **un** slot, ahí va. Si declara varios, no se
adivina: se falla con el motivo. Adivinar sería meter el fichero de gastos en el slot de plantilla
porque estaba primero.
"""

from __future__ import annotations

import pytest


def _contrato(*slots: tuple[str, bool]) -> dict:
    """Un `contrato_entrada` como el que trae el resolutor, con los slots que se le digan."""
    return {
        "slots": [
            {"slot_id": sid, "kind": "excel", "required": req} for sid, req in slots
        ],
        "parametros": [],
        "finalidad": "prueba",
        "categorias_datos": ["sin_datos_personales"],
    }


class _Ejecutable:
    """Lo mínimo del resuelto que el nodo mira."""

    origen = "paquete"

    def __init__(self, contrato: dict) -> None:
        self.contrato_entrada = contrato


class TestElFicheroLlegaAlSlotDeLaFuncion:

    def test_con_un_solo_slot_va_ahi(self) -> None:
        from server.app.modules.redaccion.graph.nodes.deterministic_extraction import (
            _ficheros_del_bloque,
        )
        from server.app.modules.redaccion.pipelines.contracts import StorageRef

        ficheros = _ficheros_del_bloque(
            _Ejecutable(_contrato(("gastos", True))),
            StorageRef(bucket="", key="informes/gastos.xlsx"),
        )

        assert ficheros == {"gastos": "informes/gastos.xlsx"}, (
            "El fichero del bloque no llega al slot que la función declara. Antes esto "
            "devolvía {} siempre y la validación fallaba con «falta el slot gastos»."
        )

    def test_sin_fichero_no_se_inventa_ninguno(self) -> None:
        from server.app.modules.redaccion.graph.nodes.deterministic_extraction import (
            _ficheros_del_bloque,
        )

        assert _ficheros_del_bloque(_Ejecutable(_contrato(("gastos", True))), None) == {}

    def test_con_varios_slots_no_se_adivina(self) -> None:
        """Meter el fichero en el primero que aparezca es peor que fallar: da un resultado."""
        from server.app.modules.redaccion.graph.nodes.deterministic_extraction import (
            SlotAmbiguo,
            _ficheros_del_bloque,
        )
        from server.app.modules.redaccion.pipelines.contracts import StorageRef

        with pytest.raises(SlotAmbiguo, match="gastos|plantilla"):
            _ficheros_del_bloque(
                _Ejecutable(_contrato(("gastos", True), ("plantilla", True))),
                StorageRef(bucket="", key="informes/gastos.xlsx"),
            )

    def test_un_slot_opcional_tambien_cuenta_como_el_unico(self) -> None:
        """Una función con un solo slot, opcional, sigue teniendo un solo sitio donde poner
        el fichero. Exigir `required` dejaría a esas funciones sin entrada."""
        from server.app.modules.redaccion.graph.nodes.deterministic_extraction import (
            _ficheros_del_bloque,
        )
        from server.app.modules.redaccion.pipelines.contracts import StorageRef

        ficheros = _ficheros_del_bloque(
            _Ejecutable(_contrato(("gastos", False))),
            StorageRef(bucket="", key="g.xlsx"),
        )
        assert ficheros == {"gastos": "g.xlsx"}

    def test_una_funcion_sin_slots_no_recibe_fichero(self) -> None:
        """Una función que sólo toma parámetros es legítima (lo dice `contrato_coherente`)."""
        from server.app.modules.redaccion.graph.nodes.deterministic_extraction import (
            _ficheros_del_bloque,
        )
        from server.app.modules.redaccion.pipelines.contracts import StorageRef

        assert _ficheros_del_bloque(
            _Ejecutable(_contrato()), StorageRef(bucket="", key="g.xlsx")
        ) == {}


class TestNoSeMiraDondeNoHay:
    """Los dos sitios donde el ayudante buscaba antes, y por qué no servían."""

    def test_ningun_tipo_de_bloque_declara_slot(self) -> None:
        """Si algún día lo declara, este test se pone rojo y hay que decidir cuál manda.

        `BlockContract` es una unión discriminada por `kind`, no un modelo: se recorren sus
        miembros. Buscar `model_fields` sobre el alias daba `AttributeError`, que es el tipo de
        detalle por el que un guardarraíl acaba comprobando otra cosa.
        """
        from typing import get_args

        from server.app.modules.redaccion.contracts.blocks import BlockContract

        miembros = [m for m in get_args(get_args(BlockContract)[0]) if hasattr(m, "model_fields")]
        assert miembros, "no se han reconocido los tipos de bloque: la unión ha cambiado de forma"

        con_slot = [m.__name__ for m in miembros if "slot" in m.model_fields]
        assert not con_slot, (
            f"Estos tipos de bloque declaran `slot`: {con_slot}. El ayudante lo ignora a "
            "propósito desde APER.15 —decide el contrato de la función—, así que hay que "
            "releer cuál manda."
        )

    def test_options_slot_es_del_pipeline_manual(self) -> None:
        """`options[\"slot\"]` es un **diccionario** del pipeline manual, no un nombre.

        Es la razón por la que el ayudante antiguo no encontraba nada: exigía `str`.
        """
        from pathlib import Path

        manual = (
            Path(__file__).resolve().parents[3]
            / "app" / "modules" / "redaccion" / "pipelines" / "manual_pipeline.py"
        )
        fuente = manual.read_text(encoding="utf-8")
        assert 'slot_dict: dict = inp.options.get("slot", {})' in fuente, (
            "El pipeline manual ha cambiado cómo usa `options['slot']`. Si ahora es una "
            "cadena, las dos convenciones colisionan y hay que decidir."
        )

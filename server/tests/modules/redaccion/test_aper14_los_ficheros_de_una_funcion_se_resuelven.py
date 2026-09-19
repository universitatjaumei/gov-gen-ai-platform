"""APER.14 — una función no abre la ruta que le den: la plataforma resuelve la referencia.

**El defecto, encontrado por la revisión automática de la PR del despliegue y comprobado a mano.**
`EjecutarRequest.ficheros` se documenta como «rutas o claves, **no contenido**: el fichero ya está
en el almacenamiento de la organización». Pero nada resolvía esas cadenas: `validar_entrada`
comprueba los **nombres** de los slots y nunca los valores, y `ejecutar_empaquetada` se las pasaba
tal cual al `run` del paquete, que hacía `openpyxl.load_workbook(entrada.ficheros["gastos"])`.

Dos consecuencias, y la segunda es la que importa:

1. Con `STORAGE_BACKEND=gcs` una clave de GCS **no se puede abrir como ruta local**, así que las
   funciones empaquetadas no funcionarían en el despliegue real.
2. Con el backend de ficheros, quien tenga un PAT con `funciones:execute` podía pasar **cualquier
   ruta del servidor** y el paquete la abría — **en proceso**, sin el contenedor endurecido que sí
   acota la rama de autoservicio. Es un *delegado confundido*: el llamante pone la ruta y un
   paquete de confianza la abre.

**Lo que NO se pretende arreglar aquí, dicho para que nadie lo suponga.** Un paquete corre
in-process y sin aislamiento —`docs/CATALOGO_FUNCIONES.md` lo dice sin rodeos— así que puede
llamar a `open()` con lo que quiera. Ninguna API lo impide y ésta tampoco. Lo que se cierra es que
**la plataforma** le entregue una ruta elegida por quien llama.

Y por eso hay una tercera pieza que parecía ajena: `StorageService._full_path` concatenaba
`bucket/key` sin mirar la clave, así que resolver por él **tampoco bastaba** — un `../../etc/passwd`
se sale del bucket igual. Se valida la clave ahí, donde protege a todo el que la use y no sólo a
las funciones.
"""

from __future__ import annotations

import pytest


class TestLaClaveNoSeSaleDelBucket:
    """`StorageService` valida la clave. Es el arreglo que protege a cualquier llamante."""

    @pytest.mark.parametrize(
        "clave",
        [
            "../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:/Users/fabra/Documents/AI_agents_hub/server/.env",
            "ingestion/../../../secreto",
            "a/./../../b",
        ],
    )
    def test_una_clave_que_escapa_se_rechaza(self, clave: str) -> None:
        from server.app.core.storage import ClaveNoValida, validar_clave

        with pytest.raises(ClaveNoValida):
            validar_clave(clave)

    @pytest.mark.parametrize(
        "clave",
        ["ingestion/job.pdf", "informes/2026/enero.xlsx", "un-fichero.txt"],
    )
    def test_una_clave_normal_pasa(self, clave: str) -> None:
        from server.app.core.storage import validar_clave

        assert validar_clave(clave) == clave

    def test_el_servicio_la_usa_al_resolver(self) -> None:
        """De nada vale el validador si `_full_path` no lo llama."""
        from server.app.core.storage import ClaveNoValida, FsspecStorageService

        servicio = FsspecStorageService(backend="file", bucket="/tmp/govgenai-test")
        with pytest.raises(ClaveNoValida):
            servicio._full_path("../../etc/passwd")


class TestLaFuncionRecibeUnaRutaQueAbrioLaPlataforma:
    """El contrato nuevo de `run`: `with entrada.fichero(slot) as ruta`."""

    @staticmethod
    def _almacen(contenido: dict[str, bytes]):
        """Un `StorageService` de mentira, con lo que el contrato necesita."""

        class _Almacen:
            def __init__(self) -> None:
                self.pedidas: list[str] = []

            async def get(self, key: str) -> bytes:
                from server.app.core.storage import validar_clave

                validar_clave(key)
                self.pedidas.append(key)
                if key not in contenido:
                    raise FileNotFoundError(key)
                return contenido[key]

            async def put(self, key: str, data: bytes) -> None: ...
            async def delete(self, key: str) -> None: ...
            async def exists(self, key: str) -> bool:
                return key in contenido

        return _Almacen()

    async def test_entrega_una_ruta_local_con_el_contenido_del_almacen(self) -> None:
        from server.app.modules.redaccion.contracts.funciones import EntradaValidada

        almacen = self._almacen({"informes/gastos.xlsx": b"CONTENIDO-REAL"})
        entrada = EntradaValidada(
            ficheros={"gastos": "informes/gastos.xlsx"}, almacen=almacen
        )

        async with entrada.fichero("gastos") as ruta:
            assert ruta.read_bytes() == b"CONTENIDO-REAL"

        assert almacen.pedidas == ["informes/gastos.xlsx"]

    async def test_borra_el_temporal_al_salir(self) -> None:
        """Cloud Run no garantiza disco entre peticiones, y un temporal que no se borra es una
        copia del documento de un cliente esperando a que alguien la encuentre."""
        from server.app.modules.redaccion.contracts.funciones import EntradaValidada

        entrada = EntradaValidada(
            ficheros={"gastos": "informes/gastos.xlsx"},
            almacen=self._almacen({"informes/gastos.xlsx": b"x"}),
        )

        async with entrada.fichero("gastos") as ruta:
            guardada = ruta
            assert guardada.exists()

        assert not guardada.exists(), "el temporal sobrevivió al bloque"

    async def test_una_ruta_del_servidor_no_se_abre(self) -> None:
        """El defecto original, en una línea: la referencia la pone quien llama."""
        from server.app.core.storage import ClaveNoValida
        from server.app.modules.redaccion.contracts.funciones import EntradaValidada

        entrada = EntradaValidada(
            ficheros={"gastos": "../../../server/.env"}, almacen=self._almacen({})
        )

        with pytest.raises(ClaveNoValida):
            async with entrada.fichero("gastos"):
                pass

    async def test_un_slot_que_no_esta_lo_dice(self) -> None:
        from server.app.modules.redaccion.contracts.funciones import EntradaValidada

        entrada = EntradaValidada(ficheros={}, almacen=self._almacen({}))
        with pytest.raises(KeyError, match="gastos"):
            async with entrada.fichero("gastos"):
                pass

    async def test_sin_almacen_no_se_finge_que_hay_fichero(self) -> None:
        """Construir la entrada a mano —en un test de un paquete, por ejemplo— y llamar a
        `fichero()` sin almacén tiene que decir qué falta, no dar un error de atributo."""
        from server.app.modules.redaccion.contracts.funciones import EntradaValidada

        entrada = EntradaValidada(ficheros={"gastos": "x.xlsx"})
        with pytest.raises(RuntimeError, match="almacenamiento"):
            async with entrada.fichero("gastos"):
                pass


class TestLaReferenciaSigueSiendoLaReferencia:
    """`ficheros` conserva lo que pidió el llamante, y eso es lo que va a la procedencia."""

    async def test_ficheros_guarda_la_clave_y_no_el_temporal(self) -> None:
        from server.app.modules.redaccion.contracts.funciones import EntradaValidada

        entrada = EntradaValidada(
            ficheros={"gastos": "informes/gastos.xlsx"},
            almacen=TestLaFuncionRecibeUnaRutaQueAbrioLaPlataforma._almacen(
                {"informes/gastos.xlsx": b"x"}
            ),
        )
        async with entrada.fichero("gastos"):
            pass

        assert entrada.ficheros["gastos"] == "informes/gastos.xlsx", (
            "La procedencia de un informe cita la referencia del almacén, no una ruta "
            "temporal que no existirá cuando alguien lea el informe meses después."
        )


class TestElPaqueteDeEjemploUsaElContratoNuevo:
    """El ejemplo del catálogo es lo que copia el primer equipo. Si abre una ruta, todos lo harán."""

    def test_el_demo_no_abre_ficheros_por_su_cuenta(self) -> None:
        from pathlib import Path

        demo = (
            Path(__file__).resolve().parents[2]
            / "fixtures" / "paquete_funcion_demo" / "paquete_funcion_demo" / "__init__.py"
        )
        fuente = demo.read_text(encoding="utf-8")

        # Se mira el **código**, no la prosa: el comentario que explica el cambio cita la forma
        # antigua a propósito, y un test que no distingue las dos cosas se pone rojo por una
        # explicación bien escrita. Mismo tropiezo que el guardarraíl de FUN.7.
        codigo = "\n".join(
            linea for linea in fuente.splitlines() if not linea.lstrip().startswith("#")
        )

        assert "entrada.fichero(" in codigo, (
            "El paquete de ejemplo no usa `entrada.fichero(slot)`. Es el código que copia quien "
            "escribe el primero."
        )
        assert "load_workbook(entrada.ficheros[" not in codigo, (
            "El ejemplo sigue abriendo la referencia como si fuera una ruta local."
        )

"""APER.25 — materializar el fichero de un slot no bloquea el bucle de eventos.

`EntradaValidada.fichero()` es un gestor de contexto **asíncrono** y corre en la ruta de una
petición, pero por dentro hacía tres operaciones de disco **síncronas**: crear el temporal,
`write_bytes` del contenido descargado y `shutil.rmtree` al salir. Mientras cualquiera de ellas
trabaja, el bucle no atiende a nadie más, y el tamaño lo pone el documento que suba el cliente.

Choca con una regla dura de `AGENTS.md` —«asincronía total: prohibidos métodos síncronos para
I/O en el servidor»— y es de las que no dan síntoma en un test: en un fichero de prueba de dos
kilobytes no se nota nada. Lo encontró la revisión automática de la PR #50 leyendo el diff de
APER.14, que fue quien introdujo el método.

Lo mismo le pasaba al paquete de demostración, que llama a `openpyxl.load_workbook` dentro del
bloque: ahí el arreglo importa el doble porque es **el ejemplo que copia quien escribe una
función nueva**.

**Cómo se comprueba, y por qué así.** No se mira si el fichero fuente dice `asyncio.to_thread`,
que sería otro guardarraíl de los que no ejecutan nada. Se sustituye `asyncio.to_thread` por un
envoltorio que apunta lo que pasa por él y delega, y después se mira si el trabajo de disco pasó
por ahí. Eso observa el camino de llamada de verdad.
"""

from __future__ import annotations

import asyncio

import pytest

from server.app.modules.redaccion.contracts.funciones import EntradaValidada


class AlmacenDoble:
    """Lo mínimo que `fichero()` usa del almacenamiento."""

    def __init__(self, contenido: bytes) -> None:
        self.contenido = contenido
        self.pedidos: list[str] = []

    async def get(self, clave: str) -> bytes:
        self.pedidos.append(clave)
        return self.contenido


@pytest.fixture
def espia_de_hilos(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Apunta qué funciones se han mandado a un hilo, y las ejecuta igual."""
    pasaron: list[str] = []
    original = asyncio.to_thread

    async def _envoltorio(funcion, /, *args, **kwargs):
        pasaron.append(getattr(funcion, "__name__", type(funcion).__name__))
        return await original(funcion, *args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", _envoltorio)
    return pasaron


@pytest.mark.asyncio
async def test_el_contenido_llega_entero_y_con_su_extension() -> None:
    """El camino bueno primero: lo que este método tiene que hacer, sigue haciéndolo."""
    almacen = AlmacenDoble(b"unas cuantas filas")
    entrada = EntradaValidada(
        ficheros={"gastos": "organizacion/7/gastos-2026.xlsx"}, almacen=almacen
    )

    async with entrada.fichero("gastos") as ruta:
        assert ruta.read_bytes() == b"unas cuantas filas"
        assert ruta.suffix == ".xlsx", (
            "se pierde la extensión, y muchas bibliotecas deciden el formato por ella"
        )
        guardada = ruta

    assert not guardada.exists(), "el temporal sobrevive al bloque"
    assert not guardada.parent.exists(), "el directorio temporal sobrevive al bloque"
    assert almacen.pedidos == ["organizacion/7/gastos-2026.xlsx"]


@pytest.mark.asyncio
async def test_escribir_el_temporal_va_a_un_hilo(espia_de_hilos: list[str]) -> None:
    entrada = EntradaValidada(
        ficheros={"gastos": "clave.xlsx"}, almacen=AlmacenDoble(b"x" * 4096)
    )
    async with entrada.fichero("gastos"):
        pass

    assert espia_de_hilos, (
        "ni una sola operación de disco pasó por `asyncio.to_thread`: crear el temporal y "
        "escribir el contenido descargado bloquean el bucle mientras duran, y el tamaño lo "
        "decide el documento que suba el cliente."
    )


@pytest.mark.asyncio
async def test_el_borrado_tambien_va_a_un_hilo(espia_de_hilos: list[str]) -> None:
    """El `finally` cuenta igual: borrar un árbol de ficheros también es trabajo de disco."""
    entrada = EntradaValidada(
        ficheros={"gastos": "clave.xlsx"}, almacen=AlmacenDoble(b"x" * 4096)
    )
    async with entrada.fichero("gastos"):
        durante = list(espia_de_hilos)

    despues = espia_de_hilos[len(durante):]
    assert despues, (
        "la limpieza al salir del bloque no pasó por un hilo. `shutil.rmtree` borra un "
        "directorio entero de forma síncrona, y está en el `finally`, o sea que corre siempre."
    )


@pytest.mark.asyncio
async def test_el_bucle_sigue_atendiendo_mientras_se_materializa() -> None:
    """Lo mismo visto desde fuera: otra tarea tiene que poder avanzar mientras tanto.

    No se mide tiempo —eso sería inestable en cualquier máquina— sino que una tarea concurrente
    consiga ejecutarse al menos una vez mientras el bloque está abierto.
    """
    entrada = EntradaValidada(
        ficheros={"gastos": "clave.xlsx"}, almacen=AlmacenDoble(b"y" * 1_000_000)
    )
    vueltas = 0

    async def testigo() -> None:
        nonlocal vueltas
        while True:
            vueltas += 1
            await asyncio.sleep(0)

    tarea = asyncio.create_task(testigo())
    try:
        async with entrada.fichero("gastos") as ruta:
            assert ruta.stat().st_size == 1_000_000
    finally:
        tarea.cancel()

    assert vueltas > 0, "ninguna otra tarea pudo avanzar durante la materialización"

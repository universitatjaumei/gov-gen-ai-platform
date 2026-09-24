"""Issue #14 — detectar los enlaces de cita que no llevan a ninguna parte.

**Qué se detecta, y por qué importa más que un 404 normal.** Una cita sin enlace verificable
obliga a creerse al asistente, que es justo lo que el proyecto no quiere: el fundamento existe
para poder contrastarlo. Un enlace muerto **es peor que no citar**, porque aparenta verificación.

**Dos formas de estar muerto, y las dos cuentan.** Que la página no responda es la obvia. La otra
es más traicionera: la página responde 200 y el **ancla no existe** en ella, así que el lector
aterriza en la cabecera del documento convencido de estar leyendo el artículo citado. Nada falla,
nadie ve un error, y la cita miente. Es la misma familia que la issue #15, por el otro extremo:
allí componíamos el ancla sobre un destino que no podía servirla; aquí se comprueba contra lo que
el sitio sirve de verdad.

**Por qué el acceso HTTP se inyecta.** Un test que salga a la red no es un test: es una medición
del estado de un servidor ajeno en el instante en que corre, y falla los días que el sitio va
lento o el corpus se está republicando. Lo que aquí se fija es la **lógica del veredicto** —qué
cuenta como muerto— y eso no necesita red. La red la pone el CLI, que es manual y nocturno, nunca
un gate de CI. Es el mismo reparto que `retrieval_metrics` (puro, en CI) frente a `run_golden`
(real, a mano).

**Y no lee ninguna conversación.** La issue encontró los cuatro enlaces auditando conversaciones
guardadas, que fue un buen método de diagnóstico. Para la comprobación permanente no hacen falta:
los enlaces salen de `hub_documents`, y las consultas de los ciudadanos no tienen por qué pasar
por aquí. Detectar lo mismo sin tocar datos personales es preferible aunque cueste lo mismo.
"""

from __future__ import annotations

from server.app.modules.agents_hub.evaluation.verificar_enlaces import (
    Hallazgo,
    comprobar_enlaces,
)


def _fetch_de(respuestas: dict[str, tuple[int, str]]):
    """Un acceso HTTP falso: devuelve lo que diga el diccionario, 599 si no lo conoce."""

    async def fetch(url: str) -> tuple[int, str]:
        return respuestas.get(url, (599, ""))

    return fetch


class TestLoQueCuentaComoMuerto:

    async def test_una_url_que_responde_200_sin_ancla_esta_viva(self):
        fetch = _fetch_de({"https://x.es/a.html": (200, "<h1>Norma</h1>")})

        assert await comprobar_enlaces(["https://x.es/a.html"], fetch) == []

    async def test_una_url_que_no_responde_200_esta_muerta(self):
        fetch = _fetch_de({"https://x.es/a.html": (404, "")})

        hallazgos = await comprobar_enlaces(["https://x.es/a.html"], fetch)

        assert hallazgos == [Hallazgo("https://x.es/a.html", "no_resuelve", "404")]

    async def test_un_ancla_que_no_esta_en_la_pagina_esta_muerta(self):
        """La página existe y el ancla no. El lector aterriza en la cabecera sin saberlo."""
        fetch = _fetch_de({"https://x.es/a.html": (200, '<h2 id="art-1">U</h2>')})

        hallazgos = await comprobar_enlaces(["https://x.es/a.html#art-9"], fetch)

        assert [h.motivo for h in hallazgos] == ["ancla_ausente"]
        assert "art-9" in hallazgos[0].detalle

    async def test_un_ancla_que_si_esta_no_se_reporta(self):
        fetch = _fetch_de({"https://x.es/a.html": (200, '<h2 id="art-9">U</h2>')})

        assert await comprobar_enlaces(["https://x.es/a.html#art-9"], fetch) == []

    async def test_el_ancla_vale_tambien_como_atributo_name(self):
        """El corpus publicado no siempre usa `id`; los anclajes antiguos van con `name`."""
        fetch = _fetch_de({"https://x.es/a.html": (200, '<a name="art-9"></a>')})

        assert await comprobar_enlaces(["https://x.es/a.html#art-9"], fetch) == []


class TestElMedidorNoMienteSolo:

    async def test_la_pagina_se_pide_una_sola_vez_por_documento(self):
        """Dos anclas del mismo documento no son dos descargas.

        No es sólo eficiencia: el corpus tiene cientos de fragmentos por norma, y pedir la misma
        página una vez por fragmento convierte una comprobación en algo parecido a un ataque
        contra el propio sitio.
        """
        pedidas: list[str] = []

        async def fetch(url: str) -> tuple[int, str]:
            pedidas.append(url)
            return (200, '<h2 id="art-1">a</h2><h2 id="art-2">b</h2>')

        await comprobar_enlaces(
            ["https://x.es/a.html#art-1", "https://x.es/a.html#art-2"], fetch
        )

        assert pedidas == ["https://x.es/a.html"]

    async def test_un_fallo_de_red_no_se_lee_como_pagina_viva(self):
        """Si la petición revienta, eso **no** es «está bien». Es un hallazgo con su motivo."""

        async def fetch(url: str) -> tuple[int, str]:
            raise TimeoutError("se acabó el tiempo")

        hallazgos = await comprobar_enlaces(["https://x.es/a.html"], fetch)

        assert [h.motivo for h in hallazgos] == ["no_resuelve"]
        assert "TimeoutError" in hallazgos[0].detalle

    async def test_sin_urls_no_hay_hallazgos_y_tampoco_peticiones(self):
        async def fetch(url: str) -> tuple[int, str]:  # pragma: no cover
            raise AssertionError("no debería pedirse nada")

        assert await comprobar_enlaces([], fetch) == []


class TestElCliNoSeCuelaEnCI:

    def test_el_modulo_no_sale_a_la_red_al_importarse(self):
        """Importarlo tiene que ser gratis: la red la pone quien ejecuta el CLI, no el import."""
        import server.app.modules.agents_hub.evaluation.verificar_enlaces as mod

        fuente = __import__("pathlib").Path(mod.__file__).read_text(encoding="utf-8")
        assert "httpx" not in fuente.split("def _fetch_real")[0], (
            "el módulo importa el cliente HTTP en el nivel superior. Se importa dentro de la "
            "función que lo usa, para que la lógica del veredicto —que es lo que corre en CI— "
            "no arrastre la red."
        )


# Aquí hubo una *fixture* que prohibía abrir cualquier socket, para demostrar que estos tests no
# salen a la red. **Rompía los tests que protegía**: en Windows el bucle de asyncio abre un socket
# interno para despertarse a sí mismo, así que la guarda mataba a todo lo asíncrono antes de que
# empezara.
#
# Lo que garantiza que no hay red es más simple y no necesita guarda: `comprobar_enlaces` recibe
# el acceso HTTP como argumento y estos tests le pasan un diccionario. El único sitio por donde
# podría colarse la red es un import del cliente en el nivel superior del módulo, y eso lo vigila
# `TestElCliNoSeCuelaEnCI`.

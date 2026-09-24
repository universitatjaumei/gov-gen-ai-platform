"""Issue #148 — leer las citas de una respuesta cuesta tiempo lineal, no cuadrático.

**Qué pasaba.** Las dos expresiones que definen qué cuenta como cita tenían retroceso cuadrático:

    _MD_LINK             = r"\\[([^\\]]+)\\]\\(([^)]+)\\)"
    _CORCHETE_SIN_ENLACE = r"\\[([^\\]\\n]+)\\](?!\\()"

El motor arranca en cada `[` del texto y, si no encuentra el cierre, escanea hasta el final. Con
*m* corchetes sobre *n* caracteres eso es O(n·m). Lo señaló CodeQL (`py/polynomial-redos`) en
cinco puntos, que son los cinco usos de estas dos expresiones.

**Medido antes de tocar nada, sobre un texto de sólo corchetes:**

    n=4.000    88 ms  ·  127 ms
    n=16.000  1.358 ms  ·  5.216 ms
    n=64.000  32.671 ms  ·  68.225 ms      ← 32 y 68 SEGUNDOS

Doblar la entrada multiplica el tiempo por cuatro, que es la firma del coste cuadrático.

**El arreglo es acotar lo que puede casar**, no reescribir la expresión. Un título de cita de más
de 500 caracteres no es un título, y una URL de más de 2.048 no cabe en `source_url`, que es
`String(2048)`. Con el límite, el escaneo interior deja de ser proporcional al texto:

    n=64.000   515 ms  ·  898 ms           ← 64 y 76 veces más rápido

**Qué cambia y qué no.** Sobre texto realista los resultados son idénticos —se comprobó—. Lo que
cambia es el borde: un enlace cuyo título pase de 500 caracteres deja de reconocerse como cita, y
el contrato lo tratará como si no la hubiera. Es un intercambio consciente: ese enlace no existe
en ninguna respuesta real, y el coste de no acotarlo es que una respuesta larga con muchos
corchetes bloquee el proceso durante segundos.

**Por qué importaba poco y aun así se hace.** La entrada es la salida del modelo, acotada por el
límite de *tokens*: nadie la controla lo bastante para convertir esto en una denegación de
servicio. Lo que lo hace razonable es que estas dos expresiones son **la definición de qué cuenta
como cita en todo el proyecto** —`citas_de()` existe para que nadie escriba una tercera— y un
coste cuadrático escondido ahí se paga el día que cambia otra cosa: un corpus con documentos más
largos, un límite de *tokens* mayor, un modelo más verboso.
"""

from __future__ import annotations

import time

from server.app.modules.agents_hub.agent.citation_validator import (
    _CORCHETE_SIN_ENLACE,
    _MD_LINK,
    citas_de,
)

#: Un texto patológico: todo corchetes sin cerrar, que es el peor caso de las dos expresiones.
#: 32.000 caracteres es menos de lo que cabe en una respuesta larga del modelo.
_PATOLOGICO = "[" * 32_000

#: Con la versión acotada esto tarda ~0,25 s; con la cuadrática, unos 8. El techo va muy holgado
#: —treinta veces el tiempo esperado— porque un runner cargado puede ir lento y un test que mide
#: tiempo y falla por eso se acaba borrando. Aun así deja fuera el comportamiento cuadrático por
#: un orden de magnitud.
_TECHO_SEGUNDOS = 5.0


class TestElCosteEsLineal:

    def test_md_link_no_se_atasca_con_corchetes_sin_cerrar(self):
        inicio = time.perf_counter()
        _MD_LINK.findall(_PATOLOGICO)
        tardo = time.perf_counter() - inicio

        assert tardo < _TECHO_SEGUNDOS, (
            f"`_MD_LINK` ha tardado {tardo:.2f}s sobre {len(_PATOLOGICO)} caracteres. Con el "
            f"límite puesto tarda ~0,25s; sin él, unos 8. Si alguien quitó la acotación, el "
            f"coste ha vuelto a ser cuadrático y una respuesta larga bloquea el proceso."
        )

    def test_el_corchete_sin_enlace_tampoco(self):
        inicio = time.perf_counter()
        _CORCHETE_SIN_ENLACE.findall(_PATOLOGICO)
        tardo = time.perf_counter() - inicio

        assert tardo < _TECHO_SEGUNDOS, (
            f"`_CORCHETE_SIN_ENLACE` ha tardado {tardo:.2f}s. Es la peor de las dos: sin acotar "
            f"tardaba 68 segundos sobre 64.000 caracteres."
        )

    def test_el_medidor_mide_algo(self):
        """Si el texto patológico dejara de serlo, los dos test de arriba pasarían sin mérito."""
        assert len(_PATOLOGICO) >= 32_000
        assert "]" not in _PATOLOGICO, (
            "el texto de prueba tiene cierres, así que el motor no llega al peor caso y estos "
            "test estarían midiendo una ejecución fácil"
        )


class TestLoQueSeReconoceNoCambia:

    def test_una_cita_normal_se_sigue_leyendo(self):
        texto = (
            "Veure [Directrius, art. 3](https://uji.es/d.html#art-3) i "
            "[Instruccio 2/2016](https://uji.es/i.html)."
        )
        assert citas_de(texto) == [
            ("Directrius, art. 3", "https://uji.es/d.html#art-3"),
            ("Instruccio 2/2016", "https://uji.es/i.html"),
        ]

    def test_un_titulo_largo_pero_razonable_sigue_valiendo(self):
        """El límite tiene que dejar pasar cualquier título que exista de verdad.

        400 caracteres es más de lo que ocupa el título completo de una norma con su fecha y su
        órgano, que es el caso más largo que produce el corpus.
        """
        titulo = "A" * 400
        texto = f"[{titulo}](https://uji.es/x.html)"

        assert citas_de(texto) == [(titulo, "https://uji.es/x.html")]

    def test_un_titulo_absurdo_deja_de_contar_como_cita(self):
        """Y el borde se fija a propósito, para que el intercambio esté escrito.

        Un enlace con un título de 600 caracteres no aparece en ninguna respuesta real. Si
        apareciera, el contrato lo trataría como si no hubiera cita — que es el precio de que
        leer las citas no cueste tiempo cuadrático.
        """
        texto = f"[{'A' * 600}](https://uji.es/x.html)"

        assert citas_de(texto) == []

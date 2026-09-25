"""Issue #158 — detectar los artículos del corpus que la norma ya no tiene.

**Por qué esto es peor que un enlace roto.** Un enlace muerto se ve: se pincha y no lleva a
ninguna parte. Una respuesta fundada en un artículo derogado **es correcta en su forma** —cita una
fuente real, de la norma correcta, con su número— y es falsa en su contenido. El lector no tiene
forma de notarlo y el sistema no lo detecta con ninguna otra comprobación.

**Lo medido el 2026-09-25**: 19 preceptos del corpus están derogados. En 8 el corpus lo dice —el
texto lleva «(Suprimido)» y la norma que lo suprimió—; en los otros **12** guarda el articulado
original íntegro, sin una sola marca, con el aspecto de norma vigente. Son 243 fragmentos
recuperables, concentrados en dos reglamentos: arts. 114-117 del RD 1098/2001 (derogados en 2009) y
arts. 35-41 del RD 887/2006 (derogados en 2019), más la disposición adicional tercera de la Ley
2/2003. Esa última la encontró el detector y no la medición a mano, que sólo cruzaba artículos.

**La causa es de conversión, no de la plataforma.** El XML consolidado del BOE mata un precepto de
dos maneras: dejando una `<version>` nueva cuyo texto es «(Suprimido)», o **caducando el bloque
entero** con `fecha_caducidad`. El convertidor del corpus elige la versión en vigor *dentro* de
cada bloque y nunca mira el atributo del bloque, así que la primera forma la ve y la segunda no.

**Por qué hace falta este detector aunque el convertidor se arregle.** Porque el fallo **no produce
ningún error**: el artículo derogado se recupera, se cita y se responde exactamente igual que uno
vigente. Sin una comprobación que lo mire a propósito, la próxima vez que el BOE caduque un bloque
nadie se enterará. Es la misma razón por la que existe `verificar_enlaces.py`, y el mismo reparto:
la lógica del veredicto es determinista y corre en CI; la red la pone el CLI.

**Y no se deduce nada de las anclas**, que es la trampa en la que cayó la issue #152: el ancla del
BOE no se puede calcular desde el número de artículo. Aquí se cruzan dos cadenas escritas por el
BOE —el encabezado que el corpus guarda y el `titulo` del bloque del XML—, normalizadas igual.
"""

from __future__ import annotations

from datetime import date

from server.app.modules.agents_hub.evaluation.detectar_derogados import (
    Derogado,
    Precepto,
    bloques_caducados,
    cruzar,
    designacion,
)

HOY = date(2026, 9, 25)


class TestLaDesignacionSaleDelEncabezado:
    """La clave del cruce es la designación, y es lo único que ambos lados comparten."""

    def test_un_articulo_se_reduce_a_su_designacion(self):
        assert designacion("Artículo 35. Ámbito objetivo") == "articulo 35"

    def test_una_disposicion_tambien(self):
        """Las disposiciones cuentan: también se derogan, y el corpus tiene 2.192 anclas de
        disposición frente a 9.192 de artículo."""
        assert (
            designacion("Disposición adicional primera. Régimen jurídico de los convenios")
            == "disposicion adicional primera"
        )

    def test_el_espacio_duro_no_crea_una_designacion_distinta(self):
        """El BOE escribe `Artículo\xa035` en unas normas y `Artículo 35` en otras. Si no se
        normaliza, media biblioteca deja de cruzar y el informe da cero sin dar error."""
        assert designacion("Artículo\xa035") == designacion("Artículo 35")

    def test_sin_espacio_ninguno_tambien_cruza(self):
        """El corpus guarda `Artículo1. Objeto de la Ley` —**sin espacio**— en la Ley 39/2015 y en
        la Ley 40/2015: el convertidor borró el espacio duro en vez de sustituirlo.

        Lo caza este detector el 2026-09-25, y sólo porque lleva la cuenta de las designaciones
        que no consigue leer: eran 292 de esas dos leyes. Si no la llevara, el cruce habría dado
        cero para ambas —es decir, «ningún artículo derogado»— sin fallar ni una vez.

        Aquí se tolera para que el cruce no mienta. El encabezado mal formado es un defecto del
        convertidor y se arregla allí.
        """
        assert designacion("Artículo1. Objeto de la Ley") == designacion("Artículo 1. Objeto")

    def test_sin_titulo_tras_el_numero_tambien_vale(self):
        """El XML titula el bloque `Artículo 35` a secas; el corpus guarda `Artículo 35. Ámbito`."""
        assert designacion("Artículo 35") == designacion("Artículo 35. Ámbito objetivo")

    def test_lo_que_no_es_un_precepto_no_se_inventa_designacion(self):
        assert designacion("CAPÍTULO III. Disposiciones comunes") is None
        assert designacion("") is None


class TestQueCuentaComoCaducado:

    def _xml(self, atributos: str) -> str:
        return (
            f'<documento><texto><bloque id="a35" tipo="precepto" {atributos}>'
            f'<version fecha_vigencia="20061025"><p>x</p></version>'
            f"</bloque></texto></documento>"
        )

    def test_un_bloque_con_caducidad_pasada_esta_caducado(self):
        caducados, _, _ = bloques_caducados(
            self._xml('fecha_caducidad="20190330" titulo="Artículo 35"'), HOY
        )

        assert caducados == {"articulo 35": "2019-03-30"}

    def test_una_caducidad_futura_no_cuenta(self):
        """Un bloque puede tener fecha de caducidad anunciada y seguir en vigor hoy. Contarlo
        daría por derogado lo que rige, que es el error simétrico y igual de caro."""
        caducados, _, _ = bloques_caducados(
            self._xml('fecha_caducidad="20991231" titulo="Artículo 35"'), HOY
        )

        assert caducados == {}

    def test_sin_el_atributo_no_hay_caducidad(self):
        caducados, _, _ = bloques_caducados(self._xml('titulo="Artículo 35"'), HOY)

        assert caducados == {}

    def test_una_designacion_que_tambien_tiene_bloque_vivo_es_una_sustitucion(self):
        """Dos bloques con el mismo título y uno vivo significa **reemplazo**, no derogación.

        Pasa de verdad: la Ley 47/2003 tiene `dfquinta` (caducado el 2020-12-31) y `df`, vivo,
        los dos titulados «Disposición final quinta». Sin esta regla el detector diría que una
        disposición **en vigor** está derogada, que es el error caro: le dice a un jurista que
        desatienda derecho vigente.

        No se descarta en silencio, se devuelve aparte: el corpus tiene dos anclas para esa
        designación y una de las dos sí guarda el texto muerto. Eso lo resuelve una persona.
        """
        xml = (
            '<documento><texto>'
            '<bloque id="dfquinta" tipo="precepto" fecha_caducidad="20201231" '
            'titulo="Disposición final quinta"><version/></bloque>'
            '<bloque id="df" tipo="precepto" titulo="Disposición final quinta ">'
            "<version/></bloque>"
            "</texto></documento>"
        )

        caducados, _, sustituidas = bloques_caducados(xml, HOY)

        assert caducados == {}
        assert sustituidas == {"disposicion final quinta": "2020-12-31"}

    def test_un_bloque_que_no_es_precepto_no_se_mira(self):
        xml = (
            '<documento><texto><bloque id="ti" tipo="encabezado" fecha_caducidad="20190330" '
            'titulo="TÍTULO I"><version fecha_vigencia="20061025"><p>x</p></version>'
            "</bloque></texto></documento>"
        )

        caducados, _, _ = bloques_caducados(xml, HOY)

        assert caducados == {}


class TestElMedidorNoPuedeCallar:
    """Un medidor mal emparejado no da error: da cero hallazgos, que es la cifra cómoda.

    Es exactamente lo que pasó el 2026-09-25 con `verificar_enlaces.py` cuando le faltaba
    `CORPUS_SITE_BASE_URL`: midió un sistema que no existía y dio un resultado pequeño y creíble.
    Aquí el riesgo equivalente es que los encabezados del corpus y los títulos del XML dejen de
    normalizar igual —basta con que el BOE cambie el espacio duro por otra cosa— y el cruce
    devuelva vacío para siempre.
    """

    def test_los_bloques_con_titulo_ilegible_se_cuentan_aparte(self):
        xml = (
            '<documento><texto>'
            '<bloque id="a35" tipo="precepto" fecha_caducidad="20190330" titulo="Artículo 35">'
            "<version/></bloque>"
            '<bloque id="au" tipo="precepto" fecha_caducidad="20190330" titulo="Artículo único">'
            "<version/></bloque>"
            "</texto></documento>"
        )

        caducados, sin_designacion, _ = bloques_caducados(xml, HOY)

        assert caducados == {"articulo 35": "2019-03-30"}
        assert sin_designacion == ["Artículo único"]

    def test_los_preceptos_del_corpus_sin_designacion_se_cuentan_aparte(self):
        preceptos = [
            Precepto("Artículo 35. Ámbito objetivo", "art-35", 7),
            Precepto("CAPÍTULO III", "cap-3", 2),
        ]

        _, sin_designacion = cruzar(preceptos, {"articulo 35": "2019-03-30"})

        assert sin_designacion == ["CAPÍTULO III"]


class TestElCruce:

    def test_un_precepto_caducado_es_un_hallazgo_con_su_fecha(self):
        preceptos = [Precepto("Artículo 35. Ámbito objetivo", "art-35", 7)]

        hallazgos, _ = cruzar(preceptos, {"articulo 35": "2019-03-30"})

        assert hallazgos == [
            Derogado(
                designacion="articulo 35",
                encabezado="Artículo 35. Ámbito objetivo",
                ancla="art-35",
                fragmentos=7,
                caducado_el="2019-03-30",
            )
        ]

    def test_un_precepto_vigente_no_lo_es(self):
        preceptos = [Precepto("Artículo 42. Régimen general de garantías", "art-42", 3)]

        hallazgos, _ = cruzar(preceptos, {"articulo 35": "2019-03-30"})

        assert hallazgos == []

    def test_una_disposicion_caducada_tambien_se_detecta(self):
        preceptos = [Precepto("Disposición adicional primera. Régimen", "da-1", 2)]

        hallazgos, _ = cruzar(preceptos, {"disposicion adicional primera": "2019-03-30"})

        assert [h.ancla for h in hallazgos] == ["da-1"]

    def test_sin_preceptos_no_hay_hallazgos(self):
        hallazgos, sin_designacion = cruzar([], {"articulo 35": "2019-03-30"})

        assert hallazgos == []
        assert sin_designacion == []


class TestElCliNoSeCuelaEnCI:

    def test_el_modulo_no_sale_a_la_red_al_importarse(self):
        """Importarlo tiene que ser gratis: la red la pone quien ejecuta el CLI, no el import.

        Es la misma guarda que `verificar_enlaces.py`, y por la misma razón: la lógica del
        veredicto corre en CI y no tiene por qué arrastrar el cliente HTTP.
        """
        import pathlib

        import server.app.modules.agents_hub.evaluation.detectar_derogados as mod

        fuente = pathlib.Path(mod.__file__).read_text(encoding="utf-8")
        assert "httpx" not in fuente.split("def _descargar_xml")[0], (
            "el módulo importa el cliente HTTP en el nivel superior. Se importa dentro de la "
            "función que lo usa."
        )

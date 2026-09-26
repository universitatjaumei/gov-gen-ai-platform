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
            == "disposicion adicional 1"
        )

    def test_el_espacio_duro_no_crea_una_designacion_distinta(self):
        """El BOE escribe `Artículo\xa035` en unas normas y `Artículo 35` en otras. Si no se
        normaliza, media biblioteca deja de cruzar y el informe da cero sin dar error."""
        assert designacion("Artículo\xa035") == designacion("Artículo 35")

    def test_sin_espacio_ninguno_tambien_cruza(self):
        """La base guarda `Artículo1. Objeto de la Ley`, **sin separador**, en la Ley 39/2015 y en
        la Ley 40/2015.

        El `.md` sí lo trae: escribe `Artículo\xa01.` con espacio duro, que es como titula el BOE
        esas dos normas. Quien lo borra es **nuestra ingesta**: `MarkdownHeaderTextSplitter` filtra
        el encabezado con `str.isprintable`, y `'\xa0'.isprintable()` es `False`. Tiene issue
        aparte, porque el encabezado mutilado es lo que el modelo lee como contexto.

        Lo caza este detector el 2026-09-25, y sólo porque lleva la cuenta de las designaciones que
        no consigue leer: eran 292 de esas dos leyes. Sin esa cuenta, el cruce habría dado cero
        para ambas —es decir, «ningún artículo derogado»— sin fallar ni una vez.

        Aquí se tolera para que el cruce no mienta mientras la ingesta no se arregle.
        """
        assert designacion("Artículo1. Objeto de la Ley") == designacion("Artículo 1. Objeto")

    def test_sin_titulo_tras_el_numero_tambien_vale(self):
        """El XML titula el bloque `Artículo 35` a secas; el corpus guarda `Artículo 35. Ámbito`."""
        assert designacion("Artículo 35") == designacion("Artículo 35. Ámbito objetivo")

    def test_lo_que_no_es_un_precepto_no_se_inventa_designacion(self):
        assert designacion("CAPÍTULO III. Disposiciones comunes") is None
        assert designacion("") is None


class TestLosOrdinalesCompuestos:
    """Las disposiciones altas se nombran con ordinales compuestos, y son la mayoría del residuo.

    **Medido el 2026-09-26**: de las 174 designaciones que el detector no sabía leer, **79 eran
    preceptos de verdad** y casi todas del mismo patrón —«vigésima primera», «trigésima novena»,
    «cuadragésima séptima»—. La Ley 9/2017 llega a la quincuagésima séptima.

    No hay que inventar nada: `converteix_boe.py` ya resuelve las **84 formas** que aparecen de
    verdad en estas normas, y esta es la misma lógica. La clave es **numérica** a propósito,
    porque el BOE escribe lo mismo de tres maneras —«vigesimoprimera», «vigésima primera» y
    «décimo primera»— y las tres tienen que dar el mismo número o el cruce se parte en dos.
    """

    def test_la_forma_partida(self):
        assert designacion("Disposición adicional vigésima primera. Contratos") == (
            "disposicion adicional 21"
        )

    def test_la_forma_junta(self):
        assert designacion("Disposición adicional vigesimoprimera") == (
            "disposicion adicional 21"
        )

    def test_las_tres_grafias_dan_lo_mismo(self):
        """Es la razón de que la clave sea un número y no el texto."""
        assert (
            designacion("Disposición adicional decimotercera")
            == designacion("Disposición adicional décima tercera")
            == designacion("Disposición adicional décimo tercera")
            == "disposicion adicional 13"
        )

    def test_las_decenas_altas(self):
        assert designacion("Disposición adicional cuadragésima séptima") == (
            "disposicion adicional 47"
        )
        assert designacion("Disposición adicional quincuagésima séptima [sic]") == (
            "disposicion adicional 57"
        )

    def test_el_bis_es_una_disposicion_distinta(self):
        """«Disposición adicional novena bis» no es la novena: tiene ancla propia."""
        assert designacion("Disposición adicional quinta bis. Infraestructuras") == (
            "disposicion adicional 5 bis"
        )
        assert designacion("Disposición adicional quinta") == "disposicion adicional 5"

    def test_sin_ordinal_es_la_unica(self):
        """«Disposición derogatoria» a secas, cuando sólo hay una, es la única — y así la ancla
        el corpus, como `dd-1`."""
        assert designacion("Disposición derogatoria") == "disposicion derogatoria 1"
        assert designacion("Disposición derogatoria única") == "disposicion derogatoria 1"

    def test_las_mayusculas_no_crean_una_designacion_distinta(self):
        assert designacion("DISPOSICIÓN TRANSITORIA") == designacion(
            "Disposición transitoria"
        )


class TestLoQueNoAplicaNoEsUnaLaguna:
    """Un preámbulo no es cobertura que falte; una disposición trigésima sí.

    **Mientras fueran en el mismo saco, el número no decía nada** — y por eso la issue #158 no se
    podía cerrar: 120 «designaciones no legibles» no permitía saber si era mucho o era cero. De
    las 174 medidas, **41 eran rótulos estructurales** que no designan ningún precepto y 54 eran
    de normas sin texto consolidado en el BOE.
    """

    def test_los_rotulos_estructurales_no_son_preceptos(self):
        from server.app.modules.agents_hub.evaluation.detectar_derogados import no_es_precepto

        for rotulo in (
            "Preámbulo",
            "SECCIÓN 1. La Carta Europea del Investigador",
            "ANEXO I. Clasificación de personal",
            "CAPÍTULO III. Disposiciones comunes",
            "TÍTULO VI. Del Registro Público",
        ):
            assert no_es_precepto(rotulo), rotulo

    def test_un_precepto_de_verdad_no_se_descarta_como_rotulo(self):
        from server.app.modules.agents_hub.evaluation.detectar_derogados import no_es_precepto

        for enc in (
            "Artículo 35. Ámbito objetivo",
            "Disposición adicional trigésima novena. Régimen de contratación",
            "Artículo 1 del anexo",
        ):
            assert not no_es_precepto(enc), enc

    def test_el_cruce_los_devuelve_separados(self):
        preceptos = [
            Precepto("Artículo 35. Ámbito objetivo", "art-35", 7),
            Precepto("Preámbulo", "preambul", 3),
            Precepto("Vaya usted a saber", "raro-1", 1),
        ]

        hallazgos, ilegibles, no_aplican = cruzar(preceptos, {"articulo 35": "2019-03-30"})

        assert [h.ancla for h in hallazgos] == ["art-35"]
        assert ilegibles == ["Vaya usted a saber"]
        assert no_aplican == ["Preámbulo"]


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
        assert sustituidas == {"disposicion final 5": "2020-12-31"}

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
            '<bloque id="n4" tipo="precepto" fecha_caducidad="20190330" titulo="Norma cuarta">'
            "<version/></bloque>"
            "</texto></documento>"
        )

        caducados, sin_designacion, _ = bloques_caducados(xml, HOY)

        # «Artículo único» ya se lee —lo pidió la revisión de la PR #168—, así que el bloque que
        # de verdad no se entiende es otro. Si se usara «Artículo único» aquí, este test estaría
        # comprobando la cuenta de ilegibles con algo que dejó de serlo.
        assert caducados == {"articulo 35": "2019-03-30", "articulo unico": "2019-03-30"}
        assert sin_designacion == ["Norma cuarta"]

    def test_los_preceptos_del_corpus_sin_designacion_se_cuentan_aparte(self):
        """Y **un rótulo de estructura no cuenta como laguna**, que es lo que se separó el
        2026-09-26: «CAPÍTULO III» no designa ningún precepto, así que no saber leerlo no es
        cobertura que falte. Lo que cuenta es lo que **parece** un precepto y no se entiende."""
        preceptos = [
            Precepto("Artículo 35. Ámbito objetivo", "art-35", 7),
            Precepto("CAPÍTULO III", "cap-3", 2),
            Precepto("Norma cuarta. De la contabilidad", "norma-4", 1),
        ]

        _, sin_designacion, no_aplican = cruzar(preceptos, {"articulo 35": "2019-03-30"})

        assert sin_designacion == ["Norma cuarta. De la contabilidad"]
        assert no_aplican == ["CAPÍTULO III"]


class TestDistingueElCasoBuenoDelMalo:
    """Un precepto derogado en el corpus no es, por sí solo, un defecto.

    **Lo enseñó la reingesta del 2026-09-25.** Antes de ella, los arts. 35-41 del RD 887/2006
    estaban en el corpus con su articulado íntegro y sin marca: 243 fragmentos que el recuperador
    no distinguía de derecho vigente. Después, los mismos artículos siguen ahí —el §5 del contrato
    **manda** conservar el encabezado y el ancla, porque quitarlos rompería enlaces publicados—
    pero con un solo fragmento que dice «(Derogado)» y su fecha.

    Y el detector daba **la misma cifra en los dos casos**: «12 preceptos». O sea que el informe
    era idéntico antes y después de arreglar el problema que el detector existe para vigilar. Un
    medidor que no separa el caso bueno del malo no sirve para vigilar nada: el día que el
    convertidor vuelva a copiar articulado muerto, dirá otra vez 12 y nadie lo notará.
    """

    def test_un_derogado_declarado_no_es_un_defecto(self):
        preceptos = [Precepto("Artículo 35. Ámbito objetivo", "art-35", 1, declarado=True)]

        hallazgos, _, _ = cruzar(preceptos, {"articulo 35": "2019-03-30"})

        assert [h.declarado for h in hallazgos] == [True]

    def test_un_derogado_sin_declarar_si_lo_es(self):
        preceptos = [Precepto("Artículo 35. Ámbito objetivo", "art-35", 7)]

        hallazgos, _, _ = cruzar(preceptos, {"articulo 35": "2019-03-30"})

        assert [h.declarado for h in hallazgos] == [False]

    def test_lo_que_no_se_declara_es_lo_que_hace_fallar_al_cli(self):
        """El código de salida tiene que hablar del defecto, no del inventario.

        Si el CLI fallara por haber preceptos derogados, fallaría para siempre —los 12 se quedan
        en el corpus a propósito— y un rojo permanente se ignora igual que un verde permanente.
        """
        from server.app.modules.agents_hub.evaluation.detectar_derogados import cuantos_sin_declarar

        todos_declarados = [
            Derogado("articulo 35", "Artículo 35", "art-35", 1, "2019-03-30", declarado=True),
            Derogado("articulo 36", "Artículo 36", "art-36", 1, "2019-03-30", declarado=True),
        ]
        assert cuantos_sin_declarar(todos_declarados) == 0

        con_uno_crudo = todos_declarados + [
            Derogado("articulo 37", "Artículo 37", "art-37", 9, "2019-03-30", declarado=False)
        ]
        assert cuantos_sin_declarar(con_uno_crudo) == 1


class TestUnaRenumeracionNoEsUnaDerogacion:
    """El caso de la d.f. quinta de la Ley 47/2003, que lo destapó leyendo la ley.

    En 2021 el BOE insertó una disposición final quinta nueva —la del Informe de Impacto de
    Género— y la de entrada en vigor, que era la quinta, pasó a **sexta**. En el XML eso es un
    bloque `dfquinta` caducado y un bloque `df` con una `<version>` nueva.

    **No hay ningún precepto derogado**: hay un número que se ha movido, y el precepto que lo
    tenía sigue vivo con otro. Leerlo como derogación hizo que el bloque muerto se quedara el
    ancla buena (`df-5`), que la disposición vigente saliera como `df-5-2`, y que encima llevara
    una nota diciendo que «el texto oficial numera esta unidad igual que una anterior», **que es
    falso**: el BOE sólo tiene una. La duplicidad la fabricaba el convertidor.

    Aquí se fija lo que el detector debe decir de eso, que depende de **cuántas anclas trae el
    corpus**: con una, el convertidor resolvió bien y no hay nada que mirar.
    """

    def test_el_caso_sale_aparte_y_no_como_derogado(self):
        """Marcarlo como derogado diría que una disposición vigente no rige."""
        xml = (
            '<documento><texto>'
            '<bloque id="dfquinta" tipo="precepto" fecha_caducidad="20201231" '
            'titulo="Disposición final quinta"><version/></bloque>'
            '<bloque id="df" tipo="precepto" titulo="Disposición final quinta ">'
            "<version/></bloque>"
            "</texto></documento>"
        )

        caducados, _, sustituidas = bloques_caducados(xml, HOY)
        hallazgos, _, _ = cruzar(
            [Precepto("Disposición final quinta", "df-5", 2)], caducados
        )

        assert hallazgos == []
        assert "disposicion final 5" in sustituidas


class TestElCruce:

    def test_un_precepto_caducado_es_un_hallazgo_con_su_fecha(self):
        preceptos = [Precepto("Artículo 35. Ámbito objetivo", "art-35", 7)]

        hallazgos, _, _ = cruzar(preceptos, {"articulo 35": "2019-03-30"})

        assert hallazgos == [
            Derogado(
                designacion="articulo 35",
                encabezado="Artículo 35. Ámbito objetivo",
                ancla="art-35",
                fragmentos=7,
                caducado_el="2019-03-30",
                declarado=False,
            )
        ]

    def test_un_precepto_vigente_no_lo_es(self):
        preceptos = [Precepto("Artículo 42. Régimen general de garantías", "art-42", 3)]

        hallazgos, _, _ = cruzar(preceptos, {"articulo 35": "2019-03-30"})

        assert hallazgos == []

    def test_una_disposicion_caducada_tambien_se_detecta(self):
        preceptos = [Precepto("Disposición adicional primera. Régimen", "da-1", 2)]

        hallazgos, _, _ = cruzar(preceptos, {"disposicion adicional 1": "2019-03-30"})

        assert [h.ancla for h in hallazgos] == ["da-1"]

    def test_sin_preceptos_no_hay_hallazgos(self):
        hallazgos, sin_designacion, _ = cruzar([], {"articulo 35": "2019-03-30"})

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

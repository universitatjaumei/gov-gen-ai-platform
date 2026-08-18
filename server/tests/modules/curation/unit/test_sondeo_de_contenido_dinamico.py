"""Sondeo de contenido dinámico: avisar en vez de acusar (RAS.2).

Los enlaces se extraen con una expresión regular sobre `href=` del HTML **servido**. Una página que
pinta su contenido con JavaScript vuelve sin texto, y el detector determinista la llamaría `empty`
con severidad crítica: un falso positivo que afirma lo contrario de la verdad —la página está llena
y el rastreador es el que no ve—. En la primera pasada contra un portal real eso llena el informe de
acusaciones falsas y le quita toda la credibilidad.

**Las heurísticas están calibradas contra el portal real, no inventadas.** Medido el 2026-08-18 en
`https://www.uji.es/centres/escola-doctorat/`: 51.098 bytes de HTML, **4.249 caracteres de texto
visible**, 10 `<script>`, 195 enlaces y **un `<noscript>` presente**. O sea: una página
perfectamente estática lleva `<noscript>` y diez scripts. Cualquier regla que mire sólo esas dos
cosas la habría declarado dinámica.
"""
from __future__ import annotations

from server.app.modules.curation.contenido_web import texto_visible, titulo_de
from server.app.modules.curation.sondeo_dinamico import (
    InformeDeSondeo,
    senales_de_dinamismo,
    sondear,
)

# Una página como las del apartado real: mucho marcado, texto de sobra, scripts y `<noscript>`.
_PAGINA_ESTATICA_REAL = (
    "<html><head><title>Escola de Doctorat - UJI</title>"
    + "".join(f'<script src="/js/{i}.js"></script>' for i in range(10))
    + "<style>.a{color:red}</style></head><body><noscript>Activa JavaScript</noscript>"
    "<h1>Escola de Doctorat</h1>"
    + "<p>" + ("Text de la pagina amb informacio real del programa. " * 90) + "</p>"
    + "</body></html>"
)

# Una página que de verdad no se puede leer sin renderizar: el contenedor está vacío.
_PAGINA_DINAMICA = (
    "<html><head><title>Cercador</title>"
    + "".join(f'<script src="/js/{i}.js"></script>' for i in range(8))
    + '</head><body><div id="root"></div>'
    '<script>window.__NEXT_DATA__ = {"props":{}}</script></body></html>'
)


# ---------------------------------------------------------------------------
# El texto de una página
# ---------------------------------------------------------------------------


def test_el_texto_visible_deja_fuera_el_marcado_los_scripts_y_los_estilos():
    texto = texto_visible(_PAGINA_ESTATICA_REAL)

    assert "Text de la pagina" in texto
    assert "<script" not in texto
    assert "color:red" not in texto
    assert "  " not in texto, "los espacios en blanco tienen que quedar colapsados"


def test_el_texto_visible_de_una_pagina_sin_contenido_es_corto():
    assert len(texto_visible(_PAGINA_DINAMICA)) < 40


def test_las_entidades_html_se_devuelven_como_caracteres():
    """«Centre d&#39;Atenció» es lo que sirve el portal; guardarlo así ensucia el corpus."""
    assert texto_visible("<p>Centre d&#39;Atenci&oacute;</p>") == "Centre d'Atenció"


def test_el_titulo_sale_del_html_y_no_de_un_encabezado_markdown():
    """El listado de la bandeja de curación se lee por el título: sin esto sale vacío."""
    assert titulo_de(_PAGINA_ESTATICA_REAL) == "Escola de Doctorat - UJI"


def test_sin_title_el_titulo_cae_al_primer_encabezado():
    assert titulo_de("<html><body><h1>Beques i ajudes</h1></body></html>") == "Beques i ajudes"


# ---------------------------------------------------------------------------
# Las señales, calibradas contra el portal real
# ---------------------------------------------------------------------------


def test_una_pagina_del_portal_real_no_se_declara_dinamica():
    """Diez scripts y un `<noscript>` no son evidencia de nada: los lleva el portal entero."""
    assert senales_de_dinamismo(_PAGINA_ESTATICA_REAL) == []


def test_un_contenedor_de_framework_vacio_si_es_evidencia():
    codigos = [s.codigo for s in senales_de_dinamismo(_PAGINA_DINAMICA)]

    assert "contenedor_vacio" in codigos or "marcador_de_framework" in codigos


def test_muy_poco_texto_con_muchos_scripts_es_evidencia():
    html = "<html><body>" + "<script>x</script>" * 12 + "<p>Cargando</p></body></html>"

    codigos = [s.codigo for s in senales_de_dinamismo(html)]

    assert "poco_texto_muchos_scripts" in codigos


def test_una_pagina_corta_pero_sin_scripts_no_es_dinamica():
    """Una página con tres frases es pobre, y eso es otro hallazgo: no es ilegible."""
    assert senales_de_dinamismo("<html><body><p>Aviso breve.</p></body></html>") == []


def test_cada_senal_dice_en_que_se_basa():
    """Un aviso sin evidencia no se puede revisar ni discutir."""
    for senal in senales_de_dinamismo(_PAGINA_DINAMICA):
        assert senal.detalle


# ---------------------------------------------------------------------------
# El informe del sondeo, por apartado
# ---------------------------------------------------------------------------


def test_el_sondeo_cuenta_cuantas_paginas_parecen_dinamicas_y_con_que_senal():
    informe = sondear(
        paginas={
            "https://www.uji.es/a": _PAGINA_ESTATICA_REAL,
            "https://www.uji.es/b": _PAGINA_ESTATICA_REAL,
            "https://www.uji.es/buscador": _PAGINA_DINAMICA,
        },
        urls_del_sitemap={"https://www.uji.es/a", "https://www.uji.es/b"},
        urls_alcanzadas={"https://www.uji.es/a", "https://www.uji.es/b"},
    )

    assert isinstance(informe, InformeDeSondeo)
    assert informe.paginas_sondeadas == 3
    assert informe.paginas_dinamicas == 1
    assert informe.senales_por_codigo, "el informe tiene que decir con qué señal"


def test_el_hueco_entre_el_sitemap_y_los_enlaces_es_la_senal_mas_fuerte():
    """Si el sitemap declara cientos de páginas que el recorrido no alcanza, los listados
    se pintan con JavaScript. Sale gratis: las dos listas ya se calculan al rastrear."""
    informe = sondear(
        paginas={"https://www.uji.es/a": _PAGINA_ESTATICA_REAL},
        urls_del_sitemap={f"https://www.uji.es/p{i}" for i in range(200)},
        urls_alcanzadas={"https://www.uji.es/a"},
    )

    assert informe.hueco_de_sitemap >= 199
    assert informe.merece_renderizar is True
    assert "sitemap" in informe.motivo.lower()


def test_si_el_contenido_estatico_cubre_el_apartado_el_informe_dice_que_no_hace_falta_navegador():
    informe = sondear(
        paginas={
            "https://www.uji.es/a": _PAGINA_ESTATICA_REAL,
            "https://www.uji.es/b": _PAGINA_ESTATICA_REAL,
        },
        urls_del_sitemap={"https://www.uji.es/a", "https://www.uji.es/b"},
        urls_alcanzadas={"https://www.uji.es/a", "https://www.uji.es/b"},
    )

    assert informe.merece_renderizar is False
    assert informe.motivo


def test_un_sondeo_sin_paginas_no_concluye_que_haga_falta_renderizar():
    """No haber podido sondear nada no es evidencia de nada."""
    informe = sondear(paginas={}, urls_del_sitemap=set(), urls_alcanzadas=set())

    assert informe.merece_renderizar is False
    assert informe.paginas_sondeadas == 0

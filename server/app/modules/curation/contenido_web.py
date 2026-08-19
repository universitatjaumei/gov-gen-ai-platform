"""De una página web, su texto y su título (RAS.2).

Deploy: edge

`SiteCrawler` guardaba el cuerpo de la respuesta tal cual en `markdown_content`. Medido contra el
portal real: **51.098 bytes de HTML con 4.249 caracteres de texto**. Con el marcado dentro, tres
cosas medían lo que no querían medir: el umbral de `thin` (120 tokens) era inalcanzable, el detector
semántico comparaba plantillas HTML —idénticas en todo el portal— y a la ingesta del asistente
llegaban 51 KB de `<div>` por página.

Se convierte al guardar, no al leer: lo que hay en la base es lo que se audita, lo que se embebe y
lo que acaba en el corpus, así que tiene que ser ya el texto.
"""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
import re

_SCRIPT_O_ESTILO = re.compile(
    r"<(script|style|noscript|template)\b[\s\S]*?</\1>", re.IGNORECASE
)
_COMENTARIO = re.compile(r"<!--[\s\S]*?-->")
_ETIQUETA = re.compile(r"<[^>]+>")
_ESPACIOS = re.compile(r"\s+")
_TITULO = re.compile(r"<title[^>]*>([\s\S]*?)</title>", re.IGNORECASE)
_ENCABEZADO = re.compile(r"<h[1-3][^>]*>([\s\S]*?)</h[1-3]>", re.IGNORECASE)
#: Suficiente para distinguir una respuesta HTML de un Markdown o un texto plano.
_PARECE_HTML = re.compile(r"<(html|body|div|p|h[1-6]|table|span)\b", re.IGNORECASE)


def parece_html(contenido: str) -> bool:
    """`True` si merece la pena convertir. El corpus normativo entra como Markdown por otra
    vía y convertirlo sería estropearlo."""
    return bool(_PARECE_HTML.search(contenido or ""))


def texto_visible(contenido: str) -> str:
    """El texto que una persona vería, con los espacios colapsados.

    `<noscript>` se descarta con los scripts: su contenido es «activa JavaScript», que no es
    contenido de la página y aparece en todas las del portal.
    """
    if not contenido:
        return ""
    sin_script = _SCRIPT_O_ESTILO.sub(" ", contenido)
    sin_comentarios = _COMENTARIO.sub(" ", sin_script)
    sin_etiquetas = _ETIQUETA.sub(" ", sin_comentarios)
    limpio = _ESPACIOS.sub(" ", _html.unescape(sin_etiquetas)).strip()
    # Cinturón: cualquier respuesta puede traer bytes nulos —un binario servido como si fuera
    # página— y Postgres rechaza la fila entera con «invalid byte sequence for encoding UTF8».
    # Pasó con un PDF del portal y se llevó por delante el rastreo completo.
    return limpio.replace("\x00", "")


def fecha_y_responsable(
    contenido: str, selector: str | None, formato: str
) -> tuple[datetime | None, str | None]:
    """La fecha que **publica** la página y la unidad que la mantiene (CUR.1).

    El portal las sirve juntas en el HTML —medido en `/base/doctorands/`:
    `<div class="clockBarDate"><span>24/09/2025</span> | <span>Escola de Doctorat</span></div>`— y
    las estábamos ignorando: `stale` adivinaba la antigüedad del año más reciente citado en el texto,
    y marcaba 303 de 400 páginas.

    El selector llega de la **configuración del sitio**, no del código: ese marcado es de este
    portal, y hardcodearlo acoplaría el módulo a un cliente. Sin selector, nada cambia.

    Nada de esto puede tumbar un rastreo: un selector inválido, un bloque que no está o un texto que
    no es una fecha devuelven `None`, que es exactamente lo que había antes.
    """
    if not selector or not contenido:
        return None, None

    try:
        from bs4 import BeautifulSoup

        bloque = BeautifulSoup(contenido, "html.parser").select_one(selector)
    except Exception:  # noqa: BLE001 — selector mal escrito, HTML roto: da igual cuál
        return None, None

    if bloque is None:
        return None, None

    partes = [t.get_text(strip=True) for t in bloque.find_all("span")]
    if not partes:
        partes = [bloque.get_text(strip=True)]

    fecha = None
    responsable = None
    for parte in partes:
        if fecha is None:
            try:
                # `strptime` rechaza `31/02/2025`, y eso es lo que se quiere: aceptar una fecha
                # imposible daría una antigüedad inventada.
                fecha = datetime.strptime(parte, formato).replace(tzinfo=timezone.utc)
                continue
            except ValueError:
                pass
        if responsable is None and parte and parte != "|":
            responsable = parte

    return fecha, responsable


def titulo_de(contenido: str) -> str | None:
    """El `<title>`, o el primer encabezado si no hay.

    Antes se llamaba a `extract_title_from_markdown` sobre HTML, que busca una línea `# `: las
    páginas rastreadas quedaban sin título y la bandeja del curador se leía por la URL.
    """
    for patron in (_TITULO, _ENCABEZADO):
        encontrado = patron.search(contenido or "")
        if encontrado:
            texto = _ESPACIOS.sub(" ", _html.unescape(_ETIQUETA.sub(" ", encontrado.group(1))))
            if texto.strip():
                return texto.strip()
    return None

"""Sondeo de contenido dinámico: medir antes de acusar, y antes de instalar un navegador (RAS.2).

Deploy: edge

Los enlaces se extraen con una expresión regular sobre el HTML **servido**. Una página que pinta su
contenido con JavaScript vuelve sin texto, y el detector determinista la llamaría `empty` con
severidad crítica: un falso positivo que afirma lo contrario de la verdad, porque la página está
llena y es el rastreador el que no ve. En la primera pasada contra un portal real eso llena el
informe de acusaciones falsas, y es lo primero que nota quien conoce esas páginas.

**Sin navegador.** Aquí sólo hay heurísticas sobre el HTML servido y el sitemap. Meter un navegador
en este paso sería decidir la solución antes de medir el problema.

**Las heurísticas están calibradas contra el portal real.** Medido el 2026-08-18 en
`https://www.uji.es/centres/escola-doctorat/`: 51.098 bytes de HTML, 4.249 caracteres de texto,
**10 `<script>` y un `<noscript>`**. Una página perfectamente estática de ese portal lleva las dos
cosas, así que ni los scripts ni el `<noscript>` son evidencia de nada por sí solos. Lo que sí lo es:
un contenedor de framework vacío, y muy poco texto **junto a** muchos scripts.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from server.app.modules.curation.contenido_web import texto_visible

#: Por debajo de esto, la página no tiene contenido que leer: ni el menú del portal cabe.
_TEXTO_MINIMO_CARACTERES = 250

#: A partir de aquí, «muchos scripts». El portal real sirve diez en páginas llenas de texto, así
#: que el número solo pesa cuando además no hay texto.
_SCRIPTS_QUE_LLAMAN_LA_ATENCION = 6

#: Un sitemap que declara muchas más páginas de las que el recorrido por enlaces alcanza significa
#: que los listados se pintan en el navegador. Es la señal más fiable y sale gratis.
_HUECO_DE_SITEMAP_RELEVANTE = 20

_CONTENEDOR_VACIO = re.compile(
    r"<div[^>]+id=[\"'](?:root|app|main-app)[\"'][^>]*>\s*</div>", re.IGNORECASE
)
_MARCADORES = (
    ("__NEXT_DATA__", "datos de hidratación de Next.js"),
    ("data-reactroot", "raíz de React sin contenido servido"),
    ("ng-app", "aplicación Angular"),
)
_SCRIPT = re.compile(r"<script\b", re.IGNORECASE)


@dataclass(frozen=True)
class SenalDeDinamismo:
    """Una razón concreta para no fiarse de lo que se ha leído. Sin detalle no se puede revisar."""

    codigo: str
    detalle: str

    def como_dict(self) -> dict[str, str]:
        return {"codigo": self.codigo, "detalle": self.detalle}


@dataclass
class InformeDeSondeo:
    """Lo que el sondeo puede afirmar de un apartado, con las cifras delante."""

    paginas_sondeadas: int = 0
    paginas_dinamicas: int = 0
    urls_del_sitemap: int = 0
    urls_alcanzadas: int = 0
    hueco_de_sitemap: int = 0
    merece_renderizar: bool = False
    motivo: str = ""
    senales_por_codigo: dict[str, int] = field(default_factory=dict)
    ejemplos: list[str] = field(default_factory=list)


def senales_de_dinamismo(contenido: str) -> list[SenalDeDinamismo]:
    """Las señales de que esta página no se puede leer sin renderizar. Vacío = se puede leer."""
    if not contenido:
        return []

    senales: list[SenalDeDinamismo] = []

    vacio = _CONTENEDOR_VACIO.search(contenido)
    if vacio:
        senales.append(SenalDeDinamismo(
            codigo="contenedor_vacio",
            detalle=f"el contenedor principal viene vacío: {vacio.group(0)[:80]}",
        ))

    scripts = len(_SCRIPT.findall(contenido))
    texto = texto_visible(contenido)

    for marcador, explicacion in _MARCADORES:
        if marcador.lower() in contenido.lower() and len(texto) < _TEXTO_MINIMO_CARACTERES:
            senales.append(SenalDeDinamismo(
                codigo="marcador_de_framework",
                detalle=f"{explicacion} ({marcador}) y {len(texto)} caracteres de texto",
            ))
            break

    if len(texto) < _TEXTO_MINIMO_CARACTERES and scripts >= _SCRIPTS_QUE_LLAMAN_LA_ATENCION:
        senales.append(SenalDeDinamismo(
            codigo="poco_texto_muchos_scripts",
            detalle=f"{len(texto)} caracteres de texto frente a {scripts} scripts",
        ))

    return senales


def sondear(
    *,
    paginas: dict[str, str],
    urls_del_sitemap: set[str],
    urls_alcanzadas: set[str],
) -> InformeDeSondeo:
    """El informe del apartado: cuántas páginas parecen dinámicas, con qué señal, y si compensa
    renderizar."""
    informe = InformeDeSondeo(
        paginas_sondeadas=len(paginas),
        urls_del_sitemap=len(urls_del_sitemap),
        urls_alcanzadas=len(urls_alcanzadas),
    )
    informe.hueco_de_sitemap = len(urls_del_sitemap - urls_alcanzadas)

    for url, contenido in paginas.items():
        senales = senales_de_dinamismo(contenido)
        if not senales:
            continue
        informe.paginas_dinamicas += 1
        if len(informe.ejemplos) < 5:
            informe.ejemplos.append(url)
        for senal in senales:
            informe.senales_por_codigo[senal.codigo] = (
                informe.senales_por_codigo.get(senal.codigo, 0) + 1
            )

    informe.merece_renderizar, informe.motivo = _veredicto(informe)
    return informe


def _veredicto(informe: InformeDeSondeo) -> tuple[bool, str]:
    """Renderizar cuesta cientos de megabytes: la respuesta por defecto es que no hace falta."""
    if informe.paginas_sondeadas == 0 and informe.hueco_de_sitemap < _HUECO_DE_SITEMAP_RELEVANTE:
        return False, "No se ha podido sondear ninguna página, así que no hay nada que concluir."

    if informe.hueco_de_sitemap >= _HUECO_DE_SITEMAP_RELEVANTE:
        return True, (
            f"El sitemap declara {informe.urls_del_sitemap} URLs y el recorrido por enlaces "
            f"alcanza {informe.urls_alcanzadas}: {informe.hueco_de_sitemap} páginas quedan fuera "
            f"del alcance de los enlaces del HTML servido, lo que apunta a listados dinámicos."
        )

    if informe.paginas_sondeadas and informe.paginas_dinamicas / informe.paginas_sondeadas >= 0.3:
        return True, (
            f"{informe.paginas_dinamicas} de {informe.paginas_sondeadas} páginas sondeadas no se "
            f"pueden leer sin renderizar ({informe.senales_por_codigo})."
        )

    return False, (
        f"El contenido estático cubre el apartado: {informe.paginas_dinamicas} de "
        f"{informe.paginas_sondeadas} páginas necesitarían navegador y el sitemap no declara "
        f"páginas fuera del alcance de los enlaces."
    )

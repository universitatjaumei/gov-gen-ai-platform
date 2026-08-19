"""La plantilla de un sitio, reconocida por repetición (CUR.3).

Deploy: edge

Quitar el menú por selectores funciona cuando alguien los declara y el portal es regular. Lo que
generaliza es otra cosa: **una línea que aparece igual en casi todas las páginas del sitio es
plantilla, no contenido**. No hace falta pedir nada ni conocer el portal; se calcula sobre lo que ya
se rastreó.

Por qué importa: cada página del apartado real llevaba el menú completo —más de mil caracteres
idénticos en todas—, y al corpus entraba con el contenido. El asistente recuperaba menús y los
citaba.

**La regla de seguridad no es «no recortes mucho».** El plan del bloque decía conservar el original
si el recorte se llevaba más de la mitad, y la medición lo desmintió: en la página de normativa del
portal, 2.120 caracteres de texto contienen 697 de contenido, así que llevarse el 67 % es lo
correcto. Lo que hay que temer es **habernos comido el contenido**, y eso se ve en el resultado: una
página que se queda prácticamente vacía.
"""
from __future__ import annotations

from collections import Counter

#: Por debajo de esto, una línea repetida no merece considerarse plantilla: «Compartir», «Més» o un
#: año suelto aparecen en todas partes, quitarlos no aporta nada y en una ficha corta podrían ser
#: contenido.
_LARGO_MINIMO_DE_BLOQUE = 12

#: Con menos páginas no hay estadística: dos páginas que comparten una frase pueden estar repitiendo
#: contenido de verdad, no plantilla.
_PAGINAS_MINIMAS = 4

#: Lo que se considera «se ha quedado sin contenido» tras el recorte: **nada**.
#
#: Aquí había un mínimo de caracteres, y un test lo desmintió: una página cuyo contenido propio es
#: una frase corta —«El contingut útil.»— se revertía entera, y devolver el menú a cambio de
#: conservar dieciocho caracteres es peor negocio. Que una página tenga poco contenido ya lo dice
#: `thin`, que además es criterio de cada sitio desde CUR.2.1; lo que este cinturón tiene que
#: cazar es habernos comido **todo**.
_MINIMO_QUE_DEBE_QUEDAR = 1


def bloques_repetidos(textos: list[str], umbral: float = 0.6) -> set[str]:
    """Las líneas que aparecen en al menos `umbral` de las páginas: la plantilla del sitio.

    Se cuenta **una vez por página** —una línea repetida diez veces dentro de la misma página sigue
    siendo una página— para que un menú lateral largo no se cuele por volumen.
    """
    paginas = [t for t in textos if t and t.strip()]
    if len(paginas) < _PAGINAS_MINIMAS:
        return set()

    apariciones: Counter[str] = Counter()
    for texto in paginas:
        lineas = {
            linea.strip()
            for linea in texto.split("\n")
            if len(linea.strip()) >= _LARGO_MINIMO_DE_BLOQUE
        }
        apariciones.update(lineas)

    minimo = max(2, int(len(paginas) * umbral))
    return {linea for linea, veces in apariciones.items() if veces >= minimo}


def sin_bloques(texto: str, bloques: set[str]) -> tuple[str, str | None]:
    """El texto sin las líneas de plantilla, y un aviso si el recorte lo dejó sin contenido.

    Cuando el aviso salta se devuelve el **original**: es mejor un corpus con algún menú dentro que
    una página vacía que nadie nota hasta que el asistente no sabe responder.
    """
    if not texto:
        return texto, None
    if not bloques:
        return texto, None

    conservadas = [
        linea for linea in texto.split("\n") if linea.strip() and linea.strip() not in bloques
    ]
    limpio = "\n".join(conservadas)

    if len(limpio.strip()) < _MINIMO_QUE_DEBE_QUEDAR < len(texto.strip()):
        return texto, "recorte_deja_la_pagina_vacia"

    return limpio, None

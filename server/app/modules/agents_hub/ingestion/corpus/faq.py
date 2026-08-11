"""Formato de los documentos de preguntas frecuentes (FAQ.1). Deploy: edge.

Una FAQ se ingiere como cualquier otro documento del corpus, con `content_class: faq`. Lo que
la distingue no es cómo se guarda sino **cómo se trocea**: cada pregunta con su respuesta
tiene que caer en un solo fragmento.

El troceador parte por encabezados. Si las preguntas van en **negrita** o en una **lista**, el
documento entero cae en uno o dos fragmentos y pasan dos cosas, las dos malas:

- La recuperación devuelve un bloque con veinte preguntas de las que diecinueve no vienen a
  cuento, y el modelo tiene que adivinar cuál responder.
- Si el bloque supera el tamaño de fragmento, el corte cae donde toque y deja **media
  pregunta con la respuesta de otra**. Eso no se ve leyendo la respuesta: se ve cuando
  alguien actúa según ella.

Por eso el formato es «la pregunta **es** el encabezado», con su ancla `{#faq-N}` para que la
cita apunte a la pregunta concreta y no al documento entero.

Este módulo es la comprobación de que se cumple. Existe porque el error es fácil de cometer
—escribir una FAQ en negritas es lo natural— y **el sistema no protestaría**: se ingiere sin
ruido y responde peor a partir de entonces.
"""
from __future__ import annotations

import re

# Encabezado Markdown, con su nivel y su bloque de atributos opcional al final.
_ENCABEZADO = re.compile(r"^(?P<nivel>#{1,6})\s+(?P<texto>.*?)\s*$")
# Ancla de FAQ dentro del bloque de atributos: `{#faq-3}`, con o sin clases al lado.
_ANCLA_FAQ = re.compile(r"\{#(?P<ancora>faq-[A-Za-z0-9._-]+)[^}]*\}")
# Cualquier ancla, para saber si un encabezado la lleva.
_ANCLA = re.compile(r"\{#[A-Za-z0-9][A-Za-z0-9._-]*[^}]*\}")

# Una línea que "parece una pregunta" sin ser encabezado: negrita suelta o ítem de lista.
_PREGUNTA_EN_NEGRITA = re.compile(r"^\s*\*\*.+\?\s*\*\*\s*$")
_PREGUNTA_EN_LISTA = re.compile(r"^\s*[-*+]\s+.*\?")

_COMO_SE_ESCRIBE = (
    "Cada pregunta tiene que ser un ENCABEZADO con su ancla, así:\n"
    "    ##### ¿Cómo se justifica una dieta? {#faq-1}\n"
    "    (aquí la respuesta)\n"
    "Si las preguntas van en negrita o en una lista, todas caen en el mismo fragmento y la "
    "recuperación devuelve un bloque entero en vez de la pregunta que se buscaba."
)


class FaqFormatoInvalido(Exception):
    """El documento declara `content_class: faq` pero no tiene forma de FAQ."""


def debe_validarse_como_faq(frontmatter: dict) -> bool:
    """Solo se valida lo que se declara FAQ.

    Una norma no tiene que cumplir esto: sus unidades citables son artículos, con sus propias
    anclas. Aplicar la regla a todo convertiría el contrato en una molestia.
    """
    return (frontmatter or {}).get("content_class") == "faq"


def _lineas_de_encabezado(cuerpo: str) -> list[tuple[int, int, str]]:
    """`(numero_de_linea, nivel, texto)` de cada encabezado."""
    salida: list[tuple[int, int, str]] = []
    for numero, linea in enumerate(cuerpo.splitlines(), start=1):
        match = _ENCABEZADO.match(linea)
        if match:
            salida.append((numero, len(match.group("nivel")), match.group("texto")))
    return salida


def assert_formato_faq(cuerpo: str) -> None:
    """Comprueba que el cuerpo tiene forma de FAQ, o explica qué falta.

    Tres reglas, y las tres nacen del mismo sitio —que pregunta y respuesta acaben juntas—:

    1. Hay al menos una pregunta como encabezado con ancla `faq-`.
    2. No hay preguntas sueltas en negrita o en lista, que es como se escribe cuando no se
       conoce el formato.
    3. Todo encabezado por debajo del título lleva ancla, para que la cita pueda apuntar a
       la pregunta y no al documento.
    """
    encabezados = _lineas_de_encabezado(cuerpo)

    # 1 — ¿hay alguna pregunta con forma de pregunta?
    if not _ANCLA_FAQ.search(cuerpo):
        raise FaqFormatoInvalido(
            "El documento declara `content_class: faq` pero no tiene ninguna pregunta con "
            f"ancla `faq-`.\n{_COMO_SE_ESCRIBE}"
        )

    # 2 — ¿hay preguntas escritas como no se debe?
    sueltas: list[str] = []
    for numero, linea in enumerate(cuerpo.splitlines(), start=1):
        if _PREGUNTA_EN_NEGRITA.match(linea) or _PREGUNTA_EN_LISTA.match(linea):
            sueltas.append(f"  línea {numero}: {linea.strip()[:70]}")
    if sueltas:
        raise FaqFormatoInvalido(
            "Hay preguntas que no son encabezados y acabarían en el fragmento de otra "
            "pregunta:\n" + "\n".join(sueltas) + f"\n{_COMO_SE_ESCRIBE}"
        )

    # 3 — ¿toda pregunta puede citarse por sí sola?
    sin_ancla = [
        f"  línea {numero}: {texto[:70]}"
        for numero, nivel, texto in encabezados
        if nivel >= 2 and not _ANCLA.search(texto)
    ]
    if sin_ancla:
        raise FaqFormatoInvalido(
            "Estas preguntas no llevan ancla, así que una cita apuntaría al documento "
            "entero y se perdería cuál de ellas lo dijo:\n"
            + "\n".join(sin_ancla)
            + f"\n{_COMO_SE_ESCRIBE}"
        )

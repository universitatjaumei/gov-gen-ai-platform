"""Extracción de texto de PDFs aportados como **contexto** (EXT.2). Deploy: shared.

Las dos vías de contexto —el PDF que una persona sube para preguntarle cosas y el que entra
como fuente de un informe de redacción— convertían con Docling, que carga modelos de layout
y OCR. Aquí basta `pdfplumber`, que ya es dependencia directa, porque el requisito de calidad
es otro: **la persona tiene el documento delante** y ve en la respuesta si la extracción salió
regular. En el corpus no lo tiene, y por eso EXT.1 cerró esa puerta.

**Un solo extractor y no dos copias.** El umbral y el aviso tienen que ser los mismos para
las dos vías; dos implementaciones acaban divergiendo justo en el caso raro, que es el que
importa.

## Por qué el umbral es por página

Sin capa de texto, `pdfplumber` devuelve poco o nada, y eso **no puede pasar en silencio**:
un documento vacío ingerido sin avisar es una avería muda —el usuario pregunta, el asistente
no encuentra nada y nadie sabe por qué—. Con un umbral **absoluto** se colaría el caso que
más se da en una administración: el escaneado de 60 páginas cuyo sello o pie de página sí
tiene capa de texto, que sumaría lo bastante para pasar. Medir por página lo distingue.

El OCR no se pierde: vive en el pipeline de curación, que es donde puede revisarse, y el
contrato del corpus tiene `origen_del_text` para declarar lo transcrito automáticamente.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import IO, Any

# Caracteres útiles por página por debajo de los cuales se considera que no hay capa de
# texto. Un párrafo corto de verdad pasa de largo; un sello o un pie de página, no.
MIN_CARACTERES_POR_PAGINA = 40


class PdfSinCapaDeTexto(Exception):
    """El PDF no tiene texto extraíble: es una imagen escaneada.

    Es una excepción y no un valor vacío a propósito: quien llama tiene que decidir qué
    contarle a la persona, y devolver `""` invita a seguir adelante con nada.
    """


def _mensaje() -> str:
    return (
        "El documento parece escaneado: no tiene capa de texto que extraer. "
        "Pásalo por el pipeline de curación, que sí aplica OCR, y sube el resultado."
    )


def extraer_paginas(datos: bytes | IO[bytes] | str | Path) -> list[str]:
    """Texto de cada página, sin juzgar si hay bastante.

    Admite bytes, un fichero abierto o una **ruta**: quien llama suele tener una u otra y
    obligarle a convertir sería mover el `open()` —y su manejo de errores— a cada llamante.

    Lo usa el pipeline de redacción, que necesita el reparto por páginas y **avisa** en vez
    de fallar: un informe puede tener otras fuentes, y perder la ejecución entera por una
    sola sería peor que señalar cuál falló.
    """
    import pdfplumber

    if isinstance(datos, bytes):
        origen: Any = io.BytesIO(datos)
    elif isinstance(datos, (str, Path)):
        origen = str(datos)
    else:
        origen = datos

    with pdfplumber.open(origen) as pdf:
        return [(pagina.extract_text() or "") for pagina in pdf.pages]


def hay_capa_de_texto(paginas: list[str]) -> bool:
    """¿El reparto por páginas tiene texto suficiente para no ser un escaneado?"""
    if not paginas:
        return False
    utiles = sum(len(p.strip()) for p in paginas)
    return utiles >= MIN_CARACTERES_POR_PAGINA * len(paginas)


def extraer_texto_de_pdf(datos: bytes | IO[bytes] | str | Path) -> str:
    """Texto del PDF, o `PdfSinCapaDeTexto` si parece escaneado.

    Es la puerta de las vías que **ingieren** el documento (el contexto temporal del
    usuario): ahí no vale avisar y seguir, porque lo que se guardaría es nada.
    """
    paginas = extraer_paginas(datos)
    if not hay_capa_de_texto(paginas):
        raise PdfSinCapaDeTexto(_mensaje())
    return "\n\n".join(p.strip() for p in paginas if p.strip())

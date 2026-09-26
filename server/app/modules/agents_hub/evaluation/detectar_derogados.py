"""Los artículos del corpus que la norma ya no tiene, cruzados contra el BOE (issue #158).

Deploy: edge

**Por qué existe, y por qué no basta con lo que ya hay.** Un enlace roto se ve: se pincha y no
lleva a ninguna parte, y para eso está `verificar_enlaces.py`. Una respuesta fundada en un
artículo derogado **es correcta en su forma** —cita una fuente real, de la norma correcta, con su
número— y falsa en su contenido. No produce ningún error, no se nota al leerla, y ninguna otra
comprobación del sistema la ve.

**Lo medido el 2026-09-25**: 19 preceptos del corpus están derogados y en 8 de ellos el corpus lo
dice —el propio texto lleva «(Suprimido)» y la norma que lo suprimió—. Los otros **12** guardan el
articulado original íntegro, sin marca, con el aspecto de norma vigente: los arts. 114-117 del RD
1098/2001 (derogados en 2009), los arts. 35-41 del RD 887/2006 (derogados en 2019) y la disposición
adicional tercera de la Ley 2/2003 (2025). Son 243 fragmentos recuperables en los cuatro
ejemplares del corpus.

**La causa está en la conversión.** El XML consolidado del BOE mata un precepto de dos maneras:

    1. dejando una `<version>` nueva cuyo texto es «(Suprimido)», o
    2. **caducando el bloque entero** con `fecha_caducidad` y sin tocar sus versiones.

El convertidor del corpus elige la versión en vigor *dentro* de cada bloque comparando
`fecha_vigencia`, así que ve la primera forma y no la segunda. Se arregla allí; esto es lo que
permite saber que ha vuelto a pasar.

**Nada se deduce del ancla**, que es la trampa de la issue #152: el ancla del BOE no se puede
calcular desde el número de artículo. El cruce va entre dos cadenas que escribe el propio BOE —el
encabezado que el corpus guardó y el atributo `titulo` del bloque del XML—, normalizadas igual.

**No es un gate de CI**, por la misma razón que `verificar_enlaces.py`: depende de un servidor
ajeno. Lo que sí corre en CI es la lógica del veredicto, que es determinista y está aquí.

    uv run python -m server.app.modules.agents_hub.evaluation.detectar_derogados \
        --chatbot-id <uuid>
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
import unicodedata
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

#: Un precepto del corpus, tal y como el corpus lo guarda.
#:
#: `declarado` es si el corpus **dice** que no rige: la clase `.derogat` del ancla, que la ingesta
#: guarda en `chunk_metadata['estat']`, o la marca «(Derogado)»/«(Suprimido)» en el texto. Es la
#: diferencia entre el caso bueno y el malo, y sin ella el informe es el mismo antes y después de
#: arreglar el problema.
@dataclass(frozen=True)
class Precepto:
    encabezado: str
    ancla: str
    fragmentos: int
    declarado: bool = False


@dataclass(frozen=True)
class Derogado:
    designacion: str
    encabezado: str
    ancla: str
    fragmentos: int
    caducado_el: str
    declarado: bool = False


def cuantos_sin_declarar(hallazgos: list[Derogado]) -> int:
    """Los que el corpus guarda **como si rigieran**, que es el defecto de verdad.

    Es lo que decide el código de salida del CLI. Fallar por haber preceptos derogados sería
    fallar para siempre —el §5 del contrato manda conservarlos, con su encabezado y su ancla,
    porque quitarlos rompería enlaces publicados—, y un rojo permanente se ignora exactamente
    igual que un verde permanente.
    """
    return sum(1 for h in hallazgos if not h.declarado)


# El BOE escribe `Artículo\xa035` en unas normas y `Artículo 35` en otras; el corpus arrastra lo que
# le llegó, y en la Ley 39/2015 y la Ley 40/2015 llegó **sin espacio ninguno** (`Artículo1. Objeto
# de la Ley`), porque el convertidor borró el espacio duro en vez de sustituirlo. De ahí `\s*`: si
# las dos formas no producen la misma clave, el cruce devuelve vacío sin dar error, que es la
# manera que tienen los medidores de mentir.
_ARTICULO = re.compile(
    r"^articulo\s*(\d{1,4})\s*(bis|ter|quater|quinquies|sexies)?(?:\s*[.,]|\s|$)"
)

#: «Artículo único» es la forma que usan los reales decretos que aprueban un reglamento: su
#: articulado entero es uno solo. No lleva número, así que no cae en `_ARTICULO`, y la revisión
#: de la PR #168 señaló que seguía sin leerse. Hoy no oculta ningún hallazgo —los tres casos del
#: corpus están en normas sin texto consolidado en el BOE— pero es un precepto citable y
#: derogable como cualquier otro.
_ARTICULO_UNICO = re.compile(r"^articulo\s+unico(?:\s*[.,]|\s|$)")
# ─────────────── Ordinales de disposición ───────────────
#
# **Portado de `converteix_boe.py`, que ya resuelve las 84 formas que aparecen de verdad en estas
# normas.** El BOE escribe lo mismo de tres maneras —«vigesimoprimera», «vigésima primera» y
# «décimo primera»— y las tres tienen que dar el MISMO número, que es lo que va a la clave del
# cruce. Si no, la misma disposición produce dos claves y el cruce se parte en dos sin dar error.
#
# De ahí que la clave sea numérica (`disposicion adicional 21`) y no el texto: es lo único que no
# depende de cómo esté escrita.
_UNIDADES = {
    "primera": 1, "primer": 1, "segunda": 2, "segundo": 2, "tercera": 3, "tercero": 3,
    "cuarta": 4, "cuarto": 4, "quinta": 5, "quinto": 5, "sexta": 6, "sexto": 6,
    "septima": 7, "septimo": 7, "octava": 8, "octavo": 8, "novena": 9, "noveno": 9,
}
_DECENAS = {
    "decima": 10, "decimo": 10, "vigesima": 20, "vigesimo": 20, "trigesima": 30,
    "trigesimo": 30, "cuadragesima": 40, "cuadragesimo": 40, "quincuagesima": 50,
    "quincuagesimo": 50, "sexagesima": 60, "sexagesimo": 60,
}
#: Las que no se descomponen.
_SUELTAS = {"unica": 1, "unico": 1, "undecima": 11, "duodecima": 12}


def numero_ordinal(texto: str) -> tuple[int | None, str]:
    """«quincuagésima séptima» → (57, ""). El sufijo recoge el `bis`, que es otra disposición."""
    t = texto.strip()
    sufijo = ""
    if t.endswith("[sic]"):
        t = t[:-5].strip()
    for extra in ("bis", "ter", "quater"):
        if t.endswith(" " + extra):
            sufijo, t = f" {extra}", t[: -len(extra) - 1].strip()
    if t in _SUELTAS:
        return _SUELTAS[t], sufijo
    partes = t.split()
    if len(partes) == 1:
        p = partes[0]
        if p in _UNIDADES:
            return _UNIDADES[p], sufijo
        if p in _DECENAS:
            return _DECENAS[p], sufijo
        for raiz, decena in _DECENAS.items():
            if p.startswith(raiz[:-1]):  # decim-, vigesim-, trigesim-
                # La vocal de unión se comporta de dos maneras y las dos aparecen en el BOE:
                # «decimo|tercera» la pone y «decim|octava» la comparte con la unidad. Se prueban
                # las tres lecturas en vez de adivinar una.
                for cand in (cua := p[len(raiz) - 1 :], cua[1:] if cua[:1] == "o" else "", "o" + cua):
                    if cand in _UNIDADES:
                        return decena + _UNIDADES[cand], sufijo
        return None, sufijo
    if len(partes) == 2 and partes[0] in _DECENAS and partes[1] in _UNIDADES:
        return _DECENAS[partes[0]] + _UNIDADES[partes[1]], sufijo
    return None, sufijo


_DISPOSICION = re.compile(
    r"^disposicion\s+(adicional|transitoria|derogatoria|final)\s*([a-z\s\[\]]{0,40}?)(?:\s*[.,]|$)"
)

#: Rótulos de estructura. No designan ningún precepto, así que no tener designación es lo
#: correcto y **no es una laguna de cobertura**. Mientras fueran en el mismo saco que los
#: preceptos ilegibles, el número no decía nada.
_ROTULO = re.compile(
    r"^(preambulo|seccion|subseccion|anexo|capitulo|titulo|libro|parte)\b"
)


def no_es_precepto(encabezado: str) -> bool:
    """Si el encabezado es un rótulo de estructura y no un precepto citable."""
    plano = unicodedata.normalize("NFD", encabezado or "")
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return bool(_ROTULO.match(re.sub(r"\s+", " ", plano).strip().lower()))


def designacion(encabezado: str) -> str | None:
    """La designación canónica del precepto, o `None` si el encabezado no designa ninguno.

    Es la única clave que comparten los dos lados del cruce. No se deduce de nada —ni del ancla,
    que es la trampa de #152—: se recorta de lo que cada lado ya trae escrito, y se reescribe en
    una forma única para que las variantes de espaciado del BOE no partan el cruce en dos.
    """
    if not encabezado:
        return None
    plano = unicodedata.normalize("NFD", encabezado)
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    plano = re.sub(r"\s+", " ", plano).strip().lower()
    if _ARTICULO_UNICO.match(plano):
        return "articulo unico"
    if m := _ARTICULO.match(plano):
        return f"articulo {m.group(1)}" + (f" {m.group(2)}" if m.group(2) else "")
    if m := _DISPOSICION.match(plano):
        familia, ordinal = m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()
        # Sin ordinal es la única, que es como la ancla el corpus: `dd-1`.
        numero, sufijo = numero_ordinal(ordinal) if ordinal else (1, "")
        if numero is None:
            return None
        return f"disposicion {familia} {numero}{sufijo}"
    return None


_BLOQUE = re.compile(r"<bloque\s+([^>]{1,600}?)>", re.S)


def bloques_caducados(
    xml: str, hoy: date
) -> tuple[dict[str, str], list[str], dict[str, str]]:
    """`(caducados, titulos_ilegibles, sustituidas)`, todos por designación.

    Sólo entran los bloques de precepto con `fecha_caducidad` **pasada**. Una caducidad futura es
    un precepto que sigue en vigor hoy y anuncia su final: darlo por derogado es el error simétrico
    y cuesta lo mismo.

    **`sustituidas`** son las designaciones que tienen un bloque caducado y además **uno vivo**.
    Eso no es una derogación, es un reemplazo: el BOE jubila el bloque viejo y publica otro con el
    mismo título. La Ley 47/2003 tiene así su «Disposición final quinta». Marcarlas como derogadas
    sería decirle a un jurista que desatienda derecho vigente, que es el error caro de los dos.

    **`titulos_ilegibles`** existe para que el medidor no pueda callar. Si el BOE cambia la forma
    de titular los bloques, este cruce devolvería cero hallazgos sin fallar, y cero es justamente
    el resultado que nadie cuestiona.
    """
    caducados: dict[str, str] = {}
    vivas: set[str] = set()
    sin_designacion: list[str] = []
    limite = hoy.strftime("%Y%m%d")
    for atributos in _BLOQUE.findall(xml):
        if 'tipo="precepto"' not in atributos:
            continue
        titulo = re.search(r'titulo="([^"]{0,200})"', atributos)
        crudo = titulo.group(1) if titulo else ""
        clave = designacion(crudo)
        caducidad = re.search(r'fecha_caducidad="(\d{8})"', atributos)
        if not caducidad or caducidad.group(1) > limite:
            if clave is not None:
                vivas.add(clave)
            continue
        if clave is None:
            sin_designacion.append(crudo)
            continue
        d = caducidad.group(1)
        caducados[clave] = f"{d[:4]}-{d[4:6]}-{d[6:]}"
    sustituidas = {k: v for k, v in caducados.items() if k in vivas}
    return (
        {k: v for k, v in caducados.items() if k not in vivas},
        sin_designacion,
        sustituidas,
    )


def cruzar(
    preceptos: list[Precepto], caducados: dict[str, str]
) -> tuple[list[Derogado], list[str], list[str]]:
    """`(hallazgos, ilegibles, no_aplican)`.

    **La tercera lista se separó de la segunda el 2026-09-26, y es lo que permitió cerrar la
    cuenta.** Antes iban juntas bajo «designaciones no legibles», y con 120 no se podía saber si
    era mucho o era cero: un preámbulo no es cobertura que falte, una disposición trigésima sí.
    Medido entonces: de 174, **41 eran rótulos de estructura** y 79 preceptos de verdad.
    """
    hallazgos: list[Derogado] = []
    sin_designacion: list[str] = []
    no_aplican: list[str] = []
    for p in preceptos:
        clave = designacion(p.encabezado)
        if clave is None:
            (no_aplican if no_es_precepto(p.encabezado) else sin_designacion).append(
                p.encabezado
            )
            continue
        if clave in caducados:
            hallazgos.append(
                Derogado(
                    clave, p.encabezado, p.ancla, p.fragmentos, caducados[clave], p.declarado
                )
            )
    return hallazgos, sin_designacion, no_aplican


def _descargar_xml(identificador: str, timeout: float = 120.0) -> str:
    """El XML consolidado de una norma. `httpx` se importa aquí y no arriba: la lógica del
    veredicto corre en CI y no tiene por qué arrastrar la red."""
    import httpx

    url = (
        "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/"
        f"{identificador}/texto"
    )
    respuesta = httpx.get(
        url, headers={"Accept": "application/xml"}, timeout=timeout, follow_redirects=True
    )
    respuesta.raise_for_status()
    return respuesta.text


_IDENTIFICADOR = re.compile(r"(BOE-A-\d{4}-\d+)")


# ─────────────── Cómo dice el corpus que un precepto no rige ───────────────
#
# Dos formas, y valen las dos. La clase `.derogat` del ancla —que la ingesta guarda en
# `chunk_metadata['estat']`— es la estructurada, y la única que puede leer el recuperador. La marca
# en el texto es la que traen los preceptos que el BOE suprime dejando una `<version>` nueva, que
# por tanto llegan sin clase en el ancla.
#
# **Una sola definición de cada una, y la señaló la revisión de la PR #167.** La primera versión
# traía un `re.compile` en Python *además* del patrón escrito a mano dentro de la consulta, y el
# CLI usaba el de la consulta: dos gramáticas independientes de lo mismo, de las cuales una no la
# ejecutaba nadie. Eso no es redundancia, es una divergencia esperando a ocurrir — y ya había
# empezado. Ahora el patrón es esta constante y la usa quien pregunta, que es la base de datos.
ESTADOS_QUE_DECLARAN = ("derogat", "suprimit")

#: Sintaxis de expresión regular POSIX, que es la que entiende el `~*` de Postgres. No se compila
#: en Python porque en Python no la usa nadie: la pregunta se hace en la base para no traerse el
#: contenido de decenas de miles de fragmentos.
PATRON_MARCA = r"\*\*\((derogad|suprimid)"


def _preceptos_del_documento(
    metadatos_por_ancla: dict[str, tuple[str, int, bool]],
) -> list[Precepto]:
    """Las anclas de una norma, con su encabezado, sus fragmentos y si el corpus las declara."""
    return [
        Precepto(enc, ancla, n, declarado)
        for ancla, (enc, n, declarado) in sorted(metadatos_por_ancla.items())
    ]


async def _run(args: argparse.Namespace) -> int:
    from sqlalchemy import func, or_ as sa_or, select

    from server.app.modules.agents_hub.database.connection import (
        create_async_engine,
        create_session_factory,
    )
    from server.app.modules.agents_hub.database.operational_models import (
        HubDocument,
        HubDocumentChunk,
    )

    engine = create_async_engine()
    factory = create_session_factory(engine)
    # `{identificador del BOE: {ancla: (encabezado, n_fragmentos)}}`, y el título para el informe.
    por_norma: dict[str, dict[str, tuple[str, int, bool]]] = defaultdict(dict)
    titulos: dict[str, str] = {}
    fuera_de_alcance: dict[str, int] = defaultdict(int)
    try:
        async with factory() as session:
            # **Sólo SELECT**, y contra la base que sirve a gente de verdad. Se piden columnas
            # planas y no objetos ORM: la unión completa de documentos y fragmentos es la consulta
            # que el 2026-09-24 se comió la memoria de la VM y dejó el sitio caído 50 minutos.
            documentos = {
                d.id: d
                for d in (
                    await session.execute(
                        select(HubDocument).where(HubDocument.chatbot_id == args.chatbot_id)
                    )
                )
                .scalars()
                .all()
                if (d.doc_metadata or {}).get("tipus_document") == "norma_externa"
            }
            ancora = HubDocumentChunk.chunk_metadata["ancora"].astext
            # **Dos consultas acotadas, y ninguna trae los fragmentos.** Traer los metadatos de
            # todos —decenas de miles de JSON— es la misma forma de la consulta que tumbó la VM:
            # cabe hoy y deja de caber cuando el corpus crezca, sin avisar. De cada ancla hace
            # falta su encabezado (una fila, `DISTINCT ON`) y cuántos fragmentos tiene (un
            # `count`), que son unos pocos miles de filas en total.
            conteos = {
                (doc_id, anc): n
                for doc_id, anc, n in (
                    await session.execute(
                        select(HubDocumentChunk.document_id, ancora, func.count())
                        .where(HubDocumentChunk.document_id.in_(documentos))
                        .group_by(HubDocumentChunk.document_id, ancora)
                    )
                ).all()
            }
            cabeceras = (
                await session.execute(
                    select(
                        HubDocumentChunk.document_id, ancora, HubDocumentChunk.chunk_metadata
                    )
                    .where(HubDocumentChunk.document_id.in_(documentos))
                    .distinct(HubDocumentChunk.document_id, ancora)
                    .order_by(HubDocumentChunk.document_id, ancora)
                )
            ).all()
            # Si el corpus DICE que ese precepto no rige. Se agrupa en la base y no se traen los
            # textos: lo unico que hace falta es un booleano por ancla, y traer el contenido de
            # decenas de miles de fragmentos es la forma de consulta que tumbo la VM.
            estado = HubDocumentChunk.chunk_metadata["estat"].astext
            declarados = {
                (doc_id, anc)
                for doc_id, anc in (
                    await session.execute(
                        select(HubDocumentChunk.document_id, ancora)
                        .where(
                            HubDocumentChunk.document_id.in_(documentos),
                            sa_or(
                                estado.in_(ESTADOS_QUE_DECLARAN),
                                HubDocumentChunk.content.op("~*")(PATRON_MARCA),
                            ),
                        )
                        .distinct()
                    )
                ).all()
            }
    finally:
        await engine.dispose()

    for doc_id, anc, meta in cabeceras:
        documento = documentos.get(doc_id)
        if documento is None or not anc:
            continue
        m = documento.doc_metadata or {}
        ident = _IDENTIFICADOR.search(m.get("url_oficial") or m.get("url_eli") or "")
        if not ident:
            # El DOGV y el DOUE no publican texto consolidado con este formato, así que estas
            # normas quedan fuera de la comprobación. Se cuentan y se dicen: un medidor que
            # descarta en silencio informa sobre menos corpus del que aparenta.
            fuera_de_alcance[getattr(documento, "title", "") or str(doc_id)] += 1
            continue
        titulos.setdefault(ident.group(1), getattr(documento, "title", "") or "")
        # El encabezado más profundo es el del precepto; los de arriba son la jerarquía (título,
        # capítulo). `header_10` iría antes que `header_2` en orden alfabético, de ahí el número.
        encabezados = [
            (int(k.removeprefix("header_")), v)
            for k, v in (meta or {}).items()
            if k.startswith("header_") and k.removeprefix("header_").isdigit()
        ]
        encabezado = max(encabezados)[1] if encabezados else ""
        por_norma[ident.group(1)][anc] = (
            encabezado,
            conteos.get((doc_id, anc), 0),
            (doc_id, anc) in declarados,
        )

    hoy = date.today()
    total_hallazgos = total_dudas = total_sin_declarar = total_no_aplican = 0
    for ident, por_ancla in sorted(por_norma.items()):
        try:
            xml = _descargar_xml(ident)
        except Exception as exc:  # noqa: BLE001
            # Una excepción NO es «esta norma está bien». Sin esto, un fallo de red dejaría la
            # comprobación en silencio y el informe diría que todo está en orden.
            print(f"no_resuelve\t{ident}\t{type(exc).__name__}: {exc}")
            total_dudas += 1
            continue
        caducados, sin_titulo, sustituidas = bloques_caducados(xml, hoy)
        preceptos = _preceptos_del_documento(por_ancla)
        hallazgos, sin_encabezado, no_aplican = cruzar(preceptos, caducados)
        for h in hallazgos:
            # **La distinción que importa.** `SIN_DECLARAR` es el defecto: el corpus guarda el
            # articulado como si rigiera. `declarado` es el caso correcto —el §5 del contrato
            # manda conservar el precepto con su encabezado y su ancla— y se dice igualmente,
            # porque conviene saber cuáles son.
            #
            # Sin separarlos, este informe era **idéntico antes y después** de la reingesta del
            # 2026-09-25: doce preceptos las dos veces, con 243 fragmentos de articulado muerto la
            # primera y 48 marcados la segunda. Un medidor que no distingue el caso bueno del malo
            # no sirve para vigilar, que es justo para lo que existe.
            print(
                f"{'declarado' if h.declarado else 'SIN_DECLARAR'}\t{ident}\t{h.ancla}"
                f"\t{h.caducado_el}\t{h.fragmentos} fragmentos\t{h.encabezado[:90]}"
            )
        # **Renumeraciones.** Un bloque caducado cuya designación tiene además un bloque vivo no
        # es una derogación: el BOE insertó un precepto nuevo con ese número y el que lo tenía
        # pasó al siguiente. Pasó con la d.f. quinta de la Ley 47/2003, que en 2021 dejó de ser
        # «Entrada en vigor» para ser la del Informe de Impacto de Género.
        #
        # **Lo que hay que mirar es si el corpus se quedó con las dos.** Si trae una sola ancla
        # para esa designación, el convertidor resolvió bien y no hay nada que hacer; decirlo
        # igualmente sería ruido con aspecto de hallazgo, y a la tercera vez que alguien lo mire
        # sin encontrar nada dejará de mirarlo. Si trae dos, una es la numeración vieja.
        renumeradas = cruzar(preceptos, sustituidas)[0]
        por_designacion: dict[str, list[Derogado]] = defaultdict(list)
        for h in renumeradas:
            por_designacion[h.designacion].append(h)
        for designacion_repetida, cuales in sorted(por_designacion.items()):
            if len(cuales) < 2:
                continue
            for h in cuales:
                print(
                    f"revisar\t{ident}\t{h.ancla}\t{h.caducado_el}\t{h.fragmentos} fragmentos"
                    f"\t{h.encabezado[:90]}\tel corpus trae {len(cuales)} anclas para "
                    f"«{designacion_repetida}», y el BOE renumero: una es la numeracion vieja"
                )
        total_hallazgos += len(hallazgos)
        total_sin_declarar += cuantos_sin_declarar(hallazgos)
        total_dudas += len(sin_titulo) + len(sin_encabezado)
        total_no_aplican += len(no_aplican)
        print(
            f"# {ident}: {len(por_ancla)} preceptos · {len(caducados)} bloques caducados en el BOE"
            f" · {len(hallazgos)} en el corpus ({cuantos_sin_declarar(hallazgos)} sin declarar)"
            f" · {len(sin_titulo) + len(sin_encabezado)} sin leer"
            f" · {len(no_aplican)} rotulos que no son preceptos"
            f"\t{titulos.get(ident, '')[:60]}",
            file=sys.stderr,
        )

    for titulo, n in sorted(fuera_de_alcance.items()):
        print(f"# fuera de alcance: {n} preceptos · {titulo[:80]}", file=sys.stderr)
    print(
        f"{total_hallazgos} preceptos con el bloque caducado en el BOE, de {len(por_norma)} normas"
        f" — de ellos {total_sin_declarar} SIN DECLARAR, que es el defecto"
        f"\n  Cobertura: {total_dudas} preceptos que NO se saben leer"
        f" (eso es lo unico que falta por cubrir),"
        f" {total_no_aplican} rotulos que no son preceptos,"
        f" {len(fuera_de_alcance)} normas sin texto consolidado en el BOE",
        file=sys.stderr,
    )
    # Falla por el defecto, no por el inventario. Los preceptos derogados se quedan en el corpus a
    # propósito, así que fallar por tenerlos sería un rojo permanente — y un rojo permanente se
    # ignora exactamente igual que un verde permanente.
    return 1 if total_sin_declarar else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--chatbot-id", required=True, type=uuid.UUID, dest="chatbot_id")
    return asyncio.run(_run(parser.parse_args(argv)))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

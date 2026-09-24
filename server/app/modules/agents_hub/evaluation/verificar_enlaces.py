"""Los enlaces que el asistente ofrece como fundamento, comprobados contra el sitio (issue #14).

Deploy: edge

**Por qué existe.** Cuatro de los enlaces que el asistente daba como fundamento no llevaban a
ninguna parte, y salieron a mano. Una cita sin enlace verificable obliga a creerse al asistente,
que es justo lo que este proyecto no quiere: el fundamento existe para poder contrastarlo. Un
enlace muerto **es peor que no citar**, porque aparenta verificación.

**Dos formas de estar muerto.** Que la página no responda es la obvia. La otra es peor: la página
responde 200 y el **ancla no existe** en ella, así que el lector aterriza en la cabecera del
documento convencido de estar leyendo el artículo citado. Nada falla y la cita miente.

**Esto NO es un gate de CI**, y la razón es la misma que separa `retrieval_metrics` de
`run_golden`: depende de un servidor ajeno y de la red. Un rojo aquí puede significar «el corpus
se está republicando» o «la red del runner va mal», y un gate que falla por causas que no son el
cambio enseña a ignorarlo. Se ejecuta a mano o de noche.

Lo que sí corre en CI es `comprobar_enlaces`, con el acceso HTTP inyectado: la lógica del
veredicto —qué cuenta como muerto— es determinista y se fija con tests.

**No lee ninguna conversación.** La issue encontró los cuatro auditando conversaciones guardadas,
que fue buen método de diagnóstico y no hace falta para la comprobación permanente: los enlaces se
derivan de `hub_documents`. Detectar lo mismo sin tocar datos personales es preferible aunque
cueste igual.

    uv run python -m server.app.modules.agents_hub.evaluation.verificar_enlaces \
        --chatbot-id <uuid> [--limite 0] [--concurrencia 8]
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Awaitable, Callable

#: `id="art-9"` o `name="art-9"`, con comillas simples o dobles y espacios alrededor del `=`.
#: Se busca el atributo y no la cadena suelta: `art-9` aparece en el texto de cualquier norma que
#: se cite a sí misma, y buscarla a pelo daría por viva un ancla que no existe.
def _ancla_presente(html: str, ancla: str) -> bool:
    patron = rf"""\b(?:id|name)\s*=\s*['"]{re.escape(ancla)}['"]"""
    return re.search(patron, html) is not None


@dataclass(frozen=True)
class Hallazgo:
    url: str
    motivo: str  # "no_resuelve" | "ancla_ausente"
    detalle: str


Fetch = Callable[[str], Awaitable[tuple[int, str]]]


async def comprobar_enlaces(
    urls: list[str], fetch: Fetch, concurrencia: int = 8
) -> list[Hallazgo]:
    """Los hallazgos de una lista de URLs de cita. Lista vacía significa que todas viven.

    `fetch` devuelve `(status, cuerpo)`. Se inyecta para que esta función —que es la que decide
    qué cuenta como muerto— sea determinista y pueda correr en CI sin red.
    """
    # Las anclas del mismo documento comparten descarga. El corpus tiene cientos de fragmentos
    # por norma: pedir la página una vez por fragmento convertiría la comprobación en algo
    # parecido a un ataque contra el propio sitio.
    por_pagina: dict[str, list[str]] = defaultdict(list)
    for url in urls:
        pagina, _, ancla = url.partition("#")
        por_pagina[pagina].append(ancla)

    # `Semaphore(0)` no es «sin límite»: deja todas las tareas esperando para siempre, y el
    # medidor se cuelga sin decir por qué. Un cero llega solo desde `--concurrencia 0`, que es
    # justo lo que alguien escribiría creyendo que significa «sin tope».
    if concurrencia < 1:
        raise ValueError(
            f"concurrencia={concurrencia}: tiene que ser al menos 1. Un cero no quita el límite, "
            f"deja la comprobación colgada indefinidamente."
        )

    limite = asyncio.Semaphore(concurrencia)
    hallazgos: list[Hallazgo] = []

    async def _una(pagina: str, anclas: list[str]) -> list[Hallazgo]:
        async with limite:
            try:
                status, cuerpo = await fetch(pagina)
            except Exception as exc:  # noqa: BLE001
                # Una excepción NO es «está viva». Sin este `except`, un fallo de red dejaría
                # la comprobación en silencio y el informe diría que todo está bien.
                return [Hallazgo(pagina, "no_resuelve", f"{type(exc).__name__}: {exc}")]

        if status != 200:
            return [Hallazgo(pagina, "no_resuelve", str(status))]

        return [
            Hallazgo(f"{pagina}#{a}", "ancla_ausente", f"la pagina no declara `{a}`")
            for a in dict.fromkeys(a for a in anclas if a)
            if not _ancla_presente(cuerpo, a)
        ]

    for lote in await asyncio.gather(
        *(_una(p, a) for p, a in por_pagina.items())
    ):
        hallazgos.extend(lote)
    return hallazgos


async def _fetch_real(timeout: float = 15.0) -> Fetch:
    """El acceso HTTP de verdad. `httpx` se importa aquí y no arriba: la lógica del veredicto
    corre en CI y no tiene por qué arrastrar la red."""
    import httpx

    cliente = httpx.AsyncClient(timeout=timeout, follow_redirects=True)

    async def fetch(url: str) -> tuple[int, str]:
        respuesta = await cliente.get(url)
        return respuesta.status_code, respuesta.text

    return fetch


async def _run(args: argparse.Namespace) -> int:
    from sqlalchemy import select

    from server.app.modules.agents_hub.database.connection import (
        create_async_engine,
        create_session_factory,
    )
    from server.app.modules.agents_hub.database.operational_models import (
        HubDocument,
        HubDocumentChunk,
    )
    from server.app.modules.agents_hub.services.retrieval.citations import url_de_cita

    engine = create_async_engine()
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            # **Sólo SELECT.** Esta herramienta no escribe nada, y se ejecuta contra la base que
            # sirve a gente de verdad.
            #
            # Y se comprueba lo que el lector ve, que no es lo mismo que lo que hay guardado:
            # `chunk.source_url` es la URL de **ingesta**, mientras que la cita se compone al
            # recuperar con `url_de_cita(documento, metadata)` —es lo que hace
            # `vector_strategy`—. Comprobar la de ingesta daría un informe sobre unas URL que
            # nadie llega a pinchar.
            #
            # **Y se recorre en flujo, sin materializar la consulta entera.** La primera versión
            # hacía `.all()` sobre la unión completa, que en este corpus son cientos de miles de
            # filas de objetos ORM: exactamente la clase de consulta que el 2026-09-24 se comió
            # la memoria de la VM y dejó el sitio caído 50 minutos. Con los techos de la issue
            # #149 ya no tumbaría la máquina —moriría el contenedor—, pero morir tampoco es el
            # objetivo. `stream()` mantiene en memoria una fila cada vez.
            consulta = (
                select(HubDocument, HubDocumentChunk.chunk_metadata)
                .join(HubDocumentChunk, HubDocumentChunk.document_id == HubDocument.id)
                .where(HubDocument.chatbot_id == args.chatbot_id)
            )
            vistas: set[str] = set()
            async for documento, metadata in await session.stream(consulta):
                u = url_de_cita(documento, metadata or {})
                if u:
                    vistas.add(u)
            urls = sorted(vistas)
    finally:
        await engine.dispose()

    if args.limite:
        urls = urls[: args.limite]

    print(f"{len(urls)} URL de cita distintas", file=sys.stderr)
    fetch = await _fetch_real()
    hallazgos = await comprobar_enlaces(urls, fetch, args.concurrencia)

    for h in sorted(hallazgos, key=lambda x: (x.motivo, x.url)):
        print(f"{h.motivo}\t{h.url}\t{h.detalle}")

    print(
        f"{len(hallazgos)} enlaces con problema de {len(urls)} comprobados",
        file=sys.stderr,
    )
    return 1 if hallazgos else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--chatbot-id", required=True, type=uuid.UUID, dest="chatbot_id")
    parser.add_argument("--limite", type=int, default=0, help="0 = sin limite")
    parser.add_argument("--concurrencia", type=int, default=8)
    return asyncio.run(_run(parser.parse_args(argv)))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

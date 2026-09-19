#!/usr/bin/env python3
"""Decide si los informes de `pip-audit` bloquean el build, y por qué.

Lo ejecuta el job `supply-chain` de `ci.yml` después de auditar. Lee uno o más informes JSON de
`pip-audit` y `avisos_aceptados.toml`, y sale con 1 si algo tiene que bloquear.

EL CRITERIO, y por qué es éste (decidido el 2026-09-15, al cerrar DEP.7)
-----------------------------------------------------------------------
Bloquea un aviso que **tiene corrección publicada** (`fix_versions` no vacío) y **no está
aceptado** en `avisos_aceptados.toml`, o lo está pero su aceptación **ha caducado**. Lo que no
tiene corrección informa y no bloquea.

El prompt del bloque proponía «bloquear en `high` y `critical`, informar por debajo». No se puede:
**`pip-audit` no informa de severidad.** Sus entradas traen `id`, `aliases`, `description` y
`fix_versions` — ni CVSS ni etiqueta. Un umbral por severidad tendría que inventarse el dato o
dejar un hueco silencioso (los avisos sin severidad no bloquearían nunca), que es la clase de
avería que no se ve en el verde.

«¿Tiene corrección?» sí es un dato que la herramienta da, y además es **la pregunta que decide si
quien lee el rojo puede hacer algo**. Ésa era la razón escrita cuando el job nació informando —«un
guardarraíl rojo por algo que quien lo lee no puede arreglar acaba desactivado»—, y este criterio
la respeta en vez de contradecirla: si hay versión corregida, se sube; si no la hay, subir no es
una opción y el sitio del aviso es el fichero de aceptados, con fecha.

El lado JavaScript no necesita este guion: `npm audit` sí trae severidad y bloquea solo, con
`--audit-level=high` sobre el árbol de producción.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import tomllib
from pathlib import Path
from typing import NamedTuple


class Aviso(NamedTuple):
    paquete: str
    version: str
    id: str
    correcciones: tuple[str, ...]

    @property
    def tiene_correccion(self) -> bool:
        return bool(self.correcciones)


def lee_informe(ruta: Path) -> list[Aviso]:
    """Los avisos de un informe JSON de pip-audit, sin duplicados.

    pip-audit repite la misma pareja (paquete, id) cuando un paquete entra por más de un camino.
    Contarlos dos veces no cambia la decisión pero infla el resumen, y un número inflado en un
    informe de seguridad es una forma barata de perder credibilidad.
    """
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    dependencias = datos.get("dependencies", datos)
    vistos: dict[tuple[str, str], Aviso] = {}
    for dep in dependencias:
        nombre = dep.get("name", "?")
        version = dep.get("version", "?")
        for vuln in dep.get("vulns", []):
            aviso = Aviso(
                paquete=nombre,
                version=version,
                id=vuln.get("id", "?"),
                correcciones=tuple(vuln.get("fix_versions") or ()),
            )
            vistos.setdefault((nombre, aviso.id), aviso)
    return sorted(vistos.values())


def lee_aceptados(ruta: Path, hoy: dt.date) -> tuple[set[str], list[str]]:
    """Devuelve (ids aceptados y vigentes, descripciones de los caducados).

    Los caducados se devuelven aparte y NO cuentan como aceptados: una aceptación vencida es
    exactamente lo que este mecanismo existe para sacar a la luz. Que además haya un test que se
    ponga rojo por ellos es el cinturón; esto es los tirantes, porque el test vive en la suite y
    la puerta tiene que valer aunque alguien ejecute sólo el job.
    """
    if not ruta.is_file():
        return set(), []

    vigentes: set[str] = set()
    caducados: list[str] = []
    for aviso in tomllib.loads(ruta.read_text(encoding="utf-8")).get("aviso", []):
        caduca = aviso["caduca"]
        if isinstance(caduca, str):
            caduca = dt.date.fromisoformat(caduca)
        if isinstance(caduca, dt.datetime):
            caduca = caduca.date()
        if caduca < hoy:
            caducados.append(f"{aviso['id']} ({aviso['paquete']}), caducó el {caduca}")
        else:
            vigentes.add(aviso["id"])
    return vigentes, caducados


def _linea(aviso: Aviso) -> str:
    arreglo = ", ".join(aviso.correcciones) if aviso.correcciones else "sin corrección publicada"
    return f"{aviso.paquete} {aviso.version} — {aviso.id} → {arreglo}"


def main(argv: list[str] | None = None) -> int:
    # CI corre en Linux con UTF-8, pero este guion también se ejecuta en local para comprobarlo
    # antes de empujar, y la consola de Windows es cp1252: sin esto, una flecha en el resumen
    # tumba la puerta con un `UnicodeEncodeError` y el rojo no dice nada de seguridad. Un
    # guardarraíl que falla por la codificación de quien lo mira no es un guardarraíl.
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "informes",
        nargs="+",
        type=Path,
        help="JSON de pip-audit del conjunto QUE SE DESPLIEGA. Sólo éstos pueden bloquear.",
    )
    parser.add_argument(
        "--informativos",
        nargs="*",
        type=Path,
        default=[],
        metavar="INFORME",
        help=(
            "JSON de pip-audit del conjunto COMPLETO del lock (con extras y dev). Informan y "
            "nunca bloquean: son dependencias que el lock describe y el despliegue no instala."
        ),
    )
    parser.add_argument("--aceptados", type=Path, required=True)
    parser.add_argument("--resumen", type=Path, help="Fichero donde volcar el resumen Markdown")
    args = parser.parse_args(argv)

    hoy = dt.date.today()
    aceptados, caducados = lee_aceptados(args.aceptados, hoy)

    def _leer(rutas: list[Path]) -> list[Aviso] | None:
        """Los avisos de una lista de informes, o `None` si falta alguno.

        Un informe que falta no es «cero avisos»: es una auditoría que no corrió. Esta
        distinción es literalmente el agujero que la primera ejecución del job destapó, cuando
        `mcp_server` no se auditó y el único síntoma fue un fichero ausente.
        """
        reunidos: list[Aviso] = []
        for informe in rutas:
            if not informe.is_file():
                print(f"::error::Falta el informe {informe}. La auditoría no llegó a ejecutarse.")
                return None
            reunidos.extend(lee_informe(informe))
        return reunidos

    avisos = _leer(args.informes)
    if avisos is None:
        return 1

    # APER.17 — el conjunto completo del lock. **No bloquea**: son dependencias que el lock
    # describe y la imagen no instala (extras como `agente-navegador` o `local-models`, y el
    # grupo `dev`). Auditar lo que se despliega es lo correcto; lo que no valía era que el verde
    # no dijera su alcance —200 paquetes de 438— mientras Dependabot informaba de críticos.
    del_lock = _leer(list(args.informativos))
    if del_lock is None:
        return 1

    bloquean = [a for a in avisos if a.tiene_correccion and a.id not in aceptados]
    informan = [a for a in avisos if not a.tiene_correccion or a.id in aceptados]

    # El completo CONTIENE al desplegado, así que se resta: sin esto cada aviso saldría dos
    # veces y el informe engañaría sobre cuántos hay.
    ya_dichos = {a.id for a in avisos}
    solo_en_el_lock = sorted(
        {a.id: a for a in del_lock if a.id not in ya_dichos}.values(),
        key=lambda a: (a.paquete, a.id),
    )

    lineas = [
        "## Puerta de avisos (Python)",
        "",
        "Bloquea sobre el conjunto **que se despliega** (sin extras y sin `dev`). El conjunto "
        "completo del lock se informa aparte, más abajo.",
        "",
    ]
    if bloquean:
        lineas += [f"**BLOQUEA: {len(bloquean)} aviso(s) con corrección publicada y sin aceptar.**", ""]
        lineas += [f"- {_linea(a)}" for a in bloquean]
        lineas += [
            "",
            "Se arregla subiendo el paquete. Si el techo de un padre lo impide, la salida es una "
            "entrada en `avisos_aceptados.toml` con motivo, responsable y caducidad — no apagar "
            "la puerta.",
        ]
    else:
        lineas += ["Ningún aviso con corrección publicada sin aceptar.", ""]

    if informan:
        lineas += ["", f"Informan y no bloquean ({len(informan)}):", ""]
        lineas += [
            f"- {_linea(a)}" + (" *(aceptado)*" if a.id in aceptados else "") for a in informan
        ]

    if solo_en_el_lock:
        lineas += [
            "",
            f"**En el lock pero fuera del despliegue ({len(solo_en_el_lock)})** — informan y no "
            "bloquean:",
            "",
            "La imagen se instala sin extras y sin `dev`, así que estos paquetes **no se "
            "instalan** en producción. Se listan porque el lock los describe y porque son los "
            "que Dependabot ve: si esta sección crece, la pregunta es si el extra que los trae "
            "sigue haciendo falta — retirar un extra quita sus avisos de raíz, que es lo que "
            "pasó con `pdfplumber` y `pillow` en APER.12.",
            "",
        ]
        lineas += [f"- {_linea(a)}" for a in solo_en_el_lock]

    if caducados:
        lineas += [
            "",
            f"**Aceptaciones CADUCADAS ({len(caducados)})** — vuelven a bloquear:",
            "",
        ]
        lineas += [f"- {c}" for c in caducados]

    resumen = "\n".join(lineas)
    print(resumen)
    if args.resumen:
        with args.resumen.open("a", encoding="utf-8") as fh:
            fh.write(resumen + "\n")

    return 1 if bloquean else 0


if __name__ == "__main__":
    sys.exit(main())

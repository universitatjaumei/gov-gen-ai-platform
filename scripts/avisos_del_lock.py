"""Avisos conocidos de un conjunto de dependencias ya resuelto, preguntando a OSV por lotes.

**Por qué existe, en vez de usar `pip-audit` como el otro conjunto.** `pip-audit -r` **instala**
lo que lee para resolverlo, y el conjunto completo del lock incluye `torch` y sus ruedas: medido
el 2026-09-19, más de quince minutos sin producir informe. Para el conjunto **desplegado** eso se
paga (son 200 paquetes y da la resolución de verdad); para el conjunto **completo**, que sólo
informa, no hay nada que resolver: el `uv export` ya viene pinchado a `nombre==versión`.

Así que se pregunta a **OSV** directamente, que es la misma base que `pip-audit` consulta por
omisión, en lotes de cien. Segundos en vez de cuartos de hora.

La salida imita la de `pip-audit --format json` **a propósito**: `puerta_de_avisos.py` la lee sin
cambiar una línea, y el día que esto se pueda sustituir por `pip-audit` no habrá que tocar la
puerta.

    python scripts/avisos_del_lock.py requirements.txt --salida informe.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

OSV = "https://api.osv.dev/v1/querybatch"
OSV_VULN = "https://api.osv.dev/v1/vulns/"

#: OSV admite hasta mil consultas por lote; se parte en cien por prudencia con el tamaño.
POR_LOTE = 100

_PINCHADO = re.compile(r"^(?P<nombre>[A-Za-z0-9_.\-]+)(?:\[[^\]]*\])?==(?P<version>[^\s;]+)")


def paquetes_de(requirements: Path) -> dict[str, str]:
    """Los `nombre==versión` del fichero. Lo demás se ignora: marcadores, comentarios, flags."""
    encontrados: dict[str, str] = {}
    for linea in requirements.read_text(encoding="utf-8").splitlines():
        limpia = linea.strip()
        if not limpia or limpia.startswith(("#", "-")):
            continue
        m = _PINCHADO.match(limpia)
        if m:
            encontrados[m.group("nombre").lower()] = m.group("version")
    return encontrados


def _consulta(lote: list[dict]) -> list[dict]:
    peticion = urllib.request.Request(
        OSV,
        data=json.dumps({"queries": lote}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(peticion, timeout=60) as respuesta:
        return json.load(respuesta)["results"]


def _arreglos(vuln_id: str, paquete: str) -> list[str]:
    """Las versiones que corrigen el aviso. Es el dato con el que la puerta decide.

    `querybatch` devuelve sólo identificadores, así que hace falta una segunda llamada por
    aviso. Son pocas —los avisos de un lock sano se cuentan con los dedos— y el resultado
    decide si algo bloquea o informa, que es justo lo que no se puede aproximar.

    **Y por eso un fallo de red se propaga (APER.23).** Aquí había un
    `except (URLError, TimeoutError): return []`, y la lista vacía es exactamente el valor que
    significa «este aviso no tiene corrección publicada». O sea que un OSV lento convertía un
    aviso **corregible** en uno **incorregible**, la puerta lo dejaba pasar y el informe salía
    en verde sin que nada lo dijera. La frase de arriba ya avisaba de que este dato no se puede
    aproximar; el `except` la contradecía. Un auditor que no ha podido auditar tiene que caerse.
    """
    with urllib.request.urlopen(OSV_VULN + vuln_id, timeout=60) as respuesta:
        detalle = json.load(respuesta)

    versiones: list[str] = []
    for afectado in detalle.get("affected", []):
        nombre = (afectado.get("package") or {}).get("name", "")
        if nombre.lower() != paquete:
            continue
        for rango in afectado.get("ranges", []):
            for evento in rango.get("events", []):
                if "fixed" in evento:
                    versiones.append(evento["fixed"])
    return sorted(set(versiones))


def main(argv: list[str] | None = None) -> int:
    # La misma razón que en `puerta_de_avisos.py`: CI corre en Linux con UTF-8, pero esto se
    # ejecuta también en local para comprobarlo antes de empujar, y la consola de Windows es
    # cp1252. Sin esto, la flecha del resumen tumba el guion con un `UnicodeEncodeError` y el
    # rojo no dice nada de dependencias.
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("requirements", type=Path)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args(argv)

    paquetes = paquetes_de(args.requirements)
    if not paquetes:
        # Un fichero sin paquetes no es «cero avisos»: es un export que salió mal. Se dice, y se
        # falla, porque escribir un informe vacío sería exactamente el fichero que parece bueno
        # y mide otra cosa.
        print(f"::error::{args.requirements} no tiene ningún `nombre==versión`.")
        return 1

    nombres = list(paquetes)
    consultas = [
        {"package": {"name": n, "ecosystem": "PyPI"}, "version": v} for n, v in paquetes.items()
    ]

    resultados: list[dict] = []
    for inicio in range(0, len(consultas), POR_LOTE):
        resultados.extend(_consulta(consultas[inicio : inicio + POR_LOTE]))

    # **El emparejado es por posición, así que la posición se comprueba (APER.23).** Abajo hay
    # un `zip(nombres, resultados)`: si OSV devolviera menos resultados que consultas, `zip` se
    # pararía en el más corto sin decir nada y cada aviso quedaría colgado del paquete
    # equivocado. Un informe que acusa a `jinja2` de lo de `torch` tiene el mismo aspecto que
    # uno bueno, y ésta es la única línea que puede distinguirlos.
    if len(resultados) != len(consultas):
        print(
            f"::error::OSV devolvió {len(resultados)} resultados para {len(consultas)} "
            "consultas. El informe se empareja por posición, así que con esto no se puede "
            "decir de qué paquete es cada aviso."
        )
        return 1

    dependencias = []
    for nombre, resultado in zip(nombres, resultados):
        vulns = resultado.get("vulns") or []
        if not vulns:
            continue
        dependencias.append(
            {
                "name": nombre,
                "version": paquetes[nombre],
                "vulns": [
                    {"id": v["id"], "fix_versions": _arreglos(v["id"], nombre)} for v in vulns
                ],
            }
        )

    args.salida.write_text(
        json.dumps({"dependencies": dependencias}, indent=1), encoding="utf-8"
    )
    print(
        f"{len(paquetes)} paquetes consultados, {len(dependencias)} con avisos conocidos "
        f"→ {args.salida}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

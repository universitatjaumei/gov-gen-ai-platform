"""Exporta el catálogo de plantillas demo a ficheros versionados (D.7).

Deploy: cloud (operación)

**Por qué a ficheros y no por volcado de la base.** El catálogo que acompaña al producto y los
datos operativos del cliente viajan de forma distinta, y confundirlos es lo que hacía que la
pregunta «¿qué pasa al piloto?» no tuviera buena respuesta:

- El **catálogo** —las plantillas demo— se exporta aquí a `server/app/data/plantillas_demo/` y lo
  siembra `bootstrap.py --con-demo`. Así la demo es reproducible, se revisa en un diff, y es la
  misma en todos los despliegues. Es la regla que ya rige el vocabulario del corpus: lo que
  define el producto es dato versionado, no una fila que alguien tenía en su portátil.
- Los **datos operativos** —corpus, curación, chatbots— van por `scripts/volcado_piloto.sh`, con
  lista explícita de tablas y filtro por organización.

**La lista vive aquí, en el código, y no se deduce.** Ni de `is_global`, ni de la fecha, ni del
perfil: en la base de desarrollo hay más de veinte plantillas y casi todas son basura de
verificación (`PRO4 …`, `VER3 …`, `Plantilla prueba Camino3 repro3`). Deducir cuáles son demo por
una propiedad las arrastraría, y el día que alguien cree una plantilla de pruebas «global» se
colaría sin que nadie lo decida.

Uso:
    uv run python -m server.app.scripts.exportar_plantillas_demo [--salida DIR] [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

DESTINO_POR_OMISION = Path(__file__).resolve().parents[1] / "data" / "plantillas_demo"


@dataclass(frozen=True)
class PlantillaDemo:
    """Una plantilla del catálogo, con el nombre con el que se publica y por qué está."""

    #: Nombre tal como está en la base de origen.
    nombre_origen: str
    #: Nombre con el que se siembra. Distinto cuando el de origen es un nombre de trabajo.
    nombre_publicado: str
    #: Fichero de salida.
    fichero: str
    #: Por qué esta plantilla forma parte del producto.
    razon: str


#: El catálogo. Tres entradas, y la segunda todavía no existe: se añade cuando el usuario la
#: prepare en las pruebas manuales. Dejarla declarada y ausente es mejor que olvidarla, porque
#: el exportador avisa de que falta en vez de callarse.
CATALOGO: tuple[PlantillaDemo, ...] = (
    PlantillaDemo(
        nombre_origen="Informe anual de seguimiento — Doctorado (criterios 1 y 2)",
        nombre_publicado="Informe anual de seguimiento — Doctorado (criterios 1 y 2)",
        fichero="informe_seguimiento_doctorado.json",
        razon=(
            "El caso guía del módulo: tablas deterministas por plantilla más valoración de la "
            "IA con revisión humana obligatoria. Es la plantilla de la que salieron las dos "
            "reglas duras del módulo de informes."
        ),
    ),
    PlantillaDemo(
        nombre_origen="GUI3 ejecucion presupuestaria",
        nombre_publicado="Ejecución presupuestaria",
        fichero="ejecucion_presupuestaria.json",
        razon=(
            "Ejercita la cadena entera sobre una hoja de cálculo: hueco `excel`, conversión de "
            "importes en formato español, columna calculada, orden, tabla, gráfico y resumen de "
            "IA con revisión. Se renombra porque `GUI3` es el nombre de un prompt de "
            "verificación, no de un producto. Su juego de datos está en "
            "`pruebas_manuales/datos/ejecucion_presupuestaria_demo.xlsx`."
        ),
    ),
    PlantillaDemo(
        nombre_origen="Económica — saldo de cuentas de tesorería",
        nombre_publicado="Económica — saldo de cuentas de tesorería",
        fichero="saldo_cuentas_tesoreria.json",
        razon=(
            "La tercera del catálogo. **Todavía no existe**: la prepara una persona en las "
            "pruebas manuales y se exporta después. Está declarada para que su ausencia sea "
            "visible en cada exportación en vez de olvidarse."
        ),
    ),
)

#: Plantillas que hay que **borrar**, no exportar, y por qué. Se declaran aquí para que el
#: borrado sea una decisión escrita y no un `DELETE` a mano en producción.
A_BORRAR: tuple[tuple[str, str], ...] = (
    (
        "Ejecucion presupuestaria trimestral",
        "Su `spec_json` son 2 bytes (`{}`): se eligió por tener el nombre más limpio y está "
        "vacía. Sembrarla daría una plantilla que se abre y no tiene nada dentro, y el fallo "
        "aparecería en el piloto y no aquí.",
    ),
)


class SpecVacia(ValueError):
    """El `spec_json` de una versión no tiene contenido."""


def esta_vacia(spec: object) -> bool:
    """Un `{}` —o algo que no sea un mapa con claves— no es una plantilla."""
    return not isinstance(spec, dict) or not spec


def a_documento(plantilla: PlantillaDemo, fila, versiones: list) -> dict:
    """El JSON que se escribe: la plantilla y **todas** sus versiones.

    Todas y no sólo la vigente: una plantilla sin historial no se puede revertir, y el
    versionado append-only del módulo existe precisamente para eso.
    """
    return {
        "nombre": plantilla.nombre_publicado,
        "nombre_origen": plantilla.nombre_origen,
        "razon": plantilla.razon,
        "descripcion": fila.description,
        "report_profile": fila.report_profile,
        "versiones": [
            {"version": v.version, "spec_json": v.spec_json} for v in versiones
        ],
        "version_vigente": next(
            (v.version for v in versiones if v.id == fila.current_version_id), None
        ),
    }


async def _exportar(destino: Path, dry_run: bool) -> int:
    from sqlalchemy import select

    from server.app.modules.agents_hub.database.connection import (
        create_session_factory,
        get_engine,
    )
    from server.app.modules.redaccion.database.models import (
        HubReportTemplate,
        HubReportTemplateVersion,
    )

    fabrica = create_session_factory(get_engine())
    problemas = 0

    async with fabrica() as sesion:
        for plantilla in CATALOGO:
            fila = (
                await sesion.execute(
                    select(HubReportTemplate).where(
                        HubReportTemplate.name == plantilla.nombre_origen
                    )
                )
            ).scalars().first()

            if fila is None:
                print(f"  [FALTA]    {plantilla.nombre_origen}")
                print(f"             {plantilla.razon}")
                continue

            versiones = list(
                (
                    await sesion.execute(
                        select(HubReportTemplateVersion)
                        .where(HubReportTemplateVersion.template_id == fila.id)
                        .order_by(HubReportTemplateVersion.version)
                    )
                ).scalars()
            )

            vacias = [v.version for v in versiones if esta_vacia(v.spec_json)]
            if not versiones or vacias:
                print(
                    f"  [VACIA]    {plantilla.nombre_origen} "
                    f"(versiones sin contenido: {vacias or 'ninguna versión'})"
                )
                problemas += 1
                continue

            documento = a_documento(plantilla, fila, versiones)
            ruta = destino / plantilla.fichero
            if dry_run:
                print(
                    f"  [seria]    {ruta.name} "
                    f"({len(versiones)} versión(es), {len(json.dumps(documento))} B)"
                )
            else:
                destino.mkdir(parents=True, exist_ok=True)
                ruta.write_text(
                    json.dumps(documento, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                print(
                    f"  [escrita]  {ruta.name} "
                    f"({len(versiones)} versión(es), {ruta.stat().st_size} B)"
                )

        print()
        print("== Plantillas a borrar de la base de origen ==")
        for nombre, razon in A_BORRAR:
            existe = (
                await sesion.execute(
                    select(HubReportTemplate.id).where(HubReportTemplate.name == nombre)
                )
            ).scalars().first()
            estado = "existe todavía" if existe else "ya no está"
            print(f"  {nombre} — {estado}")
            print(f"    {razon}")

    return problemas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=DESTINO_POR_OMISION)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    print("== Catálogo de plantillas demo ==")
    print(f"  destino: {args.salida}")
    print(f"  declaradas: {len(CATALOGO)}")
    print()

    problemas = asyncio.run(_exportar(args.salida, args.dry_run))

    if problemas:
        print()
        print(
            f"ERROR: {problemas} plantilla(s) con `spec_json` vacío. No se exportan: sembrar "
            "un `{}` da una plantilla que se abre y no tiene nada dentro.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

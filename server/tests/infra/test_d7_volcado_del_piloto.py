"""Qué datos llegan al piloto: lista explícita, y la guarda sobre el fichero (D.7).

Antes de esto la pregunta «¿qué pasa al piloto?» sólo tenía dos respuestas y las dos eran
malas: un volcado completo —que arrastra 29 informes de prueba y toda la basura de test— o
empezar de cero, tirando el corpus curado y los hallazgos ya revisados por una persona.

Tres invariantes, y el orden importa:

- **Lista de inclusión, no de exclusión.** Una lista de «todo menos X» se queda corta el día
  que alguien añade una tabla, y los datos de más viajan sin que nadie lo decida. Con inclusión,
  una tabla nueva se queda fuera por omisión — el lado seguro del error.
- **La comprobación va sobre el FICHERO, no sobre la consulta.** Un filtro mal escrito produce
  un `WHERE` que pasa los tests de la consulta y datos de más en el volcado. Esa diferencia es
  justo la que importa.
- **El catálogo del producto no viaja como filas.** Las plantillas demo se exportan a ficheros
  versionados y las siembra `bootstrap.py --con-demo`: así la demo se revisa en un diff y es la
  misma en todos los despliegues. Es la regla que ya rige el vocabulario del corpus.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
VOLCADO = RAIZ / "scripts" / "volcado_piloto.sh"

_BASH = shutil.which("bash") or "bash"

#: Entradas "tabla|razón" de cada lista del guion.
_ENTRADA = re.compile(r'^\s*"(hub_[a-z_]+)\|([^"]*)"\s*$', re.MULTILINE)


def _texto() -> str:
    assert VOLCADO.is_file(), f"Falta {VOLCADO.relative_to(RAIZ).as_posix()}"
    return VOLCADO.read_text(encoding="utf-8")


def _bloque(nombre: str) -> str:
    """El cuerpo del array `nombre=( … )` del guion."""
    texto = _texto()
    inicio = texto.index(f"{nombre}=(")
    return texto[inicio : texto.index("\n)", inicio)]


def _tablas(nombre: str) -> dict[str, str]:
    return {t: r for t, r in _ENTRADA.findall(_bloque(nombre))}


def _run(*args: str, env: dict[str, str] | None = None):
    return subprocess.run(
        [_BASH, str(VOLCADO), *args],
        cwd=RAIZ, capture_output=True, text=True, timeout=60,
        env={**os.environ, **(env or {})},
    )


# ---------------------------------------------------------------------------
# Las dos listas
# ---------------------------------------------------------------------------


def test_las_dos_listas_son_explicitas_y_cada_tabla_dice_por_que() -> None:
    viajan = _tablas("TABLAS")
    no_viajan = _tablas("PROHIBIDAS")
    assert viajan, "La lista de tablas que viajan está vacía."
    assert no_viajan, "La lista de tablas prohibidas está vacía."
    for tabla, razon in {**viajan, **no_viajan}.items():
        assert razon.strip(), f"{tabla} no dice por qué está en su lista"


def test_ninguna_tabla_esta_en_las_dos_listas() -> None:
    solapan = set(_tablas("TABLAS")) & set(_tablas("PROHIBIDAS"))
    assert not solapan, f"Tablas en las dos listas a la vez: {sorted(solapan)}"


def test_no_viaja_ningun_informe_ni_ninguna_persona() -> None:
    """Los dos grupos que el prompt saca por decisión, no por descuido."""
    viajan = set(_tablas("TABLAS"))
    no_viajan = set(_tablas("PROHIBIDAS"))
    for tabla in ("hub_workspaces", "hub_workspace_blocks", "hub_workspace_audit_events",
                  "hub_run_manifests", "hub_users", "hub_personal_access_tokens"):
        assert tabla not in viajan, f"{tabla} NO puede viajar al piloto"
        assert tabla in no_viajan, (
            f"{tabla} tiene que estar en la lista de prohibidas, para que se COMPRUEBE que no "
            "está en el fichero — no basta con no listarla"
        )


def test_no_viajan_las_conversaciones() -> None:
    """Son de quien preguntó, no del despliegue."""
    assert "hub_interactions" in _tablas("PROHIBIDAS")
    assert "hub_interactions" not in _tablas("TABLAS")


def test_el_catalogo_de_plantillas_no_viaja_como_filas() -> None:
    """Se exporta a ficheros versionados y lo siembra `bootstrap.py --con-demo`."""
    for tabla in ("hub_report_templates", "hub_report_template_versions"):
        assert tabla in _tablas("PROHIBIDAS"), (
            f"{tabla} tiene que quedar fuera: el catálogo del producto es dato versionado, no "
            "una fila que alguien tenía en su portátil"
        )


def test_viaja_lo_que_costaria_rehacer() -> None:
    """El corpus, sus vectores, el vocabulario y el trabajo humano de la curación."""
    viajan = _tablas("TABLAS")
    for tabla in ("hub_organizaciones", "hub_chatbots", "hub_documents", "hub_document_chunks",
                  "hub_vocabulary_terms", "hub_web_sites", "hub_crawled_pages",
                  "hub_content_findings"):
        assert tabla in viajan, f"Falta {tabla}: es lo que costaría rehacer"


def test_los_fragmentos_viajan_porque_reembeber_cuesta() -> None:
    razon = _tablas("TABLAS").get("hub_document_chunks", "")
    assert "reembeber" in razon.lower() or "gpu" in razon.lower(), (
        "La razón de llevarse los fragmentos tiene que estar dicha: un vector se regenera con "
        "GPU y horas, no con un UPDATE."
    )


# ---------------------------------------------------------------------------
# La guarda, que va sobre el fichero
# ---------------------------------------------------------------------------


def test_la_verificacion_se_hace_sobre_el_fichero_generado() -> None:
    texto = _texto()
    assert re.search(r'grep -qE "COPY \(public\\?\.\)\?\$tabla ', texto), (
        "Las tablas prohibidas se buscan en el volcado ya generado: un filtro mal escrito pasa "
        "los tests de la consulta y deja datos de más en el fichero."
    )
    assert "hub_organizaciones WHERE id <> " in texto, (
        "Hay que comprobar que no aparece ninguna OTRA organización en el fichero."
    )


def test_un_volcado_con_datos_de_mas_se_borra() -> None:
    """Dejarlo en el disco es dejar el fichero que alguien restaura por error."""
    texto = _texto()
    assert re.search(r'rm -f "\$SALIDA"', texto), (
        "Si la verificación falla, el fichero tiene que borrarse."
    )


def test_se_cuenta_antes_de_escribir() -> None:
    texto = _texto()
    assert "Recuento en origen" in texto
    # La INVOCACIÓN, no cualquier mención: la primera aparición de `pg_dump` en el guion es el
    # `command -v` que comprueba que está instalado, y comparar contra eso medía otra cosa.
    invocacion = texto.index('pg_dump "$DSN_LIBPQ"')
    assert texto.index("Recuento en origen") < invocacion, (
        "El recuento va ANTES de generar el fichero: si las cifras no son las esperadas, se "
        "para sin haber escrito nada."
    )


# ---------------------------------------------------------------------------
# Interfaz
# ---------------------------------------------------------------------------


def test_exige_organizacion_y_salida() -> None:
    for argumentos in (("--salida", "x.sql"), ("--organizacion", "u")):
        resultado = _run(*argumentos, "--dry-run")
        assert resultado.returncode == 2, f"Debería negarse con {argumentos}"


def test_la_conexion_no_esta_cableada() -> None:
    texto = _texto()
    assert "DATABASE_URL_SYNC" in texto
    assert "postgres:5432" not in texto and "localhost" not in texto, (
        "El DSN se lee del entorno; cablearlo apunta al portátil de quien lo escribió."
    )


def test_el_plan_en_seco_enumera_las_dos_listas_y_no_toca_la_base() -> None:
    solo_bash = str(Path(_BASH).parent)
    resultado = _run("--organizacion", "u", "--salida", "x.sql", "--dry-run",
                     env={"PATH": solo_bash, "DATABASE_URL_SYNC": ""})
    assert resultado.returncode == 0, resultado.stderr
    assert "Viajan" in resultado.stdout and "NO viajan" in resultado.stdout
    for tabla in ("hub_documents", "hub_workspaces"):
        assert tabla in resultado.stdout, f"{tabla} no aparece en el plan"

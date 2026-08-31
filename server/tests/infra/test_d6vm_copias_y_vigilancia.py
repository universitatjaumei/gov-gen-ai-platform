"""Copias, vigilancia y publicación: la contrapartida de haber elegido una VM (D.6-VM).

Un servicio gestionado trae el reinicio, el registro y la salud gratis. Una VM no, y sin esto
la primera noticia de una caída la da un usuario.

Lo que estos tests fijan es lo que se rompe **sin ruido**:

- **Que las alertas lleguen a alguien.** Un correo obligatorio, porque una alerta que no llega
  a una persona no es una alerta; es un gráfico.
- **Que la comprobación de salud valide el certificado.** Con TLS mal renovado el servicio
  responde y una comprobación sin `validateSsl` pasaría — justo el fallo que nadie ve venir.
- **Que el agente de operaciones esté.** Sin él, Cloud Monitoring sólo ve la máquina desde
  fuera (CPU y red): las alertas de memoria y disco no se podrían ni escribir, y el disco lleno
  por logs es la avería más común de una VM.
- **Que los logs roten en local.** Un envío remoto no protege el disco: si la red falla, el
  fichero sigue creciendo.
- **Que el guion no dependa de `python3`.** La primera versión lo usaba para leer JSON y se
  rompió en Git Bash con un «curl: Failed writing body» que no señalaba a la causa.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
VIGILANCIA = RAIZ / "scripts" / "gcp_provision_vigilancia.sh"
STARTUP = RAIZ / "deploy" / "vm" / "startup.sh"
RUNBOOK = RAIZ / "docs" / "RUNBOOK_REINGESTA.md"
WIDGET = RAIZ / "docs" / "WIDGET_INCRUSTACION.md"

_BASH = shutil.which("bash") or "bash"


def _texto(ruta: Path) -> str:
    assert ruta.is_file(), f"Falta {ruta.relative_to(RAIZ).as_posix()}"
    return ruta.read_text(encoding="utf-8")


def _run(*args: str, env: dict[str, str] | None = None):
    return subprocess.run(
        [_BASH, str(VIGILANCIA), *args],
        cwd=RAIZ, capture_output=True, text=True, timeout=60,
        env={**os.environ, **(env or {})},
    )


# ---------------------------------------------------------------------------
# Vigilancia
# ---------------------------------------------------------------------------


def test_exige_a_quien_avisar() -> None:
    """Sin destinatario no hay alerta: hay un gráfico que nadie mira."""
    resultado = _run("--project", "p", "--host", "h", "--dry-run")
    assert resultado.returncode == 2, (
        f"Sin --email tiene que negarse.\nsalida: {resultado.stdout}\n{resultado.stderr}"
    )
    assert "no es una alerta" in resultado.stderr


def test_exige_proyecto_y_host() -> None:
    for argumentos in (
        ("--host", "h", "--email", "a@b.c"),
        ("--project", "p", "--email", "a@b.c"),
    ):
        resultado = _run(*argumentos, "--dry-run")
        assert resultado.returncode == 2, f"Debería negarse con {argumentos}"


def test_la_comprobacion_de_salud_valida_el_certificado() -> None:
    texto = _texto(VIGILANCIA)
    assert '"validateSsl": true' in texto, (
        "Sin validar el certificado, un TLS mal renovado pasaría la comprobación: el servicio "
        "responde y el navegador es el único que se queja."
    )
    assert '"path": "/health"' in texto
    assert '"useSsl": true' in texto


def test_declara_las_tres_alertas() -> None:
    texto = _texto(VIGILANCIA)
    for alerta in ("la salud no responde", "memoria por encima", "disco por encima"):
        assert alerta in texto, f"Falta la alerta: {alerta}"


def test_el_guion_no_depende_de_python() -> None:
    """Se ejecuta desde la máquina de quien despliega, y en Git Bash no hay `python3`."""
    texto = _texto(VIGILANCIA)
    activas = [
        l for l in texto.splitlines()
        if "python3" in l and not l.strip().startswith("#")
    ]
    assert not activas, f"El guion sigue dependiendo de python3: {activas}"


def test_dry_run_no_llama_a_ninguna_api() -> None:
    solo_bash = str(Path(_BASH).parent)
    resultado = _run("--project", "p", "--host", "h", "--email", "a@b.c", "--dry-run",
                     env={"PATH": solo_bash})
    assert resultado.returncode == 0, resultado.stderr
    assert "dry-run" in resultado.stdout


# ---------------------------------------------------------------------------
# La máquina: agente y rotación
# ---------------------------------------------------------------------------


def test_el_arranque_instala_el_agente_de_operaciones() -> None:
    texto = _texto(STARTUP)
    assert "ops-agent" in texto, (
        "Sin el agente no hay métricas de memoria ni de disco del huésped, así que las dos "
        "alertas que D.6-VM pide no se podrían ni escribir."
    )


def test_el_despliegue_refresca_el_guion_de_arranque_en_los_metadatos() -> None:
    """Editar `startup.sh` NO cambia la máquina: GCE lo lee de los metadatos de la instancia.

    Se descubrió al cerrar D.6-VM — la VM llevaba horas ejecutando la versión original, así que
    el agente de operaciones y la rotación de logs nunca se instalaron, y **las alertas de
    memoria y disco eran inertes sin que nada lo dijera**. El despliegue lo refresca para que
    lo que corre venga del repositorio y no del estado del disco de la máquina.
    """
    workflow = (RAIZ / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    assert "startup-script=deploy/vm/startup.sh" in workflow, (
        "El despliegue tiene que refrescar el guion de arranque en los metadatos."
    )
    assert "add-metadata" in workflow

    texto = _texto(STARTUP)
    assert "NO cambia la máquina" in texto, (
        "El propio guion tiene que advertirlo: es el defecto que costó descubrirlo."
    )


def test_los_logs_de_contenedor_rotan_en_local() -> None:
    texto = _texto(STARTUP)
    assert "max-size" in texto and "max-file" in texto, (
        "El disco lleno por logs es la avería más común de una VM, y no avisa. Un envío a "
        "Cloud Logging no protege el disco local: si la red falla, el fichero crece igual."
    )


def test_el_agente_recoge_tambien_los_logs_de_los_contenedores() -> None:
    texto = _texto(STARTUP)
    assert "/var/lib/docker/containers" in texto, (
        "Sin este receptor, Cloud Logging tendría los logs del sistema y no los de la "
        "aplicación, que son los que se miran en un incidente."
    )


# ---------------------------------------------------------------------------
# Lo que queda escrito para operar
# ---------------------------------------------------------------------------


def test_el_runbook_de_reingesta_lleva_la_puerta_y_las_dos_comprobaciones() -> None:
    texto = _texto(RUNBOOK)
    assert "--dry-run" in texto, "El plan se lee antes de aplicar; es la puerta del 27-08."
    assert "metadatos=0" in texto, "Falta el invariante de idempotencia del bloque ACT."
    assert "sin fragmentos" in texto, "Falta la comprobación de la fuga que destapó ACT.8."
    assert "única fuente de verdad" in texto, (
        "El runbook tiene que decir cuál de las dos bases manda, o divergirán."
    )


def test_la_documentacion_del_widget_explica_la_credencial_y_su_rotacion() -> None:
    texto = _texto(WIDGET)
    for pieza in ("data-chatbot-id", "data-widget-key", "data-api-url",
                  "public_anon", "CORS_ALLOWED_ORIGINS"):
        assert pieza in texto, f"Falta documentar {pieza}"
    assert "emitir, publicar, revocar" in texto or "revocar la" in texto, (
        "El orden de la rotación importa: al revés deja el widget muerto en producción."
    )
    assert "Contenido mixto" in texto or "contenido mixto" in texto, (
        "Es el fallo que no da error visible en la página; tiene que estar en la guía."
    )

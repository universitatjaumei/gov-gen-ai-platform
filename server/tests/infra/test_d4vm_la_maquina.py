"""La pila de la VM: el estado fuera, el sandbox bajo gVisor y nada duplicado (D.4-VM).

**Por qué existe un compose aparte, que es el hallazgo del prompt.** El bloque Deploy decía que
en una VM esto era «prácticamente `docker compose up -d`» sobre `docker-compose.prod.yml`. No lo
era: ese fichero es la opción *autoinstalable* —lo dice su propia cabecera— y trae **su** Postgres,
**su** MinIO y un perfil de Ollama, con el `DATABASE_URL` del servicio `app` apuntando al
contenedor `postgres`. Levantarlo en GCP habría corrido una base de datos que nadie usa junto a
la que sí, con el mismo nombre de variable. De ahí `deploy/vm/docker-compose.vm.yml`.

Lo que estos tests vigilan es lo que se rompe sin ruido:

- Que el estado no vuelva a entrar en la máquina (ni Postgres, ni MinIO, ni Langfuse).
- Que `runtime: runsc` esté **y sólo** en el sandbox: es la capa 8 que D.0.doc decidió
  conservar, y ponerla en todo mataría el rendimiento sin añadir aislamiento donde importa.
- Que las cabeceras de seguridad no se dupliquen en el proxy. La primera versión del Caddyfile
  escribía `X-Frame-Options: SAMEORIGIN` donde la aplicación dice `DENY`: dos fuentes de verdad
  y la del proxy era la débil.
- Que el 22 no quede abierto al mundo.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
VM = RAIZ / "deploy" / "vm"
COMPOSE = VM / "docker-compose.vm.yml"
CADDYFILE = VM / "Caddyfile"
UNIDAD = VM / "govgenai.service"
STARTUP = VM / "startup.sh"
PROVISION = RAIZ / "scripts" / "gcp_provision_vm.sh"

_BASH = shutil.which("bash") or "bash"


def _texto(ruta: Path) -> str:
    assert ruta.is_file(), f"Falta {ruta.relative_to(RAIZ).as_posix()}"
    return ruta.read_text(encoding="utf-8")


def _servicios() -> list[str]:
    """Nombres de servicio del compose, por indentación (sin cargar YAML)."""
    dentro = False
    nombres: list[str] = []
    for linea in _texto(COMPOSE).splitlines():
        if re.match(r"^services:\s*$", linea):
            dentro = True
            continue
        if dentro:
            if re.match(r"^\S", linea):  # otra clave de primer nivel
                dentro = False
                continue
            m = re.match(r"^  ([a-z0-9][a-z0-9_-]*):\s*$", linea)
            if m:
                nombres.append(m.group(1))
    return nombres


# ---------------------------------------------------------------------------
# El estado vive fuera de la máquina
# ---------------------------------------------------------------------------


def test_la_pila_de_la_vm_no_levanta_base_de_datos_ni_almacenamiento_propios() -> None:
    servicios = _servicios()
    assert servicios, "No se han podido leer los servicios del compose."
    for prohibido in ("postgres", "minio", "langfuse", "ollama"):
        assert prohibido not in servicios, (
            f"El servicio «{prohibido}» no puede correr en la VM: la base está en Cloud SQL y "
            "los documentos en GCS. Si vuelve, el estado regresa al disco de la máquina y "
            "perderla deja de ser inocuo."
        )


def test_la_base_se_alcanza_por_el_auth_proxy_y_no_por_una_ip() -> None:
    texto = _texto(COMPOSE)
    assert "cloud-sql-proxy" in texto, "Falta el Cloud SQL Auth Proxy."
    assert "--unix-socket=/cloudsql" in texto, (
        "El proxy tiene que exponer el socket Unix que espera DATABASE_URL (?host=/cloudsql/...)."
    )
    assert "CLOUDSQL_CONNECTION_NAME" in texto


def test_el_almacenamiento_es_gcs_y_el_entorno_es_produccion() -> None:
    texto = _texto(COMPOSE)
    assert "STORAGE_BACKEND: gcs" in texto
    assert "ENVIRONMENT: production" in texto


def test_la_configuracion_entra_por_el_fichero_que_escribe_secret_manager() -> None:
    """Ningún `.env` mantenido a mano en la máquina: lo monta `vm_fetch_secrets.sh`."""
    texto = _texto(COMPOSE)
    assert "/opt/govgenai/.env.runtime" in texto
    assert "server/.env" not in texto, (
        "El compose de la VM no puede leer el .env del repositorio."
    )


# ---------------------------------------------------------------------------
# La capa 8, donde toca y sólo donde toca
# ---------------------------------------------------------------------------


def test_solo_el_sandbox_corre_bajo_gvisor() -> None:
    texto = _texto(COMPOSE)
    # Sólo líneas activas: el comentario que explica la decisión también nombra la directiva.
    activas = [
        l for l in texto.splitlines()
        if "runtime: runsc" in l and not l.strip().startswith("#")
    ]
    assert len(activas) == 1, (
        f"`runtime: runsc` está activo {len(activas)} veces. Va sólo en el sandbox: es el "
        "único servicio que ejecuta código que no hemos escrito, y ponerlo en todo cuesta "
        f"rendimiento sin añadir aislamiento donde importa. {activas}"
    )
    # …y que esa aparición esté dentro del bloque del sandbox. Se ancla a la clave del
    # servicio (dos espacios de indentación): «script-sandbox» a secas también aparece como
    # host en `SANDBOX_BASE_URL` del servicio `app`, y partir por ahí leía el bloque
    # equivocado — el primer intento de este test cayó justo en eso.
    bloque = re.split(r"\n  script-sandbox:\s*\n", texto, maxsplit=1)
    assert len(bloque) == 2, "No se encuentra el servicio script-sandbox."
    siguiente = re.split(r"\n  [a-z0-9][a-z0-9_-]*:\s*\n", bloque[1], maxsplit=1)[0]
    assert "runtime: runsc" in siguiente, "`runtime: runsc` no está en el sandbox."


def test_el_arranque_instala_gvisor_con_la_plataforma_que_funciona_en_una_vm() -> None:
    texto = _texto(STARTUP)
    assert "runsc" in texto, "El guion de arranque tiene que instalar gVisor."
    assert "systrap" in texto, (
        "La plataforma tiene que ser `systrap`: `kvm` exige /dev/kvm, o sea virtualización "
        "anidada, que GCE no da en todos los tipos de máquina."
    )


def test_el_sandbox_conserva_las_capas_que_ya_tenia() -> None:
    """No se «mejoran» ni se pierden al copiar el servicio a otro fichero."""
    texto = _texto(COMPOSE)
    for capa in ('cap_drop: ["ALL"]', "no-new-privileges:true", 'user: "65534:65534"',
                 "read_only: true", "pids_limit: 128"):
        assert capa in texto, f"El sandbox de la VM ha perdido: {capa}"
    assert "internal: true" in texto, "La red del sandbox tiene que seguir sin salida."


# ---------------------------------------------------------------------------
# El proxy no duplica lo que ya hace la aplicación
# ---------------------------------------------------------------------------


def test_el_proxy_no_repite_las_cabeceras_de_seguridad_de_la_aplicacion() -> None:
    texto = _texto(CADDYFILE)
    for cabecera in ("X-Frame-Options", "Strict-Transport-Security",
                     "X-Content-Type-Options", "Referrer-Policy"):
        # Se permite nombrarla en un comentario que explica por qué NO se pone.
        activas = [
            l for l in texto.splitlines()
            if cabecera in l and not l.strip().startswith("#")
        ]
        assert not activas, (
            f"{cabecera} la pone `server/app/core/security_headers.py`. Repetirla aquí crea "
            f"dos fuentes de verdad para la misma cabecera: {activas}"
        )


def test_el_proxy_pasa_la_api_y_la_salud_a_la_aplicacion() -> None:
    texto = _texto(CADDYFILE)
    assert "handle /api/*" in texto and "reverse_proxy app:8000" in texto
    assert "handle /health" in texto
    assert "{$GOVGENAI_HOST}" in texto, (
        "El host tiene que llegar por entorno: hoy es un sslip.io y mañana el subdominio."
    )


def test_el_proxy_no_abre_docs_porque_lo_cierra_la_aplicacion() -> None:
    texto = _texto(CADDYFILE)
    activas = [l for l in texto.splitlines() if "/docs" in l and not l.strip().startswith("#")]
    assert not activas, f"`/docs` lo apaga SEC.7 en la aplicación; no se enruta aquí: {activas}"


# ---------------------------------------------------------------------------
# Arranque tras reinicio
# ---------------------------------------------------------------------------


def test_la_unidad_systemd_levanta_la_pila_y_baja_los_secretos_antes() -> None:
    texto = _texto(UNIDAD)
    assert "WantedBy=multi-user.target" in texto, (
        "Sin esto la máquina reinicia y el sistema se queda apagado hasta que alguien entra."
    )
    assert "vm_fetch_secrets.sh" in texto, (
        "Los secretos se rebajan en cada arranque: rotar es cambiar el secreto y reiniciar."
    )
    assert "docker compose" in texto and "docker-compose.vm.yml" in texto
    assert "unless-stopped" in _texto(COMPOSE), (
        "Lo que mantiene los contenedores en pie entre fallos es `restart: unless-stopped`."
    )


# ---------------------------------------------------------------------------
# Aprovisionamiento
# ---------------------------------------------------------------------------


def test_el_22_no_queda_abierto_al_mundo() -> None:
    texto = _texto(PROVISION)
    assert "35.235.240.0/20" in texto, "El SSH tiene que entrar sólo por el rango de IAP."
    reglas_22 = [l for l in texto.splitlines() if "tcp:22" in l]
    assert reglas_22, "No se encuentra la regla del 22."
    for linea in reglas_22:
        assert "0.0.0.0/0" not in linea, f"22 abierto a Internet: {linea.strip()}"


def test_la_maquina_usa_cuenta_propia_y_no_la_de_por_defecto_de_compute() -> None:
    texto = _texto(PROVISION)
    assert "--service-account=" in texto
    # El correo se compone en el guion, así que se comprueba en su plan y no como literal.
    solo_bash = str(Path(_BASH).parent)
    seco = subprocess.run(
        [_BASH, str(PROVISION), "--project", "proyecto-de-prueba", "--dry-run"],
        cwd=RAIZ, capture_output=True, text=True, timeout=60,
        env={**os.environ, "PATH": solo_bash},
    )
    assert "govgenai-vm@proyecto-de-prueba.iam.gserviceaccount.com" in seco.stdout, (
        f"El plan no declara la cuenta de servicio propia:\n{seco.stdout}"
    )
    for rol in ("roles/cloudsql.client", "roles/artifactregistry.reader"):
        assert rol in texto, f"Falta el rol mínimo {rol}"
    assert "roles/editor" not in texto and "roles/owner" not in texto


def test_la_ip_es_estatica_porque_el_nombre_del_host_depende_de_ella() -> None:
    texto = _texto(PROVISION)
    assert "compute addresses create" in texto
    assert "sslip.io" in texto, (
        "El guion tiene que decir qué nombre usar con esa IP: es lo que va al certificado y "
        "al ASSISTENT_API de las páginas publicadas."
    )


def test_el_tamano_de_la_maquina_es_el_medido() -> None:
    texto = _texto(PROVISION)
    assert "e2-small" in texto
    assert "345 MB" in texto, (
        "El tamaño se justifica con la medición de D.4.0, no con una estimación."
    )


def test_el_aprovisionamiento_exige_proyecto_y_su_plan_en_seco_no_toca_nada() -> None:
    sin_proyecto = subprocess.run(
        [_BASH, str(PROVISION), "--dry-run"],
        cwd=RAIZ, capture_output=True, text=True, timeout=60,
    )
    assert sin_proyecto.returncode == 2, "Sin --project tiene que negarse."

    solo_bash = str(Path(_BASH).parent)
    seco = subprocess.run(
        [_BASH, str(PROVISION), "--project", "proyecto-de-prueba", "--dry-run"],
        cwd=RAIZ, capture_output=True, text=True, timeout=60,
        env={**os.environ, "PATH": solo_bash},
    )
    assert seco.returncode == 0, seco.stderr
    assert "dry-run" in seco.stdout

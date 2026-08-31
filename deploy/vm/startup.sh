#!/usr/bin/env bash
#
# Guion de arranque de la VM (D.4-VM). Lo ejecuta GCE en el primer arranque y en cada
# reinicio, así que **tiene que ser idempotente**: comprueba antes de instalar.
#
# ⚠️ **Editar este fichero NO cambia la máquina.** GCE lo lee de los metadatos de la instancia,
# fijados al crearla, así que un cambio aquí no llega sola ni reiniciando: hay que refrescar los
# metadatos y volver a ejecutarlo.
#
#     gcloud compute instances add-metadata govgenai-vm --zone europe-southwest1-b \
#         --metadata-from-file startup-script=deploy/vm/startup.sh
#     gcloud compute ssh govgenai-vm --zone europe-southwest1-b --tunnel-through-iap \
#         --command "sudo google_metadata_script_runner startup"
#
# Se descubrió al cerrar D.6-VM: la máquina llevaba horas ejecutando la versión original de este
# guion, así que el agente de operaciones y la rotación de logs **nunca se instalaron** —y sin el
# agente, las alertas de memoria y disco no pueden dispararse—. El despliegue de D.5-VM refresca
# los metadatos por eso: lo que corre tiene que venir del repositorio, no del estado del disco.
#
# Ojo al aplicarlo en caliente: el bloque de rotación reinicia Docker, así que los contenedores
# se reinician. Vuelven solos por `restart: unless-stopped`, pero no es una operación invisible.
#
# Instala lo que la máquina necesita y nada más:
#   - Docker + plugin de Compose        (la pila)
#   - gVisor (`runsc`)                  (capa 8 del sandbox; ver docs/SANDBOX_SECURITY.md)
#   - google-cloud-cli                  (lo usa vm_fetch_secrets.sh para leer Secret Manager)
#
# NO instala Postgres, MinIO ni Langfuse: el estado vive en Cloud SQL y GCS, y Langfuse no cabe
# en 2 GB (su v3 exige Clickhouse) además de degradar a no-op sin clave.

set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

log() { echo "[startup] $*"; }

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  log "instalando Docker"
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg \
    -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
else
  log "Docker ya está"
fi

# ---------------------------------------------------------------------------
# gVisor — la capa 8, que aquí la ponemos nosotros
#
# Plataforma `systrap` y no `kvm`: `kvm` necesita /dev/kvm, o sea virtualización anidada, que
# en GCE no está en todos los tipos de máquina. `systrap` funciona en cualquier VM y el coste
# es irrelevante para scripts que duran segundos.
# ---------------------------------------------------------------------------
if ! command -v runsc >/dev/null 2>&1; then
  log "instalando gVisor (runsc)"
  apt-get install -y -qq apt-transport-https ca-certificates curl gnupg
  curl -fsSL https://gvisor.dev/archive.key | gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" \
    > /etc/apt/sources.list.d/gvisor.list
  apt-get update -qq
  apt-get install -y -qq runsc
else
  log "gVisor ya está"
fi

# Registrar runsc como runtime de Docker, sin pisar el resto de la configuración.
if ! grep -q '"runsc"' /etc/docker/daemon.json 2>/dev/null; then
  log "registrando runsc como runtime de Docker"
  runsc install -- --platform=systrap
  systemctl restart docker
else
  log "runsc ya está registrado"
fi

# ---------------------------------------------------------------------------
# gcloud — lo necesita vm_fetch_secrets.sh
# ---------------------------------------------------------------------------
if ! command -v gcloud >/dev/null 2>&1; then
  log "instalando google-cloud-cli"
  curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
  echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
    > /etc/apt/sources.list.d/google-cloud-sdk.list
  apt-get update -qq
  apt-get install -y -qq google-cloud-cli
else
  log "gcloud ya está"
fi

# ---------------------------------------------------------------------------
# Autenticar Docker contra Artifact Registry
#
# Tener el rol `artifactregistry.reader` en la cuenta de la VM **no basta**: el demonio de
# Docker no sabe usarlo hasta que se instala el ayudante de credenciales. Sin esto, el `pull`
# falla con «Unauthenticated request. Unauthenticated requests do not have permission
# artifactregistry.repositories.downloadArtifacts», que suena a permiso ausente y es un
# ayudante ausente. El cuarto despliegue real murió exactamente ahí.
#
# Se escribe en la configuración de root porque la pila se levanta con `sudo`.
# ---------------------------------------------------------------------------
AR_REGION="$(curl -fsS -H 'Metadata-Flavor: Google' \
  http://metadata.google.internal/computeMetadata/v1/instance/attributes/ar-region \
  2>/dev/null || true)"
[ -n "$AR_REGION" ] || AR_REGION="europe-southwest1"

if ! grep -q "$AR_REGION-docker.pkg.dev" /root/.docker/config.json 2>/dev/null; then
  log "autenticando Docker contra $AR_REGION-docker.pkg.dev"
  gcloud auth configure-docker "$AR_REGION-docker.pkg.dev" --quiet
else
  log "Docker ya autenticado contra Artifact Registry"
fi

# ---------------------------------------------------------------------------
# Rotación local de los logs de contenedor
#
# El disco lleno por logs es la avería más aburrida y más común de una VM, y la que no avisa:
# el sistema simplemente deja de escribir. `json-file` con techo y rotación pone el límite
# donde se genera. Cloud Logging se lleva una copia (abajo), pero un envío remoto no protege
# el disco local — si la red falla, el fichero sigue creciendo.
# ---------------------------------------------------------------------------
if ! grep -q '"log-driver"' /etc/docker/daemon.json 2>/dev/null; then
  log "fijando rotación de logs de contenedor"
  python3 - <<'PY'
import json, pathlib
ruta = pathlib.Path("/etc/docker/daemon.json")
datos = json.loads(ruta.read_text()) if ruta.exists() else {}
datos["log-driver"] = "json-file"
datos["log-opts"] = {"max-size": "10m", "max-file": "3"}
ruta.write_text(json.dumps(datos, indent=2))
PY
  systemctl restart docker
else
  log "rotación de logs ya configurada"
fi

# ---------------------------------------------------------------------------
# Agente de operaciones
#
# Sin él NO hay métricas de memoria ni de disco del huésped, así que las alertas que D.6-VM
# pide no se pueden ni escribir: Cloud Monitoring sólo ve la máquina desde fuera (CPU, red).
# Es la diferencia entre «el disco se llenó» y «alguien avisó antes».
# ---------------------------------------------------------------------------
if ! systemctl is-enabled google-cloud-ops-agent >/dev/null 2>&1; then
  log "instalando el agente de operaciones"
  curl -fsSL https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh \
    -o /tmp/add-ops-agent.sh
  bash /tmp/add-ops-agent.sh --also-install
  rm -f /tmp/add-ops-agent.sh
else
  log "el agente de operaciones ya está"
fi

# Que el agente recoja además los logs de los contenedores, no sólo los del sistema.
if [ ! -f /etc/google-cloud-ops-agent/config.yaml ]; then
  mkdir -p /etc/google-cloud-ops-agent
  cat > /etc/google-cloud-ops-agent/config.yaml <<'YAML'
logging:
  receivers:
    contenedores:
      type: files
      include_paths:
        - /var/lib/docker/containers/*/*-json.log
  service:
    pipelines:
      contenedores:
        receivers: [contenedores]
YAML
  systemctl restart google-cloud-ops-agent || true
fi

mkdir -p /opt/govgenai/scripts
chmod 755 /opt/govgenai

# El directorio donde el Cloud SQL Auth Proxy monta su socket. **Con dueño 65532**, que es el
# uid con el que corre su imagen: un volumen de Docker nuevo nace de root con 0755 y el proxy
# no puede crear dentro, así que muere con «Unable to mount socket: mkdir …: permission
# denied» y reintenta en bucle. Por eso es un directorio del anfitrión y no un volumen.
mkdir -p /opt/govgenai/cloudsql
chown 65532:65532 /opt/govgenai/cloudsql
chmod 755 /opt/govgenai/cloudsql

log "listo. Falta desplegar: copiar docker-compose.vm.yml, Caddyfile, .env.despliegue,"
log "scripts/vm_fetch_secrets.sh + scripts/lib/secretos.tsv, y habilitar govgenai.service (D.5-VM)."

#!/usr/bin/env bash
#
# Guion de arranque de la VM (D.4-VM). Lo ejecuta GCE en el primer arranque y en cada
# reinicio, así que **tiene que ser idempotente**: comprueba antes de instalar.
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

mkdir -p /opt/govgenai/scripts
chmod 755 /opt/govgenai

log "listo. Falta desplegar: copiar docker-compose.vm.yml, Caddyfile, .env.despliegue,"
log "scripts/vm_fetch_secrets.sh + scripts/lib/secretos.tsv, y habilitar govgenai.service (D.5-VM)."

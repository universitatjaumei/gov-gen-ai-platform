#!/usr/bin/env bash
#
# Aprovisiona la VM del despliegue (D.4-VM): cuenta de servicio, permisos, cortafuegos, IP
# estática y máquina. Idempotente y versionado — nada de clics, porque un recurso creado a mano
# no se puede volver a crear igual cuando haga falta.
#
# Tamaño MEDIDO, no estimado (EXT.3 y D.4.0): sin el extra `local-models`, que es este
# despliegue, la aplicación son 345 MB de RSS. `e2-small` (2 GB) es holgado. `e2-medium` sólo
# haría falta en un edge que instale los modelos locales.
#
# El estado vive fuera de la máquina a propósito: la base en Cloud SQL y los documentos en GCS.
# El disco de la VM sólo guarda sistema, imágenes y logs, así que perderla no pierde nada.
#
# Uso:
#   scripts/gcp_provision_vm.sh --project <ID> [--zone europe-southwest1-b]
#                               [--machine-type e2-small] [--bucket <BUCKET>]
#                               [--name govgenai-vm] [--dry-run]

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STARTUP="$RAIZ/deploy/vm/startup.sh"

PROYECTO=""
ZONA="europe-southwest1-b"
TIPO="e2-small"
NOMBRE="govgenai-vm"
BUCKET=""
SA_NOMBRE="govgenai-vm"
DRY_RUN=0

uso() {
  echo "Uso: $0 --project <ID> [--zone <ZONA>] [--machine-type <TIPO>] [--bucket <BUCKET>]" >&2
  echo "        [--name <NOMBRE>] [--dry-run]" >&2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --project)        PROYECTO="${2:-}"; shift 2 ;;
    --project=*)      PROYECTO="${1#*=}"; shift ;;
    --zone)           ZONA="${2:-}"; shift 2 ;;
    --zone=*)         ZONA="${1#*=}"; shift ;;
    --machine-type)   TIPO="${2:-}"; shift 2 ;;
    --machine-type=*) TIPO="${1#*=}"; shift ;;
    --name)           NOMBRE="${2:-}"; shift 2 ;;
    --name=*)         NOMBRE="${1#*=}"; shift ;;
    --bucket)         BUCKET="${2:-}"; shift 2 ;;
    --bucket=*)       BUCKET="${1#*=}"; shift ;;
    --dry-run)        DRY_RUN=1; shift ;;
    -h|--help)        uso; exit 0 ;;
    *) echo "ERROR: opción desconocida: $1" >&2; uso; exit 2 ;;
  esac
done

if [ -z "$PROYECTO" ]; then
  echo "ERROR: falta --project. Sin proyecto explícito no se crean máquinas." >&2
  uso
  exit 2
fi

REGION="${ZONA%-*}"
SA_EMAIL="$SA_NOMBRE@$PROYECTO.iam.gserviceaccount.com"
ETIQUETA="govgenai"
IP_NOMBRE="$NOMBRE-ip"

# Roles a nivel de proyecto. Lo MÍNIMO, y no la cuenta por defecto de Compute, que viene con
# permisos de editor sobre todo el proyecto.
ROLES=(
  "roles/cloudsql.client"            # conectar por el Auth Proxy
  "roles/logging.logWriter"          # logs de los contenedores (D.6-VM)
  "roles/monitoring.metricWriter"    # métricas y alertas (D.6-VM)
  "roles/artifactregistry.reader"    # bajar la imagen que publica CI (D.5-VM)
)

echo "== Aprovisionamiento de la VM =="
printf '  %-18s %s\n' "proyecto" "$PROYECTO"
printf '  %-18s %s\n' "zona" "$ZONA"
printf '  %-18s %s (medido: 345 MB de RSS sin el extra local-models)\n' "tipo" "$TIPO"
printf '  %-18s %s\n' "nombre" "$NOMBRE"
printf '  %-18s %s\n' "cuenta servicio" "$SA_EMAIL"
printf '  %-18s %s\n' "bucket" "${BUCKET:-(ninguno: pásalo con --bucket)}"
echo
echo "  Roles de proyecto: ${ROLES[*]}"
echo "  Cortafuegos: 80 y 443 abiertos; 22 SÓLO desde el rango de IAP (35.235.240.0/20)."
echo

if [ "$DRY_RUN" -eq 1 ]; then
  echo "(--dry-run: no se llama a gcloud y no se crea nada.)"
  exit 0
fi

command -v gcloud >/dev/null 2>&1 || { echo "ERROR: gcloud no está en el PATH." >&2; exit 3; }
[ -f "$STARTUP" ] || { echo "ERROR: no existe $STARTUP" >&2; exit 3; }

g() { gcloud "$@" --project "$PROYECTO"; }

# ---------------------------------------------------------------------------
# 1. Cuenta de servicio
# ---------------------------------------------------------------------------
echo "== 1. Cuenta de servicio =="
if g iam service-accounts describe "$SA_EMAIL" >/dev/null 2>&1; then
  echo "  [ya estaba] $SA_EMAIL"
else
  g iam service-accounts create "$SA_NOMBRE" \
    --display-name="Gov Gen AI — VM del despliegue" >/dev/null
  echo "  [creada]    $SA_EMAIL"
fi

for rol in "${ROLES[@]}"; do
  # `add-iam-policy-binding` es idempotente: repetir un binding existente no falla.
  g projects add-iam-policy-binding "$PROYECTO" \
    --member="serviceAccount:$SA_EMAIL" --role="$rol" >/dev/null
  printf '  [ok]        %s\n' "$rol"
done

if [ -n "$BUCKET" ]; then
  # Sobre el bucket y no sobre el proyecto: la máquina escribe donde tiene que escribir.
  gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" \
    --member="serviceAccount:$SA_EMAIL" --role="roles/storage.objectAdmin" \
    --project "$PROYECTO" >/dev/null
  echo "  [ok]        roles/storage.objectAdmin sobre gs://$BUCKET"
fi
echo

# ---------------------------------------------------------------------------
# 2. IP estática
#
# Estática y no efímera porque el nombre del host depende de ella: en el prototipo es un
# `sslip.io` derivado de la IP, y mañana un registro A. Una IP que cambia al reiniciar
# invalida el certificado y el `ASSISTENT_API` de las páginas ya publicadas.
# ---------------------------------------------------------------------------
echo "== 2. IP estática =="
if g compute addresses describe "$IP_NOMBRE" --region "$REGION" >/dev/null 2>&1; then
  echo "  [ya estaba] $IP_NOMBRE"
else
  g compute addresses create "$IP_NOMBRE" --region "$REGION" >/dev/null
  echo "  [creada]    $IP_NOMBRE"
fi
IP="$(g compute addresses describe "$IP_NOMBRE" --region "$REGION" \
        --format='value(address)' | tr -d '\r\n')"
echo "  IP: $IP"
echo "  Nombre para el certificado (prototipo): ${IP//./-}.sslip.io"
echo

# ---------------------------------------------------------------------------
# 3. Cortafuegos
# ---------------------------------------------------------------------------
echo "== 3. Cortafuegos =="
if g compute firewall-rules describe "$ETIQUETA-http-https" >/dev/null 2>&1; then
  echo "  [ya estaba] $ETIQUETA-http-https"
else
  g compute firewall-rules create "$ETIQUETA-http-https" \
    --allow=tcp:80,tcp:443 --target-tags="$ETIQUETA" \
    --source-ranges=0.0.0.0/0 \
    --description="HTTP y HTTPS publicos (Caddy termina TLS)" >/dev/null
  echo "  [creada]    $ETIQUETA-http-https"
fi

if g compute firewall-rules describe "$ETIQUETA-ssh-iap" >/dev/null 2>&1; then
  echo "  [ya estaba] $ETIQUETA-ssh-iap"
else
  # 35.235.240.0/20 es el rango de IAP. Es la diferencia entre «SSH cerrado al mundo» y
  # «22 abierto», que es como se pierde una máquina.
  g compute firewall-rules create "$ETIQUETA-ssh-iap" \
    --allow=tcp:22 --target-tags="$ETIQUETA" \
    --source-ranges=35.235.240.0/20 \
    --description="SSH solo desde IAP; 22 nunca abierto a Internet" >/dev/null
  echo "  [creada]    $ETIQUETA-ssh-iap"
fi
echo

# ---------------------------------------------------------------------------
# 4. La máquina
# ---------------------------------------------------------------------------
echo "== 4. La máquina =="
if g compute instances describe "$NOMBRE" --zone "$ZONA" >/dev/null 2>&1; then
  echo "  [ya estaba] $NOMBRE"
else
  g compute instances create "$NOMBRE" \
    --zone="$ZONA" \
    --machine-type="$TIPO" \
    --image-family=debian-12 \
    --image-project=debian-cloud \
    --boot-disk-size=30GB \
    --boot-disk-type=pd-balanced \
    --tags="$ETIQUETA" \
    --address="$IP" \
    --service-account="$SA_EMAIL" \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --metadata=enable-oslogin=TRUE \
    --metadata-from-file=startup-script="$STARTUP" \
    --shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring >/dev/null
  echo "  [creada]    $NOMBRE"
fi
echo

echo "== Lo que falta, y de quién es =="
echo "  1. Conceder a la cuenta de la VM acceso a los secretos (D.2):"
echo "       scripts/gcp_create_secrets.sh --project $PROYECTO --grant-accessor $SA_EMAIL"
echo "  2. Publicar la imagen y desplegar la pila: D.5-VM."
echo "  3. GOVGENAI_HOST=${IP//./-}.sslip.io en /opt/govgenai/.env.despliegue"
echo "  4. Comprobar la capa 8 cuando la pila esté arriba:"
echo "       docker compose exec script-sandbox dmesg | grep -i gvisor"
echo
echo "  Entrar por SSH (nunca por IP publica en el 22):"
echo "       gcloud compute ssh $NOMBRE --zone $ZONA --tunnel-through-iap --project $PROYECTO"

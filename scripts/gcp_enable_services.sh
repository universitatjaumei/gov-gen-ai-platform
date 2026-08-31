#!/usr/bin/env bash
#
# Habilita en un proyecto de GCP todos los servicios que la plataforma necesita (D.0).
#
# Por qué existe: hasta ahora esto era una frase de «requisito previo» en prosa, con una
# lista incompleta —no incluía Vertex AI ni Discovery Engine— y nadie la ejecutaba. Los
# prompts de despliegue daban por hecho que las APIs estaban encendidas, y una API que
# falta no se manifiesta al desplegar: se manifiesta como un 403 en producción, la primera
# vez que alguien usa la función que la necesita.
#
# El destino es una VM con Docker Compose, no un servicio gestionado de contenedores
# (docs/DECISION_EXTRACCION_Y_DESPLIEGUE.md §2), así que `run.googleapis.com` NO está en la
# lista y sí están `compute` y `oslogin`.
#
# Uso:
#   scripts/gcp_enable_services.sh --project <PROJECT_ID> [--dry-run]
#
# El proyecto es obligatorio y no tiene valor por defecto a propósito: heredar el que
# `gcloud config` tenga puesto significa habilitar APIs en el proyecto que el desarrollador
# usara la última vez, y eso se descubre tarde.

set -euo pipefail

# ---------------------------------------------------------------------------
# La lista, y qué prompt necesita cada servicio
#
# Formato: "servicio|quién lo necesita". La razón no es documentación decorativa: es lo que
# permite a quien lea la lista saber qué se rompe si quita una línea.
# ---------------------------------------------------------------------------
SERVICIOS=(
  "compute.googleapis.com|D.4-VM — la máquina donde corre todo"
  "oslogin.googleapis.com|D.4-VM — acceso por SSH gobernado por IAM, no claves en metadatos"
  "iap.googleapis.com|D.5-VM — el despliegue entra por SSH sobre IAP, sin IP pública"
  "sqladmin.googleapis.com|D.3 — Cloud SQL (PostgreSQL 16 + pgvector)"
  "secretmanager.googleapis.com|D.2 — los secretos dejan de vivir en .env"
  "storage.googleapis.com|StorageService con STORAGE_BACKEND=gcs (core/storage.py)"
  "artifactregistry.googleapis.com|D.5-VM — la imagen etiquetada con el SHA del commit"
  "iamcredentials.googleapis.com|D.5-VM — Workload Identity Federation desde GitHub Actions"
  "sts.googleapis.com|D.5-VM — intercambio de token de Workload Identity"
  "aiplatform.googleapis.com|Vertex AI — embeddings google_vertexai (embedding_service.py)"
  "generativelanguage.googleapis.com|Gemini API con API key — proveedor google_genai (MOD.2)"
  "discoveryengine.googleapis.com|RAG.6b — Ranking API del reranker (reranker.py llama a este host)"
  "logging.googleapis.com|D.6-VM — logs de los contenedores fuera de la máquina"
  "monitoring.googleapis.com|D.6-VM — uptime check de /health y alertas de memoria y disco"
)

# Servicios cuya cuota por defecto conviene mirar antes de contar con ellos.
AVISOS_DE_CUOTA=(
  "discoveryengine.googleapis.com|la cuota por defecto del Ranking API es baja; si el reranker se enciende para el piloto, comprobarla antes"
)

PROYECTO=""
DRY_RUN=0

uso() {
  echo "Uso: $0 --project <PROJECT_ID> [--dry-run]" >&2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --project)
      [ $# -ge 2 ] || { echo "ERROR: --project necesita un valor." >&2; uso; exit 2; }
      PROYECTO="$2"
      shift 2
      ;;
    --project=*)
      PROYECTO="${1#*=}"
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      uso
      exit 0
      ;;
    *)
      echo "ERROR: opción desconocida: $1" >&2
      uso
      exit 2
      ;;
  esac
done

if [ -z "$PROYECTO" ]; then
  echo "ERROR: falta --project. No hay valor por defecto: habilitar APIs en el proyecto" >&2
  echo "       equivocado se descubre tarde y cuesta dinero." >&2
  uso
  exit 2
fi

nombres() {
  local entrada
  for entrada in "${SERVICIOS[@]}"; do
    echo "${entrada%%|*}"
  done
}

echo "== Servicios de GCP para el proyecto: $PROYECTO =="
echo
for entrada in "${SERVICIOS[@]}"; do
  printf '  %-40s %s\n' "${entrada%%|*}" "${entrada#*|}"
done
echo

if [ "$DRY_RUN" -eq 1 ]; then
  echo "(--dry-run: no se llama a gcloud. Serían ${#SERVICIOS[@]} servicios.)"
  exit 0
fi

command -v gcloud >/dev/null 2>&1 || {
  echo "ERROR: gcloud no está en el PATH. Instala el SDK de Google Cloud." >&2
  exit 3
}

# ---------------------------------------------------------------------------
# Habilitar. `gcloud services enable` es idempotente: volver a pedir un servicio ya
# habilitado devuelve 0 y no cambia nada, así que el script se puede repetir sin miedo.
# ---------------------------------------------------------------------------
echo "== Habilitando =="
# shellcheck disable=SC2046
gcloud services enable $(nombres | tr '\n' ' ') --project "$PROYECTO"
echo

# ---------------------------------------------------------------------------
# Comprobar. Habilitar y no comprobar deja el mismo agujero que había: creer que están.
# ---------------------------------------------------------------------------
echo "== Comprobando =="
HABILITADOS="$(gcloud services list --enabled --project "$PROYECTO" --format='value(config.name)')"

FALTAN=0
while IFS= read -r servicio; do
  if echo "$HABILITADOS" | grep -qx "$servicio"; then
    printf '  [ok]    %s\n' "$servicio"
  else
    printf '  [FALTA] %s\n' "$servicio"
    FALTAN=$((FALTAN + 1))
  fi
done < <(nombres)
echo

for aviso in "${AVISOS_DE_CUOTA[@]}"; do
  echo "AVISO — ${aviso%%|*}: ${aviso#*|}"
done
echo

if [ "$FALTAN" -gt 0 ]; then
  echo "ERROR: $FALTAN servicio(s) siguen sin habilitar. La habilitación puede tardar unos" >&2
  echo "       segundos en propagarse: vuelve a ejecutar el script antes de dar por buena" >&2
  echo "       la conclusión de que falló." >&2
  exit 1
fi

echo "Los ${#SERVICIOS[@]} servicios están habilitados en $PROYECTO."

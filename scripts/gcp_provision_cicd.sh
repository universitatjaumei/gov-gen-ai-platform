#!/usr/bin/env bash
#
# Aprovisiona lo que el despliegue continuo necesita (D.5-VM): repositorio de imágenes,
# federación de identidad con GitHub y la cuenta que despliega. Idempotente y versionado.
#
# **Por qué federación y no una clave de cuenta de servicio.** Una clave JSON en los secretos
# de un repositorio es una credencial permanente que nadie rota y que se lleva quien consiga
# leer los secretos una sola vez. Con Workload Identity Federation, GitHub presenta un token
# de vida corta que Google canjea, y no hay nada que robar en reposo.
#
# **La condición de atributo no es opcional.** Sin `--attribute-condition` sobre el repositorio,
# el proveedor acepta tokens de CUALQUIER repositorio de GitHub: cualquiera podría crear uno,
# pedir un token y suplantar a la cuenta de despliegue. Es el error clásico de esta
# configuración, y por eso aquí el repositorio es un parámetro obligatorio.
#
# Uso:
#   scripts/gcp_provision_cicd.sh --project <ID> --repo <owner/nombre>
#                                 [--region europe-southwest1] [--dry-run]

set -euo pipefail

PROYECTO=""
REPO=""
REGION="europe-southwest1"
POOL="github"
AR_REPO="govgenai"
SA_NOMBRE="govgenai-deploy"
DRY_RUN=0

uso() {
  echo "Uso: $0 --project <ID> --repo <owner/nombre> [--region <REGION>] [--dry-run]" >&2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --project)   PROYECTO="${2:-}"; shift 2 ;;
    --project=*) PROYECTO="${1#*=}"; shift ;;
    --repo)      REPO="${2:-}"; shift 2 ;;
    --repo=*)    REPO="${1#*=}"; shift ;;
    --region)    REGION="${2:-}"; shift 2 ;;
    --region=*)  REGION="${1#*=}"; shift ;;
    --dry-run)   DRY_RUN=1; shift ;;
    -h|--help)   uso; exit 0 ;;
    *) echo "ERROR: opción desconocida: $1" >&2; uso; exit 2 ;;
  esac
done

[ -n "$PROYECTO" ] || { echo "ERROR: falta --project." >&2; uso; exit 2; }
if [ -z "$REPO" ]; then
  echo "ERROR: falta --repo <owner/nombre>. No hay valor por defecto a propósito: es lo que" >&2
  echo "       acota qué repositorio puede desplegar, y sin él el proveedor aceptaría tokens" >&2
  echo "       de cualquier repositorio de GitHub." >&2
  uso
  exit 2
fi

SA_EMAIL="$SA_NOMBRE@$PROYECTO.iam.gserviceaccount.com"
#: La cuenta con la que corre la VM (la crea `gcp_provision_vm.sh`). Hace falta nombrarla para
#: conceder `actAs` sobre ella, que es lo que permite entrar por SSH y copiar ficheros.
VM_SA="govgenai-vm@$PROYECTO.iam.gserviceaccount.com"

# Roles de la cuenta que despliega. Lo mínimo para: publicar la imagen, entrar por IAP y
# ejecutar `docker compose` en la máquina.
ROLES=(
  "roles/artifactregistry.writer"      # publicar la imagen etiquetada con el SHA
  "roles/iap.tunnelResourceAccessor"   # el túnel de IAP hacia el 22
  "roles/compute.osAdminLogin"         # entrar por OS Login y poder usar sudo con docker
  "roles/compute.viewer"               # resolver la instancia y su zona
)

echo "== CI/CD — proyecto: $PROYECTO =="
printf '  %-22s %s\n' "repositorio GitHub" "$REPO"
printf '  %-22s %s\n' "región" "$REGION"
printf '  %-22s %s\n' "Artifact Registry" "$AR_REPO"
printf '  %-22s %s\n' "pool de identidad" "$POOL"
printf '  %-22s %s\n' "cuenta de despliegue" "$SA_EMAIL"
echo "  Roles: ${ROLES[*]}"
echo

if [ "$DRY_RUN" -eq 1 ]; then
  echo "(--dry-run: no se llama a gcloud y no se crea nada.)"
  exit 0
fi

command -v gcloud >/dev/null 2>&1 || { echo "ERROR: gcloud no está en el PATH." >&2; exit 3; }

limpiar() { tr -d '\r\n'; }
g() { gcloud "$@" --project "$PROYECTO"; }

NUMERO="$(g projects describe "$PROYECTO" --format='value(projectNumber)' | limpiar)"

# ---------------------------------------------------------------------------
# 1. Artifact Registry
# ---------------------------------------------------------------------------
echo "== 1. Repositorio de imágenes =="
if g artifacts repositories describe "$AR_REPO" --location "$REGION" >/dev/null 2>&1; then
  echo "  [ya estaba] $AR_REPO"
else
  g artifacts repositories create "$AR_REPO" \
    --repository-format=docker --location "$REGION" \
    --description="Imagenes de Gov Gen AI Platform, etiquetadas por SHA de commit" >/dev/null
  echo "  [creado]    $AR_REPO"
fi
echo "  Ruta: $REGION-docker.pkg.dev/$PROYECTO/$AR_REPO"
echo

# ---------------------------------------------------------------------------
# 2. Cuenta de despliegue
# ---------------------------------------------------------------------------
echo "== 2. Cuenta de despliegue =="
if g iam service-accounts describe "$SA_EMAIL" >/dev/null 2>&1; then
  echo "  [ya estaba] $SA_EMAIL"
else
  g iam service-accounts create "$SA_NOMBRE" \
    --display-name="Gov Gen AI — despliegue desde GitHub Actions" >/dev/null
  echo "  [creada]    $SA_EMAIL"
fi

for rol in "${ROLES[@]}"; do
  g projects add-iam-policy-binding "$PROYECTO" \
    --member="serviceAccount:$SA_EMAIL" --role="$rol" >/dev/null
  printf '  [ok]        %s\n' "$rol"
done
echo

# ---------------------------------------------------------------------------
# 3. Federación de identidad
# ---------------------------------------------------------------------------
echo "== 3. Federación con GitHub =="
if g iam workload-identity-pools describe "$POOL" --location=global >/dev/null 2>&1; then
  echo "  [ya estaba] pool $POOL"
else
  g iam workload-identity-pools create "$POOL" --location=global \
    --display-name="GitHub Actions" >/dev/null
  echo "  [creado]    pool $POOL"
fi

PROVEEDOR="$(echo "$REPO" | tr '/' '-' | tr '[:upper:]' '[:lower:]')"
if g iam workload-identity-pools providers describe "$PROVEEDOR" \
     --location=global --workload-identity-pool="$POOL" >/dev/null 2>&1; then
  echo "  [ya estaba] proveedor $PROVEEDOR"
else
  # La condición ACOTA el repositorio. Sin ella, cualquier repositorio de GitHub podría pedir
  # un token válido para este proyecto.
  g iam workload-identity-pools providers create-oidc "$PROVEEDOR" \
    --location=global --workload-identity-pool="$POOL" \
    --display-name="$REPO" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
    --attribute-condition="assertion.repository=='$REPO'" >/dev/null
  echo "  [creado]    proveedor $PROVEEDOR (acotado a $REPO)"
fi

# Sólo ese repositorio puede suplantar a la cuenta de despliegue.
PRINCIPAL="principalSet://iam.googleapis.com/projects/$NUMERO/locations/global/workloadIdentityPools/$POOL/attribute.repository/$REPO"
g iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --member="$PRINCIPAL" --role="roles/iam.workloadIdentityUser" >/dev/null
echo "  [ok]        $REPO puede suplantar a la cuenta de despliegue"
echo

# ---------------------------------------------------------------------------
# 4. `actAs` sobre la cuenta de la MÁQUINA
#
# Esto no es un extra: sin él, `gcloud compute scp` y `ssh` contra una instancia que corre
# como cuenta de servicio fallan con
#     PERMISSION_DENIED: User does not have iam.serviceAccounts.actAs permission on the
#     instance's service account
# y el mensaje no dice sobre QUÉ cuenta falta el permiso — falta sobre la de la VM, no sobre
# la de despliegue. El segundo despliegue real murió exactamente aquí.
#
# Se concede **sobre esa cuenta** y no a nivel de proyecto: `serviceAccountUser` en el proyecto
# permitiría suplantar a cualquier cuenta de servicio, incluida la de la propia máquina para
# otros fines.
# ---------------------------------------------------------------------------
echo "== 4. Permiso para entrar en la máquina =="
g iam service-accounts add-iam-policy-binding "$VM_SA" \
  --member="serviceAccount:$SA_EMAIL" --role="roles/iam.serviceAccountUser" >/dev/null
echo "  [ok]        $SA_NOMBRE puede actuar como $VM_SA"
echo

echo "== Lo que hay que poner en GitHub (variables del repositorio, no secretos) =="
echo "  GCP_PROJECT_ID       $PROYECTO"
echo "  GCP_REGION           $REGION"
echo "  GCP_WIF_PROVIDER     projects/$NUMERO/locations/global/workloadIdentityPools/$POOL/providers/$PROVEEDOR"
echo "  GCP_DEPLOY_SA        $SA_EMAIL"
echo "  GCP_AR_REPO          $AR_REPO"
echo
echo "  Ninguno es un secreto: son identificadores. Lo que autoriza es la federación, y sólo"
echo "  desde $REPO — por eso no hay ninguna clave que guardar."

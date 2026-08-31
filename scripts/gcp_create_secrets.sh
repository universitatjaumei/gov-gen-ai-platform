#!/usr/bin/env bash
#
# Crea en Secret Manager los secretos del despliegue (D.2), lee el inventario de
# `scripts/lib/secretos.tsv` y NO imprime ningún valor.
#
# Dos reglas que gobiernan todo lo de abajo:
#
# 1. **Idempotente sin rotar.** Volver a ejecutarlo no cambia un secreto que ya existe. Un
#    script que regenerase `JWT_SECRET_KEY` en cada pasada echaría a la calle a todo el mundo
#    en la siguiente ejecución, y el síntoma —«se me ha caducado la sesión»— no señala aquí.
#
# 2. **Los valores no pasan por la pantalla ni por el historial.** Se generan y se canalizan
#    directamente a `gcloud secrets create --data-file=-`. Lo que se imprime es el NOMBRE del
#    secreto y si tiene versión, nunca su contenido.
#
# Uso:
#   scripts/gcp_create_secrets.sh --project <PROJECT_ID> [--sql-instance <NOMBRE>]
#                                 [--db-name <BD>] [--db-user <USUARIO>]
#                                 [--grant-accessor <SA_EMAIL>] [--dry-run]
#
# `--sql-instance` habilita los secretos derivados (las dos URL de base de datos): sin él se
# crean los demás y se avisa de que faltan.

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INVENTARIO="$RAIZ/scripts/lib/secretos.tsv"

PROYECTO=""
SQL_INSTANCE=""
DB_NAME="govgenai"
DB_USER="govgenai"
GRANT_ACCESSOR=""
DRY_RUN=0

uso() {
  echo "Uso: $0 --project <PROJECT_ID> [--sql-instance <NOMBRE>] [--db-name <BD>]" >&2
  echo "        [--db-user <USUARIO>] [--grant-accessor <SA_EMAIL>] [--dry-run]" >&2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --project)         PROYECTO="${2:-}"; shift 2 ;;
    --project=*)       PROYECTO="${1#*=}"; shift ;;
    --sql-instance)    SQL_INSTANCE="${2:-}"; shift 2 ;;
    --sql-instance=*)  SQL_INSTANCE="${1#*=}"; shift ;;
    --db-name)         DB_NAME="${2:-}"; shift 2 ;;
    --db-name=*)       DB_NAME="${1#*=}"; shift ;;
    --db-user)         DB_USER="${2:-}"; shift 2 ;;
    --db-user=*)       DB_USER="${1#*=}"; shift ;;
    --grant-accessor)  GRANT_ACCESSOR="${2:-}"; shift 2 ;;
    --grant-accessor=*) GRANT_ACCESSOR="${1#*=}"; shift ;;
    --dry-run)         DRY_RUN=1; shift ;;
    -h|--help)         uso; exit 0 ;;
    *) echo "ERROR: opción desconocida: $1" >&2; uso; exit 2 ;;
  esac
done

if [ -z "$PROYECTO" ]; then
  echo "ERROR: falta --project. Sin proyecto explícito no se crean secretos: heredar el de" >&2
  echo "       'gcloud config' significa escribir credenciales donde nadie mira." >&2
  uso
  exit 2
fi

[ -f "$INVENTARIO" ] || { echo "ERROR: no existe $INVENTARIO" >&2; exit 3; }

# Lee el inventario ignorando comentarios y líneas vacías.
inventario() {
  grep -vE '^\s*#|^\s*$' "$INVENTARIO"
}

echo "== Secretos del despliegue — proyecto: $PROYECTO =="
echo
while IFS='|' read -r nombre variable origen consumidor; do
  printf '  %-32s %-26s %-9s %s\n' "$nombre" "$variable" "$origen" "$consumidor"
done < <(inventario)
echo

if [ "$DRY_RUN" -eq 1 ]; then
  echo "(--dry-run: no se llama a gcloud. Serían $(inventario | wc -l | tr -d ' ') secretos.)"
  exit 0
fi

command -v gcloud >/dev/null 2>&1 || { echo "ERROR: gcloud no está en el PATH." >&2; exit 3; }

# Todo valor capturado de `gcloud` pasa por aquí. En Windows su salida puede terminar en CRLF,
# y `$(...)` sólo se come el `\n`: el `\r` sobrevive dentro de la cadena y no da ningún error
# que apunte al origen. Pasó dos veces en la primera siembra — un secreto de 97 caracteres y
# una URL de conexión con un retorno de carro al final—, así que se limpia en un solo sitio.
limpiar() {
  tr -d '\r\n'
}

existe() {
  gcloud secrets describe "$1" --project "$PROYECTO" >/dev/null 2>&1
}

tiene_version() {
  local n
  n="$(gcloud secrets versions list "$1" --project "$PROYECTO" --filter='state:ENABLED' \
        --format='value(name)' 2>/dev/null | wc -l | tr -d ' ')"
  [ "$n" -gt 0 ]
}

crear_vacio() {
  existe "$1" || gcloud secrets create "$1" --project "$PROYECTO" \
      --replication-policy=automatic >/dev/null
}

# Genera y sube un valor SIN que aparezca en ninguna parte.
sembrar_generado() {
  local nombre="$1"
  if tiene_version "$nombre"; then
    printf '  [ya estaba]  %s (no se rota)\n' "$nombre"
    return
  fi
  crear_vacio "$nombre"
  # `tr -d '\r\n'` y no sólo '\n': en Windows `openssl` termina con CRLF, y un `\r` dentro de
  # una contraseña o de un fichero de entorno se lleva por delante la línea entera sin dar
  # ningún error que apunte aquí. Costó un «longitud=97» donde tenían que haber 96.
  openssl rand -hex 48 | tr -d '\r\n' \
    | gcloud secrets versions add "$nombre" --project "$PROYECTO" --data-file=- >/dev/null
  printf '  [generado]   %s\n' "$nombre"
}

sembrar_derivado() {
  local nombre="$1" variable="$2"
  if tiene_version "$nombre"; then
    printf '  [ya estaba]  %s\n' "$nombre"
    return
  fi
  if [ -z "$SQL_INSTANCE" ]; then
    crear_vacio "$nombre"
    printf '  [FALTA]      %s — necesita --sql-instance\n' "$nombre"
    return
  fi
  if ! tiene_version "govgenai-db-password"; then
    printf '  [FALTA]      %s — antes hace falta govgenai-db-password\n' "$nombre"
    return
  fi

  local conexion clave esquema url
  conexion="$(gcloud sql instances describe "$SQL_INSTANCE" --project "$PROYECTO" \
                --format='value(connectionName)' | limpiar)"
  clave="$(gcloud secrets versions access latest --secret=govgenai-db-password \
             --project "$PROYECTO" | limpiar)"

  # El Auth Proxy expone un socket Unix en /cloudsql/<connectionName>; es el patrón que
  # CLAUDE.md fija para Cloud SQL y no lleva host ni puerto.
  if [ "$variable" = "DATABASE_URL_SYNC" ]; then
    esquema="postgresql+psycopg2"
  else
    esquema="postgresql+asyncpg"
  fi
  url="$esquema://$DB_USER:$clave@/$DB_NAME?host=/cloudsql/$conexion"

  crear_vacio "$nombre"
  printf '%s' "$url" \
    | gcloud secrets versions add "$nombre" --project "$PROYECTO" --data-file=- >/dev/null
  unset clave url
  printf '  [derivado]   %s\n' "$nombre"
}

sembrar_humano() {
  local nombre="$1" variable="$2"
  crear_vacio "$nombre"
  if tiene_version "$nombre"; then
    printf '  [ya estaba]  %s\n' "$nombre"
  else
    printf '  [PENDIENTE]  %s — lo aporta una persona:\n' "$nombre"
    printf '               printf %%s "$%s" | gcloud secrets versions add %s --project %s --data-file=-\n' \
           "$variable" "$nombre" "$PROYECTO"
  fi
}

echo "== Creando =="
while IFS='|' read -r nombre variable origen consumidor; do
  case "$origen" in
    generado) sembrar_generado "$nombre" ;;
    derivado) sembrar_derivado "$nombre" "$variable" ;;
    humano)   sembrar_humano "$nombre" "$variable" ;;
    *) echo "  ERROR: origen desconocido '$origen' para $nombre" >&2; exit 4 ;;
  esac
done < <(inventario)
echo

if [ -n "$GRANT_ACCESSOR" ]; then
  echo "== Concediendo acceso a $GRANT_ACCESSOR =="
  # Por secreto y no a nivel de proyecto: la cuenta de la VM puede leer lo que la aplicación
  # necesita y nada más.
  while IFS='|' read -r nombre variable origen consumidor; do
    gcloud secrets add-iam-policy-binding "$nombre" --project "$PROYECTO" \
      --member="serviceAccount:$GRANT_ACCESSOR" \
      --role="roles/secretmanager.secretAccessor" >/dev/null
    printf '  [ok] %s\n' "$nombre"
  done < <(inventario)
  echo
fi

echo "== Comprobando =="
FALTAN=0
while IFS='|' read -r nombre variable origen consumidor; do
  if tiene_version "$nombre"; then
    printf '  [ok]    %s\n' "$nombre"
  else
    printf '  [FALTA] %s (%s)\n' "$nombre" "$origen"
    FALTAN=$((FALTAN + 1))
  fi
done < <(inventario)
echo

if [ "$FALTAN" -gt 0 ]; then
  echo "ERROR: $FALTAN secreto(s) sin valor. El despliegue no puede arrancar así." >&2
  exit 1
fi

echo "Todos los secretos tienen valor en $PROYECTO."

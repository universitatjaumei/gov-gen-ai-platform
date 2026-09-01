#!/usr/bin/env bash
#
# Baja los secretos de Secret Manager a un fichero de entorno en la VM (D.2).
#
# Esto es lo que sustituye al `.env` en producción: el fichero lo escribe la máquina en cada
# arranque a partir de Secret Manager, así que la credencial vive en un solo sitio y rotarla no
# obliga a entrar en la máquina a editar nada — se rota el secreto y se reinicia.
#
# En el despliegue gestionado esto lo hacía la plataforma inyectando variables; en una VM lo
# hace este guion, que es la parte que el prompt original daba por hecha.
#
# Tres cosas que hace a propósito:
#   - No imprime NINGÚN valor. Imprime el nombre de la variable y si se pudo leer.
#   - Escribe con `umask 077` a un temporal y luego lo mueve: nunca hay un instante en que el
#     fichero exista con permisos abiertos.
#   - Si falta un secreto, falla y dice cuál. Un fichero de entorno a medias arranca la
#     aplicación con la mitad de la configuración, que es peor que no arrancar.
#
# Uso (en la VM, como root o con sudo):
#   scripts/vm_fetch_secrets.sh --project <PROJECT_ID> [--out /opt/govgenai/.env.runtime]
#                               [--dry-run]

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INVENTARIO="$RAIZ/scripts/lib/secretos.tsv"

PROYECTO=""
SALIDA="/opt/govgenai/.env.runtime"
DRY_RUN=0

uso() {
  echo "Uso: $0 --project <PROJECT_ID> [--out <RUTA>] [--dry-run]" >&2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --project)   PROYECTO="${2:-}"; shift 2 ;;
    --project=*) PROYECTO="${1#*=}"; shift ;;
    --out)       SALIDA="${2:-}"; shift 2 ;;
    --out=*)     SALIDA="${1#*=}"; shift ;;
    --dry-run)   DRY_RUN=1; shift ;;
    -h|--help)   uso; exit 0 ;;
    *) echo "ERROR: opción desconocida: $1" >&2; uso; exit 2 ;;
  esac
done

if [ -z "$PROYECTO" ]; then
  echo "ERROR: falta --project." >&2
  uso
  exit 2
fi

[ -f "$INVENTARIO" ] || { echo "ERROR: no existe $INVENTARIO" >&2; exit 3; }

inventario() {
  # Se saltan los secretos marcados `FICHERO:`: son ficheros (el certificado del dominio y su
  # clave), los baja `vm_fetch_tls.sh`, y un PEM multilínea metido en un fichero de entorno
  # rompería todas las variables que vinieran detrás.
  grep -vE '^\s*#|^\s*$' "$INVENTARIO" | grep -vE '^[^|]*\|FICHERO:'
}

echo "== Secretos a montar en $SALIDA (proyecto $PROYECTO) =="
while IFS='|' read -r nombre variable origen consumidor; do
  printf '  %-26s <- %s\n' "$variable" "$nombre"
done < <(inventario)
echo

if [ "$DRY_RUN" -eq 1 ]; then
  echo "(--dry-run: no se llama a gcloud y no se escribe nada.)"
  exit 0
fi

command -v gcloud >/dev/null 2>&1 || { echo "ERROR: gcloud no está en el PATH." >&2; exit 3; }

umask 077
DESTINO_DIR="$(dirname "$SALIDA")"
mkdir -p "$DESTINO_DIR"
TEMPORAL="$(mktemp "$DESTINO_DIR/.env.runtime.XXXXXX")"
# Si algo falla a media escritura, el temporal no se queda con secretos dentro.
trap 'rm -f "$TEMPORAL"' EXIT

{
  echo "# Generado por scripts/vm_fetch_secrets.sh — NO editar a mano."
  echo "# Los valores vienen de Secret Manager del proyecto $PROYECTO."
  echo "# Para rotar: cambia el secreto y reinicia; no toques este fichero."
} >> "$TEMPORAL"

FALTAN=0
while IFS='|' read -r nombre variable origen consumidor; do
  # `tr -d '\r\n'`: un `\r` al final de un valor se lleva por delante la línea del fichero de
  # entorno, y el fallo aparece lejos de aquí. Lo aprendimos sembrando los secretos.
  if valor="$(gcloud secrets versions access latest --secret="$nombre" \
                --project "$PROYECTO" 2>/dev/null | tr -d '\r\n')"; then
    printf '%s=%s\n' "$variable" "$valor" >> "$TEMPORAL"
    unset valor
    printf '  [ok]    %s\n' "$variable"
  else
    printf '  [FALTA] %s (secreto %s sin versión legible)\n' "$variable" "$nombre"
    FALTAN=$((FALTAN + 1))
  fi
done < <(inventario)
echo

if [ "$FALTAN" -gt 0 ]; then
  echo "ERROR: $FALTAN secreto(s) no se pudieron leer. No se escribe el fichero: la" >&2
  echo "       aplicación no debe arrancar con la configuración a medias." >&2
  echo "       Comprueba que la cuenta de servicio de la VM tiene" >&2
  echo "       roles/secretmanager.secretAccessor sobre esos secretos." >&2
  exit 1
fi

chmod 600 "$TEMPORAL"
mv "$TEMPORAL" "$SALIDA"
trap - EXIT
echo "Escrito $SALIDA con $(inventario | wc -l | tr -d ' ') variables, permisos 600."

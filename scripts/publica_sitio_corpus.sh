#!/usr/bin/env bash
#
# Publica el corpus navegable en un bucket (D.6.1): el buscador, las páginas por norma con sus
# anclas, los PDF y las imágenes.
#
# **Este guion publica, no produce.** El paquete lo genera el pipeline de curación, fuera de este
# repositorio, y aquí no se cambia ni su formato ni su contenido: la frontera es
# `docs/CONTRATO_MD_CORPUS.md`.
#
# Por qué importa: `CORPUS_SITE_BASE_URL` apuntaba a `127.0.0.1:4174`, así que las citas del
# asistente sólo funcionaban en la máquina de quien lo desarrolla — medido el 2026-08-24, 16 de
# 25 respuestas llevaban enlaces a localhost. Publicar el sitio es lo que convierte el esfuerzo
# de generar 6.571 anclas en algo que la persona que pregunta nota.
#
# **La URL de una norma no puede cambiar entre publicaciones**: es la que cita el asistente y la
# que la gente guarda. De ahí que se suba por rutas fijas y que el guion no renombre nada.
#
# Uso:
#   scripts/publica_sitio_corpus.sh --project <ID> --bucket <BUCKET> --dir <RUTA_DEL_SITIO>
#                                   [--con-widget] [--dry-run]

set -euo pipefail

PROYECTO=""
BUCKET=""
DIR=""
CON_WIDGET=0
DRY_RUN=0

uso() {
  echo "Uso: $0 --project <ID> --bucket <BUCKET> --dir <RUTA> [--con-widget] [--dry-run]" >&2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --project)     PROYECTO="${2:-}"; shift 2 ;;
    --project=*)   PROYECTO="${1#*=}"; shift ;;
    --bucket)      BUCKET="${2:-}"; shift 2 ;;
    --bucket=*)    BUCKET="${1#*=}"; shift ;;
    --dir)         DIR="${2:-}"; shift 2 ;;
    --dir=*)       DIR="${1#*=}"; shift ;;
    --con-widget)  CON_WIDGET=1; shift ;;
    --dry-run)     DRY_RUN=1; shift ;;
    -h|--help)     uso; exit 0 ;;
    *) echo "ERROR: opción desconocida: $1" >&2; uso; exit 2 ;;
  esac
done

[ -n "$PROYECTO" ] || { echo "ERROR: falta --project." >&2; uso; exit 2; }
[ -n "$BUCKET" ]   || { echo "ERROR: falta --bucket." >&2; uso; exit 2; }
[ -n "$DIR" ]      || { echo "ERROR: falta --dir (la carpeta del sitio generado)." >&2; uso; exit 2; }
[ -d "$DIR" ]      || { echo "ERROR: no existe la carpeta $DIR" >&2; exit 3; }

# ---------------------------------------------------------------------------
# Qué se sube, y qué NO
#
# Se enumera lo publicable en vez de excluir lo demás: la carpeta del corpus tiene material de
# ingesta (`generat/`, `md*/`, `paquet_*`) que no debe salir a internet, y una lista de
# exclusiones se queda corta el día que aparece una carpeta nueva.
# ---------------------------------------------------------------------------
FICHEROS_SUELTOS=()
for f in index.html cercador.html cercador_corpus.html cercador_gerencia.html \
         index_gerencia.html widget.iife.js; do
  [ -f "$DIR/$f" ] && FICHEROS_SUELTOS+=("$f")
done

CARPETAS=()
for d in html pdf img; do
  [ -d "$DIR/$d" ] && CARPETAS+=("$d")
done

# ---------------------------------------------------------------------------
# La guarda de la credencial
#
# La credencial de sitio del widget acaba DENTRO del HTML generado. Si el paquete se generó en
# local con la credencial de pruebas y se sube tal cual, se publica esa credencial. Así que si
# aparece una, hay que decir explícitamente que es la buena.
# ---------------------------------------------------------------------------
# Se busca un VALOR, no el nombre del atributo, y sólo en HTML. La primera versión miraba
# también `widget.iife.js` —que menciona `data-widget-key` porque es el código que lee ese
# atributo— y se negaba a publicar un sitio que no llevaba ninguna credencial.
_CLAVE_CON_VALOR='data-widget-key[[:space:]]*=[[:space:]]*"[^"]\+"'

CON_CLAVE=0
for f in "${FICHEROS_SUELTOS[@]}"; do
  case "$f" in
    *.html) grep -q "$_CLAVE_CON_VALOR" "$DIR/$f" 2>/dev/null && CON_CLAVE=1 ;;
  esac
done
if [ "$CON_CLAVE" -eq 0 ] && [ -d "$DIR/html" ]; then
  if grep -rl --include='*.html' "$_CLAVE_CON_VALOR" "$DIR/html" 2>/dev/null | head -1 | grep -q .; then
    CON_CLAVE=1
  fi
fi

echo "== Publicación del corpus navegable =="
printf '  %-12s %s\n' "proyecto" "$PROYECTO"
printf '  %-12s gs://%s\n' "bucket" "$BUCKET"
printf '  %-12s %s\n' "origen" "$DIR"
printf '  %-12s %s\n' "sueltos" "${FICHEROS_SUELTOS[*]:-(ninguno)}"
printf '  %-12s %s\n' "carpetas" "${CARPETAS[*]:-(ninguna)}"
if [ "$CON_CLAVE" -eq 1 ]; then
  printf '  %-12s SÍ — el HTML lleva credencial de sitio dentro\n' "widget"
else
  printf '  %-12s no — el sitio se publica sin asistente\n' "widget"
fi
echo

if [ "$CON_CLAVE" -eq 1 ] && [ "$CON_WIDGET" -eq 0 ]; then
  echo "ERROR: las páginas llevan una credencial de sitio (data-widget-key) y no se ha pasado" >&2
  echo "       --con-widget. Si esa credencial es la de pruebas de local, publicarla la expone." >&2
  echo "       Emite una para el bucket, regenera el sitio con ella, revoca la de local, y" >&2
  echo "       entonces vuelve con --con-widget." >&2
  exit 4
fi

if [ "$DRY_RUN" -eq 1 ]; then
  echo "(--dry-run: no se llama a gcloud y no se sube nada.)"
  exit 0
fi

command -v gcloud >/dev/null 2>&1 || { echo "ERROR: gcloud no está en el PATH." >&2; exit 3; }

# ---------------------------------------------------------------------------
# Subida
#
# `rsync` y no `cp`: sólo viaja lo que ha cambiado, así que republicar tras corregir una norma
# cuesta esa norma y no 54 MB.
#
# `Cache-Control` explícito y distinto por tipo: un HTML de norma cambia cuando cambia la norma
# —cinco minutos de caché para que una corrección se vea pronto—, mientras un PDF o una imagen
# no cambian nunca sin cambiar de nombre.
# ---------------------------------------------------------------------------
CACHE_HTML="public, max-age=300"
CACHE_ESTATICO="public, max-age=86400"

echo "== Subiendo =="
for f in "${FICHEROS_SUELTOS[@]}"; do
  gcloud storage cp "$DIR/$f" "gs://$BUCKET/$f" --project "$PROYECTO" \
    --cache-control="$CACHE_HTML" >/dev/null
  printf '  [ok] %s\n' "$f"
done

for d in "${CARPETAS[@]}"; do
  case "$d" in
    html) cache="$CACHE_HTML" ;;
    *)    cache="$CACHE_ESTATICO" ;;
  esac
  gcloud storage rsync "$DIR/$d" "gs://$BUCKET/$d" --recursive --project "$PROYECTO" \
    --cache-control="$cache" 2>&1 | tail -2
  printf '  [ok] %s/ (Cache-Control: %s)\n' "$d" "$cache"
done
echo

echo "== Comprobando =="
BASE="https://$BUCKET.storage.googleapis.com"
# Se comprueba con la forma **virtual-hosted**, que da un origen propio del bucket: la otra
# forma (`storage.googleapis.com/<bucket>/…`) comparte origen con todos los buckets del mundo,
# y CORS tendría que abrirse a eso. Ver docs/DESPLIEGUE_PROTOTIPO_GCP.md §3.quater.
for ruta in "index.html" "cercador.html"; do
  codigo="$(curl -s -o /dev/null -w '%{http_code}' "$BASE/$ruta" || true)"
  printf '  %-16s %s\n' "$ruta" "$codigo"
done
echo
echo "CORPUS_SITE_BASE_URL para el despliegue: $BASE"
echo
echo "Si el bucket no es público todavía, las comprobaciones dan 403. Hazlo legible:"
echo "  gcloud storage buckets add-iam-policy-binding gs://$BUCKET \\"
echo "      --member=allUsers --role=roles/storage.objectViewer --project $PROYECTO"

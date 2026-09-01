#!/usr/bin/env bash
#
# Baja el certificado del dominio institucional y su clave a la VM, e instala el sitio de Caddy
# que los usa (D.8).
#
# Por qué es un guion aparte de `vm_fetch_secrets.sh`: eso escribe un fichero de ENTORNO, y un
# PEM es multilínea. Metido ahí rompería todas las variables que vinieran detrás.
#
# ⚠️  ESTE CERTIFICADO NO SE RENUEVA SOLO.
#
# El del nombre provisional lo obtiene y renueva Caddy por ACME. Este lo emite la Universitat a
# través de HARICA/GÉANT y **caduca el 19 de marzo de 2027**. Renovar es: subir la versión nueva
# de los dos secretos y `systemctl restart govgenai`. Este guion baja siempre `latest`, así que
# no hay que editar nada aquí.
#
# LA GUARDA QUE IMPORTA. Si los secretos no existen todavía —la situación mientras el dominio no
# esté en el DNS—, el fichero del sitio se RETIRA en vez de dejarse. Un `tls` de Caddy apuntando
# a ficheros que no están impide que Caddy arranque, y un Caddy que no arranca se lleva por
# delante también el nombre provisional, que es el que sirve a las 313 páginas ya publicadas. O
# sea: el modo de fallo de no tener certificado tiene que ser «el dominio nuevo no responde», no
# «el servicio entero está caído».
#
# Uso (en la VM, como root o con sudo):
#   scripts/vm_fetch_tls.sh --project <PROJECT_ID> --host <DOMINIO>
#                           [--tls-dir /opt/govgenai/tls] [--sites-dir /opt/govgenai/sites.d]
#                           [--dry-run]

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INVENTARIO="$RAIZ/scripts/lib/secretos.tsv"
PLANTILLA="$RAIZ/deploy/vm/sites.d/dominio.caddy.tpl"

PROYECTO=""
HOST=""
TLS_DIR="/opt/govgenai/tls"
SITES_DIR="/opt/govgenai/sites.d"
DRY_RUN=0

# Nombres de los secretos, leídos del inventario y no copiados aquí.
SECRETO_CERT=""
SECRETO_KEY=""

uso() {
  echo "Uso: $0 --project <PROJECT_ID> --host <DOMINIO> [--tls-dir <RUTA>]" >&2
  echo "        [--sites-dir <RUTA>] [--dry-run]" >&2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --project)     PROYECTO="${2:-}"; shift 2 ;;
    --project=*)   PROYECTO="${1#*=}"; shift ;;
    --host)        HOST="${2:-}"; shift 2 ;;
    --host=*)      HOST="${1#*=}"; shift ;;
    --tls-dir)     TLS_DIR="${2:-}"; shift 2 ;;
    --tls-dir=*)   TLS_DIR="${1#*=}"; shift ;;
    --sites-dir)   SITES_DIR="${2:-}"; shift 2 ;;
    --sites-dir=*) SITES_DIR="${1#*=}"; shift ;;
    --dry-run)     DRY_RUN=1; shift ;;
    -h|--help)     uso; exit 0 ;;
    *) echo "ERROR: opción desconocida: $1" >&2; uso; exit 2 ;;
  esac
done

[ -n "$PROYECTO" ] || { echo "ERROR: falta --project." >&2; uso; exit 2; }
[ -f "$INVENTARIO" ] || { echo "ERROR: no existe $INVENTARIO" >&2; exit 3; }

# ---------------------------------------------------------------------------
# Sin dominio institucional configurado no hay nada que hacer, y se sale BIEN
#
# La unidad systemd llama a este guion con `--host ${GOVGENAI_HOST_INSTITUCIONAL}`, tomado del
# fichero de entorno del despliegue. Si esa variable no está puesta, systemd la expande a vacío;
# tratarlo como error haría fallar el `ExecStartPre` y con él **el arranque de toda la pila**,
# por no tener configurado un dominio que en este despliegue puede no existir. El modo de fallo
# correcto es «no hay dominio institucional», no «el servicio no arranca».
# ---------------------------------------------------------------------------
if [ -z "$HOST" ]; then
  echo "No hay dominio institucional configurado (GOVGENAI_HOST_INSTITUCIONAL vacío)."
  echo "No se baja ningún certificado y se retiran los sitios que hubiera en $SITES_DIR."
  if [ -d "$SITES_DIR" ]; then
    rm -f "$SITES_DIR"/*.caddy
  fi
  rm -f "$TLS_DIR/fullchain.pem" "$TLS_DIR/privkey.pem"
  exit 0
fi

# ---------------------------------------------------------------------------
# Los nombres salen del inventario, que es la fuente única
# ---------------------------------------------------------------------------
while IFS='|' read -r nombre variable origen consumidor; do
  case "$variable" in
    FICHERO:TLS_FULLCHAIN) SECRETO_CERT="$nombre" ;;
    FICHERO:TLS_PRIVKEY)   SECRETO_KEY="$nombre" ;;
  esac
done < <(grep -vE '^\s*#|^\s*$' "$INVENTARIO")

if [ -z "$SECRETO_CERT" ] || [ -z "$SECRETO_KEY" ]; then
  echo "ERROR: el inventario no declara FICHERO:TLS_FULLCHAIN y FICHERO:TLS_PRIVKEY." >&2
  exit 3
fi

DESTINO_SITIO="$SITES_DIR/$HOST.caddy"

echo "== Certificado del dominio institucional =="
printf '  %-16s %s\n' "proyecto" "$PROYECTO"
printf '  %-16s %s\n' "host" "$HOST"
printf '  %-16s %s (%s)\n' "certificado" "$TLS_DIR/fullchain.pem" "$SECRETO_CERT"
printf '  %-16s %s (%s)\n' "clave" "$TLS_DIR/privkey.pem" "$SECRETO_KEY"
printf '  %-16s %s\n' "sitio" "$DESTINO_SITIO"
echo
echo "  Recordatorio: este certificado NO se renueva solo. Caduca y hay que subir la versión"
echo "  nueva de los dos secretos y reiniciar la unidad."
echo

if [ "$DRY_RUN" -eq 1 ]; then
  echo "(--dry-run: no se llama a gcloud y no se escribe nada.)"
  exit 0
fi

command -v gcloud >/dev/null 2>&1 || { echo "ERROR: gcloud no está en el PATH." >&2; exit 3; }
[ -f "$PLANTILLA" ] || { echo "ERROR: no existe la plantilla $PLANTILLA" >&2; exit 3; }

# ---------------------------------------------------------------------------
# Bajada. `umask 077` antes de crear nada: nunca hay un instante en que la clave exista con
# permisos abiertos. No se imprime NINGÚN valor, sólo si se pudo leer.
# ---------------------------------------------------------------------------
umask 077
mkdir -p "$TLS_DIR" "$SITES_DIR"

bajar() {
  local nombre="$1" destino="$2"
  local temporal
  temporal="$(mktemp "$TLS_DIR/.tls.XXXXXX")"
  if gcloud secrets versions access latest --secret="$nombre" --project "$PROYECTO" \
       > "$temporal" 2>/dev/null && [ -s "$temporal" ]; then
    chmod 600 "$temporal"
    mv "$temporal" "$destino"
    return 0
  fi
  rm -f "$temporal"
  return 1
}

echo "== Bajando =="
FALTA=0
if bajar "$SECRETO_CERT" "$TLS_DIR/fullchain.pem"; then
  printf '  [ok]     %s\n' "$SECRETO_CERT"
else
  printf '  [FALTA]  %s (sin versión legible)\n' "$SECRETO_CERT"
  FALTA=1
fi
if bajar "$SECRETO_KEY" "$TLS_DIR/privkey.pem"; then
  printf '  [ok]     %s\n' "$SECRETO_KEY"
else
  printf '  [FALTA]  %s (sin versión legible)\n' "$SECRETO_KEY"
  FALTA=1
fi
echo

# ---------------------------------------------------------------------------
# La guarda: sin las dos piezas, el sitio se retira y el guion sale BIEN
#
# Sale 0 a propósito. Esto lo llama la unidad systemd como `ExecStartPre`, y fallar aquí
# impediría levantar la pila entera por no tener un certificado que todavía no se espera tener.
# ---------------------------------------------------------------------------
if [ "$FALTA" -eq 1 ] || [ ! -s "$TLS_DIR/fullchain.pem" ] || [ ! -s "$TLS_DIR/privkey.pem" ]; then
  rm -f "$DESTINO_SITIO"
  rm -f "$TLS_DIR/fullchain.pem" "$TLS_DIR/privkey.pem"
  echo "El certificado no está completo, así que el sitio de $HOST NO se instala."
  echo "Se retira $DESTINO_SITIO si existía: con un 'tls' apuntando a ficheros que no están,"
  echo "Caddy no arranca y eso tumbaría también el nombre provisional."
  echo
  echo "Cuando el dominio exista en el DNS, cargar los dos secretos y reiniciar la unidad."
  exit 0
fi

# ---------------------------------------------------------------------------
# Comprobación antes de instalar: que la clave sea la de este certificado
#
# Si no cuadran, Caddy arranca y sirve un TLS que ningún navegador acepta — un fallo que se ve
# como «sitio no seguro» y no como un error en los logs. Barato de comprobar aquí.
# ---------------------------------------------------------------------------
if command -v openssl >/dev/null 2>&1; then
  H_CERT="$(openssl x509 -in "$TLS_DIR/fullchain.pem" -noout -pubkey 2>/dev/null \
            | openssl pkey -pubin -outform DER 2>/dev/null | openssl dgst -sha256 2>/dev/null \
            | awk '{print $NF}')"
  H_KEY="$(openssl pkey -in "$TLS_DIR/privkey.pem" -pubout -outform DER 2>/dev/null \
           | openssl dgst -sha256 2>/dev/null | awk '{print $NF}')"
  if [ -n "$H_CERT" ] && [ "$H_CERT" != "$H_KEY" ]; then
    rm -f "$DESTINO_SITIO"
    echo "ERROR: la clave privada no corresponde al certificado. El sitio no se instala." >&2
    exit 4
  fi
  CADUCA="$(openssl x509 -in "$TLS_DIR/fullchain.pem" -noout -enddate 2>/dev/null \
            | sed 's/notAfter=//')"
  [ -n "$CADUCA" ] && echo "  El certificado caduca: $CADUCA"
fi

# ---------------------------------------------------------------------------
# Instalación del sitio
# ---------------------------------------------------------------------------
TEMPORAL_SITIO="$(mktemp "$SITES_DIR/.sitio.XXXXXX")"
sed "s/{{HOST}}/$HOST/g" "$PLANTILLA" > "$TEMPORAL_SITIO"
chmod 644 "$TEMPORAL_SITIO"
mv "$TEMPORAL_SITIO" "$DESTINO_SITIO"

echo "  [ok]     $DESTINO_SITIO instalado para $HOST"
echo
echo "Listo. Caddy servirá $HOST con su certificado propio, y el nombre provisional sigue"
echo "sirviendo por ACME mientras las páginas publicadas apunten a él."

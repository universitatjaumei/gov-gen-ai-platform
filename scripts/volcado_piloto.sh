#!/usr/bin/env bash
#
# Volcado de los datos operativos que pasan al piloto (D.7).
#
# **Por qué existe.** Hasta ahora la pregunta «¿qué pasa al piloto?» sólo tenía dos respuestas
# posibles y las dos eran malas: un volcado completo —que arrastra los informes de prueba y toda
# la basura de test— o empezar de cero, tirando el corpus curado y los hallazgos ya revisados.
#
# **Lo que este guion NO hace, y es la mitad del asunto**: no lleva el catálogo del producto. Las
# plantillas demo se exportan a ficheros versionados en el repositorio y las siembra
# `bootstrap.py --con-demo`, así que la demo es reproducible, se revisa en un diff y es la misma
# en todos los despliegues. Es la misma regla que ya rige el vocabulario del corpus: lo que
# define el producto es dato versionado, no una fila que alguien tenía en su portátil.
#
# Uso:
#   scripts/volcado_piloto.sh --organizacion <UUID> --salida <FICHERO.sql> [--dry-run]
#
# La conexión se lee de `DATABASE_URL_SYNC` (o de `--dsn`), nunca cableada.

set -euo pipefail

ORGANIZACION=""
SALIDA=""
DSN="${DATABASE_URL_SYNC:-}"
DRY_RUN=0

uso() {
  echo "Uso: $0 --organizacion <UUID> --salida <FICHERO.sql> [--dsn <DSN>] [--dry-run]" >&2
}

while [ $# -gt 0 ]; do
  case "$1" in
    --organizacion)   ORGANIZACION="${2:-}"; shift 2 ;;
    --organizacion=*) ORGANIZACION="${1#*=}"; shift ;;
    --salida)         SALIDA="${2:-}"; shift 2 ;;
    --salida=*)       SALIDA="${1#*=}"; shift ;;
    --dsn)            DSN="${2:-}"; shift 2 ;;
    --dsn=*)          DSN="${1#*=}"; shift ;;
    --dry-run)        DRY_RUN=1; shift ;;
    -h|--help)        uso; exit 0 ;;
    *) echo "ERROR: opción desconocida: $1" >&2; uso; exit 2 ;;
  esac
done

[ -n "$ORGANIZACION" ] || { echo "ERROR: falta --organizacion." >&2; uso; exit 2; }
[ -n "$SALIDA" ]       || { echo "ERROR: falta --salida." >&2; uso; exit 2; }

# ---------------------------------------------------------------------------
# LO QUE VIAJA — lista explícita, y el porqué de cada tabla.
#
# Explícita y no «todo menos X»: una lista de exclusiones se queda corta el día que alguien
# añade una tabla, y entonces los datos de más viajan sin que nadie lo decida. Con una lista de
# inclusión, una tabla nueva se queda fuera por omisión, que es el lado seguro del error.
# ---------------------------------------------------------------------------
TABLAS=(
  "hub_organizaciones|la organización del piloto, y sólo ella"
  "hub_chatbots|los asistentes con su configuración medida (umbrales, top_k, modo)"
  "hub_documents|el corpus curado, con su vigencia y su validación"
  "hub_document_chunks|los fragmentos y sus vectores: reembeberlos cuesta GPU y horas"
  "hub_vocabulary_terms|ámbitos y submaterias; sin esto la ingesta aborta"
  "hub_lexicon_pairs|el puente léxico catalán/castellano de la búsqueda de texto"
  "hub_web_sites|el sitio de curación"
  "hub_crawled_pages|sus páginas rastreadas, con las señales de frescura"
  "hub_content_findings|los hallazgos ya revisados por una persona: es trabajo humano"
  "hub_corpus_selections|qué páginas alimentan a qué asistente"
  "hub_prompt_templates|los prompts del sistema, afinados por medición"
  "hub_themes|la identidad visual de la organización"
  "hub_widget_keys|las credenciales de sitio ya emitidas"
  "hub_module_grants|qué módulos tiene concedidos la organización"
)

# ---------------------------------------------------------------------------
# LO QUE NO VIAJA — y se comprueba que no está en el fichero.
#
# No basta con no listarlas: se verifica sobre el volcado YA GENERADO. Un filtro mal escrito
# produce un `WHERE` que pasa los tests de la consulta y datos de más en el fichero, y esa
# diferencia es justo la que importa.
# ---------------------------------------------------------------------------
PROHIBIDAS=(
  "hub_workspaces|informes de prueba: 29 filas de basura de test"
  "hub_workspace_blocks|sus bloques"
  "hub_workspace_audit_events|sus eventos de auditoría"
  "hub_run_manifests|manifiestos de ejecución de informes"
  "hub_users|ninguna persona: se recrean por SSO al primer acceso"
  "hub_personal_access_tokens|credenciales de máquina, que se emiten donde se usan"
  "hub_interactions|conversaciones: son de quien preguntó, no del despliegue"
  "hub_test_runs|resultados de escenarios de prueba"
  "hub_test_scenarios|los escenarios"
  "hub_script_proposals|propuestas de script en revisión"
  "hub_report_templates|el catálogo del producto viaja como fichero, no como fila"
  "hub_report_template_versions|idem"
)

echo "== Volcado para el piloto =="
printf '  %-14s %s\n' "organización" "$ORGANIZACION"
printf '  %-14s %s\n' "salida" "$SALIDA"
echo
echo "  Viajan ${#TABLAS[@]} tablas:"
for entrada in "${TABLAS[@]}"; do
  printf '    %-28s %s\n' "${entrada%%|*}" "${entrada#*|}"
done
echo
echo "  NO viajan ${#PROHIBIDAS[@]} tablas:"
for entrada in "${PROHIBIDAS[@]}"; do
  printf '    %-28s %s\n' "${entrada%%|*}" "${entrada#*|}"
done
echo

if [ "$DRY_RUN" -eq 1 ]; then
  echo "(--dry-run: no se consulta la base y no se escribe nada.)"
  exit 0
fi

[ -n "$DSN" ] || { echo "ERROR: falta DATABASE_URL_SYNC o --dsn." >&2; exit 2; }
command -v psql >/dev/null 2>&1 || { echo "ERROR: psql no está en el PATH." >&2; exit 3; }
command -v pg_dump >/dev/null 2>&1 || { echo "ERROR: pg_dump no está en el PATH." >&2; exit 3; }

# `psql` y `pg_dump` quieren un DSN de libpq; SQLAlchemy añade el driver.
DSN_LIBPQ="$(printf '%s' "$DSN" | sed 's#^postgresql+psycopg2://#postgresql://#; s#^postgresql+asyncpg://#postgresql://#')"

# ---------------------------------------------------------------------------
# Recuento ANTES de escribir nada. Si las cifras no son las que se esperan, se para aquí y no
# después de haber generado un fichero que alguien podría restaurar.
# ---------------------------------------------------------------------------
echo "== Recuento en origen =="
for entrada in "${TABLAS[@]}"; do
  tabla="${entrada%%|*}"
  if [ "$tabla" = "hub_organizaciones" ]; then
    donde="id = '$ORGANIZACION'"
  else
    donde="organizacion_id = '$ORGANIZACION'"
  fi
  n="$(psql "$DSN_LIBPQ" -tAc "SELECT count(*) FROM $tabla WHERE $donde" 2>/dev/null || echo "n/d")"
  printf '  %-28s %s\n' "$tabla" "$n"
done
echo
echo "  «n/d» = la tabla no tiene columna de organización directa; su filtro va por su padre."
echo "  Revisa estas cifras ANTES de continuar: son las que tienen que aparecer al restaurar."
echo

echo "== Generando $SALIDA =="
ARGS=()
for entrada in "${TABLAS[@]}"; do
  ARGS+=("--table=${entrada%%|*}")
done
pg_dump "$DSN_LIBPQ" --data-only --no-owner --no-privileges "${ARGS[@]}" > "$SALIDA"
echo "  escrito: $(wc -c < "$SALIDA") bytes"
echo

# ---------------------------------------------------------------------------
# Verificación SOBRE EL FICHERO
# ---------------------------------------------------------------------------
echo "== Comprobando el fichero =="
PROBLEMAS=0
for entrada in "${PROHIBIDAS[@]}"; do
  tabla="${entrada%%|*}"
  if grep -qE "COPY (public\.)?$tabla " "$SALIDA"; then
    printf '  [FUGA]  %s aparece en el volcado (%s)\n' "$tabla" "${entrada#*|}"
    PROBLEMAS=$((PROBLEMAS + 1))
  fi
done
[ "$PROBLEMAS" -eq 0 ] && echo "  [ok]    ninguna tabla prohibida aparece en el fichero"

# Y que no viaje ninguna fila de otra organización. Se busca el UUID de la organización en las
# líneas de datos: si hay filas de otra, aparecerá algún UUID distinto en esa columna.
OTRAS="$(psql "$DSN_LIBPQ" -tAc \
  "SELECT string_agg(id::text, '|') FROM hub_organizaciones WHERE id <> '$ORGANIZACION'" \
  2>/dev/null || true)"
if [ -n "$OTRAS" ]; then
  while IFS= read -r otra; do
    [ -n "$otra" ] || continue
    if grep -qF "$otra" "$SALIDA"; then
      printf '  [FUGA]  aparece la organización %s\n' "$otra"
      PROBLEMAS=$((PROBLEMAS + 1))
    fi
  done < <(printf '%s' "$OTRAS" | tr '|' '\n')
  [ "$PROBLEMAS" -eq 0 ] && echo "  [ok]    ninguna otra organización aparece en el fichero"
else
  echo "  [i]     no hay otras organizaciones con las que confundirse"
fi
echo

if [ "$PROBLEMAS" -gt 0 ]; then
  rm -f "$SALIDA"
  echo "ERROR: $PROBLEMAS problema(s). **El fichero se ha borrado**: un volcado con datos de más" >&2
  echo "       que se queda en el disco es el que alguien restaura por error." >&2
  exit 1
fi

echo "Volcado listo. Restaurar en una base limpia y comprobar los recuentos de arriba."

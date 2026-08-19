# Curación en un despliegue con varias organizaciones

**Fecha**: 2026-08-19 (CUR.2.1). Sale de una pregunta del usuario mientras se ejecutaba el bloque:
la aplicación se instala en la UJI, pero está diseñada multiorganización, y varios ajustes de
curación estaban entrando **en el código** a partir de cómo es un portal concreto.

La pregunta era buena y la respuesta era «a medias». Este documento fija la frontera para que la
siguiente decisión caiga del lado correcto sin volver a discutirlo.

## La regla

**El criterio es dato; la honestidad es código.**

Es la misma regla que el proyecto ya aplica al vocabulario del corpus (CLAUDE.md §5: «el vocabulario
es dato, no código»), y por el mismo motivo: lo que depende de cómo es *un* portal tiene que poder
cambiarse sin tocar el código, o el módulo deja de servir al segundo cliente.

## Lo que es dato: configuración del sitio

Cada sitio cuelga de una organización (`HubWebSite.organizacion_id`) y los routers lo verifican, así
que **por sitio es por organización**. En `config_json`, validado por `CrawlConfig`:

| Ajuste | Qué decide | Defecto |
|---|---|---|
| `url_regex_filter` | Qué apartado es este sitio | — |
| `crawl_depth`, `max_pages`, `max_seconds` | Hasta dónde llega una ejecución | 1 / 50 / 1800 |
| `delay_seconds`, `respect_robots`, `max_concurrency`, `max_retries` | Cortesía **cuánta**, no si la hay | 1 / sí / 1 / 3 |
| `content_date_selector`, `content_date_format` | Dónde publica **este portal** la fecha de cada página | — / `%d/%m/%Y` |
| `stale_days` | Cuándo el contenido de este portal se considera antiguo | 365 |
| `thin_min_tokens` | Cuánto texto es «poco» aquí | 120 |
| `version_series_policy` | Qué significan varias versiones por año | `series` |

Los tres últimos son los que **estaban en el código** hasta CUR.2.1: el despachador construía el
detector con los valores por defecto del constructor y no le pasaba nada, así que todas las
organizaciones compartían criterio por mucho que cada sitio guardara el suyo.

### El caso que lo hizo evidente

`version_series_policy` existe porque el usuario aportó un dato del dominio que el HTML no dice: la
UJI **publica acuerdos y actas por año y todos siguen vigientes**, así que declarar «superada» la de
2017 es falso. Pero para un portal que versiona convocatorias —la de 2025 sustituye a la de 2024—
sería exactamente lo contrario. Fijarlo global era cambiar una suposición por otra:

* `series` — varias versiones, todas vigentes. Un aviso **informativo por grupo**, con sus URLs y
  fechas, para que una persona decida si sobran las antiguas.
* `superseded` — la nueva deroga a la anterior. Un aviso **por página antigua**, que es una lista de
  trabajo.
* `off` — el año de la URL no significa nada en este portal; agrupar sólo daría ruido.

## Lo que es código, y no debe poder desactivarse

Esto no describe cómo es una web: describe **qué puede afirmar el sistema**. Vale igual para
cualquier portal, y hacerlo configurable sería ofrecer la opción de mentir en el informe.

* **Cortesía**: pausa entre peticiones, `robots.txt`, `User-Agent` identificable, presupuesto. Se
  puede ajustar *cuánta*; no se puede apagar el mecanismo.
* **No acusar de lo que no se pudo leer**: una página con 404 o con error de red no es «vacía» ni
  «pobre», y una que necesita JavaScript se avisa como tal (`needs_javascript`), no como vacía.
* **404 ≠ timeout**: uno es una respuesta —contenido que ya no está— y el otro un fallo del que no se
  concluye nada sobre la página.
* **Un fallo no tumba el rastreo**: ni un enlace roto, ni un PDF servido como página, ni un error al
  guardar.
* **Un rastreo truncado no declara bajas**: lo que no se visitó no es lo que desapareció.
* **Normalizaciones de identidad de URL**: `http`/`https` de la misma página, y los parámetros de
  navegación que llevan una URL dentro (la trampa del conmutador de idioma). Son hechos sobre qué es
  la misma página, no preferencias.
* **Lo que no es una página**: PDF, imágenes, hojas de cálculo. Un PDF puede ser contenido valioso,
  pero no por esta vía.

## Lo que queda pendiente de decidir

* **Defectos por organización.** Hoy los defectos son del contrato (`CrawlConfig`), iguales para
  todos, y cada sitio los sobreescribe. Si una organización acaba con veinte apartados y el mismo
  criterio en todos, tendrá sentido una capa de defectos por organización —la cascada
  Plataforma→Organización→Sitio que el proyecto ya usa para modelos y temas—. **No se anticipa**:
  hasta que exista la segunda organización no se sabe si el criterio se repite por apartado o por
  casa.
* **El selector de plantilla de CUR.3** (quitar menús) nace ya como configuración del sitio, por la
  misma razón que el de la fecha.

# Caso guía: rastreo y curación del apartado de la Escuela de Doctorado

Primer rastreo del módulo de curación contra un portal institucional real: el apartado de la
**Escuela de Doctorado de `www.uji.es`**. Elegido porque está acotado, su contenido envejece de
verdad (convocatorias, planes, normativa de programas) y es **la misma unidad** que el caso guía del
módulo de Informes: la misma gente, dos herramientas.

Este documento recoge lo que costó, lo que encontró y **los umbrales que hubo que corregir**, para
poder repetirlo en otro apartado sin volver a descubrirlo todo.

## 1. Cómo se da de alta un apartado

Un sitio por apartado, no uno por portal. No es sólo una salida técnica: cada apartado tiene un
responsable distinto en la casa, y un informe de calidad del portal completo no lo lee nadie.

| Ajuste | Valor usado | Por qué |
|---|---|---|
| `url_regex_filter` | `escola-doctorat` | Es lo que acota el apartado |
| `crawl_depth` | 4 | Alcanza normativa y convocatorias colgadas del índice |
| `delay_seconds` | 2 | Cortesía; el defecto es 1 |
| `respect_robots` | sí | Deja `/seu/` fuera sin tener que decir nada |
| `max_pages` / `max_seconds` | 400 / 900 | Presupuesto de una ejecución; el resto se reanuda |
| `audit_semantic_scope` | **Completo** | El defecto (`Solo ingerido`) no sirve para depurar **antes** de ingerir |

Ese último es el que más fácil se queda mal puesto: con `Solo ingerido`, la auditoría semántica sólo
compara lo que ya está en el corpus —barato, y útil después— pero no puede detectar duplicados entre
páginas que aún no se han publicado.

## 2. Lo que cuesta un rastreo cortés (medido)

| Medida | Valor |
|---|---|
| Latencia del portal por página | **1,4 s** |
| Pausa de cortesía | 2,0 s |
| Coste real por página | ~3,4 s |
| 400 páginas | **14 minutos** |
| Proceso propio por página | ~4 ms… |
| …salvo `detect_language` | **153 ms** |

O sea: **el rastreo lo domina la red y la cortesía**, no nuestro código. Por eso el bloque necesitaba
presupuesto de tiempo (RAS.1) y reanudación por la cola guardada (RAS.3): el apartado no cabe en una
ejecución y empezar de cero cada vez son horas de peticiones repetidas contra el mismo servidor.

El `robots.txt` del portal declara `Disallow: /seu/` para todos los rastreadores, y el nuestro se
identifica como `GovGenAI-Curacion/1.0 (+contacto)`. Las tres URLs del apartado que caen bajo `/seu/`
no se pidieron, y eso consta en el resumen como `pages_forbidden`, no como error.

## 3. Sin navegador: medido, no supuesto

Sondeo de contenido dinámico sobre 25 páginas del apartado: **0 necesitan JavaScript**. Cada página
sirve entre 2 KB y 4 KB de texto dentro de 51 KB de HTML. Decisión y condiciones en
`docs/DECISION_RENDERIZADO_RASTREO.md`.

Dos cosas que sólo se ven con el portal delante:

* Una página **perfectamente estática** de este portal lleva `<noscript>` y **diez `<script>`**. Una
  heurística que mirara sólo eso habría declarado dinámico el portal entero y el primer informe
  habría salido lleno de acusaciones falsas.
* **El portal no publica `sitemap.xml`** (404). La señal más fiable del sondeo —el hueco entre lo que
  declara el sitemap y lo que alcanza el recorrido por enlaces— **no está disponible aquí**.

## 4. Lo que el rastreo real destapó

Siete defectos, y ninguno se veía contra un sitio de pruebas. Los tres primeros impedían
**rastrear**; los demás hacían que el informe **mintiera**.

1. **Un enlace roto tumbaba el rastreo completo.** El primer intento devolvió **cero páginas** por un
   404 en `/estudis/centres/escola-doctorat/estudiantat/`: la excepción subía hasta el `except`
   global y el sitio quedaba en `error` sin guardar nada. Todo portal real tiene enlaces rotos —son
   justo lo que este módulo busca—, así que era irrastreable por construcción.
2. **Un PDF enlazado se guardaba como si fuera página.** El recorrido siguió un `.pdf` de un acuerdo
   del consejo, `httpx` decodificó sus bytes como texto y Postgres rechazó la fila entera con
   `invalid byte sequence for encoding "UTF8": 0x00`, **tumbando otra vez el rastreo**. Antes de
   reventar ya había calculado 26.872 «tokens» de cabecera binaria e idioma «bengalí».
3. **Cada página se pedía dos veces.** El recorrido descargaba el HTML para extraer enlaces, lo
   tiraba, y el guardado volvía a pedir la misma URL. Medido en el sondeo: 25 páginas, 50 peticiones.
4. **La mitad de las páginas eran la misma en `http` y en `https`.** El portal responde por los dos
   esquemas y su HTML enlaza a los dos. Consecuencias: la mitad del presupuesto gastado en
   duplicados y **191 avisos de supersesión** entre `http://x` y `https://x`.
5. **Las tres páginas con 404 salían además como `empty` crítico.** Una página que no se pudo
   descargar no tiene contenido *porque no se leyó*, y eso ya lo dice `crawl_error`.
6. **El portal tiene una trampa de rastreador.** Su conmutador de idioma genera enlaces que llevan
   la URL actual dentro (`?urlRedirect=https://…&url=/centres/…`), así que cada página rastreada
   producía una variante más larga de sí misma: espacio de URLs infinito con el mismo contenido
   detrás. Es lo que dejaba **526 URLs pendientes** que no se acababan nunca y **107 avisos de
   supersesión** entre variantes de una sola página. Un parámetro cuyo valor es una URL o una ruta
   es un ayudante de navegación, no identidad de página: se quita antes de encolar, con un tope de
   longitud de URL como red de seguridad.
7. **Una página ilegible se declaraba «la versión vigente».** El agrupador ordena las versiones por
   fecha efectiva y, sin ninguna fecha, cae en `first_seen_at` —de hace un instante—. Así, un
   acuerdo de 2017 que falló al descargarse declaraba superados los de 2023, 2024 y 2025.

## 5. Los umbrales, corregidos con datos del portal

El informe del primer rastreo (400 páginas) salió así:

| Hallazgo | Antes | Después | Por qué |
|---|---|---|---|
| `stale` (antiguo) | **303** | **9** | La fecha salía del año más reciente **mencionado en el texto** |
| `superseded` | **191** | **9** | `http`/`https` de la misma página, y las variantes de la trampa |
| `empty` | 3 | **0** | Eran las tres que dieron 404 |
| `crawl_error` | 3 | **2** | Ciertos: enlaces del apartado que apuntan a páginas que ya no están |
| **Total** | **500** | **20** | |

**El caso de `stale` merece detalle**, porque es el que enseña cómo se calibra un umbral. El portal
**no declara ninguna fecha**: sin `Last-Modified`, sin `ETag` y sin sitemap. Así que la «fecha del
contenido» se inferría del año más reciente citado en el cuerpo de la página; en la de normativa de
estudios se leen **1925, 2010, 2016, 2021, 2024 y 2071**, y de ahí salía «contenido de 2024, 960 días
de antigüedad». Un número en el texto no es una fecha de publicación, y con esa inferencia el 76 % de
las páginas quedaba marcado: una lista de trabajo que nadie usa.

Ahora `stale` exige una fecha con procedencia, y el hallazgo **dice cuál es**: `sitemap_lastmod`,
`http_last_modified` o `url_year` —un año en la URL, que sí es una señal del portal, porque así
versiona sus documentos (`/2019/`, `/pext/19-20/`)—. Contra este portal eso deja sólo el tercer caso,
que es el útil.

## 6. Resultado del rastreo tras las correcciones

| Medida | Valor |
|---|---|
| Páginas del apartado | **351** |
| Peticiones | 353 (una por página, más el `robots.txt` y los reintentos) |
| Duración | ~12 min (569 s de red) |
| Rastreo | **completo**: 0 URLs pendientes, sin truncar |
| Excluidas por `robots.txt` | 4 (todas bajo `/seu/`) |
| Páginas en error | 2, las dos 404 reales |
| Páginas que necesitan JavaScript | 0 |
| Texto por página | mediana 813 tokens (máx. 2.610) |
| **Hallazgos** | **20** |

**Y aquí está la respuesta a la pregunta que abrió el bloque —«¿se puede rastrear `www.uji.es` de
golpe o hay que fraccionar?»—: fraccionado por apartado, sí, y de una sola vez.** El apartado de la
Escuela de Doctorado son 351 páginas y cabe en doce minutos con la cortesía puesta. Lo que no cabía
era el rastreo con la trampa de parámetros: la primera pasada dejó 734 URLs pendientes que no eran
páginas, sino variantes de la misma.

**Los 20 hallazgos, revisados uno a uno:**

* **9 `superseded`** — los acuerdos del consejo de doctorado de 2017, 2018, 2019… todos apuntando a
  `/acordacded/2025/` como versión vigente. **Ciertos**, y es exactamente el caso que motivó el
  bloque: la nueva se publicó y las viejas siguen ahí.
* **9 `stale`** — las mismas páginas por año, con `source: url_year` y entre 7 y 10 años de
  antigüedad. **Ciertos**, y accionables: son documentos que alguien debería revisar o retirar.
* **2 `crawl_error`** — `/centres/escola-doctorat/estudiantat/` y
  `/base/info-academica/contractes-premis/pext/19-20/`, los dos 404 con severidad *aviso*: enlaces
  del apartado que apuntan a contenido que ya no está. **Ciertos**, y es depuración pura del portal.

Cero falsos positivos sobre 351 páginas, frente a los 500 avisos de la primera pasada.

**Un aviso sobre la red, que también es una lección del bloque:** en una de las pasadas
intermedias, la resolución DNS de la máquina falló a mitad del rastreo y 30 páginas dieron error.
Salieron como `crawl_error` con severidad **informativa**, `kind: transient` y `attempts: 3` —no como
hallazgos críticos ni como páginas vacías—, que es exactamente lo que RAS.3 vino a arreglar: de un
fallo de red no se concluye nada sobre la página. La siguiente pasada las recuperó.

## 7. Del portal al asistente

La bandeja de curación **no es un corpus**. Para que un asistente responda con estas páginas hay que
publicarlas, y eso es una decisión por candidata (`docs/DECISION_CURACION_SEPARADA.md`). Lo que la
ingesta **no** hace es volver a rastrear: reutiliza el texto que ya trajo el rastreo.

Tres cosas que estaban desconectadas en ese camino y ahora no:

* **El botón de ingerir respondía 202 y no ingería nada**: el servicio inyectado venía sin watcher y
  el `AttributeError` moría dentro de un `BackgroundTask`.
* **Una página del corpus que cambiaba en el portal no se actualizaba.** El rastreo detectaba el
  cambio (`content_hash`) y `changed_page_ids` no lo consumía nadie: el asistente seguía respondiendo
  con el texto viejo. Ahora se reingiere **sólo donde ya estaba** —actualizar lo aprobado no es
  publicar lo que nadie aprobó— y queda un aviso `content_updated` con el enlace.
* **El job del arranque se construía con `watcher=None`**, así que nada de esto podía ocurrir en la
  aplicación real. Ahora recibe una fábrica que resuelve el modelo de embeddings **de cada chatbot**:
  ingerir con otro modelo del que usa su corpus deja vectores que no se pueden comparar.

## 8. Límites conocidos

* **El menú del portal viaja en cada página.** De los ~4 KB de texto de una página, buena parte es la
  navegación, idéntica en todas. Al corpus entra con el contenido. Quitar el *boilerplate* no está
  hecho.
* **El apartado no cabe en una ejecución** con la cortesía puesta: se rastrea por tandas y se reanuda.
* **La auditoría semántica cuesta un embedding por página** en alcance `Completo`. Para un apartado de
  cientos de páginas es calderilla; para un portal de decenas de miles, no lo sería.
* **`/seu/` queda fuera** por decisión del portal en su `robots.txt`. Si algún día hiciera falta
  rastrear la sede electrónica, es una conversación con quien la gestiona, no un ajuste.

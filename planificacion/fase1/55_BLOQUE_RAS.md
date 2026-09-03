## Bloque RAS — Rastreo de un portal institucional real

> **Planificado el 2026-08-18.** Caso guía: **el apartado de la Escuela de Doctorado de
> `www.uji.es`**, elegido porque está acotado, su contenido envejece de verdad (convocatorias,
> planes, normativa de programas) y **es la misma unidad que el caso de los informes de
> seguimiento** del Bloque SEG: la misma gente, dos herramientas.
>
> **La finalidad ya está construida** y no se toca: los detectores emiten `empty`, `thin`,
> `stale`, `orphan_page`, `crawl_error` y **`superseded`** —este último agrupa versiones del mismo
> recurso quitando los segmentos de año de la URL, que es exactamente «la nueva se publicó y la
> vieja sigue ahí»—, más duplicado y contradicción por semántica. Y `CorpusSelectionService` ya
> lleva de la página rastreada al corpus del asistente, con la decisión en manos de una persona.
>
> **Lo que falta es poder apuntarlo a un portal de verdad**, y son cuatro cosas. La primera es de
> seguridad operativa y la segunda de credibilidad; sin ellas esto no debe lanzarse contra
> `www.uji.es` ni para una demo.
>
> **Fraccionar, no rastrear el portal entero.** El spider ya lee `url_regex_filter` de la
> configuración del sitio, así que se da de alta **un sitio por apartado**, con su periodicidad.
> No es solo una salida técnica: cada apartado tiene un responsable distinto en la casa, y un
> informe de calidad por apartado es accionable mientras que uno del portal completo no lo lee
> nadie.

### Prompt RAS.1 (RED/GREEN) — Cortesía: no parecer un ataque contra tu propia casa

**Modelo sugerido**: **Sonnet** — alcance cerrado.

```
# PROMPT RAS.1 (RED/GREEN) — Pausa, robots.txt y presupuesto del rastreo
# Deploy: edge (modules/curation/spider.py)

## Por que
El bucle es `while queue: await self._fetch(url)`: secuencial, con timeout de 10 s y **sin pausa
entre peticiones ni lectura de `robots.txt`**. Contra un sitio de pruebas da igual; contra el
portal de la propia institucion, miles de peticiones seguidas desde una IP figuran en los
registros del servidor web como lo que parecen. Es el requisito que convierte esto en una
herramienta que se puede usar en casa.

## Que hacer
1. RED: dos peticiones consecutivas al mismo host **no salen** sin la pausa configurada; una ruta
   excluida por `robots.txt` no se pide; un `Crawl-delay` declarado por el sitio se respeta y gana
   sobre la configuracion propia si es mayor.
2. GREEN: `delay_seconds` y `respect_robots` en la configuracion del sitio, con valores por
   defecto **conservadores** -la cortesia es el defecto, no una opcion-. Cabecera `User-Agent`
   identificable, con contacto: quien vea el trafico tiene que poder saber quien es y a quien
   escribir.
3. Presupuesto por ejecucion **de tiempo**, ademas de `max_pages`. Alcanzado el presupuesto, el
   rastreo termina en `COMPLETED_PARTIAL` -que ya existe- y **dice** cuantas URLs quedaron en la
   cola.
4. Concurrencia acotada y configurable, nunca ilimitada, y por host.

## Criterio de done
- [ ] La pausa se respeta (medido, no supuesto)
- [ ] Una ruta prohibida por robots.txt no se pide
- [ ] El User-Agent identifica al sistema y a un contacto
- [ ] Un rastreo truncado dice cuanto se dejo sin ver
```

### Prompt RAS.2 (RED/GREEN) — Detectar el contenido dinámico y **avisar**, no llamarlo vacío

**Modelo sugerido**: **Opus** — decide qué evidencia basta para afirmar «esto necesita
JavaScript», y esa decisión determina la credibilidad del informe.

```
# PROMPT RAS.2 (RED/GREEN) — Sondeo de contenido dinamico
# Deploy: edge (modules/curation/)

## Por que
Los enlaces se extraen con una expresion regular sobre `href=` del HTML servido. Una pagina que
pinta su contenido con JavaScript vuelve **sin texto**, y el detector determinista emite hoy
`empty` con severidad **critica**. Es un falso positivo que afirma lo contrario de la verdad:
la pagina esta llena y el rastreador es el que no ve. En la primera pasada contra un portal real
eso llena el informe de acusaciones falsas y le quita toda la credibilidad -y es lo primero que
notaria quien conoce esas paginas-.

El usuario lo pregunto en estos terminos: "se podria analizar antes o que si que avisara". Las dos
cosas, y en este orden.

## Que hacer
1. **Sondeo previo, antes del rastreo completo.** Sobre una muestra de URLs del apartado, decidir
   si necesita renderizado, **sin navegador** y por tanto sin dependencias nuevas. Senales, de mas
   fiable a menos:
   - **El hueco entre el sitemap y los enlaces alcanzados.** Ya se calcula: el rastreo une las URLs
     del spider con las del sitemap. Si el sitemap declara cientos de paginas que el recorrido por
     enlaces no alcanza, los listados son dinamicos. Es la senal mas fuerte y sale gratis.
   - Un `<body>` con muy poco texto y muchos `<script>`.
   - Marcadores de framework: `__NEXT_DATA__`, `data-reactroot`, `ng-app`, contenedores `id="app"`
     o `id="root"` vacios.
   - Un `<noscript>` que pide activar JavaScript.
2. **El informe del sondeo** dice, por apartado: cuantas paginas parecen dinamicas, con que senal, y
   **si merece la pena renderizar** o el contenido estatico basta.
3. RED/GREEN del cambio que importa: una pagina con evidencia de contenido dinamico **no genera
   `empty`**. Genera `needs_javascript` -aviso, no critico- que dice "no se ha podido leer sin
   renderizar", que es lo unico que el sistema sabe de verdad.
4. Lo mismo con `thin`: no se acusa de contenido pobre a una pagina que no se ha podido leer.

## Restricciones
- **Sin navegador en este prompt.** Solo heuristicas sobre el HTML servido y el sitemap. Meter un
  navegador aqui seria decidir la solucion antes de medir el problema (P2, frugalidad).

## Criterio de done
- [ ] Sondeo ejecutado contra el apartado real, con cifras
- [ ] Una pagina dinamica sale como `needs_javascript` y **nunca** como `empty`
- [ ] El informe dice si hace falta renderizar, y con que evidencia
```

### Prompt RAS.3 (RED/GREEN) — Rastreo reanudable, y un fallo transitorio no es un hallazgo

**Modelo sugerido**: **Sonnet**.

```
# PROMPT RAS.3 (RED/GREEN) — Reanudar y reintentar
# Deploy: edge (modules/curation/)

## Por que
La cola BFS vive **en memoria** y el rastreo arranca siempre de `root_url`: si se corta en la
pagina 8.000, se empieza de cero. Y no hay reintentos: un `timeout` de 10 s marca la pagina como
error y produce un `crawl_error` **critico**. En un rastreo grande eso son decenas de falsos
positivos por causas de red, mezclados con los hallazgos de verdad.

## Que hacer
1. Persistir la frontera del rastreo -URLs pendientes con su profundidad- para que una ejecucion
   interrumpida **retome donde se quedo** en vez de repetir lo hecho.
2. Reintentos con espera creciente antes de dar una URL por fallida. Solo lo que falla de forma
   persistente llega a `crawl_error`, y el hallazgo dice **cuantos intentos** hubo.
3. Distinguir en los hallazgos lo que dice el servidor: un 404 es contenido que ya no esta -y eso
   es informacion util para depurar-, un 500 o un timeout es un fallo del que no se puede concluir
   nada sobre la pagina.

## Criterio de done
- [ ] Un rastreo interrumpido se reanuda sin repetir lo ya visitado
- [ ] Un fallo transitorio no genera hallazgo; uno persistente si, con su recuento
- [ ] 404 y 5xx no se confunden en el informe
```

### Prompt RAS.4 (decisión + RED/GREEN) — Renderizar, sólo si el sondeo dice que hace falta

**Modelo sugerido**: **Opus** — es una decisión de despliegue con coste, no solo código.

```
# PROMPT RAS.4 (decision) — Navegador sin cabeza, como extra opcional
# Deploy: edge

## Por que
Si el sondeo de RAS.2 dice que una parte grande del apartado es dinamica, no hay forma de leerla
sin renderizar. Pero un navegador sin cabeza **no es gratis**: pesa cientos de megabytes y el
despliegue previsto es una VM pequena -la aplicacion esta en ~345 MB justamente porque los modelos
locales se hicieron opcionales-. Es la misma decision que se tomo con `torch`, y se resuelve igual.

## Que hacer
1. **Primero la medicion de RAS.2.** Si el contenido estatico cubre el apartado, este prompt se
   cierra sin codigo y se documenta por que: seria infraestructura anticipada.
2. Si hace falta: renderizado detras del mismo protocolo de fetch que ya usa el spider, como
   **extra de instalacion** (`[render]`), desactivado por defecto y activable **por sitio**.
   Ningun sitio renderiza por accidente.
3. La cortesia de RAS.1 se aplica igual o mas: un navegador pide muchos mas recursos por pagina.
4. Documentar el coste real medido -tamano de imagen, memoria, segundos por pagina- para que la
   decision de activarlo en produccion se tome con cifras.

## Criterio de done
- [ ] La decision tomada **con la medicion delante**, y escrita
- [ ] Si se implementa: extra opcional, por sitio, desactivado por defecto
- [ ] Coste medido y documentado
```

### Prompt RAS.5 (verificación) — La Escuela de Doctorado, de punta a punta

**Modelo sugerido**: **Sonnet**.

```
# PROMPT RAS.5 (verificacion) — El primer apartado real

## Por que
Es la demo, y es lo que dice si el modulo sirve: encontrar contenido que retirar y contenido que
merece entrar en el asistente.

## Que hacer
1. Alta del sitio: apartado de la Escuela de Doctorado, con su `url_regex_filter`, su profundidad,
   su presupuesto y la cortesia de RAS.1.
2. Sondeo (RAS.2) y **decision registrada** sobre renderizado.
3. Rastreo, informe de calidad y revision de los hallazgos **uno a uno con criterio humano**: de
   cada tipo, si el hallazgo es cierto. Es la unica forma de saber si los umbrales -`thin`,
   `stale`- valen para este portal o hay que ajustarlos.
4. Selección de candidatas al corpus de un asistente y una consulta que **cite** una de las
   paginas ingeridas: cierra el circuito rastreo → curacion → RAG.
5. `docs/CASO_CURACION_ESCOLA_DOCTORAT.md` con las cifras y los ajustes de umbral, para replicarlo
   en otros apartados.

## Criterio de done
- [ ] Rastreo completo del apartado, con cortesia y sin incidencias en el servidor
- [ ] Hallazgos revisados por tipo, con los falsos positivos identificados
- [ ] Una pagina rastreada, ingerida y citada por el asistente
- [ ] Umbrales ajustados con datos del portal real, no con los de laboratorio
```

---

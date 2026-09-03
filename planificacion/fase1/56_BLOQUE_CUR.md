## Bloque CUR — La curación vista por quien cura

> **Planificado el 2026-08-19**, a partir de las pruebas humanas del Bloque RAS sobre el apartado de
> la Escuela de Doctorado. Ocho observaciones del usuario, y ninguna es de estilo: cuatro son
> hallazgos falsos o duplicados, tres son cosas que **no se pueden hacer** desde la interfaz —ver el
> contenido de una página, abrir una URL, elegir qué se ingiere— y una es un botón que responde 401.
>
> **El hilo común**: el módulo produce un informe y no da forma de comprobarlo. Quien cura tiene que
> poder abrir la página, leer su contenido y decidir; hoy tiene que copiar y pegar URLs.
>
> **Un dato del dominio que cambia un detector**: el portal publica acuerdos y actas **por año** y
> *todos siguen vigentes*; los nuevos no derogan a los anteriores. Así que agrupar por año y declarar
> «superada» la de 2017 afirma algo falso. Lo dijo el usuario, no se deduce del HTML.
>
> **Y un regalo del portal que estábamos ignorando**: cada página publica su fecha y su unidad
> responsable en el HTML (`<div class="clockBarDate">` → `24/09/2025` | `Escola de Doctorat`). Con eso,
> «desactualizada» pasa de conjetura a dato.

### Prompt CUR.1 (RED/GREEN + migración) — La fecha que el portal ya publica

**Modelo sugerido**: **Sonnet** — alcance cerrado.

```
# PROMPT CUR.1 (RED/GREEN) — La fecha de la pagina, y quien la mantiene
# Deploy: edge (modules/curation/)

## Por que
`stale` se apoyaba en el ano mas reciente citado en el texto (303 de 400 paginas marcadas) y desde
RAS.5 solo en un ano dentro de la URL. Pero el portal **publica la fecha**: esta en el HTML, junto a
la unidad responsable. Medido en `/centres/escola-doctorat/base/doctorands/`: `24/09/2025` dentro de
`<div class="clockBarDate">`, seguido de `<span>Escola de Doctorat</span>`.

Con esa fecha, `stale` deja de ser una conjetura. Y la unidad responsable es justo lo que hace
accionable un informe de calidad: dice a quien escribir.

## Que hacer
1. `CrawlConfig` gana `content_date_selector` (selector CSS) y `content_date_format`, **por sitio y
   vacios por defecto**: no se hardcodea el marcado de un portal concreto, igual que no se hardcodea
   su URL.
2. Al rastrear, si el sitio declara selector: extraer fecha y unidad responsable y persistirlas
   (`content_published_at`, `content_owner`). Un selector que no encuentra nada **no rompe** el
   rastreo: la pagina queda sin fecha, que es lo que era antes.
3. `stale` usa esa fecha con prioridad sobre todo lo demas, y el hallazgo dice `source: page_date`.
4. El informe de calidad muestra la unidad responsable de cada pagina con hallazgos.

## Criterio de done
- [ ] La fecha real del portal extraida y guardada (medido contra la pagina de verdad)
- [ ] `stale` con `source: page_date` cuando la hay
- [ ] Sin selector configurado, el comportamiento no cambia
- [ ] Migracion aplicada
```

### Prompt CUR.2 (RED/GREEN) — Una serie anual no es una versión superada

**Modelo sugerido**: **Opus** — decide qué se puede afirmar de un grupo de URLs con año.

```
# PROMPT CUR.2 (RED/GREEN) — Un grupo, un hallazgo, y sin duplicar apartados
# Deploy: edge (modules/curation/deterministic_detector.py)

## Por que
El usuario, que conoce el contenido: «se utiliza el sistema de publicar acuerdos o actas por anos
pero todos son validos. Los mas recientes no derogan a los anteriores». Nuestro agrupador declara
`superseded` la de 2017 «superada por» la de 2025: afirma algo falso.

Y aparecen **las mismas paginas en los dos apartados**, `stale` y `superseded`, que es ruido: una
lista de trabajo con la misma pagina dos veces no se usa.

## Que hacer
1. Un grupo de versiones por ano produce **un solo hallazgo del grupo**, no uno por cada version
   antigua, con la lista de URLs y sus fechas en la senal. Severidad informativa: es «hay una serie
   anual, revisa si sobran las antiguas», no «esto esta obsoleto».
2. Una pagina **no puede salir en dos apartados**: si tiene el hallazgo especifico (serie/version),
   no se emite tambien el genérico de antiguedad. El especifico se come al generico.
3. Distinguir de verdad los dos casos donde se pueda: dos URLs con **el mismo contenido**
   (`content_hash` igual) y fechas distintas si son duplicado a depurar, y eso el usuario lo pidio
   explicitamente: mostrar las dos URLs con sus dos fechas.

## Criterio de done
- [ ] Una serie de nueve anos da UN hallazgo, no nueve
- [ ] Ninguna pagina aparece en dos tipos de hallazgo a la vez
- [ ] Dos URLs con el mismo contenido salen juntas, con sus fechas
```

### Prompt CUR.2.1 (RED/GREEN) — El criterio es dato, no código

**Añadido el 2026-08-19, a mitad del bloque**, por una pregunta del usuario: la aplicación se
instala en la UJI pero está diseñada multiorganización, y varios ajustes de curación estaban
entrando **en el código** a partir de cómo es un portal concreto.

**Modelo sugerido**: **Opus** — decide qué es criterio de un cliente y qué es honestidad del sistema.

```
# PROMPT CUR.2.1 (RED/GREEN) — Los criterios de curacion, por sitio
# Deploy: edge (modules/curation/) + frontend

## Por que
Comprobado: el aislamiento de datos si es por organizacion -cada sitio cuelga de
`organizacion_id` y los routers lo verifican- y todo lo del rastreo ya era configuracion del
sitio. Pero **los criterios de juicio eran globales**:

- `stale_days=365` y `thin_token_threshold=120` los ponia el constructor del detector y
  **nadie los pasaba**: `DeterministicDetectorDispatcher` lo instanciaba con los defectos.
- CUR.2 acababa de fijar **global** que una serie por anos no supersede. Para la UJI es cierto
  -lo aporto quien conoce el contenido-, pero un portal que versiona convocatorias hace lo
  contrario. Una suposicion global cambiada por otra.

Es la misma regla que el proyecto ya aplica al vocabulario del corpus: **el criterio es dato, no
codigo**.

## Que hacer
1. `CrawlConfig` gana `stale_days`, `thin_min_tokens` y `version_series_policy`
   (`series` | `superseded` | `off`), con los valores de hoy como defecto: desplegar esto no
   puede cambiarle el informe a quien no ha tocado nada.
2. El despachador se los pasa al detector, que hoy los ignora por completo.
3. El formulario del sitio los ofrece, en su propio bloque «criterios de curacion».
4. **Escribir la frontera** en `docs/CURACION_MULTIORGANIZACION.md`: que es dato (criterio de un
   portal) y que es codigo y **no debe poder desactivarse** (cortesia, no acusar de lo que no se
   pudo leer, 404 != timeout, un fallo no tumba el rastreo, la identidad de una URL).

## Criterio de done
- [ ] Dos sitios con criterios distintos, sobre paginas identicas, dan hallazgos distintos
- [ ] Un sitio que no declara nada conserva el criterio de hoy
- [ ] Lo que no es criterio sino honestidad **no** aparece en la configuracion
- [ ] La frontera, escrita
```

### Prompt CUR.3 (RED/GREEN) — Al corpus solo el contenido

**Modelo sugerido**: **Opus** — quitar el menú sin comerse contenido es un juicio, y se afina
mirando páginas concretas.

```
# PROMPT CUR.3 (RED/GREEN) — Fuera el menu y la estructura comun
# Deploy: edge (modules/curation/contenido_web.py)

## Por que
El usuario quiere crear un chatbot con esto, y hoy **cada pagina lleva el menu completo del portal**:
de los ~4 KB de texto de una pagina, buena parte es navegacion identica en todas. Al corpus entra con
el contenido, asi que el asistente recupera menus y los cita.

## Que hacer
1. Quitar por **estructura**, no por lista de palabras: `<nav>`, `<header>`, `<footer>`, `<aside>`, y
   los contenedores que el sitio declare como plantilla (selector configurable por sitio, mismo
   patron que CUR.1).
2. Y quitar por **repeticion medida**, que es lo unico que generaliza: los bloques de texto que
   aparecen identicos en la mayoria de las paginas del sitio son plantilla, no contenido. Se calcula
   sobre lo ya rastreado, sin pedir nada.
3. **Regla de seguridad**: si el recorte se lleva mas de la mitad del texto de una pagina, se avisa y
   se conserva el original. Comerse contenido es peor que dejar el menu.
4. Medir el antes y el despues sobre el apartado real: caracteres de plantilla frente a contenido.

## Criterio de done
- [ ] El texto guardado de una pagina real no lleva el menu del portal
- [ ] Ninguna pagina pierde su contenido (comprobado con las mas cortas)
- [ ] Cifras del antes y el despues
```

### Prompt CUR.4 (RED/GREEN) — Poder mirar lo que el informe dice

**Modelo sugerido**: **Sonnet**.

```
# PROMPT CUR.4 (RED/GREEN) — Abrir la pagina, leer su contenido, desplegar el resto
# Deploy: edge + frontend

## Por que
El informe acusa y no deja comprobar: «hay que copiar y pegar». Y no hay ninguna pantalla que muestre
el texto de una pagina rastreada, que es lo que hace falta para juzgar un hallazgo o para decidir si
una pagina merece entrar en el corpus.

## Que hacer
1. URLs clickables en hallazgos y en publicacion, abriendo en pestana nueva (`rel="noopener"`) para no
   perder la navegacion.
2. El «+4 mas» de los grupos, desplegable.
3. Ver el **contenido guardado** de una pagina: el texto que de verdad iria al corpus, no la pagina
   original. Es la unica forma de comprobar que CUR.3 no se come nada.

## Criterio de done
- [ ] Toda URL del informe se abre en pestana nueva
- [ ] El resto de un grupo se despliega sin salir de la pagina
- [ ] Se puede leer el texto guardado de una pagina rastreada
```

### Prompt CUR.5 (RED/GREEN) — La descarga y la seleccion

**Modelo sugerido**: **Sonnet**.

```
# PROMPT CUR.5 (RED/GREEN) — El informe se descarga y las paginas se eligen
# Deploy: edge + frontend

## Por que
Dos botones que no funcionan. El de descargar el informe es un `<a href download>` **sin la cabecera
de autorizacion**, asi que el servidor responde 401 y el navegador muestra su propio error de
descarga: el endpoint esta bien, el enlace no puede pedirlo asi. Y en publicacion no se pueden
desmarcar paginas: «Convendria que se pudiera elegir».

## Que hacer
1. La descarga con el token: pedir el fichero con el cliente autenticado y entregarlo al navegador.
2. Seleccion multiple de candidatas: marcar, desmarcar, seleccionar todo, y **ingerir lo marcado**.
3. Que se vea lo que ya esta ingerido, para no volver a publicarlo.

## Criterio de done
- [ ] DOCX y PDF se descargan de verdad (comprobado en navegador)
- [ ] Se puede marcar y desmarcar, e ingerir solo lo marcado
```

### Prompt CUR.6 (RED/GREEN) — Reconocimiento antes de rastrear

**Modelo sugerido**: **Sonnet**.

```
# PROMPT CUR.6 (RED/GREEN) — Cuantas paginas tiene esto, antes de comprometerse
# Deploy: edge + frontend

## Por que
El usuario: «convendria que al dar de alta un nuevo sitio se pudiera generar y descargar un sitemap.
De ese modo se podria valorar la extension del sitio y si conviene hacerlo todo de golpe o por
subapartados». El portal **no publica sitemap** (404), asi que hay que construirlo: es el recorrido
de RAS.2 sin guardar nada, con su informe.

## Que hacer
1. Reconocimiento acotado (profundidad y tope propios, cortesia de RAS.1) que devuelve las URLs
   encontradas agrupadas por primer nivel de ruta, con su recuento.
2. Descargable como CSV, que es lo que se puede compartir con quien decide.
3. Estimacion de tiempo con la cortesia puesta: es el dato que responde «de golpe o por apartados».

## Criterio de done
- [ ] Recuento por subapartado y total
- [ ] CSV descargable
- [ ] Estimacion de duracion del rastreo completo
```

### Prompt CUR.7 (RED/GREEN) — Que «Completo» signifique algo

**Modelo sugerido**: **Sonnet**.

```
# PROMPT CUR.7 (RED/GREEN) — Cablear el detector semantico
# Deploy: edge (main.py, modules/curation/)

## Por que
El sitio esta guardado con `audit_semantic_scope='full'` y **no cambia nada**: el job del arranque
solo recibe el detector determinista. El semantico —duplicados y contradicciones por significado—
existe, tiene sus tests y **no lo ejecuta nadie**. Mismo patron que el watcher de RAS.5.

## Que hacer
1. Cablear el detector semantico en el job, detras del flag que ya existe
   (`content_quality_semantic_enabled`) y del alcance del sitio.
2. Su servicio de embeddings, resuelto como el de la ingesta: por el chatbot cuando lo haya, y por la
   configuracion de plataforma cuando no.
3. Que el alcance sea **editable** desde la pantalla del sitio: hoy solo se fija al crear.
4. Ejecutarlo contra el apartado real y revisar los duplicados que encuentre uno a uno.

## Criterio de done
- [ ] El detector semantico corre de verdad (medido: hallazgos o cero razonado)
- [ ] El alcance se puede cambiar despues de crear el sitio
- [ ] Los duplicados encontrados, revisados
```

---

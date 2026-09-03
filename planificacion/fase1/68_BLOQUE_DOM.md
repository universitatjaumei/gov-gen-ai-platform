## Bloque DOM — El dominio institucional sirve lo público (PENDIENTE, planificado el 2026-09-01, **rehecho el 2026-09-02** cuando apareció el DNS)

> **El prerrequisito externo ya está cumplido**: el 2026-09-02 `normativa.uji.es` resuelve a
> `34.175.38.129` y el certificado de HARICA que cargó D.8 en Secret Manager sirve por SNI. El
> bloque se ejecuta del tirón, que es lo que decidió el usuario cuando lo planificó bloqueado.

**Origen**: pregunta del usuario el 2026-09-01 — «¿el bucket con el buscador está en la misma IP?
¿Se puede utilizar también este subdominio?». No: el bucket lo sirve la infraestructura de Google
(siete IPs rotando, `Server: UploadServer`), y la VM es `34.175.38.129`. De las tres formas de
darle el dominio al buscador —proxy en Caddy, segundo subdominio con segundo certificado, o
balanceador HTTPS delante del bucket a 18-25 €/mes— el usuario eligió la primera.

### Qué cambió el 2026-09-02, y por qué el plan anterior ya no valía

La primera versión de este bloque decidió **no mover el panel**: `normativa.uji.es` serviría sólo
lo público y el panel se quedaría en el nombre provisional, para no tocar el frontend. Al aparecer
el DNS, lo primero que vio el usuario al abrir el dominio fue **el login del panel** —que es
literalmente lo que aquel reparto dejaba en la raíz mientras la plantilla del sitio importara el
fragmento del panel—, y pidió lo contrario: en la raíz, la portada pública; el login, bajo una
ruta propia.

Medido antes de replanificar, mover el panel sale mucho más barato de lo que el plan supuso:

- **Una sola navegación absoluta en todo el frontend** (`LoginPage.tsx:96`), y va a la API, no a
  una ruta de la aplicación. Ni un `href="/…"` de navegación en el código de producción.
- **La vuelta del SSO ya es configuración**: `SAML_FRONTEND_RETURN_URL`, leída en
  `core/config.py:110`. No hay ninguna ruta de callback escrita en el servidor.
- **El widget se compila aparte** (`vite.config.widget.ts`, modo `lib`), así que un `base` en la
  configuración del panel no le afecta: es el fichero que viaja al bucket y el que sostiene las
  313 páginas publicadas.

Y aparece una **simplificación** que el plan anterior no podía tener: con el panel bajo un
prefijo, **los dos nombres pueden servir exactamente lo mismo con un solo fragmento de rutas**. El
plan de la primera versión necesitaba dos fragmentos —uno con la raíz al panel y otro con la raíz
al bucket— sólo porque el panel ocupaba la raíz. Se conserva `(govgenai_rutas)`, con su reparto
nuevo, y los tests de D.8 que fijan «los dos nombres sirven lo mismo» siguen valiendo tal cual.

### El reparto, que es la decisión de diseño del bloque

Decidido por el usuario el 2026-09-02 sobre tres propuestas medidas:

| Dirección | Qué sirve | Quién |
|---|---|---|
| `normativa.uji.es/` | portada pública: índice y presentación | bucket, `index.html` |
| `normativa.uji.es/cercador` | cercador de normativa | redirección 301 a `/cercador.html` |
| `normativa.uji.es/gerencia` | cercador de Gerència | redirección 301 a `/cercador_gerencia.html` |
| `normativa.uji.es/html/<norma>.html#art-63` | la ficha de una norma | bucket, **sin cambiar de forma** |
| `normativa.uji.es/pdf/…`, `/img/…`, `/widget.iife.js` | PDF, imágenes y el widget | bucket |
| `normativa.uji.es/api/*` | la API | `app:8000` |
| `normativa.uji.es/health` | salud | `app:8000` |
| `normativa.uji.es/panel/` | **el panel de gestión, y el login** | `frontend:80` |

Y las tres razones de las tres decisiones:

- **`/panel` y no `/plataforma`**, que es lo que el usuario propuso primero: el panel ya tiene
  una sección interna en `/plataforma` (la administración de plataforma, creada en PLAT.2), así
  que montarlo ahí daría `/plataforma/plataforma/modelos`. El usuario eligió `/panel` al verlo.
- **La raíz la sigue produciendo el pipeline del corpus**, no este repositorio. Su `index.html`
  ya *es* un índice con presentación —título, 313 documentos, 7.350 unidades citables, tarjeta al
  cercador, identidad visual de la Universitat y el asistente incrustado—; lo que le falta es la
  presentación del proyecto, la tarjeta del cercador de Gerència y el acceso al panel. Escribir
  una portada nueva en este repositorio duplicaría esa identidad visual en un sitio desconectado
  del programa que la mantiene.
- **Las direcciones de las normas no cambian de forma.** `html/<slug>.html` es un detalle de
  implementación algo feo, pero es la forma que tienen los 313 ficheros y **los enlaces relativos
  entre ellos** (cercador→ficha, ficha→PDF). Cambiarla obligaría a tocar el generador, que vive
  fuera de este repositorio, y a que 313 páginas se volvieran a subir con enlaces nuevos. Lo
  único que cambia es la **base**, que es lo que este bloque ya iba a hacer.

**Un hallazgo que obliga a una línea de configuración**: la raíz del bucket devuelve **200 con el
listado XML de todos sus objetos** (`ListBucketResult`, medido el 2026-09-02). GCS sólo mapea
`/` → `index.html` con la configuración de sitio web, que necesita el balanceador que este bloque
evitó. Así que el proxy tiene que **reescribir la raíz** explícitamente; sin esa línea,
`normativa.uji.es/` serviría el inventario del bucket en vez de la portada.

**Dos cosas que se comprobaron ANTES de planificar, porque la primera versión de este plan las
daba por buenas al revés:**

- **La credencial de sitio sigue siendo necesaria.** Compartir origen no la elimina: medido el
  2026-09-01, el chat sin cabecera `X-Widget-Key` responde **401** aunque el chatbot sea
  `public_anon`. La credencial identifica el *sitio*, no el origen.
- **CORS no se cierra.** Mientras la URL del bucket siga siendo pública, las páginas servidas
  desde ahí son de otro origen y necesitan su entrada en `CORS_ALLOWED_ORIGINS`. Lo que sí
  desaparece es la dependencia de CORS **para quien entre por el dominio**, que será la mayoría.

**Reglas duras del bloque:**

- **Nada deja de funcionar en ningún paso.** Los dos nombres y las dos URL del sitio conviven
  durante todo el bloque: la del bucket sigue sirviendo las páginas y el nombre provisional sigue
  sirviendo la API y el panel. Un bloque que necesite una ventana de caída está mal planificado.
- **El panel queda bajo `/panel/` en los DOS nombres, y eso no es una elección: es el
  mecanismo.** `base` es de tiempo de compilación, así que la imagen del frontend referencia
  `/panel/assets/…` sea quien sea el que la sirva. Servirla en la raíz de un nombre y bajo prefijo
  en el otro exigiría dos imágenes del frontend.
- **El prefijo no se escribe en el código de la aplicación.** El router lo toma de
  `import.meta.env.BASE_URL`, que Vite deriva de `base`; así el mismo código sirve en desarrollo
  (raíz) y en la imagen (`/panel/`) sin ningún literal, y los tests siguen montando en la raíz.
- **La imagen del frontend se comporta igual con proxy y sin él.** Su nginx sirve el panel en
  `/panel/` de verdad, no gracias a que alguien le quite el prefijo por delante: un
  `handle_path` que lo despoje deja el contenedor roto para quien lo abra directo, y esa
  diferencia sólo se descubre depurando.
- **`data-api-url` se mantiene, apuntando al dominio nuevo.** Quitarlo sólo funcionaría si las
  páginas fueran alcanzables *únicamente* por el dominio; mientras la URL del bucket exista, una
  página sin `data-api-url` servida desde ahí llamaría a `storage.googleapis.com/api/v1` y daría
  404. Lo explícito funciona desde los dos sitios.
- **El bucket se queda público.** Cerrarlo obligaría a que Caddy se autenticara contra GCS —el
  `reverse_proxy` a secas no lo hace— y eso es un bloque distinto. Queda anotado como opción, no
  como parte de éste. Lo que sí deja de estar expuesto por el dominio es el listado XML.
- **Una sola fuente de verdad para la base del sitio.** `CORPUS_SITE_BASE_URL` sigue siendo la
  variable que manda; no se hardcodea el dominio en ningún sitio del servidor. Y el nombre del
  bucket llega al proxy por entorno (`CORPUS_BUCKET`), no escrito a mano: el mismo mecanismo
  tiene que servir a otra organización con otro bucket.

**Lo que queda FUERA a propósito**, con su motivo:

- **Hacer el dominio y el sitio de corpus configurables por organización.** Hoy es *un
  despliegue, un dominio, un sitio*: `CORPUS_SITE_BASE_URL` es una variable de entorno global
  leída en `citations.py` con `os.getenv`, y `HubOrganizacion` tiene veinte campos de
  configuración por defecto pero **ninguno para su dominio ni para su sitio**. Una segunda
  organización con su propio buscador publicado necesitaría eso. **No es urgente y se dijo así al
  usuario**: sería una columna anulable con la cascada que ya existe y `citations.py` leyéndola
  con el entorno como reserva, así que hacerlo hoy o en seis meses cuesta lo mismo. Lo que sí
  generaliza ya, y gratis, es el mecanismo de `sites.d` de D.8: añadir el dominio de otra
  organización es un fichero y dos secretos.
- **Retirar el nombre provisional.** Se decide en DOM.5 con las páginas ya republicadas, no antes.
- **Mover el panel a un `admin.…` con su propio certificado.** Es la alternativa a un prefijo, y
  cuesta un certificado más que renovar a mano cada año y medio. Si algún día el panel quiere
  nombre propio, ese es el camino; hoy no lo pide nadie.

---

### Prompt DOM.1 (RED/GREEN) — Caddy: un solo reparto para los dos nombres

**Modelo sugerido**: **Sonnet** — alcance cerrado; el mecanismo de sitios por dominio lo construyó
D.8 y aquí se le cambia el reparto a un fragmento que ya existe.

**Objetivo**: que `(govgenai_rutas)` sirva la portada del corpus en la raíz, el panel bajo
`/panel/`, y la API donde estaba; y que los dos nombres —el provisional y el institucional— lo
sirvan idéntico.

**Contexto**: hoy el fragmento manda todo lo que no es `/api/*` ni `/health` al panel, y la
plantilla del dominio lo importa: por eso `normativa.uji.es/` enseña el login. El cambio es del
fragmento, no de la plantilla, que sigue importándolo sin tocarse.

**Instrucciones al agente**:
```markdown
# PROMPT DOM.1 (RED/GREEN) — el reparto público en Caddy

## Caddyfile
- `(govgenai_rutas)` pasa a repartir: `/api/*` y `/health` a `app:8000`; `/panel` y
  `/panel/*` a `frontend:80` **sin despojar el prefijo**; todo lo demás, al bucket.
- El proxy al bucket va con la forma **virtual-hosted** y reescribiendo la cabecera Host:
  `reverse_proxy https://{$CORPUS_BUCKET}.storage.googleapis.com { header_up Host {upstream_hostport} }`.
  Sin reescribir Host, GCS no resuelve el bucket y responde 404 a todo.
- `rewrite / /index.html` **explícito**: la raíz del bucket devuelve el listado XML de todos
  sus objetos (medido: 200 y `ListBucketResult`), porque el mapeo a `index.html` es
  configuración de sitio web y eso necesita balanceador.
- `redir /cercador /cercador.html permanent` y `redir /gerencia /cercador_gerencia.html
  permanent`: son las dos direcciones que la gente escribe y comparte, y así hay una sola
  página canónica en vez de dos copias.
- El nombre del bucket llega por entorno (`CORPUS_BUCKET`), no escrito a mano.

## compose y despliegue
- `CORPUS_BUCKET` en el `environment` del servicio `caddy` de `docker-compose.vm.yml`, con la
  forma `${CORPUS_BUCKET:?falta CORPUS_BUCKET}`: sin ella Caddy compondría
  `https://.storage.googleapis.com` y todo el sitio daría error sin decir por qué.
- La línea correspondiente en el heredoc de `.env.despliegue` de `deploy.yml`, desde
  `vars.CORPUS_BUCKET`.

## Tests (RED primero), en server/tests/infra/
- El fragmento NO manda `/` al frontend, y el panel está bajo un prefijo.
- La raíz se reescribe a `index.html` (el test que impide publicar el inventario del bucket).
- El proxy al bucket reescribe Host, y el nombre del bucket viene de una variable.
- La plantilla del dominio sigue importando el fragmento, y el bloque del host provisional
  también: si esto se rompe, uno de los dos nombres deja de servir y no lo nota nadie.
- `caddy validate` sobre la configuración compuesta, con la plantilla sustituida y un
  certificado de prueba: es la comprobación que impide desplegar un Caddy que no arranca.
- `CORPUS_BUCKET` llega hasta el contenedor: compose y workflow, no sólo el Caddyfile.
```

**Verificación de cierre**: `server/tests/infra` completo, y `caddy validate` en local.

---

### Prompt DOM.2 (RED/GREEN) — El panel bajo `/panel/`, sin literales en el código

**Modelo sugerido**: **Opus** — es la parte con riesgo del bloque y toca tres capas a la vez
(compilación, router y nginx); el plan original la evitó por eso.

**Objetivo**: que la imagen del frontend sirva el panel en `/panel/` —también abierta directa, sin
proxy— y que el código no contenga el prefijo.

**Contexto**: `frontend/vite.config.ts` no tiene `base` y el `BrowserRouter` de `App.tsx` no tiene
`basename`. Con `base` puesto, Vite emite `/panel/assets/…` en el HTML y expone el valor en
`import.meta.env.BASE_URL`, que es de donde lo toma el router: así el mismo código sirve en la
raíz (desarrollo y tests) y bajo prefijo (la imagen).

**Instrucciones al agente**:
```markdown
# PROMPT DOM.2 (RED/GREEN) — el panel bajo su prefijo

- `vite.config.ts`: `base` desde `VITE_BASE_PATH` con `/` por defecto. El defecto es la raíz
  para no invalidar `arranque.bat`, `.env.example` y la docena de guiones de pruebas
  manuales que dicen `localhost:5173`.
- `App.tsx`: `<BrowserRouter basename={import.meta.env.BASE_URL}>`. Ni un literal.
- `frontend/Dockerfile`: `ARG VITE_BASE_PATH="/panel/"`, porque la imagen ES producción, y
  el `dist` se copia a `/usr/share/nginx/html/panel`.
- `frontend/nginx.conf`: `location /panel/ { try_files $uri /panel/index.html; }`,
  `location = /panel { return 301 /panel/; }` y la raíz redirigiendo a `/panel/`. El
  `try_files` tiene que caer en `/panel/index.html`: con el de la raíz, cualquier
  `/panel/assets/x.js` que no exista devolvería HTML con tipo de contenido de JavaScript.
- `/healthz` se queda donde está: lo usa el `HEALTHCHECK` de la imagen.

## Tests (RED primero)
- Frontend (vitest): el router toma su base de `BASE_URL` y no de un literal.
- `server/tests/infra/`: el prefijo del `ARG` del Dockerfile, el de `nginx.conf` y el del
  Caddyfile son **el mismo**. Son tres ficheros y una sola verdad; divergen en silencio y el
  síntoma es una pantalla en blanco con 404 en la consola.
- `server/tests/infra/`: nginx sirve el panel desde su subdirectorio y su `try_files` cae en
  el `index.html` de dentro.
- Que no haya quedado ninguna navegación absoluta en el frontend: `LoginPage.tsx` va a la
  API, y eso es correcto porque la API no está bajo el prefijo.

## Documentación
- `SAML_FRONTEND_RETURN_URL` pasa a `https://normativa.uji.es/panel/auth/callback` allí donde
  esté escrita (`.env.example`, `scripts/generate_env.sh`, la documentación del SSO). El SSO
  institucional no está configurado todavía, así que esto es dejarlo correcto para cuando lo
  esté, no un cambio en caliente.
```

**Verificación de cierre**: `npm run build` y comprobar en el `dist` que el HTML referencia
`/panel/assets/…`; suite de vitest de las pantallas tocadas; `server/tests/infra` completo.

---

### Prompt DOM.3 (RED/GREEN) — Las citas y los orígenes apuntan al dominio

**Modelo sugerido**: **Sonnet**.

**Objetivo**: `CORPUS_SITE_BASE_URL=https://normativa.uji.es`, el origen del dominio en CORS, y
las citas del asistente verificadas resolviendo de verdad.

**Contexto**: `citations.py:89` construye `{CORPUS_SITE_BASE_URL}/html/{slug}.html` más el ancla.
La configuración del despliegue **no vive en ningún fichero del repositorio**: la escribe
`deploy.yml` desde las variables del repositorio de GitHub (`vars.CORPUS_SITE_BASE_URL`,
`vars.CORS_ALLOWED_ORIGINS`), así que cambiarla es `gh variable set`, no una edición. Lo que hay
que comprobar es que las URL resultantes existen: un cambio de base con las páginas en otro sitio
produce 404 en cada cita sin que ningún test lo vea.

**Instrucciones al agente**:
```markdown
# PROMPT DOM.3 (RED/GREEN) — la base de las citas

- `gh variable set CORPUS_BUCKET`, `CORPUS_SITE_BASE_URL` al dominio y `CORS_ALLOWED_ORIGINS`
  **aditivo** (el origen del bucket se conserva mientras su URL siga siendo pública). Los
  valores anteriores, anotados en el informe: son el camino de vuelta.
- Test de contrato: que `citations.py` sigue leyendo la base del entorno y no de un literal, y
  que la forma de la URL de una norma no ha cambiado.
- Después del despliegue de DOM.5, TRES consultas reales que se sepa que citan (contractes
  menors, bases d'execució, una de Gerència) y comprobar con `curl` que **cada URL citada
  devuelve 200 y su ancla existe dentro del HTML**. No vale comprobar que la base cambió: hay
  que abrir lo que cita.
```

**Verificación de cierre**: las tres consultas con sus URL y códigos pegados en el informe.

---

### Prompt DOM.4 — La portada, y republicar el sitio apuntando al dominio

**Modelo sugerido**: **Sonnet**.

**Objetivo**: una raíz que presente el proyecto y lleve a los dos cercadores, y las 313 páginas
regeneradas con `ASSISTENT_API` en el dominio nuevo.

**Contexto**: la portada y las páginas las produce el pipeline de curación, **fuera de este
repositorio** (`Descarregar_pdf/normativa_propia/publicacio_transparencia_2026-07/`), y la
frontera es `docs/CONTRATO_MD_CORPUS.md`: aquí no se cambia ni el formato ni el contenido del
paquete, se publica. Las páginas publicadas llevan `data-api-url=https://<provisional>/api/v1`; se
cambia al dominio **sin quitar el atributo** (regla dura del bloque) y **conservando la credencial
de sitio**, que sigue siendo necesaria. Las credenciales vigentes son las dos del bucket emitidas
en D.6.1; se reutilizan leyéndolas del HTML actual, porque en claro no se pueden recuperar de la
base.

**Instrucciones al agente**:
```markdown
# PROMPT DOM.4 — la portada y la republicación

- La portada (`index.html` del paquete) gana: la presentación del proyecto en dos párrafos, la
  tarjeta del cercador de Gerència junto a la de normativa, y el acceso al panel —discreto,
  al pie: es para quien administra, no para quien consulta—. Lo genera el programa del
  pipeline, no se edita el HTML a mano: un HTML editado a mano se pierde en la regeneración
  siguiente.
- Regenerar con `ASSISTENT_API=https://normativa.uji.es/api/v1`, cada cercador con SU
  chatbot, SU credencial (leída del HTML publicado) y SU `data-title`. Las fichas siguen sin
  widget.
- Comprobar antes de publicar que ninguna página suelta lleva un chatbot que no le toca, y
  que las 313 fichas siguen con cero widgets.
- Publicar con `scripts/publica_sitio_corpus.sh --con-widget`.
- Comprobar el preflight desde el origen del dominio Y desde el del bucket, con un origen
  inventado como control: sin control, un 200 no dice nada.
```

**Verificación de cierre**: la portada abierta en el navegador con los dos cercadores
alcanzables, y el asistente respondiendo desde `https://normativa.uji.es/cercador` y desde la URL
del bucket, con la consola limpia en los dos casos.

---

### Prompt DOM.5 (verificación + decisión) — Desplegar, verificar y qué se hace con el provisional

**Modelo sugerido**: **Sonnet**.

**Objetivo**: recorrido completo verificado en navegador contra el dominio real, y decidir con
datos si el nombre provisional se retira o se conserva.

**Instrucciones al agente**:
```markdown
# PROMPT DOM.5 — despliegue, verificación y cierre

## El recorrido, en el dominio nuevo
1. La raíz enseña la portada —no el login— y sus dos tarjetas llevan a los dos cercadores.
2. El cercador carga, filtra y sus resultados abren en pestaña nueva.
3. El asistente de normativa responde, con la cabecera diciendo su nombre.
4. Una cita abre la ficha en el ancla correcta, servida por el dominio.
5. El cercador de gerencia, con SU asistente.
6. `https://normativa.uji.es/panel/` da el login, entra, y el panel navega —incluida una
   recarga en una ruta profunda, que es lo que rompe un `basename` mal puesto.
7. El panel sigue funcionando también en el nombre provisional, bajo el mismo prefijo.
8. `read_console_messages` y `read_network_requests` en cada paso.

## La decisión sobre el provisional
- NO se retira en este prompt. Se deja escrito qué sigue apuntando a él —la comprobación de
  salud de la vigilancia, el paso de verificación de `deploy.yml`, y cualquier página o correo
  ya enviado— y se recomienda un plazo. Retirarlo el mismo día que se estrena el dominio no
  gana nada y puede romper algo que nadie recordaba.
- Actualizar la comprobación de uptime y la alerta si se decide mover el objetivo.
```

**Verificación de cierre**: informe con las evidencias, y `docs/DESPLIEGUE_PROTOTIPO_GCP.md`
actualizado con el reparto final de nombres y rutas.

---

**Al cerrar el bloque**: suite completa (`uv run pytest tests` desde Git Bash), y las URL nuevas
recogidas donde alguien las busque: `PROJECT_STATE.md`, `docs/WIDGET_INCRUSTACION.md` (el
fragmento de ejemplo) y `docs/RUNBOOK_REINGESTA.md` si menciona la base del sitio.

---

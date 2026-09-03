## Bloque DIN — Secciones parametrizables y ciclo de vida de la ingesta automática (PENDIENTE, planificado el 2026-08-31)

> **Posición en orden de ejecución**: independiente del Deploy (todo es edge y ya corre en
> local). No depende de que se decida ningún apartado concreto: los apartados los crea quien
> cura, cuando los necesita.

**Origen**: reunión con desarrollo del 2026-08-31 («las secciones que se actualizan de forma
permanente, como jornadas o eventos, deberían alimentar el chatbot en cada actualización sin
curación manual»), y la corrección posterior del usuario: **los apartados se han de poder
parametrizar como bloques o secciones dentro de un proceso de curación, no quedar fijados**.
Valoración completa en `docs/EVOLUCIO_I_ASPECTES_PENDENTS.md` (valoración 3).

**Lo que la revisión del código encontró ya hecho** —con tests y corriendo en el APScheduler que
arranca con la aplicación— es dos tercios de lo que la reunión pedía: el rastreo periódico con
`url_regex_filter` y cadencia (RAS.5), la **auto-ingesta de páginas nuevas** que casan una regla
de selección con `auto_ingest_new=True` (9Q.7, `quality_job.py` paso 4) y la **reingesta
automática de lo que cambió** donde ya estaba ingerido (RAS.5, paso 3.bis, con aviso
`content_updated`). Este bloque hace dos cosas: convertir el apartado en **dato configurable** y
cerrar el **ciclo de vida** que falta (retirada, puerta de calidad, diario).

### Por qué la sección tiene que ser dato

Hoy un apartado se expresa **creando un `HubWebSite` entero** con su `url_regex_filter`. Es la
decisión de RAS.5 y tenía una buena razón —cada apartado tiene un responsable distinto—, pero
paga un precio que se nota justo cuando los apartados se multiplican: duplica `root_url`,
sitemap, cortesía y criterios de juicio; obliga a un alta técnica por apartado; y hace que
«añadir un apartado» sea trabajo de quien tiene acceso a la administración de sitios en vez de
trabajo de quien cura.

Es el mismo razonamiento que el proyecto ya aplicó al vocabulario del corpus (CLAUDE.md §5): lo
que va a cambiar mientras alguien lo usa **es dato, no estructura**. Fijar `/jornadas` y
`/eventos` en el plan —o peor, en el código— convierte «añadir el apartado de becas» en un
prompt de desarrollo. Con secciones parametrizables es un formulario.

**El principio que se conserva**: *curación una vez, automatización después*. La decisión del
2026-08-02 («una página nueva es señal para el curador, no disparador»,
`docs/DECISION_CURACION_SEPARADA.md`) sigue vigente; lo que la matiza es que **la sección y su
modo los define un curador** tras la primera pasada manual sobre ese apartado, y dentro del
ámbito de esa sección la automatización mantiene. No hay ingesta automática de nada que ningún
humano haya aprobado nunca; hay mantenimiento automático de lo que un humano aprobó una vez. (Es
la distinción que RAS.5 ya dejó escrita para la reingesta: «actualizar lo que alguien aprobó una
vez no es publicar lo que nadie ha aprobado».)

### La trampa que este bloque tiene que evitar, y que hoy no existe

`site_crawler.py:232` declara las bajas así: `gone_ids = [p.id for p in existing_pages if p.url
not in seen_urls]`, protegido por `if not summary.truncated` («una página no visitada no es una
página desaparecida»). Hoy es correcto porque **el sitio *es* el apartado**: lo rastreado y lo
existente son el mismo conjunto.

En cuanto un sitio tenga varias secciones con cadencias distintas, eso se rompe: una pasada de
`/eventos` que termine completa vería `seen_urls` sólo con las de `/eventos` y `existing_pages`
con **todo el sitio** — y declararía baja el resto del portal. Con la retirada automática de
DIN.4 encima, eso vacía corpus.

Es literalmente la lección que `ingestion/corpus/source.py` ya tiene escrita para el corpus
normativo: «solo con un censo se puede detectar una retirada, porque solo entonces "ausente"
significa algo. Una carga parcial que se interpretara como censo retiraría cientos de normas».
**El censo se acota al ámbito realmente rastreado**, y esa es la regla dura nº 1 del bloque.

**Reglas duras del bloque DIN**:
- **El censo se acota al ámbito rastreado.** Una pasada de sección compara contra las páginas de
  esa sección, nunca contra las del sitio entero. Un ámbito no rastreado no declara bajas.
- **Nada entra al corpus con hallazgos bloqueantes.** La automatización no puede tener menos
  criterio que el curador al que sustituye en el camino feliz.
- **Ninguna retirada masiva silenciosa.** Salvaguarda de proporción, como la del reconciliador
  del corpus normativo: un rastreo malo no puede vaciar un corpus.
- **Nulo hereda.** Todo parámetro de sección admite nulo y entonces vale el del sitio — la misma
  semántica que `core/ambito.py` da a `heredable`. Un sitio **sin secciones** se comporta
  exactamente como hoy (ámbito implícito = el sitio entero); no es un *shim*, es la herencia.
- **La pertenencia de una página a una sección se deriva del patrón, no se almacena.** Los
  patrones se editan, y una columna `section_id` en `hub_crawled_pages` exigiría reescribirla en
  cada edición.
- **Todo lo que la automatización hace queda escrito** donde el curador trabaja, no sólo en el
  summary del job.
- El corpus normativo queda **fuera**: sus fuentes son `load.py`/`sync.py` con su puerta de
  validación. Este bloque toca sólo el camino web (crawler → selección → chatbot).

---

### Prompt DIN.1 (RED/GREEN) — La sección como dato, y qué parámetro gana cuando hay dos

**Modelo sugerido**: **Opus** — decide el modelo de datos y la semántica de herencia que
consumen los seis prompts siguientes; equivocarse aquí se paga en todos.

**Objetivo**: crear `HubWebSection` (bloque o sección dentro de un sitio) con sus parámetros de
curación, y la resolución de **parámetros efectivos** sitio→sección como función pura y probada.

**Contexto**: `HubWebSite` vive en `operational_models.py` (`HubOperationalBase`) y sus campos
son en inglés (`root_url`, `crawl_interval_hours`, `config_json`); la sección sigue esa
nomenclatura para leerse como su vecina. La sección llega a su organización **a través del
sitio**, y eso hay que anotarlo en `docs/MULTITENENCIA.md` (su test lo exige). `mode` sí lleva
`CheckConstraint`: son dos valores estables con consumidor en el código, como `nivell_acces`.
Los criterios de juicio (`criteria_json`) **no** lo llevan: son vocabulario que crecerá, igual
que los de sitio de CUR.2.1.

**Instrucciones al agente**:
```markdown
# PROMPT DIN.1 (RED/GREEN) — HubWebSection + resolución de parámetros efectivos

## Modelo (operational_models.py, junto a HubWebSite)
- HubWebSection, __tablename__="hub_web_sections":
  - id UUID pk; site_id FK hub_web_sites.id ondelete CASCADE, index
  - name str(255)              — el nombre que le da quien cura ("Jornadas", "Eventos")
  - pattern str(2048)          — lo que delimita la sección
  - pattern_kind str(20)       — 'path_prefix' | 'regex', CheckConstraint
  - crawl_interval_hours int NULL   — NULL = hereda del sitio
  - mode str(20)               — 'manual' | 'automatic', CheckConstraint, default 'manual'
  - criteria_json JSONB NULL   — overrides de criterios de juicio; NULL = hereda del sitio
  - owner str(255) NULL        — responsable del apartado (la razón original de RAS.5 para
                                 partir por sitios; aquí es un campo, no una tabla nueva)
  - last_crawled_at timestamptz NULL   — la sección tiene su propio reloj
  - is_active bool default True
  - created_at timestamptz
- UniqueConstraint(site_id, name): dos secciones homónimas en un sitio son un error de alta.
- El defecto de `mode` es 'manual' A PROPÓSITO, al contrario que `auto_ingest_new` (que nació
  con default True): una sección nueva no automatiza hasta que alguien lo dice.

## Resolución de parámetros efectivos (módulo propio, función pura)
- parametros_efectivos(site, section | None) -> dataclass con intervalo, criterios y patrón
  ya resueltos. Reglas: NULL en la sección hereda del sitio; sin sección, el ámbito es el
  sitio entero (comportamiento de hoy). Sin sesión de BD: entra dato, sale dato.
- Los criterios se fusionan CLAVE A CLAVE (un override de `stale_days` no debe borrar el
  umbral de retirada que sólo está en el sitio).

## Pertenencia de una página a una sección
- casa(section, url) -> bool, con las dos clases de patrón. Reutilizar el mecanismo que ya
  usa el repo de selecciones (`matches`) en vez de escribir un segundo comparador; si no
  encaja, decir por qué en el PR.
- Un `regex` que no compila se rechaza AL GUARDAR (la lección de CrawlConfig en RAS.5: un
  patrón inválido rompería todos los rastreos y el fallo saldría lejos del formulario).

## Migración
- Alembic autogenerate + revisión; aplicar con uv run alembic upgrade <rev>.
- Sin datos que migrar: los sitios-apartado existentes siguen sin secciones y por tanto
  siguen comportándose igual.

## Tests (mínimo 9) — tests/modules/curation/unit/test_din1_secciones.py
- Nulo hereda: intervalo y criterios de la sección vacíos -> valen los del sitio.
- El valor de la sección gana cuando está puesto.
- Fusión clave a clave de criterios (el caso que un `dict | dict` mal hecho rompe).
- Sin sección -> ámbito del sitio entero, parámetros del sitio.
- casa() con path_prefix y con regex, incluidos los que NO casan.
- Un regex inválido se rechaza al guardar, con mensaje que dice qué patrón y por qué.
- UniqueConstraint(site_id, name) impide la homónima; el mismo nombre en OTRO sitio sí vale.
- El defecto de mode es 'manual'.
```

**Verificación**: suite de `tests/modules/curation` + `tests/infra/test_suite_hygiene.py`
verdes; `alembic current` con la revisión; `docs/MULTITENENCIA.md` actualizado con la tabla
nueva y su camino a la organización.

---

### Prompt DIN.2 (RED/GREEN) — Rastrear por sección sin que el censo se lleve el resto del sitio

**Modelo sugerido**: **Opus** — toca la detección de bajas y el reloj del scheduler, que es
donde vive la trampa del bloque; un error aquí retira corpus en silencio.

**Objetivo**: que el rastreo y el scheduler operen por sección —cada una con su cadencia y su
`last_crawled_at`— y que la declaración de bajas se acote al ámbito realmente rastreado.

**Contexto**: hoy `_get_due_sites` (`quality_scheduler.py`) selecciona sitios cuyo
`crawl_interval_hours` venció, y `site_crawler.py:232` compara `seen_urls` contra **todas** las
páginas del sitio. Las dos cosas cambian, y la segunda es la delicada: ver la trampa descrita en
la cabecera del bloque. El presupuesto (`max_pages`, `max_seconds`) y la cola persistida de
RAS.3 siguen valiendo; `truncated` sigue impidiendo bajas, ahora por ámbito.

**Instrucciones al agente**:
```markdown
# PROMPT DIN.2 (RED/GREEN) — Ámbito de rastreo por sección y censo acotado

## Elegibilidad (quality_scheduler.py)
- Vencen SECCIONES activas por su intervalo efectivo (DIN.1) y su propio last_crawled_at;
  un sitio sin secciones sigue venciendo como sitio (comportamiento de hoy).
- Una sección nunca rastreada (last_crawled_at NULL) vence, igual que un sitio nuevo.

## Rastreo acotado (site_crawler.py)
- El crawl recibe el ámbito: el patrón de la sección se APLICA ADEMÁS del url_regex_filter
  del sitio, no en su lugar (el filtro del sitio es la valla del dominio; el de la sección,
  el apartado dentro).
- **El censo se acota**: `existing_pages` para el diff de bajas son las páginas del sitio
  que CASAN el ámbito rastreado. Fuera del ámbito no se declara nada — ni baja ni cambio.
- `truncated` sigue vetando las bajas del ámbito rastreado.
- Al cerrar, se sella `section.last_crawled_at` (y el del sitio sólo si el ámbito era el
  sitio entero: si no, `last_crawled_at` del sitio mentiría diciendo que se vio todo).
- El summary declara qué ámbito cubrió la pasada (id de sección o "sitio"), porque el job y
  el diario de DIN.6 tienen que poder decirlo.

## Tests (mínimo 10) — tests/modules/curation/unit/test_din2_ambito_de_rastreo.py
- **El test que justifica el prompt**: sitio con dos secciones, pasada completa de una;
  las páginas de la OTRA no se marcan gone. (Sin la acotación, este test es rojo y el
  portal entero se declara baja.)
- Dentro del ámbito, una página que ya no aparece SÍ se marca gone.
- Pasada truncada -> cero bajas incluso dentro del ámbito.
- Sección vencida por su intervalo propio; no vencida por el heredado del sitio.
- Sección nunca rastreada vence.
- Sección inactiva no vence.
- last_crawled_at de la sección se sella; el del sitio NO, si el ámbito era parcial.
- Ámbito = sitio entero -> comportamiento idéntico al de hoy (el test de no-regresión).
- El patrón de sección se compone con el url_regex_filter del sitio (una URL que casa la
  sección pero no la valla del sitio no se rastrea).
- El summary dice qué ámbito cubrió.
```

**Verificación**: suite de `tests/modules/curation` + higiene verdes. Comprobar a mano el
camino de no-regresión: un sitio existente sin secciones produce el mismo diff que antes del
prompt (mismo recuento de nuevas/cambiadas/bajas sobre datos sembrados).

---

### Prompt DIN.3 (RED/GREEN) — Parametrizar secciones dentro del proceso de curación

**Modelo sugerido**: **Sonnet** — CRUD y pantalla sobre contratos ya cerrados en DIN.1.

**Objetivo**: que quien cura pueda crear, editar, activar y desactivar secciones de un sitio
desde la interfaz de curación, con **prueba del patrón antes de guardar**, y enlazarlas al
chatbot destino.

**Contexto**: `hub_sites_router` ya sirve la administración de sitios y selecciones, y
`HubCorpusSelection` ya expresa chatbot↔sitio con `rule_type`/`rule_value`. La selección gana
`section_id` (nullable) para apuntar a una sección en vez de repetir su patrón: dos sitios de
verdad de la regla —el patrón de la sección y el `rule_value`— divergirían. Con `section_id`
puesto, el patrón lo manda la sección.

**Instrucciones al agente**:
```markdown
# PROMPT DIN.3 (RED/GREEN) — API + UI de secciones

## Backend (hub_sites_router.py, Deploy: edge)
- CRUD de secciones de un sitio: listar, crear, editar, activar/desactivar. Borrado sólo
  si no tiene selecciones colgando; si las tiene, se desactiva (y el mensaje lo explica).
- HubCorpusSelection gana section_id UUID NULL FK: cuando está puesto, el patrón efectivo
  es el de la sección y `rule_value` se ignora (documentarlo en el modelo).
- POST de PRUEBA del patrón: devuelve cuántas páginas YA RASTREADAS del sitio casarían y
  una muestra de 10 URL. Es lo que evita el regex que no casa nada, que hoy sólo se
  descubre cuando la pasada siguiente no ingiere nada.
- Acotación por organización de siempre (tenancy vía el sitio).

## Frontend (pestaña de curación del sitio)
- Lista de secciones con nombre, patrón, modo, cadencia efectiva (diciendo cuándo es
  heredada), responsable y última pasada.
- Formulario con react-hook-form + zodResolver; el botón «Probar patrón» muestra el
  recuento y la muestra antes de dejar guardar.
- i18n es/ca/en, hooks Orval, cero strings hardcodeados.

## Tests (mínimo 9: 6 backend + 3 frontend)
- Crear/editar/desactivar; borrado bloqueado con selecciones y mensaje explicativo.
- Patrón inválido -> 422 con el motivo (la validación de DIN.1, ahora por HTTP).
- La prueba del patrón cuenta y muestra sin escribir nada.
- Dos organizaciones: cada una ve las secciones de sus sitios.
- Selección con section_id -> el patrón efectivo es el de la sección.
- Frontend: la lista se construye de la respuesta del hook; la cadencia heredada se
  distingue de la propia; «Probar patrón» pinta recuento y muestra.
```

**Verificación**: backend + vitest (`--no-file-parallelism`) verdes; contrato regenerado
(`openapi.json` + Orval); verificación en navegador: crear una sección, probar el patrón contra
un sitio sembrado, guardarla y verla en la lista, con consola y red limpias.

---

### Prompt DIN.4 (RED/GREEN) — La retirada automática de lo que desapareció, con salvaguarda

**Modelo sugerido**: **Sonnet** — el mecanismo (`retire_page`) y la señal (`gone_page_ids`)
existen, y DIN.2 ya garantizó que la señal significa lo que dice.

**Objetivo**: retirar del corpus los documentos de las páginas desaparecidas, sólo en el ámbito
de secciones en modo `automatic`, con salvaguarda de proporción y rastro.

**Contexto**: hoy `mark_gone` marca la página y ahí muere; `retire_page`
(`selection_service.py:109`) sólo lo llama el endpoint manual, así que un evento borrado del
portal sigue en el corpus respondiendo como si existiera — para un apartado de eventos es el
fallo dominante. La salvaguarda protege del rastreo que salió mal de una forma que `truncated`
no capta (portal que responde 200 con una plantilla vacía, redirección masiva).

**Instrucciones al agente**:
```markdown
# PROMPT DIN.4 (RED/GREEN) — Auto-retirada de páginas gone, acotada y con salvaguarda

## En quality_job.py (paso nuevo, tras la auto-ingesta)
- Para cada página de gone_page_ids: si su sección está en mode='automatic' y hay
  selección al chatbot -> retire_page(chatbot_id, page_id). Contador
  summary.documents_auto_retired.
- Sección en mode='manual' (o sitio sin secciones) -> NO retira: hallazgo `page_gone`
  para el curador, con la identidad estándar de hallazgos (la reconciliación de CUR.9 lo
  retira sola si la página reaparece).

## Salvaguarda de proporción
- Si las bajas de esta pasada superan el umbral (defecto 30%) de las páginas activas
  **del ámbito rastreado** —no del sitio, que con secciones sería otra cifra—, no se
  retira nada: hallazgo `retirada_masiva_detenida` con el recuento y a la cola del
  curador. El umbral es un criterio de juicio más, y por tanto heredable sitio→sección
  (DIN.1).

## Tests (mínimo 8) — tests/modules/curation/unit/test_din4_auto_retirada.py
- gone en sección automática con selección -> retire_page llamado, contador sube.
- gone en sección manual -> NO retira, hallazgo page_gone.
- gone sin documentos ingeridos -> no llama a retire_page.
- 30%+ del ÁMBITO -> cero retiradas, hallazgo retirada_masiva_detenida.
- 29% -> sí retira (el camino bueno de la salvaguarda, no sólo el disparo).
- El umbral heredado del sitio y el sobrescrito en la sección, los dos.
- La proporción se calcula sobre el ámbito, no sobre el sitio (dos secciones sembradas).
- Un fallo en retire_page de una página no aborta el resto y queda en summary.errors.
```

**Verificación**: suite de `tests/modules/curation` + higiene verdes.

---

### Prompt DIN.5 (RED/GREEN) — La puerta de calidad delante de la ingesta automática

**Modelo sugerido**: **Sonnet** — los hallazgos ya se calculan en el mismo job dos pasos antes;
el prompt consulta lo que ya está en memoria.

**Objetivo**: que ni la auto-ingesta de páginas nuevas ni la reingesta de las cambiadas metan al
corpus una página con hallazgos bloqueantes; la página queda como candidata con el motivo
visible.

**Contexto**: hoy el paso 4 ingiere cualquier página nueva que case la regla sin mirar los
hallazgos que el propio job acaba de calcular — una página vacía, ilegible o `needs_javascript`
(el sondeo de RAS.2 existe justo para detectarlas) entraría al corpus. La automatización no
puede tener menos criterio que el curador al que sustituye.

**Instrucciones al agente**:
```markdown
# PROMPT DIN.5 (RED/GREEN) — Hallazgos bloqueantes detienen auto-ingesta y reingesta

## Tipos bloqueantes
- Defecto: los hallazgos de legibilidad (vacía, ilegible, needs_javascript, contenido
  cortado). Nombrarlos por los finding_type REALES de los detectores existentes —leerlos
  del código, no inventarlos.
- Es un criterio de juicio más: heredable sitio→sección (DIN.1), así que un apartado puede
  ser más exigente que su portal.

## En quality_job.py
- Paso 4 (nuevas) y paso 3.bis (cambiadas): antes de process_source, consultar los
  hallazgos abiertos de la página en esta pasada; si alguno es bloqueante -> no ingerir,
  contador summary.pages_blocked_by_findings y hallazgo `auto_ingesta_detenida` con el
  motivo, para que el curador vea POR QUÉ no entró.
- La página bloqueada sigue siendo candidata: resuelto el hallazgo, la siguiente pasada la
  ingiere sola, sin acción extra.

## Tests (mínimo 7) — tests/modules/curation/unit/test_din5_puerta_de_calidad.py
- Página nueva que casa + hallazgo bloqueante -> NO se ingiere, contador y hallazgo.
- Página cambiada ya ingerida + hallazgo bloqueante -> NO se reingiere (la versión buena
  del corpus se conserva: peor es reemplazar texto bueno por vacío).
- Hallazgos NO bloqueantes (p. ej. stale) -> se ingiere igual.
- Hallazgo resuelto -> la siguiente pasada la ingiere.
- Tipos bloqueantes heredados del sitio y sobrescritos en la sección, los dos.
- El camino bueno: página limpia -> ingerida (que la puerta no se cierre de más).
- Los finding_type usados existen en los detectores (test que los cruza con el registro
  de tipos, para que un renombrado no deje la puerta abierta en silencio).
```

**Verificación**: suite de `tests/modules/curation` + higiene verdes; `grep` de que los
`finding_type` del defecto existen en los detectores.

---

### Prompt DIN.6 (RED/GREEN) — El diario de la automatización, donde trabaja el curador

**Modelo sugerido**: **Sonnet** — persistir un resumen que ya se calcula y mostrarlo.

**Objetivo**: que cada pasada deje rastro consultable —ámbito, qué ingirió, reingirió, retiró y
bloqueó, y por qué— y que la pantalla de curación lo muestre por sitio y por sección.

**Contexto**: el `summary` del job (con los contadores que DIN.4 y DIN.5 añaden) hoy se devuelve
y se pierde. La confianza en una automatización se construye pudiendo auditarla barata: si el
curador no ve lo que hizo, la apagará al primer susto — y tendrá razón.

**Instrucciones al agente**:
```markdown
# PROMPT DIN.6 (RED/GREEN) — Diario por pasada

## Persistencia
- Resumen por pasada: sitio, **sección (o "sitio entero")**, timestamps, contadores
  (nuevas ingeridas, reingeridas, retiradas, bloqueadas, bajas, errores), stop_reason.
- Revisar si HubIngestionJob o el registro de jobs existente sirve ANTES de crear tabla
  nueva; crearla sólo si ninguno encaja, y decir por qué en el PR.
- Retención: últimas N pasadas por sección (N=50 por defecto); poda en el propio job, sin
  scheduler nuevo.

## API + UI
- GET paginado de pasadas de un sitio, filtrable por sección (Deploy: edge).
- En la pestaña de curación: tabla de pasadas con el detalle de errores y bloqueos
  desplegable, y el ámbito de cada una bien visible. i18n es/ca/en, hooks Orval.

## Tests (mínimo 7: 5 backend + 2 frontend)
- Una pasada persiste su resumen con los contadores y el ámbito correctos.
- La poda deja N por sección y no toca las de otras secciones ni otros sitios.
- El GET pagina, filtra por sección y acota por organización.
- Orden estable, con desempate determinista (la regla de DET.1 para listados).
- Frontend: la tabla se construye de la respuesta del hook; el ámbito se muestra.
```

**Verificación**: backend + vitest verdes; verificación en navegador (pasada real sobre un sitio
sembrado, el diario aparece con contadores y ámbito, consola y red limpias).

---

### Prompt DIN.7 (VERIFICACIÓN + docs) — Un apartado real, parametrizado por quien cura, de punta a punta

**Modelo sugerido**: **Sonnet** — ejecución y documentación sobre mecanismos ya probados.

**Objetivo**: parametrizar **desde la interfaz** una sección real sobre un apartado dinámico del
portal, verificar el ciclo completo (nueva que entra, cambiada que se reingiere, borrada que se
retira) y dejar la receta en `docs/SECCIONES_DINAMICAS.md`.

**Contexto**: qué apartado sea es indiferente para el código y **no se fija aquí**: el prompt
verifica el mecanismo con el que quien cura elija el día que lo ejecute. Las trampas del portal
real están inventariadas (conmutador de idioma, prefijos duplicados, fechas en `.clockBarDate`,
robots.txt que excluye rastreadores) y son la razón de que la primera pasada de un apartado sea
manual: calibra los criterios antes de que la automatización mantenga. La **caducidad
editorial** —el evento que ya ocurrió pero sigue publicado— no se implementa: es decisión del
propietario del contenido y se documenta con opciones.

**Instrucciones al agente**:
```markdown
# PROMPT DIN.7 (VERIFICACIÓN + docs) — Ciclo completo sobre una sección parametrizada

## Montaje, todo por la interfaz (nada de SQL a mano: si hace falta, la UI está incompleta)
- Sección nueva sobre un sitio ya rastreado, patrón probado con el botón de DIN.3,
  cadencia y responsable puestos, modo 'manual' primero.
- Primera pasada de curación revisada hallazgo a hallazgo. Después, modo 'automatic'.

## Ciclo verificado (evidencia en el informe de cierre)
- Nueva -> entra sola en la siguiente pasada (o bloqueada con motivo si tiene hallazgos).
- Cambiada -> se reingiere, con aviso content_updated.
- Desaparecida -> se retira, con rastro en el diario.
- **La comprobación que cierra la trampa del bloque**: una pasada de la sección deja
  intacto lo ingerido del resto del sitio (recuento antes y después).
- El diario cuenta la historia completa, con el ámbito de cada pasada.

## docs/SECCIONES_DINAMICAS.md
- La receta paso a paso para parametrizar el siguiente apartado (pantallas reales).
- El principio «curación una vez, automatización después» y por qué la primera pasada es
  manual.
- Las dos salvaguardas (hallazgos bloqueantes, retirada masiva detenida) y cómo se
  ajustan por sección.
- La decisión pendiente de caducidad editorial, con las opciones y a quién le toca.
```

**Verificación**: el ciclo completo observado de verdad (no simulado), con las salidas pegadas
en el informe de cierre; `docs/SECCIONES_DINAMICAS.md` existe y quien cura puede seguirla sin
preguntar. Suite completa (`uv run pytest tests` desde Git Bash) al cerrar el bloque.

---

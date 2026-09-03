# Bloque ACT — actualizar el corpus sin pagar dos veces, y hacer que idioma, emparejamiento y vigencia signifiquen lo que el corpus dice

> Se llama **ACT** (actualización del corpus) y no COR porque ya existe un «Bloque COR — Un
> documento, muchos chatbots», descartado el 2026-08-11, con sus propios COR.0–COR.6 más
> arriba en este fichero; dos bloques con los mismos identificadores serían una trampa.
>
> **Escrito el 2026-08-28**, a partir de una auditoría del código y de la configuración hecha
> con el corpus del 27-08-2026 (`publicacio_transparencia_2026-07`, 317 + 130 documentos) contra
> la base de datos de desarrollo, con `--dry-run`. **No se ha ingerido nada.** El usuario
> decidió esperar: el piloto no está abierto, el despliegue no está hecho, y «cada vez que
> miramos alguna cosa aparece algo que no está configurado como esperábamos». Este bloque
> existe para que la siguiente mirada no encuentre lo mismo.
>
> **Las decisiones de criterio de este bloque son de Secretaría General y del usuario**, y están
> recogidas —con sus opciones— en `docs/CONFIGURACION_APERTURA_PILOTO.html` §12. Los prompts que
> siguen implementan la opción recomendada; si la decisión cambia, cambia el parámetro, no el
> diseño.

## Lo que la auditoría encontró, en una tabla

| eje | lo que se creía | lo que hay | dónde |
|---|---|---|---|
| **Normas externas** | «decidimos excluirlas de Normativa» | La decisión vive **sólo en la columna** `us_assistents` de la BD; el corpus dice `si` en las dos carpetas y `assistents.json` declara `normatiu.tot: true` sobre `md_externes`. Cada reconciliación propone deshacerlo (24 `EXT-*`, 27.623 fragmentos ya embebidos) | `assistents.json`; `reconciler.py:_difiere` |
| **Idioma: filtro** | «si pregunta en castellano, busca en castellano» | La recuperación **no recibe la lengua**: `rag_vector_pipeline.py:91` llama `get_context` sin `language`. Ambas versiones compiten en el top-k | `rag_vector_pipeline.py:91` |
| **Idioma: `prefer`** | «prioriza la lengua del usuario» | Ordena, **no descarta** (`protocols.py:139`). Con `top_k=3` y `parent_child` caben las dos versiones → se citan las dos | `protocols.py:117-175` |
| **Idioma: `canonica`** | «es la versión de referencia» | Es un **filtro duro** (`metadata_filter.py:89`): `canonica=false` nunca se recupera. Son 33 castellanas hoy y **57 con este corpus** → preguntar en castellano por una norma bilingüe devuelve la valenciana. **Se retira (28-08)**: las dos versiones son oficiales y no hay jerarquía; de las 57 parejas **47 tienen URL distinta**, así que ni siquiera sostiene a VIS.3 | `metadata_filter.py:89` |
| **Idioma: códigos** | `ca` y `val` son lo mismo | `langdetect` dice `ca`, el corpus dice `val`; **nunca casan**. Ya se tropezó (`graph_factory.py:203`) y se resolvió *no usando* la lengua. `prefer` mete todo en «otra lengua» en las preguntas en valenciano, y `_NOMBRE_DE_LA_LENGUA` no tiene `val`: el aviso puede salir «está en val» | `graph_factory.py:203`, `hub_chat.py:177` |
| **Vigencia por curso** | «la del curso pasado no se recupera» | En la BD, DIR-003/004 están `no_vigent` (a mano). El corpus las pone `vigent` + `vigencia_curs: substituida`, y **`vigencia_curs` no existe en el repo** (0 coincidencias) → **al ingerir, las directrices de dos cursos vuelven a competir**. **Resuelto por criterio el 28-08 (lectura A)**: la del curso pasado es `no_vigent` con causa temporal; `vigencia_curs` sobra y se retira del corpus | `manifest.py`, `metadata_filter.py` |
| **Vigencia: `no_vigent`** | — | Sólo `derogat` exacto se excluye. `no_vigent` (INS-019 y 2 más) **se recupera con aviso**. **Decidido el 28-08**: `no_vigent` es el estado y `derogat` una de sus causas (`motiu_no_vigencia`, vocabulario como dato); sólo `vigent` se recupera | `metadata_filter.py:95` |
| **Vigencia: `suprimit`** | «el artículo suprimido no se cita como vigente» | El troceador guarda `estat=suprimit` en el chunk y **nadie lo consume** (lo dice `vigencia.py:110`). Son 3 fragmentos en Normativa: poco, pero el mecanismo no existe | `chunker.py:432`, `vigencia.py` |
| **Vigencia: validación** | «la validación humana la escribe el panel» | El reconciliador **pisa** `vigencia_validada_el` con la fecha del `.md` en cada pasada (249 documentos), y `revisat_el` compara *aware* contra *naive*: **292 «actualizaciones» falsas por pasada**, que ocultan las 24 reales | `reconciler.py:_difiere`, `hub_ingestion_router.py:392` |
| **Emparejamiento** | «las parejas están hechas» | Paquete: **57** parejas, todas resueltas (0 rotas), no canónica siempre `es`. Excel de SG: 55 filas `parella`, 180 «sense versió en l'altra llengua», **14 parejas con una versión validada y otra no**, 7 con ninguna. PRG-003 pasa de `parcialment_derogat` a `vigent` en este corpus: **contradice** el caso de referencia de `INGESTA.md` | `parelles_i_vigencies.xlsx` |
| **Operativa de actualización** | «hay un procedimiento para dar de alta una norma» | Los siete pasos de `INGESTA.md` existen, pero el segundo —la ficha— **no tiene herramienta**: hay **12 `alta_*.py`, uno por lote**, y ninguno genérico. Y `correccions_cataleg.json` no puede crear campos (bien hecho), así que poner una causa nueva tampoco se declara. **El alta no es un procedimiento: es un programa que se reescribe** | los 12 `alta_*.py`; `aplica_correccions_cataleg.py` |
| **Coste** | «cada asistente embebe lo suyo» | `chunk_copier.py` (HIB.N) sabe copiar fragmentos entre gemelos con permiso empírico y **tiene cero llamadores**. Los 6 nuevos de Gerencia son subconjunto de los 19 de Normativa: ~142k tokens repetidos ×3 | `chunk_copier.py` |

**Tres cosas funcionan como se pensaba y no necesitan prompt**: el hash sobre el cuerpo (reetiquetar
es un `UPDATE`), la poda que marca y nunca borra, y la hidratación del aviso de desplazamiento por
ancla (880 fragmentos `desplacat`, resuelto en PIL.3).

## Orden, y por qué

```
ACT.0  externas: la decisión, escrita donde se lee    (lado corpus; puede ir en paralelo)
ACT.1  el instrumento dice la verdad                   (sin esto, lo demás se mide con ruido)
ACT.2  ca ≡ val, y el aviso de traducción              (barato; prerrequisito para medir ACT.3)
ACT.3  una sola versión por norma, la de la lengua     (el cambio de comportamiento grande)
ACT.4  solo `vigent` se recupera; causa y suprimit     (sin migración; lectura A del 28-08)
ACT.5  copiar en vez de embeber                        (abarata la ingesta que cierra el bloque)
ACT.6  un comando, y la ingesta real                   (cierre: el corpus del 27-08 en los cuatro)
ACT.7  alta y baja de norma sin escribir un programa    (lado corpus; va con ACT.0, no bloquea)
```

ACT.2 y ACT.3 van **antes** de la ingesta y no después: este corpus sube las parejas de 33 a 57,
y con el código actual eso son 24 normas castellanas más que dejan de responderse en castellano el
día que se ingiere. ACT.4 va antes por lo mismo con las directrices de curso —y su prerrequisito es del lado del corpus: la lectura A (§12.3 del informe) cambia el catálogo e `INGESTA.md` antes que el código.

El botón de «Actualizar corpus» en el frontend **no está en el bloque**: queda como candidato
(abajo). Hoy la actualización son ocho pasos previos en la máquina de curación y una puerta de
validación que vive en este repositorio; un botón que ingiere sin esa puerta invita a saltársela.

---

### Prompt ACT.0 (CORPUS) — La exclusión de las externas, escrita en `assistents.json`

**Modelo sugerido**: **Sonnet** — alcance cerrado, un fichero JSON y una regeneración.

**Objetivo**: que «las externas no van al asistente de normativa» sea una línea del corpus y no un
`UPDATE` manual en una columna que la siguiente reconciliación deshace. Y que la **opción
intermedia** que se hablará con Secretaría General —LOSU sí, LCSP no— tenga ya dónde escribirse.

```
# PROMPT ACT.0 (CORPUS) — La decision sobre las externas, donde el reconciliador la lea
# Deploy: — (repositorio de curacion, no este)

## Que se hace
- En `assistents.json`, `normatiu` deja de tomar `paquet_gerencia/md_externes` en `fonts`, y gana
  el par `excepcions_si` / `excepcions_no` que `gerencia` ya tiene. Por defecto, vacios: la
  configuracion hoy es EXCLUIR. Cuando SG decida el subconjunto, son ids en `excepcions_si`.
- `empaqueta_ingesta.py --aplica` regenera `generat/ingesta/normatiu` (esperado: 317 - 22 = 295)
  y `gerencia` sin cambio (130).
- `valida_contra_el_pipeline.py` sobre las dos carpetas, desde donde este repositorio esta.
- **Lectura A de la vigencia (acordada el 28-08)**: DIR-003/004 a `no_vigent` con
  `motiu_no_vigencia: fi-de-vigencia-temporal`, `substituida_per` y `curs_academic`;
  `vigencia_curs` retirado de `genera_frontmatter.py` y `vigencia_cursos.py`; INS-019 con
  `motiu_no_vigencia: extincio-de-l-objecte`; RES-006/-val y ALT-059 con `derogacio-expressa` y
  `derogada_per`; `vocabulari/motius_no_vigencia.csv` con los seis codigos de §12.3 del informe;
  INGESTA.md reescrita en «Que ha d'acompanyar cada chunk» y «Una norma que deroga una altra».
  `parcialment_derogat` → `vigent` + marca de articulo en NOR-001.
- **PRG-003 / PRG-004 (confirmado por el usuario el 28-08 con la DT primera de PRG-004)**:
  PRG-004 a `vigent` con `substitueix: [PRG-003]` y anclas en sus secciones (hoy solo dt-1 y
  annex-1). PRG-003 `vigent` con `vigencia_transitoria` {per: PRG-004/dt-1/2024-02-27, fins:
  2027-07-31, abast: unic sexenni viu el 27-02-2024, ancores_vigents: [div-3]},
  `data_revisio_prevista: 2027-08-01`, `substituida_per: [PRG-004]`; en el .md, la seccion de
  sexenios con `{#div-3 .transitori}` + nota editorial, y div-1, div-2, div-4..div-7 y annex-1
  con `.derogat` + nota «substituit per PRG-004». Las anclas div-3..div-7 de PRG-003 se declaran
  en `ancores_declarades.json` (secciones sin numerar: el generador no las ancla solo), NO a mano
  en el .md, que se regenera. Sin anclas la regla del corpus es citar el documento entero, y la
  declaracion transitoria valdria igual pero a nivel de documento (ver ACT.4 §4).
  YAML y notas exactas en `CONFIGURACION_APERTURA_PILOTO.html` §12.3.

## Lo que NO se hace
- No se tocan los .md a mano (se regeneran). No se borra nada de la BD: los 22 EXT-* de Normativa se quedan con sus
  27.623 fragmentos y `us_assistents=no`, que es lo que hay hoy. Si SG mete un subconjunto,
  entra a coste cero.
- No se lanza `--prune`: sin censo, la ausencia no significa retirada, y con censo marcaria los
  22 como `retirada_de_la_font`, que es falso.

## Criterio de done
- `--dry-run` de `normatiu` sobre `Normativa UJI` ya NO lista ningun EXT-* con `=`.
- El paquete lo firma la puerta del pipeline (295 / 130 validos).
```

---

### Prompt ACT.1 (CÓDIGO) — El informe de reconciliación dice la verdad

**Modelo sugerido**: **Sonnet** — el defecto está localizado y el criterio de done es un número:
`metadatos=0` en una segunda pasada.

**Objetivo**: hoy una pasada sobre un corpus sin cambios reporta 292 «actualizaciones de
metadatos». Son dos artefactos: `revisat_el` compara `datetime` *aware* (columna `timestamptz`)
contra *naive* (YAML), y `vigencia_validada_el` se pisa con la fecha del `.md` aunque la haya
escrito una persona desde el panel. Con ese ruido, las 24 diferencias reales no se ven.

```
# PROMPT ACT.1 (CODIGO) — Idempotencia de fechas y precedencia de la validacion humana
# Deploy: edge

## Cambio
- `reconciler._difiere` y `_aplicar`: las fechas del front-matter se normalizan a UTC ANTES de
  comparar y de asignar. Un solo sitio (`corpus/frontmatter.py` o `manifest.py`), no dos.
- Precedencia de `vigencia_validada_el` / `vigencia_validada_per`:
  * si el .md trae `vigencia_validada_per`, manda el .md (es la validacion de SG que viaja con
    el corpus);
  * si el .md NO lo trae y la BD tiene fecha, la BD se conserva (la puso el panel, una persona).
  Se escribe en el docstring por que: los dos sistemas escriben el mismo campo y hasta hoy
  ganaba el ultimo en pasar.

## Tests (RED primero)
- Un .md con `revisat_el: '2026-08-10'` contra un documento con `revisat_el` a las 22:00 UTC del
  dia 9 (lo que hoy hay en la BD por la conversion local) → `_difiere` False.
- Documento validado por el panel, .md sin `vigencia_validada_per` → no se pisa.
- Documento sin validar, .md con `vigencia_validada_per` → se escribe.

## Criterio de done
- Dos pasadas seguidas de `--dry-run` sobre el mismo paquete: la segunda da `metadatos=0`.
- Sobre el corpus del 27-08 contra la BD de hoy, el informe lista EXACTAMENTE las diferencias
  reales (esperadas: 24 canonica, 6 estat_vigencia, 31 relacionada_amb, 5 vigencia_curs, y
  las de us_assistents que ACT.0 deje). Se pega el desglose en el commit.
```

---

### Prompt ACT.2 (CÓDIGO) — `ca` y `val` son la misma lengua en todo el sistema

**Modelo sugerido**: **Sonnet** — es una normalización en un punto y un test de tabla.

**Objetivo**: el detector devuelve `ca`; el corpus y sus 60.859 fragmentos llevan `val`. Todo lo
que compara las dos —`prefer`, el aviso de traducción, cualquier filtro futuro— falla en
silencio. Se arregla **una vez, en la frontera**, y no cambiando el corpus (60.859 filas) ni
enseñando a cada consumidor a tolerar los dos.

```
# PROMPT ACT.2 (CODIGO) — Un solo codigo de lengua a partir de la deteccion
# Deploy: edge

## Cambio
- `services/language_detector.py`: la salida de `langdetect` se mapea al codigo DEL CORPUS
  (`ca` → `val`). Es la unica funcion que produce la lengua de la pregunta; todo lo demas la
  consume. Tabla explicita, con `es` y `en` pasando tal cual.
- `hub_chat._NOMBRE_DE_LA_LENGUA` y `_PLANTILLA_DEL_AVISO`: clave `val`. Se retira `ca` de las
  tablas, no se duplica: dos claves para la misma lengua es lo que hoy esta roto.
- `CoreGraphState.language` documenta que lleva el codigo del corpus.

## Lo que NO cambia
- Ni los chunks ni `HubDocument.language`. La lengua del corpus la fija el contrato del corpus
  (`CONTRATO_MD_CORPUS.md`), y `val` es su codigo.

## Tests (RED primero)
- Pregunta en valenciano → `language == "val"`; en castellano → `"es"`.
- Aviso de traduccion: fuente `val`, pregunta `es` → «...esta en valenciano»; fuente `es`,
  pregunta `val` → «...esta en castella». Nunca el codigo crudo.
- `PreferLanguagePolicy.filter_items` con pregunta `val` y items `val`/`es` ordena `val` primero
  (hoy los trata todos como «otra lengua»).

## Criterio de done
- En navegador: una pregunta en valenciano a `Normativa UJI` que se responda con una norma solo
  castellana muestra el aviso con «castella», y una en castellano con norma solo valenciana lo
  muestra con «valenciano». Se adjuntan las dos capturas.
```

---

### Prompt ACT.3 (CÓDIGO) — Una sola versión por norma: la de la lengua de quien pregunta

**Modelo sugerido**: **Opus** — es el cambio de comportamiento del bloque, toca el `WHERE` de las
tres estrategias y redefine qué significa `canonica`.

**Objetivo**: la regla del usuario, literal: *cuando una norma tiene las dos versiones aprobadas,
las dos son oficiales; se busca, se envía al modelo y se cita **la de la lengua de la pregunta**;
si solo existe en la otra, se usa esa y se avisa. Nunca las dos.* Hoy `canonica` excluye la
castellana siempre y `prefer` deja pasar las dos. Y `canonica` se retira: ver mas abajo.

```
# PROMPT ACT.3 (CODIGO) — Canonica por lengua, resuelta en tiempo de consulta
# Deploy: edge

## La condicion, en el WHERE (regla 1 de metadata_filter.py)
Para la lengua L de la pregunta:
    HubDocument.language = L
    OR NOT EXISTS (hermana idiomatica del documento con language = L)
Las dos ramas son excluyentes por construccion: NUNCA sobreviven las dos versiones. Va en el
WHERE y no despues del top-k, porque una version descartada en Python ya ha consumido plaza.
«Hermana» es `versio_idiomatica_de` en cualquiera de los dos sentidos (el corpus lo declara
solo en la no canonica).

## `canonica` se RETIRA (decision del usuario, 28-08-2026)
Las dos versiones publicadas son OFICIALES: a l'UJI la norma s'aprova en valencia (salvo algun
reglamento del Consell Social) y el Reglament de Politica Linguistica manda traducir algunas; la
traduccion la publica Secretaria General o el organo que dicto la resolucion. No hay jerarquia
entre ellas, y llamar «canonica» a una invita a leer que la otra vale menos. Lo unico relevante es
si existe traduccion oficial y en que lengua esta cada version, y las dos cosas ya estan: la
segunda en `language`, que sale del front-matter y es `nullable=False`.

- Se retira `HubDocument.canonica`, el campo del contrato, `include_non_canonical` del
  MetadataFilter y la exposicion en `read_document`. Borrar, no comentar. Migracion Alembic.
- El emparejamiento se queda: es lo que la regla necesita. `versio_idiomatica_de` sigue
  declarandose en un solo lado y el codigo ya lo resuelve en los dos sentidos
  (`agentic_strategy._variant_id`); su direccion pasa a ser un detalle de escritura y **no una
  afirmacion de autoridad**, y asi se documenta.
- No hay rama de repliegue por «lengua no detectada»: el grafo detecta SIEMPRE
  (`detect_language_node`, y `detect_language` tiene `default='es'`). El unico `detect` que
  devuelve None es el de `language_mode: none`, que significa «sin tratamiento de lengua» por
  configuracion explicita: alli la regla no aplica, y no hay nada que repletar.

## VIS.3 se rehace, y se hace mas fuerte
Hoy la guarda agrupa por `source_url` y **salta las no canonicas**, asi que `canonica` funciona
como silenciador. Medido sobre el corpus del 27-08: de las **57 parejas, 47 tienen `url_oficial`
distinta** —cada lengua su PDF— y solo **5 comparten URL**. Es decir, en 47 de 57 `canonica` no
interviene, y lo que la guarda detecta de verdad no son versiones linguisticas sino **dos
documentos que reclaman la misma URL**, que es el defecto real que cazo (NOR-006 y NOR-007, dos
normas distintas con la misma `url_publicacio`).

La regla nueva dice eso mismo, sin `canonica`: **es un defecto que dos documentos compartan
`source_url` y NO sean hermanos idiomaticos**. Gana fuerza, porque ya no se puede silenciar por
accidente marcando algo como no canonico. El mensaje de error nombra las dos rutas y dice si les
falta el emparejamiento o si son normas distintas.

## Lo que NO se hace, y por que
- NO se usa el parametro `language` de `hybrid_search`: es un filtro duro y con `es` desaparecen
  las 195 normas que solo existen en valenciano. Es la trampa de `graph_factory.py:203`.
- NO se cambia `language_mode`: `prefer` sigue ordenando por vigencia y lengua lo que la
  condicion deja pasar; ahora hay una sola version por norma, asi que ordena entre normas
  distintas, que es para lo que sirve.

## Guarda: parejas incompletas
- Al reconciliar, se cuenta cuantos documentos comparten `url_oficial` o titulo normalizado con
  otro de distinta lengua SIN `versio_idiomatica_de` entre ellos, y se lista en el informe.
  Hoy la regla depende de que el emparejamiento este completo, y eso hay que verlo en cada
  pasada, no suponerlo.

## Tests (RED primero)
- Corpus de fixture con: norma A (val+es emparejadas), norma B (solo val), norma C (solo es).
  Pregunta `es` → recupera A-es, B-val, C-es. Pregunta `val` → A-val, B-val, C-es. Nunca A-es y
  A-val a la vez.
- VIS.3: dos documentos con la misma `source_url` y sin emparejar → error que los nombra; los
  mismos dos emparejados → pasa. Es el caso de las 5 parejas que comparten URL (FAQ-001,
  CNV-001, GES-001, REG-127, REG-101) y del defecto NOR-006/NOR-007.
- El agentico (`list_documents`) muestra UNA ficha por norma, la de la lengua de la pregunta.
- La condicion se comprueba en las TRES estrategias (RAG, long-context, agentico) con el mismo
  fixture: el defecto de HIB.U se colo por llevar un cambio a dos de tres puntos.

## Criterio de done
- Medicion sobre las 25 del lote en las dos lenguas (`medir_lote.py`): ninguna respuesta cita
  dos versiones de la misma norma; el documento esperado sigue entrando en igual o mas
  consultas que antes (recuperacion pura, como en HIB.A).
- En navegador: la misma pregunta en castellano y en valenciano sobre una norma bilingue
  (REG-124, que es nueva en este corpus) cita en cada caso la version de esa lengua.
```

---

### Prompt ACT.4 (CÓDIGO) — La vigencia como el corpus la declara: un estado, una causa y las marcas por artículo

**Modelo sugerido**: **Sonnet** — con la lectura A acordada el 2026-08-28 el prompt ya no lleva
migración ni decisión abierta: es un filtro que se simplifica, un metadato que se lee y una
condición sobre fragmentos.

**Objetivo**: el corpus normativo universitario tiene vigencias que «vigente / derogado» no
describe, pero **la solución no es más estados de documento sino menos**: *vigente* significa que
rige ahora; si no rige, hay una causa (la derogación es una de varias); y lo que pasa dentro de
una norma vigente —artículo suprimido, artículo desplazado— se marca en el artículo. Es la
lectura A, acordada con el usuario, que dejó escrita en `CONFIGURACION_APERTURA_PILOTO.html`
§12.3 y que **cambia el corpus antes que el código**: DIR-003/004 pasan a `no_vigent` con causa
temporal, `vigencia_curs` se retira y `INGESTA.md` se reescribe (eso va en ACT.0).

```
# PROMPT ACT.4 (CODIGO) — Solo `vigent` se recupera; la causa se lee, no filtra
# Deploy: edge

## 1. El filtro
- `metadata_filter.document_conditions`: `estat_vigencia = 'vigent'` sustituye a
  `estat_vigencia IS NULL OR != 'derogat'`. Un documento sin estado NO se recupera: el contrato
  del corpus exige el campo en `regulation`, y un NULL es un defecto del paquete, no una norma
  vigente por omision. Se comprueba en las TRES estrategias con el mismo fixture (leccion HIB.U).
- `no_vigent` y `futur` siguen legibles por id (`read_document`): preguntar que regia el curso
  pasado es legitimo, y lo resuelve el agentico leyendola, no el top-k.
- `ESTAT_DEROGAT` se retira del codigo (borrar, no comentar); queda `ESTAT_VIGENT`.

## 2. La causa, sin columna
- `motiu_no_vigencia`, `derogada_per` y `substituida_per` van a `extra` → `doc_metadata`. Nada
  filtra por ellos; `read_document` los devuelve y el prompt del agentico dice como usarlos
  («derogada por X» ≠ «era la del curso X; la vigente es Y»).
- `curs_academic` tambien a `extra`. NO se anade `vigencia_curs` al contrato: bajo la lectura A
  sobra, y anadirlo seria consolidar la lectura contraria.
- El vocabulario de `motiu_no_vigencia` es DATO: `vocabulari/motius_no_vigencia.csv`, cargado
  como los ambitos, validado por `assert_vocabulary` al reconciliar. Propuesta de seis codigos en
  §12.3 del informe; si SG cambia la lista, cambia el CSV.

## 3. El aviso de vigencia no validada
- Queda solo para `vigencia_validada_el IS NULL`. La rama «estado distinto de vigent» de
  `vigencia_no_validada()` desaparece: lo no vigente ya no llega al modelo.

## 4. Marcas por articulo: `suprimit`/`derogat` fuera, `transitori` con aviso
- `ESTADOS_CONSOLIDACION` gana `derogat` (hoy: suprimit, modificat, afegit). El chunker ya
  escribe `estat` en el fragmento; `MetadataFilter.chunk_condition` excluye
  `chunk_metadata->>'estat' IN ('suprimit','derogat')`. Son 3 `suprimit` en Normativa hoy, mas
  los ~7 `derogat` que PRG-003 traera; el coste es una condicion y el beneficio es que el
  mecanismo exista antes de que sean 300.
- `vigencia.py`: `hidratar_desplazamiento` se generaliza a `hidratar_avisos_de_vigencia`, que
  antepone TAMBIEN el aviso de `vigencia_transitoria` cuando el fragmento lleva la clase
  `transitori` y su ancla esta en `ancores_vigents`. **`ancores_vigents` es opcional**: si la
  norma no tiene anclas, la declaracion es de documento y el aviso se antepone a TODOS sus
  fragmentos (y no hay exclusion por articulo). Mismo patron que `desplacat_per`: la
  declaracion vive en el documento por ancla, el aviso se monta al construir la evidencia, y no
  entra en el embedding. Texto: «AVISO DE VIGENCIA: norma sustituida por {norma} ({data}). Este
  apartado sigue aplicandose transitoriamente hasta {fins} solo a {abast} ({norma}, {ancora}).»
- `.desplacat` no cambia: PIL.3 ya lo hidrata por ancla.

## Prerrequisito (ACT.0, lado corpus)
- DIR-003 y DIR-004 con `estat_vigencia: no_vigent`, `motiu_no_vigencia: fi-de-vigencia-temporal`,
  `substituida_per`, `curs_academic`; `vigencia_curs` retirado de `genera_frontmatter.py` y de
  `vigencia_cursos.py`; INGESTA.md §«Que ha d'acompanyar cada chunk» reescrita con la lectura A;
  `parcialment_derogat` sustituido por `vigent` + marca de articulo (NOR-001, y PRG-003 si SG lo
  confirma). Sin esto, el filtro nuevo dejaria las dos directrices compitiendo.

## Tests (RED primero)
- Fixture con DIR-x (`no_vigent`, temporal, `substituida_per` DIR-y) y DIR-y (`vigent`):
  pregunta → solo DIR-y en las tres estrategias. `read_document(DIR-x)` devuelve el texto y el
  motivo.
- `futur` fuera del top-k; documento sin `estat_vigencia` fuera del top-k (y el paquete que lo
  trae, rechazado por el contrato si es `regulation`).
- Fragmento `suprimit` o `derogat` no vuelve de `hybrid_search` aunque sea el mas similar.
- Fragmento `transitori` vuelve CON el aviso delante (fixture: PRG-003 con `vigencia_transitoria`
  y `div-3 .transitori`); un fragmento del mismo documento sin la clase, sin aviso.
- `assert_vocabulary` rechaza un `motiu_no_vigencia` que no esta en el CSV, enumerando todos.
- El aviso de vigencia no salta por un `no_vigent` (ya no hay evidencia suya) y si por un
  `vigent` sin `vigencia_validada_el`.

## Criterio de done
- `--dry-run` del paquete regenerado muestra DIR-003/004 como `= (metadatos)` con
  `estat_vigencia=no_vigent`; tras aplicar, una pregunta sobre matricula de grado sin curso cita
  solo DIR-009/DIR-001 (verificado en navegador, captura). `SELECT count(*) FROM hub_documents
  WHERE estat_vigencia IS NULL AND content_class='regulation'` = 0 en los cuatro chatbots.
```

---

### Prompt ACT.5 (CÓDIGO) — Copiar en vez de embeber, cuando el gemelo ya lo tiene

**Modelo sugerido**: **Sonnet** — el veredicto y el remapeo existen y están probados (HIB.N);
lo que falta es el conductor y la transacción.

**Objetivo**: `chunk_copier.py` decide si los fragmentos de un documento se pueden copiar a otro
chatbot (mismo `content_hash`, misma forma de padre, bajo el techo) y los remapea. **Nadie lo
llama.** El reconciliador embebe siempre. Medido en este corpus: 6 documentos × 3 chatbots de
Gerencia que Normativa ya habrá embebido.

```
# PROMPT ACT.5 (CODIGO) — El reconciliador copia antes de embeber
# Deploy: edge

## Cambio
- `CorpusReconciler._ingerir`: antes de `watcher.process_source`, busca en los chatbots de la
  MISMA organizacion un HubDocument con el mismo `content_hash` del cuerpo y fragmentos. Si
  `se_puede_copiar(...)` es True: crea el HubDocument destino, copia los fragmentos con
  `remapea(...)` (embedding, `parent_content` y `chunk_metadata` incluidos) y aplica los
  metadatos del .md. Si es False, embebe como hoy y el motivo va al informe.
- Nuevo veredicto en `ReconcileReport`: `copiados`, y en el detalle `≈ ruta (copiado de
  <chatbot>)`. El `HubIngestionJob` lo cuenta aparte de `chunks_processed`.
- La comprobacion de coherencia `incoherentes()` se pasa sobre el destino al terminar, siempre
  (leccion de HIB.U: un invariante que solo se comprueba donde se sospecha no es un invariante).

## Lo que NO se hace
- No se comparte el corpus entre chatbots: cada uno sigue con sus filas. Es una decision tomada
  (memoria `project_corpus_normativo_estrategia`). Copiar es respetarla pagando una vez.
- No se copia entre organizaciones.

## Tests (RED primero)
- Dos chatbots, mismo .md: el segundo `--chatbot-id` no llama a `embed` (mock con `spec=`) y
  termina con los mismos fragmentos, `document_id` y metadato coherentes.
- Veredicto False (padre por encima del techo) → embebe y el motivo aparece en el informe.

## Criterio de done
- `--dry-run` del paquete `gerencia` sobre los tres chatbots tras haber cargado `normatiu` lista
  los 6 nuevos como `≈` y `ingeridos=0`.
```

---

### Prompt ACT.6 (CÓDIGO + OPERACIÓN) — Un comando, y la ingesta del corpus del 27-08

**Modelo sugerido**: **Sonnet** — orquesta lo que los cinco anteriores dejaron hecho; la
única decisión es la forma de la confirmación.

**Objetivo**: que actualizar el corpus sea **un comando** con un descriptor, un dry-run
obligatorio, una confirmación que **separa** lo que cambia de estado de lo que solo entra, y la
aplicación en el orden que hace que ACT.5 ahorre. Y ejecutarlo de verdad: el bloque se cierra
con el corpus del 27-08 en los cuatro chatbots de desarrollo.

```
# PROMPT ACT.6 (CODIGO + OPERACION) — actualiza_corpus.py, y la primera actualizacion real
# Deploy: edge

## Cambio
- `server/app/modules/agents_hub/ingestion/corpus/actualiza.py` (CLI `python -m ...`):
  * lee un descriptor YAML: lista de {paquete, chatbots[]} (el de la UJI vive en `_local/`, no
    en el repo: lleva UUIDs de una instancia);
  * `--dry-run` de TODOS los paquetes primero, y un resumen por chatbot con CUATRO bloques
    separados: nuevos (+), cuerpo cambiado (~), copiables (≈), y **cambios de estado**
    (us_assistents, canonica, estat_vigencia, vigencia_curs) listados uno a uno;
  * exige `--confirmar` o respuesta interactiva para aplicar; sin ella, termina tras el plan;
  * aplica en el orden del descriptor (Normativa primero, para que Gerencia copie);
  * termina con `detectar_divergencias` sobre los chatbots tocados y falla si quedan copias
    fuera de sincronia que el propio comando debia haber resuelto.
- Sin `--prune` por defecto; se pasa explicitamente y con `--census`, como hoy.

## Operacion (cierre del bloque)
1. ACT.0 aplicado en el corpus: paquete `normatiu` sin las 22 externas.
2. `actualiza --dry-run` y pegar el plan en el informe de cierre.
3. Aplicar sobre los cuatro chatbots. Esperado: Normativa +19; Gerencia ≈6 ×3; 0 reingeridos;
   los cambios de estado exactamente los que ACT.1 dejo visibles.
4. Segunda pasada: `metadatos=0`, `ingeridos=0`, `copiados=0`. Es la prueba de idempotencia
   de todo el bloque.
5. Las 17 copias fuera de sincronia de hoy (FAQ-001, CNV-001, GES-001, REG-127-es, REG-101-es)
   resueltas por la propia pasada; si alguna queda, se dice por que.

## Tests (RED primero)
- Descriptor con dos paquetes: el comando ejecuta los dry-run antes de tocar nada, y sin
  `--confirmar` no escribe (la BD de test queda identica).
- El resumen separa los cuatro bloques y lista los cambios de estado por id.

## Criterio de done
- Corpus del 27-08 en los cuatro chatbots de desarrollo, segunda pasada a cero, y la medicion
  de ACT.3 repetida sobre el corpus nuevo (las 57 parejas) sin ninguna cita doble.
```

---

### Prompt ACT.7 (CORPUS) — Dar de alta una norma y cambiar su vigencia, con un comando cada cosa

**Modelo sugerido**: **Opus** — hay que decidir qué es declaración y qué es acción en un corpus con
doce programas de alta escritos uno por lote, y equivocarse aquí deja un decimotercero.

**Objetivo**: ACT.1–ACT.6 arreglan la **reingesta**; esta es la otra mitad, la **actualización**. Hoy
dar de alta una norma son los siete pasos de `INGESTA.md` §«Una norma nova», de los que el segundo
—la ficha del catálogo— **no tiene herramienta**: se ha resuelto escribiendo un programa nuevo cada
vez. Hay **doce** `alta_*.py` en el corpus, uno por lote (`alta_directrius_curs_2026_2027.py`,
`alta_versions_valencianes_2026_08{,b,c}.py`, `alta_fitxes_gerencia_2026_08{,b}.py`…), y ninguno
genérico. El alta no es un procedimiento: es un programa que se reescribe. Con cada norma nueva, el
coste no baja.

Y cambiar una vigencia tiene el problema simétrico: `correccions_cataleg.json` corrige un campo que
la ficha **ya tiene** —se niega a crear campos, y hace bien—, así que poner una causa a una norma
que aún no la lleva no se puede declarar: hay que volver a escribir un programa.

```
# PROMPT ACT.7 (CORPUS) — `alta_norma.py` y `vigencia.py`
# Deploy: — (repositorio de curacion, no este)

## 1. `vigencia.py` — cambiar el estado de una norma, con su causa
    python vigencia.py NOR-001 --estat vigent --motiu ""            # en sec
    python vigencia.py ALT-059 --estat no_vigent --motiu fi-de-mandat --aplica
    python vigencia.py RES-006 --estat no_vigent --motiu derogacio-expressa \
                       --derogada-per RES-005 --aplica
- Valida el motiu contra `vocabulari/motius_no_vigencia.csv` y **exige** `--derogada-per` cuando
  la causa es `derogacio-expressa` y `--substituida-per` cuando es `substitucio`: una derogacion
  expresa sin la norma que deroga es una afirmacion que nadie puede comprobar.
- Rechaza `--motiu` sobre una norma que queda `vigent`, y exige `--motiu` cuando el estado deja de
  serlo, salvo `--motiu-pendent "<por que aun no se sabe>"`, que lo deja explicito en vez de vacio.
- Es el DUENO del campo: crea `motiu_no_vigencia`/`derogada_per`/`substituida_per` en la ficha si
  no estan, que es justo lo que `aplica_correccions_cataleg.py` no debe hacer. Idempotente, en
  seco por defecto, copia de seguridad antes de escribir, y reescribe JSON **y** CSV.
- Deja rastro en `correccions_cataleg.json` con `motiu` y `confirmat` (quien y cuando), que es
  como el corpus registra las decisiones humanas. Sin esto, dentro de un ano nadie sabe si la
  causa la decidio una persona o la dedujo un programa.
- `alta_motiu_no_vigencia.py` se RETIRA al terminar: era el alta del campo, y su trabajo lo hace
  ahora esto. Es codigo muerto en cuanto exista `vigencia.py`.

## 2. `alta_norma.py` — la ficha, sin escribir un programa
    python alta_norma.py fitxa_REG-140.json --aplica
- Un JSON por norma con los campos que decide una persona (`id_publicacio`, `titol`, `tipus`,
  `organ_emissor`, `data_aprovacio`, `estat_vigencia`, `url_publicacio`, `ambit`, `submateries`,
  `resum`, `publicar_al_portal`) y nada mas: lo derivable se deriva.
- Valida ANTES de escribir: id libre y de la serie correcta, ambito y submaterias contra el
  vocabulario, `url_publicacio` que no colisione con otra ficha (es el defecto que VIS.3 caza
  tarde: NOR-006 y NOR-007 compartian URL sin ser la misma norma), y el `.md` de origen presente.
- Admite VARIAS fichas en un fichero, que es como llegan de verdad: los lotes de 2026-08 fueron
  de 19 y de 13, y por eso se escribieron programas.
- **Los doce `alta_*.py` no se borran en este prompt.** Son el registro de lo que se dio de alta
  y cuando; borrarlos es perder la trazabilidad de doce lotes. Se marcan como historicos en su
  docstring y no se escriben mas.

## 3. Lo que este prompt NO hace, y por que
- No convierte el PDF ni construye las paginas: eso ya es `passa_el_pipeline.py`. `alta_norma.py`
  y `vigencia.py` terminan diciendo «ahora: python passa_el_pipeline.py --aplica», como hace hoy
  `aplica_correccions_cataleg.py`.
- No decide la vigencia ni la clasificacion. Son juicios; el programa comprueba que lo escrito es
  coherente, no lo inventa.

## Tests (RED primero)
- `vigencia.py` sobre una ficha sin el campo lo crea; sobre una que ya lo tiene igual, no escribe
  (idempotencia) y lo dice.
- `derogacio-expressa` sin `--derogada-per` → error, nada escrito.
- Un motiu que no esta en el vocabulario → error que enumera los validos.
- `alta_norma.py` con una `url_publicacio` que ya usa otra ficha → error nombrando las dos.
- Con un id repetido → error. Con un ambito inexistente → error que enumera los validos.
- Tras `alta_norma.py` + `passa_el_pipeline.py`, la ficha nueva pasa el validador real de ingesta.

## Criterio de done
- Dar de alta una norma de prueba y retirarla despues, sin escribir ni una linea de Python, y con
  el pipeline en verde en las dos pasadas. Se pega la sesion entera en el commit.
- `INGESTA.md` §«Una norma nova» reescrita con los dos comandos, y §«Una norma que deroga una
  altra» con `vigencia.py`.
```

---

### Prompt ACT.8 (CÓDIGO) — El agéntico también trocea lo que ingiere

**Modelo sugerido**: **Sonnet** — la decisión ya está tomada (el usuario, 2026-08-28); lo que
queda es cambiar una condición en tres sitios y reindexar un asistente.

**Objetivo**: la ingesta trocea y embebe **sólo en modo RAG**, y el banco agéntico está en
`MD_AGENT_SELECTOR`. Al actualizar el corpus, sus 6 documentos nuevos entraron **sin un solo
fragmento**. La premisa —«los otros dos modos no embeben nada»— está escrita igual en tres sitios
y fue una decisión, pero es **anterior** a que el agéntico tuviera búsqueda por fragmentos: su
herramienta `search_knowledge` consulta justamente eso, y HIB reparó sus 14.198 fragmentos
dejando escrito que «no son peso muerto».

Sin esto, su búsqueda por fragmentos es ciega a lo que se ingiera desde ahora, **y una reingesta
de un documento ya troceado le borraría los fragmentos que tiene** —el `else` los borra—.

```
# PROMPT ACT.8 (CODIGO) — Quien tiene busqueda por fragmentos, los tiene
# Deploy: edge

## La pregunta correcta no es el modo, es si el asistente busca por fragmentos
`RAG` y `MD_AGENT_SELECTOR` los usan: el primero como su unica via, el segundo a traves de
`search_knowledge`. `MD_LONG_CONTEXT` no: inyecta documentos enteros y no consulta el indice
vectorial nunca. Asi que la condicion deja de preguntar «¿es RAG?» y pasa a preguntar «¿este
modo busca por fragmentos?», que es lo que de verdad decide si hay que trocear.

## Cambio, en los tres sitios que hoy dicen lo mismo
- `MODES_QUE_BUSQUEN_PER_FRAGMENTS = ("RAG", "MD_AGENT_SELECTOR")`, en un solo sitio, y los tres
  lo importan. Que la premisa estuviera repetida tres veces es por lo que envejecio sin que
  nadie la revisara.
- `watcher.process_source`: trocea si el modo esta en el conjunto. **El `else` que BORRA los
  fragmentos** se queda solo para los modos que de verdad no los usan.
- `corpus_recalculator`: igual.
- `hub_chatbots_router`: exigir servicio de embeddings operativo al crear tambien en
  `MD_AGENT_SELECTOR`. Crear un asistente que no va a poder trocear es fallar tarde.

## Lo que NO cambia
- `MD_LONG_CONTEXT` sigue sin embeber, y su `else` sigue borrando: es el unico modo que de
  verdad no consulta fragmentos.
- Ningun asistente en produccion se toca: los dos son RAG. Esto afecta a un banco de
  comparacion.

## Tests (RED primero)
- `process_source` con `MD_AGENT_SELECTOR` crea fragmentos (hoy son 0).
- `process_source` con `MD_LONG_CONTEXT` NO crea fragmentos y borra los que hubiera.
- Reingerir un documento en `MD_AGENT_SELECTOR` no deja el documento sin fragmentos, que es el
  defecto latente: hoy el `else` se los llevaria.
- `corpus_recalculator` en `MD_AGENT_SELECTOR` devuelve `chunks_created > 0` y `deleted == 0`.

## Criterio de done
- Los 6 documentos del banco agentico con fragmentos, y **cero documentos sin fragmentos** en
  los cuatro asistentes.
- La suite de `modules/agents_hub`, `public_graphs` y `api` en verde.
- §12.4 del informe reescrito: deja de ser un hueco abierto.
```

---

### Prompt ACT.9 (CÓDIGO) — La caducidad también es de la norma, no de una de sus lenguas

**Modelo sugerido**: **Sonnet** — es el mismo argumento que ya se aceptó para la validación, y el
sitio donde va es el mismo.

**Objetivo**: ACT.6 hizo que la validación de vigencia se compartiera entre las dos versiones de
una norma, porque lo que una persona valida es **que la norma rige**. La `data_revisio_prevista`
—cuándo hay que volver a mirarla— es el mismo tipo de hecho y **no se comparte**: al declarar que
`PLA-003` caduca el 31-12-2026, su versión valenciana se quedó con el plazo por defecto de 365
días. Nadie la habría vuelto a mirar el día que toca.

```
# PROMPT ACT.9 (CODIGO) — Propagar la caducidad entre hermanas idiomaticas
# Deploy: edge

## Cambio
- `_compartir_la_validacion` pasa a compartir tambien `data_revisio_prevista`, y se renombra a
  lo que hace: `_compartir_lo_que_es_de_la_norma`. Las dos cosas son hechos sobre la NORMA
  —cuando se valido y cuando caduca—, no sobre el texto de una lengua.
- Misma regla que la validacion: solo cuando UNA la tiene. Con las dos declaradas se respeta
  cada una; con ninguna, no hay nada que compartir.
- **Gana la mas TEMPRANA cuando las dos existen y difieren.** No es simetrico con la validacion:
  volver a mirar una norma antes de tiempo cuesta una revision de mas, y hacerlo tarde es no
  haberla mirado. Ante la duda, antes.
- Se anota `data_revisio_des_de` en `doc_metadata`, como `vigencia_validada_des_de`, y entra en
  `_METADATOS_QUE_NO_VIENEN_DEL_CORPUS` para que la pasada siguiente no lo quite y lo vuelva a
  poner.

## Lo que NO cambia
- El defecto de 365 dias de SYNC.2 sigue: solo se aplica cuando NINGUNA de las dos lo declara.

## Tests (RED primero)
- Pareja con la fecha declarada en una: la otra la hereda y queda `data_revisio_des_de`.
- Pareja con las dos declaradas y distintas: las dos conservan la suya (no se pisa ninguna) y
  ninguna queda con `data_revisio_des_de`.
- Ninguna declarada: las dos con el defecto, sin marca de herencia.
- Idempotencia: segunda pasada con `metadatos=0`.

## Criterio de done
- `PLA-003` y `PLA-003-val` con `2027-01-01` sin declararlo dos veces en el corpus, y una
  segunda pasada a cero.
```

---

### Prompt ACT.10 (CORPUS) — Ficha para los cinco documentos que no la tienen

**Modelo sugerido**: **Opus** — hay que decidir qué se rellena, qué se deja vacío y qué NO se
inventa, y equivocarse aquí mete en el catálogo metadatos que nadie ha decidido.

**Objetivo**: aplicar la propuesta de §12.6 del informe. Cinco documentos de la UJI entran al
asistente **sin ficha en el catálogo**, y sus metadatos viven en `router_sense_fitxa.json`, un
canal paralelo que ya ha demostrado tres veces que no lleva todo: les falta el **puente
bilingüe** —son los únicos cinco del corpus sin `termes_bilingues`, así que quien pregunte en
castellano no encuentra su texto valenciano y al revés—, la firma de la revisión de conversión, y
hasta hoy no les llegaba la validación de vigencia.

**Una corrección de premisa, medida**: los cinco **sí tienen URL** —están en el web de la UJI, en
páginas de servicio— así que no son «no publicados»: lo que les falta es estar en el **catálogo
de transparencia**. La decisión de publicarlos ahí es posterior e independiente.

```
# PROMPT ACT.10 (CORPUS) — Los cinco al camino principal
# Deploy: — (repositorio de curacion)

## Que entra al cataleg
Tres normas en cinco ficheros: FAQ-001 / FAQ-001-val (preguntes frequents de la UGITJ),
GES-001 / GES-001-val (procediment de gestio economica de cursos) i MAN-001 (manual del
pressupost de contractes de l'article 60 LOSU).

## Que se rellena, y de donde sale
- Lo que YA declaran su front matter o `router_sense_fitxa.json` se transcribe: `titol`,
  `idioma`, `tipus`, `url_publicacio`, `resum_router`, `preguntes_tipus`, `ambit`,
  `submateries`, `rang`. No se re-decide nada que ya este decidido.
- `estat_vigencia: vigent` y la validacion del 28-08, que ya tienen.
- **Las dos parejas se declaran como parejas** (`versio_idiomatica_de`), que es lo que hoy no
  esta: sin eso la regla de lengua de ACT.3 no las separa y las dos versiones pueden citarse
  juntas. MAN-001 no tiene pareja.
- `publicar_al_portal: false`. Tener ficha no es estar publicado, y confundirlo seria decidir
  por Secretaria General.

## Que NO se inventa
- `data_aprovacio` si el documento no la dice. Un campo vacio es honesto; una fecha inventada
  contamina el eje temporal y nadie la vuelve a mirar.
- `organ_emissor` si no consta.
- `content_class`: FAQ-001 se queda en `faq` y los otros en `generic`. Promoverlos a
  `regulation` exigiria la firma de la revision de conversion, que nadie ha hecho.

## Que se gana, y hay que comprobarlo
- `termes_bilingues` en los cinco: el pipeline los genera desde el cataleg, asi que entran solos.
  **Es el motivo principal del prompt** y es lo que hay que medir al cerrar.
- El emparejamiento de las dos parejas.
- El canal unico: `router_sense_fitxa.json` se queda solo con las 22 externas, y su docstring lo
  dice.

## Criterio de done
- `alta_norma.py` los da de alta (es su primer uso real; si el programa no sirve para esto, el
  problema es del programa).
- Los cinco con `termes_bilingues` y **cero documentos del corpus sin puente bilingue**.
- Las dos parejas emparejadas, y la guarda de VIS.3 en verde.
- Pipeline entero y la puerta del validador: 295 y 130.
```

---

### Prompt ACT.11 (INFORME) — Los 35 documentos sin vigencia confirmada, con nombre

**Modelo sugerido**: **Sonnet** — es un listado sacado de la base de datos; lo que hay que
pensar es cómo se ordena para que se pueda revisar de un tirón.

**Objetivo**: el informe dice «35 documentos sin confirmar» y no dice cuáles. Quien tiene que
revisarlos no puede hacerlo desde una cifra. Se listan con título, estado y si tienen URL, para
que el responsable del corpus los revise él mismo y sólo lleve a Secretaría General aquellos en
los que tenga dudas.

```
# PROMPT ACT.11 (INFORME) — El listado, para poder revisarlo
# Deploy: — (documentacion)

## Que se escribe
- Apartado nuevo en §12 con los 35, ordenados por serie, con: identificador, lengua, titulo,
  estado declarado y si tienen URL oficial.
- Agrupados por lo que hace falta para decidirlos, no por orden alfabetico: las 31 que no tienen
  URL —internas, casi todas circulares e instrucciones de Gerencia y del Vicerectorat
  d'Investigacio— separadas de las 4 que si la tienen.
- Una linea diciendo que validar una version de una pareja basta.

## Que NO se escribe
- No se propone un veredicto para ninguna. El informe lista; quien valida es una persona.
```

---

## Candidatos con prompt propio, para después

- **Botón «Actualizar corpus» en la pestaña Documentos.** La pantalla útil no es «ingerir» sino
  **ver el plan** (los cuatro bloques de ACT.6) y aplicar. Tiene sentido cuando el corpus lo
  mantenga alguien sin terminal; hoy la puerta de validación vive en este repositorio y un botón
  que la salte es peor que no tenerlo.
- **`audita_versions_publicades.py` como tarea periódica** (el «tercer caso» de INGESTA.md: la
  UJI publica una consolidación nueva en la MISMA URL). Es del lado del corpus; aquí sólo
  haría falta que el `source_url` cambiado se viera como `~`, y ya se ve.
- **Subconjunto de externas en Normativa** (LOSU sí, LCSP no): cuando SG decida, es
  `excepcions_si` en `assistents.json` y una pasada. Cero código.

## Lo que este bloque le pide a Secretaría General

Está en `docs/CONFIGURACION_APERTURA_PILOTO.html` §12, con las opciones. Resumido: (1) qué
externas entran en Normativa, si alguna; (2) confirmar la regla de lengua tal como la formuló el
usuario; (3) las 14 parejas con una versión validada y otra no, y las 7 sin ninguna; (4) validar
el modelo de vigencia de la lectura A y el vocabulario de `motiu_no_vigencia`; (5) validar la
lectura de la DT primera de PRG-004 (colectivo, alcance y fin), que el usuario ya fijó el 28-08.

---

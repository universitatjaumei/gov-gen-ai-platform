# Contrato del `.md` del corpus normativo

**Versión 2** (2026-07-29). Incorpora las quince enmiendas de
`publicacio_transparencia_2026-07/PROPOSTA_ESMENES_CONTRACTE_MD.md`, medidas sobre la conversión
completa de los 229 documentos, y reencuadra el alcance (§0) tras revisar el contrato contra la
estrategia de recuperación real.

Especificación del Markdown que consume el asistente. Se aplica al corpus histórico y al que emita
el pipeline de publicación.

Destinatarios: quien convierte el corpus existente y quien defina el generador de publicación (el
`.md` se guarda en la BD de publicación y de ahí salen el PDF y el HTML).

Consumidor en el hub: `MarkdownChunker` (`server/app/modules/agents_hub/ingestion/chunker.py`) y
`ingestion/corpus/` (front-matter y contrato de paquete), prompts **ING.0.3** e **ING.0.4** de
`Plan_TDD_Fase1.md`.

---

## 0. Alcance y prioridad: qué de esto paga y qué no

La versión 1 de este documento trataba la jerarquía y las anclas como **requisito**. Al contrastarlo
con la estrategia de recuperación resulta que apunta al corpus equivocado, y conviene decirlo antes
de que nadie invierta más esfuerzo:

| Nivel de la estrategia | Corpus | ¿Se trocea? |
|---|---|---|
| 0-2 — índice de submaterias → fichas → **inyección de 1-3 normas completas** | ~380 normas UJI | **No** |
| 3 — RAG por artículos | ~22 leyes BOE/DOGV | **Sí** |

El 99,7 % de la normativa propia se inyecta entera, así que **para ese corpus el chunker no
interviene**: no hay fronteras de fragmento que proteger ni ruta que reconstruir, porque el modelo
ve el documento completo. Y el corpus que sí necesita troceado —las leyes estatales y
autonómicas— llega de `legistools` como **XML consolidado**, con la estructura de artículos ya
marcada por el BOE: ahí las anclas salen del XML sin que nadie clasifique encabezados a mano.

De donde sale la regla de prioridad de esta versión:

**1. Las anclas son oportunistas, no obligatorias.** Se emiten donde el patrón es inequívoco —con
los tres prefijos que fija esta versión, las doce familias de la taxonomía quedan decididas y
cubren los 1.115 encabezados— y **no se fuerzan** en el resto. Su único consumidor es el enlace profundo de la cita, y un ancla que
falta degrada a citar el documento, que es lo que el hub ya hace. Verificado: con el corpus sin
anclas, 14.192 fragmentos y todo funcionando.

**2. La jerarquía por tipo se mantiene** (§1) porque es barata y resuelve el 78 % de los
encabezados con una tabla de correspondencias. Un encabezado que no encaje en ninguna familia se
queda en `##` y no pasa nada.

**3. Lo que sí es obligatorio es que el contenido esté completo.** Un artículo cuyo cuerpo se
perdió en la conversión falla en **todos** los modos de recuperación —inyección, RAG y cita— y es
el fallo que hunde un piloto en silencio, porque nadie descubre que falta hasta que el asistente
responde mal a alguien. En la medición actual son **8 unidades citables sin cuerpo** —5 con rúbrica
y 3 que además la han perdido— y, en una categoría aparte, **3 documentos con pérdida real de
articulado**: ALT-065, ALT-034 y REG-030 (Anexo A). **Ese es el trabajo que paga**, por delante de
cualquier refinamiento de la taxonomía de encabezados.

Conviene medirlo **sobre la salida convertida y no sobre la entrada**, y con una definición escrita:
en `md/` el recuento no mide lo mismo, porque una división estructural interpuesta entre el artículo
y su cuerpo hace que el artículo parezca vacío y la conversión la degrada precisamente por eso. La
definición que se usa está en el Anexo A. Y conviene **clasificar por causa antes de abrir un PDF**:
los artículos suprimidos no tienen cuerpo porque no deben tenerlo, y desde el §8.3 lo declaran con la
clase `.suprimit` en vez de deducirse de una nota al pie.

**4. Para BOE y DOGV no se escribe `.md` a mano.** Se genera desde el XML consolidado.

---

## 1. Principio que decide todo lo demás

**El nivel del encabezado lo determina el TIPO de elemento, no su anidamiento real.**

Un artículo es `#####` siempre: en una norma con Título > Capítulo > Sección y en una de doce
artículos sin ninguna división. Un capítulo es `###` aunque la norma no tenga títulos.

Esto se aparta de lo que haría un editor humano (que subiría de nivel lo que no está anidado) y es
deliberado, por tres razones:

1. **La conversión del histórico es una tabla de correspondencias, no un algoritmo con estado.** Los
   encabezados del corpus original están aplanados en `##`, pero llevan su etiqueta en el texto
   («Article 14», «Capítol III»). Con nivel fijo por tipo, el script lee la etiqueta y asigna el
   nivel; medido, esa tabla resuelve sin ambigüedad el **78 %** de los encabezados. Con nivel por
   anidamiento habría que mantener una pila y decidir profundidades relativas en 229 documentos.
2. **El chunker puede confiar en el nivel.** Si el artículo está siempre en el mismo nivel, el
   troceado es uniforme. Si varía entre `##` y `#####` según la norma, el nivel deja de significar
   nada.
3. **Los saltos de nivel no son un problema.** Un `#####` justo debajo de un `##` es Markdown
   válido y el splitter lo trata bien: registra los encabezados que ve y descarta los niveles
   intermedios que quedaron atrás. No hay que rellenar huecos con encabezados vacíos.

---

## 2. Tabla de niveles

| Nivel | Elementos | Ancla | Ejemplo |
|---|---|---|---|
| `#` | Título del documento (**uno solo por fichero**, ver §2.1) | no | `# Reglament sobre indemnitzacions per raó del servei` |
| `##` | Preámbulo · Título (Títol) · encabezado de grupo de disposiciones · Anexo · división de primer orden en documentos sin articulado | según §4 | `## Títol I. Disposicions generals` |
| `###` | Capítulo | no (§4.4) | `### Capítol III. Dietes` |
| `####` | Sección | no (§4.4) | `#### Secció 2a. Manutenció` |
| `#####` | **Unidad citable**: Artículo · Disposición concreta · Apartado de resolución · Unidad con etiqueta ordinal | oportunista, §4 | `##### Article 14. Import de la dieta {#art-14}` |

**Preámbulo, Título, Disposiciones y Anexo comparten el nivel `##`** porque son las divisiones de
primer orden de la norma, hermanas entre sí.

**Todas las unidades citables comparten el nivel `#####`** porque son la misma cosa a efectos de
cita y de recuperación: la unidad autónoma que alguien cita. El encabezado de grupo («Disposicions
addicionals») es `##` y cada disposición dentro es `#####`.

### 2.1 De dónde sale el `#` único

> *(Enmienda 10.)* El `.md` convertido trae el título partido en dos, en mayúsculas, mezclado con la
> cabecera institucional o con el número de publicación del DOGV, y en algún caso un `#` propio que
> es un slug truncado de la conversión.

**El título del documento se toma del catálogo de publicación, no del cuerpo del `.md`.** Si algún
encabezado del cuerpo coincide con él, se promueve a `#`; si no, se inserta. Cualquier `#`
preexistente que no sea el título se degrada a `##`: el contrato admite uno solo.

### 2.2 Número y rúbrica van en un solo encabezado

> *(Enmienda 8. El defecto más numeroso del corpus: 784 encabezados, el 40 % de los sin clasificar.)*

La conversión los separa y además **invierte la jerarquía**:

```
### CAPÍTULO II
## Facultades y escuelas superiores      <- la rúbrica, en un nivel SUPERIOR
```

**Forma canónica: número y rúbrica en el mismo encabezado** — `### CAPÍTULO II. Facultades y
escuelas superiores`. Una rúbrica en un encabezado aparte deja la rúbrica huérfana, sin nivel ni
ruta, y rompe el orden de la ruta que reconstruye el hub.

Dos avisos de implementación, los dos aprendidos a golpes:

- Fundir **solo** cuando la división no trae rúbrica propia.
- El patrón debe aceptar el indicador ordinal (`Secció 2.ª`, `Secció 2a`), y hay que contar los
  puntos **realmente** añadidos: hay divisiones ya escritas con punto final (`CAPÍTOL II.`) y
  suponer siempre un punto nuevo descuadra la verificación de integridad.

### 2.3 Lo que NO lleva encabezado

Los **apartados** de un artículo (`1.`, `2.`, `a)`, `b)`) se quedan como contenido —lista o
párrafo— dentro de su artículo. **El artículo es la unidad atómica.** Bajar de ahí multiplicaría por
diez el número de encabezados y no mejora la cita: «art. 14.2» se resuelve leyendo el artículo 14.

Tampoco son encabezados:

- La fórmula de aprobación, los pies de firma y las notas al pie.
- *(Enmienda 12.)* **Cabeceras de página** (`Universitat Jaume I`, `Vicerectorat d'…`, `Conselleria
  d'Educació…`) y **aparato del diario oficial** (`DECRETO`, `Estado`, `I. DISPOSICIONES
  GENERALES`, `[2023/12857]`). Como encabezado crean una frontera de fragmento y un tramo de ruta
  que no informa de nada.

  Se degradan a texto **en el `.md` que alimenta al asistente**, que es lo que este contrato
  regula. Si la vista de publicación necesita conservarlas, es asunto del generador de HTML: los dos
  artefactos tienen destinatarios distintos y no tienen por qué coincidir.
- *(Enmienda 11.)* **Las entradas del índice.** La conversión las promueve a encabezados y entonces
  el mismo artículo aparece dos veces, con anclas que colisionan. Se delimita la región del índice
  —desde el encabezado `ÍNDICE`/`ÍNDEX` hasta que reaparece el primero de sus encabezados, que es
  donde empieza el cuerpo— y se degrada a texto.

  > **Aviso, y es el más importante de esta sección.** La regla «un artículo sin cuerpo es una
  > entrada de índice» **es falsa y destruye información**. `## Artículo 50. Periodicidad y
  > numeración` seguido directamente del 51 no es índice: es un artículo **cuyo cuerpo se perdió** en
  > la conversión, y degradarlo borra la última traza que queda de él. Solo se degrada si el mismo
  > número aparece **otra vez** en el documento con cuerpo. Con la regla mal puesta se destruían 39
  > encabezados legítimos.

  **Punto ciego conocido, y se deja así a propósito.** La delimitación de arriba parte del
  encabezado `ÍNDICE`/`ÍNDEX`, y **el índice no siempre es una región de encabezados**: en 43 de los
  229 documentos es una **tabla** (`| Índex |` y una fila por entrada), sin encabezado que abra la
  región. Ahí la regla no puede dispararse, y basta con que una línea se escape de la tabla y se
  promueva a encabezado para que aparezca un resto de índice con ancla. Es lo que pasa en el
  `Reglament per a la concessió de distincions`, donde además el resto fusiona dos entradas
  (`DISPOSICIÓ DEROGATÒRIA DISPOSICIÓ FINAL` en una sola línea).

  **No se endurece la detección de la región.** El coste esperado es malo: este terreno ya destruyó
  39 encabezados legítimos una vez, y el problema que quedaría por resolver es **un caso de 11**
  (§4.8). Se cubre por la vía barata y reversible —el desempate por cuerpo del §4.8, que no
  reclasifica nada— y se vigila con un detector que reporta y no bloquea (§7).

### 2.4 Prohibido sustituir encabezados por negrita

Si un artículo se marca con `**Article 14.**` en lugar de un encabezado real, para el hub ese
artículo no existe como estructura: se pierde el nivel, la ruta y el ancla.

---

## 3. Esqueleto del fichero

```markdown
---
id_publicacio: REG-020
title: Reglament sobre indemnitzacions per raó del servei i gratificacions
language: ca
ambit_principal: administracio
submateries: [indemnitzacions-i-dietes]
estat_vigencia: vigent
url_oficial: https://www.uji.es/...
---

# Reglament sobre indemnitzacions per raó del servei i gratificacions

## Preàmbul {#preambul}

Text del preàmbul...

## Títol I. Disposicions generals

### Capítol I. Objecte i àmbit

##### Article 1. Objecte {#art-1}

1. Aquest reglament regula...
2. Als efectes previstos...

## Títol II. Indemnitzacions

### Capítol III. Dietes

#### Secció 2a. Manutenció

##### Article 14. Import de la dieta {#art-14}

...

## Disposicions addicionals

##### Disposició addicional primera. Actualització d'imports {#da-1}

...

##### Segona. Limitació al gasto {#da-2}

...

## Annex A. Quadre d'imports {#annex-a}

<!-- TABLA-TEXT: t01.png | pàg. 12 | 6x3 | markdown -->
| Concepte | Import | Vigència |
| --- | --- | --- |
| Dieta sencera | 53,34 € | 2026 |
<!-- /TABLA-TEXT -->
```

El front-matter va **antes** del `#`. El hub lo separa del cuerpo y **calcula el hash sobre el
cuerpo**, no sobre el front-matter: así reetiquetar una norma no dispara un re-troceado ni un
re-embedding, y cambiar el texto sí. Dos corolarios de la implementación (ING.0.3):

- Un `.md` que **gana** front-matter después conserva su hash y no se reingiere: la línea en blanco
  que separa el bloque del cuerpo es formato, no contenido.
- El hash **no depende del final de línea**: CRLF y LF dan el mismo. El corpus se produce en Windows
  y el sync puede entregarlo con LF; no debe reingerirse por eso.

### Claves del front-matter

No hace falta que el `.md` enumere los 56 campos del esquema, y tampoco que el hub los conozca:
**las claves que el contrato no declara van a `doc_metadata`** tal cual, así el esquema puede crecer
sin tocar el código. Las que sí tienen tratamiento propio, porque gobiernan recuperación, acceso o
puertas de calidad:

`id_publicacio` · `title` · `language` · `content_class` · `ambit_principal` ·
`ambits_secundaris` · `submateries` · `submateries_internes` · `nivell_acces` · `us_assistents` ·
`motiu_exclusio` · `canonica` · `versio_idiomatica_de` · `estat_vigencia` ·
`vigencia_validada_per` · `vigencia_validada_el` · `revisat_per` · `revisat_el` ·
`data_revisio_prevista` · `original_pdf_sha256` · `converter`

Tres reglas de validación que rechazan el paquete antes de ingerir nada:

- `content_class: regulation` **exige** `revisat_per` y `revisat_el`.
- `us_assistents: no` **exige** `motiu_exclusio` — que quedar fuera del índice sea una decisión
  auditable y no un silencio.
- `ambit_principal` y las submaterias se validan contra el vocabulario, y el error **enumera todos**
  los códigos no reconocidos con el fichero en que aparecen, no el primero que falla.

`versio_idiomatica_de` lleva la **referencia** de la versión canónica (su `id_publicacio`), no un
identificador de base de datos: al escribir el `.md` ese id no existe todavía.

### El front-matter es un artefacto derivado

Conviene separar dos papeles que no son el mismo:

| Papel | Quién |
|---|---|
| **Maestro de autoría**: donde una persona etiqueta y revisa | El catálogo (CSV hoy; la BD de publicación después) |
| **Portador de transporte**: lo que viaja con el contenido y lee el hub | El front-matter, **generado por script** |

El etiquetado vive en la tabla y no en los 380 YAML por una razón de revisión: en una tabla se
puede ordenar por ámbito y **ver la distribución**, que es lo que permite detectar de un vistazo el
fallo medido en el informe de materias —3 documentos etiquetados «Gestió econòmica» frente a 121
seleccionados por la vicegerencia—. Repartido en 380 ficheros, ese error es invisible.

**Regla: el front-matter no se edita a mano.** Una corrección hecha en el `.md` la pierde la
siguiente regeneración; las correcciones van a la fuente. Y regenerarlo es gratis para el hub:
como el hash se calcula sobre el cuerpo (§3), reemitir el front-matter —idéntico o distinto— no
dispara reingesta, re-troceado ni re-embedding.

### Dos hitos, no uno

De la lista de campos sale una secuencia útil, porque **no todo depende de que Secretaría General
valide el vocabulario**:

- **Hito A, sin SG** — `url_oficial`, `title`, `language`, `content_class` + `revisat_per`/`revisat_el`,
  `nivell_acces`/`us_assistents`, `canonica`/`versio_idiomatica_de`, `rang`,
  `data_revisio_prevista`. Con esto el corpus **carga, cita con enlace correcto y respeta el nivel
  de acceso**. Recuperable, todavía no enrutable por submateria.
- **Hito B, con SG** — `ambit_principal`, `ambits_secundaris`, `submateries`,
  `submateries_internes`, `resum_router`, `preguntes_tipus`, `termes_bilingues`. Con esto funcionan
  los Niveles 0-2.

Pasar de A a B es una edición del catálogo, regenerar y volver a cargar: el reconciliador lo
reporta como «metadatos actualizados» y **no re-embebe nada**.

> Precisión que ahorra un malentendido: **`resum` ≠ `resum_router`**. El resumen abstractivo del
> catálogo está escrito para el buscador del portal; el `resum_router` debe decir objeto + a quién
> se aplica + qué resuelve. Y **`perfil` ≠ `nivell_acces`**: `perfil` es el eje de destinatario
> (`aplica_a`), no el control de acceso.

### Mapeo desde el catálogo existente

Para el corpus histórico, los metadatos que ya existen salen de
`normativa_propia/cataleg_metadades_amb_resum.csv`:

| Columna del catálogo | Campo del front-matter |
|---|---|
| `id` | `id_publicacio` |
| `fitxer` | ruta del `.md` |
| `titol` | `title` (también es el origen del `#`, §2.1) |
| `idioma` | `language` |
| `estat_vigencia` | `estat_vigencia` (tal cual, incluido `vigent?`) |
| `tipus`, `organ_emissor`, `data_aprovacio`, `resum_abstractiu` | claves libres → `doc_metadata` |
| `n_caracters` | se descarta (derivado) |
| `materia`, `categoria_actual` | **clave libre, NUNCA `ambit_principal` ni `submateries`** |

La última fila es la importante. El eje `materia` actual mezcla cuatro ejes —colectivo, función,
unidad orgánica e instrumento—, y de ahí que «Gestió econòmica» tenga 3 documentos de 314 cuando la
vicegerencia seleccionó 121. Mapearlo automáticamente al ámbito importaría esa incoherencia al
corpus indexado. Se conserva como `materia_antiga` para trazabilidad, y la clasificación nueva se
etiqueta aparte.

---

## 4. Anclas

### 4.1 Sintaxis y las dos reglas que las hacen servir

`{#ancla}` al final de la línea del encabezado, separado por un espacio. Es la sintaxis de atributos
de Pandoc / kramdown / `markdown-it-attrs`: **si el generador de HTML usa cualquiera de esos, el
`id="art-14"` sale del mismo token sin trabajo adicional.**

**1. El ancla se deriva del NÚMERO, nunca de la rúbrica.** `{#art-14}`, no
`{#import-de-la-dieta}`. Si mañana «Import de la dieta» pasa a «Quantia de la dieta», los enlaces
publicados siguen funcionando.

**2. El ancla es la MISMA en las dos versiones idiomáticas.** «Article 14» y «Artículo 14» son ambos
`{#art-14}`. Así una cita resuelve contra cualquiera de las dos versiones, y el prefijo neutro
(`art`, `da`, `annex`) es lo que lo permite.

### 4.2 Prefijos

| Elemento | Prefijo | Ejemplo |
|---|---|---|
| Artículo | `art-` | `art-14`, `art-23-sexies` |
| Artículo dentro de un anexo | `annex-<n>-art-` | `annex-1-art-1` |
| Disposición adicional | `da-` | `da-1` |
| Disposición transitoria | `dt-` | `dt-2` |
| Disposición derogatoria | `dd-` | `dd-1` |
| Disposición final | `df-` | `df-1` |
| Preámbulo / Exposición de motivos | `preambul` | `preambul` |
| Anexo | `annex-` | `annex-1`, `annex-b`, `annex-3-2` |
| *(Enmienda 5a)* Apartado de la parte dispositiva de una resolución | `res-` | `res-2` |
| *(Enmienda 5b)* Unidad con etiqueta ordinal que **es** el articulado | `norma-` | `norma-1` |
| *(Enmienda 9)* División numerada en documento sin articulado | `div-` | `div-3` |

Los tres prefijos nuevos son nomenclatura, no diseño: cualquier par de códigos neutros sirve
siempre que se derive del número. Se fijan aquí para que no deriven en el tiempo.

### 4.3 Cómo se resuelven las formas ambiguas

**El contexto, no la forma, decide el prefijo.** Tres casos que el corpus produce y que se parecen:

| Forma en el `.md` | Contexto | Prefijo |
|---|---|---|
| `Segona. Limitació al gasto` | dentro de un grupo `## Disposicions addicionals` | `da-2` *(enmienda 6)* |
| `Segona. Utilització dels elements` | fuera de un grupo de disposiciones, y los ordinales son el articulado | `norma-2` *(enmienda 5b)* |
| `1. Presentació` | hay un artículo abierto | **apartado**: se queda como contenido |
| `3. Conductes contràries a la integritat` | documento sin articulado | `div-3` *(enmienda 9)* |

> *(Enmienda 6.)* Cuando una disposición aparece con el ordinal solo —la etiqueta se elide a partir
> de la segunda dentro del grupo— hereda la clase del encabezado de grupo que la precede.

Sin la distinción por contexto de la última fila, los 137 casos de `N. Rúbrica` del corpus se
resuelven todos mal en un sentido o en el otro.

### 4.4 Las divisiones estructurales NO llevan ancla

> *(Enmienda 7, opción (a).)* Título, capítulo y sección **no llevan ancla**.

Motivo medido: en el `Reglamento de selección del PDI`, `CAPÍTULO I` aparece tres veces, una por
título, y el contrato scopeaba las secciones por capítulo pero no los capítulos por título. Con las
anclas estructurales suprimidas, las anclas duplicadas del corpus bajaron de **127 a 21**, y en la
medición actual quedan **11**, todas del cuerpo y legítimas: documentos con preámbulo y exposición
de motivos a la vez, y numeración repetida en el original.

No se pierde nada: las divisiones no son destino de cita, y **el hub reconstruye la ruta del texto
del encabezado**, no del ancla. Verificado sobre el corpus convertido.

### 4.5 Normalización del número

- **Romanos a árabes**: `Títol III` → `3`; `Annex II` → `annex-2`.
- **Ordinales en palabra a cifra**: `Disposició addicional primera` → `da-1`; `segona` → `da-2`.
  Hace falta la tabla primera…dècima en valenciano y castellano.
- **Única**: `Disposició final única` → `df-1`.
- *(Enmienda 3.)* **Sufijos de artículo**, serie completa: `bis, ter, quater, quinquies, sexies,
  septies, octies, nonies`. `Article 23 sexies` → `art-23-sexies`. Sin la serie completa cae como
  artículo 23 y colisiona con el 23 real.
- *(Enmienda 2.)* **Anexos**: con letra, la letra es el identificador y se conserva en minúscula
  (`ANNEX B` → `annex-b`; convertirla a número haría que A y B compartieran ancla). Los subanexos se
  scopean con el padre (`ANNEX III. 2` → `annex-3-2`). Sin identificador, `annex-1`.

  *Aviso de implementación*: detectar la letra exige que sea un identificador **aislado**. Con un
  patrón laxo, `ANNEX Titulacions de la Facultat…` captura la «T» y produce `annex-t`.
- Todo en **minúsculas**, sin acentos, separando con `-`.

### 4.6 `Artículo 5.5` no es el artículo 5

> *(Enmienda 4. Es la enmienda más importante de las quince: produce anclas **falsas**, no
> ausentes.)*

**El número del artículo no puede ir seguido de punto y dígito.** `Artículo 5.5` es un apartado
numerado y **no lleva ancla**. Un patrón ingenuo clasifica `Artículo 5.5`, `5.6` y `5.7` como
artículo 5 y «resuelve» las colisiones con `art-5-2`, `art-5-3`…, con lo que **una cita a `art-5`
puede resolver a un apartado equivocado**. Un ancla ausente degrada; un ancla falsa engaña.

### 4.7 Unicidad

**El ancla debe ser única dentro del documento, y el conversor debe abortar si detecta un
duplicado.** Es lo que evita que un enlace publicado apunte a dos sitios.

Los artículos y las disposiciones del cuerpo se numeran de corrido, así que `art-14` ya es único.
Los **artículos dentro de un anexo no**: reinician la numeración, y por eso se scopean con el anexo
(§4.2, enmienda 1).

**Ante una colisión hay dos regímenes, y el prefijo decide cuál.**

- Las anclas del cuerpo —`art-`, `da-`, `annex-`, `preambul`— se **desambiguan** con sufijo `-2`,
  como dice el §5: los dos elementos existen de verdad y ambos han de ser alcanzables.
- Las oportunistas de esta versión —`div-`, `res-`, `norma-`— se **descartan**. Un `div-1-2` no
  corresponde a ninguna cita real: nadie escribe «la división 1-2». Vale más no emitirla —§0.1: un
  ancla que falta degrada a citar el documento— que inventar una que engaña (§4.6). En la medición
  actual se descartan 13 por esta regla.

Y el separador tras el número **es obligatorio** para reconocer una división numerada. Con el
separador opcional, `1 Benchmarking de la Universitat de Kent www.kent.ac.uk/…` —que es una nota al
pie— recibía `{#div-1}`.

### 4.8 Desempate por cuerpo: quién se lleva el ancla limpia

> **Decidido el 2026-07-29** a partir de un hallazgo en el `Reglament per a la concessió de
> distincions`, donde un resto de índice se llevaba `{#dd-1}` y la disposición derogatoria real
> quedaba en `{#dd-1-2}`: una cita a `dd-1` aterrizaba en el índice.

El §4.7 desambigua las colisiones con sufijo, pero **no dice quién se queda el ancla limpia**, y por
omisión decide el **orden de aparición**. Cuando el que aparece primero es un resto de índice, el
orden premia al equivocado.

**Regla: ante una colisión, el ancla limpia va al que tiene cuerpo.**

| Situación | Qué se hace |
|---|---|
| Exactamente uno de los que colisionan tiene cuerpo | Ese se lleva el ancla limpia. Los demás **conservan su encabezado y pierden el ancla** |
| Dos o más tienen cuerpo | Es el duplicado real del §5: ancla limpia al primero, `-2`, `-3`… al resto |
| Ninguno tiene cuerpo | Decide el orden, como hasta ahora. Ninguna cita queda peor |

El perdedor pierde el ancla y no un `-2` por dos razones: un ancla sobre un resto de índice es un
destino de enlace que no lleva a nada, y así **un sufijo `-N` en la salida pasa a significar una sola
cosa** —numeración duplicada de verdad en el original— en vez de ser ambiguo.

**Por qué esta regla no repite el error de los 39 encabezados.** La regla que destruyó contenido era
«un encabezado sin cuerpo es una entrada de índice, degrádalo», y se aplicaba a **cualquier
encabezado aislado**: por eso arrasó con artículos cuyo cuerpo se había perdido. Esta solo se activa
**cuando dos encabezados chocan en el mismo ancla**, no reclasifica nada y no borra nada —el
perdedor sigue siendo un encabezado—. Un encabezado sin cuerpo que no colisiona con nadie **no la
activa nunca**: conserva su nivel y su ancla, y quien lo señala es la puerta de calidad del §7 como
posible pérdida de contenido, que es donde tiene que salir.

**Alcance medido** sobre `md_contracte` (229 documentos), con la regla ya implementada: **11
colisiones con sufijo, 1 desempatada** por esta regla —el caso que la motivó— y **10 que son
duplicado legítimo**, los dos con cuerpo y régimen §5 sin cambios. Cero colisiones sin cuerpo en
ninguno de los dos lados. La regla corrige exactamente un caso y no toca los demás.

El conversor lo reporta en la parte no bloqueante del §7, con el ancla, el perdedor y su línea, para
que un aumento de esta cifra se vea: si un día desempata veinte, lo que ha cambiado es la calidad de
la conversión, no esta regla.

**Umbral de «tiene cuerpo».** Aquí es **más permisivo** que el de la puerta del §7 (10 caracteres
visibles frente a 40), y es deliberado: la puerta busca contenido perdido y le conviene ser sensible,
mientras que aquí un falso negativo le quitaría el ancla a una unidad legítima. Con 10, un resto de
índice —que no tiene cuerpo en absoluto— se distingue de un artículo de cuerpo corto, que la conserva.

---

## 5. Casos límite

| Caso | Qué hacer |
|---|---|
| Norma sin ninguna división (solo artículos) | Los artículos van a `#####` igual. No se inventan títulos ni capítulos. |
| Artículo derogado que se conserva | Se conserva el encabezado y su ancla, con el texto «(derogat)» en el cuerpo. Retirar el encabezado rompería enlaces publicados. |
| Artículo sin rúbrica | `##### Article 7 {#art-7}`. La rúbrica es opcional; el número no. |
| Numeración duplicada en el original | Se conserva la del original y se desambigua el ancla con sufijo `-2`, dejando nota en el cuerpo. No se renumera la norma. |
| **Anexo con articulado** *(enmienda 1)* | Un anexo **puede** contener artículos, y cuando los contiene **reinician la numeración**. El anexo es `##`, sus artículos `#####`, y las anclas se scopean: `{#annex-1-art-1}`. Se citan así en la práctica: «l'article 1 de l'Annex I». Son 3 documentos y 190 anclas. |
| Anexo con divisiones que no son artículos | El anexo es `##` y sus divisiones internas `###`/`####`. |
| **Documento sin articulado** *(enmienda 9)* | Las divisiones de primer orden **son** las unidades citables: `##` con ancla `div-<n>` derivada de su número. Si la división no está numerada, no lleva ancla. Son 40 documentos y 178 divisiones, y varias se citan de verdad. |
| **Documento bilingüe a dos columnas** *(enmienda 13)* | Se parte en dos ficheros, uno por lengua, con las mismas anclas. El fichero nuevo recibe un id **derivado del de su hermana con sufijo de lengua** (`CNV-001-val`, `REG-127-es`) y las dos fichas se enlazan. **No se usa el primer número libre de la serie**: `CNV-002`, `REG-008` y `REG-012` ya están ocupados por normas distintas en el catálogo global de 314 fichas, y reutilizarlos colisiona al unificar catálogos. Si las dos versiones se publican como documentos separados en el portal es decisión del propietario del conjunto publicable. |

---

## 6. Tablas

El problema original: el contenido de las tablas complejas vivía **solo** en el sidecar
`.tables.json`, y el `.md` llevaba únicamente un `<!-- TABLE-IMG -->`. Para el asistente eso son
datos invisibles, sin aviso, y afecta de lleno a lo que Gerencia consulta a diario (precios
públicos, RLT, importes de dietas).

El requisito es **que el dato tabular esté presente como texto**. No que esté en un formato
concreto. (La versión 1 exigía `<table>` HTML; era un argumento de procedencia —el HTML es lo que
había en el sidecar— disfrazado de argumento de recuperación.)

### Forma canónica: el bloque `TABLA-TEXT`

```
<!-- TABLE-IMG: img/<doc>/t01.png | page=21 2x6 -->

<!-- TABLA-TEXT: t01.png | pàg. 21 | 2x6 | markdown -->
**Retribucions del professorat permanent laboral**
| Sou | Complement de destinació (CD) | Complement específic (CE) |
| --- | --- | --- |
| 1.288,31 € | 924,48 € | 294,95 € |
<!-- /TABLA-TEXT -->
```

Tres propiedades de las que depende que el chunker haga su trabajo:

1. **Bloque delimitado** con apertura y cierre. Permite tratar la tabla como unidad en vez de como
   texto suelto que se corta por donde caiga.
2. **Procedencia en la cabecera**: PNG de origen, página y dimensiones. El hub las lleva a
   `chunk_metadata`, de modo que una cita puede decir de qué tabla y de qué página sale un importe.
3. **Formato declarado** (`markdown` | `html`) como último campo. Los dos conviven y el chunker
   ramifica según lo declarado; no se adivina mirando el contenido.

**La leyenda va dentro del bloque**, como en el ejemplo. Convierte un bloque de importes anónimos en
algo recuperable por su asunto, y el hub la repite en cada fragmento cuando parte la tabla. La fila
de cabecera es la que **precede al separador** `| --- |`, no la primera línea del bloque.

### Qué formato usar

| Caso | Formato |
|---|---|
| Tabla rectangular (misma estructura en todas las filas) | **`markdown`** (pipe table) |
| Celdas combinadas (`colspan`/`rowspan`), cabeceras a varios niveles, tabla anidada | **`html`** |

**El pipe table es el formato por defecto** y cuesta menos: medido sobre una tabla de 42×11 del
corpus, 1.311 tokens en pipe contra 2.087 en HTML (**×1,59**; el factor sube en tablas estrechas,
donde el marcado domina). El ahorro pesa doble, porque el Nivel 2 inyecta documentos enteros y el
presupuesto de contexto decide si una norma cabe.

El HTML se reserva a lo que los pipes **no pueden expresar**: una tabla con celdas fusionadas
volcada a pipes o pierde información o obliga a repetir valores, y las dos cosas producen respuestas
equivocadas sobre importes.

### El troceado lo resuelve el hub

Los bloques que superan el presupuesto de fragmento se parten **por filas repitiendo leyenda y
cabecera** (ING.0.4). Del lado del `.md` solo hacen falta el bloque delimitado y el formato
declarado.

---

## 7. Puerta de calidad del conversor

Antes de dar un documento por convertido. La primera lista es **bloqueante**; la segunda **reporta y
no bloquea**.

### Bloqueante

- [ ] Exactamente un `#` en el fichero, y es el título del catálogo (§2.1).
- [ ] Ningún ancla duplicada en el documento.
- [ ] Ningún ancla derivada de la rúbrica en lugar del número.
- [ ] *(Enmienda 4.)* Ningún ancla de artículo derivada de un `Artículo N.M`.
- [ ] *(Enmienda 14.)* **Ninguna unidad citable sin cuerpo.** Detecta el contenido perdido en la
      conversión, que es el defecto que importa (§0.3). Se mide **sobre la salida**, no sobre la
      entrada, y con la definición del Anexo A. Hoy son **8**. La pérdida real de articulado se
      cuenta aparte y son 3 documentos, no 3 de estas 8.
- [ ] *(Enmienda 14.)* **Ninguna unidad citable repetida con cuerpo** (índice mal degradado, §2.3).
- [ ] Ningún artículo marcado con negrita en lugar de encabezado.
- [ ] Ningún `<!-- TABLE-IMG -->` sin su bloque `TABLA-TEXT` al lado.
- [ ] Todo bloque `TABLA-TEXT` declara su formato, y el `html` se usa solo donde hay celdas
      combinadas o cabeceras a varios niveles.
- [ ] El recuento de artículos coincide con el del documento original.

### Reporta, no bloquea

- [ ] *(Enmienda 14.)* **Unidades con ancla ausente**, contadas **por clase de elemento y no solo
      por nivel**. Contar solo los `#####` deja un agujero por el que se colaron las anclas de anexo
      al caer de 279 a 19 sin disparar la puerta. Con las anclas oportunistas (§0.1) esto es una
      métrica de cobertura, no un fallo.
- [ ] *(Enmienda 14.)* **Paridad de anclas entre versiones idiomáticas.** Es un **detector, no una
      puerta**: puede fallar legítimamente cuando el original está incompleto. Encontró 16 artículos
      presentes en una lengua y ausentes en la otra —15 estaban en el documento como texto plano sin
      reconocer y uno falta de verdad en el DOGV castellano—, que es exactamente el defecto del §0.3.
- [ ] **Colisiones de ancla resueltas por el §4.8**: cuántas hubo, y en cuántas el perdedor era un
      encabezado sin cuerpo. Es el sustituto de endurecer la detección de la región de índice
      (§2.3): si el patrón crece, aquí se ve. Hoy: 11 colisiones, 10 duplicado legítimo, 1 resto de
      índice.
- [ ] **Encabezado que casa con dos patrones de unidad citable a la vez** —`DISPOSICIÓ DEROGATÒRIA
      DISPOSICIÓ FINAL` en una sola línea— es señal de alta precisión de que dos entradas de índice
      se fusionaron. Reporta: no siempre lo es, pero merece un ojo.

> **Advertencia metodológica, aprendida en este trabajo.** Comparar texto **ignorando espacios** no
> puede detectar una corrección cuyo único contenido es un espacio. Una corrección que pedía añadir
> un salto de línea entre la rúbrica y el cuerpo se dio por satisfecha porque el texto sin espacios
> coincidía; el defecto sobrevivió y lo encontró después la comprobación de paridad, por otra vía.

El hub tolera un `.md` sin anclas y sin jerarquía —`ancora=None` y la ruta que haya—, así que un
documento imperfecto entra igual. Eso es deliberado: permite que el corpus entre por fases en vez de
todo o nada.

---

## 8. Consolidación y desplazamiento

> **Estado de esta sección (2026-08-01).** El contrato venía citando el **§8.3** en su Anexo A
> y el **§8.13** en el §7, pero el §8 no existía en el documento: las clases de consolidación
> se estaban aplicando sin sección normativa que las definiera. Lo que sigue redacta lo que
> está **implementado y en uso**. Los apartados §8.1 a §8.12 —el régimen general de la
> consolidación: qué acto la origina, cómo se registra, cómo se numeran las notas al pie de
> las que se extrae— **siguen pendientes de redacción**, y hasta que se escriban la referencia
> del Anexo A al «§8.3» hay que leerla como una referencia a esta sección en su conjunto.

### 8.3 Clases de estado (las que hay en uso)

Se aplican al encabezado de la unidad citable, junto al ancla:
`##### Article 9. Mandat {#art-9 .desplacat}`.

| Clase | Qué afirma | Qué acto la origina |
|---|---|---|
| `.suprimit` | el texto fue **suprimido** por un acto posterior | un acto que modifica la norma |
| `.modificat` | el texto fue **modificado** por un acto posterior | un acto que modifica la norma |
| `.afegit` | el texto fue **añadido** por un acto posterior | un acto que modifica la norma |
| `.desplacat` | el texto **sigue siendo el aprobado**, pero su contenido ha quedado desplazado por una norma posterior de rango superior | **ninguno**: es *lex superior* (§8.13) |

Las tres primeras describen cambios hechos **a** la norma. La cuarta no: nadie ha tocado la
norma. Esa es la frontera que separa el §8.13 del resto de la sección.

**Las clases son acumulables, y `.modificat` con `.desplacat` es el caso normal.** Un artículo
puede haber sido modificado por un acuerdo de 2019 y estar desplazado hoy por los Estatutos de
2025: son dos hechos distintos y los dos son ciertos. Suprimir uno para poder anotar el otro
falsearía la historia del artículo. Se escriben las dos:
`{#art-6 .modificat .desplacat}`.

La única combinación que hay que mirar antes de escribirla es `.suprimit` con `.desplacat`: un
artículo suprimido no tiene contenido que pueda quedar desplazado, así que ahí lo más probable
es que una de las dos anotaciones esté mal.

### 8.3.1 Cuándo el desplazamiento deja de ser un caso y pasa a ser una familia

El §5 fija el criterio general —por debajo de unas pocas docenas de casos, registrar sale mejor
que generalizar— y el desplazamiento por los Estatutos de 2025 lo desborda: **no es un caso, es
una categoría**. Los reglamentos de departamento dicen todos lo mismo y todos chocan con el
mismo artículo de los Estatutos.

La **familia es el artículo de los Estatutos que desplaza**, no una etiqueta temática. Es un
criterio objetivo y tiene la propiedad que importa: si lo que desplaza es lo mismo, la nota
debe decir lo mismo. Un artículo de la norma superior con **tres o más documentos afectados**
forma familia y comparte el texto de la nota; por debajo va individual.

Lo que **no** cambia al agrupar: la nota sigue yendo **dentro de cada artículo**. Agrupar sirve
para no escribir la misma frase cuarenta veces —y para no tener una errata en la trigésima
séptima—, no para ahorrarse la nota en el chunk. La razón del §8.13 no se debilita porque haya
muchos casos: es justamente al contrario.

### 8.13 Artículo desplazado por norma superior posterior

**El supuesto.** Un artículo **vigente**, cuyo texto **nadie ha modificado**, cuyo contenido ha
quedado desplazado por una norma **posterior y de rango superior**. No hay acto modificativo:
no existe acuerdo, resolución ni disposición que haya tocado la norma. Es *lex superior*.

El caso que lo motiva: el `art-9.1` del Reglamento de la Sindicatura de Greuges (REG-048) fija
el mandato en cinco años; el `art-128.4` de los Estatutos de 2025 lo fija en seis. El
reglamento sigue vigente y su artículo 9 sigue diciendo cinco.

**Por qué necesita clase propia.** Etiquetarlo `.modificat` afirmaría que alguien modificó la
norma, que es falso, e invitaría a buscar el acuerdo inexistente. Etiquetarlo `.suprimit`
afirmaría que el artículo no está en vigor, que también es falso: está en vigor y es aplicable
en todo lo que no contradiga la norma superior. Clase: `.desplacat`. Relación en el front
matter: `desplacat_per`, con la norma superior, su ancla, su apartado y su fecha.

**Dónde va la nota, y por qué no solo en el front matter.** La nota editorial va **dentro del
cuerpo del artículo**. El front matter es de **documento** y el chunk del RAG es de
**artículo**: un agente que recupere `art-9` no ve la cabecera del documento, y responde
«cinco años» con total seguridad y sin ninguna señal de que la respuesta está desplazada. La
nota tiene que viajar **dentro del trozo** que el buscador devuelve.

Forma: un bloque delimitado (`::: nota-vigencia` … `:::`) tras la rúbrica, **en la lengua del
documento** —cada versión lingüística recibe su propia redacción—, marcado como editorial para
que el lector humano vea que no es texto aprobado.

**Consecuencia para el §7.** La nota es texto que el conversor **añade**, así que la
comprobación de «el cuerpo no ha perdido nada» debe excluirla. La primera implementación no lo
hacía y abortó dos documentos por una pérdida de texto inexistente.

**Consecuencia para los bilingües (§10).** El bloque `desplacat_per` se emite en **las dos**
versiones. La declaración lleva un `slug` y un `versio_castellana.slug`; leer solo el primero
deja la versión castellana con la clase en el cuerpo y sin el bloque en la cabecera, que es la
incoherencia más difícil de detectar porque cada capa, por separado, parece correcta.

**Lo que NO se hace: buscarlo por patrón.** De las 229 normas propias, 199 son anteriores a los
Estatutos de 2025-12-18 y 149 los citan en su texto. Es una categoría, no un caso aislado. Y
aun así no se busca automáticamente: decidir que un artículo está desplazado exige leer las dos
normas y comparar el contenido, no detectar una cita. Un falso positivo publica una advertencia
de vigencia **falsa** sobre un artículo correcto, que es peor que no advertir nada. Cada
desplazamiento se **declara**, con su motivo escrito. Es el modelo del §5: por debajo de unas
pocas docenas de casos, registrar sale mejor que generalizar.

### 8.14 Anclas declaradas a mano

**El supuesto.** La rúbrica de la disposición transitoria segunda de los Estatutos ha perdido
la «S» inicial en el PDF oficial y en el cuerpo dice «egunda. Continuidad de cargos» (en el
índice del propio PDF sí figura completa). El conversor no puede reconocerla, y sin
reconocerla no hay ancla.

El texto **no se toca**: la errata es del original y se publica como está. El ancla sí se pone,
porque el §4.1 exige que las anclas sean **idénticas entre las dos versiones lingüísticas**, y
la versión valenciana sí tiene su `dt-2`. Sin esto, una cita de la transitoria segunda funciona
en valenciano y falla en castellano.

**Verificaciones, las tres obligatorias.** El texto declarado coincide con **exactamente un**
encabezado del documento; ese encabezado **no** tiene ya ancla; el ancla **no** existe ya en el
documento. Si falla cualquiera, no se pone y se avisa.

**Límite deliberado.** Solo cuando la causa es un defecto del documento **original**. Si el
ancla falta porque nuestro patrón es corto, se arregla el patrón: un ancla declarada para un
caso que se repetirá es un apaño que caduca. Precedente: los apartados `I.-` / `II.-` de las
circulares no se declararon uno a uno, se añadió la serie romana al reconocimiento del número
(§4.5), y el arreglo sirvió para todo el corpus.

---

## Anexo A — Cifras de referencia

> *(Enmienda 15.)* Las cifras del cuerpo del contrato eran una instantánea y quedaron obsoletas al
> partir los bilingües. Se recogen aquí, fechadas, y el texto normativo no depende de ellas.

Medido sobre `publicacio_transparencia_2026-07/md_contracte/` el **2026-07-30**, después de importar
del DOGV los 6 documentos que se publicaron a dos columnas:

| Magnitud | Valor |
|---|---|
| Documentos | 229 (eran 226 antes de partir 3 bilingües) |
| Caracteres visibles del corpus | 6.089.248 |
| Encabezados por nivel | `#` 229 · `##` 1.093 · `###` 902 · `####` 316 · `#####` 5.664 |
| Anclas emitidas | **5.952** |
| Anclas por prefijo | `art` 4.774 · `da` 265 · `df` 174 · `annex` 172 · `preambul` 157 · `dt` 144 · `dd` 136 · `norma` 87 · `div` 39 · `res` 4 |
| Cobertura de ancla por clase | artículo/disposición 5.662/5.664 |
| Anclas duplicadas sin resolver | 0 |
| `id` emitidos en las 229 páginas HTML | 5.952 (uno por ancla) |
| Documentos sin articulado | 40 |
| Familias de regla decididas por el contrato | **12 de 12** |
| Bloques `TABLA-TEXT` | 52 |
| Clases de consolidación en uso (§8.3) | `.suprimit` 4 |
| Unidades citables sin cuerpo (**a corregir**) | **8** |
| Documentos con pérdida real de articulado (**a corregir**) | **3** |

### La importación desde el DOGV (2026-07-30)

Seis documentos se publicaron en el DOGV **a dos columnas**, valenciano y castellano en la misma
página, y el OCR de ese formato era el origen de la mayor parte del daño del corpus: **141 de los 190
encabezados de artículo perdidos** estaban en esos seis ficheros. El DOGV los ofrece en HTML con una
versión por lengua, de donde no hace falta OCR.

| Documento | Artículos antes → después | Caracteres |
|---|---|---|
| Estatuts (va) | 112 → **172** | +60.310 |
| Estatutos (es) | 151 → **172** | +30.135 |
| Admin. electrónica (va) | 41 → **62** | −1.619 |
| Admin. electrónica (es) | 41 → **62** | +992 |
| Convenio colectivo (va) | 59 → **82** | −5.288 |
| Convenio colectivo (es) | 58 → **82** | +2.941 |

**Los tres deltas negativos no son pérdida de contenido**, y comprobarlo fue el trabajo:

- En administración electrónica (va), el documento anterior contenía **2.724 caracteres de castellano**
  en 5 párrafos, restos de la partición de bilingües. El nuevo trae 1.105 caracteres más de valenciano
  real y suelta ese castellano.
- En el Convenio (va), de los 60 importes distintos del documento anterior **no se pierde ninguno**:
  los 13 que la comparación de multiconjuntos señalaba eran repeticiones que el doble columnado había
  duplicado (`1.236,60 €` ocho veces frente a cuatro).

**Y la paridad idiomática del §4.1, que no se cumplía**, queda resuelta en dos de los tres pares:

| Par | Antes | Ahora |
|---|---|---|
| Estatuts | `art-N` (es) frente a `annex-1-art-N` (va): **cero anclas comunes** | **172 = 172, completa** |
| Admin. electrónica | 41 y 41, estructura mal detectada | **62 = 62, completa** |
| Convenio colectivo | 59 y 58 | **82 = 82, completa** |

**La paridad se cierra en los tres pares.** El `art-164` que parecía faltar de la versión valenciana sí
está publicado, pero con una errata de la fuente: el DOGV escribe «**Articles** 164. Dret de sufragi»,
en plural, y así aparece tanto en el índice como en el cuerpo. El patrón de `RE_ARTICLE` tolera ahora el
plural **sin tocar el texto**, con un guardián que excluye el plural legítimo —«Articles 5 i 6 queden
redactats»— porque tras el número lleva conjunción y otro número. Medido: en todo el corpus hay 2
ocurrencias del plural, las dos de esta errata.

Y el `art-19` del Convenio, que se daba por ausente del DOGV castellano, **está en las dos lenguas**: era
un defecto de la versión OCR, no de la publicación oficial.

**Lo que ninguna vía de extracción recupera** son las tablas retributivas del artículo 51 del Convenio:
en el DOGV van como imagen, así que el `.txt` del portapapeles y la impresión a PDF dan los mismos 49
importes. Esas tablas solo pueden venir del corpus anterior, y por eso la importación **fusiona** en vez
de sustituir: reinserta un bloque `TABLA-TEXT` solo si aporta algún importe que el texto nuevo no tenga.

Las tres decisiones de prefijo de la versión 2 —`res-`, `norma-`, `div-`— aportan 134 anclas, y los
ordinales que caen dentro de un grupo de disposiciones resuelven por contexto a su propio prefijo
(§4.3): `da` +10, `dt` +3, `df` +1 respecto de la medición anterior.

**Sobre las unidades sin cuerpo: son 8, y la definición importa tanto como la cifra.**
Una discrepancia anterior de este documento (10 en un sitio, 11 en otro) venía de contar de dos
maneras distintas, así que la definición queda enunciada aquí: **encabezado `#####` con ancla y sin
ninguna línea de cuerpo hasta el siguiente encabezado**, excluyendo la nota editorial del §8.13.
Medido sobre `md_contracte` con el corpus al día, después de la importación del DOGV, las
promociones y la corrección del scope de anexo del Reglamento del Consell Social.

No se da la cifra sobre la entrada (`md/`) porque no es comparable: allí casi todo encabezado va
seguido de otro —los pares título/rúbrica que el conversor fusiona— y el recuento no mide lo mismo.

**Las 8 no son todas la misma cosa:**

| Caso | n | Qué necesita |
|---|---|---|
| Sin cuerpo, con rúbrica correcta | 5 | Comparar con el PDF y recuperar el texto |
| Sin cuerpo **y sin rúbrica**: solo conservan el número de página (`Artículo 2. 12`) | 3 | Recuperar enunciado y cuerpo. Los tres del Reglamento del Comité de Ética de la Investigación |

Ninguna de las 8 es pérdida real en el sentido de que el texto no exista en el original: son fallos
de extracción con el PDF disponible.

**Pérdida real de contenido: tres documentos, no tres unidades.** Es una categoría distinta y el
trabajo que exige también: aquí no falta un artículo, falta el articulado.

| Documento | Qué falta |
|---|---|
| **ALT-065** Reglamento de selección del PDI | 32.179 caracteres y **cero anclas de artículo**: solo están el Anexo I y el II de baremos |
| **ALT-034** Pedagogía | Empieza en el Títol II, artículo 5: faltan el preámbulo y los artículos 1 a 4 |
| **REG-030** Instituto López Piñero | Cortado en el artículo 12: faltan régimen económico, reforma y disposiciones |

El detalle por documento y línea de las 8 está en
`publicacio_transparencia_2026-07/articles_sense_cos.csv`.

---

## Anexo B — Trazabilidad de las quince enmiendas

| # | Enmienda | Dónde queda |
|---|---|---|
| 1 | Un anexo sí puede contener artículos | §4.2, §4.7, §5 |
| 2 | Anclas de anexo: letras y subanexos | §4.5 |
| 3 | Sufijos de artículo hasta *nonies* | §4.5 |
| 4 | `Artículo 5.5` no es el artículo 5 | §4.6, §7 |
| 5 | Dos tipos de unidad citable que faltaban | §2, §4.2, §4.3 |
| 6 | La etiqueta «Disposición» se elide | §4.3 |
| 7 | Anclas estructurales suprimidas (opción a) | §2, §4.4 |
| 8 | Número y rúbrica en un solo encabezado | §2.2 |
| 9 | Documentos sin articulado: prefijo `div-` | §4.2, §5 |
| 10 | Origen del `#` único: el catálogo | §2.1 |
| 11 | Índice convertido en encabezados | §2.3 |
| 12 | Cabeceras de página y aparato del DOGV | §2.3 |
| 13 | Partir un bilingüe: ids derivados | §5 |
| 14 | Comprobaciones nuevas, y cuáles no bloquean | §7 |
| 15 | Las cifras son una instantánea | Anexo A |
| — | *(posterior)* Desempate por cuerpo ante colisión de ancla | §4.8, §2.3, §7 |

**Lo que la propuesta pedía no cambiar, y no ha cambiado**: el principio de nivel por tipo (§1), el
artículo como unidad atómica (§2.3), la sintaxis `{#ancla}` de Pandoc (§4.1), el ancla derivada del
número e idéntica entre lenguas (§4.1), y que el hub tolere un `.md` imperfecto (§7).

**Fuera del contrato porque es contenido y no formato**: las 8 unidades citables sin cuerpo y los 3
documentos con pérdida real de articulado —ALT-065, ALT-034 y REG-030— (Anexo A).

Los 35 encabezados propios del DOCENTIA (`NORMA TÈCNICA 1..4`, `Dimensió I..III`) **ya no necesitan
una regla para ese documento**: no eran un caso especial, eran una regla mal puesta. La familia J
—«rúbrica dentro de artículo, degrádala a texto»— se había extendido a «dentro de artículo *o de
disposición*», y el estado es pegajoso: pasada la disposición final, toda la cola del documento lo
heredaba y perdía sus divisiones. Restringida a artículo, como decía la taxonomía, el DOCENTIA
recupera su estructura y con él otros 9 documentos, 23 encabezados en total.

La moraleja generaliza, y por eso queda escrita aquí: **antes de escribir una regla para un documento
que parece único, comprobar que no es una regla general que le está pasando por encima.** El §0.2 da
el comportamiento seguro por defecto —un encabezado que no encaja se queda donde está y no pasa
nada—, y degradar es siempre la opción que hay que justificar.

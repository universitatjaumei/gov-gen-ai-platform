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

**1. Las anclas son oportunistas, no obligatorias.** Se emiten donde el patrón es inequívoco —las
familias que este contrato decide sin ambigüedad, 752 de 1.115 encabezados en la medición actual— y
**no se fuerzan** en el resto. Su único consumidor es el enlace profundo de la cita, y un ancla que
falta degrada a citar el documento, que es lo que el hub ya hace. Verificado: con el corpus sin
anclas, 14.192 fragmentos y todo funcionando.

**2. La jerarquía por tipo se mantiene** (§1) porque es barata y resuelve el 78 % de los
encabezados con una tabla de correspondencias. Un encabezado que no encaje en ninguna familia se
queda en `##` y no pasa nada.

**3. Lo que sí es obligatorio es que el contenido esté completo.** Un artículo cuyo cuerpo se
perdió en la conversión falla en **todos** los modos de recuperación —inyección, RAG y cita— y es
el fallo que hunde un piloto en silencio, porque nadie descubre que falta hasta que el asistente
responde mal a alguien. En la medición actual son **40 artículos sin cuerpo** más el artículo 19 del
Convenio ausente del DOGV castellano. **Ese es el trabajo que paga**, por delante de cualquier
refinamiento de la taxonomía de encabezados.

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
anclas estructurales suprimidas, las anclas duplicadas del corpus bajaron de **127 a 21**.

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
| **Documento sin articulado** *(enmienda 9)* | Las divisiones de primer orden **son** las unidades citables: `##` con ancla `div-<n>` derivada de su número. Si la división no está numerada, no lleva ancla. Son 38 documentos y 178 divisiones, y varias se citan de verdad. |
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
      conversión, que es el defecto que importa (§0.3). Hoy son **40 artículos**.
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

> **Advertencia metodológica, aprendida en este trabajo.** Comparar texto **ignorando espacios** no
> puede detectar una corrección cuyo único contenido es un espacio. Una corrección que pedía añadir
> un salto de línea entre la rúbrica y el cuerpo se dio por satisfecha porque el texto sin espacios
> coincidía; el defecto sobrevivió y lo encontró después la comprobación de paridad, por otra vía.

El hub tolera un `.md` sin anclas y sin jerarquía —`ancora=None` y la ruta que haya—, así que un
documento imperfecto entra igual. Eso es deliberado: permite que el corpus entre por fases en vez de
todo o nada.

---

## Anexo A — Cifras de referencia

> *(Enmienda 15.)* Las cifras del cuerpo del contrato eran una instantánea y quedaron obsoletas al
> partir los bilingües. Se recogen aquí, fechadas, y el texto normativo no depende de ellas.

Medido sobre `publicacio_transparencia_2026-07/md_contracte/` el **2026-07-29**:

| Magnitud | Valor |
|---|---|
| Documentos | 229 (eran 226 antes de partir 3 bilingües) |
| Encabezados clasificados | 9.087 |
| Unidades citables con ancla | 5.582 |
| Documentos sin articulado | 38 |
| Familias de regla decididas por el contrato | 752 de 1.115 encabezados |
| Bloques `TABLA-TEXT` | 59 (49 `markdown`, 5 `html` en la medición anterior de 54) |
| Fragmentos que produce el hub | 12.044 |
| Artículos sin cuerpo (**a corregir**) | 40 |

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

**Lo que la propuesta pedía no cambiar, y no ha cambiado**: el principio de nivel por tipo (§1), el
artículo como unidad atómica (§2.3), la sintaxis `{#ancla}` de Pandoc (§4.1), el ancla derivada del
número e idéntica entre lenguas (§4.1), y que el hub tolere un `.md` imperfecto (§7).

**Fuera del contrato porque es contenido y no formato**: los 40 artículos sin cuerpo, el artículo 19
del Convenio ausente del DOGV castellano, y los 35 encabezados propios del DOCENTIA (`NORMA
TÈCNICA`, `Dimensió I`), que merecen una regla para ese documento antes que una regla general.

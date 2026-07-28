# Contrato del `.md` del corpus normativo

Especificación del Markdown que consume el asistente: **jerarquía de encabezados y anclas de
artículo**. Se aplica al corpus histórico y al que emita el pipeline de publicación.

Destinatarios: quien convierte el corpus existente y quien defina el generador de publicación
(el `.md` se guarda en la BD de publicación y de ahí salen el PDF y el HTML).

Consumidor en el hub: `MarkdownChunker` (`server/app/modules/agents_hub/ingestion/chunker.py`),
prompts **ING.0.3** (front-matter) e **ING.0.4** (jerarquía y anclas) de `Plan_TDD_Fase1.md`.

---

## 1. Principio que decide todo lo demás

**El nivel del encabezado lo determina el TIPO de elemento, no su anidamiento real.**

Un artículo es `#####` siempre: en una norma con Título > Capítulo > Sección y en una de doce
artículos sin ninguna división. Un capítulo es `###` aunque la norma no tenga títulos.

Esto se aparta de lo que haría un editor humano (que subiría de nivel lo que no está anidado) y
es deliberado, por tres razones:

1. **La conversión del histórico es una tabla de correspondencias, no un algoritmo con estado.**
   Los encabezados actuales están todos aplanados en `##`, pero llevan su etiqueta en el texto
   («Article 14», «Capítol III»). Con nivel fijo por tipo, el script lee la etiqueta y asigna el
   nivel. Con nivel por anidamiento habría que mantener una pila y decidir profundidades
   relativas: más código y más formas de equivocarse en 226 documentos.
2. **El chunker puede confiar en el nivel.** Si el artículo está siempre en el mismo nivel, el
   troceado es uniforme en todo el corpus. Si varía entre `##` y `#####` según la norma, el
   nivel deja de significar nada y hay que reconocer los artículos por su texto.
3. **Los saltos de nivel no son un problema.** Un `#####` justo debajo de un `##` es Markdown
   válido y el splitter lo trata bien: registra los encabezados que ve y descarta los niveles
   intermedios que quedaron atrás. No hay que rellenar huecos con encabezados vacíos.

---

## 2. Tabla de niveles

| Nivel | Elementos | Ancla | Ejemplo |
|---|---|---|---|
| `#` | Título del documento (**uno solo por fichero**) | no | `# Reglament sobre indemnitzacions per raó del servei` |
| `##` | Preámbulo · Título (Títol) · encabezado de grupo de disposiciones · Anexo | según §4 | `## Títol I. Disposicions generals {#tit-1}` |
| `###` | Capítulo | opcional | `### Capítol III. Dietes {#cap-3}` |
| `####` | Sección | opcional | `#### Secció 2a. Manutenció {#cap-3-sec-2}` |
| `#####` | **Unidad citable**: Artículo · Disposición concreta | **obligatoria** | `##### Article 14. Import de la dieta {#art-14}` |

Dos decisiones que conviene entender:

**Preámbulo, Título, Disposiciones y Anexo comparten el nivel `##`** porque son las divisiones de
primer orden de la norma, hermanas entre sí.

**Artículo y disposición concreta comparten el nivel `#####`** porque son la misma cosa a efectos
de cita y de recuperación: la unidad autónoma que se cita. El encabezado de grupo
(«Disposicions addicionals») es `##` y cada disposición dentro es `#####`.

### Lo que NO lleva encabezado

Los **apartados** de un artículo (`1.`, `2.`, `a)`, `b)`) se quedan como contenido —lista o
párrafo— dentro de su artículo. **El artículo es la unidad atómica.** Bajar de ahí multiplicaría
por diez el número de encabezados, dispararía el número de fragmentos y no mejora la cita: «art.
14.2» se resuelve leyendo el artículo 14.

Tampoco son encabezados: la fórmula de aprobación, los pies de firma, ni las notas al pie.

### Prohibido sustituir encabezados por negrita

Si un artículo se marca con `**Article 14.**` en lugar de un encabezado real, para el hub ese
artículo no existe como estructura: se pierde el nivel, la ruta y el ancla. Los encabezados son
`#`, y punto.

---

## 3. Esqueleto del fichero

```markdown
---
id_publicacio: REG-020
titol: Reglament sobre indemnitzacions per raó del servei i gratificacions
language: ca
ambit_principal: administracio
submateries: [indemnitzacions-i-dietes]
estat_vigencia: vigent
url_oficial: https://www.uji.es/...
---

# Reglament sobre indemnitzacions per raó del servei i gratificacions

## Preàmbul {#preambul}

Text del preàmbul...

## Títol I. Disposicions generals {#tit-1}

### Capítol I. Objecte i àmbit {#cap-1}

##### Article 1. Objecte {#art-1}

1. Aquest reglament regula...
2. Als efectes previstos...

##### Article 2. Àmbit d'aplicació {#art-2}

...

## Títol II. Indemnitzacions {#tit-2}

### Capítol III. Dietes {#cap-3}

#### Secció 2a. Manutenció {#cap-3-sec-2}

##### Article 14. Import de la dieta {#art-14}

...

## Disposicions addicionals

##### Disposició addicional primera. Actualització d'imports {#da-1}

...

## Disposicions finals

##### Disposició final única. Entrada en vigor {#df-1}

...

## Annex I. Quadre d'imports {#annex-1}

<table>...</table>
```

El front-matter va **antes** del `#`. El hub lo separa del cuerpo y **calcula el hash sobre el
cuerpo**, no sobre el front-matter: así reetiquetar una norma no dispara un re-troceado ni un
re-embedding, y cambiar el texto sí. Dos corolarios de la implementación (ING.0.3):

- Un `.md` que **gana** front-matter después conserva su hash y no se reingiere: la línea en
  blanco que separa el bloque del cuerpo es formato, no contenido.
- El hash **no depende del final de línea**: CRLF y LF dan el mismo. El corpus se produce en
  Windows y el sync puede entregarlo con LF; no debe reingerirse por eso.

### Claves del front-matter

No hace falta que el `.md` enumere los 56 campos del esquema, y tampoco hace falta que el hub los
conozca: **las claves que el contrato no declara van a `doc_metadata`** tal cual. Así el esquema
puede crecer sin tocar el código. Las que sí tienen tratamiento propio, porque gobiernan
recuperación, acceso o puertas de calidad:

`id_publicacio` · `title` · `language` · `content_class` · `ambit_principal` ·
`ambits_secundaris` · `submateries` · `submateries_internes` · `nivell_acces` ·
`us_assistents` · `motiu_exclusio` · `canonica` · `versio_idiomatica_de` ·
`estat_vigencia` · `vigencia_validada_per` · `vigencia_validada_el` · `revisat_per` ·
`revisat_el` · `data_revisio_prevista` · `original_pdf_sha256` · `converter`

Tres reglas de validación que rechazan el paquete antes de ingerir nada:

- `content_class: regulation` **exige** `revisat_per` y `revisat_el`.
- `us_assistents: no` **exige** `motiu_exclusio` — que quedar fuera del índice sea una decisión
  auditable y no un silencio.
- `ambit_principal` y las submaterias se validan contra el vocabulario, y el error **enumera
  todos** los códigos no reconocidos con el fichero en que aparecen, no el primero que falla.

`versio_idiomatica_de` lleva la **referencia** de la versión canónica (su `id_publicacio`), no un
identificador de base de datos: al escribir el `.md` ese id no existe todavía.

### Mapeo desde el catálogo existente

Para el corpus histórico, los metadatos que ya existen salen de
`normativa_propia/cataleg_metadades_amb_resum.csv`:

| Columna del catálogo | Campo del front-matter |
|---|---|
| `id` | `id_publicacio` |
| `fitxer` | ruta del `.md` |
| `titol` | `title` |
| `idioma` | `language` |
| `estat_vigencia` | `estat_vigencia` (tal cual, incluido `vigent?`) |
| `tipus`, `organ_emissor`, `data_aprovacio`, `resum_abstractiu` | claves libres → `doc_metadata` |
| `n_caracters` | se descarta (derivado) |
| `materia`, `categoria_actual` | **clave libre, NUNCA `ambit_principal` ni `submateries`** |

La última fila es la importante. El eje `materia` actual mezcla cuatro ejes —colectivo, función,
unidad orgánica e instrumento—, y de ahí que «Gestió econòmica» tenga 3 documentos de 314 cuando
la vicegerencia seleccionó 121. Mapearlo automáticamente al ámbito importaría esa incoherencia al
corpus indexado. Se conserva como `materia_antiga` para trazabilidad, y la clasificación nueva se
etiqueta aparte.

---

## 4. Anclas

### Sintaxis

`{#ancla}` al final de la línea del encabezado, separado por un espacio.

Es la sintaxis de atributos de Pandoc / kramdown / `markdown-it-attrs`. **Si el generador de HTML
usa cualquiera de esos, el `id="art-14"` del HTML sale del mismo token sin trabajo adicional.** Ese
es el argumento para elegir esta sintaxis y no un comentario o un `<a name>`.

### Las dos reglas que hacen que el ancla sirva

**1. El ancla se deriva del NÚMERO, nunca de la rúbrica.** `{#art-14}`, no `{#import-de-la-dieta}`.
Si mañana «Import de la dieta» pasa a «Quantia de la dieta», los enlaces publicados siguen
funcionando.

**2. El ancla es la MISMA en las dos versiones idiomáticas.** «Article 14» y «Artículo 14» son
ambos `{#art-14}`. Así una cita del asistente resuelve contra cualquiera de las dos versiones, y
el prefijo neutro (`art`, `da`, `annex`) es lo que lo permite.

### Prefijos

| Elemento | Prefijo | Ejemplo | Obligatoria |
|---|---|---|---|
| Artículo | `art-` | `art-14`, `art-14-bis`, `art-14-ter` | **sí** |
| Disposición adicional | `da-` | `da-1` | **sí** |
| Disposición transitoria | `dt-` | `dt-2` | **sí** |
| Disposición derogatoria | `dd-` | `dd-1` | **sí** |
| Disposición final | `df-` | `df-1` | **sí** |
| Preámbulo / Exposición de motivos | `preambul` | `preambul` | **sí** |
| Anexo | `annex-` | `annex-1` | **sí** |
| Título | `tit-` | `tit-2` | opcional |
| Capítulo | `cap-` | `cap-3` | opcional |
| Sección | `sec-` | `cap-3-sec-2` | opcional |

Obligatorias en las **unidades citables**; opcionales en las **divisiones estructurales**, que son
navegación y no destino de cita —y cuya ruta el hub reconstruye del texto del encabezado, no del
ancla—. Si decidís ponerlas también ahí, mejor: solo tened en cuenta la regla de unicidad.

### Normalización del número

- **Romanos a árabes**: `Títol III` → `tit-3`; `Annex II` → `annex-2`.
- **Ordinales en palabra a cifra**: `Disposició addicional primera` → `da-1`; `segona` → `da-2`.
  Hace falta la tabla primera…dècima en valenciano y castellano.
- **Única**: `Disposició final única` → `df-1`.
- **Bis / ter / quater**: sufijo con guion. `Article 14 bis` → `art-14-bis`.
- Todo en **minúsculas**, sin acentos, separando con `-`.

### Unicidad

**El ancla debe ser única dentro del documento, y el script de conversión debe abortar si detecta
un duplicado.** Es la comprobación que evita que un enlace publicado apunte a dos sitios.

Los artículos y las disposiciones se numeran de corrido en toda la norma, así que `art-14` ya es
único. Las **secciones no**: pueden repetirse en capítulos distintos («Capítol I, Secció 1a» y
«Capítol II, Secció 1a»). Por eso, si ponéis ancla a las secciones, **scopeadla con su capítulo**:
`cap-3-sec-2`.

---

## 5. Casos límite

| Caso | Qué hacer |
|---|---|
| Norma sin ninguna división (solo artículos) | Los artículos van a `#####` igual. No se inventan títulos ni capítulos. |
| Artículo derogado que se conserva | Se conserva el encabezado y su ancla, con el texto «(derogat)» en el cuerpo. Retirar el encabezado rompería enlaces publicados. |
| Artículo sin rúbrica | `##### Article 7 {#art-7}`. La rúbrica es opcional; el número no. |
| Numeración duplicada en el original | Se conserva la del original y se desambigua el ancla con sufijo `-2`, dejando nota en el cuerpo. No se renumera la norma. |
| Anexo con estructura interna | El anexo es `##` y sus divisiones internas `###`/`####`. Un anexo no contiene artículos. |
| Documento sin articulado (protocolos, planes) | Solo `#` y `##`, con las anclas que tengan sentido. Es válido: 41 de los 226 documentos son así. |
| Documento bilingüe a dos columnas | **Se parte en dos ficheros**, uno por lengua, con las mismas anclas. Indexar las dos lenguas juntas contamina la recuperación en ambas. |

---

## 6. Tablas

El problema original: el contenido de las tablas complejas vivía **solo** en el sidecar
`.tables.json`, y el `.md` llevaba únicamente un `<!-- TABLE-IMG -->`. Para el asistente eso son
datos invisibles, sin aviso, y afecta de lleno a lo que Gerencia consulta a diario (precios
públicos, RLT, importes de dietas).

El requisito, por tanto, es **que el dato tabular esté presente como texto**. No que esté en un
formato concreto. (La versión inicial de este documento exigía `<table>` HTML; era un argumento de
procedencia —el HTML es lo que había en el sidecar— disfrazado de argumento de recuperación.
Corregido el 2026-07-28 con el corpus ya convertido delante.)

### Forma canónica: el bloque `TABLA-TEXT`

```
<!-- TABLE-IMG: img/<doc>/t01.png | page=21 2x6 -->

<!-- TABLA-TEXT: t01.png | pàg. 21 | 2x6 | markdown -->
| Sou | Complement de destinació (CD) | Complement específic (CE) |
| --- | --- | --- |
| 1.288,31 € | 924,48 € | 294,95 € |
<!-- /TABLA-TEXT -->
```

Tres propiedades que el `.md` debe conservar, porque de ellas depende que el chunker haga su
trabajo:

1. **Bloque delimitado** con apertura y cierre. Es lo que permite tratar la tabla como unidad y no
   como texto suelto que se corta por donde caiga.
2. **Procedencia en la cabecera**: PNG de origen, página y dimensiones. El hub las lleva a
   `chunk_metadata`, de modo que una cita puede decir de qué tabla y de qué página sale un importe.
3. **Formato declarado** (`markdown` | `html`) como último campo. Los dos formatos conviven y el
   chunker ramifica según lo declarado; no hay que adivinar mirando el contenido.

### Qué formato usar

| Caso | Formato |
|---|---|
| Tabla rectangular (misma estructura en todas las filas) | **`markdown`** (pipe table) |
| Celdas combinadas (`colspan`/`rowspan`), cabeceras a varios niveles, tabla anidada | **`html`** |

**El pipe table es el formato por defecto** y cuesta menos: medido sobre una tabla de 42×11 del
corpus, 1.311 tokens en pipe contra 2.087 en HTML (**×1,59**; el factor sube en tablas estrechas,
donde el marcado domina). Y ese ahorro pesa doble, porque el Nivel 2 de la estrategia inyecta
documentos enteros y el presupuesto de contexto decide si una norma cabe.

El HTML se reserva a lo que los pipes **no pueden expresar**. Una tabla con celdas fusionadas
volcada a pipes o pierde información o obliga a repetir valores, y las dos cosas producen
respuestas equivocadas sobre importes.

### La cabecera de la tabla y el troceado

Medido sobre el corpus convertido: **30 de los 54 bloques superan los 1.000 caracteres**, que es el
`chunk_size` del chunker. Un bloque que no cabe se parte, y por defecto **todos los fragmentos
menos el primero pierden la fila de cabecera**: quedan importes sin nombre de columna, que es peor
que no tener el dato, porque se pueden recuperar y sostener una respuesta segura y falsa.

Eso **se arregla en el hub, no en el corpus** (ING.0.4: troceado consciente de tablas, que repite
la fila de cabecera en cada fragmento). Del lado del `.md` solo hacen falta dos cosas, y las dos
ya se cumplen: el bloque delimitado y el formato declarado.

Lo que sí conviene del lado del corpus: **preceder cada tabla de un encabezado o de una frase que
la nombre**. «Retribucions del professorat permanent laboral» delante de la tabla convierte un
bloque de importes anónimos en algo recuperable por su asunto.

---

## 7. Comprobaciones que debería hacer el conversor

Puerta de calidad del propio script, antes de dar un documento por convertido:

- [ ] Exactamente un `#` en el fichero.
- [ ] Ninguna unidad citable (artículo, disposición, anexo, preámbulo) sin ancla.
- [ ] Ningún ancla duplicada en el documento.
- [ ] Ningún ancla derivada de la rúbrica en lugar del número.
- [ ] Ningún artículo marcado con negrita en lugar de encabezado.
- [ ] Las dos versiones idiomáticas de la misma norma tienen el **mismo juego de anclas** (si no,
      o falta un artículo en una o hay un error de numeración).
- [ ] Ningún `<!-- TABLE-IMG -->` sin su bloque `TABLA-TEXT` al lado (a 2026-07-28: **54 de 54**).
- [ ] Todo bloque `TABLA-TEXT` declara su formato, y el `html` se usa solo donde hay celdas
      combinadas o cabeceras a varios niveles.
- [ ] El recuento de artículos coincide con el del documento original.

El hub tolera un `.md` sin anclas y sin jerarquía —`ancora=None` y la ruta que haya—, así que un
documento imperfecto entra igual. Pero pierde la cita por artículo, que es la mitad del valor.

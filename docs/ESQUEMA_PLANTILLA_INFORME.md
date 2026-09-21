# El esquema de una plantilla de informe, en prosa

> **Clase: referencia viva.** Escrita el 2026-09-21 leyendo el código, para quien va a **definir
> plantillas** y necesita entender qué le está proponiendo el modelo en `/redaccion/draft` y cómo
> corregirlo con criterio.
>
> **El contrato ejecutable es el JSON Schema**, no este texto: `GET /api/v1/hub/redaccion/template-schema`
> devuelve el `model_json_schema()` de `ReportTemplateSpec` sin retoques, con todos los submodelos
> alcanzables. Si este documento y ese esquema discrepan, el esquema tiene razón y este documento
> tiene un fallo que hay que arreglar.
>
> Para qué forma tiene que tener un informe y por qué, [`CASO_INFORME_SEGUIMIENTO.md`](CASO_INFORME_SEGUIMIENTO.md).
> Para el contrato del módulo entero, [`REDACCION_CONTRACT_FIRST.md`](REDACCION_CONTRACT_FIRST.md).

---

## 1. Qué es una plantilla, y qué no es

Una plantilla **no es un documento con huecos**. Es la declaración de una cadena de montaje: qué
ficheros pide, qué se extrae de ellos, cómo se limpian esos datos, qué se pinta, qué comenta el
modelo y dónde se para a esperar a una persona.

La consecuencia práctica es que **la plantilla no contiene texto del informe salvo el que sea
literalmente fijo**. Todo lo demás son referencias: un bloque que muestra una tabla no lleva la
tabla, lleva el identificador del bloque que la produjo.

Una plantilla se guarda **versionada e inmutable**: nunca se edita una versión, se publica la
siguiente. Y una versión concreta es lo que queda anclado a cada informe, para que publicar la v2
no reescriba lo que ya se redactó con la v1.

## 2. Las siete claves

Una spec (`spec_json`) tiene exactamente siete claves y **las siete son obligatorias**. No hay
valores por defecto: omitir una es un 422.

| Clave | Qué es |
|---|---|
| `sections` | Las secciones del informe y, dentro de cada una, qué bloques se imprimen y en qué orden |
| `blocks` | La lista de bloques. Es una **lista**, no un diccionario |
| `input_contract` | Qué ficheros y datos hay que aportar antes de poder ejecutar |
| `ui_contract` | Qué pinta el frontend: zonas de arrastre, campos, paneles |
| `ai_block_policy` | `allowed` / `disabled` / `required_review` |
| `review_policy` | `none` / `optional` / `required` |
| `export_policy` | `docx` / `odt` / `pdf` / `markdown` |

**Las tres políticas son hoy metadatos declarativos.** Están en el contrato, se guardan y se leen,
y ningún nodo del grafo, ni el exportador, ni el ensamblador las consulta. En particular
`export_policy: "odt"` no impide exportar DOCX, porque el exportador sólo sabe hacer DOCX. Dicho de
otro modo: declaran la intención de la plantilla, no gobiernan el comportamiento. Quien las
escriba esperando que cambien algo se llevará una sorpresa silenciosa, que es la peor clase.

Cuando una plantilla nace de una propuesta del modelo, **las tres se deducen** en vez de
preguntarse: `ai_block_policy` es `allowed` si hay algún bloque de IA y `disabled` si no;
`review_policy` es `required` si hay una puerta de revisión y `none` si no; `export_policy` es
siempre `docx`.

## 3. Lo que la plantilla pide: `input_contract`

Dos listas, `required_slots` y `optional_slots`, las dos opcionales y vacías por defecto. Cada
*slot* es un hueco donde alguien deja algo:

```json
{
  "slot_id": "datos",
  "kind": "markdown",
  "label": {"es": "Datos del programa", "ca": "Dades del programa", "en": "Programme data"},
  "required": true,
  "multiple": false,
  "max_size_mb": null,
  "validation": null
}
```

Los tipos admitidos son `pdf`, `excel`, `csv`, `markdown`, `text`, `number`, `date` y `selector`.

Dos detalles que cuestan tiempo si se ignoran. **`label` es siempre un diccionario por idioma,
nunca una cadena**: el módulo sirve a una institución bilingüe y una cadena plana no pasa la
validación. Y **`validation` es un diccionario libre sin esquema**: lo que se meta ahí no lo
comprueba nadie al publicar, así que sirve de documentación para quien lea la plantilla y poco
más.

## 4. Los once bloques

Hay once tipos, ni uno más, discriminados por la clave `kind`. Todos comparten cinco campos: `id`
y `title` obligatorios, y `required`, `depends_on` y `order` opcionales.

Conviene pensarlos en cinco familias, porque la familia dice quién produce el contenido.

**Texto fijo.** `STATIC_TEXT` lleva su contenido en el campo `content` y se imprime tal cual. Es lo
único de la plantilla que es texto del informe.

**Lo que teclea una persona.** `USER_INPUT` declara un `field_type` (`text`, `number`, `date`) y
lo rellena quien prepara el informe. Es la salida para lo que no está en ningún fichero: una
valoración de la coordinación, un dato que sólo conoce el servicio.

**Lo que produce el dato.** `DETERMINISTIC_DATA` es el bloque central del módulo. Declara
`source_pipeline` —obligatorio: `excel`, `pdf_text`, `pdf_table`, `md_table`, `manual` o
`admin_script`— y un diccionario `options` cuyas claves dependen del pipeline. `DATA_TRANSFORM`
encadena a partir de otro bloque de datos para limpiar y calcular. **Ninguno de los dos se
imprime**: producen datos para que otro los pinte.

**Lo que se ve.** `TABLE` y `CHART` apuntan con `data_block_ref` al bloque de datos cuyo contenido
muestran. `CITATION_BLOCK` agrega las citas de los bloques que enumere.

**Lo que escribe el modelo.** `AI_ASSISTED_TEXT`, `AI_SUMMARY` y `AI_REWRITE`, los tres con
`ai_prompt_template_id` y `review_policy_id` obligatorios y una lista opcional `data_block_refs`.
Los tres exigen aprobación humana antes de que su texto entre en el documento.

**Lo que frena.** `REVIEW_GATE` no produce nada visible: declara una política de revisión y
bloquea el ensamblado hasta que los bloques de los que depende estén aprobados.

### `depends_on` no es el canal de datos

Es el error conceptual más común. `depends_on` sirve para **propagar fallos en cascada** —si el
bloque del que dependes falla, tú fallas con `dependency_failed`— y para que una puerta de revisión
sepa qué tiene que estar aprobado antes de abrirse. Los datos viajan por otros tres campos:
`data_block_ref` en una tabla o un gráfico, `config.source_block_ref` en una transformación, y
`data_block_refs` en un bloque de IA.

## 5. Las tres cadenas, y la regla del anclaje

Sólo hay tres maneras de que un bloque llegue a un dato.

### 5.1 Del fichero subido al bloque de extracción

**El bloque no nombra el slot.** La correspondencia se hace por tipo: un `source_pipeline: "excel"`
busca un slot `excel` o `csv`, uno `md_table` busca un slot `markdown`, uno `pdf_text` o
`pdf_table` busca un slot `pdf`. Se toma **el primer slot compatible que tenga fichero**.

De ahí una limitación que hay que tener presente al diseñar: **con dos slots `excel` y dos bloques
que extraen de Excel, los dos bloques leen el mismo fichero**. No existe forma, desde el contrato
del bloque, de decir «éste lee el slot B». Si el informe necesita dos hojas distintas, hoy la
salida es un solo fichero con dos pestañas y dos bloques que se diferencian por `options.sheet`.

Qué se saca del fichero lo dicen las `options`, y cada pipeline tiene las suyas:

| Pipeline | Opciones |
|---|---|
| `md_table` | `table` — el código del pie, `"Tabla 1.1"`; `include_free_text` |
| `excel` | `sheet` (por defecto la primera), `header_row`, `required_columns` |
| `pdf_table` | `pages` |
| `manual` | `slot`, `kind` |
| `admin_script` | las inyecta el sistema; ver abajo |

El pipeline de markdown busca **el código exacto del pie de tabla**. Si no lo encuentra, emite un
aviso `TABLE_NOT_FOUND` y devuelve vacío: **no devuelve la tabla más parecida**. Esa negativa es
deliberada — una tabla aproximada en un informe institucional es peor que una tabla ausente.

### 5.2 Del bloque a una función del catálogo

Cuando el cálculo no lo hace un pipeline estándar, el bloque declara `source_pipeline:
"admin_script"` y **una referencia a una función del catálogo**:

```json
{"funcion_ref": {"funcion_id": "…uuid…", "version": 3}}
```

La versión es exacta y a propósito: publicar la v4 de una función no toca ninguna plantilla
anclada a la v3. Dos reglas duras lo protegen, y las dos las comprueba el validador del contrato:

- **El código no se incrusta.** Si `options` lleva `code` o `approved`, la plantilla no valida. El
  código vive en el catálogo; el bloque lo referencia.
- **Un bloque `admin_script` sin `funcion_ref` no valida.** Sin función no hay nada que ejecutar.

Si la función referenciada está suspendida o retirada, el bloque **falla en alto** con su aviso. No
se queda vacío en silencio, que es lo que hacía antes y lo que costó encontrar.

Una limitación que conviene saber antes de escribir una función pensando en usarla desde una
plantilla: **una función con más de un slot de fichero hoy no se puede invocar desde un bloque**.
Con cero slots se invoca sin ficheros; con uno, se le pasa el que corresponda; con dos o más, el
sistema se niega a adivinar a cuál va cada cosa.

### 5.3 Del dato a la valoración: apunta al dato, nunca a la tabla

Un bloque de IA se ancla con `data_block_refs`, y **tiene que apuntar al bloque que produce los
datos, no al bloque que los pinta**:

```json
{"id": "t_tabla_1_1", "kind": "DETERMINISTIC_DATA", "source_pipeline": "md_table",
 "options": {"table": "Tabla 1.1"}, "title": "Tabla 1.1 Número de plazas"}

{"id": "tab_tabla_1_1", "kind": "TABLE", "data_block_ref": "t_tabla_1_1",
 "title": "Número de plazas del programa"}

{"id": "v_tabla_1_1", "kind": "AI_ASSISTED_TEXT",
 "data_block_refs": ["t_tabla_1_1"],
 "ai_prompt_template_id": "valoracion_de_tendencia_v1",
 "review_policy_id": "required", "title": "Valoración de Tabla 1.1"}
```

La valoración apunta a `t_tabla_1_1`, **no** a `tab_tabla_1_1`. Es lo que exige el validador y es
la corrección que hubo que hacerle al prompt del modelo, porque la primera redacción describía
`data_block_refs` como «la tabla» y el modelo apuntaba, razonablemente, al bloque `TABLE`.

Y hay una semántica que se olvida: **`data_block_refs` vacío significa «todo el informe»**. No
significa «sin datos». Un bloque de IA sin anclaje comenta el documento entero, que es el
comportamiento heredado y casi nunca lo que se quiere: es exactamente el fallo que producía
valoraciones citando cifras de otra tabla.

## 6. Secciones: lo que sale en el informe, y lo que no

La vista previa y el ensamblado final **recorren las secciones** y pintan los bloques que cada
sección enumera en `block_ids`. Un bloque que no aparece en ninguna sección existe, se ejecuta,
extrae sus datos, pasa la revisión… y no sale en el informe.

Eso pasó de verdad: un informe de seguimiento con las dos secciones vacías después de que las
nueve tablas se extrajeran y las nueve valoraciones se aprobaran. La primera versión de la
plantilla del doctorado, que sigue en el repositorio, es ese contraejemplo: secciones sin
`block_ids` y treinta y dos bloques huérfanos.

Publicar una versión **rechaza con 422** los bloques imprimibles huérfanos, con la lista de
identificadores y qué hacer. Pero «imprimible» excluye tres tipos: `DETERMINISTIC_DATA`,
`DATA_TRANSFORM` y `REVIEW_GATE`. **Que esos estén fuera de toda sección es lo normal**, y meter un
`DETERMINISTIC_DATA` en una sección además duplicaría la tabla, porque el `TABLE` que lo
referencia ya la pinta.

La comprobación es **asimétrica a propósito**: una sección que enumera un bloque que no existe no
es error. La vista previa se lo salta sin ruido, porque una plantilla se construye por pasos y una
referencia adelantada es un estado de trabajo legítimo.

### El orden es el del array

`sections` tiene un campo `order` y los bloques también, y **ninguno de los dos ordena nada**. El
orden efectivo es el del array `sections` y el de `block_ids` dentro de cada sección. Mantén el
campo coherente por higiene, pero no cuentes con él para mover nada de sitio.

## 7. Las tres capas de validación, que no comprueban lo mismo

Es la parte que más confunde, porque una plantilla puede pasar una capa y romperse en la
siguiente.

**La primera es el validador de propuestas**, y sólo actúa sobre lo que devuelve el modelo en
`/redaccion/draft`. Es la más estricta: rechaza un perfil desconocido, una dependencia colgante,
una tabla o un gráfico que no apunte a nada o que apunte a algo que no produce datos, una
valoración anclada a un bloque inexistente o a uno que no produce datos, una transformación que
lea de donde no hay, un bloque imprimible huérfano, y **una propuesta con bloques de IA y sin
puerta de revisión**.

Ese validador además **normaliza en silencio** dos cosas, y conviene saberlo: reasigna los
identificadores duplicados —el segundo pasa a llamarse `block_<hex>`, y si una sección lo listaba
por el nombre viejo, ese bloque queda huérfano— y reordena los bloques según las secciones.

**La segunda es la publicación de una versión**, y comprueba mucho menos: que la spec valide contra
Pydantic, y que no haya bloques imprimibles huérfanos. Nada más. **Publicar una spec con un `TABLE`
cuyo `data_block_ref` apunte a la nada pasa la publicación y falla en ejecución.** Si construyes
plantillas por API o por MCP en vez de por la pantalla de propuesta, esta diferencia es tuya:
valida el borrador explícitamente antes de publicarlo.

**La tercera es la ejecución**, que comprueba lo que sólo se puede comprobar con el workspace
delante: que el bloque referenciado esté de verdad ahí, que el pipeline declarado exista, que la
función referenciada se pueda ejecutar. Un `source_pipeline` inventado valida en las dos primeras
capas y falla aquí.

## 8. El contrato de UI no se escribe: se deriva

`ui_contract` es la proyección para el frontend —zonas de arrastre, campos manuales, si hay panel
de revisión de IA, qué aspecto tiene la vista previa— y **se calcula a partir de
`input_contract`**: un slot cuyo tipo tiene extensiones de fichero conocidas se convierte en zona
de arrastre; el resto, en campo manual.

Dos cosas que se siguen de ahí. La primera: **lo obligatorio lo decide `input_contract`, no el
contrato de UI**; el servidor recalcula el `required` de cada zona de arrastre al servirlo, porque
las versiones guardadas antes de esa corrección no lo traían y el formulario dejaba enviar sin
fichero. La segunda: si escribes una plantilla a mano con `manual_fields` vacío pero declaras
bloques `USER_INPUT`, **esos campos no tendrán dónde rellenarse** — la sección existirá y saldrá
vacía. Le pasa hoy a la plantilla del doctorado con sus cuatro campos de coordinación.

## 9. Versionado y migración

Publicar es **append-only**: nunca se muta una versión, se añade la siguiente y pasa a ser la
vigente. Los informes existentes **no se mueven**: cada uno queda anclado a la versión con la que
nació.

Migrar un informe a una versión nueva es explícito y lo pide su propietario. No transforma nada:
crea un informe nuevo con los mismos ficheros de entrada, sin bloques —se vuelven a ejecutar—,
archiva el antiguo y anota el parentesco.

**La detección de cambios rompedores está escrita y hoy no funciona.** La única regla implementada
—«rompe si la versión destino exige un fichero que la actual no pedía»— lee la clave
`proposed_inputs`, que es la del borrador del modelo, sobre una spec persistida que guarda
`input_contract`. Sobre cualquier plantilla real devuelve el conjunto vacío, así que la migración
nunca avisa de nada. Está anotado aquí para que nadie confíe en ese aviso mientras no se arregle.

Al margen de eso: una plantilla **retirada** no admite informes nuevos —409 con el nombre de la
plantilla y qué hacer— pero los informes que ya existían siguen vivos. Es lo que hace que retirar
sea reversible y borrar no exista.

## 10. Dónde está el contrato de verdad

**El esquema completo**, siempre al día, en una sola respuesta:

```
GET /api/v1/hub/redaccion/template-schema
```

Requiere el módulo `informes` y un token con `redaccion:templates:read`. Devuelve el JSON Schema
de Pydantic con todos los submodelos: los once bloques, la configuración de gráficos, la de
transformaciones, la referencia a función, los slots, el contrato de UI, las secciones y los
enumerados de política. Es el mismo contrato que se le da al modelo cuando propone una plantilla,
troceado — describirlo a mano en el prompt fue un juego del topo que se abandonó a propósito.

**Desde un cliente MCP** es el recurso `govgenai://redaccion/template-schema`, y va acompañado de
`govgenai://redaccion/profiles` con los cinco perfiles de informe. Las herramientas de autoría de
plantillas —listar, leer una versión, validar un borrador, crear la plantilla, publicar una
versión— existen sólo en el transporte **stdio**; el servidor MCP remoto no las expone. Detalle en
[`MCP_SERVER.md`](MCP_SERVER.md).

**Dos ejemplos completos y vivos** en `server/app/data/plantillas_demo/`:
`ejecucion_presupuestaria.json` recorre la cadena entera sobre una hoja de cálculo —hueco `excel`,
conversión de importes en formato español, columna calculada, orden, tabla, gráfico y resumen con
revisión— y es el mejor punto de partida para leer una spec de cabo a rabo.
`informe_seguimiento_doctorado.json` es el caso guía, con su v1 rota y su v2 correcta.

## 11. Dos recetas

### El informe de seguimiento: nueve veces el mismo patrón

Un informe con tablas de indicadores y comentario se monta repitiendo un trío por apartado:
`DETERMINISTIC_DATA` que extrae la tabla por su código, `TABLE` que la pinta, bloque de IA anclado
al primero que la comenta. Al final, los `USER_INPUT` de lo que no está en ningún fichero y un
`REVIEW_GATE`. Las secciones enumeran las tablas, las valoraciones y los campos; **no** enumeran
los bloques de datos ni la puerta.

Un solo slot markdown alimenta las nueve extracciones: cada bloque elige su tabla por `options`.

### La hoja de cálculo: limpiar antes de calcular

`DETERMINISTIC_DATA` con `source_pipeline: "excel"` → `DATA_TRANSFORM` con `to_number` →
`DATA_TRANSFORM` con `compute_column` → `DATA_TRANSFORM` con `sort_rows` → `TABLE` y `CHART`
apuntando al **último** eslabón → `AI_SUMMARY`.

**`to_number` va siempre antes de cualquier suma o agrupación.** Cualquier aplicación de gestión de
aquí exporta `1.234,56 €`, y sobre texto una suma concatena o revienta: el informe sale con una
cifra mal **y sin un error que mirar**. Ésa es la razón de que la operación exista y de que esté
dicha aquí en negrita.

Hay veinte operaciones de transformación, de `filter` y `groupby` a `merge_columns` y `unpivot`.
`compute_column` **no tiene campo de fórmula y no hay `eval`**, a propósito: lo compuesto se
consigue encadenando operaciones, y un operando de texto es siempre un nombre de columna.

## 12. Lo que el esquema hoy no permite decir

Lista corta y honesta, para no buscar lo que no está:

- **Qué slot lee un bloque.** La resolución es por tipo y toma el primero compatible.
- **Qué hace cada política.** `ai_block_policy`, `review_policy` y `export_policy` se guardan y no
  se consumen.
- **Ordenar por el campo `order`.** Ordena el array.
- **Invocar una función con dos slots de fichero.**
- **Exportar a otra cosa que no sea DOCX.** El campo admite `odt`, `pdf` y `markdown`; el
  exportador sólo sabe DOCX, y convertir a PDF exigiría LibreOffice en el servidor.
- **Fijar el hueco de un gráfico de anillo.** `donut_ratio` existe en el renderizador y no en la
  configuración del bloque.
- **Un registro cerrado de prompts o de políticas de revisión.** `ai_prompt_template_id` y
  `review_policy_id` son cadenas libres; los valores en uso son `valoracion_de_tendencia_v1`,
  `resumen_de_resultados_v1`, `generic_report_v1` y `required`.

Y una advertencia sobre nombres, que se paga cara al configurar un gráfico: el bloque usa
`x_axis`, `y_axis` y `color_by`; el renderizador, por dentro, usa `x_column`, `y_column` y
`color_column`. La traducción la hace el sistema. Escribe siempre los nombres del bloque.

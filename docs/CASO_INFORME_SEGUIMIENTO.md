# Caso guía: el informe anual de seguimiento de un programa de doctorado

Este documento describe el supuesto de uso que el módulo de Informes tiene que servir, cómo se
monta con las piezas que existen y qué se comprobó al montarlo de verdad con el informe del
Programa de Doctorado en Ciencias (curso 2024/2025). Es el caso guía porque hay muchos informes
con la misma forma: seguimiento de titulaciones, ejecución presupuestaria, memorias de servicio.

## 1. La forma del informe

Un informe de seguimiento no es un texto que un modelo redacta. Es una **estructura fija** —la
que define la plantilla— en la que se alternan dos cosas de naturaleza distinta:

| Pieza | Quién la produce | Puede equivocarse |
|---|---|---|
| Tablas y gráficos | El sistema, de forma **determinista**, a partir del dato | No: reproduce o avisa |
| Valoración de tendencias y resumen de resultados | La **IA propone**; el técnico aprueba o edita | Sí, y por eso se revisa |

La regla que ordena todo lo demás: **la cifra no la escribe el modelo**. La tabla se reproduce del
dato de origen tal cual —«No hay valor» incluido, porque la diferencia entre *no hay dato* y *el
dato es cero* es información— y el modelo sólo interpreta lo que ya está impreso al lado.

El intento previo con una gema de Gemini falló justo aquí: al pintar las tablas se inventaba
cifras, y al resumir omitía tablas sin decirlo. Ninguno de los dos fallos es detectable leyendo el
resultado, que es lo que los hace caros.

## 2. Los datos de entrada

Hoy llegan como un `.md` con las tablas del programa (una treintena por informe, cuarenta y dos en
el fichero real). El pipeline `md_table_pipeline_v1` las extrae **literales**: no convierte tipos,
no calcula, no normaliza y no rellena huecos. Cada tabla se identifica por su código de pie
(«Tabla 1.4.2 …»), que es lo que permite que una plantilla diga *valora la Tabla 1.2* y que el
informe final conserve la numeración original.

Mañana el mismo dato llegará como dataset, JSON o consulta a una API: eso es un pipeline nuevo
detrás del mismo contrato de extracción, sin tocar plantillas ni prompts.

Lo que **no** está en el documento —porcentaje de movilidad, destinos, quejas recibidas,
reacreditación— se pide por **formulario** (bloques `USER_INPUT`), no por conversación: así queda
registrado qué se preguntó y qué se contestó.

## 3. La forma de la plantilla

Por cada apartado del informe, tres bloques:

```
DETERMINISTIC_DATA   options.table = "Tabla 1.3"     ← trae UNA tabla, la suya
TABLE                data_block_ref = <el anterior>  ← la imprime, sin tocarla
AI_ASSISTED_TEXT     data_block_refs = [<el primero>] ← valora ESA tabla y sólo esa
                     ai_prompt_template_id = valoracion_de_tendencia_v1
                     review_policy_id = required
```

El anclaje del último bloque es lo que evita el fallo de «resumir todo el documento»: la IA de
cada apartado recibe **su** tabla, no el informe entero. Una tabla, una valoración, nueve veces.
Cuando un apartado agrega varias tablas, el mismo bloque acepta varias referencias y usa
`resumen_de_resultados_v1`, cuya instrucción obliga a mencionar **todas** las tablas del contexto
—y a decirlo en una frase si alguna no aporta nada— porque omitir una en silencio es el fallo más
difícil de detectar de un resumen.

Las secciones de la plantilla enumeran en `block_ids` los bloques que se imprimen y en qué orden.
Los bloques que sólo producen datos (`DETERMINISTIC_DATA`, `DATA_TRANSFORM`) y la puerta de
revisión no van en ninguna sección: no son contenido.

## 4. Lo que hace el humano

1. Sube el fichero de datos y rellena los campos del formulario.
2. Lee cada valoración propuesta junto a **la referencia de la tabla en que se apoya**
   («Valora: Tabla 1.3»), y aprueba, edita, rechaza o pide otra.
3. Al editar, el texto original de la IA queda a la vista y en el registro, con quién editó y
   cuándo. La edición no borra el rastro.
4. Con todo aprobado, la vista previa muestra el informe montado y la exportación entrega el DOCX
   con su anexo de auditoría.

Ningún bloque de IA llega al documento final sin pasar por ese punto: es el requisito de
gobernanza —la propuesta es propuesta— y a la vez lo que hace el resultado utilizable.

## 5. Lo que se encontró al montarlo de verdad

Montar el informe completo con el fichero real destapó cuatro cosas que ningún test unitario veía,
todas del mismo tipo: **la capacidad existía y la puerta estaba cerrada**.

- **Los bloques `TABLE` no los pintaba nadie.** Estaban en el contrato, el validador les exigía
  `data_block_ref` y el prompt los ofrecía al modelo, pero ningún nodo del grafo los rellenaba: el
  informe salía con las nueve tablas vacías, sin error y sin aviso. Es el mismo agujero que PRO.5
  tapó para los gráficos. Lo cubre ahora `TableRenderNode`.
- **Un bloque que no está en ninguna sección desaparece del informe.** La vista previa y el
  ensamblado recorren las secciones; lo que ninguna enumera se ejecuta, se revisa y no se imprime.
  El informe salía corto y con aspecto de estar bien. Ahora se rechaza al publicar la plantilla y
  al validar el borrador del modelo, que es el único momento en que avisar sirve de algo.
- **Las tablas del cuerpo se pintaban sin estilo.** Sólo estaba vestido el anexo de auditoría,
  porque hasta ahora ningún bloque del cuerpo había llegado a producir una tabla.
- **La valoración llegaba con markdown crudo y longitud de ensayo.** El informe imprime el texto
  tal cual, así que los asteriscos salían impresos. Las dos instrucciones piden ahora prosa
  corrida y un par de párrafos.

## 6. Verificado con el informe real

Sobre el fichero del Programa de Doctorado en Ciencias (70.181 bytes, 42 tablas):

- Las 42 tablas se extraen con su código, sin duplicados.
- Los nueve bloques de datos traen **exactamente una** tabla cada uno, y es la suya.
- Ninguna valoración usa cifras que no estén en el documento de origen, y ninguna usa cifras de
  otra tabla.
- Las tres tablas con celdas «No hay valor» lo dicen; ni se rellenan ni se convierten en cero.
- La vista previa monta tres secciones con sus nueve tablas y sus nueve valoraciones; la
  exportación entrega un DOCX con las tablas como tablas de Word.

## 7. Lo que queda fuera de este caso

- La consulta automática del dato (hoy se sube el `.md`).
- Los gráficos: la plantilla del caso guía no los usa, pero el bloque `CHART` funciona desde PRO.5
  y el catálogo de tipos está en `chart_configuration.py`.
- El resto de criterios del informe (3 a 8), incluidas las quince tablas del plan de acciones de
  mejora, que el pipeline ya extrae con su código.

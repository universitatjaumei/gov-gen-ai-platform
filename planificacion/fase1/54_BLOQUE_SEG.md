## Bloque SEG — El asistente de informes de seguimiento: valoración anclada a su tabla

> **Planificado el 2026-08-18**, a partir del supuesto de uso que el usuario necesita y que hasta
> ahora no estaba escrito en ningún plan. Caso guía: el **informe anual de seguimiento de un
> programa de doctorado**, con dos documentos reales sobre la mesa —el resumen de datos de un
> programa (30 tablas) y el prompt de la gema que se usó antes—.
>
> **El supuesto, en una frase del usuario**: «el informe lee la información, presenta las tablas y
> gráficos en la estructura que se define en la plantilla de forma determinista y, a continuación,
> la literatura con la valoración de tendencias o el resumen de resultados lo propone la IA, sujeto
> a aprobación o edición por el humano».
>
> **Por qué el intento anterior no bastó.** Con una gema de Gemini el resultado no fue
> satisfactorio: *inventaba datos al pintar las tablas* y *resumía omitiendo información
> relevante*. El prompt de esa gema pelea contra eso en mayúsculas —«BAJO NINGÚN CONCEPTO CREES
> TABLAS CON DATOS INVENTADOS», «NO HAGAS CÁLCULOS COMO MEDIAS SI NO SE TE PIDE»—, y perder esa
> batalla a base de instrucciones es lo normal: se le pide al modelo que no haga algo que sí puede
> hacer. Aquí las tablas **no las escribe el modelo**, así que no puede inventarlas.
>
> **El hueco que decide si esto sirve.** `_build_context` construye **un único contexto con todos
> los bloques extraídos** y se lo pasa igual a todos los apartados de IA; y
> `AIAssistedTextBlock` solo tiene `ai_prompt_template_id` y `review_policy_id`, así que **no
> puede decir «reflexiona sobre la Tabla 1.2»**. Con treinta tablas, cada valoración recibiría las
> treinta: exactamente el fallo de la gema, reproducido por arquitectura. Sin SEG.1 el resto del
> bloque no vale.
>
> **Lo que ya está y no hay que construir**: estructura por plantilla, extracción y transformación
> deterministas, once tipos de gráfico, puerta de revisión bloqueante, manifiesto de ejecución, y
> **el endpoint de edición con el original guardado en auditoría** (`editBlock`) — cuyo hook
> generado no llama ninguna pantalla.

### Prompt SEG.1 (RED/GREEN) — Cada valoración lee su tabla, no el informe entero

**Modelo sugerido**: **Opus** — decide la forma del contrato y la compatibilidad con las
plantillas que ya existen.

```
# PROMPT SEG.1 (RED/GREEN) — Anclaje del apartado de IA a sus datos
# Deploy: edge (contracts/blocks.py, graph/nodes/ai_assist_draft.py)

## Por que
`_build_context(state.blocks)` mete TODOS los bloques extraidos en un solo contexto y lo entrega
igual a cada apartado de IA. Con 30 tablas, la valoracion de la Tabla 1.2 recibe las 30 y el
encargo de "redacta esta seccion": el modelo mezcla, resume y se deja fuera lo relevante. Es el
fallo que el usuario ya vivio con una gema, y no se arregla con instrucciones: se arregla no
dandole lo que no necesita.

## Que hacer
1. RED: un apartado de IA anclado a un bloque de datos recibe en su contexto **ese** bloque y
   **no** los otros. Con dos tablas en el informe, la valoracion de la primera no puede ver la
   segunda.
2. GREEN: `AIAssistedTextBlock` (y `AI_SUMMARY` / `AI_REWRITE`) admiten `data_block_refs:
   list[str]`. El nodo construye el contexto **solo** con esos bloques, en el orden declarado.
3. Compatibilidad: sin `data_block_refs` se conserva el comportamiento actual -contexto completo-,
   porque hay plantillas vivas que dependen de el. Pero eso **se anota en el manifiesto** de la
   ejecucion: un apartado sin anclaje es una valoracion cuya fuente no consta, y quien audite el
   informe tiene que poder verlo.
4. El validador de plantillas comprueba que cada `data_block_refs` apunta a un bloque que produce
   datos, con el mismo criterio que GUI.3 aplico a TABLE y CHART.

## Criterio de done
- [ ] Un apartado anclado no ve las tablas de los demas (medido, no supuesto)
- [ ] Varias tablas en un mismo apartado, en el orden declarado
- [ ] Una referencia a un bloque inexistente no pasa la validacion
- [ ] Un apartado sin anclaje consta como tal en el manifiesto
```

### Prompt SEG.2 (RED/GREEN) — La instrucción de valorar tendencias, con sus reglas duras

**Modelo sugerido**: **Opus** — es redacción de instrucciones para un modelo, con criterio
institucional.

```
# PROMPT SEG.2 (RED/GREEN) — Valoracion de tendencias sobre una tabla multianual
# Deploy: edge (services/redactor_de_bloques.py)

## Por que
El catalogo del modulo tiene una sola instruccion, `generic_report_v1`: "redacta esta seccion". Lo
que estos informes necesitan es otra cosa y muy concreta: **comparar el ultimo curso con los
anteriores sobre una tabla**, decir si la tendencia crece o decrece, y cuando decrece **sugerir**
acciones -sin imperativos-. El prompt de la gema ya tenia esa doctrina escrita; se porta, que es
lo que PRO.1 y PRO.4 ensenaron a hacer con el legacy.

## Que hacer
1. Anadir al catalogo una instruccion de **valoracion de tendencia** con estas reglas duras,
   tomadas del caso real:
   - Se apoya solo en las cifras de la tabla del contexto. Un dato que no este, no se menciona.
   - **No recalcula**: ni medias, ni totales, ni agregados que no vengan dados.
   - Una celda sin dato -"No hay valor"- se respeta como ausencia y se dice, no se rellena ni se
     interpola.
   - Si la tendencia decrece, sugiere acciones **en tono neutro**, nunca imperativo.
   - Puede senalar una relacion entre dos variables de la misma tabla, y la marca como hipotesis.
   - Cierra dejando claro que la reflexion cualitativa corresponde a quien firma el informe.
2. Anadir tambien una instruccion de **resumen de resultados** para los apartados que agregan
   varias tablas.
3. RED/GREEN con una tabla multianual real del informe de doctorado: la valoracion cita las cifras
   de esa tabla y **ninguna otra**; una tabla con "No hay valor" no produce un numero inventado.

## Criterio de done
- [ ] Las dos instrucciones en el catalogo, con test
- [ ] Sobre una tabla con celdas vacias, el texto dice que faltan y no las rellena
- [ ] Ninguna cifra del texto esta ausente de la tabla (comprobado con la tabla real)
```

### Prompt SEG.3 (RED/GREEN) — Leer las tablas de un Markdown

**Modelo sugerido**: **Sonnet** — alcance cerrado, con un fichero real de referencia.

```
# PROMPT SEG.3 (RED/GREEN) — Pipeline de tablas Markdown
# Deploy: edge (pipelines/)

## Por que
Los origenes de datos hoy son excel, pdf_text, pdf_table, manual y admin_script. Los datos de
entrada de estos informes son **Markdown con 30 tablas**, uno por programa, y ya existen. Manana
seran un JSON o una consulta a una API: la abstraccion de pipeline ya esta, asi que esto es
aditivo.

## Que hacer
1. RED contra el fichero real `Informe Resumen Programa de Doctorado en Ciencias (90162).md`:
   - Se extraen las tablas con sus cabeceras y filas **literales**.
   - El **codigo de la tabla** ("Tabla 1.2 Evolucion de la Matricula", que va DEBAJO de la tabla
     en este formato) queda como nombre, para que una plantilla pueda referenciarla.
   - Las celdas "No hay valor" y las vacias se conservan tal cual: no se convierten a 0 ni a
     nulo, porque la diferencia entre "no hay dato" y "el dato es cero" es informacion.
   - Las celdas con texto largo y multiples valores -la de matriculados por linea de
     investigacion- no se parten.
2. GREEN: pipeline `md_table`, registrado como los demas.
3. Documentar en `docs/` que este pipeline **reproduce**, no interpreta: si hace falta calcular,
   lo hace una operacion declarativa aguas abajo.

## Criterio de done
- [ ] Las tablas del fichero real, extraidas y contadas
- [ ] Codigos de tabla disponibles como nombre
- [ ] "No hay valor" sobrevive al viaje hasta la vista previa
```

### Prompt SEG.4 (RED/GREEN + navegador) — Editar la propuesta de la IA desde la pantalla

**Modelo sugerido**: **Sonnet**.

```
# PROMPT SEG.4 (RED/GREEN) — Aprobar, editar o rechazar, desde la pantalla
# Deploy: edge (frontend + workspaces_router)

## Por que
El backend ya sabe hacerlo: `PATCH /workspaces/{id}/blocks/{block_id}/edit` sobreescribe el
contenido y **guarda el original en un evento de auditoria** con su actor, que es justo lo que el
marco de gobernanza pide de una supervision humana efectiva. Lo que falta es la pantalla: el hook
generado existe y **no lo llama nadie**. Sin eso, el tecnico solo puede aprobar o rechazar en
bloque, y el usuario lo senala como limitacion.

## Que hacer
1. RED de frontend: el panel de revision de un apartado de IA ofrece **editar**, no solo aprobar y
   rechazar; al guardar, llama al endpoint con el texto nuevo.
2. GREEN, y con dos cosas visibles: **lo que propuso la IA sigue consultable** despues de editar
   -esta en auditoria, no se pierde- y se ve **quien edito y cuando**.
3. Editar no aprueba solo: el bloque queda como lo que es, un texto editado por una persona, y
   sigue el camino de aprobacion de la maquina de estados.
4. Verificacion en navegador con el informe real: proponer, editar, aprobar, exportar.

## Criterio de done
- [ ] Se edita el texto de un apartado y el informe exportado lleva el texto editado
- [ ] El original de la IA sigue recuperable
- [ ] i18n en los tres idiomas
- [ ] Comprobado en navegador, no solo en test
```

### Prompt SEG.5 (plantilla + verificación) — El informe de seguimiento, de punta a punta

**Modelo sugerido**: **Opus** — traducir un informe institucional de 30 tablas a una plantilla es
donde se decide si el modelo de plantillas aguanta el caso real.

```
# PROMPT SEG.5 (plantilla) — El informe anual de doctorado como primer caso real
# Deploy: edge

## Por que
Una plantilla de ~60 bloques -30 tablas y sus 30 valoraciones- no la puede proponer un modelo, y
no hace falta: se redacta **una vez** por tipo de informe y se les facilita a los coordinadores.
Es lo que el usuario ya intuia. La via existe: el servidor MCP tiene `create_template` y
`publish_template_version`.

## Que hacer
1. Construir la plantilla del informe de seguimiento con la estructura real: apartados A (siete
   criterios, con sus subcriterios) y B (plan de acciones de mejora); por cada tabla del resumen
   de datos, un bloque de tabla y un apartado de valoracion **anclado a ella** (SEG.1); y una
   puerta de revision.
2. **Los datos que no estan en el documento se piden por formulario**, no por conversacion:
   porcentaje de movilidad y donde se hicieron las estancias, quejas y sugerencias recibidas, si
   hubo reacreditacion en el curso. Cada respuesta queda registrada y asociada al informe; con una
   conversacion no hay forma de saber despues que se pregunto ni que se contesto.
   **Decision tomada**: campos opcionales con un selector de si/no, sin campos condicionales. La
   condicionalidad exigiria ampliar el contrato de entrada y no aporta nada que un campo vacio no
   resuelva; si al usarlo estorba, se replantea con el caso en la mano.
3. Verificacion de punta a punta con el fichero real de un programa: cargar, generar, revisar,
   editar un par de valoraciones, aprobar y exportar.
4. Comprobar las dos cosas que fallaron con la gema, una por una:
   - **Ninguna cifra del informe esta ausente del documento de datos.**
   - **Ninguna tabla del documento se ha quedado fuera** ni ha cambiado de columnas o de valores.

## Criterio de done
- [ ] Plantilla publicada y un informe generado con datos reales de un programa
- [ ] Las dos comprobaciones de fidelidad, verificadas tabla a tabla
- [ ] El .bat humano con lo unico irreducible: si la valoracion le sirve a un coordinador
- [ ] `docs/CASO_INFORME_SEGUIMIENTO.md` con el recorrido, para replicarlo en otros informes
```

---

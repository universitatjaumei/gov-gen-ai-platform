# Comparativa: los ocho prompts de AutomatIA frente a los prompts vivos

**Fecha**: 2026-08-18 (LEG.1). **Propósito**: leer antes de borrar. Son 580 líneas escritas para la
aplicación NiceGUI y sembradas en cada arranque en dos tablas legacy (`ExtractionServiceConfig` y
`SystemPrompt`). La lección de PRO.1 y PRO.4 es que el legacy tenía decisiones **mejores** que las
del código nuevo y se descubrieron leyéndolo, así que aquí queda por escrito qué se salva, qué no y
por qué.

Los prompts vivos son otros dos sistemas que este bloque **no toca**: `HubPromptTemplate` (por
asistente) y `HubActivityPrompt` (por actividad, con su catálogo por defecto en
`modules/redaccion/services/actividades_llm.py`).

## Resumen

| Prompt legacy | Equivalente vivo | Veredicto |
|---|---|---|
| `sys_custom_script_gen` | actividad `propuesta_de_script` | El vivo es mejor. Nada que portar, y una regla que **no** se porta a propósito |
| `script_generator` (v12) | la misma actividad | Igual: duplicado del anterior con menos detalle |
| `sys_clarification_*` (4) | — | Sin equivalente. **Se cita** para el bloque de automatizaciones |
| `sys_llm_process` | nodos de redacción | El vivo es mucho más específico. Nada que portar |
| `sys_semantic_naming` | operaciones del ETL | **Aporta**: reglas de nomenclatura que el prompt del ETL no daba. **Portado** |
| `sys_flow_orchestrator` + `flow_orchestrator` (v12) | — | Sin equivalente (automatizaciones). **Se cita** |
| `sys_metaprogramming` | — | Sin equivalente. **Se cita** en una línea |
| `copilot_helper` (v12) | `CopilotService.answer` | Arquitectura distinta; una idea aprovechable, **citada** |

## 1. Generación de scripts: el vivo gana, y por razones concretas

El legacy (`sys_custom_script_gen`, y su duplicado `script_generator`) pide un script «robusto,
autocontenido y de calidad de producción», enumera a mano las librerías permitidas y las prohibidas,
y exige formato markdown.

El vivo (`_PROMPT_PROPUESTA`) hace tres cosas que el legacy no:

* **Las listas de módulos y nombres prohibidos no se escriben a mano**: se generan del auditor
  determinista de PRO.1. Un prompt que enumera lo que otro fichero bloquea divergen en el primer
  cambio, y el síntoma es una propuesta rechazada sin motivo entendible.
* **Prohíbe las rutas absolutas explícitamente**, incluso en comentarios. El legacy las detectaba
  con una regex en su auditor pero no se lo decía al modelo, así que las producía y luego las
  rechazaba.
* **Declara el contrato de salida** (`result` con `tables`, `metrics`, `free_text`) y las variables
  disponibles. El legacy dejaba «genera los resultados en la ruta especificada o retorna objetos si
  se pide», que no es un contrato.

**Y una regla del legacy que se descarta a propósito**: «El script debe manejar excepciones
(try/except) y reportar errores claramente». En este diseño es lo contrario de lo que se quiere: el
prompt de auditoría vivo dice que un script que «puede devolver datos vacíos o basura sin fallar» es
**peor que uno que falla**. Un `try/except` alrededor de la extracción convierte un fallo visible en
una tabla vacía que nadie revisa. No se porta.

## 2. Clarificación previa: no hay equivalente, y la idea es buena

Cuatro prompts (`custom`, `etl`, `rpa`, `extraction`) que analizan si hay que **preguntar antes** de
generar. El módulo de Informes no pregunta: propone y el humano corrige. Es una capacidad futura, y
lo que merece sobrevivir del texto son sus reglas, que están bien pensadas:

* **Máximo tres preguntas**, priorizando las más críticas.
* **No preguntar obviedades** ni cosas deducibles del contexto o de los ficheros.
* **Si la confianza es alta (≥ 0,8), no preguntar nada.**
* **Cada pregunta debe afectar directamente a la estructura del código.** Ésta es la que convierte
  la clarificación en algo útil y no en un cuestionario.
* Contrato de respuesta con `needs_clarification`, `confidence_score`, `reasoning` y preguntas
  tipadas (`single_choice` con opciones y valor por defecto).

Y una observación de contenido específica de extracción que también vale: las ambigüedades reales
son **selección de datos cuando hay varias tablas**, **formato de fechas y monedas** y
**equivalencias semánticas** entre nombres de columna. Las tres han aparecido de verdad en PRO.9.

**Para quien planifique el bloque de automatizaciones**: esto es el punto de partida; no hace falta
volver a `git log` a buscarlo.

## 3. Nomenclatura semántica: portado

`sys_semantic_naming` daba reglas para nombrar el resultado de un paso: `snake_case`, español, tres o
cuatro palabras como máximo, sin sufijos `_var` ni `_step`, y que el nombre refleje **qué datos**
lleva, no qué operación los produjo (`lista_facturas`, no `resultado_extraccion`).

El prompt del ETL vivo (`_PROMPT_ETL`) hace que el modelo **cree columnas nuevas** con
`compute_column` y renombre con `rename`, y no decía nada sobre cómo nombrarlas. Se ha portado, con
su test: es la única mejora de texto que el legacy aporta al código vivo.

## 4. Orquestación de flujos y metaprogramación: sin equivalente, con decisiones que citar

Dos generaciones del mismo prompt (`sys_flow_orchestrator` y el `flow_orchestrator` v12) describen
una arquitectura que **no existe todavía** en este codebase. Lo que merece conservarse como decisión
tomada:

* **Prioridad de búsqueda de recursos: LOCAL → ORGANIZATION → PARTNER → GLOBAL.** Y la etiqueta de
  origen en la respuesta al usuario («un compañero de tu organización ya creó…»), que es lo que
  convierte la reutilización en algo que se entiende.
* **No inventar átomos ni parámetros fuera del inventario.** Es la misma regla que el ETL vivo aplica
  a las columnas y que el pipeline de tablas aplica a los datos: si no está, no se adivina.
* **Los disparadores son entidades independientes y los flujos se suscriben a ellos**, no se
  arrastran al lienzo. Con activación perezosa: un disparador sin flujos suscritos no consume nada.
* **Pasos `PLACEHOLDER`** para la lógica que falta, en vez de inventarla: un recordatorio visible en
  el flujo.
* **Análisis de dependencia secuencial** con cableado por `{{variable}}`: si el paso N produce un
  fichero, el N+1 lo recibe explícitamente.

De `sys_metaprogramming` sobrevive una línea: el código generado se normaliza a una función
`transform(data)` que sólo usa las variables declaradas en `inputs`. Es la misma idea que el contrato
`result` de la extracción viva.

## 5. Copiloto: arquitectura distinta

El `copilot_helper` v12 es un copiloto **por modos** (`flow`, `atom`, `wizard`, `documentation`,
`idle`, `triggers`) con el contexto del átomo inyectado. El vivo (`CopilotService`) tiene dos modos
—responder con RAG sobre la documentación interna, y traducir lenguaje natural a configuración— y
responde **con citas**, obligándose a decir «no tengo esa información» cuando no está en el contexto.
Son diseños distintos y el vivo encaja con la gobernanza del proyecto.

Una idea del legacy que sí es aprovechable cuando existan los flujos: **detectar incompatibilidades
de tipos entre pasos** (un paso devuelve texto y el siguiente espera un número). Es una comprobación
determinista, no una tarea de modelo, así que cuando llegue el bloque de automatizaciones va en el
validador, no en el prompt.

## 6. Lo que no aportaba nada

`sys_llm_process` («resumen, clasificación, traducción, análisis de sentimiento…») es un prompt
genérico de procesado de texto. Los nodos de redacción vivos (SEG.2) son mucho más específicos: no
calcular, respetar «No hay valor», mencionar todas las tablas, dejar la reflexión cualitativa a quien
firma. No hay nada que portar.

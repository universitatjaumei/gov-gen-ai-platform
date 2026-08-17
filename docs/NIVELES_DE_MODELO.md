# Niveles de modelo (tiers): cuál es cuál

`hub_llm_configs.tier` vale 1, 2 o 3, y **el número no dice nada por sí mismo**. Esto es lo
que significa cada uno y quién lo usa. Se asigna desde el panel, en **Modelos IA**
(`/hub/llm-configs`): cada configuración lleva su nivel y una marca «por defecto», y la que
está marcada por defecto en un nivel es la que se usa. Marcar una releva a la anterior del
mismo nivel en la misma transacción (FIX.1), así que nunca hay dos ni ninguna.

| Nivel | Para qué | Quién lo pide hoy |
|---|---|---|
| **1** | Conversar y redactar: respuestas del asistente, redacción de bloques de informe, propuesta de plantilla, análisis de HTML en la ingesta | El grafo de chat, `RedactorDeBloques`, `LLMSpecService`, el analizador de la ingesta |
| **2** | **Programar**: escribir el script de extracción que pide una persona en lenguaje natural | `ScriptProposalService` (PRO.2). Le seguirá el ETL en modo IA (PRO.4) |
| **3** | **Juzgar código ajeno**: la auditoría con modelo del script propuesto | La revisión que acompaña a cada propuesta (PRO.2) |

Los niveles 2 y 3 son de PRO.2 y responden a una petición explícita: **escribir código y
juzgar si es peligroso son tareas distintas**, así que no las hace el mismo modelo. El 3 es el
superior de los dos.

## Qué actividad usa qué nivel

El mapa vive en **código**, en `server/app/modules/redaccion/services/actividades_llm.py`, y
es también la lista de actividades que existen. La base de datos sólo guarda excepciones
(PRO.2.1). Es la forma que tenía la aplicación NiceGUI: `DEFAULT_TIER_MAPPING` en código y
`tier_override` en la tabla.

## Qué pasa si falta un nivel

La petición devuelve **503 diciendo qué nivel falta y para qué servía**:

> No hay modelo configurado para el nivel 3, que es el que audita el script escrito.
> Asígnale uno en Modelos IA.

No es un detalle de estilo: con dos niveles en juego, «falta un modelo» obliga a adivinar cuál
de los dos configurar.

## La auditoría con modelo no sustituye a la determinista

El script pasa **primero** por el auditor de AST (`script_auditor.py`, PRO.1), que no se puede
convencer: llamadas prohibidas, introspección del intérprete, módulos de la denegación
explícita y rutas absolutas. **Después** lo mira el modelo de nivel 3, que ve lo que un AST no
puede ver —si hace lo que se pidió, si asume columnas que no constan, si puede devolver vacío
sin fallar—. Su veredicto (`acepta` / `duda` / `rechaza`) viaja con la propuesta hasta quien la
revisa y **no cambia** el resultado de la auditoría determinista.

Sobre un script con un hallazgo **crítico** no se pide la segunda opinión: no se va a ejecutar
nunca, así que juzgar su semántica es pagar una llamada por una opinión sobre código muerto.

## Configuraciones de la base de desarrollo

Creadas desde el panel el 2026-08-17, las dos con el proveedor Google que ya estaba:

| Etiqueta | Modelo | Nivel |
|---|---|---|
| Nivel 2 — escribe scripts (PRO.2) | `gemini-2.5-flash` | 2 |
| Nivel 3 — audita scripts (PRO.2) | `gemini-2.5-pro` | 3 |

`gemini-2.5-flash` es el mismo modelo que el nivel 1 por defecto: el nivel es un **papel**, no
una promesa de que el modelo sea distinto. Lo que importa es que el 3 sea superior al 2, y
`pro` lo es respecto de `flash`.

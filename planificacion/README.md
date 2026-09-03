# `planificacion/` — el plan, el cursor y el historial

Estos documentos no describen el producto: **lo dirigen**. Son los instrumentos con los que se
ejecuta el desarrollo, y cambian a diario. La documentación estable —arquitectura, decisiones,
manuales— vive en `docs/`.

> **Si lo que buscas es qué garantiza el sistema, esto no es.** Un plan dice «haz X»; lo que
> puedes dar por cierto al construir encima está en
> [`../docs/ESPECIFICACIONES.md`](../docs/ESPECIFICACIONES.md), organizado por capacidad y no por
> orden de ejecución. Aquí está **qué falta y en qué orden**; allí, **qué se puede romper**.

| Fichero | Para qué |
|---|---|
| `PROJECT_STATE.md` | **La fuente de verdad del progreso.** Cursor actual, planes activos, modelo sugerido para el próximo prompt y los bloques cerrados recientes. Se lee al arrancar cada sesión. |
| `HISTORIAL.md` | El archivo: una fila por prompt cerrado, con qué se desvió del plan y qué defecto apareció al verificar. Se consulta para saber **por qué** algo se hizo así. |
| `PLAN_DESARROLLO.md` | El plan a alto nivel: fases, subfases y qué entrega cada una. |
| `PLAN_TDD_DETALLADO.md` | Prompts detallados de las fases iniciales. |
| `Plan_TDD_Fase1.md` | **El índice** de la Fase 1 — hub informativo, personalización y redacción. Es el plan en curso. Eran 27.449 líneas en un fichero; ahora cada bloque y cada fase viven en `fase1/`, con su número de orden delante. |
| `fase1/` | Un fichero por bloque o fase: los prompts, sus tests mínimos y su verificación. Es lo que se lee para implementar, y lo que se puede revisar en un *pull request*. |
| `Plan_TDD_Fase2.md`, `Plan_TDD_Fase3.md` | Fases posteriores, aún sin abrir. |

## Cómo se usan

La metodología está en `CLAUDE.md` y en `docs/METODOLOGIA_AGENTICA.md`. En resumen: el desarrollo
avanza por **bloques** de prompts; cada prompt sigue RED → GREEN → REFACTOR, cierra con un commit
propio, y al cerrarlo se mueve el cursor en `PROJECT_STATE.md` y se añade una fila **arriba** de la
tabla de `HISTORIAL.md`.

Los prompts se leen **verbatim** del plan: están redactados para ejecutarse tal cual, con su
etiqueta de modelo sugerido. Si el plan y el código real no coinciden, se aplica la interpretación
más fiel al prompt y se registra como «desviación documentada» en el historial.

## Por qué están en el repositorio y no sólo en local

Porque sin ellos un clon nuevo no puede continuar el trabajo: se pierde el cursor y se pierden los
prompts. Y porque el historial explica decisiones que el código no explica por sí solo — por qué se
descartó una opción, qué se rompió al intentarlo de la otra manera.

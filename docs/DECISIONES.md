# Registro de decisiones de arquitectura

Las decisiones que condicionan el resto del proyecto, con su fecha y su estado. Un ADR (*Architecture
Decision Record*) en el sentido clásico: **qué se decidió, cuándo, por qué, y qué queda descartado**.

> **Lo vigila un test.** `server/tests/infra/test_decisiones_estan_indexadas.py` comprueba que
> toda decisión de `docs/DECISION_*.md` está en la tabla de abajo y declara `Fecha` y `Estado`.
> Una decisión escrita y no indexada es una decisión que nadie encuentra.

## Por qué existe este registro y no una carpeta `adr/`

Las decisiones **no se han movido** a una carpeta nueva, y es deliberado: hay doce referencias a
sus rutas en `planificacion/HISTORIAL.md` y diez en `PROJECT_STATE.md`. El historial es un
**archivo**, y reescribir entradas pasadas para que apunten a otro sitio sería falsificarlo. Así
que las decisiones se quedan donde están, con el prefijo `DECISION_`, y esta página les da número
y estado.

## Cuándo hace falta un ADR

No todo cambio merece uno. La regla, y viene de lo que ha pasado de verdad en este proyecto:

**Hace falta** cuando el cambio deja fuera una alternativa razonable, y quien venga detrás
preguntaría «¿por qué no lo hicisteis de la otra manera?». Ejemplos reales: retirar Docling,
elegir VM en vez de Cloud Run, no instalar navegador sin cabeza para el rastreo, decidir cuál de
las cuatro tablas de identidad es la de administración.

**No hace falta** para un defecto corregido, un refactor, o un paso del plan que sólo ejecuta algo
ya decidido. Eso va en `planificacion/HISTORIAL.md`, que es donde vive el *por qué* de cada
prompt.

**La diferencia práctica**: si dentro de un año alguien pudiera implementar lo contrario de buena
fe, hace falta ADR. Si sólo repetiría un error ya pagado, basta el historial.

## Cómo se escribe uno

Un fichero `docs/DECISION_<TEMA>.md` con esta cabecera, que es lo que el test exige:

```markdown
# Decisión: <qué se decide, en una frase>

> **Fecha**: AAAA-MM-DD. **Estado**: <aceptada | sustituida por … | revertida>.
> **Origen**: <de dónde salió la pregunta>. **Afecta a**: <bloques, módulos>.
```

Y después, en el cuerpo: la pregunta, las opciones que se consideraron **con lo que las descarta**,
la decisión, y lo que **no** hace. Esa última parte es la que más se agradece: en este proyecto
varias decisiones son precisamente sobre lo que algo no hace.

**Una decisión no se edita para cambiarla.** Se escribe otra que la sustituya, y la vieja pasa a
`Estado: sustituida por …`. Borrar el razonamiento viejo es perder la única prueba de que la
alternativa se consideró.

---

## Las decisiones

| # | Decisión | Fecha | Estado |
|---|---|---|---|
| 1 | [Open WebUI como carcasa de chat desechable](DECISION_OPENWEBUI_CARCASA_CHAT.md) | 2026-07-24 | Aceptada |
| 2 | [Modelos de embedding y reranker: local en edge, API en cloud](DECISION_MODELOS_EMBEDDING_RERANKER.md) | 2026-08-01 | Aceptada, con el reranker **apagado por medición** en Normativa (HIB.A) |
| 3 | [La curación del corpus es previa al asistente, no una función suya](DECISION_CURACION_SEPARADA.md) | 2026-08-02 | Aceptada |
| 4 | [Frontera de la extracción y forma del despliegue](DECISION_EXTRACCION_Y_DESPLIEGUE.md) | 2026-08-10 | Aceptada y aplicada. **Sustituye** a la sección de servicios de computación pesada de `AGENTS.md` |
| 5 | [No se instala navegador sin cabeza para el rastreo](DECISION_RENDERIZADO_RASTREO.md) | 2026-08-18 | Decidida con la medición delante. **Se revisa** si un apartado da un sondeo distinto |
| 6 | [Quién es una cuenta de administración](DECISION_IDENTIDAD_DE_ADMINISTRACION.md) | 2026-09-03 | Aceptada y aplicada; USR.9 cerró el hueco que dejaba anotado |

## Decisiones que viven en otro sitio, y por qué

Tres decisiones estructurales no tienen fichero propio porque su sitio natural es donde se hacen
cumplir. Se listan aquí para que no parezcan olvidadas:

| Decisión | Dónde está escrita |
|---|---|
| El vocabulario del corpus es dato y no `Enum`, y la taxonomía nunca entra en el texto que se embebe | [`../AGENTS.md`](../AGENTS.md) §corpus normativo, y el invariante I3/I4 de [`ESPECIFICACIONES.md`](ESPECIFICACIONES.md) |
| La frontera edge/cloud: dos bases declarativas, sin `relationship()` que las cruce | [`../AGENTS.md`](../AGENTS.md) §frontera Edge-Cloud |
| Se trabaja en `desarrollo`; `main` es para desplegar | [`../AGENTS.md`](../AGENTS.md), tras el despliegue accidental del 2026-09-02 |

**Por qué en `AGENTS.md` y no aquí**: son reglas que un agente tiene que leer **antes** de escribir
código, y un fichero que no se lee no obliga a nada. El registro las apunta; la regla vive donde
se aplica.

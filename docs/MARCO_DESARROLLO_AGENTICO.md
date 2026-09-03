# Marco de desarrollo asistido por agentes

> **Qué es esto.** El método con el que se desarrolla Gov Gen AI Platform, escrito para poder
> aplicarse a otros proyectos. No es una propuesta teórica: es lo que ha quedado después de varios
> meses de ensayo y error en un proyecto real, contrastado con lo que hay publicado.
>
> **Fecha**: 2026-09-03. **Ámbito**: desarrollo de software con agentes de programación bajo
> supervisión humana.

---

## 0. Cómo leer este documento

Está escrito para tres lectores distintos, y conviene saber cuál eres:

| Si eres… | Lee |
|---|---|
| Quien decide si adoptar esto | §1 (la evidencia), §2 (los principios), §10 (la comparación) |
| Quien va a trabajar así | §3 a §7, y sobre todo **§9, lo que nos ha fallado** |
| **Un agente que tiene que montar los documentos de un proyecto nuevo** | §11, que lleva el orden, el prompt de arranque y las plantillas |

**Las tres capas de credibilidad.** Este documento mezcla tres cosas que no valen lo mismo, y las
marca siempre:

- **[Evidencia]** — hay estudio publicado detrás. Se cita.
- **[Convención]** — es práctica establecida o estándar emergente, sin evidencia cuantitativa.
- **[n=1]** — es nuestra experiencia en **un** proyecto. Puede ser un acierto o una casualidad, y
  lo honesto es no presentarlo como más de lo que es.

La sección más útil para otro equipo es probablemente §9, que es toda `[n=1]` y toda negativa: los
errores que ya pagamos.

---

## 1. Qué problema resuelve, y qué dice la evidencia

### 1.1 El dato incómodo del que hay que partir

En julio de 2025, METR publicó un **ensayo controlado aleatorizado**: 16 desarrolladores
experimentados, 246 tareas reales en sus propios repositorios (proyectos de más de 22.000 estrellas
y más de un millón de líneas). Resultado: con acceso a herramientas de IA fueron **un 19 % más
lentos** — y creían haber sido un 20 % más rápidos. Habían pronosticado un 24 % de mejora
**[Evidencia]**.

Ese estudio se cita mucho y casi siempre mal, en las dos direcciones. Dos matices que lo hacen
utilizable:

1. **La misma organización estima que un año después esos desarrolladores serían un 18 % más
   rápidos.** El dato de 2025 no es una ley: es una foto de unas herramientas concretas en un
   momento concreto **[Evidencia]**.
2. **La brecha entre percepción y realidad fue de casi 40 puntos.** Eso sí es estructural y no
   depende del modelo: quien usa un agente **no sabe por introspección** si le está yendo bien.

De ahí sale el primer requisito de cualquier método serio en esto: **medir, no sentir**.

### 1.2 Por qué el método importa más que la herramienta

El informe DORA de 2025 sobre desarrollo asistido por IA —cerca de 5.000 profesionales y más de
100 horas de datos cualitativos, con una adopción del 90 %— concluye que la IA actúa como
**amplificador**: multiplica las fortalezas de una organización y también sus debilidades. Su frase
resumen es la mejor justificación de este documento: *«velocidad sin estabilidad es caos
acelerado»* **[Evidencia]**.

Traducido: un equipo con tests, revisión y trazabilidad va a ir mejor con agentes. Un equipo sin
eso va a producir más deuda, más rápido. **El agente no arregla el método; lo revela.**

### 1.3 Y por qué la supervisión no es opcional

El informe de tendencias de codificación agéntica de Anthropic de 2026 encuentra un reparto
revelador: los humanos toman alrededor del **70 % de las decisiones de planificación** y sólo cerca
del **20 % de las decisiones de ejecución** **[Evidencia]**.

Eso describe exactamente el equilibrio que buscamos, y explica por qué el método se concentra en la
planificación y en las puertas de cierre, no en vigilar cada comando.

En la industria hay al menos dos taxonomías de autonomía —cinco niveles al estilo de la conducción
autónoma, y una de seis niveles con controles alineados al riesgo— y coinciden en algo: **el nivel
máximo no es apropiado para producción hoy**, porque los mecanismos de control que lo harían seguro
no existen todavía **[Convención]**.

---

## 2. Principios

Seis. Están ordenados: cuando dos chocan, gana el de arriba.

### P1 — Agentes supervisados, no autónomos

El agente ejecuta, mide y demuestra. **Las decisiones que cambian el producto son humanas.** No es
desconfianza en el modelo: es que una decisión de diseño mal tomada se paga durante años, y quien
paga es quien mantiene.

En la práctica esto se concreta en **cuatro y sólo cuatro causas para interrumpir** al humano a
mitad de trabajo (§5.3). Menos causas y el agente se atasca; más, y la supervisión se vuelve ruido
que se ignora — que es la forma habitual en que muere una barrera.

### P2 — Nada se reporta sin medirlo

Si una cifra no se ha medido, no se dice como medida. Si un test no se ha ejecutado, no se dice que
pasa. Si algo se verificó en navegador, se dice **con qué evidencia**: qué URL, qué texto
encontrado, qué decía la consola.

Es el principio que la brecha de percepción de METR obliga a tener **[Evidencia]**.

### P3 — Lo determinista antes que el modelo

Si algo se puede calcular, se calcula. El modelo se reserva para lo que sólo él puede hacer:
redactar, valorar, interpretar lenguaje. Una tabla de datos la produce código; una valoración de
esa tabla, el modelo, y sujeta a aprobación humana.

### P4 — Una sola fuente de verdad por cosa

Cada hecho vive en un sitio. Los demás **apuntan**, no copian. Dos documentos que dicen lo mismo
divergen, y el día que divergen los dos mienten: no se sabe cuál.

### P5 — El *por qué* se escribe, no sólo el *qué*

El *qué* está en el diff. Lo que se pierde es por qué se descartó la otra opción, y eso se paga
cuando alguien la reimplementa de buena fe seis meses después. Tres destinos según el alcance: el
**docstring** si es local, el **historial** si es del paso, un **registro de decisión** si
condiciona al resto (§4).

### P6 — Lo que hay que mantener al día, se pone rojo cuando miente

Un documento que envejece es peor que no tenerlo, porque **miente con autoridad**. Todo documento
que se pueda comprobar mecánicamente, se comprueba con un test de la suite (§6).

---

## 3. El modelo de permisos: qué se autoacepta y qué no

Esta es la sección más transferible del documento, porque es la que se puede copiar casi literal.

### 3.1 La forma: tres cubos y una guarda

Los agentes de programación modernos permiten declarar permisos en tres cubos: **permitir**
(ejecuta sin preguntar), **preguntar** (eleva al humano) y **denegar** (no se ejecuta nunca). Sobre
eso añadimos un **hook** que inspecciona el comando antes de ejecutarlo y decide, porque los
patrones de texto no bastan: `rm -rf` puede ser legítimo dentro del directorio de trabajo y
catastrófico fuera.

Esto coincide con lo que la literatura sobre **supervisión humana graduada** en generación de
código recomienda: la intensidad de la supervisión escala con el riesgo, y los mecanismos concretos
son puertas de revisión, **matrices de permisos**, registros de auditoría y despliegue por etapas
**[Evidencia]**.

### 3.2 El criterio: tres familias suben siempre al humano

Nuestra guarda clasifica cada comando y eleva si cae en una de estas tres. Todo lo demás es trabajo
normal de desarrollo y se aprueba solo **[n=1, y es el corazón del modelo]**:

| Familia | Qué incluye |
|---|---|
| **A. Sistema operativo** | Particiones, arranque, servicios, registro, cuentas locales, firewall, tareas programadas, ACL, apagado, elevación, instalación de software, ejecución de código descargado |
| **B. Borrado fuera de las raíces permitidas** | Cualquier borrado fuera del directorio de trabajo y del temporal |
| **C. Pérdida irreversible de datos o de historial** | `git push --force`, poda de volúmenes, `DROP DATABASE`, `git clean -xdf` |

La lógica es que las tres tienen la misma propiedad: **no se pueden deshacer con `git revert`**. Lo
que se puede deshacer con git no necesita permiso; lo que no, siempre.

### 3.3 Lo que sí se autoacepta

Esto es deliberadamente amplio, y es lo que hace el método viable: si cada comando pide permiso, el
humano deja de leer y aprueba en bloque, que es peor que no preguntar.

```jsonc
// Se ejecuta sin preguntar
"Read(*)", "Edit(*)", "Write(*)", "Glob", "Grep",
"Bash(git *)",            // incluido commit; el force-push lo captura el cubo de preguntar
"Bash(uv *)",             // gestor de paquetes y ejecutor de Python
"Bash(npm *)", "Bash(npx *)", "Bash(node *)",
"Bash(pytest *)", "Bash(alembic *)",   // tests y migraciones
"Bash(docker compose *)", "Bash(curl *)", "Bash(gh *)"
```

**Escribir ficheros del proyecto se autoacepta.** Es la decisión que más sorprende y la que más
defiendo: el trabajo del agente **es** escribir ficheros, todo está en git, y pedir permiso por
edición convierte la supervisión en un clic reflejo. Lo que se supervisa no es la edición: es el
**cierre** (§5.2).

### 3.4 Lo que exige autorización, y lo que no se ejecuta nunca

```jsonc
// Preguntar (extracto)
"Bash(sudo *)", "Bash(shutdown *)", "Bash(diskpart *)", "Bash(reg *)",
"Bash(net user *)", "Bash(netsh *)", "Bash(schtasks *)", "Bash(icacls *)",
"Bash(winget *)", "Bash(msiexec *)",
"Bash(git push --force *)", "Bash(git clean -xdf*)",
"Bash(docker system prune*)", "Bash(docker volume rm*)",
"Edit(C:/Windows/**)", "Write(C:/Program Files/**)"

// Denegar: no se ejecuta ni preguntando
"Bash(rm -rf /)", "Bash(rm -rf ~)", "Bash(mkfs*)", "Bash(dd if=*)",
"PowerShell(Format-Volume*)", "PowerShell(Clear-Disk*)", "Bash(bcdedit *)"
```

**La diferencia entre «preguntar» y «denegar»** es si existe un caso legítimo. `git push --force`
lo tiene —reescribir un historial con datos filtrados, que nos pasó— así que pregunta. `mkfs` sobre
el disco del portátil no lo tiene nunca: se deniega, y así no hay un momento de despiste en que se
apruebe.

### 3.5 La regla que hace que esto funcione

**La guarda tiene sus propios tests.** Un mecanismo de seguridad sin tests es una intención: nadie
sabe si sigue funcionando después del siguiente refactor. Y **el agente no busca rodeos**: si la
guarda eleva algo, se para y pregunta; intentar otro camino para el mismo efecto es violar el
método, no ser eficiente.

---

## 4. Los documentos que rigen el desarrollo

Siete, cada uno contesta **una** pregunta. La disciplina está en no dejar que uno contesté la de
otro (P4).

| Documento | Contesta | Cambia |
|---|---|---|
| **Reglas** (`AGENTS.md`) | ¿Cómo se trabaja aquí? Qué está prohibido | Rara vez |
| **Especificaciones** | ¿Qué **garantiza** el sistema? ¿Qué no puedo romper? | Cuando cambia una garantía |
| **Plan** (prompts TDD) | ¿Qué falta, y en qué orden? | Al planificar |
| **Cursor** | ¿Dónde estamos ahora mismo? | Cada paso |
| **Historial** | ¿Por qué esto está así? ¿Qué se midió? | Cada paso, añadiendo |
| **Registro de decisiones** | ¿Por qué no se hizo de la otra manera? | Cuando se descarta una alternativa |
| **Contribución** | ¿Cómo aporto desde fuera? | Rara vez |

### 4.1 Las reglas: `AGENTS.md`

**Usa el nombre estándar.** `AGENTS.md` se formalizó en agosto de 2025 con participación de OpenAI,
Google, Cursor, Factory y Sourcegraph; pasó de unos 20.000 repositorios a más de 60.000 en
diciembre de 2025, cuando la especificación se donó a la *Agentic AI Foundation* de la Linux
Foundation. Más de veinte herramientas lo leen **[Convención, con adopción medida]**.

Es Markdown plano sin esquema obligatorio. Si tu herramienta busca otro nombre —Claude Code busca
`CLAUDE.md`—, ese fichero debe ser de tres líneas que **importan** el canónico, para que no haya
dos versiones que puedan divergir (P4).

> **Un hallazgo contra nosotros, y lo que hicimos con él.** El estudio empírico sobre ficheros de
> contexto para agentes encuentra que **la longitud moderada funciona mejor** que la exhaustiva, que
> las instrucciones **explícitas** pesan más que los ejemplos implícitos, y que los agentes
> **se saltan** el contenido verboso y redundante **[Evidencia]**.
>
> Nuestro `AGENTS.md` tenía **40 KB**. Al medirlo apareció algo peor que la longitud:
> **el 28 % duplicaba `docs/METODOLOGIA_AGENTICA.md`** —las cuatro causas de parada, el bucle, el
> informe de cierre y el protocolo de verificación estaban escritos dos veces, con redacción
> distinta—. Es una violación de P4 **dentro del fichero que enuncia P4**, y ya había costado una
> edición doble.
>
> Se partió el 2026-09-03 por **registro y no por tema**: el imperativo se queda —es lo que se lee
> antes de escribir código— y el relato se va al documento que lo explica, dejando **una cláusula**
> de por qué junto a cada regla. Resultado: **de 40 a 33 KB**, con un guardarraíl que comprueba que
> los punteros resuelven, que los dieciocho imperativos siguen ahí y que el fichero no vuelve a
> crecer.
>
> **Y sigue siendo mucho.** 33 KB no es «longitud moderada» por ninguna medida; la ganancia real
> fue quitar la doble fuente de verdad, no el tamaño. La recomendación para quien empiece es la
> misma y más fuerte: **no llegues ahí**. Reglas duras y accionables en el fichero principal, y el
> razonamiento largo en documentos aparte que el fichero enlace, desde el primer día.

### 4.2 Las especificaciones: qué garantiza el sistema

Es el documento que más tardamos en escribir y el que más falta hacía. Un plan dice «haz X»; una
especificación dice **«el sistema garantiza Y»**, y sólo lo segundo permite saber qué se puede
cambiar sin romper nada.

Se organiza **por capacidad, no por orden de ejecución**, y cada una lleva el mismo esqueleto:

```markdown
### 5.2 Política de lengua

**Qué hace.** Decide en qué lengua responde un asistente.

**Garantiza.** Tres modos y sólo tres, configurables en cascada y validados al escribirse.
Un valor que no sea uno de los tres da 422 con los modos enumerados.

**Superficie.** `core/language_mode.py` · `hub_opciones_router` · dos columnas en cascada.

**Invariantes.** I3, I10.

**Madurez**: `construido`.

**Abierto.** Ningún despliegue monolingüe real lo ha usado todavía.
```

Y su pieza central es una **tabla de invariantes**, cada uno con **dónde se hace cumplir**:

| # | Invariante | Se hace cumplir en |
|---|---|---|
| I1 | Una respuesta sin cita válida no se entrega | `citation_validator.py` |
| I5 | Una lista de organizaciones vacía significa «ninguna», no «todas» | `core/auth/tenancy.py` |
| I9 | Un docstring no autoriza nada: declarar un módulo obliga a exigirlo | `test_router_inventory_is_walked.py` |

**La columna derecha es lo que distingue un invariante de una intención.** Un invariante que sólo
vive en un documento no obliga a nada.

**Cuatro palabras de madurez y no un porcentaje**: `producción`, `construido`, `parcial`,
`previsto`. Un porcentaje hay que revisarlo; cuatro palabras no. Y **la madurez la mueve el
despliegue**, no el cierre del trabajo **[n=1, aprendido equivocándonos]**.

### 4.3 El plan: especificaciones en forma de prompts TDD

El trabajo pendiente se escribe como **instrucciones ejecutables**, agrupadas en **bloques**. Cada
prompt lleva su objetivo, sus tests mínimos enumerados y su verificación de cierre:

```markdown
### Prompt LANG.1 (RED/GREEN) — Cablear `language_mode`

**Modelo sugerido**: Sonnet — alcance cerrado: dos clases sobre un protocolo existente.

**Objetivo**: que `cfg.language_mode` decida la política que compone la factoría.

## Tests (mínimo 6)
- `none`: el prompt final NO contiene «Responde en» y no se lanza segunda búsqueda.
- `fixed:es` con pregunta en catalán: el prompt instruye responder en es.
- `prefer`: comportamiento idéntico al actual (test de regresión).
- 422 del endpoint con `language_mode="castellano"`.

**Verificación**: suite del directorio verde, y una conversación real contra un chatbot en
`fixed:es` preguntando en catalán, respondida en castellano (evidencia en el informe de cierre).
```

Tres detalles que hacen la diferencia **[n=1]**:

- **Los tests van enumerados en el prompt.** Escribir «añade tests» produce tests que confirman lo
  que el código hace. Enumerarlos antes fija qué tiene que ser cierto.
- **Un test de regresión explícito** en todo prompt que cambie algo existente.
- **La verificación dice qué evidencia hace falta**, no «comprobar que funciona».

**Y una lección de tamaño**: nuestro plan de fase 1 llegó a **27.449 líneas en un solo fichero**.
No se puede revisar en un *pull request* ni comentar por línea. Hay que partirlo **un fichero por
bloque desde el principio**.

### 4.4 El cursor y el historial

**El cursor** dice dónde estamos: qué bloque, qué paso, qué quedó cerrado. Se actualiza siempre.

**El historial** es una fila por paso cerrado, añadida **arriba**, con lo que sólo se sabe después:
la cifra que salió, el doble de test que mentía, la alternativa que no funcionó. Es el documento
que ninguna herramienta del mercado te da y el que más agradece quien llega después **[n=1]**.

Ejemplo de fila real, y fíjate en que lo valioso es la parte negativa:

> **USR.8** — El asistente agéntico tenía **0 interacciones registradas** mientras los de RAG
> tenían 33, 9 y 1. Todas sus conversaciones se perdían. Causa: `"".join(collected_tokens)` con
> `TypeError` porque el proveedor devuelve el contenido como lista de bloques. **Son dos defectos**:
> el contenido en bloques y que el tramo posterior estaba fuera de todo `try`, así que el cliente
> no recibía ni un evento de error. Tercera vez que muerde el mismo problema.

**Separa el historial del cursor en cuanto crezca.** El nuestro llegó a ser 535 de los 626 KB del
fichero del cursor, que se lee entero al arrancar cada sesión.

### 4.5 El registro de decisiones (ADR)

Formato clásico de *Architecture Decision Record*: qué se decidió, cuándo, por qué, y **qué queda
descartado** **[Convención, establecida desde 2011]**.

```markdown
# Decisión: <qué se decide, en una frase>

> **Fecha**: AAAA-MM-DD. **Estado**: aceptada | sustituida por … | revertida.
> **Origen**: <de dónde salió la pregunta>. **Afecta a**: <módulos>.
```

**El criterio de cuándo hace falta uno** es lo que evita los dos extremos —nadie escribe ninguno, o
se escribe uno por cada corrección—:

> Si dentro de un año alguien pudiera implementar **lo contrario** de buena fe, hace falta ADR. Si
> sólo repetiría un error ya pagado, basta una fila del historial.

Y: **una decisión no se edita para cambiarla.** Se escribe otra que la sustituya, y la vieja pasa a
`sustituida por…`. Borrar el razonamiento viejo pierde la prueba de que la alternativa se
consideró.

### 4.6 Comparación con los marcos publicados

| | Spec Kit (GitHub) | Este marco |
|---|---|---|
| Principios no negociables | `constitution.md` | `AGENTS.md` |
| Qué construir | `spec.md` | Plan por prompts |
| Plan técnico | `plan.md` | Dentro de cada prompt |
| Tareas ordenadas | `tasks.md` | Cursor |
| **Qué garantiza el sistema** | — | **Especificaciones** |
| **Por qué se hizo así** | — | **Historial + ADR** |
| **TDD obligatorio** | — | **Sí, y es lo que más protege** |
| **Documentación con test** | — | **Guardarraíles (§6)** |

La forma coincide **[Convención]**: hay convergencia real de la industria en «principios → qué →
plan → tareas». Lo que añadimos son las cuatro filas de abajo, y de esas la que yo defendería
primero ante otro equipo es **TDD obligatorio**, porque es la que hace que el resto sea comprobable
y no una declaración de intenciones.

---

## 5. El ciclo de trabajo

### 5.1 El bloque es la unidad de interacción

Un **bloque** es un conjunto de prompts que entregan algo utilizable. Una vez arrancado, el agente
**no informa hasta cerrarlo**: no pide confirmación entre pasos.

Esto es lo que hace el método rentable, y encaja con el reparto que mide Anthropic —el humano en la
planificación, el agente en la ejecución **[Evidencia]**. Confirmar cada paso convierte al humano
en un cuello de botella que además deja de leer.

### 5.2 El bucle por paso

```
RED → GREEN → REFACTOR → verificaciones de cierre → actualizar el cursor → un commit firmado
```

**Un commit por paso, firmado.** Es lo que hace reversible un bloque largo: si el paso 5 rompe lo
que hizo el 3, hay un punto exacto al que volver. Sin eso, un bloque de siete pasos es un solo
commit gigante que no se puede revertir a medias **[n=1, y de las cosas que más han servido]**.

Las **verificaciones de cierre** son la supervisión real, y por eso los permisos pueden ser amplios
(§3.3): suite verde en los directorios tocados, migración aplicada, contrato regenerado si cambió
la API, retirada del código viejo comprobada con búsqueda a cero, y verificación en navegador si
toca interfaz.

### 5.3 Cuándo interrumpir al humano, y cuándo no

**Sólo por estas cuatro causas:**

1. **Operación de riesgo** — la detecta la guarda (§3). No se fuerza ni se busca rodeo.
2. **Decisión de criterio** — ambigüedad que llevaría a productos distintos, arquitectura que el
   plan no cierra, alcance que excede el bloque.
3. **Fallo persistente** — un rojo que no llega a verde. Se para y se reporta **con la salida
   real**.
4. **Prerrequisito externo ausente** — base de datos apagada, credencial que falta.

**Y explícitamente NO se interrumpe por**: desviaciones entre el plan y el código real —se aplica
la interpretación más fiel, se registra como *desviación documentada* y se sigue—, fallos
preexistentes ya inventariados, o dudas de estilo que las reglas ya resuelven.

Enumerar las causas de **no** interrumpir es tan importante como las de sí. Sin esa lista el agente
pregunta por todo, y la supervisión se degrada a aprobación automática **[n=1]**.

### 5.4 Tests escalonados

| Cuándo | Qué | Coste |
|---|---|---|
| Durante el paso | Sólo el fichero de tests que se está escribiendo | segundos |
| Al cerrar el paso | Los directorios que toca + el test de higiene de la suite | segundos a 1 min |
| Al cerrar el bloque | La suite entera | minutos a una hora |

La suite completa después de cada cambio no aporta información nueva y sí una hora de espera. El
test de higiene entra en el nivel intermedio porque tarda medio segundo y caza justo lo que se
escapa de un subconjunto: mocks mal puestos, creación de esquema sobre la base del desarrollador,
imports a módulos que ya no existen.

### 5.5 Verificación en navegador por el propio agente

Si el trabajo toca interfaz, **el agente lo comprueba él mismo en un navegador real** dentro del
bloque: navega, busca el texto, interactúa, y lee la consola y las peticiones de red buscando
errores que los tests unitarios no ven.

Las **pruebas manuales humanas se reservan** a lo irreducible: credenciales reales, sistemas
externos no simulables, juicio de identidad visual, lector de pantalla real, datos personales. Y se
entregan como un guion ejecutable, no como una lista de deseos.

Esto no es cosmético. En nuestro proyecto, la verificación en navegador ha encontrado defectos que
la suite no veía **y que la suite no podía ver**: un 500 en un login, un flujo que no terminaba
nunca, y una etiqueta que decía «Editar» y lo que hacía era activar un asistente **[n=1]**.

### 5.6 El informe de cierre

Un solo mensaje con: pasos cerrados y sus commits, **cifras reales** por suite, migraciones
aplicadas, qué se verificó en navegador y con qué evidencia, desviaciones documentadas, lo que
queda pendiente, las pruebas manuales, y **una línea diciendo qué cambió en las especificaciones o
por qué no cambió nada**.

Esa última parte es la que sostiene el mantenimiento de la documentación: **obligar a afirmar la
omisión** convierte «me lo salté» en una frase revisable.

---

## 6. Guardarraíles: documentación que se pone roja

### 6.1 La idea

Todo documento que se pueda comprobar mecánicamente tiene un test en la suite que falla cuando el
documento miente. No es documentación *sobre* el código: es documentación **comprobada por** el
código.

Es la respuesta operativa a P6, y no la he visto en ninguno de los marcos publicados **[n=1]**.

### 6.2 Los cinco tipos que usamos

| Tipo | Qué comprueba | Ejemplo real |
|---|---|---|
| **Inventario completo** | Que el documento nombra **todo** lo que el código declara | Toda tabla de configuración está en el inventario de multitenencia con su ámbito |
| **Vocabulario sincronizado** | Que las listas del documento son las del código | Los modos de lengua del documento son los que el validador acepta |
| **Referencias vivas** | Que las rutas y ficheros que nombra existen | Las 35 rutas de la especificación |
| **Regla presente** | Que una regla no ha desaparecido del fichero de reglas | Que la regla de mantener la especificación sigue ahí **y conserva su condición** |
| **Clase de defecto** | Que un patrón que ya falló no vuelve | Que nadie lee el contenido del modelo sin normalizarlo |

### 6.3 La trampa: el guardarraíl que pasa en el vacío

**Esto es lo más importante de la sección.** Un guardarraíl que recorre un directorio inexistente
no encuentra nada, y por tanto **pasa en verde sin mirar nada**. Nos ocurrió: un test que prohibía
un patrón usaba una ruta mal calculada y llevaba días en verde sin haber comprobado una sola línea.
Se descubrió por casualidad, al copiarlo **[n=1, y es el error más peligroso del método]**.

Es peor que un falso negativo normal porque **no hay cifra extrema que dé el aviso**: un verde no
llama la atención de nadie.

Dos reglas que lo evitan:

```python
# 1. La raíz se comprueba, no se supone.
RAIZ = Path(__file__).resolve().parents[3]
assert (RAIZ / "docs").is_dir(), f"la raíz no es la que se cree: {RAIZ}"

# 2. El test tiene que demostrar que sabe encontrar lo que busca:
#    se escribe primero contra el estado que SÍ tiene ocurrencias, y se ve rojo.
```

Y la práctica que lo cierra: **sabotear el documento a propósito y ver el rojo** antes de dar el
guardarraíl por bueno. Un guardarraíl que sólo se ha visto en verde no se ha visto.

### 6.4 Un guardarraíl completo, como plantilla

```python
"""El registro de decisiones no puede quedarse corto.

Una decisión escrita y no indexada es una decisión que nadie encuentra: quien venga detrás
implementará lo contrario de buena fe.
"""
RAIZ = Path(__file__).resolve().parents[3]
assert (RAIZ / "docs").is_dir(), f"la raíz no es la que se cree: {RAIZ}"


def _decisiones() -> list[Path]:
    encontradas = sorted((RAIZ / "docs").glob("DECISION_*.md"))
    assert encontradas, "no se ha encontrado ninguna: la ruta está mal y esto pasaría en vacío"
    return encontradas


@pytest.mark.parametrize("decision", _decisiones(), ids=lambda p: p.stem)
def test_should_be_listed_in_the_register(decision, registro):
    assert decision.name in registro, (
        f"`{decision.name}` no está en el registro. Una decisión escrita y no indexada es una "
        "decisión que nadie encuentra."
    )
```

Fíjate en tres cosas: el `assert` de la raíz, el `assert` de que la búsqueda encontró algo, y que
**el mensaje de error explica la consecuencia**, no sólo el hecho. Quien se encuentre ese rojo
dentro de un año tiene que entender por qué importa.

---

## 7. Integración continua

### 7.1 Las puertas

CI no es «que pasen los tests». Son puertas con propósito, y cada una existe por algo que pasó:

| Puerta | Por qué |
|---|---|
| Lint | Corre **antes** de los tests: un import sin usar deja el trabajo en rojo sin que nada se ejecute |
| Dependencias con *lock* verificado | Instalar sin verificar vuelve a resolver en silencio, y un *lock* que no corresponde a su manifiesto no da ningún síntoma |
| Contrato regenerado y tipado | El cliente del frontend se genera del contrato del backend; si no compila, el contrato se rompió |
| Suite completa | En **una sola invocación** |
| Puerta de control de acceso | Un subconjunto de tests de aislamiento que **bloquea el despliegue** |
| Puerta de regresión de calidad | Falla si una métrica baja más de un umbral respecto a una línea base versionada |
| Accesibilidad | Base mínima que no puede empeorar |
| Certificado de origen (DCO) | Cada commit va firmado |

### 7.2 En CI el paralelismo se apaga, a propósito

En local los tests corren en paralelo por velocidad. **En CI, no.** El paralelismo reparte los
tests entre procesos y eso **esconde el estado filtrado entre tests** —un mock asignado a una
clase, un singleton contaminado—, que es justo lo que se quiere cazar. En local manda la velocidad;
en CI, la detección **[n=1]**.

### 7.3 Ramas: trabajar y desplegar no son lo mismo

El trabajo va a una rama de desarrollo; la rama principal **es la que despliega**. CI y la firma
corren en las dos; el despliegue, sólo en la principal.

Esto lo aprendimos de la peor manera: un commit que sólo tocaba un guion de publicación desplegó
producción entera, con su reinicio y su aviso de vigilancia **[n=1]**. La regla que lo cierra es
que **el fichero de despliegue no lleva la rama de desarrollo en su disparador**, y si algún día
aparece ahí, la separación desaparece.

---

## 8. Apertura del repositorio

### 8.1 Licencia

Nuestro proyecto usa **AGPL-3.0-or-later**. El razonamiento, que es el que hay que replicar y no la
elección:

- Es software para **administraciones públicas**, financiado con dinero público. Que las mejoras
  vuelvan a la comunidad es coherente con su origen.
- La AGPL cubre el **§13**: quien ofrezca el software como servicio en red tiene que ofrecer la
  fuente a sus usuarios. Con GPL a secas, un despliegue SaaS de un tercero no obliga a nada.
- Titularidad institucional, autoría personal. Se distinguen.

**Para otro proyecto la elección puede ser otra**, y lo que este marco pide es que esté **razonada
por escrito**, no que sea AGPL.

### 8.2 Certificado de origen (DCO)

Cada commit lleva `Signed-off-by`, con `git commit -s`. Certifica que quien commitea tiene derecho
a aportar ese código bajo la licencia del proyecto. Lo comprueba un *workflow*.

**Se exige también al mantenedor**, y eso no es simetría decorativa: un mantenedor que se exceptúa
de su propia política la deja sin fuerza.

### 8.3 Issues y la vía para proponer

Dos plantillas, y la segunda es la que importa en un proyecto multiorganización:

**Fallo** — qué pasó, qué se esperaba, cómo reproducirlo, y **en qué modo de despliegue y con qué
configuración**: el mismo código se comporta distinto según cómo esté configurado.

**Propuesta** — con una pregunta central que decide todo:

```markdown
## Qué falta

## Por qué lo necesita **cualquier** organización
<!-- La pregunta que decide si esto es material del principal o de tu fork.
     Si otra administración diría «me da igual», es material de fork. Si diría «lo necesito
     pero al revés», entonces lo que se propone no es la funcionalidad sino la OPCIÓN DE
     CONFIGURACIÓN que permite las dos. -->

## Cómo lo resuelves hoy
<!-- Si tienes un apaño en tu fork, cuéntalo: suele ser la mitad del diseño. -->

## Lo que NO debería hacer
<!-- Los límites de una propuesta se olvidan antes que su objetivo. -->
```

**Se propone antes de escribir código.** Contestar esa pregunta primero ahorra escribir lo que no
puede entrar.

Y la plantilla de *pull request* empieza por la misma pregunta: **¿por qué esto es generalizable?**

### 8.4 Un principal y tantos *forks* como organizaciones

El repositorio principal decide la dirección. Cada organización que despliegue trabaja sobre **su
fork**, y lo generalizable sube por *pull request*. **La regla vale también para la institución
donde nació el proyecto**: su desarrollo entra como aportación, no como dirección.

Sin esa regla, en poco tiempo el principal *sería* el sistema de una institución concreta y el
resto heredaría decisiones tomadas para un contexto que no es el suyo.

### 8.5 Lo que la especificación no resuelve

Advertencia práctica **[n=1]**: para abrir un repositorio, la documentación resuelve «qué no puedo
romper». No resuelve **«qué tarea cojo»**. Eso son *issues*, y sin ellos quien llega no tiene por
dónde entrar. Nosotros llegamos a tener toda la documentación y **cero issues**, que es la mitad del
trabajo sin hacer.

---

## 9. Lo que nos ha fallado

Toda esta sección es `[n=1]` y toda es negativa. Es la que yo leería primero.

### 9.1 El medidor miente antes que el sistema

**Es el error más frecuente, con diferencia.** Ante una cifra extrema —un 0, un 100 %, un valor
exacto repetido, una comparación que se invierte— el fallo está en el instrumento más veces que en
el sistema. Y es **más barato de creer**, porque confirma que había algo que arreglar.

Nos ha pasado más de quince veces. Ejemplos: «0 de 12 fuentes» era leer un campo que no existía;
«1.000 exacto» era medir una cosa distinta de la que decide; «cuatro fichas sin texto» lo tenían,
guardado por otra clave; y una diferencia de 22 KB al partir un fichero era mi propio verificador
buscando mal.

**La variante peligrosa: un rojo en un test recién escrito es tan sospechoso como una cifra
extrema**, porque ahí se interpreta como «falta implementarlo» y la prisa por arreglar tapa la
revisión del instrumento.

### 9.2 El doble de test se queda corto respecto al código

Un mock que enumera a mano lo que un módulo exporta se queda viejo en el siguiente cambio, y el
rojo aparece **lejos de su causa**: 19 tests fallando que parecían del menú y eran del doble.

Regla: **un solo doble por módulo, en un solo sitio.** Si un fichero de tests nuevo necesita el
mismo doble, los tests van al fichero que ya lo tiene.

### 9.3 Una guarda defensiva esconde un bug

Donde un `except` evita que un fallo tumbe el servicio, hace falta **un test del camino bueno**.
Tuvimos un arreglo inerte durante días porque un `except` se tragaba el error que probaba que no
funcionaba.

### 9.4 Los mocks sin `spec=` esconden cambios de API externa

Un doble sin especificación acepta cualquier método, incluido uno que el SDK real renombró. Se
descubre en producción.

### 9.5 La duplicación se cuela en el documento que la prohíbe

`AGENTS.md` enuncia «una sola fuente de verdad por cosa» y tenía el 28 % de su contenido
duplicado en otro documento. No fue descuido: cada vez que una regla necesitaba una frase más de
contexto, se escribía ahí en vez de en el documento largo, y en meses eso son 11 KB.

**El síntoma que lo delató no fue el tamaño**: fue tener que editar la misma lista en dos sitios
al añadir una regla, y darse cuenta de que la segunda copia casi se queda sin actualizar. Y al
quitar la duplicación se puso rojo un guardarraíl **que estaba casando con la copia**, lo que
enseña algo incómodo: un guardarraíl puede estar vigilando la redundancia en vez del original.

### 9.6 Un documento con estado incrustado envejece

Nuestro documento de «leer primero» llevaba una sección de estado fechada, y tres bloques después
mentía. **El estado va en un solo sitio** (el cursor) y los demás apuntan. Es P4 aplicado a lo que
más tienta romperlo.

### 9.7 Y el meta-error: el mismo problema muerde tres veces

Un defecto de frontera con un proveedor externo nos mordió **tres veces en sitios distintos** antes
de que lo arregláramos como **clase** en vez de como caso. La segunda vez ya había un módulo
escrito para evitarlo, y no se usó en los ocho sitios que lo necesitaban.

Regla: **a la segunda vez, guardarraíl.** No a la tercera.

---

## 10. Comparación con otros marcos

| Dimensión | Marcos *spec-driven* (Spec Kit, Kiro) | Marcos de personas ágiles (BMAD) | Este marco |
|---|---|---|---|
| Origen | Herramienta con opinión, 2025 | Comunidad, 2025 | Ensayo y error en un proyecto real |
| Madurez | Meses. Ninguno se ha impuesto | Meses | `[n=1]` |
| Especificación | Fichero por *feature* | Documentos por rol | Prompts TDD + especificación por capacidad |
| TDD | No lo impone | No lo impone | **Obligatorio** |
| Trazabilidad del *por qué* | — | — | **Historial + ADR** |
| Documentación comprobada | — | — | **Guardarraíles** |
| Modelo de permisos | Delegado a la herramienta | — | **Explícito y con tests** |
| Autonomía | Alta, con confirmación por fase | Alta | **Media: bloque autónomo, decisiones humanas** |

**Qué tomar de ellos**: la granularidad de un fichero por unidad de trabajo, y el vocabulario
—*constitution*, *spec*, *plan*, *tasks*— que ya empieza a ser común y facilita que alguien de
fuera entienda tu repositorio.

**Qué no tomar**: la promesa de autonomía por fases sin puerta de tests. Es donde DORA avisa: sin
estabilidad, la velocidad es caos acelerado **[Evidencia]**.

**Y qué no hacer**: adoptar una herramienta de orquestación para obtener lo que ya tienes. Si ya
tienes plan, cursor e historial funcionando, migrarlos al formato de un marco te cuesta la
reescritura entera y te devuelve lo mismo.

---

## 11. Cómo desplegarlo en un proyecto nuevo

### 11.1 El orden importa

No se montan los siete documentos el primer día. Este orden es el que evita escribir documentos que
luego hay que tirar:

| # | Paso | Por qué aquí |
|---|---|---|
| 1 | **Permisos y guarda, con sus tests** | Antes de que el agente ejecute nada |
| 2 | **`AGENTS.md` mínimo**: reglas duras, comandos del proyecto, prohibiciones | Es lo que el agente lee antes de escribir |
| 3 | **CI con lint + tests + lock verificado** | Sin esto, TDD es una intención |
| 4 | **El primer bloque de prompts TDD** | Un bloque pequeño, para calibrar el método |
| 5 | **Cursor e historial** | En cuanto haya dos bloques |
| 6 | **Registro de decisiones** | A la primera alternativa descartada |
| 7 | **Especificaciones** | Cuando haya capacidades que garanticen algo |
| 8 | **Guardarraíles** | A la primera vez que un documento se queda viejo |
| 9 | **Licencia, DCO, plantillas de issue** | Antes de abrir el repositorio, no después |

**Las especificaciones van en el 7 y no en el 1** por una razón medida: escribir garantías antes de
tener nada que garantizar produce un documento que se reescribe entero al segundo bloque.

### 11.2 El prompt de arranque

Esto es literal: se le da a un agente con este documento accesible, y produce el andamio.

```markdown
Lee `MARCO_DESARROLLO_AGENTICO.md` y monta los documentos de gobierno de este proyecto.

CONTEXTO QUE TE DOY YO:
- Proyecto: <nombre y en una frase qué hace>
- Lenguajes y stack: <...>
- Cómo se ejecutan los tests: <comando exacto>
- Cómo se arranca en local: <comando exacto>
- Sistema operativo y shell de trabajo: <...>
- Directorio de trabajo permitido: <ruta absoluta>
- Licencia elegida y por qué: <...>
- Lo primero que hay que construir: <...>

QUÉ QUIERO QUE HAGAS, EN ESTE ORDEN, PARANDO DONDE SE INDICA:

1. Configuración de permisos según §3, adaptada a mi stack: los tres cubos y el hook de la
   guarda con las tres familias de riesgo (SO, borrado fuera de raíz, pérdida irreversible).
   Escribe también los tests de la guarda. **PARA y enséñame la tabla de permisos antes de
   seguir**: es la única parte que no puedo revisar después.

2. `AGENTS.md` según §4.1. Reglas duras, accionables, con los comandos exactos de mi stack.
   **Máximo 300 líneas** — la evidencia dice que la longitud moderada funciona mejor, y nuestro
   propio fichero se pasó. Si algo necesita más razonamiento, va a un documento aparte enlazado.
   Si mi herramienta busca otro nombre, crea ese fichero con tres líneas que importen este.

3. CI según §7.1, con las puertas que apliquen a mi stack. Lint antes de tests. Lock verificado.

4. El primer bloque de prompts TDD según §4.3, para «lo primero que hay que construir»:
   entre 3 y 7 prompts, cada uno con sus tests ENUMERADOS y su verificación de cierre con
   evidencia concreta. Un fichero por bloque desde el principio.
   **PARA y enséñame el bloque antes de ejecutar nada.**

5. Cursor e historial vacíos, con su cabecera explicando qué va en cada uno.

6. Plantillas: registro de decisiones, issue de fallo, issue de propuesta (con la pregunta de
   §8.3), plantilla de pull request, y el fichero de la licencia elegida.

7. Un `CONTRIBUTING.md` con el ciclo de §5 y qué NO se le pide a quien contribuye desde fuera.

QUÉ NO HAGAS:
- No escribas especificaciones todavía (§11.1, paso 7): no hay nada que garantizar.
- No escribas guardarraíles todavía: llegan cuando un documento se queda viejo.
- No inventes cifras, umbrales ni métricas. Si algo hay que medir, deja escrito cómo se mide.
- No copies nuestras decisiones de arquitectura: son de nuestro dominio. Copia la FORMA.
```

### 11.3 Qué NO copiar de nosotros

Tres cosas de este marco son de nuestro contexto y copiarlas sería un error:

1. **Nuestras decisiones de arquitectura.** La frontera edge/cloud, la multitenencia por
   organización o la retirada de un conversor de documentos responden a un dominio concreto.
2. **El tamaño de nuestro `AGENTS.md`.** Es deuda, no modelo (§4.1).
3. **La AGPL.** La elección tiene que estar razonada para **tu** proyecto (§8.1).

### 11.4 Cómo saber si está funcionando

Sin métricas, esto es fe. Cuatro señales, y las dos primeras son las que de verdad importan
**[n=1]**:

| Señal | Qué indica |
|---|---|
| **Cuántas veces al mes un guardarraíl se pone rojo por un documento viejo** | Que la documentación se mantiene sola. Cero durante meses es sospechoso: probablemente pasa en vacío (§6.3) |
| **Cuántas veces el rojo era del instrumento y no del sistema** | Si baja, el método está calando. Nosotros lo anotamos cada vez |
| Tiempo desde «entra alguien nuevo» hasta su primer PR aceptado | Si la documentación sirve |
| Reversiones por bloque | Si el commit por paso está bien puesto |

**No midas velocidad sin medir estabilidad.** Es la conclusión de DORA y la moraleja de METR a la
vez: quien mide sólo velocidad va a concluir que va más rápido, y se va a equivocar en 40 puntos
**[Evidencia]**.

---

## 12. Bibliografía

**Evidencia empírica**

- METR, *Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity*
  (julio 2025) — el ECA de los 16 desarrolladores y las 246 tareas.
  <https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/>
- DORA / Google Cloud, *State of AI-assisted Software Development 2025* — la IA como amplificador.
  <https://dora.dev/dora-report-2025/>
- Anthropic, *2026 Agentic Coding Trends Report* — el reparto 70 % planificación / 20 % ejecución.
  <https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf>
- *Agent READMEs: An Empirical Study of Context Files for Agentic Coding*, arXiv:2511.12884 — la
  longitud moderada y las instrucciones explícitas. <https://arxiv.org/abs/2511.12884>
- *Graduated Human Oversight for Agentic Code Generation*, arXiv:2606.22484 — supervisión escalada
  por riesgo, matrices de permisos. <https://arxiv.org/abs/2606.22484>
- *Instruction Adherence in Coding Agent Configuration Files*, arXiv:2605.10039.
  <https://arxiv.org/abs/2605.10039>
- *Harness Engineering for Agentic AI Coding Tools: An Exploratory Study*, arXiv:2602.14690.
  <https://arxiv.org/abs/2602.14690>

**Estándares y convenciones**

- Especificación `AGENTS.md` — formalizada en agosto de 2025; donada a la *Agentic AI Foundation*
  de la Linux Foundation en diciembre de 2025. <https://agents.md>
- GitHub, *Spec-driven development with AI* y el repositorio `github/spec-kit`.
  <https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/>
  · <https://github.com/github/spec-kit>
- Michael Nygard, *Documenting Architecture Decisions* (2011) — el formato ADR.
  <https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>
- *Developer Certificate of Origin* 1.1. <https://developercertificate.org/>
- Free Software Foundation, *GNU AGPL v3*. <https://www.gnu.org/licenses/agpl-3.0.html>

**Taxonomías de autonomía**

- Cloud Security Alliance, *Autonomy Levels for Agentic AI* (enero 2026) — seis niveles con
  controles por riesgo. <https://cloudsecurityalliance.org/blog/2026/01/28/levels-of-autonomy>
- Swarmia, *Five levels of AI coding agent autonomy, and why higher isn't always better*.
  <https://www.swarmia.com/blog/five-levels-ai-agent-autonomy/>

---

## Apéndice — El marco en una página

```
PRINCIPIOS          P1 supervisado, no autónomo   P2 medir, no sentir
                    P3 determinista antes que modelo   P4 una fuente por cosa
                    P5 el por qué se escribe   P6 lo mantenible se pone rojo

PERMISOS            permitir: leer, escribir, git, tests, paquetes, contenedores
                    preguntar: SO · borrado fuera de raíz · pérdida irreversible
                    denegar: lo que no tiene caso legítimo nunca
                    + guarda con tests propios

DOCUMENTOS          reglas · especificaciones · plan · cursor
                    historial · decisiones · contribución

CICLO               bloque = unidad de interacción
                    RED → GREEN → REFACTOR → cierre → commit firmado por paso
                    4 causas para interrumpir, y una lista de cuándo NO
                    tests escalonados · verificación en navegador · informe de cierre

CONTROL             guardarraíles (documentación con test)
                    CI con puertas · sin paralelismo en CI
                    rama de trabajo ≠ rama que despliega

APERTURA            licencia razonada · DCO también al mantenedor
                    issue de propuesta con «¿por qué cualquier organización?»
                    principal + forks, sin fork privilegiado
```

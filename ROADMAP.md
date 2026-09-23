# Hoja de ruta

Este documento dice **qué hace hoy la plataforma, qué se está construyendo, qué está previsto,
qué espera una decisión ajena y qué no se va a hacer**. Es la vista pública del plan, por temas y
con estado, y no lleva fechas: las dependencias son ciertas y las fechas no lo serían.

Tres cosas para leerlo bien:

- **El detalle vive en GitHub.** Cada tema enlaza a sus *issues* y a sus hitos; ahí está el
  diseño, la discusión y el cierre. Este documento se actualiza cuando un hito se abre o se
  cierra, no con cada *issue*.
- **Qué garantiza el sistema está en otro sitio.** Un estado «construido» aquí significa que la
  capacidad existe; lo que se puede dar por cierto al construir encima, invariantes incluidos,
  está en [`docs/ESPECIFICACIONES.md`](docs/ESPECIFICACIONES.md). Para una lectura de conjunto,
  [`docs/PRESENTACION_PROYECTO.md`](docs/PRESENTACION_PROYECTO.md).
- **Los planes TDD de `planificacion/` son documentos de diseño con historia**, escritos en
  futuro y antes de decisiones que después se revirtieron. No se enmiendan; se leen para saber
  por qué se decidió lo que se decidió.

## Estados

| Estado | Significa |
|---|---|
| **En producción** | Desplegado y en uso en la instalación de referencia |
| **Construido** | Completo y verificado en la rama de desarrollo; aún sin desplegar |
| **En curso** | Hay trabajo abierto con *issues* asignadas |
| **Previsto** | Diseñado y encolado; no empezado |
| **Bloqueado** | Espera una decisión o un prerrequisito **externo al proyecto** |
| **Por revisar** | Planificado antes de decisiones que lo cambian; pendiente de reescribir |
| **No se hace** | Descartado a propósito, para que nadie lo construya creyendo que falta |

## Temas

### 1. Asistentes informativos sobre normativa — En producción

Chatbots de recuperación aumentada sobre el corpus normativo de la institución, con citas
resolubles, aviso de vigencia, política de lengua y trazas por petición. Evaluación con lote
dorado y veredicto humano.

Abierto: revisión humana de las respuestas ([#8](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/8));
el catálogo de procedimientos en el mismo asistente ([#12](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/12),
**bloqueado** por las fichas validadas y la consulta de descarga); orden vigencia→lengua y aviso
de traducción ([#9](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/9)); reordenador
por API y su medición en valenciano ([#10](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/10)).

### 2. Corpus normativo y curación de portales — En producción

El corpus entra como Markdown conforme a contrato, con vocabulario versionado como dato y
taxonomía nunca embebida, de modo que reclasificar cuesta un `UPDATE` y no un reindexado. La
curación rastrea portales públicos con cadencia, detecta huecos y propone secciones.

Sin trabajo abierto de alcance nuevo. El vocabulario está **pendiente de validación** por la
secretaría general de la instalación de referencia, y el diseño está hecho para que ese cambio sea
barato.

### 3. Informes deterministas y catálogo de funciones — En producción (informes) · Construido (catálogo)

Informes con tablas que calcula código y valoración de la IA sujeta a aprobación humana. Las
extracciones deterministas se escriben una vez como **funciones** con contrato declarado,
versionadas e inmutables, con dos orígenes (autoservicio con *sandbox*; paquete por *entry
point*), registro sin aprobación previa y revisión posterior por muestreo. Detalle en
[`docs/CATALOGO_FUNCIONES.md`](docs/CATALOGO_FUNCIONES.md).

Abierto: los campos de entrada manual de una plantilla sin dónde rellenarse
([#86](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/86)). La ampliación del
catálogo a tareas completas es el tema 4.

### 4. Automatización gobernada — En curso

**Sustituye a la «Fase 2: Automatización y Thin Client»** del plan original. De aquélla, la
migración de la interfaz quedó vacía al retirar el cliente antiguo, y la migración de servicios
se hizo bajo otros nombres (el catálogo de funciones, el *sandbox*, el `RunManifest`, el registro
de actividad y las verificaciones por API y MCP). Lo único que quedaba vivo era el agente de
ejecución local, y **se descarta**: los agentes de propósito general con acceso al navegador y al
escritorio ya cubren ese terreno, en el régimen que las normas de desarrollo ciudadano reservan al
uso personal. Lo que esos agentes no dan, y la plataforma sí, es **registro, ecosistema
autorizado, revisión posterior y anonimización**. A eso se dedican los cuatro hitos.

| Hito | Estado | Qué entrega | Issues |
|---|---|---|---|
| [1 — Cerrar lo que ya no se hace](https://github.com/universitatjaumei/gov-gen-ai-platform/milestone/9) | Previsto | La especificación declara como límite deliberado que no se ejecuta nada en el equipo de quien la usa; los planes de fase 2 se cierran | [#112](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/112), [#113](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/113) |
| [2 — Registrar lo que corre fuera](https://github.com/universitatjaumei/gov-gen-ai-platform/milestone/10) | Previsto | Funciones de **origen externo** (un cuaderno se registra por su hash sin ejecutarlo); paquete MCP y *skill* de gobernanza para agentes de código; registro de la ejecución de un cuaderno en tres líneas; depósito del manifiesto de una ejecución hecha fuera | [#114](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/114), [#115](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/115), [#124](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/124), [#116](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/116) |
| [3 — Funciones de tarea](https://github.com/universitatjaumei/gov-gen-ai-platform/milestone/11) | Previsto | Una función produce **ficheros**; red saliente sólo hacia **orígenes declarados**; el ecosistema de módulos ampliado y vigilado; los dos cuadernos reales como casos guía con datos sintéticos | [#117](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/117), [#118](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/118), [#119](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/119), [#120](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/120) |
| [4 — Decisiones de la institución](https://github.com/universitatjaumei/gov-gen-ai-platform/milestone/12) | **Bloqueado** | El régimen de ejecución frente a la regla de soberanía local; la lista del ecosistema autorizado y el plazo de revisión; quién revisa, quién suspende y la ruta a protección de datos | [#121](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/121), [#122](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/122), [#123](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/123) |

El orden recomendado es 1, 2, 3: el hito 2 es el más barato y ataca el problema real de una
organización que trabaja con cuadernos, saber cuáles circulan; el 3 es el de más diseño. El 4 no
depende del código y condiciona el alcance final del 3: si la institución no da por equivalente
la ejecución central, el catálogo autoservicio se acota y las funciones de origen externo pasan a
ser el canal principal.

### 5. Registro de actividad IA y gobernanza por API — En producción

La plataforma como registro de la actividad con IA de la institución, también de lo que se
construye fuera: evento de gobernanza por HTTP y MCP (metadatos, nunca contenido), catálogo de
categorías que se anuncia sin imponerse, y verificaciones como servicio (citas, vigencia,
auditoría estática de código). Detalle en
[`docs/REGISTRO_ACTIVIDAD_IA.md`](docs/REGISTRO_ACTIVIDAD_IA.md) y
[`docs/GOVERNANCA_PER_API.md`](docs/GOVERNANCA_PER_API.md).

Abierto: los candidatos de §4 de ese último documento que no están hechos; el depósito de
manifiestos entra por el hito 2 del tema 4. **No hay política de retención** del registro, y hace
falta una.

### 6. Identidad, roles, módulos y multitenencia — En producción

Entrada con la cuenta institucional, roles separados de los módulos concedidos, aislamiento por
organización con inventario tabla a tabla y cascada de configuración plataforma → organización →
chatbot. Detalle en [`docs/MULTITENENCIA.md`](docs/MULTITENENCIA.md).

Abierto, en el hito [Bloque 1 — dar de alta a una persona](https://github.com/universitatjaumei/gov-gen-ai-platform/milestone/5):
conceder módulos donde se da de alta ([#100](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/100)),
la siembra del catálogo sin contraseña ([#97](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/97)) y
el guion de emergencia del superadministrador ([#96](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/96)).
La segunda fase de la multitenencia, vista y permisos por organización, espera al piloto
([#11](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/11)).

### 7. Operación, despliegue y apertura del repositorio — En curso

Despliegue en máquina virtual con imágenes construidas y arrancadas en CI, esquema gobernado sólo
por Alembic, dependencias auditadas por lotes y reversión automática. Los hitos
[Bloque 2 — lo que ya costó una caída](https://github.com/universitatjaumei/gov-gen-ai-platform/milestone/6) y
[Bloque 3 — lo que verá quien instale](https://github.com/universitatjaumei/gov-gen-ai-platform/milestone/7)
recogen lo que queda antes y después de abrir. La numeración es `0.x` a propósito y no se promete
cadencia ni soporte: [`docs/VERSIONADO.md`](docs/VERSIONADO.md).

### 8. Gestor de expedientes y malla agéntica — Por revisar

La pieza de mayor valor regulatorio y la que no existe: tramitación asistida con fases y acciones
**calculadas en el servidor** según rol, fase y estado, auditoría encadenada, fotografía de la
normativa en la fecha de referencia e integración con los gestores corporativos. El plan está en
`planificacion/Plan_TDD_Fase3.md` y **se escribió antes de las decisiones del tema 4**, así que se
revisará con el mismo criterio antes de abrir ningún hito.

Lo que ya está fijado y condiciona el diseño, y no cambia con la revisión:

- el frontend **nunca** calcula qué acciones caben; el servidor devuelve `acciones_permitidas`;
- **el cloud orquesta, el edge ejecuta**, donde «edge» es el servidor desplegado en la nube de la
  institución, no un proceso en el puesto de trabajo;
- las fases referencian `plantilla@versión` y `función@versión`, nunca código incrustado.

Prerrequisito externo: los sistemas institucionales de tramitación, que no se pueden simular en
local. Y una advertencia que conviene no descubrir después: este módulo **sí toca actuación
administrativa**, así que no hereda la clasificación de riesgo de los asistentes informativos.

## Lo que no se hace

Límites deliberados, con su razón en
[`docs/ESPECIFICACIONES.md` §10](docs/ESPECIFICACIONES.md#10-qué-no-hace-la-plataforma):

- **Ejecutar en el equipo de quien la usa**: ni agente local, ni RPA, ni vigilantes de carpeta,
  correo o web, ni programador de flujos locales, ni *thin client*. Es la decisión del tema 4 y
  entra en la especificación con [#112](https://github.com/universitatjaumei/gov-gen-ai-platform/issues/112).
- **Acceder a la nube personal de la persona con credenciales centralizadas** (unidades y
  documentos compartidos). La persona sube y descarga; lo que necesite sus credenciales corre
  fuera y se registra.
- Asesoramiento jurídico, decisiones automáticas, código de motor generado en tiempo de
  ejecución, corpus compartido entre chatbots, conversión de documentos en el servidor, rastreo de
  redes internas, capas de compatibilidad.

## Cómo contribuir

Las *issues* marcadas
[`good first issue`](https://github.com/universitatjaumei/gov-gen-ai-platform/issues?q=is%3Aopen+label%3A%22good+first+issue%22)
son puntos de entrada con alcance cerrado. Las marcadas `blocked` esperan algo externo y no
admiten código todavía. El método de trabajo, la firma de los *commits* y las reglas de la casa
están en [`CONTRIBUTING.md`](CONTRIBUTING.md) y [`AGENTS.md`](AGENTS.md).

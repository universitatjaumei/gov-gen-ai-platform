# Trámites asistidos, no gestor de expedientes

> **Fecha**: 2026-09-23. **Estado**: aceptada, sin construir — su alcance es el tema 8 de
> [`../ROADMAP.md`](../ROADMAP.md), con cuatro hitos y trece *issues*. **Origen**: la pregunta del
> mantenedor al replantear la Fase 3 antes de abrir el repositorio. **Sustituye** a
> `GESTOR_EXPEDIENTES.md`, retirado en el mismo cambio.
>
> Es una **decisión**: no se actualiza, se sustituye por otra posterior que la cite. Lo que hoy
> garantiza el sistema está en [`ESPECIFICACIONES.md`](ESPECIFICACIONES.md) §7.

## La pregunta

¿Tiene sentido un gestor de expedientes para meter IA en algunas fases, cuando las
administraciones ya tienen aplicaciones de gestión de expedientes?

## La decisión

**No.** No se construye un gestor de expedientes. El de la institución es la **fuente de verdad
del procedimiento**: sus fases, su estado, quién firma, la notificación, la evidencia de
interoperabilidad. Construir otro lo duplicaba, y duplicarlo obliga a sincronizarlo.

Lo que se construye son **trámites asistidos con IA** —baremación, informe de fase, redacción de
resolución— que siguen las pautas del módulo de informes y que el gestor puede invocar.

## El principio que resuelve el problema de los dos sitios

> **El estado del procedimiento tiene un solo dueño, el gestor. La plataforma no lo cambia nunca.**

La plataforma posee sólo la **ejecución del trámite** y su evidencia. Entrega un resultado; qué se
hace con él lo decide el gestor. Con eso, «gestionar desde dos sitios» deja de ser un problema de
sincronización y pasa a ser un contrato de llamada.

De ahí se deduce lo demás, incluida la distinción que más confusión evitaría si se olvidara:
**validar en la plataforma valida el contenido generado; el acto administrativo —firmar,
notificar, avanzar de fase— sigue en el gestor.** Dos clics con dos significados distintos.

## Las cinco piezas del vínculo

1. **Catálogo.** Una plantilla marcada como trámite publica su contrato: entradas, salidas
   (documento, datos estructurados, manifiesto), si exige revisión humana, categorías de datos y
   clase. El gestor lo lee como lee un contrato de formulario.
2. **Invocación, en dos modos.** *A mano* en la plataforma, indicando la referencia del
   expediente, que es **el primero y el que no depende de nadie**; o *desde el gestor* por API,
   con token de sistema, clave de idempotencia y la persona que tramita atribuida por cabecera de
   actor.
3. **Revisión en la plataforma.** Ahí están las citas, los bloques, la anonimización y el registro
   de quién aprobó qué. El gestor muestra un enlace profundo.
4. **Devolución.** El gestor recibe un aviso firmado con reintentos, o consulta el estado, y
   recoge documento, datos, identificador de manifiesto y *hash*. El estado lleva
   `acciones_permitidas` calculadas en el servidor.
5. **Datos.** Al trámite entra sólo lo que necesita, se anonimiza antes del modelo, y el workspace
   se retira al cerrar conservando el manifiesto sin contenido. La plataforma no es archivo del
   expediente.

## La regla de la baremación

**Determinista, basada en datos objetivos, replicable, y siempre verificada por una persona.** El
modelo extrae los hechos con su cita, **una persona los verifica**, una función del catálogo aplica
el baremo —que es **dato versionado**, no código— y el modelo redacta la motivación leyendo la
tabla de puntuación. **El modelo no puntúa nunca.**

No es cautela: evaluar o clasificar personas con efectos sobre el acceso a educación, becas o
empleo público es un uso del Anexo III del Reglamento de IA. Es la regla del módulo de informes
—«las tablas las calcula código, no el modelo»— aplicada a puntuaciones.

## Qué cae del plan anterior, y qué sobrevive

| Del plan de Fase 3 | Qué pasa |
|---|---|
| Esquema de expedientes, motor con *checkpointing*, frontend de expedientes (E1, E2, E4) | **Caen.** El workspace ya suspende en las puertas de revisión y tiene pantalla |
| Adaptadores por sistema y capa ENI/ENS (E5) | **Caen.** ENI, CSV y DIR3 son del gestor, que ya los cumple; la plataforma entrega documento y *hash*. Y el contrato es único: no hay un adaptador por producto |
| Agente analista, vigencia a fecha de referencia | **Sobreviven** como **bloques de plantilla** de la resolución |
| Auditoría de equidad | **Aplazada** hasta que haya base jurídica para tratar datos de colectivo |
| Invariante de ejecución en el edge | **Se cumple sin agente**: el gestor y la plataforma están en el mismo perímetro institucional |

## Cómo se dan de alta más tipos de trámite

Un tipo de trámite es **una plantilla con clase declarada**, así que se da de alta por los caminos
que las plantillas ya tienen: **por pantalla**, **por MCP** con un agente de código
(`create_template`, `publish_template_version`) o **por API**. Es configuración versionada.

**La clase sí es código** (`baremacion`, `informe_de_fase`, `resolucion`): cada una impone reglas
que algo tiene que ejecutar, así que añadir una cuarta es una *issue* y un despliegue. Vocabulario
como dato, ejes como código, igual que en el resto de la plataforma.

**El gestor consume el catálogo e invoca; no escribe plantillas.** Puede por API y no se
recomienda: un tipo de trámite lleva clasificación de riesgo declarada, la baremación necesita una
función registrada por su propio circuito, y revisar una plantilla es trabajo de autoría. Basta con
no concederle el *scope* de escritura.

## El riesgo, dicho sin rodeos

**Es externo.** Si el gestor institucional no puede llamar a una API con token, enviar y recibir
ficheros y guardar un enlace con su *hash*, no hay integración automática. El repliegue no es un
plan B improvisado: **es el modo manual**, que se construye igual y con el que se harán las
primeras pruebas. Quien tramita ejecuta el trámite indicando la referencia, descarga y adjunta. El
registro y el manifiesto quedan idénticos.

## Por qué se retiró `GESTOR_EXPEDIENTES.md`

Describía un gestor híbrido con diseño de flujos por arrastrar y soltar, orquestación del
expediente, cola Celery con Redis, ejecución de *playbooks* de Playwright en el navegador de la
persona y **generación de scripts en tiempo de ejecución** por trámite. Las cinco cosas contradicen
decisiones ya tomadas —no hay gestor propio, no hay agente local ni RPA, no se genera código de
motor en tiempo de ejecución— y quien lo leyera desde fuera lo tomaría por el diseño vigente. Se
retira borrando: el historial de git lo conserva con su contexto.

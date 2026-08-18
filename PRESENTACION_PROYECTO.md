# Gov Gen AI Platform — Presentación del proyecto

> **Naturaleza del documento**: presentación del proyecto para instituciones, fundaciones y
> equipos externos que quieran conocerlo o colaborar. Describe qué hace la plataforma, qué está
> construido y verificado a día de hoy, y qué está previsto. No es documentación técnica: para
> cada tema remite al documento especializado correspondiente (§10).
>
> **Fecha**: 18 de agosto de 2026. Las cifras de este documento corresponden a esa fecha y son
> medidas, no estimadas.

---

## 1. Qué es y para qué sirve

**Gov Gen AI Platform** es una plataforma de inteligencia artificial diseñada específicamente para
**administraciones públicas**. Su objeto es aplicar IA generativa y automatización a procesos
administrativos reales —atención ciudadana, redacción de informes, extracción de datos de
documentos, tramitación de expedientes— de forma **auditable, trazable y conforme a la normativa
europea y española**: Reglamento (UE) 2024/1689 de IA, RGPD, Leyes 39/2015 y 40/2015, y Esquema
Nacional de Seguridad.

Lo que la diferencia de un despliegue genérico de chatbots es que **la conformidad no es
documentación aparte**: está incorporada al diseño del sistema. Cada actuación asistida por IA
deja evidencia de supervisión humana, de procedencia de la información y del tratamiento de datos
personales aplicado. El principio rector es *compliance-as-code*: las obligaciones legales se
traducen en comprobaciones ejecutables y en pruebas automáticas, no en buena fe ni en auditorías
puntuales.

Conviene decir desde el principio dónde acaba su alcance: la plataforma cubre lo que un sistema
puede garantizar por diseño, no la gobernanza institucional de la IA. El inventario de casos de uso,
el registro de sistemas y la asignación de responsabilidades se gestionan **fuera** de ella, y §7
explica por qué esa separación es deliberada.

El primer despliegue piloto es la **Universitat Jaume I**, con dos asistentes en marcha sobre
corpus normativo real, y el proyecto se publicará como **software libre (AGPLv3)** con licencia
dual comercial, de modo que cualquier institución pueda autoalojarlo.

## 2. Por qué es distinto: cinco decisiones estructurales

Estas cinco decisiones explican casi todo lo demás, y son las que sostienen la conformidad:

**Determinismo primero.** Si un resultado puede obtenerse con reglas, plantillas o extracción
estructurada, se obtiene así, y el modelo generativo se reserva para lo que el determinismo no
alcanza. Cuando el modelo interviene, la vía usada queda registrada. Un proceso determinista es
reproducible y explicable línea a línea; en actuación administrativa, la explicabilidad plena es
un requisito de legalidad, no una preferencia técnica.

**Ninguna afirmación sin fuente.** Los asistentes responden citando el fragmento concreto de la
norma que sostiene cada afirmación. Cuando el sistema no encuentra fundamento suficiente,
**responde que no lo tiene** en lugar de redactar algo plausible: la respuesta de indisponibilidad
es una función del sistema, no un fallo.

**El servidor es la única fuente de verdad.** La interfaz no contiene reglas de negocio: los
formularios y las acciones permitidas los decide el servidor y el cliente solo los dibuja. Esto
hace que el comportamiento del sistema esté descrito por un contrato versionado y auditable, y no
por lo que haga cada pantalla.

**Soberanía del dato por arquitectura, no por contrato.** La plataforma se despliega en dos modos.
En modo *cloud* todo corre en el servidor del proveedor, con disociación previa de datos
personales. En modo *edge + cloud* la lógica y los datos de la institución —conversaciones,
documentos, expedientes, vectores— viven **dentro de su propia infraestructura**, y la parte
central solo conserva configuración y métricas anonimizadas. Esa frontera está implementada en el
código (bases de datos separadas, módulos clasificados, pruebas que la vigilan), no solamente
declarada.

**Portabilidad deliberada.** Almacenamiento, base de datos y proveedor de modelos se cambian por
configuración, sin tocar código. La dependencia de un proveedor concreto es un riesgo de soberanía
y de competencia en la compra pública, así que se trata como tal.

## 3. Los módulos: lo que hay hoy

Tres módulos funcionales sobre una base común (identidad institucional, pasarela de modelos
multiproveedor, almacenamiento portable, frontera edge/cloud):

### 3.1 Asistentes informativos

Chatbots multilingües (valenciano, castellano, inglés) sobre corpus documental propio, con
**citas trazables al fragmento de origen**. Incluye:

- **Búsqueda híbrida** (semántica y léxica combinadas) con **reordenación** de los resultados y
  **reescritura conversacional** de la consulta.
- **Selección escalonada por metadatos**, en tres niveles: un índice de materias acota primero el
  ámbito, se elige el subconjunto pertinente y solo entonces se consulta. Evita que una pregunta de
  un área traiga fundamento de otra, y reduce lo que viaja al modelo.
- **Vigencia garantizada en la recuperación**: una sola versión canónica por documento, lo derogado
  fuera del índice consultable y aviso explícito cuando la norma aplicable ha sido desplazada. El
  desempate entre fragmentos equivalentes es determinista, para que la misma consulta cite siempre
  las mismas fuentes en el mismo orden.
- **Calidad medida, no supuesta**: un conjunto de consultas de referencia con las fuentes que
  deberían recuperarse actúa como **puerta de integración continua**. Ningún cambio del motor de
  recuperación se acepta si degrada la calidad por debajo de la línea base registrada.
- **Widget embebible** en webs institucionales y **modo identificado** para personal interno.
- **Preguntas frecuentes como contenido citable**, con autoridad propia frente al resto del
  corpus.
- **Vigencia del corpus**: cada documento lleva fecha de revisión prevista; cuando vence, el
  sistema lo señala. Una respuesta correcta sobre una norma derogada es un daño, no un acierto.

### 3.2 Informes y automatización

Generación asistida de informes a partir de documentos y hojas de cálculo reales:

- **Plantillas definidas por contrato**: el formulario de entrada de cada informe lo genera el
  servidor a partir de la plantilla, no está escrito en la interfaz.
- **Extracción determinista** de hojas de cálculo y PDF, con **transformación declarativa de
  datos**: veinte operaciones (limpieza, cálculo de columnas derivadas, conversión de importes
  escritos como texto, reordenación, pivotado) que se ejecutan sin generar código y se pueden
  mostrar al usuario antes de aplicarlas.
- **Once tipos de gráfico** deterministas con su presentación completa (título, etiquetas, cifras,
  orden), en formato numérico local.
- **Redacción asistida con revisión humana obligatoria** antes de que el informe se considere
  terminado, y **exportación a documento de oficina** con tablas e imágenes reales.
- **Manifiesto de ejecución**: cada informe registra qué modelo y qué versión de instrucciones
  intervinieron en cada apartado.
- **Ejecución aislada de código**: cuando un documento es tan irregular que requiere programar su
  lectura, el código se audita de forma determinista (tres niveles de severidad, con número de
  línea), lo revisa además un modelo supervisor, y se ejecuta en un **microservicio sin acceso a
  red** que vuelve a auditarlo antes de ejecutarlo. Ningún código de usuario corre en el proceso
  del servidor.

### 3.3 Curación de contenido

Módulo propio, porque la calidad del corpus es una cuestión de gobernanza y no de higiene técnica:

- **Rastreo de sitios web institucionales** y detección de patologías documentales: contenido
  obsoleto, sustituido, duplicado o contradictorio.
- **Informes de calidad** del corpus y exclusión registrada del contenido patológico.
- **Detección de huecos**: las consultas que el sistema no logra fundamentar alimentan una cola de
  revisión de contenido. El sistema dice qué documentación falta.
- **Publicación controlada** del contenido curado hacia el corpus de los asistentes.

### 3.4 Base común

Identidad institucional (**SSO SAML 2.0** con aprovisionamiento automático y tokens personales de
alcance limitado para clientes máquina), **personalización visual en cascada**
(plataforma → organización → asistente), **accesibilidad WCAG verificada en integración continua**,
**disociación de datos personales previa al envío al modelo** con cuatro modos graduados, y un
**servidor MCP** (16 herramientas) que permite administrar la plataforma desde agentes de IA con
confirmación humana en las operaciones sensibles.

## 4. Arquitectura y despliegue

Monorepo con backend **FastAPI** (Python asíncrono, contrato OpenAPI como única fuente de verdad),
frontend **React** generado contra ese contrato, y **PostgreSQL con pgvector**. El detalle está en
`Arquitectura.md`.

El primer despliegue de producción es una **máquina virtual en Google Cloud Platform** con Docker
Compose, base de datos gestionada y almacenamiento de objetos. Se descartó una arquitectura sin
servidor porque el sistema tiene procesos de ingesta programados que no encajan con el escalado a
cero, y porque a igualdad de coste añadía restricciones. La aplicación pesa ~345 MB y cabe en una
instancia pequeña: los modelos de embeddings locales son una dependencia **opcional**, necesaria
solo cuando la institución exige que el cálculo no salga de su perímetro.

## 5. Estado de desarrollo (agosto de 2026)

El proyecto se ha desarrollado **en solitario**, con disciplina de desarrollo guiado por pruebas
(la prueba antes del código) y asistencia de agentes de programación sujetos a reglas de
arquitectura escritas y verificables.

**Cifras medidas el 18 de agosto de 2026**: **2.284 pruebas de backend** y **329 de frontend** en
verde, sin fallos. La verificación no es solo automática: cada módulo con interfaz se recorre en
navegador antes de darlo por cerrado, y las pruebas manuales humanas se reservan para lo que una
máquina no puede juzgar (identidad visual, calidad editorial, sistemas externos reales).

**Funcionalmente completo y verificado:**

| Área | Estado |
|---|---|
| Asistentes informativos con citas | ✅ En marcha sobre corpus real |
| Búsqueda híbrida, selección por metadatos y calidad medida | ✅ Con puerta de calidad en integración continua |
| Curación de contenido web | ✅ Módulo propio completo |
| Informes: plantillas, extracción, transformación, gráficos, exportación | ✅ Recorrido completo verificado de punta a punta |
| Ejecución aislada de código generado | ✅ Microservicio endurecido, doble auditoría |
| Identidad institucional (SSO SAML + tokens) | ✅ |
| Disociación de datos personales previa al modelo | ✅ Cuatro modos graduados |
| Frontera edge/cloud | ✅ Implementada y vigilada por pruebas |
| Accesibilidad WCAG | ✅ Puerta automática en integración continua |
| Personalización visual institucional | ✅ |
| Servidor MCP para administración asistida | ✅ 16 herramientas |
| Autoinstalación y distribución | ✅ Instalación en un paso, prerrequisito del software libre |
| Endurecimiento de seguridad | ✅ Dos rondas de auditoría cerradas |

**El piloto, con datos reales.** El corpus normativo de la Universitat Jaume I está cargado:
**37.504 fragmentos** indexados a partir de la normativa propia y de la documentación de Gerencia,
clasificados por ámbito y materia. Hay **dos asistentes** en funcionamiento: uno sobre normativa
propia y otro para personal de Gerencia, este con identificación previa. Los embeddings se calculan
por API del proveedor de nube, con adaptador propio y proceso por lotes.

**Lo que queda antes del despliegue con usuarios reales:**

1. **Despliegue de producción** en la infraestructura descrita (§4).
2. **Revisión humana de las respuestas del asistente interno**: un circuito para que el personal
   marque respuestas y esa señal alimente la mejora del corpus.
3. **Reordenación de resultados en valenciano** medida con el proveedor de nube, pendiente del
   despliegue para poder compararla.
4. **Pruebas manuales finales** con datos e infraestructura reales.

## 6. Lo que viene

**Cliente de ejecución local (2027).** Un agente ligero instalable en el puesto de trabajo, para
los casos en que un proceso debe tocar sistemas que no exponen API: el sistema central orquesta y
el agente local ejecuta. Es la infraestructura que necesita el módulo siguiente.

**Gestor de Expedientes (2027-2028).** La pieza de mayor valor regulatorio, y la que todavía no
existe: tramitación administrativa asistida con fases y acciones **calculadas en el servidor**
según rol, fase y estado —de modo que el sistema solo ofrece lo que la norma autoriza—, auditoría
encadenada con valor probatorio, fotografía de la normativa aplicable en la fecha de referencia
(Ley 39/2015), auditoría de equidad y integración con los gestores corporativos existentes.

**Hitos orientativos**: piloto en producción en el cuarto trimestre de 2026, apertura del
repositorio público en la misma ventana, cliente local y gestor de expedientes durante 2027-2028.

## 7. Dos planos de gobernanza, y dónde acaba esta plataforma

Conviene ser explícito sobre el alcance, porque la gobernanza de la IA en una administración se
juega en **dos planos distintos** y confundirlos lleva a esperar de una herramienta cosas que una
herramienta no puede dar.

**Plano institucional (superior).** El inventario de casos de uso de IA de la organización, su
registro, la clasificación de riesgo de cada uno, la designación del órgano responsable de la
actuación automatizada, la intervención del delegado de protección de datos, las evaluaciones de
impacto, la aprobación del alta de un uso nuevo y su revisión periódica. Son decisiones de
gobierno y actos administrativos: dependen de personas y órganos con competencia, no de una
comprobación en código.

**Plano de la herramienta.** Lo que un sistema puede garantizar por diseño y demostrar por
construcción: que el resultado se obtiene por la vía más verificable disponible, que ninguna
afirmación se emite sin fuente, que existe un punto de supervisión humana instrumentado, que cada
ejecución deja registro de qué modelo y qué fuentes intervinieron, que los datos personales se
disocian antes de salir del perímetro, que el dato no cruza fronteras que no debe cruzar.

**Gov Gen AI Platform cubre el segundo plano, y no el primero.** No mantiene el inventario de casos
de uso ni el registro de sistemas de IA, y no está previsto que lo haga: esa función se gestiona
**al margen de la plataforma**, con aplicaciones y procedimientos propios, igual que la asignación
de responsabilidades. Es una decisión de alcance deliberada, no una carencia pendiente de
desarrollo: un inventario institucional debe abarcar *todos* los sistemas de IA de la
organización, incluidos los que no pasan por esta plataforma, así que alojarlo dentro de una de
las herramientas que debe inventariar sería un error de diseño.

La relación entre ambos planos es de doble sentido, y es el punto de encuentro con una plataforma
orientada al registro:

- **Del plano superior a la herramienta**: las decisiones de gobierno se traducen en
  configuración —qué modelo se asigna a cada actividad, qué modo de disociación se aplica, dónde
  hay puertas de revisión humana, qué umbrales de calidad—. La plataforma es donde esas decisiones
  se ejecutan y se hacen efectivas.
- **De la herramienta al plano superior**: la plataforma produce la evidencia con la que el registro
  se sostiene ante una auditoría. El registro declara qué se hace; la evidencia de ejecución
  demuestra qué se hizo.

Cómo se conecten ambos planos —qué campos describen un uso de IA, cómo se codifica la
clasificación de riesgo, cómo se referencia el órgano responsable— es una decisión de gobernanza
sectorial que conviene tomar de forma compartida, y no algo que deba resolver por su cuenta cada
herramienta. El marco de gobernanza del proyecto (`MARCO_GOBERNANZA_IA.md`) desarrolla esta
distinción de planos y detalla qué obligaciones vive en cada uno.

## 8. Licencia y distribución

**AGPLv3** con licencia dual comercial para partners. La autoinstalación en un paso ya está
resuelta, que era el prerrequisito real de la distribución: un proyecto que no se puede instalar
sin su autor no es software libre en la práctica. El objetivo es que otra administración pueda
levantar la plataforma en su propia infraestructura, con su corpus y su identidad visual, sin
depender del equipo original.

## 9. Cómo verlo

El punto de entrada recomendado para una demostración es el asistente sobre normativa propia
—porque enseña las citas trazables y la respuesta de indisponibilidad, que es lo que más cuesta
creer sin verlo— seguido de la generación de un informe a partir de una hoja de cálculo real, que
enseña el determinismo y la revisión humana en el mismo recorrido.

## 10. Documentación disponible

| Documento | Qué contiene |
|---|---|
| `Arquitectura.md` | Arquitectura funcional y técnica: módulos, roles, frontera cloud/edge/local, privacidad, decisiones estructurales |
| `MARCO_GOBERNANZA_IA.md` | Marco normativo interno: principios de gobernanza, mecanismos que los implementan, evidencia generada y clasificación de riesgo por caso de uso |
| `docs/EU_GOVERNANCE_CONCEPT_NOTE.md` | Proyección del marco de gobernanza hacia consorcios y financiación europea |
| `PLAN_DESARROLLO.md` | Plan de desarrollo del conjunto y decisiones durables (licencias, stack, identidad) |
| `VALORACION_PROYECTO.md` | Auditoría global del proyecto: calidad, seguridad y sentido de producto |
| `docs/SANDBOX_SECURITY.md` | Aislamiento de la ejecución de código |
| `docs/REDACCION_CONTRACT_FIRST.md` | Contrato del módulo de informes |
| `docs/A11Y_CHECKLIST.md` | Verificación de accesibilidad |
| `PROJECT_STATE.md` | Estado vivo del desarrollo, al día |

---

*Contacto y demostración: Modesto Fabra (fabra@uji.es), Universitat Jaume I.*

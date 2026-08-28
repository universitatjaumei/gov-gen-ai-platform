# Gov Gen AI Platform — Presentación del proyecto

> **Naturaleza del documento**: presentación del proyecto para instituciones, fundaciones y
> equipos externos que quieran conocerlo o colaborar. Describe qué hace la plataforma, qué está
> construido y verificado a día de hoy, y qué está previsto. No es documentación técnica: para
> cada tema remite al documento especializado correspondiente (§10).
>
> **Fecha**: 26 de agosto de 2026. Las cifras de este documento corresponden a esa fecha y son
> medidas, no estimadas. Cuando una cifra procede de una ejecución concreta, se dice cuál.

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

El primer despliegue piloto es la **Universitat Jaume I**, con tres asistentes en marcha sobre
corpus normativo real —uno público sobre normativa propia y dos internos de Gerencia, montados
para comparar dos métodos de recuperación—. El proyecto adoptó en agosto de 2026 la licencia
**AGPL-3.0-or-later** con licencia dual comercial; el repositorio sigue privado hasta la apertura
prevista, de modo que después cualquier institución pueda autoalojarlo.

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

- **Búsqueda híbrida** (semántica y léxica combinadas) con **reordenación** de los resultados por
  un reordenador multilingüe de nube —verificado sobre valenciano— y **reescritura conversacional**
  de la consulta.
- **Segunda búsqueda cuando la primera no basta**: si el filtro de calidad rechaza lo recuperado,
  la consulta se traduce al vocabulario de la norma y se vuelve a buscar una sola vez. Se paga
  solo cuando hace falta —el 28 % de las consultas del asistente público y el 71 % de las del
  interno—, y existe porque una pregunta escrita como intención («quiero tramitar una compra de
  6.500 euros») no comparte ni una palabra con el texto que la regula.
- **Un umbral de calidad que decide con la mejor fuente**, no con el promedio de todas. Promediar
  hacía que la cola de resultados votara sobre si hay respuesta, y convertía un parámetro de
  amplitud en el mando que decidía cuántas preguntas se contestan.
- **Selección escalonada por metadatos**, en tres niveles: un índice de materias acota primero el
  ámbito, se elige el subconjunto pertinente y solo entonces se consulta. Evita que una pregunta de
  un área traiga fundamento de otra, y reduce lo que viaja al modelo.
- **Vigencia garantizada en la recuperación**: una sola versión canónica por documento, lo derogado
  fuera del índice consultable y aviso explícito cuando la norma aplicable ha sido desplazada. El
  desempate entre fragmentos equivalentes es determinista, para que la misma consulta cite siempre
  las mismas fuentes en el mismo orden.
- **Calidad medida, no supuesta**, en dos niveles que conviene no confundir. En **integración
  continua** hay una puerta que mide el *mecanismo* de recuperación —fusión híbrida, filtros,
  ranking— sobre un corpus de prueba con un embedding determinista: corre en segundos y falla si
  la exhaustividad o el orden empeoran más de 0,02 respecto a la línea base versionada. La calidad
  **sobre el corpus real** se mide aparte y a mano, con un lote de consultas reales que llevan el
  veredicto escrito por la persona que las hizo (§5).
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

A esa base se le añadieron en agosto de 2026 dos piezas que el modelo multiinstitución exigía:

- **Frontera entre organizaciones explícita.** Cada tabla declara a qué ámbito pertenece
  —plataforma, organización, heredable o derivada— y una prueba lo vigila. Proveedores, modelos,
  prompts y permisos dejaron de ser globales: un ayuntamiento puede escribir sus propias
  instrucciones sin tocar las de otro, y lo que no está definido a su nivel se hereda del
  superior. El inventario tabla por tabla está escrito y comprobado por prueba, no deducido.
- **Administración separada por planos**: la gestión de la plataforma (organizaciones, personas,
  módulos concedidos) se separó de la administración de cada asistente, con concesión de módulos
  a una persona o a un grupo del proveedor de identidad.

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

## 5. Estado de desarrollo (26 de agosto de 2026)

El proyecto se ha desarrollado **en solitario**, con disciplina de desarrollo guiado por pruebas
(la prueba antes del código) y asistencia de agentes de programación sujetos a reglas de
arquitectura escritas y verificables.

**Cifras medidas.** La última ejecución completa de la suite de backend, el 25 de agosto, dio
**3.166 pruebas en verde**, una omitida y una en rojo —un guardarraíl de arquitectura, corregido
acto seguido; la suite completa no se ha vuelto a ejecutar después del arreglo, así que la última
sin ningún rojo es la del día anterior, con **3.107**—. En frontend, **661 pruebas en verde** el
26 de agosto. Desde el 22 de agosto la **integración continua ejecuta la suite entera**: hasta
entonces corría el 42 % de ella, y lo hace sin paralelismo a propósito, porque repartir las
pruebas entre procesos esconde el estado que se filtra de una a otra.

La verificación no es solo automática: cada módulo con interfaz se recorre en navegador antes de
darlo por cerrado, y las pruebas manuales humanas se reservan para lo que una máquina no puede
juzgar (identidad visual, calidad editorial, sistemas externos reales).

**Funcionalmente completo y verificado:**

| Área | Estado |
|---|---|
| Asistentes informativos con citas | ✅ En marcha sobre corpus real |
| Búsqueda híbrida, selección por metadatos y calidad medida | ✅ Puerta de regresión del mecanismo en integración continua; la calidad sobre el corpus real se mide a mano con el lote de consultas reales |
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
| Endurecimiento de seguridad | ✅ Tres rondas de auditoría cerradas, la última previa al despliegue |
| Frontera entre organizaciones | ✅ Ámbito declarado tabla por tabla, con inventario escrito y vigilado por prueba |
| Administración de plataforma e identidad | ✅ Organizaciones, personas y concesión de módulos, separadas de la administración de cada asistente |

**El piloto, con datos reales.** El corpus normativo de la Universitat Jaume I está cargado y
clasificado por ámbito y materia:

| Asistente | Acceso | Corpus |
|---|---|---|
| Normativa propia | Público, sin identificarse | 297 documentos / 23.306 fragmentos |
| Gerencia — económico-administrativo | Personal identificado | 124 documentos / 14.198 fragmentos |
| Gerencia — selección de documentos completos (pruebas) | Personal identificado | 127 documentos / 14.208 fragmentos |

Los dos últimos comparten corpus a propósito: existen para comparar **dos métodos de
recuperación** sobre el mismo material. Los embeddings y la reordenación se calculan por API del
proveedor de nube, con adaptador propio y proceso por lotes; los modelos locales siguen siendo una
dependencia opcional para quien exija que el cálculo no salga de su perímetro.

El **sitio de publicación del corpus** —portada, buscador y una página por norma con sus anclas—
está construido y hace de anfitrión del asistente público: quien lee una norma puede preguntar
sobre ella sin salir de la página, y la cita de la respuesta abre el artículo concreto.

**Qué dice la medición del asistente.** Se ha medido con **25 consultas reales del ensayo del
sistema anterior**, cada una con el veredicto escrito por la persona que la hizo, y con las
**7 consultas reales** que el personal de Gerencia hizo a su asistente. Los resultados, y esto es
lo que hay que leer con cuidado:

- El asistente público **contesta 22 de 25** consultas, frente a 18 antes del último bloque de
  trabajo. Contestar no es acertar: con la rúbrica del informador y un juez automático,
  **cumplen 9 de 25**. La distancia entre ambas cifras es el trabajo que queda.
- El asistente interno de Gerencia **contesta 6 de 7**. Su gemelo de pruebas contesta 7 de 7,
  pero **no porque recupere mejor**: su método no puntúa lo que recupera, así que su filtro de
  calidad no puede rechazar nada. Cuál de los dos acierta más lo tiene que decir Gerencia, y para
  eso hay una hoja de validación a ciegas ya generada y pendiente de sus veredictos.
- El defecto dominante del sistema anterior era **citar el curso académico equivocado** —15 de las
  25 consultas—, y eso ordena la configuración actual: se prefiere un contexto estrecho y limpio a
  uno amplio que mezcla normas de cursos distintos.

El detalle, con la configuración de cada asistente y la tabla consulta a consulta, está en
`docs/INFORME_CHATBOTS_NORMATIVA_Y_GERENCIA.html`.

**Lo que queda antes del despliegue con usuarios reales:**

1. **Despliegue de producción** en la infraestructura descrita (§4). Es lo único que queda por
   delante: los bloques de saneamiento, endurecimiento y calidad de respuesta previstos antes del
   despliegue están cerrados.
2. **Validación humana de los asistentes de Gerencia**: la hoja está generada; faltan los
   veredictos, y de lo que marquen saldrán las pruebas de regresión.
3. **Lote de consultas de referencia para Gerencia**: siete preguntas no son una medida. El
   mecanismo de carga es el mismo que ya se usa con el asistente público.
4. **Publicar el sitio del corpus**, para que las citas dejen de apuntar a una dirección local.
5. **Pruebas manuales finales** con datos e infraestructura reales.

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

**AGPL-3.0-or-later** con licencia dual comercial para partners, adoptada en agosto de 2026 con
la Universitat Jaume I como titular. La autoinstalación en un paso ya está resuelta, que era el
prerrequisito real de la distribución: un proyecto que no se puede instalar sin su autor no es
software libre en la práctica. El objetivo es que otra administración pueda levantar la plataforma
en su propia infraestructura, con su corpus y su identidad visual, sin depender del equipo
original.

Dos consecuencias de esa licencia ya están implementadas, y no son trámite: **la procedencia de
cada aportación se certifica** en el propio historial —una comprobación automática rechaza lo que
no la lleve, y la regla se aplica también al mantenedor, porque quien se exceptúa de su política
la deja sin fuerza— y **el enlace al código fuente que exige el artículo 13 de la AGPL viaja con
la aplicación**, incluido el widget que se incrusta en webs ajenas, que es el caso que se olvida.
El repositorio permanece privado hasta la apertura prevista.

## 9. Cómo verlo

El punto de entrada recomendado para una demostración es el asistente sobre normativa propia
—porque enseña las citas trazables y la respuesta de indisponibilidad, que es lo que más cuesta
creer sin verlo— seguido de la generación de un informe a partir de una hoja de cálculo real, que
enseña el determinismo y la revisión humana en el mismo recorrido.

El asistente se enseña mejor **dentro del sitio de publicación del corpus** que en una pantalla de
administración: se abre el buscador de normativa, se pregunta desde la propia norma que se está
leyendo, y la cita de la respuesta abre el artículo exacto. Ese recorrido enseña de una vez las
tres cosas que distinguen al sistema —fuente verificable, apertura por el artículo y aviso cuando
la norma aplicable ha sido desplazada— sin pedirle a nadie que se fíe.

## 10. Documentación disponible

| Documento | Qué contiene |
|---|---|
| `docs/Arquitectura.md` | Arquitectura funcional y técnica: módulos, roles, frontera cloud/edge/local, privacidad, decisiones estructurales |
| `docs/MARCO_GOBERNANZA_IA.md` | Marco normativo interno: principios de gobernanza, mecanismos que los implementan, evidencia generada y clasificación de riesgo por caso de uso |
| `docs/EU_GOVERNANCE_CONCEPT_NOTE.md` | Proyección del marco de gobernanza hacia consorcios y financiación europea |
| `docs/INFORME_CHATBOTS_NORMATIVA_Y_GERENCIA.html` | Configuración de los tres asistentes, pruebas realizadas y comparación con el sistema anterior, consulta a consulta |
| `docs/MULTITENENCIA.md` | Inventario del ámbito tabla por tabla: qué es de la plataforma, qué de cada organización y por qué camino se llega a ella |
| `docs/METODOLOGIA_AGENTICA.md` | Cómo se desarrolla: ejecución por bloques, verificación en navegador y qué se reserva al juicio humano |
| `docs/CONTRATO_MD_CORPUS.md` | Contrato del material que entra al corpus, y el pipeline de curación que lo produce |
| `docs/DESPLIEGUE_PROTOTIPO_GCP.md` | Plan del despliegue del piloto: piezas, orden, variables y riesgos |
| `planificacion/PLAN_DESARROLLO.md` | Plan de desarrollo del conjunto y decisiones durables (licencias, stack, identidad) |
| `docs/VALORACION_PROYECTO.md` | Auditoría global del proyecto: calidad, seguridad y sentido de producto |
| `docs/SANDBOX_SECURITY.md` | Aislamiento de la ejecución de código |
| `docs/REDACCION_CONTRACT_FIRST.md` | Contrato del módulo de informes |
| `docs/A11Y_CHECKLIST.md` | Verificación de accesibilidad |
| `planificacion/PROJECT_STATE.md` | Estado vivo del desarrollo, al día |
| `planificacion/HISTORIAL.md` | Por qué cada cosa se hizo como se hizo: desviaciones, defectos encontrados al verificar y decisiones con su razón |

---

*Contacto y demostración: Modesto Fabra (fabra@uji.es), Universitat Jaume I.*

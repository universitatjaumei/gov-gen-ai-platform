# Marco de Gobernanza de IA — Gov Gen AI Platform

> **Naturaleza del documento**: marco normativo interno del proyecto. Formaliza los principios de
> gobernanza que rigen la aplicación de IA en procesos de administraciones públicas mediante esta
> plataforma, y los traduce en obligaciones verificables de diseño y desarrollo.
>
> **Fecha de revisión**: 18 de agosto de 2026. El estado de implementación que se indica en §4
> corresponde a esa fecha.
>
> **Relación con otros documentos**: este marco es la referencia interna. La presentación del
> proyecto para lectores externos es `PRESENTACION_PROYECTO.md`; su proyección hacia consorcios y
> financiación europea vive en `docs/EU_GOVERNANCE_CONCEPT_NOTE.md` y `docs/EU_GOVERNANCE_TOPICS.md`.
> Las reglas de arquitectura que lo implementan son vinculantes para los agentes de desarrollo vía
> `CLAUDE.md`. El estado detallado de cada mecanismo se sigue en `PROJECT_STATE.md`.

---

## 1. Propósito y alcance

Gov Gen AI Platform aplica IA generativa y automatización a procesos de administraciones públicas:
asistentes informativos con recuperación documental, redacción asistida de informes, extracción y
transformación de datos, curación de contenido y —en fase futura— tramitación de expedientes. En
ese contexto, la conformidad normativa no puede gestionarse como documentación estática
desconectada del sistema en ejecución: debe estar **incorporada al diseño** y **producir evidencia
continua**.

Este marco establece los principios que gobiernan **todo** desarrollo de la plataforma, con dos
funciones:

1. **Ex-ante**: cada funcionalidad nueva se diseña conforme a estos principios (gobernanza por
   diseño, no por revisión posterior).
2. **Ex-post**: el sistema genera evidencia auditable de que cada actuación asistida por IA respetó
   supervisión humana, trazabilidad, protección de datos y calidad de la información.

El enfoque de fondo es **compliance-as-code**: traducir obligaciones normativas en comprobaciones
ejecutables y artefactos de evidencia, en lugar de confiar en la buena fe del desarrollador o en
auditorías puntuales.

**Alcance de este marco.** Los principios de §4 obligan al **diseño de la herramienta**. Hay
obligaciones de gobernanza que no son —ni pueden ser— propiedades de una herramienta: el inventario
de casos de uso, el registro de sistemas de IA, la asignación de responsabilidades o la aprobación
del alta de un uso nuevo son actos de gobierno. §3 separa los dos planos y dice qué corresponde a
cada uno, porque confundirlos produce dos errores simétricos: esperar que una aplicación garantice
lo que solo puede decidir un órgano, y creer que basta con una política escrita para que el sistema
se comporte conforme a ella.

## 2. Marco normativo de referencia

| Norma | Relevancia para la plataforma |
|---|---|
| **Reglamento (UE) 2024/1689 — Reglamento de IA (RIA)** | Gobernanza de datos (art. 10), registro de eventos (art. 12), transparencia (art. 13), supervisión humana (art. 14), evaluación de impacto en derechos fundamentales (FRIA, art. 27), etiquetado de contenido generado (art. 50) |
| **Reglamento (UE) 2016/679 — RGPD** | Minimización de datos, privacidad por diseño y por defecto (art. 25), seudonimización (art. 4.5), base jurídica del tratamiento, decisiones automatizadas (art. 22), transferencias internacionales |
| **LOPDGDD** | Disposición adicional 7ª (identificación de interesados en publicaciones y notificaciones administrativas — base de los modos de disociación) |
| **Ley 39/2015** | Procedimiento administrativo común; normativa aplicable en la fecha de referencia del expediente |
| **Ley 40/2015** | Art. 41: actuación administrativa automatizada — exige órgano responsable, auditoría del sistema y supervisión |
| **Interoperable Europe Act / EIF** | Interoperabilidad, estándares abiertos, reutilización entre administraciones, evitación de *lock-in* |
| **Esquema Nacional de Seguridad (ENS)** | Seguridad de la información en sistemas del sector público español |

La clasificación de riesgo del RIA se evalúa **por caso de uso**, no por plataforma (§6).

## 3. Los dos planos de la gobernanza

La gobernanza de la IA en una administración se juega en dos planos que no se sustituyen entre sí.
Esta separación es el eje del documento: determina qué se puede exigir a un sistema y qué hay que
resolver por otra vía.

### 3.1 Plano institucional (superior)

Decisiones de gobierno y actos administrativos. Dependen de órganos con competencia, y su evidencia
es documental y organizativa:

- **Inventario de casos de uso de IA** de la organización y su **registro**, incluidos los usos que
  no pasan por esta plataforma.
- **Clasificación de riesgo** de cada caso de uso conforme al RIA y su revisión.
- **Designación del órgano responsable** de la actuación administrativa automatizada (Ley 40/2015
  art. 41) y de la persona de contacto del delegado de protección de datos.
- **Base jurídica** del tratamiento y, cuando procede, **evaluación de impacto** en protección de
  datos (RGPD art. 35) y en derechos fundamentales (RIA art. 27).
- **Aprobación del alta** de un caso de uso nuevo, **retirada** de un uso que deja de ser
  aceptable, y **revisión periódica** de umbrales y clasificaciones.
- **Políticas de uso** dirigidas al personal y formación asociada.

**Estas funciones no las gestiona Gov Gen AI Platform, y no está previsto que lo haga.** Se
gestionan al margen, con aplicaciones y procedimientos propios. La razón es de diseño, no de
prioridades: un inventario institucional debe abarcar *todos* los sistemas de IA de la
organización, así que alojarlo dentro de una de las herramientas que debe inventariar lo dejaría
estructuralmente incompleto y sujeto al ciclo de vida de esa herramienta.

### 3.2 Plano de la herramienta

Propiedades que un sistema puede garantizar por diseño y demostrar por construcción. Es el objeto
de los principios de §4 y de la evidencia de §5: preferencia por el cómputo verificable, ninguna
afirmación sin fuente, supervisión humana instrumentada, registro por ejecución, disociación previa
al modelo, localización del dato, calidad del corpus, portabilidad y aislamiento de la ejecución de
código.

### 3.3 Cómo se relacionan

| Sentido | Qué viaja | Ejemplo |
|---|---|---|
| **Del plano superior a la herramienta** | Las decisiones de gobierno se traducen en **configuración** que la plataforma ejecuta | El nivel de modelo asignado a cada actividad, el modo de disociación exigido, dónde hay puertas de revisión humana, los umbrales de calidad de un caso de uso |
| **De la herramienta al plano superior** | La plataforma produce la **evidencia** con la que el plano superior responde ante una auditoría | Manifiesto de ejecución, registro de aprobaciones humanas, modo de disociación aplicado, informes de calidad del corpus (§5) |

La consecuencia práctica, y es la regla que resuelve las dudas de alcance: **la plataforma es donde
las decisiones de gobernanza se hacen efectivas y verificables, no donde se toman ni donde se
declaran.** Si una obligación consiste en decidir, documentar o responder ante terceros, pertenece
al plano superior. Si consiste en garantizar que el sistema se comporta de una manera determinada,
pertenece a este marco.

Cómo se acoplen ambos planos —qué campos describen un uso de IA, cómo se codifica la clasificación
de riesgo, cómo se referencia el órgano responsable— es una decisión de gobernanza sectorial que
conviene tomar de forma compartida entre administraciones, y no algo que deba resolver por su
cuenta cada herramienta.

## 4. Principios de gobernanza de la herramienta

Cada principio se enuncia con su fundamento, el mecanismo de la plataforma que lo materializa, su
estado de implementación y las obligaciones de desarrollo que impone.

Leyenda de estado: **✅ implementado y verificado** · **▶ parcial** · **⏳ previsto en fase futura**.

### P1 — Determinismo primero · ✅

**Principio.** Siempre que un resultado pueda obtenerse mediante cómputo determinista y verificable
(reglas, parsers, extracción estructurada, plantillas), se prefiere esa vía sobre el LLM. La IA
generativa se reserva para lo que el determinismo no alcanza, y su salida se contrasta con
verificaciones deterministas cuando es posible.

**Por qué.** Un proceso determinista es reproducible, explicable línea a línea y auditable sin
inferencia estadística. Reduce simultáneamente el riesgo jurídico (opacidad), el operativo
(alucinación) y el económico (coste por token). En actuación administrativa, la explicabilidad
plena es un requisito de legalidad, no una preferencia técnica.

**Mecanismos.** Extracción determinista de hojas de cálculo y PDF; **veinte operaciones declarativas
de transformación de datos** que cubren limpieza, cálculo de columnas derivadas, conversión de
importes escritos como texto, orden y remodelado; **once tipos de gráfico** deterministas con su
presentación completa; detección determinista de patologías documentales antes que la semántica;
ejecución de código fuera del LLM (el grafo orquesta, no genera el cómputo).

Cuando una petición se expresa en lenguaje natural, el patrón es **plan declarativo primero y
código como último recurso**: el modelo rellena un contrato cerrado de operaciones o de
configuración, que puede mostrarse al usuario antes de aplicarse; solo si la petición no cabe en el
contrato se genera código, y entonces pasa por el circuito de auditoría de P11. Que el modelo
declare que la petición no encaja es una **respuesta válida** y no se reintenta.

**Obligaciones de desarrollo.**
- Ante una tarea nueva, justificar el uso de LLM: si existe solución determinista razonable, se
  implementa esa.
- Cuando el LLM actúa como *fallback*, la ruta usada (determinista o IA) queda registrada en la
  traza de ejecución.
- La salida del LLM que alimenta decisiones se valida contra contratos tipados (Pydantic/JSON
  Schema); una salida no conforme se rechaza, no se "arregla" silenciosamente.
- El catálogo de operaciones y de tipos admitidos que se muestra al modelo **se genera del propio
  contrato**: una lista escrita a mano en un prompt divergiría del sistema en el primer cambio.

### P2 — Frugalidad algorítmica · ✅

**Principio.** Se usa el mínimo recurso computacional que resuelve el problema con la calidad
requerida: el modelo más pequeño suficiente, el menor contexto necesario, el menor número de
llamadas, y cómputo local antes que remoto cuando la tarea lo permite y la localización del dato lo
exige.

**Por qué.** La frugalidad es a la vez principio de eficiencia del gasto público, de sostenibilidad
energética y de minimización de exposición de datos: cada token que no se envía a un LLM de
terceros es un dato que no sale del perímetro.

**Mecanismos.** Escalera de recursos (determinista → modelo pequeño → modelo grande) mediante
**niveles de modelo asignados por actividad**: cada actividad de la plataforma declara con qué nivel
corre —redactar es un nivel, supervisar código es un nivel superior— y esa asignación es
configuración administrativa, sobreescribible sin desplegar. Recuperación acotada: solo los
fragmentos relevantes viajan al modelo, nunca el corpus. Cálculo de embeddings por API del
proveedor en el despliegue previsto, con **la pila de modelos locales como dependencia opcional**
que se instala solo cuando la institución exige que el cálculo no salga de su perímetro.

**Obligaciones de desarrollo.**
- No fijar el modelo más potente por defecto: la elección es configuración por caso de uso, con el
  más frugal que cumpla los criterios de evaluación (§5).
- No enviar al LLM contexto que no contribuye a la tarea (minimización aplicada al prompt).
- No reintentar una respuesta deliberada del modelo: reintentar lo que el modelo ha decidido gasta
  llamadas para oír lo mismo.
- No añadir infraestructura anticipadamente: la escala sigue a la métrica real, no a la previsión.

### P3 — Supervisión humana significativa · ✅

**Principio.** Ninguna decisión con efectos jurídicos o significativos sobre personas se adopta de
forma completamente automatizada por IA generativa. El sistema define puntos de control humano
obligatorios cuya superación queda registrada con identidad del revisor.

**Por qué.** RIA art. 14 y RGPD art. 22. La supervisión debe ser *significativa*: la persona debe
poder entender qué revisa (de ahí P5 y P6) y su intervención debe estar instrumentada, no ser un
clic ritual.

**Mecanismos.** Puertas de revisión en los grafos de ejecución, registro de aprobaciones y máquina
de estados por bloque. En el módulo de informes está **operativo y es bloqueante**: un informe con
apartados redactados por IA no puede previsualizarse ni exportarse hasta que una persona los
aprueba, y el sistema indica exactamente qué falta aprobar. La cola de aprobación de código
generado añade una segunda instancia: el administrador vuelve a ejecutar el código contra los
mismos datos y compara el resultado antes de aprobarlo.

**Obligaciones de desarrollo.**
- Todo flujo que produzca un documento o decisión con destino a un procedimiento administrativo
  incluye al menos una puerta de revisión antes del efecto.
- La aprobación humana se persiste (quién, cuándo, qué versión aprobó) y forma parte de la
  evidencia de auditoría.
- No se implementan mecanismos de aprobación en bloque que vacíen de contenido la revisión.
- **Un control que no hace nada es peor que no tenerlo**: un botón de aprobación cuya acción no se
  consuma en ningún sitio induce a creer que la revisión ocurrió. Se trata como defecto.

### P4 — Legalidad por diseño · ▶

**Principio.** El sistema solo ofrece al usuario las acciones que la norma le autoriza según su
rol, la fase del procedimiento y el estado del expediente. Esa lógica vive exclusivamente en el
servidor; la interfaz no puede fabricarla ni eludirla.

**Por qué.** Si las reglas de competencia están dispersas en el frontend, la conformidad depende de
cada pantalla. Centralizarlas en una máquina de estados servidora las hace únicas, testeables y
auditables.

**Estado.** El patrón está **aplicado** donde hay máquina de estados: las transiciones válidas de
cada bloque de un informe las calcula el servidor, y el cliente no decide qué se puede hacer. Su
forma plena —el contrato con la lista de acciones permitidas por expediente— llega con el **Gestor
de Expedientes** (fase futura), que es donde la fase del procedimiento y el rol determinan la
competencia.

**Mecanismos.** Contrato HATEOAS: el DTO de cada expediente incluirá `acciones_permitidas`,
calculado en el servidor evaluando fase, estado y rol. El frontend genera los controles iterando
ese array (regla maestra en `CLAUDE.md`).

**Obligaciones de desarrollo.**
- Prohibido en el frontend cualquier condicional de negocio del tipo `if (fase === X) mostrar()`.
- Los tests de backend verifican que un usuario sin permisos recibe un array de acciones vacío.

### P5 — Transparencia estructural (Contract-First) · ✅

**Principio.** El backend es la única fuente de verdad de la lógica y de los formularios; el
frontend es reactivo. El contrato (OpenAPI y contrato de interfaz dirigido por el servidor) es un
artefacto auditable que describe exactamente qué hace el sistema.

**Por qué.** RIA art. 13. La transparencia que depende de documentación manual se desactualiza; la
que emana del contrato es estructural: el sistema no puede comportarse de forma distinta a lo que
su contrato declara.

**Mecanismos.** Arquitectura Contract-First; formularios generados a partir del contrato de la
plantilla y no escritos en la interfaz; tipos y hooks del frontend generados desde el contrato del
servidor; validación de cliente derivada de la del servidor.

**Obligaciones de desarrollo.**
- Ningún dato de negocio, regla de estado ni estructura de formulario hardcodeada en el frontend.
- Todo cambio de comportamiento visible pasa por un cambio de contrato, versionable y revisable.

### P6 — Trazabilidad y auditabilidad *by construction* · ✅

**Principio.** Cada ejecución asistida por IA produce evidencia inmutable y suficiente para su
revisión ex-post: qué entradas se usaron, qué modelo y versión, qué fuentes fundamentan cada
afirmación, qué intervenciones humanas hubo y qué salida se produjo.

**Por qué.** RIA art. 12 (registro de eventos) y Ley 40/2015 art. 41 (auditoría de la actuación
automatizada). Sin trazabilidad no hay rendición de cuentas ni derecho de defensa efectivo del
ciudadano afectado.

**Mecanismos.** Manifiesto de ejecución por corrida (modelo, versión de instrucciones y ruta
seguida en cada paso); citas trazables al fragmento de origen, con validación del contrato de citas
que **sustituye una respuesta sin fuentes verificables por una respuesta de indisponibilidad**
—el sistema no emite una afirmación que no pueda fundamentar—; desempate determinista entre
fragmentos equivalentes, para que la misma consulta cite siempre las mismas fuentes en el mismo
orden; observabilidad por spans; registro de auditoría en los grafos.

**Obligaciones de desarrollo.**
- Toda respuesta destinada a usuarios finales incluye citas resolubles a su fragmento fuente; una
  afirmación sin fuente es un defecto, no una característica.
- Los nodos de grafo no producen efectos fuera de los campos tipados del estado: el estado es el
  registro.
- Los registros de auditoría son de solo-anexado; no se editan ni borran desde la aplicación.
- La retirada de una plantilla o configuración usada por actuaciones pasadas **no puede romper su
  reconstrucción**: se archiva, no se borra.

### P7 — Minimización y anonimización de datos personales · ✅

**Principio.** Los datos personales solo se exponen a un LLM cuando es imprescindible, y en ese
caso previa disociación. La anonimización admite modos graduados —desde detección hasta enmascarado
irreversible— y, cuando es reversible, la reversión está auditada y controlada.

**Por qué.** RGPD arts. 5.1.c y 25; LOPDGDD D.A. 7ª. La exposición de datos identificativos a
modelos de terceros es el principal riesgo de privacidad de la IA generativa en el sector público.

**Mecanismos.** Contexto de anonimización por ejecución con cuatro modos (desactivado / detección /
sustitución reversible / enmascarado irreversible) y mapas directo e inverso aplicados antes y
después de la llamada al modelo. Regla de frontera: **el edge entrega los datos ya anonimizados a
la pasarela de modelos; la pasarela no anonimiza** — la responsabilidad está en un único punto,
antes de que el dato cruce. Los datos de prueba de un script destinado a una plantilla compartida
se anonimizan antes de que el script se pruebe.

**Obligaciones de desarrollo.**
- Ningún servicio invoca al LLM con datos de expedientes o ciudadanos saltándose el contexto de
  anonimización cuando el caso de uso lo exige.
- Las categorías especiales de datos (art. 9 RGPD) usan enmascarado irreversible, nunca
  sustitución reversible.
- Los mapas de reversión no salen del edge ni se registran en trazas enviadas al cloud.

### P8 — Soberanía de datos: frontera edge-cloud · ✅

**Principio.** Los datos del cliente final (conversaciones, documentos, expedientes, fragmentos,
embeddings) y la lógica operacional que los procesa residen en el **edge** (la infraestructura de
la institución). El **cloud** solo conserva configuración y métricas anonimizadas. El cloud
orquesta; el edge ejecuta.

**Por qué.** Requisito regulatorio en despliegues edge+cloud (localización del dato) y garantía
estructural: lo que no sale del perímetro no puede fugarse. La frontera es arquitectónica, no
contractual.

**Mecanismos.** Bases de datos ORM separadas —configuración sincronizable del cloud al edge frente
a datos operacionales solo-edge, sin relaciones cruzadas—, un proveedor de configuración como único
acceso del edge a los datos de configuración, clasificación de módulos y de superficies HTTP
regulada en tiempo de ejecución por el modo de despliegue, y una única superficie de sincronización
que ve ambos mundos.

**Obligaciones de desarrollo.**
- Un módulo edge no importa módulos cloud; los grafos, el ejecutor de tareas y el módulo de
  automatización son edge y no leen modelos de configuración directamente.
- Toda superficie HTTP nueva se etiqueta con su plano de despliegue y se registra en el arranque
  correspondiente.
- Ante la duda: si toca datos del cliente final → edge; si solo configuración → cloud; si ambos →
  partir la responsabilidad. (Detalle en `CLAUDE.md`.)

### P9 — Calidad y vigencia de la información que consume la IA · ✅

**Principio.** La información que alimenta la recuperación se audita antes y durante su uso:
detección de obsolescencia, sustitución, duplicidad y contradicción. El contenido patológico se
excluye del corpus consultable, y la exclusión queda registrada.

**Por qué.** RIA art. 10 (gobernanza de datos) y derecho a la buena administración: una respuesta
correcta sobre una norma derogada es un daño, no un acierto. La calidad del corpus es una cuestión
de gobernanza, no solo de higiene técnica.

**Mecanismos.** Módulo propio de curación: rastreo de sitios institucionales, detectores
deterministas y semánticos de patologías documentales, informes de calidad, exclusión registrada y
publicación controlada hacia el corpus. **Caducidad activa**: cada documento lleva fecha de revisión
prevista y, cuando vence, el sistema lo señala como pendiente de revisión. **Detección de huecos**:
las consultas que el sistema no logra fundamentar —y el feedback negativo— alimentan una cola de
revisión de contenido. Al corpus solo entra documentación conforme a un **contrato de formato**
explícito, producido por un proceso de curación externo a la aplicación.

Regla de coste que mantiene la clasificación revisable: **la taxonomía nunca entra en el texto que
se embebe**. Reclasificar el corpus debe costar una actualización de metadatos, no un reindexado
completo; si un cambio de etiqueta obliga a recalcular embeddings, la clasificación deja de
revisarse en la práctica.

**Obligaciones de desarrollo.**
- La ingesta de fuentes nuevas pasa por el pipeline de auditoría antes de indexarse.
- Los resultados de auditoría (qué se excluyó y por qué) son consultables por el administrador.
- El vocabulario de clasificación es **dato versionado, no código**: los términos viven en tabla
  con vigencia y sustitución, no en enumeraciones del programa.

### P10 — Portabilidad e independencia de proveedor · ✅

**Principio.** El sistema funciona sin cambios de código sobre distintos proveedores de nube,
almacenamiento, base de datos y modelo de IA, cambiando solo configuración. La dependencia de un
proveedor concreto es un riesgo de soberanía y de competencia en la compra pública.

**Mecanismos.** Servicio de almacenamiento abstracto (sistema de ficheros, S3/MinIO o
almacenamiento de objetos de nube por variable de entorno), conexión a base de datos únicamente por
variable de entorno, protocolo de embeddings con implementaciones intercambiables (local o por API,
con adaptador propio por proveedor), un único punto de selección de modelo, instalación en un paso y
distribución como software libre (AGPLv3 con licencia dual comercial).

**Obligaciones de desarrollo.**
- Prohibido el acceso directo al sistema de ficheros para documentos de negocio y el hardcodeo de
  credenciales o endpoints de proveedor.
- Si un servicio usa un proveedor por API, no puede además importar la implementación local como
  respaldo silencioso: el respaldo se configura, no se decide en la lógica de negocio.

### P11 — Seguridad de la ejecución orquestada por IA · ✅

**Principio.** El código que la IA produce o dispara se ejecuta en aislamiento estricto, con
capacidades mínimas, sin acceso a la red salvo lo autorizado, y con re-auditoría del código antes
de ejecutar.

**Mecanismos.** Auditoría estática **graduada en tres niveles** (aceptable / advertencia /
crítico) con el número de línea de cada hallazgo, dos listas independientes —denegación explícita de
capacidades frente a «no está en la lista blanca»— y detección de rutas absolutas: un módulo que
falta en una lista blanca es un hueco que una persona puede aceptar; el acceso al sistema operativo
es una capacidad y no. Sobre esa auditoría determinista, y **nunca en su lugar**, un modelo
supervisor de nivel superior revisa lo que un análisis estático no puede ver (si el código hace lo
que se pidió, si asume nombres de columna, si puede devolver datos vacíos sin fallar). La ejecución
ocurre en un **microservicio aislado sin acceso a red**, que **vuelve a auditar** el código con su
propio analizador antes de ejecutarlo, y un guardarraíl impide que ese segundo analizador quede más
laxo que el primero. Ver `docs/SANDBOX_SECURITY.md`.

**Obligaciones de desarrollo.**
- Ningún script de usuario ni código generado se ejecuta en el proceso del servidor.
- Las capacidades del sandbox se amplían por lista blanca explícita, nunca por defecto.
- No se admite un campo de expresión o fórmula evaluable en un contrato declarativo: sería la misma
  capacidad que el auditor prohíbe en un script, por otra puerta y sin auditor delante. Lo compuesto
  se expresa encadenando operaciones auditables.

## 5. Evidencia y auditoría de cumplimiento

La conformidad se demuestra con artefactos que el sistema genera por construcción. Esta evidencia
es la que el plano institucional (§3.1) puede invocar ante una auditoría:

| Obligación | Evidencia generada | Estado |
|---|---|---|
| Registro de eventos (RIA art. 12) | Manifiesto por ejecución con modelo, versión de instrucciones y ruta seguida, más spans de observabilidad | ✅ |
| Supervisión humana (RIA art. 14) | Registro de aprobaciones con identidad, momento y versión aprobada | ✅ |
| Transparencia (RIA art. 13) | Contrato OpenAPI y contrato de interfaz versionados | ✅ |
| Gobernanza de datos (RIA art. 10) | Informes de auditoría del corpus, exclusiones registradas y cola de huecos de contenido | ✅ |
| Minimización y seudonimización (RGPD) | Modo de disociación aplicado, registrado por ejecución | ✅ |
| Localización del dato | Clasificación edge/cloud verificable en tiempo de ejecución | ✅ |
| Calidad de la recuperación | Métricas deterministas sobre conjunto de consultas de referencia, como puerta de integración continua | ✅ |
| Calidad de la salida | Métricas de fidelidad y relevancia más veredicto humano por escenario | ▶ evaluación periódica; el circuito de revisión humana del asistente interno está previsto |
| Accesibilidad | Verificación WCAG como puerta de integración continua | ✅ |
| Trazabilidad de la configuración | Historial de cambios de instrucciones y de nivel de modelo por actividad, con autoría | ✅ |

**Evaluación continua.** Opera en dos capas complementarias, ninguna de ellas telemetría opcional.
(1) La **calidad de la recuperación** se mide con métricas deterministas sobre un conjunto de
consultas con las fuentes que deberían recuperarse, y actúa como **puerta de integración continua**:
ningún cambio del recuperador se adopta si degrada la recuperación por debajo de la línea base.
(2) La **calidad de la salida** —fundamentación y relevancia— es criterio de aceptación periódico,
complementado por escenarios de prueba con veredicto humano: un caso de uso cuya fidelidad cae por
debajo del umbral definido para él no se despliega, o se retira de servicio hasta corregirse.

**Sobre la FRIA.** La Evaluación de Impacto en Derechos Fundamentales (RIA art. 27) es una
obligación del **plano institucional**: la decide, redacta y mantiene el órgano competente. Lo que
aporta la plataforma es la evidencia con la que esa evaluación deja de ser un documento estático y
puede sostenerse en datos de ejecución reales.

## 6. Clasificación de riesgo por caso de uso (RIA)

Este cuestionario pertenece al **plano institucional**: lo responde y lo registra quien da de alta
el caso de uso, y su conclusión se conserva fuera de la plataforma. Se incluye aquí porque
determina qué configuración de gobernanza debe aplicarse en la herramienta.

1. **¿Afecta al acceso a servicios públicos esenciales, o evalúa o clasifica a personas físicas con
   efectos sobre sus derechos?** → posible **alto riesgo** (Anexo III RIA): exige evaluación de
   impacto, registro, y refuerzo de P3 (supervisión) y P6 (trazabilidad) antes de producción.
2. **¿Interactúa con ciudadanos?** → obligaciones de transparencia (art. 50): informar de que se
   interactúa con un sistema de IA y etiquetar el contenido generado.
3. **¿Trata datos personales?** → determinar base jurídica, aplicar P7 con el modo de disociación
   adecuado y, si procede, evaluación de impacto (RGPD art. 35).
4. **¿Produce efectos jurídicos automatizados?** → prohibido sin intervención humana significativa
   (P3); verificar encaje con Ley 40/2015 art. 41, con órgano responsable declarado.
5. **¿Puede resolverse de forma determinista?** → aplicar P1 antes de aceptar la solución con LLM.

Los usos actuales de la plataforma —asistencia informativa con citas, redacción asistida con
revisión humana, extracción con validación— se sitúan en general en riesgo **limitado**. El
cuestionario existe precisamente para detectar cuándo un caso concreto cruza a alto riesgo.

## 7. Gobernanza operativa

Salvo donde se indica, estas funciones pertenecen al **plano institucional** (§3.1) y se gestionan
fuera de la plataforma. Se enumeran aquí para que la frontera quede explícita:

- **Responsable del sistema** (institucional): cada despliegue declara el órgano responsable de la
  actuación administrativa automatizada y el contacto del delegado de protección de datos.
- **Inventario y registro de casos de uso** (institucional): mantenidos en aplicaciones propias,
  con alcance sobre todos los sistemas de IA de la organización, no solo los de esta plataforma.
- **Alta de un caso de uso** (institucional, con efecto en la herramienta): requiere el cuestionario
  del §6 respondido y registrado; su consecuencia en la plataforma es la configuración de los
  parámetros de gobernanza —modo de disociación, puertas de revisión, umbrales de evaluación, nivel
  de modelo asignado—.
- **Cambios de configuración** (herramienta): toda modificación de contrato, de instrucciones de
  sistema o de modelo asignado queda versionada, con autoría, y asociada a las ejecuciones
  posteriores mediante el manifiesto.
- **Incidentes** (ambos planos): una salida incorrecta con efecto sobre una persona se trata como
  incidente. La plataforma aporta la evidencia del §5 para reconstruir qué ocurrió; la valoración
  del impacto, la comunicación y la decisión de retirada corresponden al plano institucional.
- **Revisión periódica** (institucional): los umbrales de evaluación y la clasificación de riesgo se
  revisan al menos una vez al año y ante cambios normativos o de modelo relevantes.

## 8. Documentos relacionados

- `PRESENTACION_PROYECTO.md` — presentación del proyecto, módulos y estado de desarrollo para
  lectores externos.
- `CLAUDE.md` — reglas de arquitectura vinculantes que implementan este marco.
- `docs/EU_GOVERNANCE_CONCEPT_NOTE.md` y `docs/EU_GOVERNANCE_TOPICS.md` — proyección del marco hacia
  consorcios y financiación europea.
- `docs/SANDBOX_SECURITY.md` — detalle del principio P11.
- `docs/REDACCION_CONTRACT_FIRST.md` — aplicación de P4 y P5 al módulo de informes.
- `Arquitectura.md` — arquitectura funcional y técnica.
- `PROJECT_STATE.md` — estado de implementación al día.

> **Nota de vigencia**: los estados indicados en §4 y §5 corresponden al 18 de agosto de 2026. Los
> mecanismos marcados como previstos reflejan la arquitectura objetivo: este marco es normativo para
> ambos casos —lo implementado debe conservar estas propiedades y lo nuevo debe nacer conforme a
> ellas—. La distinción de planos del §3 no es descriptiva sino de alcance: nada de lo que §3.1
> atribuye al plano institucional debe implementarse dentro de la plataforma sin revisar antes esta
> decisión.

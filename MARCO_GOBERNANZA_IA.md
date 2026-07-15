# Marco de Gobernanza de IA — Gov Gen AI Platform

> **Naturaleza del documento**: marco normativo interno del proyecto. Formaliza los principios de
> gobernanza que rigen la aplicación de IA en procesos de administraciones públicas mediante esta
> plataforma, y los traduce en obligaciones verificables de diseño y desarrollo.
>
> **Relación con otros documentos**: este marco es la referencia interna. Su proyección hacia
> consorcios y financiación europea vive en `docs/EU_GOVERNANCE_CONCEPT_NOTE.md` y
> `docs/EU_GOVERNANCE_TOPICS.md`. Las reglas de arquitectura que lo implementan son vinculantes para
> los agentes de desarrollo vía `CLAUDE.md`. El estado de implementación de cada mecanismo se sigue
> en `PROJECT_STATE.md` y los planes de fase.

---

## 1. Propósito y alcance

Gov Gen AI Platform aplica IA generativa y automatización a procesos de administraciones públicas:
asistentes ciudadanos (RAG), tratamiento de expedientes, redacción asistida, extracción de datos,
flujos ETL y scripts. En ese contexto, la conformidad normativa no puede gestionarse como
documentación estática desconectada del sistema en ejecución: debe estar **incorporada al diseño**
y **producir evidencia continua**.

Este marco establece los principios que gobiernan **todo** desarrollo de la plataforma, con dos
funciones:

1. **Ex-ante**: cada funcionalidad nueva se diseña conforme a estos principios (gobernanza por
   diseño, no por revisión posterior).
2. **Ex-post**: el sistema genera evidencia auditable de que cada actuación asistida por IA respetó
   supervisión humana, trazabilidad, protección de datos y calidad de la información.

El enfoque de fondo es **compliance-as-code**: traducir obligaciones normativas en comprobaciones
ejecutables y artefactos de evidencia, en lugar de confiar en la buena fe del desarrollador o en
auditorías puntuales.

## 2. Marco normativo de referencia

| Norma | Relevancia para la plataforma |
|---|---|
| **Reglamento (UE) 2024/1689 — Reglamento de IA (RIA)** | Gobernanza de datos (art. 10), registro de eventos (art. 12), transparencia (art. 13), supervisión humana (art. 14), evaluación de impacto en derechos fundamentales (FRIA, art. 27), etiquetado de contenido generado |
| **Reglamento (UE) 2016/679 — RGPD** | Minimización de datos, privacidad por diseño y por defecto (art. 25), seudonimización (art. 4.5), base jurídica del tratamiento, transferencias internacionales |
| **LOPDGDD** | Disposición adicional 7ª (identificación de interesados en publicaciones y notificaciones administrativas — base de los modos de disociación) |
| **Ley 40/2015** | Art. 41: actuación administrativa automatizada — exige órgano responsable, auditoría del sistema y supervisión |
| **Interoperable Europe Act / EIF** | Interoperabilidad, estándares abiertos, reutilización entre administraciones, evitación de *lock-in* |
| **Esquema Nacional de Seguridad (ENS)** | Seguridad de la información en sistemas del sector público español |

La clasificación de riesgo del RIA se evalúa **por caso de uso**, no por plataforma (§5).

## 3. Principios de gobernanza

Cada principio se enuncia con su fundamento, el mecanismo de la plataforma que lo materializa y las
obligaciones de desarrollo que impone.

### P1 — Determinismo primero

**Principio.** Siempre que un resultado pueda obtenerse mediante cómputo determinista y verificable
(reglas, parsers, extracción estructurada, plantillas), se prefiere esa vía sobre el LLM. La IA
generativa se reserva para lo que el determinismo no alcanza, y su salida se contrasta con
verificaciones deterministas cuando es posible.

**Por qué.** Un proceso determinista es reproducible, explicable línea a línea y auditable sin
inferencia estadística. Reduce simultáneamente el riesgo jurídico (opacidad), el operativo
(alucinación) y el económico (coste por token). En actuación administrativa, la explicabilidad
plena es un requisito de legalidad, no una preferencia técnica.

**Mecanismos.** Pipelines de extracción, generación de gráficos y ETL deterministas con *fallback*
a IA auditado; detección determinista de patologías documentales antes que la semántica; ejecución
de scripts fuera del LLM (el grafo orquesta, no genera el cómputo).

**Obligaciones de desarrollo.**
- Ante una tarea nueva, justificar el uso de LLM: si existe solución determinista razonable, se
  implementa esa.
- Cuando el LLM actúa como *fallback*, la ruta usada (determinista o IA) queda registrada en la
  traza de ejecución.
- La salida del LLM que alimenta decisiones se valida contra contratos tipados (Pydantic/JSON
  Schema); una salida no conforme se rechaza, no se "arregla" silenciosamente.

### P2 — Frugalidad algorítmica

**Principio.** Se usa el mínimo recurso computacional que resuelve el problema con la calidad
requerida: el modelo más pequeño suficiente, el menor contexto necesario, el menor número de
llamadas, y cómputo local (edge) antes que remoto cuando la tarea lo permite.

**Por qué.** La frugalidad es a la vez principio de eficiencia del gasto público, de sostenibilidad
energética y de minimización de exposición de datos: cada token que no se envía a un LLM de
terceros es un dato que no sale del perímetro.

**Mecanismos.** Escalera de recursos (determinista → modelo local/pequeño → LLM grande) configurada
por caso de uso vía `model_factory`; embeddings locales (BGE-M3) como opción por defecto; servicios
de cómputo pesado extraíbles a microservicios con escala a cero; recuperación RAG acotada (solo los
fragmentos relevantes viajan al modelo, nunca el corpus).

**Obligaciones de desarrollo.**
- No fijar el modelo más potente por defecto: la elección de modelo es configuración por caso de
  uso, con el más frugal que cumpla los criterios de evaluación (§4).
- No enviar al LLM contexto que no contribuye a la tarea (minimización aplicada al prompt).
- No extraer microservicios ni añadir infraestructura anticipadamente: la escala sigue a la métrica
  real, no a la previsión (criterios en `CLAUDE.md`).

### P3 — Supervisión humana significativa

**Principio.** Ninguna decisión con efectos jurídicos o significativos sobre personas se adopta de
forma completamente automatizada por IA generativa. El sistema define puntos de control humano
obligatorios (*review gates*) cuya superación queda registrada con identidad del revisor.

**Por qué.** RIA art. 14 y RGPD art. 22. La supervisión debe ser *significativa*: el humano debe
poder entender qué revisa (de ahí P5 y P6) y su intervención debe estar instrumentada, no ser un
clic ritual.

**Mecanismos.** Patrón HITL con puertas de revisión (REVIEW_GATE), registro de aprobaciones
(ApprovalRecord) y máquina de estados de bloques (BlockStateMachine) en los grafos LangGraph.

**Obligaciones de desarrollo.**
- Todo flujo que produzca un documento o decisión con destino a un procedimiento administrativo
  incluye al menos una puerta de revisión antes del efecto.
- La aprobación humana se persiste (quién, cuándo, qué versión aprobó) y forma parte de la
  evidencia de auditoría.
- No se implementan mecanismos de aprobación en bloque que vacíen de contenido la revisión.

### P4 — Legalidad por diseño

**Principio.** El sistema solo ofrece al usuario las acciones que la norma le autoriza según su
rol, la fase del procedimiento y el estado del expediente. Esa lógica vive exclusivamente en el
servidor; la interfaz no puede fabricarla ni eludirla.

**Por qué.** Si las reglas de competencia están dispersas en el frontend, la conformidad depende de
cada pantalla. Centralizarlas en una máquina de estados servidora las hace únicas, testeables y
auditables.

**Mecanismos.** Contrato HATEOAS: el DTO de cada expediente incluye `acciones_permitidas`,
calculado en el servidor. El frontend genera los controles iterando ese array (regla maestra en
`CLAUDE.md`).

**Obligaciones de desarrollo.**
- Prohibido en el frontend cualquier condicional de negocio del tipo `if (fase === X) mostrar()`.
- Los tests de backend verifican que un usuario sin permisos recibe un array de acciones vacío.

### P5 — Transparencia estructural (Contract-First)

**Principio.** El backend es la única fuente de verdad de la lógica y de los formularios; el
frontend es reactivo y "tonto". El contrato (OpenAPI, `ui_contract` SDUI) es un artefacto auditable
y registrable que describe exactamente qué hace el sistema.

**Por qué.** RIA art. 13. La transparencia que depende de documentación manual se desactualiza; la
que emana del contrato es estructural: el sistema no puede comportarse de forma distinta a lo que
su contrato declara. Es la base para registros públicos de algoritmos.

**Mecanismos.** Arquitectura Contract-First, Server-Driven UI, tipos y hooks del frontend generados
desde `openapi.json` (Orval), validación cliente derivada del contrato del servidor.

**Obligaciones de desarrollo.**
- Ningún dato de negocio, regla de estado ni estructura de formulario hardcodeada en React.
- Todo cambio de comportamiento visible pasa por un cambio de contrato, versionable y revisable.

### P6 — Trazabilidad y auditabilidad *by construction*

**Principio.** Cada ejecución asistida por IA produce evidencia inmutable y suficiente para su
revisión ex-post: qué entradas se usaron, qué modelo y versión, qué fuentes fundamentan cada
afirmación, qué intervenciones humanas hubo y qué salida se produjo.

**Por qué.** RIA art. 12 (registro de eventos) y Ley 40/2015 art. 41 (auditoría de la actuación
automatizada). Sin trazabilidad no hay rendición de cuentas ni derecho de defensa efectivo del
ciudadano afectado.

**Mecanismos.** RunManifest (manifiesto de ejecución por corrida), citas trazables al fragmento de
origen en el RAG (*source-grounding* obligatorio), validación del contrato de citas que sustituye
una respuesta sin fuentes verificables por una respuesta de indisponibilidad (no se emite una
afirmación que el sistema no pueda fundamentar), TracingService/Langfuse (spans de observabilidad),
AuditLogNode en los grafos.

**Obligaciones de desarrollo.**
- Toda respuesta RAG destinada a usuarios finales incluye citas resolubles a su fragmento fuente;
  una afirmación sin fuente es un defecto, no una característica.
- Los nodos de grafo no producen efectos fuera de los campos tipados del estado
  (`TypedDict`/Pydantic): el estado es el registro.
- Los registros de auditoría son de solo-anexado; no se editan ni borran desde la aplicación.

### P7 — Minimización y anonimización de datos personales

**Principio.** Los datos personales solo se exponen a un LLM cuando es imprescindible, y en ese
caso previa disociación. La anonimización admite modos graduados —desde detección hasta enmascarado
irreversible— y, cuando es reversible, la reversión está auditada y controlada.

**Por qué.** RGPD arts. 5.1.c y 25; LOPDGDD D.A. 7ª. La exposición de datos identificativos a
modelos de terceros es el principal riesgo de privacidad de la IA generativa en el sector público.

**Mecanismos.** `RunAnonymizationContext` con cuatro modos (OFF / detección / sustitución
reversible / enmascarado irreversible) y mapas directo/inverso aplicados en hooks pre/post-LLM.
Regla de frontera: **el edge entrega los datos ya anonimizados a `model_factory`; el factory no
anonimiza** — la responsabilidad está en un único punto, antes de que el dato cruce.

**Obligaciones de desarrollo.**
- Ningún servicio invoca al LLM con datos de expedientes o ciudadanos saltándose el contexto de
  anonimización cuando el caso de uso lo exige.
- Las categorías especiales de datos (art. 9 RGPD) usan enmascarado irreversible, nunca
  sustitución reversible.
- Los mapas de reversión no salen del edge ni se registran en trazas enviadas al cloud.

### P8 — Soberanía de datos: frontera edge-cloud

**Principio.** Los datos del cliente final (conversaciones, documentos, expedientes, chunks,
embeddings) y la lógica operacional que los procesa residen en el **edge** (la nube o
infraestructura del cliente). El **cloud** (admin/partner) solo conserva configuración y métricas
anonimizadas. El cloud orquesta; el edge ejecuta.

**Por qué.** Requisito regulatorio en despliegues Edge+Cloud (localización del dato, post-Schrems
II) y garantía estructural: lo que no sale del perímetro no puede fugarse. La frontera es
arquitectónica, no contractual.

**Mecanismos.** Bases ORM separadas (`HubConfigBase` sincronizable cloud→edge vs
`HubOperationalBase` solo-edge, sin `relationship()` cruzadas), `ConfigProvider` como único acceso
del edge a la configuración, clasificación de routers/módulos regulada en runtime por
`DEPLOY_MODE=cloud|edge|all`, router `edge_sync` como única superficie que ve ambos mundos.

**Obligaciones de desarrollo.**
- Un módulo edge no importa módulos cloud; los grafos, el task runner y `modules/automation/` son
  edge y no leen modelos de configuración directamente.
- Todo router nuevo se etiqueta `Deploy: cloud|edge|shared` en su docstring y se registra en la
  función correspondiente de `main.py`.
- Ante la duda: si toca datos del cliente final → edge; si solo configuración → cloud; si ambos →
  partir la responsabilidad. (Detalle completo en `CLAUDE.md`, "Frontera Edge-Cloud".)

### P9 — Calidad y vigencia de la información que consume la IA

**Principio.** La información pública que alimenta al RAG se audita antes y durante su uso:
detección de obsolescencia, supersesión, duplicidad y contradicción. El contenido patológico se
excluye del corpus consultable, y la exclusión queda registrada.

**Por qué.** RIA art. 10 (gobernanza de datos) y derecho a la buena administración: una respuesta
correcta sobre una norma derogada es un daño, no un acierto. La calidad del corpus es una cuestión
de gobernanza, no solo de higiene técnica.

**Mecanismos.** Motor de auditoría de contenido (detección determinista + semántica de
superseded/duplicate/contradiction) con exclusión de páginas obsoletas del índice RAG; detección de
huecos de contenido a partir de las consultas que el sistema no logra fundamentar (señales de
feedback negativo y de fallo de recuperación), que realimenta la cola de revisión del corpus.

**Obligaciones de desarrollo.**
- La ingesta de fuentes nuevas pasa por el pipeline de auditoría antes de indexarse.
- Los resultados de auditoría (qué se excluyó y por qué) son consultables por el administrador.

### P10 — Portabilidad e independencia de proveedor

**Principio.** El sistema funciona sin cambios de código sobre distintos proveedores de nube,
almacenamiento, base de datos y modelo de IA, cambiando solo configuración. La dependencia de un
proveedor concreto es un riesgo de soberanía y de competencia en la compra pública.

**Mecanismos.** `StorageService` sobre fsspec (file/S3-MinIO/GCS por variable de entorno), DSN de
base de datos solo por `DATABASE_URL`, protocolo `EmbeddingService` con implementaciones
intercambiables, `model_factory` como único punto de selección de LLM, vocación de distribución
como software libre (dual-license AGPLv3/MIT/Apache 2.0).

**Obligaciones de desarrollo.**
- Prohibido el acceso directo al sistema de ficheros para documentos de negocio y el hardcodeo de
  credenciales o endpoints de proveedor (reglas duras en `CLAUDE.md`, "Infraestructura objetivo").

### P11 — Seguridad de la ejecución orquestada por IA

**Principio.** El código que la IA produce o dispara se ejecuta en aislamiento estricto, con
capacidades mínimas, sin acceso a la red salvo lo autorizado, y con re-auditoría del código antes
de ejecutar.

**Mecanismos.** Microservicio sandbox aislado (bloque SBX: runner efímero, re-auditoría AST,
aislamiento de red, gVisor como objetivo). Ver `docs/SANDBOX_SECURITY.md`.

**Obligaciones de desarrollo.**
- Ningún script de usuario ni código generado se ejecuta en el proceso del servidor API.
- Las capacidades del sandbox se amplían por lista blanca explícita, nunca por defecto.

## 4. Evidencia y auditoría de cumplimiento

La conformidad se demuestra con artefactos que el sistema genera por construcción:

| Obligación | Evidencia generada | Mecanismo |
|---|---|---|
| Registro de eventos (RIA art. 12) | Manifiesto por ejecución + spans de observabilidad | RunManifest, TracingService/Langfuse |
| Supervisión humana (RIA art. 14) | Registro de aprobaciones con identidad y versión | ApprovalRecord, REVIEW_GATE |
| Transparencia (RIA art. 13) | Contrato OpenAPI/SDUI versionado | Contract-First, `ui_contract` |
| Gobernanza de datos (RIA art. 10) | Informes de auditoría de corpus y exclusiones | Motor de auditoría de contenido |
| Minimización / seudonimización (RGPD) | Modo de disociación aplicado por ejecución | `RunAnonymizationContext` |
| Localización del dato | Clasificación edge/cloud verificable en runtime | `DEPLOY_MODE`, bases ORM separadas |
| Calidad de la recuperación | Métricas de recuperación sobre dataset dorado, como *gate* de CI | Recall@k y MRR contra baseline versionada |
| Calidad de la salida | Métricas de fidelidad y relevancia (evaluación periódica) + veredicto humano por escenario | RAGAS (faithfulness, answer_relevancy), escenarios de prueba por chatbot |

**Evaluación continua.** La evaluación opera en dos capas complementarias, ninguna de ellas
telemetría opcional. (1) La **calidad de la recuperación** se mide con métricas deterministas
(recall@k, MRR) sobre un dataset dorado de consultas con las fuentes que deberían recuperarse, y
actúa como *gate* de integración continua: ningún cambio del recuperador se adopta si degrada la
recuperación por debajo de la baseline. (2) La **calidad de la salida** (*groundedness* y
relevancia, vía RAGAS) es criterio de aceptación periódico, complementado por escenarios de prueba
con veredicto humano: un caso de uso cuyo *faithfulness* cae por debajo del umbral definido para él
no se despliega o se retira de servicio hasta corregirse.

**FRIA como proceso.** La Evaluación de Impacto en Derechos Fundamentales (RIA art. 27), cuando
aplica, se trata como proceso continuo instrumentado sobre esta evidencia, no como documento
estático redactado una vez.

## 5. Clasificación de riesgo por caso de uso (RIA)

Antes de habilitar un caso de uso nuevo sobre la plataforma se responde este checklist y se
registra la conclusión:

1. **¿Afecta al acceso a servicios públicos esenciales o evalúa/clasifica a personas físicas con
   efectos sobre sus derechos?** → posible **alto riesgo** (Anexo III RIA): exige FRIA, registro,
   y refuerzo de P3 (supervisión) y P6 (trazabilidad) antes de producción.
2. **¿Interactúa con ciudadanos?** → obligaciones de transparencia (art. 50): informar de que se
   interactúa con un sistema de IA; etiquetar contenido generado.
3. **¿Trata datos personales?** → determinar base jurídica, aplicar P7 (modo de disociación
   adecuado) y, si procede, evaluación de impacto RGPD (art. 35).
4. **¿Produce efectos jurídicos automatizados?** → prohibido sin intervención humana significativa
   (P3); verificar encaje con Ley 40/2015 art. 41 (órgano responsable declarado).
5. **¿Puede resolverse de forma determinista?** → aplicar P1 antes de aceptar la solución con LLM.

Los usos previstos de la plataforma (asistencia a la redacción con revisión humana, RAG informativo
con citas, extracción con validación) se sitúan en general en riesgo **limitado**; el checklist
existe precisamente para detectar cuándo un caso concreto cruza a alto riesgo.

## 6. Gobernanza operativa

- **Responsable del sistema**: cada despliegue en una administración declara el órgano responsable
  de la actuación administrativa automatizada (Ley 40/2015 art. 41) y el contacto del DPD.
- **Alta de casos de uso**: requiere el checklist del §5 documentado y la configuración de los
  parámetros de gobernanza (modo de disociación, puertas de revisión, umbrales de evaluación,
  modelo asignado).
- **Cambios**: toda modificación de contrato, prompt de sistema o modelo asignado a un caso de uso
  es versionada y queda asociada a las ejecuciones posteriores vía manifiesto.
- **Incidentes**: una salida incorrecta con efecto sobre un ciudadano se trata como incidente:
  se reconstruye con la evidencia del §4, se corrige la causa (corpus, prompt, contrato, umbral) y
  se documenta.
- **Revisión periódica**: los umbrales de evaluación y la clasificación de riesgo de cada caso de
  uso se revisan al menos una vez al año y ante cambios normativos o de modelo relevantes.

## 7. Documentos relacionados

- `CLAUDE.md` — reglas de arquitectura vinculantes que implementan este marco (Contract-First,
  frontera edge-cloud, portabilidad).
- `docs/EU_GOVERNANCE_CONCEPT_NOTE.md` y `docs/EU_GOVERNANCE_TOPICS.md` — proyección del marco
  hacia consorcios y financiación europea.
- `docs/SANDBOX_SECURITY.md` — detalle del principio P11.
- `docs/REDACCION_CONTRACT_FIRST.md` — aplicación de P4/P5 al módulo de redacción.
- `PROJECT_STATE.md` y planes de fase — estado de implementación de cada mecanismo citado.

> **Nota de vigencia**: los mecanismos citados en §3 y §4 reflejan la arquitectura objetivo del
> proyecto; algunos están implementados y otros planificados en fases posteriores. Este marco es
> normativo para ambos: lo implementado debe conservar estas propiedades y lo nuevo debe nacer
> conforme a ellas.

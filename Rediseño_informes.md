# **Propuesta para incorporar a la planificación TDD**

## **Objetivo del cambio**

Reformular la subfase de **Agentes de Redacción / Workspaces** para que no sea solo un grafo híbrido básico con extracción, redacción IA y ensamblado, sino una arquitectura extensible basada en:

DraftingCoreGraph  
ReportProfiles  
ReportTemplateContracts  
ReportUIContracts  
BlockContracts  
ExtractionPipelineFactory  
DraftingRunManifest  
HITL Block Review  
GenericReportProfile  
LLM-assisted Report Specification

El sistema debe permitir dos modos principales:

1. **Plantillas predefinidas por administrador**, reutilizables por organización o usuario.  
2. **Modelo genérico de informe**, utilizable por cualquier usuario para informes no previstos.

Además, debe permitir crear o adaptar informes de dos formas:

* mediante un **editor de bloques**;  
* mediante un **asistente LLM** que convierta indicaciones en lenguaje natural en una especificación estructurada de informe, siempre con validación, vista previa y aprobación humana antes de crear una plantilla o workspace.

---

# **Decisiones de arquitectura que debe reflejar la planificación**

## **1\. No usar un grafo monolítico de redacción**

La planificación debe adoptar un patrón análogo al de 9B:

DraftingCoreGraph  
  carga workspace  
  valida inputs  
  normaliza documentos  
  ejecuta extracción determinista  
  verifica calidad/completitud de datos  
  genera bloques IA asistidos  
  exige revisión HITL  
  ensambla documento final  
  produce RunManifest

El grafo debe ser común. La variación entre tipos de informes debe resolverse mediante **ReportProfiles**, no mediante condicionales dentro del core.

Perfiles iniciales sugeridos:

GENERIC\_REPORT  
ANNUAL\_REPORT  
DOCTORATE\_PROGRAM\_REPORT  
CONTRACT\_REPORT  
FREEFORM\_MEMO

El perfil `GENERIC_REPORT` es obligatorio y debe permitir construir informes no predefinidos.

---

## **2\. Formalizar contratos de informe**

La planificación actual menciona `hub_agent_templates`, `config_hibrida JSON`, workspaces, documentos subidos y un grafo con `DataExtractorNode`, `AIDrafterNode` y `DocumentAssemblerNode`. Eso debe ampliarse con contratos explícitos: [\[ujies-my.s...epoint.com\]](https://ujies-my.sharepoint.com/personal/fabra_uji_es/Documents/Archivos%20de%20chat%20de%20Microsoft%C2%A0Copilot/Plan_TDD_Fase1.md)

ReportTemplateContract  
InputContract  
BlockContract  
ReportUIContract  
ExtractionContract  
AIBlockPolicy  
ReviewPolicy  
ExportPolicy  
DraftingRunManifest

El campo `config_hibrida JSON` no debe quedar como JSON amorfo. Debe tener estructura versionada, validable y exportada por OpenAPI.

---

## **3\. Crear contratos UI adaptativos**

El frontend no debe tener una pantalla hardcodeada por tipo de informe. Debe existir un `ReportUIContract` que permita renderizar:

wizard de configuración  
dropzones de documentos  
campos manuales  
editor de bloques  
panel de revisión IA  
preview del documento  
estado de validación  
acciones de aprobación/exportación

Esto encaja con el enfoque Contract-First ya previsto: DTO Pydantic → OpenAPI → Orval → tipos generados → formularios con `react-hook-form` \+ `zodResolver`. [\[ujies-my.s...epoint.com\]](https://ujies-my.sharepoint.com/personal/fabra_uji_es/Documents/Archivos%20de%20chat%20de%20Microsoft%C2%A0Copilot/Plan_Contrato_OpenAPI.md)

---

## **4\. El LLM debe generar especificaciones, no ejecutar directamente**

El asistente LLM podrá recibir una indicación como:

“Quiero un informe de seguimiento de un programa formativo con un Excel de indicadores y un PDF de memoria anterior.”

Pero su salida debe ser un **ReportTemplateDraft** estructurado, no código ni ejecución directa.

Flujo deseado:

Lenguaje natural del usuario  
  → LLM propone ReportTemplateDraft  
  → validador estructural  
  → normalizador  
  → vista previa editable  
  → aprobación HITL  
  → creación de workspace o plantilla versionada

Esto mantiene la filosofía HITL que ya aparece en la planificación actual para generación de scripts seguros, donde la IA propone, se audita y el usuario aprueba antes de persistir. [\[ujies-my.s...epoint.com\]](https://ujies-my.sharepoint.com/personal/fabra_uji_es/Documents/Archivos%20de%20chat%20de%20Microsoft%C2%A0Copilot/Plan_TDD_Fase1.md)

---

## **5\. Separar extracción determinista de asistencia IA**

La planificación debe reforzar que la IA no debe ser el mecanismo principal para parsear Excel/PDF.

Pipelines sugeridos:

ExcelExtractionPipeline  
PDFTextExtractionPipeline  
PDFTableExtractionPipeline  
ManualInputPipeline  
AdminScriptExtractionPipeline

Los scripts generados por IA deben ser una capacidad avanzada y controlada, no la vía principal del MVP.

---

## **6\. Introducir HITL por bloque**

Cada bloque debe tener estado:

draft  
missing\_input  
extracted  
ai\_generated  
needs\_review  
approved  
rejected  
locked

Reglas mínimas:

* un bloque IA no aprobado no entra en el documento final;  
* un bloque requerido sin datos bloquea el ensamblado;  
* toda exportación debe registrar versión de plantilla, inputs, outputs y aprobaciones;  
* el usuario debe poder editar/rechazar/regenerar bloques IA.

---

## **7\. Crear `DraftingRunManifest`**

Antes de exportar a DOCX/ODT, el agente de redacción debe producir trazabilidad.

Contenido mínimo:

workspace\_id  
template\_version\_id  
report\_profile  
uploaded\_documents  
input\_contract\_validation  
extracted\_blocks  
ai\_blocks  
model\_used  
prompt\_versions  
citations  
warnings  
user\_approvals  
final\_document\_hash

Esto conectará bien con la exportación avanzada prevista en 1C.4, que ya contempla `RunManifest`, citas, índice, notas a pie y anexo de auditoría. [\[ujies-my.s...epoint.com\]](https://ujies-my.sharepoint.com/personal/fabra_uji_es/Documents/Archivos%20de%20chat%20de%20Microsoft%C2%A0Copilot/Plan_TDD_Fase1.md)

---

# **Secuencia de prompts para modificar la planificación TDD**

A continuación tienes una secuencia de prompts **dirigidos a un agente de programación/planificación**. No piden implementar código, sino **reescribir y detallar la planificación TDD**.

---

## **Prompt P-REDAC-0 — Diagnóstico y ubicación del nuevo bloque**

Actúa como arquitecto de software y responsable de planificación TDD.

Objetivo:  
Analizar el estado actual de la subfase “Agentes de Redacción / Workspaces” en Plan\_TDD\_Fase1.md y proponer su reestructuración antes de implementar código.

Contexto:  
\- La fase 9B de grafos públicos ya define una arquitectura madura basada en CoreGraph, GraphProfiles, RetrievalPipelineFactory, contratos de evidencias y configuración efectiva.  
\- La subfase 9.11a–9.11d de redacción existe, pero es menos detallada y solo cubre modelos base, generación segura de scripts, grafo híbrido y frontend no-code.  
\- Se desea que el sistema de redacción soporte:  
  1\. plantillas predefinidas por administrador;  
  2\. un modelo genérico para cualquier informe;  
  3\. construcción manual por bloques;  
  4\. generación asistida por LLM de especificaciones de informe;  
  5\. extracción determinista desde PDF/Excel;  
  6\. revisión HITL;  
  7\. trazabilidad mediante RunManifest;  
  8\. contratos backend/frontend mediante OpenAPI \+ Orval.

Tareas:  
1\. Identificar dónde insertar un nuevo bloque de planificación, preferentemente antes de 9.11a o sustituyendo 9.11a–9.11d.  
2\. Proponer el nombre del bloque, por ejemplo:  
   “BLOQUE 9R — Redacción Contract-First: ReportProfiles, UI Contracts y DraftingCoreGraph”.  
3\. Definir qué partes de 9.11a–9.11d se conservan, cuáles se reemplazan y cuáles se mueven a prompts posteriores.  
4\. Generar una nota de arquitectura para añadir al plan.

Criterio de aceptación:  
\- El resultado debe ser una propuesta de reorganización del plan, no código.  
\- Debe quedar claro que el nuevo bloque es previo a la implementación.  
---

## **Prompt P-REDAC-1 — Definir arquitectura objetivo de redacción**

Actúa como arquitecto de producto y LangGraph.

Objetivo:  
Redactar la sección de arquitectura objetivo del nuevo bloque 9R de redacción.

Debe incluir:  
1\. DraftingCoreGraph como grafo común.  
2\. ReportProfiles para especializar tipos de informe.  
3\. GENERIC\_REPORT como perfil obligatorio para informes no predefinidos.  
4\. ReportTemplateContract como especificación versionada.  
5\. ReportUIContract para renderizar UI adaptativa.  
6\. BlockContract para modelar bloques estáticos, datos, tablas, gráficos, IA y revisión.  
7\. ExtractionPipelineFactory para Excel, PDF, inputs manuales y scripts seguros.  
8\. DraftingRunManifest para trazabilidad.  
9\. HITL por bloque.  
10\. Integración Contract-First con OpenAPI \+ Orval.

Tareas:  
\- Escribir una sección clara de “Decisiones de diseño”.  
\- Incluir un diagrama textual de alto nivel.  
\- Explicar que el LLM puede asistir en la generación de especificaciones, pero no ejecutar comportamientos no validados.  
\- Explicar que el sistema debe admitir tanto plantillas de administrador como workspaces ad hoc de usuario.

Criterio de aceptación:  
\- La sección debe poder insertarse directamente en Plan\_TDD\_Fase1.md.  
\- No debe incluir implementación de código.  
---

## **Prompt P-REDAC-2 — Redefinir modelos y contratos TDD**

Actúa como experto en FastAPI, Pydantic, OpenAPI y diseño Contract-First.

Objetivo:  
Planificar los contratos de datos del sistema de redacción, sin implementar código.

Define prompts TDD para especificar:  
1\. ReportTemplateContract.  
2\. ReportTemplateVersion.  
3\. ReportProfile.  
4\. InputContract.  
5\. BlockContract.  
6\. ReportUIContract.  
7\. WorkspaceState.  
8\. BlockState.  
9\. DraftingRunManifest.  
10\. ReportTemplateDraft generado por LLM.

Cada contrato debe incluir:  
\- propósito;  
\- campos mínimos;  
\- validaciones esperadas;  
\- relación con OpenAPI;  
\- impacto en frontend mediante Orval;  
\- tests RED esperados.

Incluir criterios de aceptación:  
\- Todos los contratos deben ser serializables.  
\- Deben poder exponerse en OpenAPI.  
\- Deben generar tipos frontend.  
\- No deben requerir interfaces TypeScript manuales.  
\- Deben permitir plantillas globales, de organización, privadas y workspaces ad hoc.

Criterio de aceptación:  
\- El resultado debe ser una planificación TDD detallada de contratos.  
\- No escribir código real.  
---

## **Prompt P-REDAC-3 — Planificar el perfil genérico `GENERIC_REPORT`**

Actúa como arquitecto funcional de productos de redacción asistida.

Objetivo:  
Definir en la planificación TDD el perfil obligatorio GENERIC\_REPORT.

Debe cubrir:  
1\. Para qué sirve.  
2\. Qué estructura inicial propone.  
3\. Qué bloques mínimos incluye.  
4\. Qué inputs acepta.  
5\. Cómo funciona con PDF, Excel y entrada manual.  
6\. Cómo se puede construir manualmente por bloques.  
7\. Cómo se puede generar desde lenguaje natural mediante LLM.  
8\. Qué validaciones mínimas aplica.  
9\. Cómo se revisan y aprueban los bloques IA.  
10\. Cómo produce DraftingRunManifest.

Estructura sugerida del perfil:  
\- título;  
\- objetivo;  
\- contexto;  
\- fuentes aportadas;  
\- datos extraídos;  
\- análisis asistido;  
\- conclusiones;  
\- recomendaciones;  
\- anexos/fuentes.

Tests RED a planificar:  
\- test\_generic\_report\_profile\_exists  
\- test\_generic\_report\_accepts\_manual\_blocks  
\- test\_generic\_report\_accepts\_excel\_and\_pdf\_inputs  
\- test\_generic\_report\_requires\_human\_approval\_for\_ai\_blocks  
\- test\_generic\_report\_generates\_run\_manifest  
\- test\_generic\_report\_can\_be\_created\_from\_llm\_draft

Criterio de aceptación:  
\- El perfil genérico debe permitir informes no previstos sin crear un grafo nuevo.  
---

## **Prompt P-REDAC-4 — Planificar sistema de bloques**

Actúa como experto en modelado de editores no-code.

Objetivo:  
Detallar en la planificación TDD el sistema de bloques de informe.

Tipos de bloque mínimos:  
\- STATIC\_TEXT  
\- USER\_INPUT  
\- DETERMINISTIC\_DATA  
\- TABLE  
\- CHART  
\- AI\_ASSISTED\_TEXT  
\- AI\_SUMMARY  
\- AI\_REWRITE  
\- CITATION\_BLOCK  
\- REVIEW\_GATE

Para cada tipo de bloque, definir:  
1\. Propósito.  
2\. Inputs.  
3\. Outputs.  
4\. Si puede ser requerido.  
5\. Si puede depender de otros bloques.  
6\. Si puede usar IA.  
7\. Si requiere aprobación.  
8\. Cómo se renderiza en UI.  
9\. Cómo se registra en RunManifest.

Planificar tests RED:  
\- test\_block\_contract\_has\_required\_fields  
\- test\_ai\_block\_requires\_review\_policy  
\- test\_data\_block\_requires\_extraction\_source  
\- test\_chart\_block\_depends\_on\_data\_block  
\- test\_review\_gate\_blocks\_final\_assembly\_until\_approved  
\- test\_block\_contract\_is\_serializable

Criterio de aceptación:  
\- La planificación debe dejar claro cómo los bloques sustituyen configuraciones ad hoc.  
\- No implementar componentes ni backend todavía.  
---

## **Prompt P-REDAC-5 — Planificar asistente LLM de especificación de informes**

Actúa como experto en LLM product design y seguridad HITL.

Objetivo:  
Planificar el asistente que convierte lenguaje natural en una especificación estructurada de informe.

Flujo esperado:  
1\. Usuario o administrador describe el informe en lenguaje natural.  
2\. El LLM genera un ReportTemplateDraft.  
3\. El backend valida el draft contra un schema permitido.  
4\. Se normalizan secciones, bloques, inputs y políticas IA.  
5\. Se muestra vista previa editable.  
6\. El usuario aprueba explícitamente.  
7\. Se crea un workspace ad hoc o una plantilla versionada.

Debe quedar claro:  
\- El LLM no ejecuta código.  
\- El LLM no crea plantillas persistentes sin aprobación.  
\- El LLM no puede introducir tipos de bloque no permitidos.  
\- Toda propuesta debe ser validable, editable y auditable.

Planificar tests RED:  
\- test\_llm\_spec\_service\_returns\_report\_template\_draft  
\- test\_invalid\_llm\_draft\_is\_rejected  
\- test\_unknown\_block\_type\_is\_rejected  
\- test\_llm\_draft\_requires\_human\_approval\_before\_persisting  
\- test\_admin\_can\_save\_llm\_draft\_as\_template  
\- test\_user\_can\_use\_llm\_draft\_as\_private\_workspace  
\- test\_llm\_draft\_preview\_contains\_sections\_blocks\_and\_inputs

Criterio de aceptación:  
\- La planificación debe diferenciar modo administrador y modo usuario.  
\- No escribir implementación real del servicio.  
---

## **Prompt P-REDAC-6 — Planificar ExtractionPipelineFactory**

Actúa como arquitecto de pipelines de extracción documental.

Objetivo:  
Definir la planificación TDD de ExtractionPipelineFactory para informes.

Pipelines mínimos:  
\- ExcelExtractionPipeline  
\- PDFTextExtractionPipeline  
\- PDFTableExtractionPipeline  
\- ManualInputPipeline  
\- AdminScriptExtractionPipeline

Debe quedar claro:  
\- La extracción primaria de datos es determinista.  
\- La IA no debe parsear datos tabulares como mecanismo principal.  
\- Los scripts generados por IA son una extensión avanzada y deben pasar seguridad AST, auditoría y aprobación HITL.  
\- Cada pipeline devuelve un ExtractionResult normalizado.

Planificar contratos:  
\- ExtractionInput  
\- ExtractionResult  
\- ExtractedTable  
\- ExtractedMetric  
\- ExtractionWarning  
\- ExtractionProvenance

Planificar tests RED:  
\- test\_factory\_returns\_pipeline\_for\_excel  
\- test\_factory\_returns\_pipeline\_for\_pdf\_text  
\- test\_factory\_returns\_pipeline\_for\_pdf\_table  
\- test\_factory\_rejects\_unknown\_source\_type  
\- test\_excel\_pipeline\_reports\_missing\_required\_columns  
\- test\_pdf\_pipeline\_reports\_non\_extractable\_pdf  
\- test\_extraction\_result\_contains\_provenance

Criterio de aceptación:  
\- Los pipelines deben ser intercambiables.  
\- Los bloques de datos no deben depender de un formato interno no documentado.  
---

## **Prompt P-REDAC-7 — Planificar DraftingCoreGraph ampliado**

Actúa como experto en LangGraph y diseño TDD.

Objetivo:  
Reformular la planificación del grafo de redacción para pasar de tres nodos básicos a un DraftingCoreGraph extensible.

Nodos mínimos:  
1\. LoadTemplateNode  
2\. ValidateInputContractNode  
3\. FileNormalizationNode  
4\. DeterministicExtractionNode  
5\. DataQualityCheckNode  
6\. MissingDataQuestionNode  
7\. AIAssistDraftNode  
8\. CitationAndTraceabilityNode  
9\. UserReviewGateNode  
10\. ApplyUserEditsNode  
11\. FinalAssemblerNode  
12\. AuditLogNode

Debe explicar:  
\- Qué hace cada nodo.  
\- Qué estado lee y escribe.  
\- Qué nodos son deterministas.  
\- Qué nodos pueden usar LLM.  
\- Dónde se detiene el flujo para revisión humana.  
\- Cómo se genera o actualiza DraftingRunManifest.  
\- Cómo se conecta con DocumentAssembler y exportación posterior.

Planificar tests RED:  
\- test\_core\_graph\_compiles\_with\_generic\_report\_profile  
\- test\_core\_graph\_blocks\_when\_required\_input\_missing  
\- test\_core\_graph\_runs\_deterministic\_extraction\_before\_ai  
\- test\_ai\_node\_receives\_only\_validated\_data\_context  
\- test\_review\_gate\_prevents\_unapproved\_ai\_blocks\_in\_final\_document  
\- test\_core\_graph\_generates\_run\_manifest  
\- test\_core\_graph\_supports\_admin\_template\_and\_ad\_hoc\_workspace

Criterio de aceptación:  
\- La planificación debe sustituir o ampliar el actual prompt 9.11c.  
\- No debe implementar LangGraph todavía.  
---

## **Prompt P-REDAC-8 — Planificar UI adaptativa por contrato**

Actúa como experto en React, UX de editores no-code y contract-first frontend.

Objetivo:  
Planificar el frontend del workspace de redacción basado en ReportUIContract.

Componentes/pantallas a planificar:  
\- ReportTemplateBuilderPage  
\- GenericReportWizard  
\- ReportUIContractRenderer  
\- DynamicUploadSlots  
\- DynamicFieldRenderer  
\- BlockEditor  
\- AIBlockReviewPanel  
\- DataQualityPanel  
\- ReportPreviewPanel  
\- WorkspaceStatusBar

Debe contemplar:  
\- modo administrador: crear/editar plantilla reusable;  
\- modo usuario: crear workspace desde plantilla o desde GENERIC\_REPORT;  
\- modo asistido por LLM: vista previa editable del ReportTemplateDraft;  
\- validación de inputs requeridos;  
\- aprobación de bloques IA;  
\- uso de tipos generados por Orval;  
\- no crear interfaces TS manuales.

Planificar tests Vitest RED:  
\- should\_render\_upload\_slots\_from\_ui\_contract  
\- should\_render\_dynamic\_fields\_from\_ui\_contract  
\- should\_block\_continue\_when\_required\_input\_missing  
\- should\_show\_ai\_blocks\_as\_pending\_review  
\- should\_require\_explicit\_approval\_before\_final\_assembly  
\- should\_allow\_admin\_to\_save\_template\_version  
\- should\_allow\_user\_to\_create\_ad\_hoc\_workspace\_from\_generic\_report  
\- should\_render\_llm\_generated\_draft\_preview\_before\_persisting

Criterio de aceptación:  
\- La planificación debe especificar comportamiento UI, no implementar componentes.  
---

## **Prompt P-REDAC-9 — Planificar trazabilidad y RunManifest**

Actúa como experto en auditoría, trazabilidad documental y exportación.

Objetivo:  
Planificar DraftingRunManifest como salida obligatoria de cada ejecución del agente de redacción.

Debe incluir:  
\- workspace\_id;  
\- template\_id;  
\- template\_version\_id;  
\- report\_profile;  
\- input files;  
\- input contract validation result;  
\- extracted data blocks;  
\- AI generated blocks;  
\- model/provider usado;  
\- prompt template versions;  
\- citas/provenance;  
\- warnings;  
\- aprobaciones/rechazos de usuario;  
\- hash o versión del final\_document.

Debe explicar conexión con:  
\- ExportService DOCX/ODT;  
\- notas a pie;  
\- anexo de auditoría;  
\- posible Google Drive;  
\- revisión posterior.

Planificar tests RED:  
\- test\_run\_manifest\_created\_for\_each\_drafting\_run  
\- test\_run\_manifest\_records\_uploaded\_documents  
\- test\_run\_manifest\_records\_extracted\_blocks  
\- test\_run\_manifest\_records\_ai\_blocks\_and\_model  
\- test\_run\_manifest\_records\_user\_approvals  
\- test\_run\_manifest\_is\_available\_to\_export\_service  
\- test\_final\_document\_hash\_is\_recorded

Criterio de aceptación:  
\- El manifiesto debe ser obligatorio  
---

## **Prompt P-REDAC-10 — Planificar vertical slice MVP**

Actúa como product owner técnico.

Objetivo:  
Definir un vertical slice MVP de redacción para validar toda la arquitectura antes de añadir casos especializados.

Vertical slice recomendado:  
\- GENERIC\_REPORT.  
\- Creación desde lenguaje natural.  
\- Vista previa de especificación.  
\- Subida de un Excel simple y un PDF opcional.  
\- Extracción determinista de una tabla Excel.  
\- Generación de un bloque IA de análisis.  
\- Revisión y aprobación del bloque IA.  
\- Ensamblado en Markdown.  
\- RunManifest básico.  
\- Preparación para exportación posterior.

Planificar criterios de aceptación end-to-end:  
1\. El usuario describe el informe.  
2\. El sistema propone secciones, bloques e inputs.  
3\. El usuario aprueba la especificación.  
4\. El usuario sube documentos.  
5\. El sistema valida inputs.  
6\. El sistema extrae datos determinísticamente.  
7\. El sistema genera texto asistido con IA.  
8\. El usuario aprueba o edita el bloque IA.  
9\. El sistema ensambla el documento final.  
10\. El sistema genera RunManifest.

Planificar tests E2E:  
\- test\_user\_can\_create\_generic\_report\_from\_natural\_language  
\- test\_user\_can\_upload\_excel\_and\_pdf\_to\_workspace  
\- test\_required\_inputs\_are\_validated  
\- test\_excel\_data\_is\_extracted\_before\_ai\_drafting  
\- test\_ai\_block\_requires\_review  
\- test\_final\_document\_contains\_only\_approved\_blocks  
\- test\_run\_manifest\_is\_generated

Criterio de aceptación:  
\- Este vertical slice debe ser el primer objetivo de implementación futura.  
\- No planificar todavía casos especializados complejos.  
---

# **Inserción recomendada en el plan**

Yo lo insertaría así:

BLOQUE 9B — Grafo Público Extensible  
...  
9B.14 — Kit de ampliación

NUEVO:  
BLOQUE 9R — Redacción Contract-First: ReportProfiles, UI Contracts y DraftingCoreGraph  
  9R.0 — Diagnóstico y arquitectura objetivo  
  9R.1 — Contratos de plantillas, inputs, bloques y UI  
  9R.2 — Perfil genérico GENERIC\_REPORT  
  9R.3 — Sistema de bloques  
  9R.4 — Asistente LLM de especificación  
  9R.5 — ExtractionPipelineFactory  
  9R.6 — DraftingCoreGraph ampliado  
  9R.7 — UI adaptativa por ReportUIContract  
  9R.8 — HITL y estados de bloque  
  9R.9 — DraftingRunManifest  
  9R.10 — Vertical slice MVP

DESPUÉS:  
9.11a–9.11d revisados o sustituidos por la implementación derivada del bloque 9R

Subfase 1.C:  
  1C.0 — Focus Mode  
  1C.4 — Exportación DOCX/ODT  
  1C.5 — Google Drive  
---

# **Resultado esperado**

Con esta modificación, la planificación pasaría de:

Plantillas \+ workspaces \+ script seguro \+ grafo híbrido básico \+ UI no-code

a:

Sistema contractual de redacción:  
  plantillas versionadas  
  perfil genérico  
  perfiles especializados  
  contratos UI adaptativos  
  bloques tipados  
  especificación asistida por LLM  
  extracción determinista  
  HITL por bloque  
  RunManifest trazable  
  integración OpenAPI/Orval

Esta estructura conserva lo que ya tenías, pero lo ordena y lo eleva al mismo nivel de madurez que el bloque 9B y el plan Contract-First.


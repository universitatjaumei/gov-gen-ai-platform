# Arquitectura de Gov Gen AI Platform

> \*\*Estado objetivo de arquitectura\*\* para la plataforma \*\*Gov Gen AI\*\*: AutomatIA, AI Agents Hub y Gestor de Expedientes.
>
> Este documento consolida la arquitectura funcional y técnica, elimina reiteraciones derivadas de iteraciones previas y mantiene el nivel de detalle necesario para desarrollo, gobierno técnico y comunicación institucional.

\---

## 1\. Alcance y propósito

Este documento describe la **arquitectura funcional y técnica** de la plataforma **Gov Gen AI** en su estado objetivo. La plataforma integra tres módulos principales:

1. **AI Agents Hub**, orientado a chatbots públicos, agentes identificados, RAG, ingesta documental y asistencia avanzada a usuarios.
2. **AutomatIA**, orientado a automatización de procesos internos, flujos, scripts, RPA y procesamiento documental.
3. **Gestor de Expedientes**, orientado a la tramitación administrativa multi-fase, auditable, con supervisión humana y trazabilidad regulatoria.

Su propósito es servir como **fuente única de verdad arquitectónica** para:

* Equipos de desarrollo.
* Órgano de gobierno técnico del proyecto.
* Instituciones públicas usuarias o colaboradoras.
* Partners tecnológicos que desplieguen, mantengan o integren la plataforma.

### 1.1 Qué define este documento

Este documento define:

* Los **principios arquitectónicos transversales**.
* La **arquitectura modular** de la plataforma.
* El modelo de **roles, entidades y responsabilidades**.
* La frontera **Cloud / Edge / Local Runner**.
* El modelo de **privacidad, soberanía del dato y memoria persistente**.
* El stack tecnológico de referencia.
* La integración de AI Agents Hub y Gestor de Expedientes dentro de la plataforma común.
* Las decisiones estratégicas adoptadas y las pendientes.
* El roadmap consolidado de implementación.

### 1.2 Qué no define este documento

Este documento no define:

* Tareas técnicas concretas, prompts TDD ni código de implementación.
* El detalle operativo de despliegue: variables de entorno, scripts de inicialización, configuración de CI/CD o runbooks.
* El estado exacto de implementación de cada módulo en cada commit.
* El detalle exhaustivo de planes TDD por fase.

Esos contenidos deben residir en documentos específicos como:

* `PLAN\_DESARROLLO.md`
* `Plan\_TDD\_Fase1.md`, `Plan\_TDD\_Fase2.md`, `Plan\_TDD\_Fase3.md`
* `ROADMAP.md`
* `PLAN\_OPEN\_CORE\_SERVER.md`
* `PLAN\_LLM\_MULTIPROVEEDOR.md`
* Documentación técnica de cada módulo en el repositorio.

### 1.3 Carácter de las decisiones arquitectónicas

Las decisiones recogidas en las secciones de:

* Principios arquitectónicos transversales.
* Roles y responsabilidades.
* Privacidad y soberanía del dato.
* Frontera Cloud / Edge / Local Runner.
* Integración modular de AutomatIA, AI Agents Hub y Gestor de Expedientes.

se consideran **decisiones arquitectónicas estructurales**. Cualquier cambio que las contradiga debe justificarse en revisión arquitectónica y reflejarse en este documento antes de su ejecución.

El resto del documento es revisable sprint a sprint conforme evolucione la implementación.

\---

## 2\. Resumen ejecutivo

**Gov Gen AI Platform** es una plataforma de inteligencia artificial para instituciones públicas. Combina automatización, asistencia conversacional, generación de documentos, conexión con sistemas corporativos y tramitación administrativa auditable.

La plataforma se organiza en tres módulos:

|Módulo|Propósito principal|Capacidades clave|
|-|-|-|
|**AutomatIA (automatización determinista)**|Automatización de procesos internos|Flujos, ETL, scripts generados, RPA, extracción documental, ejecución local cuando sea necesario|
|**AI Agents Hub**|Atención y asistencia mediante IA|Chatbots públicos, agentes identificados, RAG, Docling, LangGraph, RAGAS, widget web, modo agente|
|**Gestor de Expedientes**|Tramitación administrativa asistida por IA|Tipos de expediente, fases, acciones, HITL, audit, explicabilidad, integración con gestores externos|

El objetivo de AI Agents Hub es doble:

* **Información pública:** chatbots multilingües integrados en webs institucionales para resolver dudas frecuentes de forma masiva.
* **Trabajo asistido:** agentes identificados que ayudan a personal interno, estudiantes o usuarios autorizados a realizar tareas complejas, conectando normativa, documentos propios y datos corporativos.

La plataforma adopta una arquitectura **servidor-first**, con frontend React unificado y un **agente de ejecución local** ligero únicamente para casos en los que sea imprescindible ejecutar acciones en la máquina o red local del usuario.

El modelo de licenciamiento recomendado es **dual-license**:

* **AGPLv3** para instituciones públicas, uso autoalojado y cumplimiento de objetivos de acceso abierto.
* **Licencia comercial** para partners que requieran soporte, SLA, integraciones premium o incorporación en productos privativos.

\---

## 3\. Principios arquitectónicos transversales

Estos principios aplican a todos los módulos de la plataforma.

### 3.1 Determinista-first

La IA genera **propuestas**, pero el acto administrativo o la acción oficial debe ser siempre **determinista, verificable y reproducible**.

La capa de inteligencia —LLM, RAG, razonamiento, generación de scripts o propuestas— puede ser no determinista. La ejecución oficial, sin embargo, debe apoyarse en artefactos controlados:

* Scripts firmados.
* Plantillas validadas.
* Transiciones de estado auditadas.
* Versiones concretas de modelos, prompts y configuración.

Implicaciones de diseño:

* Toda decisión administrativa con efectos hacia terceros debe poder reejecutarse con el mismo input y obtener el mismo resultado.
* Los grafos de orquestación separan con claridad la **propuesta** de la **ejecución**.
* Las acciones automatizadas generadas por IA pasan por validación antes de ejecutarse.
* El registro de auditoría conserva la justificación de la propuesta y el artefacto exacto ejecutado.
* En el Gestor de Expedientes, la resolución administrativa se apoya en acciones trazables, no en una respuesta efímera del modelo.

### 3.2 Human-in-the-Loop como parte estructural

La supervisión humana no es un complemento posterior, sino un elemento estructural de la arquitectura.

Ninguna decisión sustantiva sale al exterior sin un punto explícito de supervisión humana cuando el contexto, la política o el riesgo lo exigen.

Aplicación:

* Los grafos de tramitación incluyen nodos humanos configurables como puntos de parada, revisión o aprobación.
* Los borradores generados por IA pasan por refinamiento iterativo antes de exportarse como documento final.
* Los paneles de supervisión exponen bandejas de aprobaciones pendientes por usuario o rol.
* Las aprobaciones, correcciones y rechazos alimentan el aprendizaje controlado del sistema.
* El sistema sólo aprende de interacciones humanas validadas, no de sus propias salidas sin supervisión.

### 3.3 Ejecución diferenciada Cloud / Edge / Local Runner

La plataforma debe poder desplegarse desde un mismo codebase en distintos modos, según la sensibilidad del dato y las necesidades de la institución.

|Modo|Descripción|
|-|-|
|**Cloud-only**|Toda la lógica corre en la infraestructura del operador o partner. Los datos se anonimizan antes de enviarse a LLM externos cuando la política aplicable lo exija.|
|**Edge + Cloud**|La lógica operacional se ejecuta en un nodo Edge dentro de la nube o infraestructura de la Organización. El Cloud conserva configuración administrativa y métricas anonimizadas.|
|**Servidor + Local Runner**|El servidor orquesta y gobierna. Un agente local sin interfaz ejecuta tareas que requieren acceso a recursos locales del usuario, como carpetas, red interna o automatización RPA local.|

Reglas duras:

* La **capa de inteligencia** puede ejecutarse en Cloud o Edge, pero no en el agente local.
* La **capa de ejecución determinista** puede ejecutarse en Edge o mediante Local Runner.
* El agente local ejecuta únicamente trabajos validados, firmados y asignados desde el servidor.
* Un módulo Edge no debe importar código de un módulo Cloud.
* La frontera se gobierna por configuración y proveedores abstraídos, por ejemplo:

  * `DEPLOY\_MODE=cloud`
  * `DEPLOY\_MODE=edge`
  * `DEPLOY\_MODE=all`
  * `ConfigProvider`
  * `StorageService`
  * `EmbeddingService`

### 3.4 Autoaprendizaje controlado y memoria persistente

La plataforma adopta una filosofía de aprendizaje controlado: el sistema acumula experiencia a partir de interacciones validadas por humanos, pero no aprende silenciosamente de cualquier salida generada.

Principios:

* **Aprendizaje sólo desde validación humana.** Correcciones, aprobaciones y rechazos explícitos son la fuente legítima de aprendizaje.
* **Skill \& Script Library.** El sistema mantiene una biblioteca de procedimientos reutilizables:

  * **Skills:** patrones generalizables de actuación.
  * **Scripts:** artefactos deterministas ejecutables.
* **Memoria de estilo.** Preferencias de redacción, tono y estructura se almacenan separadas de datos identificativos.
* **Learning Trace.** Toda skill o preferencia debe rastrearse hasta la interacción humana que la originó.
* **Opt-in y revocabilidad.** Las capacidades aprendidas pueden revisarse, desactivarse o eliminarse.

La implementación concreta —modelos de datos, extracción de patrones, nodos LangGraph y servicios asociados— corresponde a los planes técnicos de desarrollo.

\---

## 4\. Arquitectura funcional

### 4.1 Modos de uso

La plataforma adapta su interfaz y capacidades al contexto del usuario.

|Característica|Chatbot público|Agente identificado|Gestor de Expedientes|
|-|-|-|-|
|**Acceso**|Anónimo y abierto|Identificado mediante SSO institucional (SAML 2.0)|Identificado y autorizado|
|**Interfaz**|Widget compacto integrado en la web|Interfaz expandida con documentos, dropzone y previsualización|Pantallas de tramitación, bandejas y timeline|
|**Capacidades**|FAQs, normativa, orientación general|RAG, PDFs de usuario, datos corporativos, informes|Fases, acciones, aprobaciones, audit, integración con gestor externo|
|**Idiomas**|Catalán, castellano e inglés|Adaptación dinámica al idioma del usuario|Según configuración institucional|
|**Riesgo**|Bajo o medio|Medio|Medio o alto, según tipo de expediente|
|**Supervisión humana**|Feedback y validación por informadores|Refinamiento iterativo|HITL obligatorio cuando la fase lo exija|

### 4.2 Casos de uso principales

#### Chatbot público

* Responder dudas frecuentes.
* Guiar sobre normativa, plazos, procedimientos o servicios.
* Ofrecer atención multilingüe.
* Recoger feedback de calidad.
* Operar sin acceso a datos personales del usuario salvo configuración explícita.

#### Agente identificado

* Analizar documentación aportada por el usuario.
* Cruzar normativa, evidencias y datos corporativos.
* Generar borradores de informes, memorias o justificaciones.
* Permitir refinamiento humano antes de exportar.
* Conectar con sistemas internos mediante MCP u otros adaptadores.

#### Gestor de Expedientes

* Crear y tramitar expedientes administrativos.
* Ejecutar acciones automáticas y humanas por fases.
* Mantener auditabilidad completa.
* Integrarse con Oracle u otros gestores existentes.
* Generar informes de trazabilidad y cumplimiento.

\---

## 5\. Roles, entidades y responsabilidades

La nomenclatura institucional queda consolidada en cuatro identificadores:

|Identificador|Tipo|Ámbito|Responsabilidad principal|
|-|-|-|-|
|**SuperAdmin**|Rol|Plataforma global|Administra proveedores LLM, modelos, parámetros globales, seguridad, observabilidad, motores base y políticas globales. No gestiona contenido institucional ordinario.|
|**Admin**|Rol|Una o varias Organizaciones|Configura chatbots, agentes, knowledge bases, prompts, plantillas visuales, políticas de privacidad, tipos de expediente e integraciones.|
|**Organización**|Entidad de datos|Institución|Agrupa usuarios, chatbots, knowledge bases, fuentes de ingesta, tipos de expediente, políticas, branding e integraciones.|
|**User**|Rol|Sesión de usuario|Usa chatbots, agentes o expedientes. Puede actuar como aprobador HITL si tiene responsabilidad asignada. No accede a configuración.|

### 5.1 Mapeo de migración terminológica

|Nomenclatura anterior|Nomenclatura actual|Naturaleza|
|-|-|-|
|Admin global|**SuperAdmin**|Rol|
|Partner|**Admin**|Rol|
|Client / Cliente|**Organización**|Entidad de datos|
|End User|**User**|Rol|

### 5.2 Separación de responsabilidades

* El **SuperAdmin** administra la plataforma, no los contenidos de cada Organización.
* El **Admin** configura y mantiene los servicios funcionales de sus Organizaciones.
* La **Organización** es la frontera de datos, políticas, branding e integraciones.
* El **User** consume el servicio y puede validar o aprobar acciones en el bucle HITL.

\---

## 6\. Arquitectura técnica unificada

### 6.1 Visión general

La plataforma se implementa como una arquitectura modular sobre un backend común FastAPI + PostgreSQL, con frontend React unificado y servicios compartidos.

```text
GOV GEN AI PLATFORM
├── Core Services
│   ├── LLM Gateway / Model Factory
│   ├── Dynamic Prompts
│   ├── Auth OIDC/SAML
│   ├── Multi-tenancy
│   ├── MCP Client
│   ├── Audit / Logging
│   ├── Config API
│   └── Job Queue
├── Module: automation/
│   ├── Flows y ETL
│   ├── Processors LLM / Script / RPA
│   ├── Custom Scripts
│   ├── Extracción documental
│   └── Gestión de flujos
├── Module: agents\_hub/
│   ├── RAG híbrido
│   ├── Docling PDF + web
│   ├── LangGraph chatbot / agente
│   ├── Configuración de chatbots
│   ├── RAGAS evaluation
│   └── Widget embed
└── Module: expedientes/
    ├── Tipos de expediente
    ├── Fases y acciones
    ├── HITL
    ├── Audit RIA
    └── Integración con gestores externos
```

### 6.2 Servicios compartidos

|Servicio|Uso transversal|
|-|-|
|**LLM Gateway / Model Factory**|Abstrae proveedores, modelos, versiones y parámetros de inferencia.|
|**Dynamic Prompts**|Centraliza prompts editables desde base de datos y versionables por contexto.|
|**Auth SSO (SAML 2.0) + PAT**|Identidad institucional (SAML 2.0) para humanos y Personal Access Tokens revocables para clientes máquina (p. ej. servidor MCP). OIDC queda como opción futura.|
|**Multi-tenancy**|Aislamiento lógico por Organización, aplicado en el token (claim de Organización) y en un filtro obligatorio por consulta. Ningún acceso a datos de otra Organización sin rol global.|
|**MCP Client**|Conexión segura con sistemas corporativos, como Oracle u otros endpoints.|
|**Audit / Logging**|Trazabilidad de acciones, decisiones, artefactos, prompts, modelos y aprobaciones.|
|**Job Queue**|Ejecución asíncrona de trabajos y coordinación con runners locales.|
|**Config API**|Exposición controlada de configuración a módulos y nodos Edge.|

### 6.3 Capas técnicas

#### A. Capa de inteligencia y orquestación

* **LangGraph** como orquestador de lógica agéntica, flujos conversacionales y expedientes multi-fase.
* **Model Selector** para asignar modelos por instancia, chatbot, agente o proceso.
* **Dynamic Prompts** para prompts editables por Admin o SuperAdmin según ámbito.
* **Bucle de refinamiento humano** mediante nodos de espera y aprobación.

#### B. Capa de datos y conocimiento

* **Docling** para conversión de PDFs y sitios web a Markdown estructurado.
* **Playwright** para lectura de webs dinámicas cuando sea necesario.
* **PostgreSQL + pgvector** para vectores, metadatos y datos relacionales.
* **Búsqueda híbrida** combinando similitud semántica y palabras clave.
* **Caching \& hashing** para evitar reprocesar documentos o páginas no modificadas.

#### C. Conectividad institucional

* **MCP como mecanismo preferente** para consultar datos en tiempo real.
* Adaptadores REST configurables cuando MCP no esté disponible.
* Integraciones por tipo de expediente o chatbot, no necesariamente globales.

#### D. Supervisión humana

* Paneles React segmentados por rol.
* Bandejas de aprobación HITL.
* Validación de respuestas, borradores, resoluciones y acciones.
* Feedback humano como fuente del aprendizaje controlado.

\---

## 7\. Módulo AI Agents Hub

AI Agents Hub se integra como módulo de Gov Gen AI Platform, no como proyecto independiente.

### 7.1 Justificación de la integración

El solapamiento técnico con AutomatIA hace preferible una implementación común:

|Componente|Estado / necesidad|Decisión|
|-|-|-|
|LLM Gateway / Model Factory|Necesario en ambos módulos|Compartido|
|Dynamic Prompts|Necesario en ambos módulos|Compartido|
|Multi-tenancy|Necesario para Organizaciones|Compartido|
|MCP Client|Necesario para datos corporativos|Implementación única|
|Auth SSO SAML 2.0 + PAT|Necesario para agentes identificados y clientes máquina|Implementación única|
|PostgreSQL|Base común de plataforma|Extender schema existente|
|pgvector|Necesario para RAG|Añadir al PostgreSQL común|



### 7.2 Capacidades principales del Hub

* Chatbot público embebible mediante iframe/widget.
* Modo agente expandido para usuarios identificados.
* Ingesta documental con Docling.
* RAG híbrido sobre PostgreSQL + pgvector.
* Ingesta prioritaria de documentos subidos por el usuario.
* LangGraph con modo dual: chatbot / agente.
* Evaluación RAGAS.
* Feedback de usuario.
* Panel Admin para prompts, modelos, knowledge bases, temas y métricas.

### 7.3 Fases específicas del Hub dentro de la plataforma común

Al integrarse en la plataforma, algunas fases originales se eliminan o reducen:

|Fase original Hub|Nuevo estado|Razón|
|-|-|-|
|Docker, uv, PostgreSQL setup|Eliminada|Heredado de plataforma|
|Auth OIDC/SAML|Integrada|Servicio común|
|Schema BD completo|Reducida|Sólo tablas específicas Hub|
|Docling, LangGraph, RAGAS|Mantenida|Núcleo funcional del Hub|
|API endpoints|Reducida|Nuevas rutas en FastAPI existente|
|Tests, CI/CD, observabilidad|Integrada|Framework común|
|React frontend|Mantenida y ampliada|Frontend unificado|
|Autoinstalación|Fusionada|Docker Compose común|

### 7.4 Estrategia de ingesta y calidad del corpus

La calidad del corpus indexado es un requisito de fiabilidad jurídica: en un chatbot de administración pública, una norma con ruido de conversión citada con autoridad es peor que la ausencia de respuesta. Por ello:

* **Ingesta de corpus curado como vía principal.** El contenido normativo se descarga, se convierte a Markdown y se **revisa por un humano fuera de la aplicación** antes de indexarlo. La plataforma importa el corpus curado preservando su procedencia (URL de origen, hash del documento original, idioma, versión del conversor, revisor y fecha, vigencia `valid_from`/`valid_to`). La conversión pesada (Docling) no vive en la ruta de petición.
* **Revisión humana obligatoria para contenido normativo (`regulation`).** Para FAQs o información pública genérica se admite una vía más ligera.
* **El scraper autónomo integrado se reserva a fuentes web estructuradas y homogéneas**, donde la extracción por selectores es fiable; no es la vía general para normativa heterogénea en PDF.
* **Auditoría de calidad continua (post-ingesta):** detección de contenido obsoleto, duplicado o contradictorio, con recuperación consciente de calidad (páginas superseded excluidas). Es complementaria a la revisión previa, no la sustituye.

La procedencia preservada habilita citas trazables y los *snapshots* temporales (`as_of_date`) necesarios para resolver expedientes con la normativa vigente en su momento.

### 7.5 Estrategia de recuperación y evolución agéntica

Decisiones adoptadas el 2026-07-15 a partir de la comparativa arquitectónica con LAMB (`docs/COMPARATIVA_RAG_LAMB.md`); su implementación se planifica en el Bloque RAG de `planificacion/Plan_TDD_Fase1.md`:

* **Búsqueda híbrida real.** Rama vectorial (pgvector con índice HNSW, distancia coseno) + rama léxica (full-text search de PostgreSQL, `tsvector`/GIN con ranking) fusionadas por Reciprocal Rank Fusion, con **reranking cross-encoder** (BGE-reranker-v2-m3, misma familia que el embedding BGE-M3) activable por chatbot. La rama léxica cubre lo que los embeddings pierden en dominio administrativo: siglas, códigos de procedimiento, nombres de convocatorias y artículos de normativa.
* **Representación con contexto.** Los chunks se embeben enriquecidos con el título del documento y su jerarquía de cabeceras (*contextual retrieval*); el chunking *parent-child* (small-to-big: hijo pequeño para buscar, sección padre como evidencia) está disponible por configuración. Cada chunk registra el modelo y la dimensión de embedding con que fue generado, y existe una ruta de re-embedding masivo — cambiar de modelo de embedding es una operación soportada, no una migración ad-hoc.
* **Calidad medible antes que mejoras.** Dataset dorado de consultas por chatbot con métricas puras de recuperación (recall@k, MRR) como gate de CI; ninguna mejora del retriever se adopta sin comparar contra la baseline. RAGAS queda para evaluación periódica de fidelidad y los *test scenarios* por chatbot (ejecución del pipeline real con veredicto humano) complementan la evaluación end-to-end. El feedback negativo y los fallbacks sin cita alimentan la detección de **huecos de corpus** (integrada con la auditoría de calidad de §7.4).
* **La consulta se reescribe antes de buscar.** En conversaciones multivuelta, un modelo pequeño y rápido reformula la consulta con el contexto del historial (con fallback al último mensaje); el retrieval nunca depende solo del último turno.
* **Pipeline gobernado con escalada agéntica, no dicotomía.** El pipeline RAG determinista (barato, trazable, citable) es la vía por defecto para el volumen de consultas informacionales; el modo agéntico (`MD_AGENT_SELECTOR`, herramientas de listado/lectura de documentos) es la **escalada** cuando la evidencia recuperada no supera el quality gate. La recuperación se diseña como **herramienta consumible por agentes**: las inversiones en índice híbrido, reranking y calidad del corpus sirven igual al pipeline actual y a cualquier orquestación agéntica futura, mientras que se evita deliberadamente la sofisticación de pipeline (multi-hop cableado, cadenas de reescritura) que un bucle agéntico sustituye con menos código.

\---

## 8\. Módulo AutomatIA

AutomatIA es el módulo de automatización de procesos internos de la plataforma.

### 8.1 Capacidades principales

* Definición de flujos y procesos.
* Procesadores LLM, scripts, RPA y APIs.
* Extracción documental.
* Generación y ejecución controlada de scripts.
* Triggers sobre recursos locales o servidor.
* Job Queue compartida.
* Ejecución local mediante runner cuando sea necesario.

### 8.2 Migración servidor-first

La lógica de negocio se consolida en el servidor FastAPI. El antiguo cliente NiceGUI **se retiró completo el 2026-09-04** (bloque NIC): `client_app/`, su cuarentena `_legacy_nicegui/` y el entorno Python de la raíz que sólo existía para sostenerlo. El frontend es React, y el mapa de lo que hubo está en [`INVENTARIO_RETIRADA_LEGACY.md`](INVENTARIO_RETIRADA_LEGACY.md).

La migración se realizará módulo a módulo, con cobertura TDD. La lógica más crítica ya situada en servidor —LLM Gateway, estrategias LLM, prompts y configuración— se mantiene y se amplía.

La migración **no es un port en bloque**. Buena parte del valor de generación del AutomatIA original (generación y adaptación de scripts, ETL, gráficos, extracción documental) ya está reimplementado en el servidor o ha quedado superado por los agentes de IA generales; portarlo tal cual aporta poco. El valor duradero que un agente conversacional no reemplaza es la **ejecución determinista, desatendida, firmada y auditable** dentro del perímetro de la institución (triggers, watchers, runner del Edge, gobernanza). La migración es, por tanto, **selectiva y guiada por casos de uso reales**, no exhaustiva.

### 8.3 Modelo de triggers

La definición de cualquier trigger se realiza desde la UI React en el servidor. La ejecución depende del recurso monitorizado:

|Trigger|Ejecutado por|
|-|-|
|Folder watcher sobre carpeta local|Agente de ejecución local|
|Email watcher sobre cliente local|Agente de ejecución local|
|Email watcher sobre servidor IMAP/Exchange|Servidor FastAPI|
|Webhook / HTTP entrante|Servidor FastAPI|
|Cron / scheduled|Servidor FastAPI|

Si un trigger local no dispone de agente instalado o activo, queda en estado **pendiente de runner**, siguiendo un patrón similar a GitLab Runner o GitHub Actions self-hosted runner.

\---

## 9\. Módulo Gestor de Expedientes

El Gestor de Expedientes es el módulo de tramitación administrativa de la plataforma.

Aprovecha:

* LangGraph del Hub.
* Docling y pgvector para documentos.
* Metaprogramación y ejecución determinista de AutomatIA.
* Servicios comunes de identidad, auditoría, configuración y MCP.

### 9.1 Modos de operación

|Modo|Descripción|Caso de uso|
|-|-|-|
|**Integración**|Se conecta vía API/MCP a un gestor existente y añade capa de IA|Coexistencia con Oracle u otros sistemas actuales|
|**Nativo**|Gestiona el expediente directamente en la plataforma|Nuevas tramitaciones o migración progresiva|

### 9.2 Principios de diseño del módulo

* **API-first** para integrarse con gestores existentes.
* **Función y responsable explícitos** en cada tipo, fase y acción.
* **HITL configurable** por fase o acción.
* **Auditabilidad completa** de transiciones, decisiones y artefactos.
* **Determinismo** en las acciones con efectos administrativos.
* **Explicabilidad** de las decisiones asistidas por IA.

### 9.3 Modelo de datos conceptual

Tablas principales en PostgreSQL:

|Tabla|Propósito|
|-|-|
|`tipos\_expediente`|Catálogo de tramitaciones configurables. Incluye fases y acciones.|
|`expedientes`|Instancias concretas de tramitación.|
|`fases\_expediente`|Estado de cada fase para un expediente.|
|`acciones\_fase`|Acciones configuradas dentro de cada fase.|
|`ejecuciones\_accion`|Historial de ejecuciones, resultados, código ejecutado y explicación.|
|`documentos\_expediente`|Documentos vinculados al expediente.|
|`audit\_expediente`|Log inmutable de transiciones y decisiones.|

Campos estructurales obligatorios:

* `funcion`: descripción legible de qué hace una fase o acción.
* `responsable\_rol`: rol responsable de ejecutar o aprobar.
* `responsable\_usuario\_id`: usuario responsable, cuando aplique.
* `estado`: pendiente, en curso, aprobada, rechazada u otros estados definidos.
* `hash\_integridad`: garantía de integridad del registro de auditoría.

### 9.4 Motor de procesos

Cada tipo de expediente se representa como un grafo LangGraph con estado persistido en PostgreSQL.

Esto permite:

* Suspender y reanudar trámites.
* Mantener checkpoints.
* Esperar intervención humana.
* Reintentar acciones automáticas.
* Generar informes de trazabilidad.

Nodos estándar:

|Nodo|Función|Responsable|Reutiliza|
|-|-|-|-|
|`NodoLLM`|Genera propuesta de análisis o resolución|Sistema IA|LLM Gateway|
|`NodoScript`|Ejecuta script determinista|Sistema|AutomatIA|
|`NodoHuman`|Espera aprobación/rechazo humano|Rol configurado|Breakpoints LangGraph|
|`NodoRPA`|Ejecuta navegación o RPA|Sistema / agente local|Playwright + Local Runner|
|`NodoAPIExterna`|Llama a gestor externo|Sistema|MCP Client|
|`NodoNotificacion`|Notifica al siguiente responsable|Sistema|Job Queue|

Estado conceptual:

```python
class ExpedienteState(TypedDict):
    expediente\_id: str
    tipo: str
    fase\_actual: str
    datos: dict
    documentos: list\[str]
    historial\_acciones: list
    pendiente\_humano: bool
    responsable\_actual: str
    explicacion\_ia: str
```

### 9.5 API del módulo

Rutas bajo `/expedientes`:

```http
GET    /expedientes/tipos/
GET    /expedientes/tipos/{tipo\_id}
POST   /expedientes/
GET    /expedientes/
GET    /expedientes/{id}
DELETE /expedientes/{id}
POST   /expedientes/{id}/avanzar
POST   /expedientes/{id}/aprobar
POST   /expedientes/{id}/rechazar
GET    /expedientes/{id}/pendiente
POST   /expedientes/{id}/sincronizar
POST   /expedientes/{id}/publicar
GET    /expedientes/{id}/audit
GET    /expedientes/{id}/informe
GET    /expedientes/pendientes/mios
GET    /expedientes/pendientes/rol/{rol}
```

### 9.6 Integración con gestores externos

Cada tipo de expediente puede configurar su adaptador activo.

```python
class AdaptadorGestorExterno(Protocol):
    async def consultar\_expediente(self, ref\_externa: str) -> dict: ...
    async def crear\_tramitacion(self, tipo: str, datos: dict) -> str: ...
    async def actualizar\_estado(self, ref\_externa: str, estado: dict) -> bool: ...
    async def obtener\_documentos(self, ref\_externa: str) -> list\[bytes]: ...
```

Adaptadores previstos:

|Adaptador|Sistema|Mecanismo|
|-|-|-|
|`AdaptadorOracle`|Oracle institucional|MCP Client|
|`AdaptadorREST`|APIs REST genéricas|HTTP + JSON config|
|`AdaptadorNativo`|Plataforma propia|Directo en PostgreSQL|

### 9.7 Cumplimiento del Reglamento de IA de la UE

|Requisito|Implementación arquitectónica|
|-|-|
|Transparencia|Cada ejecución guarda explicación, inputs relevantes, modelo, prompt y artefacto usado.|
|Supervisión humana|`NodoHuman` configurable en cualquier fase.|
|Determinismo|Separación entre propuesta IA y ejecución validada.|
|Trazabilidad|`audit\_expediente` inmutable y endpoint de informe.|
|Exactitud|Evaluaciones tipo RAGAS aplicables a resoluciones generadas.|
|Gobernanza|Políticas por Organización, tipo de expediente y acción.|

\---

## 10\. Frontend React unificado

El frontend React sustituye a interfaces anteriores y cubre todas las superficies web de la plataforma.

### 10.1 Interfaces incluidas

|Interfaz|Usuarios|Notas|
|-|-|-|
|Widget chatbot público|Ciudadanía, usuarios anónimos|Embebible mediante iframe o script controlado|
|Modo agente expandido|Personal identificado|Dropzone, live preview, refinamiento iterativo|
|Panel Admin Hub|Admins|Prompts, modelos, knowledge bases, RAGAS, temas|
|UI Automation|Usuarios internos|Flujos, extracción PDF, scripts, RPA|
|Panel plataforma|SuperAdmins|LLM configs, tenants, auditoría, seguridad|
|Gestor de Expedientes|Users, responsables y Admins|Lista, detalle, bandejas, configurador|

### 10.2 Sistema de templates visuales

La personalización estética sigue un modelo de herencia en cascada:

```text
Plataforma
└── Organización
    └── Chatbot / Agente / Interfaz específica
```

|Nivel|Configura|Define|
|-|-|-|
|Plataforma|SuperAdmin|Paleta base, fuentes, defaults globales|
|Organización|Admin|Logo, colores corporativos, tipografía institucional|
|Chatbot / agente|Admin|Posición widget, avatar, mensaje inicial, overrides visuales|

Regla de herencia:

* Una instancia sin configuración propia hereda la de la Organización.
* Una Organización sin configuración propia hereda los defaults de plataforma.
* El nivel más específico sobrescribe al más general.

\---

## 11\. Seguridad, privacidad y soberanía del dato

### 11.1 Soberanía y aislamiento

* Los documentos, vectores y metadatos residen en PostgreSQL controlado por la institución o el operador autorizado.
* Los documentos subidos por un usuario para una tarea concreta son temporales y accesibles únicamente por ese usuario y por los procesos autorizados.
* En despliegue Edge + Cloud, los datos operacionales viven en el nodo Edge institucional.
* El Cloud conserva únicamente configuración administrativa y métricas anonimizadas cuando así lo exija el despliegue.

### 11.2 Privacidad selectiva por políticas

La anonimización no se aplica indiscriminadamente. Se gobierna por políticas configurables con prioridad de lo específico sobre lo general.

|Nivel|Política|Comportamiento|
|-|-|-|
|Organización|`default\_privacy\_policy`|Activa o desactiva anonimización por defecto.|
|Tipo de expediente / proceso|`requires\_anonymization`|Fuerza anonimización aunque la Organización no la tenga por defecto.|
|Chatbot / agente|`anonymize\_output`|Controla anonimización en una instancia concreta.|

La política aplicada a cada ejecución queda registrada en auditoría junto a:

* Modelo invocado.
* Prompt y versión.
* Usuario o rol responsable.
* Artefactos ejecutados.
* Decisiones humanas asociadas.

### 11.3 Vault de identidades en Edge

Cuando la privacidad está activa y el despliegue es Edge + Cloud:

* El Vault de identidades reside exclusivamente en el nodo Edge.
* La anonimización se ejecuta antes de llamar a LLMs o APIs externas.
* La rehidratación ocurre sólo en Edge, en el último paso antes de responder al usuario.
* Cloud y proveedores LLM externos no ven datos identificativos reales.

En despliegue Cloud-only, el Vault reside en la misma instancia que la aplicación; las garantías se sostienen por contrato, configuración y controles de seguridad, no por separación física.

### 11.4 Memoria de estilo compatible con privacidad

La memoria de preferencias se construye sobre texto re-anonimizado.

El sistema puede aprender:

* Estilo de redacción.
* Estructura preferida de informes.
* Tono institucional.
* Preferencias de formato.

Pero no debe memorizar nombres reales, identificadores personales o datos sensibles asociados a expedientes.

### 11.5 Gobernanza y feedback

* El feedback público se usa para medir calidad y mejorar RAG.
* El feedback validado por humanos puede alimentar skills o memoria, si la política lo permite.
* Toda mejora aprendida debe ser trazable, revisable y revocable.

\---

## 12\. Modelo de datos unificado

La plataforma utiliza PostgreSQL como base común. El schema existente de AutomatIA se extiende con tablas específicas del Hub y del Gestor de Expedientes.

### 12.1 Núcleo común

|Área|Tablas / conceptos|
|-|-|
|Identidad y tenancy|`users`, `organizations`, roles, permisos|
|Configuración IA|`llm\_configs`, `model\_profiles`, `prompts`|
|Ejecución|`executions`, `jobs`, `audit\_logs`|
|Integraciones|`mcp\_connections`, conectores, credenciales seguras|

### 12.2 AI Agents Hub

|Tabla|Propósito|
|-|-|
|`chatbots`|Instancias públicas o privadas de chatbot/agente|
|`knowledge\_bases`|Bases de conocimiento por Organización o servicio|
|`documents`|Documentos ingeridos|
|`document\_chunks`|Fragmentos vectorizados con metadatos|
|`conversations`|Sesiones conversacionales|
|`messages`|Mensajes de usuario y asistente|
|`feedback\_ratings`|Valoraciones y comentarios|
|`ragas\_evaluations`|Métricas de calidad RAG|

### 12.3 Gestor de Expedientes

|Tabla|Propósito|
|-|-|
|`tipos\_expediente`|Plantillas de tramitación|
|`expedientes`|Expedientes concretos|
|`fases\_expediente`|Estado de fases|
|`acciones\_fase`|Acciones configuradas|
|`ejecuciones\_accion`|Historial de ejecución|
|`documentos\_expediente`|Documentos vinculados|
|`audit\_expediente`|Trazabilidad inmutable|

\---

## 13\. Stack tecnológico de referencia

### 13.1 Backend y orquestación

|Componente|Tecnología|
|-|-|
|Lenguaje|Python 3.11+|
|Gestión de paquetes|`uv`|
|API|FastAPI|
|ORM|SQLAlchemy 2.0 Async|
|Orquestación agéntica|LangGraph|
|Jobs|Job Queue propia de AutomatIA; Celery/Redis sólo si el volumen lo justifica|

### 13.2 Inteligencia artificial y RAG

|Componente|Tecnología|
|-|-|
|LLMs|Proveedores múltiples mediante Model Factory|
|Modelos locales|Soporte mediante selector de modelos cuando aplique|
|Ingesta|Docling|
|Web dinámica|Playwright|
|Embeddings|BGE-M3 u otros modelos libres adecuados para contexto multilingüe y técnico (modelo y dimensión registrados por chunk)|
|Búsqueda vectorial|pgvector con índice HNSW (coseno)|
|Búsqueda léxica|Full-text search de PostgreSQL (`tsvector` + GIN), fusión RRF con la vectorial|
|Reranking|Cross-encoder BGE-reranker-v2-m3, activable por chatbot|
|Evaluación|RAGAS (periódica) + dataset dorado de recuperación (recall@k, MRR) como gate de CI + test scenarios con veredicto humano|

### 13.3 Almacenamiento y conectividad

|Componente|Tecnología|
|-|-|
|Base relacional|PostgreSQL|
|Vectores|pgvector|
|Objetos / ficheros|S3 compatible, MinIO u opción cloud equivalente|
|Integraciones|MCP, REST, conectores específicos|

### 13.4 Frontend

|Componente|Tecnología|
|-|-|
|Framework|React|
|Build tool|Vite|
|Estilos|Tailwind CSS|
|Temas|CSS Custom Properties|
|Internacionalización|i18next|

### 13.5 Infraestructura y DevOps

|Componente|Tecnología|
|-|-|
|Contenedores|Docker, Docker Compose|
|CI/CD|Bitbucket Pipelines|
|Despliegue|Cloud, on-premise o Edge según institución|
|Portabilidad|Servicios abstraídos y configuración por entorno|

### 13.6 Justificación técnica

* **Soberanía:** PostgreSQL, Docker y despliegue on-premise/Edge permiten control institucional.
* **Flexibilidad:** Model Factory evita dependencia de un único proveedor LLM.
* **Calidad:** TDD y evaluación RAGAS reducen errores y alucinaciones.
* **Portabilidad:** S3 compatible, proveedores abstraídos y despliegue por configuración.
* **Mantenibilidad:** Backend común y frontend unificado reducen duplicidades.

\---

## 14\. Licenciamiento y modelo de distribución

La plataforma adopta un modelo **dual-license**:

|AGPLv3|Licencia comercial|
|-|-|
|Instituciones públicas|Partners comerciales|
|Auto-hosted / on-premise|Soporte y SLA|
|Acceso amplio al código|Integraciones premium|
|Contribuciones obligatorias en uso en red|Uso en productos privativos|
|Alineado con objetivos de subvención|Modelo de negocio para partners|

\---

## 15\. Estructura de repositorio recomendada

Se recomienda monorepo mientras el equipo de desarrollo sea común y la coordinación entre módulos sea intensa.

```text
gov-gen-ai/
├── server/
│   ├── app/
│   │   ├── core/
│   │   │   ├── llm/
│   │   │   ├── auth/
│   │   │   ├── tenancy/
│   │   │   ├── mcp/
│   │   │   ├── audit/
│   │   │   └── jobs/
│   │   ├── modules/
│   │   │   ├── automation/
│   │   │   ├── agents\_hub/
│   │   │   └── expedientes/
│   │   └── api/
│   └── migrations/
├── frontend/
│   ├── src/widget/
│   ├── src/agent/
│   ├── src/admin/
│   ├── src/automation/
│   └── src/expedientes/
├── local-runner/
│   ├── runner/
│   └── installers/
├── shared/
│   └── contracts/
└── docs/
```

El monorepo facilita:

* Evolución coordinada de contratos API.
* Refactorización transversal.
* Reutilización de tipos y esquemas.
* CI/CD común.

Repos separados pueden reconsiderarse si el widget público, el runner local o una distribución comercial requieren ciclos de vida independientes.

\---

## 16\. Roadmap consolidado — Hitos funcionales (ajustado)

| Fecha estimada | Hito | Descripción |
|---|---|---|
| **Ene–Jun 2026** | Base plataforma + backend Hub (solo dev / estabilización) | Consolidación de la base común y del backend Hub: RAG/ingesta, LangGraph, endpoints, evaluación y observabilidad/feedback, con foco en estabilidad y deuda técnica mínima (trabajo en solitario). |
| **Jul–Ago 2026** | **Temas v0 (branding mínimo) + preparación piloto** | Entregar **Temas v0** para que el piloto y el repositorio ya sean presentables: **presets + variables CSS + cascada Plataforma→Organización→Chatbot** aplicada a **widget y panel Admin**, sin editor visual aún. En paralelo, cerrar las piezas necesarias para el piloto de chatbots públicos (ingesta/spiders/configuración). |
| **Sep 2026** | **Piloto chatbots públicos + apertura repositorio (AGPLv3)** | Primer piloto de **chatbots públicos** con widget embebible multilingüe y configuración admin operativa, ya con branding mínimo (Temas v0). Apertura del repositorio bajo AGPLv3. Objetivo: **piloto listo antes de octubre**. |
| **Oct–Nov 2026** | **Fase 1.B: Identidad + Temas v1 (editor) + hardening cloud** | Activar autenticación institucional (OIDC/SAML) para modo identificado y completar **Temas v1** con **editor visual** (gestión avanzada), junto con hardening operativo (secretos/CI/CD/observabilidad y preparación de despliegue estable). |
| **Oct–Nov 2026** | **Fase 1.C: Privacidad NER + workspace (base)** | Privacidad selectiva (anonimización reversible NER) aplicada a workspaces e informes (no al chatbot público), Focus Mode/infra UI reutilizable y pipeline base de redacción asistida con trazabilidad. |
| **Antes de dic 2026** | **Agentes de informes (piloto)** | Agentes de redacción end‑to‑end para usuarios identificados: subida de documentos, borrador con citas trazables, exportación maquetada (DOCX/ODT) y destino opcional si aplica. Objetivo: **antes de diciembre**. |
| **Ene–Jun 2027** | **Fase 2 (desarrollo): Automatización + Thin Client** | Desarrollo de Thin Client/Local Runner y sandbox distribuido; migración/fortalecimiento de automatización server-first y servicios transversales hasta estado beta usable. |
| **Jul–Dic 2027** | **Fase 3 (desarrollo): Gestor de Expedientes** | Motor de expedientes (schema/CRUD + LangGraph con checkpointing + HITL), auditoría/explicabilidad y frontend de expedientes, integraciones institucionales (MCP) + capa ENI/ENS hasta pre‑producción (staging). |
| **Ene–Jun 2028** | **Producción (Fases 2 y 3)** | Despliegue en producción de automatización distribuida y expedientes: hardening, seguridad/ENS, monitorización, rendimiento, operación (runbooks) y soporte real. |
| **Jul–Dic 2028** | Escalado y ampliación progresiva | Ajustes post‑producción, ampliación de usuarios/organizaciones/expedientes y activación gradual de funcionalidades diferidas según demanda y métricas. |

### Definiciones rápidas

- **Temas v0 (jul–ago 2026)**: presets + variables CSS (CSS Custom Properties) + cascada Plataforma→Organización→Chatbot aplicada en widget y panel Admin (sin editor).
- **Temas v1 (oct–nov 2026)**: editor visual de temas + gestión avanzada, manteniendo la cascada.

\---

## 17\. Decisiones adoptadas

### 17.1 Arquitectura

* AI Agents Hub y Gestor de Expedientes se integran como módulos de Gov Gen AI Platform.
* La arquitectura es servidor-first.
* React sustituye al cliente NiceGUI como frontend principal. **Hecho**: el NiceGUI se retiró completo el 2026-09-04.
* Se introduce un Local Runner sin UI para ejecución local controlada. **Previsto, sin código**: lo que había se retiró con el NiceGUI porque llevaba tiempo sin compilar. Ver `ESPECIFICACIONES.md` §10.1.
* PostgreSQL es la base común; pgvector se añade para RAG.
* LangGraph se utiliza tanto para agentes como para expedientes.
* El Job Queue existente se reutiliza antes de introducir Celery/Redis.
* La autenticación institucional se implementa con SSO SAML 2.0 + PAT revocables para clientes máquina; OIDC queda como opción futura.
* La ingesta de corpus curado con revisión humana previa es la vía principal para contenido normativo; el scraper autónomo se reserva a fuentes web estructuradas.
* La migración del AutomatIA legacy es selectiva y guiada por casos de uso, no un port en bloque.

### 17.2 Seguridad y privacidad

* La anonimización es selectiva por políticas, no automática en todos los casos.
* El Vault de identidades reside en Edge cuando el despliegue lo exige.
* La memoria de estilo se construye sobre texto re-anonimizado.
* La auditoría registra política aplicada, modelo, prompt, artefactos y aprobación humana.
* El aislamiento multi-tenant se aplica en la capa de token (claim de Organización) y en un filtro obligatorio por consulta; ningún acceso a datos de otra Organización sin rol global.

### 17.3 Producto y distribución

* Se adopta dual-license AGPLv3 + comercial.
* El repositorio público se orienta a instituciones y cumplimiento de acceso abierto.
* La fase comercial se difiere hasta que el producto institucional esté maduro.
* El diseñador visual low-code de expedientes se difiere a v2.

\---

## 18\. Decisiones pendientes

|Decisión|Impacto|
|-|-|
|Nombre definitivo de la plataforma|Marca institucional y comercialización futura|
|Política concreta de publicación AGPLv3|Repositorio público, contribuciones y gestión de forks|
|Catálogo inicial de tipos de expediente|Validación funcional con usuarios reales|
|Profundidad del diseñador low-code|Roadmap v2 del Gestor de Expedientes|
|Alcance de la migración de AutomatIA legacy|Esfuerzo de Fase 2 frente al valor real en el piloto|
|Institución y tipo de expediente piloto de la Fase 3|Compromiso previo antes de invertir en el Gestor de Expedientes|
|Acceso a APIs de UJI / Gestión 400 y specs ENI/ENS|Viabilidad de la Subfase 3.C (dependencia externa)|

\---



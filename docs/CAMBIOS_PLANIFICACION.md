# CAMBIOS PLANIFICACIÓN

Adjunto una para dividir y reestructurar tu plan de desarrollo en tres grandes bloques funcionales.

El objetivo es que **Fase 1** sea un producto mínimo viable (MVP) de información (chatbots) y redacción de informes, la **Fase 2** sea la migración de la automatización de NiceGUI a la nueva infraestructura y la Fase 3 el módulo de expedientes.

Dividir el proyecto en **tres fases** permitirá al agente de programación concentrarse en un dominio de conocimiento específico en cada bloque, reduciendo errores y acelerando el despliegue del MVP. 

Hay que dividir el PLAN\_TDD\_DESARROLLO.md en tarchresivos: Plan\_TDD\_fase1.md y Plan\_TDD\_fase2.md y Plan\_TDD\_fase3.md, con el contenido que se describe a continuación. 

En cada uno de ellos, los prompts que ya han sido ejecutados deben tener una descripción para que el agente de programación tenga contexto pero no deben incluir los prompts atómicos detallados. 

Respecto a los prompts pendientes de ejecutar, deben detallarse los pendientes en el documento Plan\_TDD\_fase\_1.md. Los de la fase 2 y 3 los detallaremos más adelante. 

En la fase 1, haremos dos subfases: chatbots públicos y charbots privados. La prioridad es acabar la primera de las subfases y poder hacer un primer despliegue. 

En cada uno de los documentos se debe indicar el orden más adecuado para la ejecución de los prompts pendientes o, mejor todavía y si es posible, reordenarlos en el orden adecuado que debe seguirse para continuar con el proyecto. No obstante, sugiero una estructura

---

## **. Fase 1: Hub Informativo, Personalización y Redacción (MVP)**

Esta fase se divide en tres sub-entregables claros. El objetivo es que al final de la Subfase 1.A ya tengas un chatbot funcional con datos reales.

### **Subfase 1.A: Chatbots Públicos y Spiders (Prioridad Máxima)**

* **Contenido:** \* **Asistente de Ingestión HITL:** Interfaz para que el **Admin** pegue el `view-source` y la IA proponga los selectores CSS del `config_json`.  
  * **Spider Skills Genéricos:** Implementación de `crawl_depth` y filtros regex para indexar jerarquías web.  
  * **Spiders Especializados (UJI):** Lógica específica para normativa y el catálogo de procedimientos.  
* **Entregable:** Sistema capaz de "mapear" cualquier web institucional y servir un chatbot informativo con citas trazables.

### **Subfase 1.B: Identidad y Despliegue Cloud**

* **Contenido:**  
  * **Sistema de Temas (Fase 10):** Variables CSS, presets (Oscuro, Universidad) y editor visual para que la **Organización** personalice su widget.  
  * **Despliegue Staging (Prompts D.2 a D.4):** Configuración de Google Cloud (Secret Manager, Cloud SQL, y una **VM con Docker Compose** — el destino dejó de ser un servicio gestionado el 2026-08-10, ver `DECISION_EXTRACCION_Y_DESPLIEGUE.md` §2).  
* **Entregable:** Un widget con la marca de la institución accesible desde una URL pública de pruebas.

### **Subfase 1.C: Privacidad y Generación de Informes**

* **Contenido:**  
  * **Privacidad NER (Fase 13):** Migración de la lógica de anonimización reversible para proteger PII en documentos subidos.  
  * **Focus Mode (9.12.a):** Infraestructura de diseño (Zustand \+ Drawer) reutilizable para el editor de informes.  
  * **Agentes de Informes (9.11):** Workspaces para redactar borradores técnicos basados en normativa pública y archivos de usuario.  
* **Entregable:** Herramienta de redacción asistida segura para empleados públicos.

**El promot 9.12.a (Focus Modo) lo avanzaremos a esta fase y modificaremos su contenido. (Versión Infraestructura de Diseño):**

El focus mode debe  actuar como infraestructura de diseño tanto para los informes como, en el futuro, para las automatizaciones. 

"Actúa como experto en React y Zustand. Implementa el sistema de **Focus Mode** y **DrawerHub** como infraestructura transversal en `frontend/src/shared/layout/`.

1. **Estado Global (useFocusStore):** Crea un store con Zustand que gestione:  
   * `viewMode`: 'standard' | 'focus' (colapsa el sidebar principal).  
   * `drawerVisible`: boolean.  
   * `activeTab`: 'config' | 'pills' | 'copilot'.  
   * `context`: objeto que define si estamos editando un **Informe** o un **Flujo**.  
2. **DrawerHub:** Un componente `Sheet` de shadcn/ui que renderice pestañas dinámicas según el contexto.  
   * Si es Informe: Pestañas de 'Bloques', 'Datos' y 'IA'.  
   * Si es Flujo: Pestañas de 'Configuración', 'Data Pills' y 'Copilot'.  
3. **HOC/Layout Wrapper:** Un componente `FocusLayout` que envuelva las páginas de diseño para automatizar el colapso del sidebar y la gestión de márgenes.

**Criterio de Aceptación:** Debes poder navegar desde la lista de informes a un 'Informe específico' y que este se abra automáticamente en modo Focus, activando el Drawer lateral."

Además, la exportación de los informes debe permitir formatos editables para utilizar herramientas colaborativas fuera de la plataforma. 

### **Exportación Maquetada para Google Workspace (HITL)**

**Objetivo:** Asegurar que la salida del sistema sea compatible con el flujo de trabajo humano fuera de la plataforma.

**Instrucciones para el Agente de Programación:**

"Actúa como desarrollador Senior. Mejora el servicio de exportación en `server/app/modules/agents_hub/services/export_service.py`:

1. **Maquetación Profesional:**  
   * Implementa una exportación a `.docx` y `.odt` usando plantillas Jinja2/Docx.  
   * El documento generado debe incluir: Índice automático, referencias a pie de página de las citas recuperadas y un anexo de auditoría con el `RunManifest`.  
2. **Flujo de Trabajo:**  
   * Añade un botón en la UI de informes: 'Enviar a Revisión Externa' que genere el archivo y proporcione un enlace de descarga optimizado para subir a Google Drive/Workspace.

**Criterio de Aceptación:** El documento exportado debe mantener los estilos institucionales definidos en el Sistema de Temas (colores, tipografía) de la Organización."

#### **Descarga en google workspace**

"Actúa como desarrollador Senior. Amplía el `ExportService` para soportar **Destinos del borrador de informe**:

1. **Driver de Google Drive:** Implementa un conector opcional usando la librería `google-api-python-client` que permita subir el archivo `.docx` generado a una carpeta específica del usuario.  
2. **Selector en UI:** En el Workspace de informes, añade un dropdown: 'Descargar local' o 'Guardar en Google Drive institucional'."

---

## **2\. Fase 2: Automatización y thinclient Local (Migración NiceGUI)**

Esta fase es la migración del sistema legacy hacia la nueva arquitectura distribuida.

* **Subfase 2.A: Thin Client:** Creación del agente ligero (proceso sin UI) que se comunica por WebSocket y ejecuta scripts en sandbox.  
* **Subfase 2.B: Migración de UI (Guía 9C.0):** Traslado de las pantallas de **Flujos, Scripts y Extractor PDF** de NiceGUI a React, moviendo la lógica de dominio al servidor.  
* **Subfase 2.C: IA Frugal y Registro:** Implementación del **Script Registry** con índice semántico para reutilizar automatizaciones sin llamadas constantes al LLM.

En esta fase hay que añadir algunos prompts: 

Prompt 1\. Skill de sincronización

"Actúa como experto en automatización local. Implementa la **Skill de Sincronización de Workspace**:

1. **Detección de Carpeta:** Crea una función que identifique automáticamente la ruta local de Google Drive File Stream o OneDrive en Windows/Linux.  
2. **Handler de Ubicación:** Cuando el servidor emita un evento `FILE_GENERATED` vía WebSocket, el Thin Client debe mover el archivo desde la carpeta temporal de descargas a la carpeta sincronizada de la Organización.  
3. **Seguridad:** El script de movimiento debe estar firmado electrónicamente por el servidor para evitar manipulaciones de archivos no autorizadas."

**Prompt 2\. Aclaración de ejecución de los scripts de automatización**

Como regla general los scripts de automatización se ejecutaran en el edge. En el módulo de informes ya se ha previsto esta ejecución de scripts de transformación o gráficos  para permitir entregar informes rápidos y redactados íntegramente en la nube institucional. En esta fase se aplicará a otras automatizaciones como la extracción de información pdf. 

En esta fase se habilitará la capacidad del agente local para recibir y ejecutar esos mismos scripts sobre carpetas locales y para realizar otras tareas de automatización que requieren recursos locales. 

---

## **3\. Fase 3: Gestor de Expedientes e Integración Institucional**

El bloque final que conecta la inteligencia con sistemas de gestión core.

* **Subfase 3.A: Motor de Expedientes:** Grafo LangGraph con persistencia (checkpointing) para trámites administrativos multi-fase.  
* **Subfase 3.B: Malla Agéntica Avanzada:** Nodos **Analista de Normativa** y **Validador de Scripts** para cumplimiento del RIA.  
* **Subfase 3.C: Endpoinds y adaptadores MCP:** Conectores seguros para **UJI** y **Gestión 400**, junto con la capa de interoperabilidad **ENI/ENS**.

En esta fase se deben añadir dos prompts nuevos:

### **Prompt 1: Snapshots Administrativos (Histórico de KB)**

**Objetivo:** Permitir que el sistema recupere información basada en la normativa vigente en una fecha específica, no solo la actual, garantizando la seguridad jurídica en la resolución de expedientes.

**Instrucciones para el Agente de Programación:**

"Actúa como desarrollador de Backend. Implementa el sistema de **Snapshots Administrativos** en `server/app/modules/agents_hub/`:

1. **Modelo de Datos (`models.py`):**  
   * Añade a `HubDocument` los campos `valid_from` (DateTime) y `valid_to` (DateTime, nullable).  
   * Crea una tabla `HubKnowledgeSnapshot` que registre el estado de una base de conocimiento (IDs de documentos y sus versiones) en un momento dado.  
2. **Filtro de Recuperación (`retriever.py`):**  
   * Modifica el `VectorRetrievalStrategy` y el `AgenticRetrievalStrategy` para aceptar un parámetro opcional `as_of_date`.  
   * La búsqueda vectorial debe filtrar los documentos cuyo rango de validez (`valid_from` / `valid_to`) no incluya la fecha solicitada.  
3. **Endpoint de Auditoría:**  
   * Crea `GET /api/v1/hub/knowledge/snapshot/{chatbot_id}?date=YYYY-MM-DD` para previsualizar qué documentos eran 'verdad' en esa fecha.

**Test TDD (Red/Green):** Valida que una consulta con `as_of_date` de hace un año devuelva resultados diferentes (o nulos) si la normativa fue cargada recientemente."

---

### **Prompt 2: Dashboard de Sesgo y Equidad (Fairness Audit)**

**Objetivo:** Implementar métricas de cumplimiento con el Reglamento de IA (RIA) para detectar respuestas disparatadas o sesgadas en procesos de alto riesgo (Expedientes).

**Instrucciones para el Agente de Programación:**

"Actúa como experto en Ciencia de Datos y Ética en IA. Implementa el **Módulo de Equidad** en `server/app/modules/agents_hub/evaluation/`:

1. **Evaluador de Sesgo (`fairness_scorer.py`):**  
   * Extiende las métricas de RAGAS para incluir un `FairnessScore`.  
   * Este evaluador debe analizar las interacciones (`HubInteraction`) agrupándolas por metadatos (ej. colectivo, tipo de trámite) y comparar la tasa de éxito o el tono de la respuesta.  
2. **AuditService Integration:**  
   * Modifica el `AuditService` para que, en expedientes de 'Alto Riesgo', se ejecute automáticamente una validación de sesgo antes de la firma del informe final.  
3. **Frontend (Admin):**  
   * Crea una pantalla en `frontend/src/admin/pages/FairnessDashboard.tsx` que muestre gráficos de dispersión sobre la equidad de las respuestas por Organización.

**Test TDD (Red/Green):** Simula 10 interacciones con sesgo introducido artificialmente y verifica que el `FairnessScore` caiga por debajo del umbral de seguridad del RIA (0.7)."

Aclaración lugar ejecución scripts: SI en la fase 3, en la tramitación de los expedientes, se debe utilizar alguno de los scripts de automatización como skills para el expediente o se generan scripts para la tramitación,  la ejecución se hará en el Edge. La orquestación administrativa llama al script en el Edge para extraer información, transformar documentos o para validar documentos aportados por el ciudadano.

---

## **4\. Instrucciones sugeridas para el "Project Manager" (Generación de Archivos)**

**Instrucciones de Reestructuración Técnica (3 Fases / 3 Archivos):**

"Actúa como Project Manager y Arquitecto de Software. Divide el archivo `planificacion/PLAN_TDD_DETALLADO.md` en tres nuevos archivos: `Plan_TDD_fase_1.md`, `Plan_TDD_fase_2.md` y `Plan_TDD_fase_3.md`.

**1\. Nomenclatura Institucional:**

* Sustituye globalmente: `Admin` (Super) → `SuperAdmin`, `Partner` → `Admin`, `Client` → `Organización`.

**2\. `Plan_TDD_fase_1.md` (Entregable: Hub Informativo & Reports):**

* Ordena los prompts de la siguiente forma:  
  * **Bloque 1 (Chatbots):** Asistente HITL (view-source), Spider Genérico (Crawl Depth) y Spiders Especializados (UJI).  
  * **Bloque 2 (Plataforma):** Sistema de Temas (Fase 10\) y Despliegue Staging Cloud (D.2-D.4).  
  * **Bloque 3 (Informes):** Anonimización NER (Fase 13), Infraestructura de diseño Focus Mode (9.12.a) y Agentes de Informes (9.11).

**3\. `Plan_TDD_fase_2.md` (Entregable: Migración Automation):**

* Incluye la **Guía 9C.0** de separación de lógica NiceGUI/React.  
* Detalla el scaffolding del **Thin Client** (WebSocket \+ Sandbox).  
* Integra la migración de **Flujos, Scripts y PDF Extractor** (basado en Docling-server).  
* Añade el **Script Registry** unificado.

**4\. `Plan_TDD_fase_3.md` (Entregable: Gestión Administrativa):**

* Detalla el **Gestor de Expedientes** (E1 a E4).  
* Añade el **Nodo Analista**, el **Validador RIA** y los conectores o adaptadores **MCP (UJI/G400)**.  
* Finaliza con el despliegue de **Nodos Edge** híbridos.

**Exigencia:** Cada prompt pendiente en la Fase 1 debe estar detallado con metodología TDD (Red/Green) para que sea ejecutable de inmediato."

Además de la migración de los prompts existentes, debes añadir los nuevos prompts que se han mencionado en este documento. 


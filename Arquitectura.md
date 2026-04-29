## 1\. Resumen ejecutivo

El **AI Agents Hub** es una infraestructura de inteligencia artificial. Su objetivo es doble:

1. **Información Pública:** Chatbots (bilingües) integrados en la web para resolver dudas frecuentes de forma masiva.  
2. **Agentes de Trabajo:** Asistentes identificados que ayudan al personal y alumnos a realizar tareas complejas (justificación de proyectos, informes) conectando datos reales corporativos y documentos propios.

El proyecto se distribuirá bajo la licencia **GNU AGPLv3 (o Apache 2.0)**, garantizando que sea software libre y fomentando la colaboración entre instituciones públicas.

Se han evaluado opciones como Dify, pero se opta por desarrollo propio para garantizar la integración con MCP y la experiencia de usuario específica (Modo Agente).

---

## 2\. Arquitectura funcional. Modos de uso

El sistema se adapta al contexto del usuario mediante una interfaz híbrida en React:

| Característica | Modo Chatbot (Público) | Modo Agente (Identificado) |
| :---- | :---- | :---- |
| **Acceso** | Anónimo y abierto. | Identificado mediante protocolos estándar de identidad: OpenID Connect (OIDC) y SAML |
| **Interfaz** | Widget compacto en la esquina de la web. | Interfaz expandida con previsualización de documentos. |
| **Capacidades** | Consultas sobre normativa y FAQs. | Acceso a Oracle (MCP), subida de PDFs y generación de informes. |
| **Idiomas** | Bilingüe: Catalán, Castellano e Inglés. | Adaptación dinámica al idioma del usuario. |

---

## 3\. Roles y Responsabilidades

El sistema distingue tres roles operativos, alineados con la arquitectura de **Gov Gen AI**:

| Rol | Ámbito | Responsabilidades |
| :---- | :---- | :---- |
| **Admin (SuperAdmin)** | Plataforma global | Gestión de proveedores LLM, modelos disponibles, configuración del sistema, usuarios partner, parámetros globales de seguridad y observabilidad. NO crea agentes ni chatbots. |
| **Partner** | Cartera de clientes | Creación y configuración de agentes y chatbots para cada cliente. Gestión de prompts, bases de conocimiento, integraciones MCP, plantillas visuales. Soporte técnico al cliente. |
| **End User** | Sesión de usuario | Uso del chatbot público o del agente identificado. Sin acceso a configuración. |

### Principio de separación de responsabilidades

- El **Admin** administra *la plataforma*, no los contenidos de cada cliente.
- El **Partner** es quien presta el servicio: despliega, configura y mantiene los bots de sus clientes. Un partner puede gestionar múltiples clientes.
- Los clientes (instituciones) son entidades de datos, no roles de acceso directo al backoffice (salvo que se habilite un rol `ClientAdmin` en fases futuras para supervisión de sus propios bots).

---

## 4\. Sistema de Templates Visuales (Cascada)

La personalización estética sigue un modelo de **herencia en cascada**, análogo a CSS: el nivel más específico sobreescribe al más general.

```
Plataforma (defaults globales)
    └── Cliente (brand del cliente: colores, logo, tipografía)
            └── Chatbot/Chat (overrides por instancia: posición widget, idioma por defecto, avatar)
```

| Nivel | Quién lo configura | Qué define |
| :---- | :---- | :---- |
| **Plataforma** | Admin | Paleta base, fuentes del sistema, valores por defecto de todos los parámetros visuales. |
| **Cliente** | Partner | Logo, colores corporativos, tipografía. Se aplica a todos los chatbots de ese cliente. |
| **Chatbot** | Partner | Overrides específicos de esa instancia: color del botón flotante, posición, avatar del bot, mensaje de bienvenida. |

Un chatbot sin configuración visual propia hereda la del cliente; un cliente sin configuración propia hereda los defaults de plataforma.

---

## 5\. Arquitectura Técnica

La solución se basa en un enfoque modular para evitar el *vendor lock-in* (dependencia de un solo proveedor).

### A. Capa de Inteligencia (Orquestación)

* **LangGraph:** Orquestador de lógica agéntica que decide si usar RAG o consultar datos mediante MCP.  
* **Model selector:** Servicio dinámico que permite cambiar el modelo desde la base de datos sin tocar el código. El **Model Selector** actúa a nivel de instancia. Cada chatbot tiene asignado un perfil de modelo específico en la base de datos que define: proveedor, versión del modelo y parámetros de creatividad (temperatura).  
* **Dynamic Prompts:** Todos los prompts residen en la base de datos y son editables por el partner (a nivel de chatbot/cliente) o por el admin (a nivel global).  
* **Bucle de Refinamiento Humano**. El grafo de LangGraph incluirá un nodo de espera de entrada de usuario para validar o corregir el borrador generado antes de la exportación.

### B. Capa de Datos y Conocimiento (RAG)

* **Ingesta (Docling):** Motor avanzado que convierte PDFs y webs (utilizando playwright para leer las webs dinámicas) a Markdown estructurado.  
* **Vector DB (PostgreSQL \+ `pgvector`):** Almacenamiento soberano de vectores y metadatos. Permite búsquedas híbridas (semánticas \+ palabras clave).  
* **Caching & Hashing:** Solo se procesan documentos o pàgines que han cambiado, optimizando costes y tiempo.

### C. Conectividad Institucional

* **MCP (Model Context Protocol):** Puente seguro para consultar datos en tiempo real (expedientes, gestión económica…) sin duplicar datos en la nube.

### D. Capa de supervisión humana

Paneles desarrollados en React, segmentados por rol:

- **Panel Admin:** gestión de proveedores LLM, usuarios partner, configuración global.
- **Panel Partner:** creación y configuración de chatbots/agentes por cliente, gestión de prompts, knowledge bases y plantillas visuales.
- **Panel de Supervisión:** validación de respuestas y feedback por informadores humanos.

---

## 6\. Seguridad, Privacidad y Soberanía

1. **Soberanía del Dato:** Los vectores y documentos residen en una instancia privada de PostgreSQL, no en servidores externos de terceros.  
2. **Aislamiento de Sesión:** Los documentos que sube un usuario para una tarea específica son temporales y solo accesibles por él.  
3. **Gobernanza y supervisión:** Panel de supervisión para que informadores humanos validen y corrijan las respuestas de la IA antes de que se conviertan en "verdad oficial".  
4. **Capa de Feedback usuarios**  para capturar valoraciones (estrellas) en chats públicos, almacenando estos datos para análisis de calidad RAGAS.

---

## 7\. Hoja de Ruta (Roadmap de Implementación)

El proyecto sigue una metodología **TDD (Test-Driven Development)** para asegurar la máxima calidad desde el primer día.

* **Fase 0-2: Infraestructura y Base de Datos:** Despliegue de Docker, PostgreSQL, autenticación SSO y gobernanza de IA (prompts dinámicos, Model Selector).
* **Fase 3-4: Cerebro e Ingesta:** Docling para PDFs y webs, ingesta prioritaria de documentos de usuario, grafo LangGraph con modo dual (chatbot/agente), Model Factory, bucle de refinamiento iterativo.
* **Fase 5-8: API, CI/CD y Observabilidad:** Endpoints REST, exportación de documentos (PDF/DOCX), Bitbucket Pipelines y métricas RAGAS.
* **Fase 9-10: Interfaz y Personalización:** Widget React con modo agente expandido, live preview, feedback de usuario, y sistema de temas visuales con panel de administración del "Cerebro" de la IA.
* **Fase 11: Autoinstalación:** Empaquetado completo (Docker Compose one-click, `.env` autodocumentado, script de inicialización) para distribución entre instituciones.

---

## 8\. Referencia del Stack Tecnológico

La plataforma utiliza un stack que prioriza el **rendimiento asíncrono**, la **velocidad de desarrollo** y la **independencia de proveedores** (no *lock-in*).

### 6.1. Backend y Orquestación (El "Motor")

* **Lenguaje:** Python 3.11+ gestionado con **uv** (el gestor de paquetes más rápido del ecosistema).  
* **Framework API:** **FastAPI**, seleccionado por su soporte nativo de operaciones asíncronas y validación de datos automática.  
* **Orquestador Agéntico:** **LangGraph**, que permite diseñar flujos de decisión complejos y mantener el estado de la conversación.  
* **Gestión de Datos:** **SQLAlchemy 2.0** (Async) para la comunicación con la base de datos relacional.

### 6.2. Inteligencia Artificial y RAG

* **Modelos de Lenguaje (LLM):**  El sistema soporta diversos modelos y proveedores. e incluso modelos locales  mediante el selector de modelos..  
* **Ingesta de Documentos:** **Docling (IBM)** para la conversión de PDFs y sitios web a Markdown estructurado con alta fidelidad.  
* **Embeddings:** **BGE-M3** o otros embeddings libres optimizados para contextos bilingües y técnicos.  
* **Evaluación:** **RAGAS** para la medición objetiva de la calidad de las respuestas (fidelidad y relevancia).

### 6.3. Almacenamiento y Conectividad

* **Base de Datos Vectorial:** **PostgreSQL** con la extensión **`pgvector`**. Es el estándar para combinar datos relacionales y vectores en un solo lugar.  
* **Integración de Datos:** **Model Context Protocol (MCP)** para la conexión segura y en tiempo real con el servidor MCP de la universidad.

### 6.4. Frontend (Interfaz de Usuario)

* **Framework:** **React** con **Vite** para una experiencia de usuario rápida y fluida.  
* **Estilos:** **Tailwind CSS** para un diseño adaptativo y **CSS Custom Properties** para el sistema de temas dinámicos.  
* **Internacionalización:** **i18next**, soportando Catalán, Castellano e Inglés de forma nativa.

### 6.5. Infraestructura y DevOps

* **Contenedores:** **Docker** y **Docker Compose** para asegurar que el entorno de desarrollo sea idéntico al de producción.  
* **Nube:** Almacenamiento compatible nube  AWS/GCP y on  premise con sistemas compatibles con API S3   como MinIO.  
* **CI/CD: Bitbucket Pipelines.** para la automatización de tests y despliegue continuo.

---

### Justificación Técnica del Stack

1. **Soberanía:** El uso de PostgreSQL y Docker permite mover toda la infraestructura a servidores propios de la universidad si fuera necesario.  
2. **Calidad:** La metodología **TDD** (Test-Driven Development) integrada en el stack reduce drásticamente los errores en producción.  
3. **Flexibilidad:** La **Model Factory** garantiza que la universidad no quede atada a los precios o políticas de un solo proveedor de IA.

## Índice de Prompts Atómicos: Guía de Construcción del "AI Chatbots Hub"

Este listado resume las instrucciones clave enviadas al agente de programación para construir la plataforma, divididas por su finalidad estratégica.

### BLOQUE 1: Infraestructura y Base de Conocimiento (RAG)

| ID | Instrucción Breve | Finalidad |
| :---- | :---- | :---- |
| **0.1 \- 0.6** | **Configuración Base (uv \+ Docker)** | Establecer un entorno de desarrollo ultrarrápido y aislado con PostgreSQL y soporte vectorial (`pgvector`). |
| **2.1 \- 2.9** | **Gobernanza de Datos e IA** | Definir el esquema de base de datos para gestionar múltiples chatbots, prompts dinámicos y configuraciones de modelos desde tablas. |
| **3.1 \- 3.8** | **Ingestor Docling & Watcher** | Crear el sistema que vigila cambios en la web/PDFs, los convierte a Markdown limpio y los vectoriza de forma eficiente. |
| **3.9** | **Ingesta Prioritaria de Usuario** | Permitir que el usuario suba sus propios PDFs para que el agente los analice en tiempo real de forma privada. |

### BLOQUE 2: Cerebro, Lógica y Agentes

| ID | Instrucción Breve | Finalidad |
| :---- | :---- | :---- |
| **4.6** | **Grafo de Decisión (LangGraph)** | Implementar el "sistema de pensamiento" con modo dual (público/agente) que decide si responder usando la web, Oracle o documentos del usuario. |
| **4.7 \- 4.8** | **Evaluación RAGAS** | Implementar métricas automáticas para asegurar que la IA no invente datos y que sus respuestas sean siempre relevantes. |
| **4.9** | **Orquestador de Tareas** | Capacitar al agente para realizar "triangulaciones": cruzar normativa (RAG) con datos reales (Oracle) y evidencias (PDF de usuario) para generar entregables. |
| **4.10** | **Model Factory y Prompts Dinámicos** | Selector de modelos dinámico y servicio de prompts desde base de datos; garantiza independencia tecnológica y personalización sin tocar código. |
| **4.11** | **Refinamiento Iterativo (Human-in-the-Loop)** | Bucle de validación donde el usuario revisa y corrige el borrador antes de la exportación final. |

### BLOQUE 3: Interfaz y Experiencia de Usuario (UI/UX)

| ID | Instrucción Breve | Finalidad |
| :---- | :---- | :---- |
| **9.2 \- 9.4** | **Sincronización i18n (Bilingüe)** | Asegurar que el chat detecte y cambie de idioma (CA/ES/EN) automáticamente según la web de la universidad donde esté insertado. |
| **9.11** | **Modo Agente Expandido** | Crear una interfaz de trabajo ancha con zona de "Dropzone" para archivos, diseñada para tareas de redacción técnica. |
| **9.12** | **Live Preview (Previsualización)** | Implementar un panel lateral donde el usuario ve, en tiempo real, cómo el agente redacta el informe o memoria técnica. |
| **9.13** | **Feedback y Edición de Borradores** | Valoración por estrellas en chat público y botón "Solicitar Cambios" en modo agente para el refinamiento iterativo. |
| **10.1 \- 10.11** | **Sistema de Temas y Panel de IA** | Personalizar colores y estilos por chatbot; panel de administración para editar prompts y cambiar el modelo en caliente. |

### BLOQUE 4: Integración, Exportación y Feedback

| ID | Instrucción Breve | Finalidad |
| :---- | :---- | :---- |
| **4.4 \- 5.4** | **Conectividad MCP y Exportación** | Conectar el agente con Oracle para obtener datos vivos y permitir descargar el resultado final en PDF/DOCX oficial. |
| **8.3** | **Servicio de Feedback Humano** | Crear el canal para que los informadores humanos puntúen y corrijan respuestas, mejorando el sistema continuamente. |

### BLOQUE 5: Distribución y Autoinstalación

| ID | Instrucción Breve | Finalidad |
| :---- | :---- | :---- |
| **11.1** | **Configuración Autodocumentada (.env)** | Generar un `.env.example` con comentarios didácticos para que cualquier institución adapte el sistema en minutos. |
| **11.2** | **Docker Compose "One-Click"** | Levantar todo el stack (Backend, Frontend, BD, MinIO, Ollama) con un solo comando, sin depender de servicios de pago. |
| **11.3** | **Script de Inicialización** | Automatizar migraciones, creación de SuperAdmin y carga de chatbot de ejemplo para una primera instalación sin fricciones. |

---

# Módulo AI Agents Hub — Integración en Gov Gen AI Platform

*Fecha: 2026-03-30 | Versión: 2.0 — Arquitectura servidor-first; agente de ejecución local; NiceGUI deprecado*

---

## 1. Decisión Estratégica

**AI Agents Hub no se desarrollará como proyecto independiente.** Se integrará como un módulo del servidor de Gov Gen AI / AutomatIA, compartiendo infraestructura, base de datos y servicios comunes.

### Justificación

El solapamiento técnico entre ambos proyectos es demasiado significativo para justificar una duplicación:

| Componente | AutomatIA Server | AI Agents Hub | Decisión |
|---|---|---|---|
| LLM Gateway / Model Factory | Implementado (P0 BYOK) | §4.10 Model Factory | **Compartido** |
| Dynamic Prompts desde BD | Implementado | §4.10 Dynamic Prompts | **Compartido** |
| Multi-tenancy | Implementado | Necesario | **Compartido** |
| MCP Client (Oracle/universidad) | Sprint 9 Q3 2026 | §4.4 MCP | **Implementación única** |
| Auth OIDC/SAML | Q4 Enterprise | Fase 1 del Hub | **Implementación única** |
| Base de datos PostgreSQL | Existente | PostgreSQL + pgvector | **Extender schema existente** |

La plataforma unificada tiene mayor valor de propuesta para las instituciones: **AutomatIA automatiza procesos internos; el Hub informa y atiende usuarios**. Son dos caras del mismo sistema de IA institucional.

---

## 2. Modelo de Licenciamiento: Dual-License

Se adopta el modelo **dual-license**, usado por MongoDB, Grafana, GitLab y Odoo.

```
┌─────────────────────────────────────────────────────────────────┐
│                    DUAL-LICENSE MODEL                           │
├──────────────────────────────┬──────────────────────────────────┤
│        AGPLv3 (libre)        │     Licencia Comercial           │
├──────────────────────────────┼──────────────────────────────────┤
│ Instituciones públicas       │ Partners comerciales             │
│ Auto-hosted / on-premise     │ Soporte y SLA garantizados       │
│ Sin soporte                  │ Integraciones premium            │
│ Contribuciones obligatorias  │ Uso en productos privativos      │
│ Cumple requisito subvención  │ Modelo de negocio para partners  │
└──────────────────────────────┴──────────────────────────────────┘
```

### Cumplimiento de la subvención

El requisito de "acceso amplio y abierto a resultados" queda satisfecho de forma óptima:
- La licencia AGPLv3 garantiza que cualquier institución pública puede usar, modificar y redistribuir el software.
- Las modificaciones de instituciones que lo usen en red deben publicarse (copyleft fuerte).
- Los partners comerciales que quieran integrarlo en productos privativos contratan la licencia comercial.

### Implicación para el repositorio cliente de AutomatIA

El cliente NiceGUI (open source Apache 2.0) **no se ve afectado**. El cambio de licencia afecta al servidor, que pasa de "propietario" a "dual-license AGPLv3 + comercial". Esto es más restrictivo para los partners pero más abierto para la comunidad, y está alineado con los objetivos del Hub.

---

## 3. Arquitectura Unificada

> **Actualización marzo 2026 — Arquitectura servidor-first**: El cliente NiceGUI queda reemplazado por el frontend React como interfaz principal para todos los usuarios. Para casos que requieren ejecución local (scripts generados, RPA), se introduce un **agente de ejecución local** ligero (sin UI), siguiendo el patrón GitLab Runner / GitHub Actions self-hosted.

```
┌────────────────────────────────────────────────────────────────────┐
│               GOV GEN AI PLATFORM (servidor universidad)           │
│          FastAPI + PostgreSQL (dual-license AGPLv3 / Comercial)    │
├────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                   CORE SERVICES (ya existe)                 │    │
│  │                                                             │    │
│  │  LLM Gateway        |  Model Factory   |  Dynamic Prompts  │    │
│  │  Auth OIDC/SAML     |  Multi-tenancy   |  MCP Client       │    │
│  │  Audit / Logging    |  Config API      |  Job Queue        │    │
│  └───────────────────────┬─────────────────────────────────────┘   │
│                          │                                         │
│          ┌───────────────┴────────────────┐                        │
│          │                                │                        │
│  ┌───────▼──────────────┐   ┌─────────────▼────────────────────┐   │
│  │ MODULE: AUTOMATION   │   │     MODULE: AGENTS HUB           │   │
│  │ (migrado a servidor) │   │     (nuevo)                      │   │
│  │                      │   │                                  │   │
│  │ · Flows y ETL        │   │  · pgvector + RAG híbrido        │   │
│  │ · Processors (LLM,   │   │  · LangGraph (modo chatbot /     │   │
│  │   Script, RPA...)    │   │    modo agente)                  │   │
│  │ · Custom Scripts     │   │  · Docling (PDF + web)           │   │
│  │ · Extracción docs    │   │  · Configuración de chatbots     │   │
│  │ · Gestión de flujos  │   │  · RAGAS evaluation              │   │
│  │ · Job Queue          │   │  · Widget embed (iframe)         │   │
│  └──────────┬───────────┘   └──────────────┬───────────────────┘   │
└─────────────┼──────────────────────────────┼────────────────────────┘
              │                              │
     ┌────────▼──────────────────────────────▼────────────────┐
     │              Frontend React + Vite (MIT)               │
     │                                                        │
     │  · Widget chatbot público (iframe embed)               │
     │  · Interfaz modo agente (Dropzone, live preview)       │
     │  · Panel admin Hub (prompts, modelos, RAGAS)           │
     │  · UI Automation (flujos, extracción, scripts)         │
     │  · Panel admin plataforma                              │
     └────────────────────────────────────────────────────────┘
              │
     ┌────────▼──────────────────────────────────────────┐
     │    AGENTE DE EJECUCIÓN LOCAL (proceso ligero)     │
     │    Sin UI — solo donde se necesite                │
     │                                                   │
     │  · Recibe jobs del servidor (websocket/polling)   │
     │  · Ejecuta scripts Python generados localmente    │
     │    (acceso a ficheros locales, red interna)       │
     │  · Ejecuta RPA (Playwright) cuando necesario      │
     │  · Reporta resultados al servidor                 │
     │                                                   │
     │  Patrón: GitLab Runner / GitHub Actions runner    │
     └───────────────────────────────────────────────────┘
```

### Base de datos unificada

PostgreSQL con el schema existente extendido:

```
Schema actual (AutomatIA)          Nuevas tablas (Hub)
─────────────────────────          ───────────────────
clients                            chatbots
partners                           knowledge_bases
users                              documents
llm_configs           ──────────►  document_chunks + vector (pgvector)
prompts                            conversations
executions                         messages
...                                feedback_ratings
                                   ragas_evaluations
```

---

## 4. Impacto en el Roadmap

### AutomatIA: cambios necesarios

El roadmap existente **no cambia en su orden de prioridades**. El BYOK (P0) sigue siendo el primer hito, ya que es la base que habilita ambos módulos. Los cambios son addictivos:

#### Sprint nuevo tras Open Core (Q2 2026, ~Sprint 4):

**"Infraestructura Hub" — preparar la plataforma para el módulo**

| Tarea | Esfuerzo | Notas |
|---|---|---|
| Añadir extensión `pgvector` al PostgreSQL existente | 0.5 días | Alembic migration |
| Diseñar y crear tablas Hub en schema compartido | 2 días | chatbots, knowledge_bases, documents, chunks |
| Servicio `EmbeddingService` compartido (BGE-M3) | 2 días | Reutilizable en AutomatIA para extracción semántica futura |
| Actualizar `docker-compose.yml` con dependencias Hub | 0.5 días | Ollama si no está, MinIO si aplica |

**Duración estimada: 1 semana**

#### Sprint nuevo en Q3 2026 (paralelo al MCP):

**"Módulo Agents Hub" — implementar el cerebro del Hub**

| Tarea | Esfuerzo | Equivale a fase Hub |
|---|---|---|
| Ingestor Docling (PDF + web con Playwright) | 1 semana | Fases 3.1-3.8 |
| Ingesta prioritaria de usuario (PDFs temporales) | 2 días | Fase 3.9 |
| Grafo LangGraph dual (chatbot / agente) | 1.5 semanas | Fases 4.6, 4.9, 4.11 |
| RAGAS evaluation service | 3 días | Fases 4.7-4.8 |
| API endpoints Hub (/chat, /admin-hub, /feedback) | 1 semana | Fases 5.1-5.4 |
| Panel admin Hub (configuración chatbots, prompts) | 1 semana | Parte de Fase 10 |

**Duración estimada: 5-6 semanas**

El **MCP client** (ya planificado en Sprint 9 Q3 AutomatIA) se implementa una sola vez y sirve a ambos módulos.

---

### AI Agents Hub: fases que se eliminan o reducen

| Fase original Hub | Nuevo estado | Razón |
|---|---|---|
| **Fase 0** — Docker, uv, PostgreSQL setup | **Eliminada** | Heredado de AutomatIA |
| **Fase 1** — Autenticación OIDC/SAML | **Eliminada** | Heredado (Q4 enterprise AutomatIA) |
| **Fase 2** — Schema BD (chatbots, prompts, modelos) | **Reducida** | Solo tablas específicas Hub; auth/tenancy/LLM ya existen |
| **Fase 3-4** — Docling, LangGraph, RAGAS | **Mantenida** | Nuevo módulo en AutomatIA server |
| **Fase 5** — API endpoints | **Reducida** | Nuevas rutas en FastAPI existente |
| **Fases 6-8** — Tests E2E, CI/CD, observabilidad | **Integrada** | Usar CI/CD y testing framework de AutomatIA |
| **Fase 9-10** — React frontend | **Mantenida íntegra** | Proyecto frontend separado |
| **Fase 11** — Autoinstalación Docker Compose | **Fusionada** | El `docker-compose.yml` de AutomatIA se extiende |
| **Fase 11.3** — Script inicialización | **Integrado** | El script de AutomatIA incluye datos de ejemplo Hub |

**Ahorro estimado: 35-40% del esfuerzo total** al no duplicar infraestructura, auth, CI/CD ni base de datos.

---

## 5. Frontend React: desarrollo independiente y unificado

El frontend React se desarrolla como **proyecto independiente** (`automatia-hub-frontend`) y cubre **todas** las interfaces web de la plataforma, incluyendo la UI del módulo Automation (que reemplaza el cliente NiceGUI).

| Interfaz | Usuarios | Notas |
|---|---|---|
| Widget chatbot público (iframe embed) | Ciudadanos, usuarios anónimos | Build autónomo, licencia MIT |
| Interfaz modo agente expandido | Personal identificado (OIDC/SAML) | Live preview, Dropzone |
| Panel admin Hub | Admins institucionales | Prompts, modelos, RAGAS, temas |
| **UI Automation** (flujos, extracción PDF, scripts, RPA) | Usuarios internos | Reemplaza cliente NiceGUI |
| Panel admin plataforma | Admins internos | LLM configs, tenancy, auditoría |

**El cliente NiceGUI queda completamente deprecado** al completar este frontend. La decisión es limpia: un solo frontend web (React) para todas las interfaces, y un agente de ejecución local ligero (sin UI) para los casos que requieren ejecución en la máquina del usuario.

**Nota sobre la migración del cliente NiceGUI**: La lógica de negocio del módulo Automation (incluyendo el procesador de extracción PDF) se migrará al servidor FastAPI módulo a módulo con asistencia de agentes de programación (Claude Code) y cobertura TDD. La parte más valiosa (estrategias LLM, gateway, prompts) ya está en el servidor. Lo que se migra es la orquestación y la lectura de PDF (lectura server-side tras subida del fichero).

Las fases 9-10 del plan TDD original del Hub se ejecutan tal cual, ampliadas con las pantallas de Automation.

---

## 6. Estructura de Repositorio Recomendada

Se recomienda **monorepo** con separación clara de módulos, dado que el equipo de desarrollo es el mismo:

```
gov-gen-ai/  (o automatia/)
├── server/                    # Backend FastAPI (dual-license AGPLv3/Comercial)
│   ├── app/
│   │   ├── modules/
│   │   │   ├── automation/    # Módulo existente (flows, processors, RPA)
│   │   │   └── agents_hub/    # Módulo nuevo (RAG, LangGraph, chatbots)
│   │   ├── core/              # Servicios compartidos (LLM, auth, tenancy, MCP)
│   │   └── api/               # Routers FastAPI
│   └── migrations/
├── client_app/                # Frontend NiceGUI (Apache 2.0)
├── frontend-hub/              # Frontend React (MIT)
│   ├── src/widget/            # Widget embed público
│   └── src/admin/             # Panel administración Hub
└── shared/                    # Tipos y contratos compartidos (si aplica)
```

---

## 7. Hitos Actualizados

| Fecha | Hito | Descripción |
|---|---|---|
| **Abril 2026** | Infraestructura Hub | pgvector, schema Hub, EmbeddingService operativos |
| **Mayo-Junio 2026** | Módulo Hub backend | Docling, LangGraph, API endpoints Hub |
| **Junio 2026** | Auth OIDC/SAML | SSO institucional activo |
| **Julio-Agosto 2026** | Frontend React | Widget embed + UI Automation + panel admin (reemplaza NiceGUI) |
| **Agosto-Septiembre 2026** | Automation servidor-first + Agente local | Extracción PDF y flujos en servidor; agente ejecución local |
| **Agosto 2026** | Paper enviado | Cumplimiento difusión subvención |
| **Septiembre 2026** | Repositorio público | Plataforma bajo AGPLv3 en GitHub |
| **Octubre 2026** | Piloto institucional | Plataforma completa (Hub + Automation) en producción universitaria |
| **TBD** | Fase comercial | BYOK, Open Core, partners — cuando el producto universitario esté maduro |

---

## 8. Decisiones Adoptadas y Pendientes

### Decisiones adoptadas (marzo 2026)

1. **Arquitectura servidor-first**: Todos los módulos en el servidor. NiceGUI reemplazado por React + agente de ejecución local ligero.
2. **Auth OIDC/SAML**: Adelantado a Q2 2026 (antes era Q4). Necesario tanto para Hub como para la interfaz web de Automation.
3. **Anonimización PII**: Diferida. No necesaria en contexto universitario con los contratos LLM actuales. Se re-habilita para fase comercial en sectores como sanidad o finanzas.
4. **BYOK**: Diferido a fase comercial. La base técnica del LLM Gateway ya está operativa para un único tenant institucional.
5. **pgvector**: Se introduce en el sprint de Infraestructura Hub (no esperar a necesitarlo en Automation).
6. **Migración NiceGUI → React + agente local**: Se realiza módulo a módulo con Claude Code, cobertura TDD. El procesador de extracción PDF es el más complejo; la lógica LLM ya está en servidor.
7. **Modelo de ejecución de triggers**: La *definición* de cualquier trigger (folder watcher, email watcher, webhook, cron) se realiza siempre desde la UI React en el servidor. La *ejecución* del trigger depende de dónde reside el recurso monitorizado:

   | Trigger | Ejecutado por |
   |---|---|
   | Folder watcher (carpeta local del PC) | Agente de ejecución local |
   | Email watcher sobre cliente local (Outlook, carpeta local) | Agente de ejecución local |
   | Email watcher sobre servidor IMAP/Exchange | Servidor FastAPI |
   | Webhook / HTTP entrante | Servidor FastAPI |
   | Cron / scheduled | Servidor FastAPI |

   Para que los triggers locales funcionen, el usuario debe tener el agente instalado y activo en su máquina. Sin agente local, los triggers configurados sobre recursos locales quedan en estado *pendiente de runner* (patrón GitLab Runner). Esto es un trade-off conocido y aceptado de la arquitectura servidor-first.

### Decisiones pendientes

1. **Nombre de la plataforma unificada**: ¿"Gov Gen AI Platform", "AutomatIA Platform" u otro? Afecta identidad de marca para instituciones y eventual comercialización.

2. **Estructura de repositorios**: Confirmar monorepo vs. repos separados. El monorepo facilita el desarrollo coordinado; repos separados facilitan la distribución diferenciada del frontend Hub.

---

## 9. Módulo: Gestor de Expedientes

*Añadido: 2026-03-31 | Evolución de la plataforma hacia gestión de tramitaciones administrativas*

El Gestor de Expedientes es el tercer módulo de la plataforma. Aprovecha la infraestructura del Hub (LangGraph, Docling, pgvector) y el patrón de metaprogramación de Automation para orquestar tramitaciones administrativas multi-fase, auditables y conformes con el Reglamento de IA de la UE.

```
GOV GEN AI PLATFORM
├── Core Services (LLM Gateway, Auth, Multi-tenancy, MCP)
├── Module: automation/      ← flujos, scripts, RPA
├── Module: agents_hub/      ← chatbots RAG, Docling, LangGraph conversacional
└── Module: expedientes/     ← tramitaciones, human-in-the-loop, audit RIA
```

---

### 9.1 Principios de diseño

**API-first con gestores existentes**: El módulo puede actuar en dos modos no excluyentes:

| Modo | Descripción | Caso de uso |
|---|---|---|
| **Integración** | Se conecta vía API/MCP al gestor existente (ej. Oracle) y añade capa de IA | Coexistencia con sistemas actuales sin reemplazarlos |
| **Nativo** | Gestiona el expediente directamente en la plataforma | Tramitaciones nuevas sin sistema previo, o migración progresiva |

**Función y responsable explícitos**: Cada fase y cada acción del expediente declara:
- `función`: qué hace (descripción legible + tipo de acción)
- `responsable`: rol o usuario que debe ejecutarla o aprobarla

Esto garantiza trazabilidad y es la base del cumplimiento del RIA (artículo 13 — transparencia).

---

### 9.2 Modelo de datos

Tablas nuevas en el schema PostgreSQL compartido:

```
tipos_expediente          → catálogo de tramitaciones (plantillas configurables)
  id, nombre, descripción, versión, configuración JSON (fases + acciones)

expedientes               → instancias de tramitación
  id, tipo_id, estado, tenant_id, creado_por, fecha_inicio, metadata JSON

fases_expediente          → estado de cada fase para un expediente concreto
  id, expediente_id, nombre, estado [pendiente|en_curso|aprobada|rechazada],
  orden, función (descripción), responsable_rol, responsable_usuario_id

acciones_fase             → acciones configuradas en cada fase (definición)
  id, fase_id, tipo [llm|script|human|rpa|api_externa], función (descripción),
  responsable_rol, configuración JSON

ejecuciones_accion        → historial de ejecuciones de cada acción
  id, accion_id, expediente_id, timestamp, actor_id, resultado, codigo_ejecutado,
  explicacion (por qué), estado [ok|error|pendiente_humano]

documentos_expediente     → documentos vinculados (FK a chunks Hub si es PDF)
  id, expediente_id, nombre, tipo, doc_chunk_id (nullable), ruta, metadata

audit_expediente          → log inmutable de transiciones y decisiones
  id, expediente_id, fase_id, accion_id (nullable), timestamp, actor,
  acción_descripción, estado_anterior, estado_nuevo, hash_integridad
```

---

### 9.3 Motor de procesos: LangGraph con checkpointing

Cada tipo de expediente se representa como un grafo LangGraph con estado persistido en PostgreSQL (checkpointing nativo). Esto permite suspender y reanudar el expediente en cualquier punto.

**Nodos estándar reutilizables:**

| Nodo | Función | Responsable | Reutiliza |
|---|---|---|---|
| `NodoLLM` | Genera propuesta de resolución o análisis | Sistema (IA) | LLM Gateway existente |
| `NodoScript` | Ejecuta script Python determinista generado por IA | Sistema | Metaprogramación de Automation |
| `NodoHuman` | Punto de parada — espera aprobación/rechazo humano | Rol configurado | Breakpoint LangGraph |
| `NodoRPA` | Ejecuta Playwright (navegación web, certificado digital) | Sistema (agente local) | Agente de ejecución local |
| `NodoAPIExterna` | Llama a API de gestor externo (Oracle u otro) | Sistema | MCP Client |
| `NodoNotificacion` | Envía notificación al responsable de la siguiente fase | Sistema | Job Queue |

**Estado del expediente (`ExpedienteState`):**

```python
class ExpedienteState(TypedDict):
    expediente_id: str
    tipo: str
    fase_actual: str
    datos: dict                  # datos acumulados del expediente
    documentos: list[str]        # IDs de documentos vinculados
    historial_acciones: list     # ejecuciones completadas
    pendiente_humano: bool       # True si hay breakpoint activo
    responsable_actual: str      # rol o usuario responsable
    explicacion_ia: str          # justificación de la última decisión IA
```

---

### 9.4 API del módulo

Nuevas rutas en el FastAPI existente bajo `/expedientes`:

```
# Catálogo de tipos
GET    /expedientes/tipos/                     → lista tipos disponibles con descripción de fases y responsables
GET    /expedientes/tipos/{tipo_id}            → detalle: fases, acciones, función y responsable de cada una

# Gestión de expedientes
POST   /expedientes/                           → crear expediente (tipo, datos iniciales, documentos)
GET    /expedientes/                           → listado con filtros (estado, tipo, responsable, fecha)
GET    /expedientes/{id}                       → estado completo + historial de fases
DELETE /expedientes/{id}                       → anular (solo si está en estado inicial)

# Tramitación
POST   /expedientes/{id}/avanzar              → ejecutar siguiente acción automática
POST   /expedientes/{id}/aprobar              → resolución humana positiva (NodoHuman)
POST   /expedientes/{id}/rechazar             → resolución humana negativa + motivo
GET    /expedientes/{id}/pendiente            → acción pendiente actual (función + responsable)

# Integración con gestores externos
POST   /expedientes/{id}/sincronizar          → pull del estado desde gestor externo (Oracle/otro)
POST   /expedientes/{id}/publicar             → push de la resolución al gestor externo

# Audit y trazabilidad
GET    /expedientes/{id}/audit                → log completo (inmutable)
GET    /expedientes/{id}/informe              → informe de trazabilidad (para RIA)

# Bandeja de trabajo
GET    /expedientes/pendientes/mios           → expedientes pendientes del usuario autenticado
GET    /expedientes/pendientes/rol/{rol}      → expedientes pendientes por rol
```

---

### 9.5 Integración con gestores externos

El módulo se conecta a sistemas externos mediante el **MCP Client** (implementado en Sprint 9 Q3 AutomatIA). Cada integración define un adaptador:

```python
class AdaptadorGestorExterno(Protocol):
    async def consultar_expediente(self, ref_externa: str) -> dict: ...
    async def crear_tramitacion(self, tipo: str, datos: dict) -> str: ...
    async def actualizar_estado(self, ref_externa: str, estado: dict) -> bool: ...
    async def obtener_documentos(self, ref_externa: str) -> list[bytes]: ...
```

**Adaptadores planificados:**

| Adaptador | Sistema | Mecanismo | Sprint |
|---|---|---|---|
| `AdaptadorOracle` | Oracle (universidad) | MCP Client | Sprint 9 Q3 |
| `AdaptadorREST` | Cualquier API REST genérica | HTTP + configuración JSON | Sprint E2 |
| `AdaptadorNativo` | Sin gestor externo | Directo en plataforma | Sprint E1 |

El adaptador activo se configura por tipo de expediente, no globalmente, lo que permite que algunos tipos de tramitación sean nativos y otros se sincronicen con Oracle.

---

### 9.6 Cumplimiento del Reglamento de IA de la UE (RIA)

| Requisito RIA | Implementación |
|---|---|
| **Transparencia** (Art. 13) | Cada `ejecuciones_accion` guarda `explicacion_ia`: el "por qué" de la decisión y el código exacto ejecutado |
| **Supervisión humana** (Art. 14) | `NodoHuman` configurable en cualquier fase; el expediente no avanza sin aprobación explícita |
| **Determinismo** | `NodoScript` separa la "lógica IA" (generación) de la "ejecución" (script determinista); el acto administrativo es reproducible |
| **Trazabilidad** | `audit_expediente` es inmutable; endpoint `/informe` genera PDF de trazabilidad completa |
| **Exactitud** (Art. 15) | RAGAS-style evaluation aplicable a las resoluciones LLM generadas |

---

### 9.7 Frontend React — Pantallas del Gestor

Integradas en el proyecto `frontend-hub` (fases 9-10 del plan TDD):

| Pantalla | Usuarios | Prioridad |
|---|---|---|
| Lista de expedientes (filtros por estado, tipo, responsable) | Todos los usuarios | Sprint E4 |
| Detalle de expediente: timeline de fases, documentos, audit | Todos los usuarios | Sprint E4 |
| Bandeja de aprobaciones (Human-in-the-loop pendiente) | Responsables funcionales | Sprint E4 |
| Configurador de tipos (editor JSON/formulario de fases y responsables) | Admins | Sprint E4 |
| Diseñador visual low-code (drag & drop nodos) | Admins | **Diferido a v2** |

El diseñador visual se difiere hasta tener feedback de usuarios reales sobre qué necesitan configurar. La primera versión configura tipos de expediente mediante formulario estructurado.

---

### 9.8 Plan de sprints

| Sprint | Contenido | Duración | Prerequisito |
|---|---|---|---|
| **E1** | Schema BD, CRUD expedientes, API base, AdaptadorNativo | 1 semana | Hub infrastructure (pgvector) |
| **E2** | Motor LangGraph con checkpointing, nodos estándar, AdaptadorREST | 2 semanas | LangGraph Hub operativo |
| **E3** | AuditService, ExplicabilidadService, endpoint `/informe`, tests RIA | 1 semana | Sprint E2 |
| **E4** | Frontend React: lista, detalle, bandeja, configurador | 3 semanas | Auth OIDC/SAML, Sprint E2 |
| **E5** | AdaptadorOracle vía MCP Client, sincronización bidireccional | 1 semana | MCP Client (Sprint 9 AutomatIA) |

**Calendario:**

| Fecha | Hito |
|---|---|
| **Julio 2026** | Sprint E1 + E2: motor de procesos operativo |
| **Agosto 2026** | Sprint E3: Audit & RIA. Paper enviado. |
| **Septiembre-Octubre 2026** | Sprint E4: Frontend expedientes |
| **Octubre-Noviembre 2026** | Sprint E5: Oracle MCP. Piloto institucional. |

---

### 9.9 Decisiones técnicas adoptadas

1. **Sin Celery/Redis**: Se reutiliza el Job Queue existente de AutomatIA para acciones asíncronas. Se evalúa Celery solo si el volumen en producción lo justifica.
2. **Checkpointing en PostgreSQL**: El estado del grafo LangGraph se persiste en la misma BD que el resto de la plataforma, sin infraestructura adicional.
3. **Modo coexistencia con Oracle**: El gestor no reemplaza Oracle en fase inicial — actúa como capa de IA sobre él. Reduce fricción de adopción institucional.
4. **Diseñador visual diferido**: Primera versión con formulario estructurado. El low-code visual llega tras validación con usuarios.
5. **Función y responsable obligatorios**: Todo tipo, fase y acción debe declarar `función` (descripción legible) y `responsable_rol`. Sin ellos, el tipo de expediente no se puede activar.

---

## 10. Documentos Relacionados

| Documento | Descripción |
|---|---|
| `ROADMAP.md` | Roadmap de AutomatIA (actualizar con sprints Hub y Expedientes) |
| `PLAN_OPEN_CORE_SERVER.md` | Estrategia licenciamiento (revisar para dual-license) |
| `PLAN_LLM_MULTIPROVEEDOR.md` | Diseño técnico BYOK (base compartida con Hub) |
| `ARCHITECTURE.md` | Arquitectura técnica AutomatIA |
| `AI_agents_hub/Arquitectura.md` | Arquitectura original Hub (referencia) |
| `AI_agents_hub/PLAN_TDD_DETALLADO.md` | Plan TDD Hub (usar como guía para fases 3-4 y 9-10) |
| `gestor de expedientes.md` | Resumen ejecutivo del módulo Gestor de Expedientes |

---

*Este documento formaliza la decisión de integrar AI Agents Hub y el Gestor de Expedientes como módulos de Gov Gen AI Platform bajo un modelo dual-license AGPLv3 / Comercial.*



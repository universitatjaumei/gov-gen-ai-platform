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


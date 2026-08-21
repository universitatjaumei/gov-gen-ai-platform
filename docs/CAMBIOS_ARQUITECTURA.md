# CAMBIOS ARQUITECTURA

Quiero hacer cambios en la arquitectura con estas finalidades. Añado sugerencia de las posibles tareas e instrucciones pero analiza las propuestas centrándote en los objetivos, en el código ya migrado o desarrollado, en el código pendiente de mirar o desarrollar que se contiene en el documento Planificacion\_TDD\_detallada.md y hazme la propuesta que consideres más adecuada para introducir los cambios. 

### Bloque 1\. Filosofía Hermes Agent

Me gustaría integrar la filosofía de **Hermes Agent** (aprendizaje autónomo, memoria persistente y creación de habilidades) en la planificación de **Gov Gen AI.**  Para ello, deberíamos realizar una **propuesta de modificación estructural** sobre los bloques de lógica y automatización.

A continuación, detallo una propuesta de modificación para la valores y ejecutes los cambios necesarios en código, modelos de datos y planificación de desarrollo pendiente. 

### **1\. Propuesta de Modificación de la Planificación**

La integración no requiere fases nuevas, sino "vitaminar" las existentes para pasar de un sistema reactivo a uno evolutivo:

#### **A. Evolución del Script Registry a "Skill Library" (Fase 15\)**

En lugar de ser solo un almacén de scripts, se convierte en una biblioteca donde el agente "descubre" cómo resolver problemas. Cada vez que el **Human-in-the-loop (HITL)** valida un borrador complejo, el sistema debe ofrecer la opción de "Aprender este proceso como Skill".

#### **B. Implementación del "Bucle de Aprendizaje" en LangGraph (Fase 4 y 16\)**

Se añade un nodo de **Reflexión Post-Tarea**. Tras la validación humana, este nodo analiza qué pasos fueron exitosos y genera un "resumen procedimental" que se guarda en la memoria del agente.

#### **C. Memoria de Preferencias (Fase 2 y 13\)**

Extender la base de datos para que el anonimizador y el generador de respuestas no solo sigan el prompt del sistema, sino un "perfil de estilo" que aprenda de las correcciones del usuario (Zero-Knowledge).

---

### **2\. Tareas a realizar**

### Hay que actualizar el PLAN\_TDD\_DETALLADO.md, código y modelos de bases de datos:

#### **3.1: Actualización de la Arquitectura de Memoria (Fase 2\)**

"Actúa como arquitecto de software. Modifica el esquema de base de datos en server/app/modules/agents\_hub/database/models.py para incluir una tabla user\_preferences\_vector. Esta tabla debe almacenar embeddings de las correcciones que los usuarios realizan en el modo HITL. El objetivo es que el retriever pueda consultar estas preferencias antes de generar una respuesta, siguiendo la filosofía de memoria persistente de Hermes Agent."

#### **3.2: Creación del Nodo de Aprendizaje (Fase 16\)**

"Implementa en server/app/modules/automation/factories/ un nuevo nodo de LangGraph llamado SkillExtractorNode. Este nodo debe activarse después de que un usuario apruebe una tarea en el NodoHuman. Su función es:

1. Analizar el RunManifest exitoso.  
2. Generar un resumen de la lógica aplicada (pasos, herramientas y prompts).  
3. Guardarlo en el Script Registry (Fase 15\) etiquetado semánticamente como una 'Skill' disponible para futuros agentes."

#### **3.3: Refactor de la Lógica de Decisión (Fase 4B)**

"Modifica el QueryClassifier en server/app/modules/agents\_hub/agent/query\_classifier.py. En lugar de buscar solo en los system\_prompts de los chatbots, debe realizar una búsqueda híbrida en la 'Skill Library'. Si encuentra una 'Skill' (procedimiento previo exitoso) con un score de similitud \> 0.85, el agente debe proponer usar ese procedimiento en lugar de razonar desde cero."

---

### **3\. Prompts previstos que se deben modificar**

Para alinear el proyecto con esta visión, debes retocar los siguientes prompts de tu documento PLAN\_TDD\_DETALLADO.md:

| Prompt Original | Sentido de la modificación |
| :---- | :---- |
| **Prompt 4.11 (Refinamiento Iterativo)** | No solo debe servir para corregir el borrador actual, sino para **disparar el evento de aprendizaje**. Al final del proceso, el sistema debe preguntar: "¿Quieres que aprenda este flujo para futuras tramitaciones similares?". |
| **Prompt 4.10 (Model Factory)** | EL model factory debe ser coherente con el sistema de selección de modelos por prompts que existía en la aplicación NiceGUI que permitía asignar modelos por Tier y asignar Tier por defecto a tareas pero reescribir el modelo a utilizar en el panel de gestión de prompts. También se preveía el autoescalado en supuestos de autohealing. . |
| **Prompt 15 (Script Registry)** | Cambiar el nombre a **Skill & Script Registry**. Se debe añadir un campo is\_learned\_skill (bool) y usage\_context (vector) para permitir que el agente use estas piezas de forma autónoma basándose en la experiencia previa. |
| **Prompt E3 (AuditService)** | La auditoría ahora debe incluir el **"Learning Trace"**. Si una respuesta se basa en una "Skill" aprendida anteriormente, el informe de trazabilidad RIA debe indicar en qué interacción humana previa se aprendió ese procedimiento. |

### 

### **Propuesta Directa de Mejora (Atajo)**

Como alternativa o de forma adicional podría añadirse una **Fase 23: Ecosistema Hermes (Aprendizaje Autónomo)** al final de tu roadmap. Esta fase consistiría en un servicio que recorre periódicamente las ejecuciones\_accion (Fase 12\) que tengan valoración de 5 estrellas y genere automáticamente los registros de la Script Registry con sus correspondientes embeddings de intención.

**1\. Creación del Microservicio (`discovery-service`):**

* Crea un nuevo servicio independiente en `services/discovery/` basado en la arquitectura de **Hermes Agent**.  
* Configura un **Dockerfile** específico que incluya las librerías de `hermes-agent` y las dependencias de navegación web (*Playwright/Chromium*).  
* Implementa un endpoint `POST /analyze-structure` que acepte una URL y un objetivo de información (ej. "normativa académica").

### Bloque 2\. Cambio de Jerarquías y roles 

Quiero cambiar la nomenclatura y jerarquía de roles para un contexto administrativo. El Admin se llamará superadmin. El partner se llamará admin. Los clientes se llamarán organizaciones. Revisa los cambios necesarios en el código existente, prompts pendientes para nuevo desarrollo o migración de NiceGUI legacy, modelo de datos etc. Respecto al modelo de datos adjunto una propuesta pero ajústala a lo que consideres necesario. 

Tarea 2.1. "Actúa como desarrollador Senior de Backend. Realiza una refactorización de los modelos de datos en `server/app/modules/agents_hub/database/models.py` y las migraciones de Alembic para actualizar la jerarquía de roles y entidades según el nuevo modelo institucional:

1. **Renombrar Entidades:** Cambia `Partner` por `Admin` y `Client` por `Organizacion` en todos los modelos, relaciones y nombres de tablas.  
2. **Actualizar Roles de Usuario:** En el modelo de `User`, actualiza los roles disponibles a: `SuperAdmin` (gestión global), `Admin` (gestión de Organización) y `User` (usuario final).  
3. **Relación Organizacional:** Asegúrate de que un `Admin` pueda estar vinculado a una o varias `Organizaciones` para permitir la gestión multi-departamental o multi-ayuntamiento desde un nodo Edge.  
4. **Impacto en Routers:** Actualiza las dependencias de seguridad en `server/app/auth/dependencies.py` para reflejar estos nombres (e.g., `require_superadmin`, `require_admin`).

**Criterio de Aceptación:** Las pruebas de integración en `server/tests/` deben pasar tras ejecutar la migración, y no deben quedar referencias a los términos 'Partner' o 'Client' en la lógica de base de datos."

### Bloque 3\. Delimitación de tareas y seguridad (Cloud vs. Local)

Hay supuestos como los informes previstos en el prompt 9.11, en los que el script se genera y ejecuta en cloud. Sin embargo, en otros casos (automatizaciones que requieren acceso a carpetas y recursos locales) se ejecutará en local. Me gustaría que quedara claro en criterio de la delimitación y qué tareas se efectúan en cada sitio cuado se utilice el runner. 

Tarea 3.1.  Habrá que refactorizar o aclarar  la lógica de ejecución de scripts y automatización para implementar la delimitación estricta entre el **Servidor (Cloud/Edge)** y el **Agente Local (Thin Client)**:

1. **Capa de Inteligencia (Servidor):** La generación de scripts mediante LLM y la **Auditoría de Seguridad (ScriptSecurityAuditor)** en `server/app/modules/agents_hub/services/` deben ser exclusivamente *server-side*. El servidor debe firmar criptográficamente los scripts validados antes de enviarlos.  
2. **Capa de Ejecución (Agente Local):** Modifica el `Runner` en `client_app/local_agent/runner.py` para que sea el encargado de la ejecución física de los scripts deterministas de la Fase 9.11c, permitiendo el acceso a ficheros locales y recursos de red interna del usuario.  
3. **Sandbox Distribuido:** Implementa la lógica de la **Fase 14**: el Servidor realiza el análisis estático (AST) y la validación de seguridad, mientras que el Agente Local realiza la ejecución aislada en un entorno restringido.  
4. **Orquestación:** Asegúrate de que el nodo `DataExtractorNode` de LangGraph en el servidor despache el trabajo al Agente Local mediante el protocolo WebSocket ya definido.

**Criterio de Aceptación:** El servidor no debe ejecutar código generado por IA directamente; debe delegar la ejecución al agente local tras la auditoría."

### Bloque 4\.  Anonimización selectiva

El sistema de **anonimización selectiva y determinista** bajo la arquitectura **Cloud/Edge** debe ser selectiva y basada en políticas institucionales. No debe aplicarse por defecto pero debe garantizar que el **Vault** de identidades no salga de la institución cuando así se establezca. Por tanto, habría que transformar la **Fase 13** en un sistema de privacidad basado en políticas institucionales.

---

### **Tarea 4.1: Esquema de Políticas de Privacidad y Configuración**

**Objetivo:** Permitir que la anonimización sea una elección estratégica por organización o tipo de tarea, no un proceso ciego. Se debe poder aplicar a expedientes y a informes.

**Instrucciones para el Agente de Programación:**

"Actúa como desarrollador de Backend. Modifica los modelos de SQLAlchemy en `server/app/modules/agents_hub/database/models.py` para soportar **Privacidad Selectiva**:

1. **Tabla Organizacion:** Añade el campo `default_privacy_policy` (booleano) para activar la anonimización por defecto en toda la institución.  
2. **Tabla TipoExpediente:** Añade `requires_anonymization` (booleano). Si es `True`, ignorará el valor de la organización y forzará la privacidad (ideal para expedientes sancionadores o expedientes o informes sensibles).  
3. **Tabla HubChatbot:** Añade un toggle `anonymize_output` para controlar si el chatbot debe procesar datos anonimizados.  
4. **Migración:** Genera el script de Alembic para actualizar el esquema."

### **Tarea 4.2: Migración de Lógica de Privacidad NER y Despliegue Distribuido**

"Actúa como desarrollador Senior de Backend y experto en Seguridad. El objetivo es migrar la lógica de anonimización determinista del cliente pesado legacy (`client_app/app/modules/privacy/anonymizer.py` y servicios asociados) al servidor FastAPI, garantizando la soberanía del dato en arquitecturas híbridas.

1\. Migración 'As-Is' (No reescribir la lógica):

* Traslada el motor NER y las reglas de sustitución determinista del código legacy a `server/app/core/privacy/`.  
* Mantén las funciones probadas de detección y reemplazo de PII (nombres, DNIs, etc.), asegurando que el comportamiento sea idéntico al sistema original.

2\. Implementación del Vault en el Edge:

* Configura el servicio `PrivacyGuardian` para que la gestión del Vault (tabla de mapeo `[PERSONA_1] <-> Valor Real`) resida en edge cuando el despliegue se haga separando cloud de edge.   
* Regla Crítica: Si el despliegue es en modo `EDGE`, el Vault debe residir exclusivamente en la base de datos  del nodo institucional.  
* P

3\. Orquestación Selectiva en LangGraph:

* En `server/app/modules/agents_hub/agent/graph.py`, añade un nodo interceptor que verifique la política de la Organización o del Tipo de Expediente.  
* Si la política exige anonimización y existe un nodo Edge, el proceso debe ejecutarse en dicho nodo antes de cualquier llamada a APIs externas o al Cloud central.  
* La 'rehidratación' (restauración de datos reales) debe ocurrir solo en el Edge, en el último paso antes de entregar la respuesta a la interfaz del usuario.

4\. Verificación y Auditoría:

* Revisa los tests legacy (`test_ner_upgrade`, `test_privacy_audit`) para validar que, en un despliegue de nodo, ningún dato real de identidad llega a las tablas del servidor Cloud.

Criterio de Aceptación: El sistema debe anonimizar de forma transparente para el usuario, pero el rastro técnico debe confirmar que el Vault de identidades nunca salió del perímetro del nodo Edge institucional."

---

Puntos clave de esta migración:

* Aprovechamiento del código: No se gasta tiempo en crear nuevos modelos NER; se utiliza la lógica que ya funciona en el cliente pesado.  
* Soberanía garantizada: Al mover el Vault al Edge, cumples con los requisitos más estrictos de privacidad, ya que el proveedor del Cloud si el despliegue se hiciera el Edge (o la IA externa) nunca "conoce" a las personas mencionadas en los documentos de aquellos expedientes marcados como sensibles. .  
* Jerarquía aplicada: El Admin (institucional) decide cuándo activar este escudo de privacidad basándose en la sensibilidad de cada Organización o trámite.

---

### **Prompt 4.3: Separación de Aprendizaje de Estilo (Filosofía Hermes)**

**Objetivo:** Aprender del usuario sin comprometer la identidad de los datos anonimizados.

**Instrucciones para el Agente de Programación:**

"Configura el sistema de **Memoria de Estilo** para que sea compatible con la anonimización:

1. **Flujo de Aprendizaje:** Cuando el usuario corrige un texto en modo HITL, el sistema debe primero 're-anonimizar' la corrección usando el Vault local.  
2. **Extracción de Patrones:** El agente debe extraer patrones de redacción y tono del texto anonimizado (ej. 'el usuario prefiere listas numeradas').  
3. **Persistencia:** Guarda estos patrones en la tabla `user_preferences_vector`.  
4. **Resultado:** De esta forma, el 'Cerebro' aprende a escribir como el funcionario, pero nunca llega a conocer los nombres reales que este maneja."

### Bloque 5\. Introducción de Estrategias de ingestión modulares

Los chatbots públicos generan su base documental a partir de **Estrategias de Ingestión** o **Spider Skills**. Me gustaría definirlas de forma modular, el sistema debe permitir que el **SuperAdmin** defina la lógica base (motores) y el **Admin** configure los parámetros específicos para su **Organización**.

A continuación, presento sugerencia de instrucciones 

**Tarea. 5.1  Extensión del Modelo de Ingestión (Base de Datos)**

**Objetivo:** Permitir que cada fuente de información web guarde qué "Skill" utiliza y su configuración específica en formato JSON.

**Instrucciones para el Agente de Programación:**

"Actúa como desarrollador de Backend. Modifica el modelo `HubIngestionSource` en `server/app/modules/agents_hub/database/models.py` para soportar **Estrategias de Ingestión Dinámicas**:

1. **Campo `spider_skill`:** Añade una columna de tipo String (ej. 'generic', 'uji\_normativa', 'procedimientos') para identificar el motor de búsqueda a usar.  
2. **Campo `config_json`:** Añade una columna de tipo JSONB para almacenar los parámetros específicos de la Organización (selectores CSS, selectores de exclusión, mapeos de campos).  
3. **Campo `organizacion_id`:** Asegura que la fuente esté vinculada a la nueva jerarquía de `Organización` definida en la refactorización de roles.  
4. Genera la migración de Alembic para actualizar el esquema."

---

### **Tarea 5\. 2: Registro de "Spider Skills" y Clase Base (Backend)**

**Objetivo:** Crear un patrón de diseño que permita al SuperAdmin añadir nuevos motores de búsqueda sin modificar el core del sistema.

**Instrucciones para el Agente de Programación:**

"Implementa un **Registro de Spider Skills** en `server/app/modules/agents_hub/ingestion/spiders/`:

1. **Interfaz `BaseSpiderSkill`:** Define una clase base abstracta con el método `async crawl(source_config: dict) -> list[str]` que devuelva la lista de URLs finales a procesar.  
2. **`SpiderRegistry`:** Crea un singleton donde se registren las diferentes implementaciones (Skills).  
3. **Migración de Spiders Existentes:** Refactoriza el `WebSpider` (Prompt 9CBis.16) y el `UJINormativaSpider` (Prompt 9CBis.17) para que hereden de esta base y se registren en el `SpiderRegistry`.  
4. **Inyección de Configuración:** Los selectores de contenido y patrones de URL deben leerse del `config_json` de la fuente, permitiendo que una misma Skill funcione para diferentes estructuras web mediante parámetros."

---

### **Tarea 5.3: Orquestador de Ingestión Multivía**

**Objetivo:** Actualizar el vigilante de ingestión para que use la "Skill" asignada por el Admin.

**Instrucciones para el Agente de Programación:**

"Refactoriza el `IngestionWatcher` en `server/app/modules/agents_hub/ingestion/watcher.py` para usar el nuevo sistema de Skills:

1. Al procesar una fuente, el `Watcher` debe consultar el `SpiderRegistry` usando el campo `spider_skill` de la base de datos.  
2. Pasa el `config_json` al motor seleccionado para obtener las URLs hoja.  
3. El proceso de conversión (Docling) se mantiene centralizado, pero el `Watcher` debe aplicar los filtros de contenido (CSS selectors) definidos en la configuración de la Organización antes de guardar el `HubDocument`."

---

### **Tarea 5.4: UI Dinámica para la Configuración de Fuentes (Frontend)**

**Objetivo:** Crear un formulario que se adapte según la "Skill" seleccionada por el Admin.

**Instrucciones para el Agente de Programación:**

"Modifica la interfaz de creación de fuentes en `frontend/src/admin/pages/DocumentsPage.tsx`:

1. **Selector de Skill:** Añade un desplegable para elegir entre los motores disponibles (Genérico, Normativa, Procedimientos, etc.).  
2. **Formulario Dinámico:** Según la Skill seleccionada, muestra campos específicos para el `config_json`:  
   * Para 'Genérico': campos de regex y profundidad.  
   * Para 'Estructurado': campos para introducir selectores CSS de título, cuerpo y fecha.  
3. **Validación:** Asegura que los parámetros requeridos por la Skill seleccionada estén presentes antes de enviar la configuración al backend."

### **Tarea 5.5. UI y lógica del Skill de Descubrimiento Autónomo con Validación HITL** 

Este es el prompt técnico detallado para implementar el **Asistente de Ingestión HITL**. Este componente internaliza la capacidad de razonamiento de Hermes dentro de tu propia infraestructura, eliminando la necesidad de aplicaciones externas y manteniendo al **Admin** al mando del proceso.

---

### **Prompt: Implementación del Asistente de Ingestión HITL (Spider Skill Generator)**

**Contexto:** Necesitamos facilitar al **Admin** la creación de plantillas de scrapping (`config_json`) para las **Organizaciones**. En lugar de un agente autónomo que navegue por la web, el Admin proporcionará el código fuente de la página y la IA propondrá los selectores óptimos para su validación inmediata.

**Instrucciones para el Agente de Programación:**

**1\. Backend: Endpoint de Análisis de Estructura**

* Crea un endpoint `POST /api/v1/hub/admin/analyze-html` en el módulo de administración.  
* **Entrada:** Recibe el código HTML (`view-source`) pegado por el usuario y el objetivo de extracción (ej. "Lista de reglamentos").  
* **Lógica de IA:** \* Utiliza el `ModelFactory` para invocar un modelo de **Tier 3** (máxima precisión lógica).  
  * Envía un prompt especializado que instruya al LLM a identificar:  
    1. El contenedor principal de la lista de documentos.  
    2. El selector CSS/XPath para el `título`, la `fecha` y el `enlace al PDF`.  
    3. Patrones de paginación si son visibles en el código.  
* **Salida:** Un JSON estructurado que represente una propuesta de `config_json`.

**2\. Frontend: Interfaz del Asistente (HITL UI)**

* En `frontend/src/admin/pages/DocumentsPage.tsx`, añade un modal llamado **"Asistente de Configuración de Fuente"**.  
* **Paso 1 (Captura):** Un `textarea` grande para que el Admin pegue el `view-source` y un campo para la URL.  
* **Paso 2 (Propuesta IA):** Al pulsar "Analizar", muestra los selectores propuestos en un formulario editable.  
* **Paso 3 (Validación en Vivo):** \* Añade un botón **"Probar Configuración"**.  
  * Al pulsarlo, el backend debe intentar realizar una extracción real usando esos selectores contra la URL proporcionada (vía `httpx` y `Docling`).  
  * Muestra una tabla con los primeros 5 resultados detectados para que el Admin confirme que son correctos.

**3\. Bucle de Aprendizaje (Filosofía Hermes)**

* Si el Admin aprueba la configuración, guárdala en el **Script Registry** etiquetada con la URL base de la Organización.  
* Añade un campo `extraction_confidence` basado en si el Admin tuvo que corregir los selectores propuestos por la IA o no, para mejorar futuros prompts de análisis.

**4\. TDD y Seguridad**

* **Test Red:** Define una prueba que envíe un fragmento HTML de la web de la UJI y verifique que el servicio no devuelve un error 500\.  
* **Test Green:** Valida que el JSON devuelto contiene selectores CSS válidos sintácticamente.

**Criterio de Aceptación:** El Admin debe ser capaz de configurar una nueva fuente web compleja en menos de 2 minutos, pasando de código HTML en bruto a una plantilla de ingesta verificada y funcional sin escribir una sola línea de código CSS/XPath manualmente.

### Bloque Seis. Actualización de documentación, 

Habrá que actualizar a los archivos de documentación `Arquitectura.md` y `planificacion/PLAN_TDD_DETALLADO.md` para reflejar los cambios realizados. 

1. La filosofía Hermes  
2. La sustitución de `Partner` por `Admin` y `Client` por `Organización`.  
3. La nueva delimitación Cloud/Local: Inteligencia y Auditoría en Server; Ejecución Determinista en Thin Client.  
4. La política de anonimización selectiva y distribuida (Edge-first).

**Criterio de Aceptación:** Los documentos deben ser coherentes con el código fuente refactorizado en los pasos anteriores."  

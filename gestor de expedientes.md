La propuesta para tu nuevo **Gestor de Expedientes Híbrido** se basa en transformar una herramienta de automatización rígida en un sistema inteligente, auditable y soberano. Aquí tienes el resumen ejecutivo de la arquitectura y su valor:

\---

## 1\. Arquitectura Técnica (El "Stack" Soberano)

El sistema abandona las dependencias propietarias para basarse en tecnologías de **Software Libre**, garantizando que cualquier administración pueda adoptarlo:

* **Frontend (React):** Una interfaz visual "Low-Code" donde el responsable funcional diseña flujos mediante arrastrar y soltar (nodos y flechas), sin programar.
* **Cerebro (LangGraph + Python):** Orquestación de procesos no lineales. Permite que el expediente avance, retroceda o entre en bucles de corrección de forma inteligente.
* **Base de Datos (PostgreSQL + pgvector):** Almacenamiento unificado de datos relacionales del expediente y vectores para búsqueda semántica en documentos (PDFs).
* **Ejecución (Celery + Redis):** Un motor de tareas en segundo plano que procesa los expedientes de forma asíncrona, evitando que la web se bloquee.

\---

## 2\. El Modelo de "Metaprogramación"

A diferencia de otros gestores, la IA no toma la decisión final, sino que actúa como un **ingeniero de software interno**:

1. **Análisis:** La IA lee la normativa y el expediente.
2. **Generación:** Crea un **script de Python determinista** (específico para ese trámite).
3. **Ejecución:** El script (o un **Playbook de Playwright**) realiza la tarea técnica (cálculos, navegación web, extracción).
4. **Resultado:** Se obtiene una respuesta 100% precisa y auditable, eliminando el riesgo de "alucinaciones" de la IA.

\---

## 3\. Gestión Híbrida: Local vs. Servidor

El sistema detecta automáticamente dónde debe ejecutarse cada fase:

* **Modo Servidor:** Para procesos oficiales, auditorías y tareas pesadas. Se integra vía API con el gestor actual de la Universidad (Oracle).
* **Modo Cliente (Headless):** Para tareas de escritorio o trámites que requieran el certificado digital o la sesión local del funcionario, ejecutando los Playbooks de Playwright en su propio navegador.

\---

## 4\. Cumplimiento del RIA (Reglamento de IA de la UE)

La propuesta sitúa a la Universidad a la vanguardia legal mediante tres pilares:

* **Transparencia (Explicabilidad):** Cada paso del grafo guarda el "por qué" de la decisión y el código exacto que se ejecutó.
* **Supervisión Humana (Human-in-the-loop):** El responsable funcional puede definir "puntos de interrupción" obligatorios donde el expediente se detiene hasta que un humano lo valida.
* **Determinismo:** Al separar la "lógica de la IA" de la "ejecución del script", se garantiza que los actos administrativos sean consistentes y repetibles.

\---

## 5\. Valor para el Responsable Funcional

El usuario experto en la materia (no en programación) recupera el control:

* **Define procesos:** Indica qué se hace en cada fase y quién es el funcionario responsable.
* **Usa plantillas:** No empieza de cero; utiliza estructuras predefinidas de expedientes comunes.
* **Asistencia activa:** Recibe propuestas de resolución ya redactadas y datos ya validados por el "asistente de metaprogramación", teniendo que actuar solo en casos ambiguos.

**En resumen:** Es una plataforma que utiliza la IA para generar herramientas deterministas (Python/Playwright), permitiendo una gestión de expedientes flexible, segura y totalmente integrada en la infraestructura existente de la Universidad.


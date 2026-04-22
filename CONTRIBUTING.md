🛠️ CONTRIBUTING.md: MANUAL UNIFICADO DE DESARROLLO (v2.0)
Este documento establece las normas obligatorias para la evolución y mantenimiento de AutomatIA. Todo colaborador (humano o agente IA) debe seguir estos protocolos estrictamente.

🎯 0. PRE-FLIGHT CHECK (Obligatorio)

Para evitar conflictos con los alias de Windows y asegurar el aislamiento del entorno, toda ejecución de scripts o tests debe realizarse mediante uv.

Antes de iniciar cualquier tarea, el agente DEBE ejecutar: uv run scripts/validate\_dev\_env.py

Nota para Windows: Nunca uses el comando python directamente. Si el sistema te redirige a la Microsoft Store, es una señal de que no estás usando el ejecutor uv.

Sincronización: Si has añadido dependencias, ejecuta primero uv sync para actualizar el entorno antes del check de validación.

🤖 1. REGLAS DE COMPORTAMIENTO PARA AGENTES (Cline, Claude Code, etc.)
Análisis Previo Obligatorio: Antes de proponer o ejecutar cambios, DEBES leer ARCHITECTURE.md para entender la soberanía de datos y la jerarquía de servicios.

No Suposición de Servicios: Utiliza siempre el objeto global state para acceder a la lógica inyectada; nunca instancies servicios de forma aislada si ya existen en el contenedor de dependencias.

Autonomía con Responsabilidad: Ejecuta cambios técnicos alineados con la arquitectura y reporta tras la ejecución. Si detectas código que viola los "Estándares de Desarrollo", propón una refactorización inmediata.

Metodología "Divide y Vencerás": Desglosa tareas complejas en pasos pequeños y solicita validación tras cada hito.

🔄 2. CICLO DE TRABAJO OBLIGATORIO (TDD + GIT)
Se debe aplicar estrictamente el ciclo de desarrollo dirigido por pruebas y control de versiones:

🔴 RED: Crea el test en la carpeta tests/ correspondiente y valida que falle.

🟢 GREEN: Implementa el código mínimo necesario para que los tests pasen.

💾 GIT COMMIT: Realiza un commit inmediatamente después de que los tests pasen y antes de continuar con la siguiente tarea.

Usa Conventional Commits (ej: feat:, fix:, test:, refactor:).

Menciona explícitamente qué tests han pasado en el mensaje del commit.

🔵 REFACTOR: Limpia y optimiza el código manteniendo la integridad de los tests.

🏗️ 3. REGLA DE ORO: LOGIC-FIRST
Prohibido el desarrollo "UI-First": No se deben implementar componentes de interfaz (NiceGUI) sin haber validado primero la lógica de negocio mediante tests unitarios en los Servicios o el Core.

Independencia de la Interfaz: La lógica debe ser funcional incluso sin la capa visual.

💻 4 ESTÁNDARES TÉCNICOS DE CODIFICACIÓN

Asincronía: Toda operación de Entrada/Salida (I/O) y llamadas a la API del Brain deben ser async por defecto.

Tipado Estricto: Usa Python Type Hints en todas las definiciones de funciones y métodos.

Seguridad: Todo script generado debe pasar por el SecurityAuditor para asegurar que no existan funciones prohibidas (eval, exec, accesos a rutas absolutas) antes de proponerlo.

Consistencia Windows: Incluye siempre manejo de errores para bloqueos de archivos (WinError 32) en módulos que manipulen el sistema de archivos.

Internacionalización (i18n): Prohibido hardcodear strings de texto en la UI. Usa state.i18n.t('key') y actualiza translations.json.

🧱 5 DESACOPLAMIENTO CLIENTE-SERVIDOR (Muro de Seguridad)

Para garantizar la soberanía de datos y la escalabilidad distribuida:

Prohibición de Importaciones: Ningún archivo bajo client\_app/ puede importar módulos de server/.

Comunicación vía API: El cliente debe comunicarse con el Brain únicamente a través de BrainAPIClient (o el LocalBrainClient adapter en modo monolito).

Protocolo de Datos: Los datos PII reales se quedan en el cliente. Solo datos anonimizados viajan al Brain.

🎨 6. INTERFAZ DE USUARIO (UI/UX)
Estilo Visual: Mantén la consistencia estética basada en Tailwind CSS y componentes nativos de NiceGUI.

Variables y Datos:

Usa el DataFlowAnalyzer para mapear y validar tipos de variables.

Evita visualizaciones crudas: Nunca renderices objetos directamente (ej: \[object Object]). Asegúrate de mostrar el atributo .name o .label de las variables en los chips y selectores.

Navegación: Los asistentes de configuración (Wizards) deben abrirse en paneles laterales (SideDrawer) para no romper el contexto del flujo de trabajo actual.

Feedback: Asegura que cada componente reactivo maneje correctamente los estados de carga mediante spinners o skeletons.a HTTP. No asumas acceso directo a la base de datos del servidor desde el código del cliente.

🌍 7. INTERNACIONALIZACIÓN (i18n)

AutomatIA es un producto global. Se prohíbe el uso de strings de texto directamente en la UI:

Uso de Claves: Usa siempre state.i18n.t('mi\_clave') en los componentes de NiceGUI.

Registro: Toda nueva etiqueta debe ser añadida a client\_app/app/i18n/translations.json.

Visualización de Variables: Al renderizar variables del flujo, nunca uses el objeto completo (evita el error \[object Object]). Usa var.name o var.label.


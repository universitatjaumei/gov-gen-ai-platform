# Motor de Ejecución (Runtime Engine)

El Runtime Engine es el corazón del Client Node. Se encarga de recibir los scripts generados por el Brain, validarlos y orquestar su ejecución segura sobre los datos locales.

## 1. Ciclo de Vida de una Tarea

1.  **Trigger**: Una tarea puede iniciarse por un Watcher (Email/Archivo), una programación de Scheduler, o manualmente desde la UI.
2.  **Preparación de Contexto**: El sistema localiza los archivos de entrada y crea un directorio de ejecución aislado (`execution_dir`).
3.  **Obtención de Script**:
    - Si existe un script publicado (`PUBLISHED`) para esa tarea, se recupera del caché local.
    - Si no, se solicita la generación al Brain mediante el flujo de anonimización.
4.  **Auditoría de Seguridad**: El código se pasa por el `SecurityAuditor` (AST check).
5.  **Ejecución en Sandbox**: Se lanza el proceso Python en un proceso hijo restringido.
6.  **Post-Procesamiento**: Se recogen los resultados, se de-anonimizan los datos y se guardan en el historial (`TaskLog`).

## 2. Orquestación de Flujos (FlowEngine)

AutomatIA permite encadenar múltiples tareas en un flujo de trabajo único (`FlowRegistry`).

- **Paso a Paso**: Cada paso del flujo es atómico. Si un paso falla, el flujo se detiene (Stop-on-error) para evitar corrupción de datos.
- **Data Binding**: Los resultados (JSON/Files) de un paso pueden ser inyectados como entrada del siguiente paso.
- **Triggers Soportados**:
    - **Schedule**: Basado en cron para ejecuciones periódicas.
    - **Watcher**: Reacción inmediata a la llegada de archivos o emails.

## 3. Manejo de Logs y Errores

Cada ejecución genera un `execution_id` único que vincula:
- Logs de consola del script ejecutado.
- Métricas de consumo y tiempo.
- Enlaces a los archivos generados.

En caso de error persistente tras reintentos automáticos, el sistema permite la "Escalación al Partner", donde se envía un paquete de diagnóstico anonimizado para revisión técnica manual.

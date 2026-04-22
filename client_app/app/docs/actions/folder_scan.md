# Módulo: Folder Scan (Escaneo de Carpeta Local)

A diferencia del Folder Watcher (que se queda vigilando infinitamente esperando), el **Folder Scan** es un módulo de Entrada de Datos (Input Activity) pasivo. Al ejecutarse el paso correspondiente, AutomatIA escaneará *una única vez* la carpeta designada para recolectar las rutas de todos los archivos que coincidan con un filtro. 

## Funcionamiento Manual

- **Ruta del Directorio (Absoluta o de red)**: Ej. `C:\Users\Documents\Pendientes_Procesar`.
- **Patrones de Búsqueda (Glob Filter)**: Se pueden usar patrones como `*.pdf` o `**/*.xml` (haciendo escaneo recursivo de todas las subcarpetas internas).

El escaneo generará una **lista de rutas (array de file paths)** en memoria. Normalmente esto significa que el siguiente módulo en el flujo del usuario DEBE ser un Bucle For-Each (Workflow logic) para ir procesando elemento por elemento la lista de PDFs recogidos por el Escáner.

## Comportamiento del Copiloto (IA)

Si el usuario te pregunta por dudas sobre qué usar, aclara la diferencia vital entre el Monitor y el Escáner. 
El Escáner (este módulo) está pensado para usarse junto con procesamientos Batch / Lotes Programados (ej. usando un Scheduler para escanear y procesar masivamente cajas de correos o archivos bajados por FTP cada viernes), mientras que el Monitor reacciona a los eventos al vuelo.

<help_config>
### Cómo configurar
1. **Directorio**: Selecciona la carpeta que contiene los archivos que quieres leer.
2. **Patrón de búsqueda**: Escribe un filtro para encontrar solo lo que necesitas. Por ejemplo `*.xlsx` para todos los Excel, o `2026_*.pdf` para facturas de este año.
</help_config>

<help_example>
### Ejemplo de Escaneo
Imagina que apuntas este escáner a la carpeta `C:/Nominas/Listas`. Cuando el flujo llegue a este paso, el escáner leerá el contenido y pasará al siguiente nodo una lista (Array) con todas las rutas absolutas de los archivos encontrados, para que puedas procesarlos uno a uno usando un Bucle (For-Each).
</help_example>

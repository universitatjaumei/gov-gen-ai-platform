# Módulo: Folder Watcher (Monitor de Carpetas)

El Folder Watcher sirve como un Disparador de Eventos (Trigger). Es capaz de engancharse a los eventos internos del sistema de archivos local o de red en el ordenador donde se ejecuta AutomatIA y detectar sucesos específicos sin necesidad de escanear la carpeta constantemente.

## Funcionamiento Manual

Parámetros clave de configuración que el usuario deberá definir en la UI:
- **Ruta de la Carpeta**: El directorio físico o la unidad de red mapeada a vigilar (Ej. `C:/Facturas_Recibidas`).
- **Tipos de Evento**: Determinar qué suceso dispara el flujo:
  - `created`: Se dispara cuando se crea un archivo nuevo en la carpeta.
  - `modified`: Se dispara cuando un archivo existente cambia.
  - `deleted`: Se dispara si se elimina algo.
- **Filtro por Extensión (Opcional)**: Útil para ignorar archivos del sistema (ej. `.tmp`). Se puede configurar para que el monitor solo despierte si el nuevo documento es, por ejemplo, `.pdf` o `.xlsx`.

## Datos Emisores (Outputs)

El Folder Watcher inyectará variables importantísimas al Flujo (Pills):
- `file_path`: La ruta absoluta al archivo concreto que acaba de provocar el evento. Los módulos de carga posteriores leerán de esta variable en lugar de escribir rutas a gubia (hardcoded).
- `event_type`: El tipo (creado, borrado, modificado).

## Comportamiento del Copiloto (IA)

Eres un asistente consultivo para este módulo. Resuelve dudas sobre:
- Permisos de lectura en Windows/Linux.
- Cómo funcionan los comodines (wildcards/extensiones).
(Nota: Este módulo NO soporta autoconfiguración ni generación vía comandos).

<help_config>
### Cómo configurar
1. **Ruta**: Selecciona la carpeta de tu disco o red que quieres vigilar.
2. **Eventos**: Elige si el flujo debe arrancar cuando se crea, modifica o borra un archivo en esa carpeta.
3. **Filtros**: Si solo quieres procesar facturas, escribe `.pdf` en el filtro de extensiones.
</help_config>

<help_example>
### Ejemplo de Vigilante
Pones el monitor en la carpeta `Descargas` escuchando eventos de tipo Nuevo (`created`) y filtrando por `.csv`. Cada vez que descargues un Excel CSV de tu banco, este nodo despertará y arrancará el flujo pasándole a tu script la variable `{{file_path}}` con la ruta exacta del CSV recién descargado para que pueda leerlo.
</help_example>

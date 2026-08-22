# Widget de Estado de Red para Carpetas Monitorizadas

## Descripción

Se ha implementado un nuevo widget en el dashboard principal que permite visualizar el estado de las carpetas monitorizadas por el sistema FolderWatcher. Este widget proporciona información crítica sobre la conectividad y disponibilidad de las rutas de archivos configuradas.

## Características

### Estados visualizados
- **ONLINE (Verde)**: Carpeta accesible y monitoreo activo
- **OFFLINE (Rojo)**: Carpeta no accesible o ruta inexistente
- **PAUSADO (Gris)**: Carpeta accesible pero monitoreo pausado
- **INACTIVO (Gris)**: Carpeta accesible pero monitoreo deshabilitado

### Información mostrada
- Nombre de la carpeta monitorizada
- Ruta de la carpeta (truncada si es muy larga)
- Estado actual con ícono correspondiente
- Tiempo desde la última verificación
- Número de archivos procesados (contador de disparos)

## Funcionalidades

### Botón de Re-escaneo
- Permite al usuario forzar una verificación de conectividad de todas las carpetas
- Actualiza inmediatamente el estado visual del widget
- Muestra notificación de confirmación

## Archivos modificados

1. `client_app/app/services/folder_watcher_service.py`
   - Se añadió el método `verify_connectivity()` para verificar el estado de todas las rutas configuradas
   - Se mejoró la lógica de verificación de estados en `check_all_paths_health()`

2. `client_app/app/database/models.py`
   - Se añadieron campos adicionales a `FolderWatcherConfig`:
     - `is_paused` (Boolean): Indica si el monitoreo está pausado
     - `last_error` (String): Almacena el último mensaje de error
     - `last_check_at` (DateTime): Fecha de la última verificación

3. `client_app/app/ui/dashboard_page.py`
   - Implementación del widget `render_network_status_widget()`
   - Integración del widget en el layout principal del dashboard
   - Adición de importaciones necesarias

## Tests unitarios

Se han creado pruebas unitarias para validar el comportamiento del widget:

- `client_app/tests/unit/test_network_status.py`
  - Prueba con configuraciones válidas
  - Prueba sin configuraciones
  - Validación de la llamada a la verificación de conectividad

## Cómo se determina el estado

El color del estado se determina siguiendo esta lógica:

```python
# Determinar estado visual
is_online = config['last_error'] is None or 'Ruta no accesible' not in (config['last_error'] or "")
is_active = config['is_active']
is_paused = config['is_paused'] and not is_active

# Asignar color según estado
if not is_online:
    color = 'red'  # Offline/Inaccesible
    status_text = 'OFFLINE'
    icon = 'cancel'
elif is_paused:
    color = 'grey'  # Pausado
    status_text = 'PAUSADO'
    icon = 'pause_circle'
elif is_active:
    color = 'green'  # Online
    status_text = 'ONLINE'
    icon = 'check_circle'
else:
    # Esto sería estado inactivo pero online
    color = 'grey'
    status_text = 'INACTIVO'
    icon = 'radio_button_unchecked'
```

## Beneficios

- Visibilidad inmediata del estado de las conexiones de carpetas
- Identificación rápida de problemas de conectividad
- Control manual de verificación de estado
- Mejora en la experiencia de usuario al administrar múltiples carpetas monitorizadas
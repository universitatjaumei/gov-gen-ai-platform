# Resolución de Problemas (Troubleshooting)

Esta guía recopila soluciones a los problemas más frecuentes encontrados durante la instalación y el uso de AutomatIA.

## 1. Errores de Instalación

### Error: `WinError 1450` (Recursos de sistema insuficientes)
- **Causa**: NiceGUI en modo nativo puede agotar los handles de Windows en versiones antiguas.
- **Solución**: Limita el número de recargas del navegador o utiliza `AUTOMATIA_MODE=web` para acceder vía navegador estándar.

### Playwright no funciona (libEGL.dll missing, etc.)
- **Causa**: Faltan dependencias de sistema para el navegador.
- **Solución**: Ejecuta `playwright install-deps` como administrador.

## 2. Errores de Ejecución (Client Node)

### Fallo en el Sandbox: `SecurityException: Blocked`
- **Causa**: El script generado por la IA intenta usar una librería no permitida o acceder a un archivo fuera del directo jail.
- **Solución**: Revisa el script en el panel de edición. Si la librería es segura y necesaria, solicita al Partner que la añada a la `SecurityPolicy`.

### El Anonymizer no detecta nombres propios
- **Causa**: El modelo de `spaCy` no está cargado o es incorrecto para el idioma.
- **Solución**: Verifica que `es_core_news_sm` está instalado (`uv run python -m spacy info`).

## 3. Comunicación Brain-Client

### El cliente no se conecta (Error 403)
- **Causa**: La `license_key` es inválida, ha expirado, o la cuota de tokens se ha agotado.
- **Solución**: Verifica el estado de la licencia en el Panel de Administrador del Brain.

### Tiempos de espera agotados (Timeout)
- **Causa**: La generación del script por parte del LLM está tardando más de lo permitido (por defecto 60s).
- **Solución**: Aumenta el timeout en la configuración del `AIBrainService` o revisa la carga de trabajo del proveedor de IA.

## 4. Errores de Características V4.0

### GraphicsFactory: Error al generar gráficos
- **Causa**: Faltan dependencias de matplotlib o seaborn.
- **Solución**: 
  ```bash
  uv add matplotlib seaborn
  uv run python -c "import matplotlib; import seaborn; print('OK')"
  ```

### ReportFactory: Error "ReportLab not found"
- **Causa**: ReportLab no está instalado.
- **Solución**: `uv add reportlab`

### ClarificationService: No aparecen preguntas
- **Causa**: Servicio desactivado o solicitud suficientemente clara.
- **Solución**: Verifica `CLARIFICATION_ENABLED=true` en `.env`.

### ScreenshotGuard: Bloquea screenshots necesarios
- **Causa**: Política en modo BLOCK.
- **Solución**: Cambia a REVIEW o TRUSTED en Configuración → Privacidad Visual.

### APIWatcher: Error de conexión a API
- **Causa**: Credenciales incorrectas o límite de rate excedido.
- **Solución**: Verifica credenciales en Conexiones → API. Si es 429, reduce frecuencia.

## 5. Logs de Diagnóstico
Si el problema persiste, revisa los archivos de log en la raíz del proyecto o en la carpeta `data/logs/`:
- `debug_output.txt`: Logs generales de la aplicación.
- `TaskLog` (BD): Errores específicos de ejecución de scripts.

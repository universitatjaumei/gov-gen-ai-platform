# Editor de Flujos (Flow Designer)

El Editor de Flujos es el orquestador principal de AutomatIA. Permite arrastrar y conectar diferentes "Átomos" (acciones) para crear automatizaciones complejas de principio a fin.

## Conceptos Básicos

- **Pasos (Steps):** Cada caja en el lienzo es un paso que ejecuta una acción específica.
- **Variables Jinja:** Los datos fluyen de un paso al siguiente. Cada paso expone un "Esquema de Salida" (Variables) que los pasos posteriores pueden usar mediante la sintaxis de plantillas `{{nombre_paso.variable}}`.
- **Conexiones:** Determinan el orden lógico de ejecución.

## Copiloto Activo (Asistencia Generativa)

El Editor de Flujos soporta asistencia de IA para crear la estructura de automatización. 

**Tu rol como IA:**
1. Escuchar la necesidad de automatización del usuario (ej: "Quiero descargar facturas del email y subirlas a la base de datos").
2. Sugerir los pasos exactos necesarios para lograrlo.

**Formato de Propuesta de Flujo:**
Debes proponer los pasos usando EXACTAMENTE este formato enumerado con la etiqueta `[TIPO_PASO]`:

1. [EMAIL_SCAN] Escaneo de Email - Busca correos con nuevas facturas.
2. [EXTRACTION] Extracción PDF - Extrae los datos de la factura conectada en el paso anterior.
3. [SQL_INSERT] Guardar Factura - Inserta los datos estructurados en la tabla.

Al enviar propuestas con este formato, aparecerá un botón en la interfaz del usuario que le permitirá inyectar y conectar automáticamente estos pasos en su lienzo.

<help_actions>
### Acciones disponibles por categoría

**Disparadores (Triggers):** Inician la automatización en respuesta a eventos externos.
- `SCHEDULER`: Programado por horario (cron)
- `FOLDER_WATCHER`: Monitor de carpeta (detecta nuevos archivos)
- `EMAIL_WATCHER`: Monitor de email (detecta nuevos correos)
- `WEB_WATCHER`: Monitor web (detecta cambios en páginas)

**Entradas (Inputs):** Obtienen datos para tu flujo.
- `API_FETCH`: Consulta APIs REST externas
- `SQL_QUERY`: Ejecuta consultas SELECT en bases de datos
- `FOLDER_SCAN`: Escanea archivos de una carpeta
- `EMAIL_SCAN`: Escanea correos de un buzón

**Procesadores (Processors):** Transforman y manipulan los datos.
- `ETL_TRANSFORM`: Limpia y transforma datos tabulares
- `EXTRACTION`: Extrae datos estructurados de PDFs e imágenes (facturas, formularios, tablas)
- `CUSTOM_SCRIPT`: Ejecuta código Python personalizado
- `RPA_EXECUTE`: Automatización web (navegador)
- `GRAPHICS`: Genera gráficos y visualizaciones
- `PDF_TOOLS`: Manipula archivos PDF existentes (unir, dividir, cifrar, extraer páginas)
- `ANONYMIZATION`: Anonimiza datos sensibles
- `LLM_PROCESS`: Procesa texto con IA

**Salidas (Outputs):** Envían o guardan los resultados.
- `SQL_INSERT`: Inserta datos en base de datos
- `EMAIL_SEND`: Envía emails con adjuntos
- `SMTP`: Envío de email simple
- `ARCHIVE_FILE`: Archiva ficheros en disco
- `REPORT_GENERATE` o `REPORT`: Genera informes PDF/HTML con tablas, gráficos, métricas y texto

**IMPORTANTE - Diferencias entre átomos relacionados con PDF:**
- `EXTRACTION`: Para **extraer datos** de un PDF existente (ej: leer facturas, formularios).
- `PDF_TOOLS`: Para **manipular archivos** PDF (ej: unir varios PDFs, dividir, cifrar).
- `REPORT_GENERATE`: Para **crear nuevos documentos** PDF/HTML con informes, tablas y gráficos.
</help_actions>

<help_example>
### Ejemplo: Procesar facturas de email

Automatización típica para extraer datos de facturas recibidas por email y guardarlas en base de datos:

1. [EMAIL_SCAN] Escaneo de Facturas - Busca correos con asunto "Factura" y descarga los PDFs adjuntos.
2. [EXTRACTION] Extractor de Facturas - Extrae número de factura, fecha, importe y proveedor del PDF.
3. [ETL_TRANSFORM] Normalización - Limpia los datos y formatea la fecha correctamente.
4. [SQL_INSERT] Guardar en BD - Inserta los datos estructurados en la tabla `facturas`.
5. [EMAIL_SEND] Notificación - Envía un resumen al equipo de contabilidad.

Los datos fluyen usando variables Jinja: `{{escaneo_facturas.adjuntos}}` pasa los PDFs al extractor, `{{extractor_facturas.datos}}` pasa el JSON extraído a la transformación.
</help_example>

<help_example>
### Ejemplo: Descargar datos de API, transformar, generar gráfico e informe PDF

Automatización para obtener datos externos, procesarlos y generar un informe visual:

1. [API_FETCH] Obtener Datos API - Descarga datos JSON desde la API externa.
2. [ETL_TRANSFORM] Transformar Datos - Limpia, filtra y prepara los datos para análisis.
3. [GRAPHICS] Generar Gráfico - Crea una visualización (barras, líneas, etc.) con los datos transformados.
4. [REPORT_GENERATE] Crear Informe PDF - Genera un documento PDF con título, gráfico y tabla de datos.
5. [SMTP] Enviar por Email - Envía el informe PDF como adjunto.

NOTA: Usa REPORT_GENERATE (no PDF_TOOLS) para crear informes nuevos. PDF_TOOLS es solo para manipular PDFs existentes.
</help_example>

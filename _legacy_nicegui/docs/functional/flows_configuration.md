# Configuración de Flujos de Trabajo (Workflows)

La verdadera potencia de AutomatIA reside en la capacidad de encadenar tareas atómicas para automatizar procesos de negocio completos.

## 1. Concepto de Flujo
Un flujo es una secuencia de **Pasos** ejecutados localmente, disparados por un **Evento**.

## 2. Ejemplo Práctico: Procesamiento de Facturas por Email

### Configuración del Trigger
- **Tipo**: `EMAIL_WATCHER`
- **Filtro**: Asunto contiene "Factura" y adjuntos con extensión `.pdf`.

### Pasos del Flujo
1.  **Paso 1: Extracción PDF**
    - **Script**: "Extractor Facturas Estándar".
    - **Entrada**: Archivo descargado por el watcher.
    - **Salida**: Objeto JSON con los datos de la factura.
2.  **Paso 2: Transformación ETL**
    - **Script**: "Convertir a Formato Contaplus".
    - **Entrada**: JSON del Paso 1.
    - **Salida**: Archivo CSV formateado.
3.  **Paso 3: Envío Webhook**
    - **Configuración**: URL de la API del sistema contable.
    - **Entrada**: CSV del Paso 2.

## 3. Ejemplo Práctico: Descarga de Notificaciones y Alerta

- **Trigger**: `SCHEDULE` (Lunes a las 09:00).
1.  **Paso 1: Navegación RPA**
    - **Script**: "Descarga Notificaciones Sede Electrónica".
    - **Salida**: PDF en la carpeta de descargas.
2.  **Paso 2: Extracción PDF**
    - **Script**: "Resumen de Notificación".
    - **Entrada**: PDF descargado.
3.  **Paso 3: Notificación Email**
    - **Configuración**: Envío a `admin@empresa.com`.
    - **Contenido**: Texto resumido extraído en el Paso 2.

## 4. Gestión de Fallos en Flujos
- **Checkpoints**: El FlowEngine guarda el estado tras cada paso.
- **Reintentos**: Se pueden configurar reintentos automáticos (ej: si la API externa está caída temporalmente).
- **Notificaciones de Error**: En caso de fallo definitivo, el sistema envía una alerta al administrador local.

## 5. Ejemplos Avanzados V4.0

### Ejemplo: Sincronización CRM → Informe con Gráficos

**Objetivo**: Consumir datos de una API CRM, generar gráficos de análisis y crear un informe PDF automáticamente.

- **Trigger**: `SCHEDULE` (Lunes a las 09:00)

**Pasos del Flujo**:
1. **Paso 1: Consumo de API**
   - **Tipo**: `API_FETCH`
   - **Configuración**: Endpoint del CRM con autenticación Bearer
   - **Salida**: JSON con datos de clientes

2. **Paso 2: Transformación ETL**
   - **Script**: "Convertir JSON a DataFrame"
   - **Entrada**: JSON del Paso 1
   - **Salida**: DataFrame con datos limpios

3. **Paso 3: Generación de Gráficos**
   - **Tipo**: `GRAPHICS`
   - **Solicitud**: "Gráfico de barras de ventas por región"
   - **Entrada**: DataFrame del Paso 2
   - **Salida**: Imagen PNG

4. **Paso 4: Generación de Informe**
   - **Tipo**: `REPORT_GENERATE`
   - **Plantilla**: "Informe Semanal CRM"
   - **Entrada**: DataFrame + Gráfico
   - **Salida**: PDF profesional

5. **Paso 5: Envío por Email**
   - **Configuración**: Destinatario: dirección@empresa.com
   - **Adjunto**: PDF del Paso 4

### Ejemplo: Validación con Feedback del Usuario

**Objetivo**: Procesar facturas con validación del usuario antes de enviar al ERP.

- **Trigger**: `EMAIL_WATCHER`

**Pasos del Flujo**:
1. **Paso 1: Extracción**
   - **Script**: "Extractor Facturas"
   - **Entrada**: PDF adjunto
   - **Salida**: JSON con datos extraídos

2. **Paso 2: Validación Usuario**
   - **Tipo**: `USER_VALIDATION`
   - **Configuración**: Mostrar datos extraídos y solicitar aprobación
   - **Opciones**: Aprobar / Rechazar con feedback / Escalar

3. **Paso 3 (Condicional): Regeneración**
   - **Condición**: Si usuario rechaza
   - **Acción**: Regenerar script con feedback (máx 3 intentos)

4. **Paso 4: Envío a ERP**
   - **Condición**: Si usuario aprueba
   - **Tipo**: `WEBHOOK`
   - **URL**: API del ERP

## 6. Integración con ClarificationService

Los flujos pueden configurarse para usar el **ClarificationService** antes de generar scripts:

- **Activación**: Automática cuando la solicitud es ambigua
- **Comportamiento**: Pausa el flujo y solicita respuestas al usuario
- **Continuación**: Una vez respondidas las preguntas, el flujo continúa con el contexto completo

Para más información sobre nuevas características, consulta [Features V4.0](../technical/new_features_v4.md).

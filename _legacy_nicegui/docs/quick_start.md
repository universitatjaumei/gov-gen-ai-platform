# Guía de Inicio Rápido - AutomatIA

Esta guía te ayudará a poner en marcha AutomatIA y realizar tus primeras automatizaciones en menos de 10 minutos.

## 📋 Antes de Empezar

Asegúrate de tener instalado:
- Python 3.11 o superior
- `uv` (gestor de paquetes recomendado)
- 4GB RAM disponibles

## ⚡ Instalación en 5 Minutos

### 1. Clonar e Instalar

```bash
# Clonar el repositorio
git clone https://github.com/tu-organizacion/automatia.git
cd automatia

# Instalar dependencias
uv sync

# Instalar modelos de lenguaje natural (para anonimización)
uv run python -m spacy download es_core_news_sm

# Instalar navegadores (para RPA)
uv run playwright install chromium
```

### 2. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# Clave de seguridad (generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
AUTOMATIA_SECRET_KEY=tu_clave_fernet_aqui

# Claves de proveedores de IA (solo necesarias en el Brain/Servidor)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Modo de ejecución
AUTOMATIA_MODE=native  # 'native' para escritorio, 'web' para servidor
AUTOMATIA_ENV=development
```

### 3. Inicializar Base de Datos

```bash
# La base de datos se inicializa automáticamente en el primer arranque
# Opcionalmente, puedes forzar la inicialización:
uv run python scripts/init_and_seed.py
```

### 4. Ejecutar la Aplicación

```bash
uv run main.py
```

La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8080`.

## 🎯 Tu Primera Extracción de PDF

Vamos a crear tu primer script de extracción de datos desde un PDF.

### Paso 1: Preparar un PDF de Ejemplo

Necesitas un PDF con datos estructurados (por ejemplo, una factura, un certificado, o un informe).

### Paso 2: Acceder al Módulo de Extracción

1. En la aplicación, haz clic en **Documentos** en el menú lateral
2. Verás el asistente de extracción con varios pasos

### Paso 3: Cargar el Documento

1. En la primera pantalla, arrastra tu PDF al área de carga o haz clic para seleccionarlo
2. El sistema mostrará una vista previa del contenido detectado
3. Haz clic en **Siguiente**

### Paso 4: Definir el Esquema de Salida

Describe qué datos quieres extraer. Tienes tres opciones:

**Opción A - Descripción en Texto** (Recomendado para empezar):
```
Extrae los siguientes campos:
- Número de factura
- Fecha de emisión
- CIF del emisor
- Base imponible
- IVA
- Total
```

**Opción B - Esquema JSON** (Avanzado):
```json
{
  "numero_factura": "string",
  "fecha": "date",
  "cif": "string",
  "base_imponible": "number",
  "iva": "number",
  "total": "number"
}
```

**Opción C - Archivo de Ejemplo**:
Sube un archivo con el formato deseado y la IA deducirá la transformación.

### Paso 5: Generar el Script

1. Haz clic en **Generar Script**
2. El sistema anonimizará los datos sensibles automáticamente
3. Enviará la solicitud al Brain para generar el código Python
4. En unos segundos, verás el script generado

### Paso 6: Probar y Validar

1. Haz clic en **Probar Script** para ejecutarlo sobre tu documento
2. Revisa los resultados extraídos
3. Si algo no es correcto, puedes:
   - Hacer clic en **Regenerar** y proporcionar feedback
   - Editar manualmente el script (modo avanzado)

### Paso 7: Publicar

1. Una vez satisfecho con los resultados, haz clic en **Publicar**
2. El script quedará guardado y listo para usar en flujos automatizados

🎉 **¡Felicidades!** Has creado tu primer script de extracción.

## 🔄 Tu Primer Flujo Automatizado

Ahora vamos a crear un flujo que procese automáticamente PDFs cuando lleguen por email.

### Paso 1: Configurar Conexión de Email

1. Ve a **Conexiones** en el menú lateral
2. Haz clic en **Nueva Conexión** → **Email (IMAP)**
3. Introduce tus credenciales:
   - Servidor IMAP (ej: `imap.gmail.com`)
   - Puerto (ej: `993`)
   - Email y contraseña
4. Haz clic en **Probar Conexión** para verificar
5. Guarda la conexión

### Paso 2: Crear el Flujo

1. Ve a **Flujos** en el menú lateral
2. Haz clic en **Nuevo Flujo**
3. Dale un nombre: "Procesar facturas por email"

### Paso 3: Configurar el Trigger

1. Selecciona **Email** como tipo de trigger
2. Elige la conexión de email que creaste
3. Configura los filtros:
   - Asunto contiene: "Factura"
   - Con adjuntos: Sí
   - Extensión: `.pdf`

### Paso 4: Añadir Pasos

**Paso 1 del Flujo - Extracción:**
1. Haz clic en **Añadir Paso**
2. Selecciona **Extracción de Documento**
3. Elige el script que creaste anteriormente
4. Configura la entrada: "Adjunto del email"

**Paso 2 del Flujo - Notificación:**
1. Haz clic en **Añadir Paso**
2. Selecciona **Enviar Email**
3. Configura:
   - Destinatario: tu email
   - Asunto: "Factura procesada: {{numero_factura}}"
   - Cuerpo: "Total: {{total}} €"

### Paso 5: Activar el Flujo

1. Revisa la configuración completa
2. Haz clic en **Guardar y Activar**

🎉 **¡Listo!** Ahora cada vez que recibas un email con "Factura" en el asunto y un PDF adjunto, se procesará automáticamente.

## 🧪 Probar el Flujo

1. Envíate un email de prueba con un PDF de factura
2. Ve a **Logs** para ver el progreso
3. Deberías recibir un email con los datos extraídos

## 📚 Próximos Pasos

Ahora que has completado tus primeras automatizaciones, puedes explorar:

### Transformación de Datos (ETL)
- [Guía de Usuario ETL](ETL_USER_GUIDE.md)
- Transforma archivos Excel, CSV, JSON entre diferentes formatos
- Usa lenguaje natural para definir transformaciones

### Automatización Web (RPA)
- [Manual de Usuario: RPA](functional/user_manual_client.md#3-automatización-de-procesos-rpa)
- Automatiza navegación en sitios web
- Descarga documentos de portales automáticamente

### Flujos Avanzados
- [Configuración de Flujos](functional/flows_configuration.md)
- Encadena múltiples tareas
- Integra con APIs externas
- Programa ejecuciones periódicas

### Generación de Gráficos e Informes
- [Features V4.0](technical/new_features_v4.md)
- Genera visualizaciones automáticamente
- Crea informes PDF profesionales

## 🆘 ¿Problemas?

Si encuentras algún error:

1. **Revisa los logs**: Ve a **Logs** en la aplicación
2. **Consulta troubleshooting**: [Resolución de Problemas](troubleshooting.md)
3. **Contacta soporte**: Usa el botón "Pedir Ayuda al Partner" en la aplicación

## 💡 Consejos

- **Empieza simple**: Prueba primero con documentos sencillos antes de procesar lotes grandes
- **Revisa siempre**: Valida los resultados antes de publicar scripts en producción
- **Usa feedback**: Si un script no funciona bien, usa el botón "Regenerar" con comentarios específicos
- **Privacidad garantizada**: Todos tus datos se anonimizan automáticamente antes de enviarse a la IA

---

¿Listo para más? Consulta el [Manual de Usuario completo](functional/user_manual_client.md) o el [Índice de Documentación](README.md).

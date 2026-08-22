# Guía de Usuario: Transformación de Datos con IA (ETL)

El módulo ETL (Extract, Transform, Load) de AutomatIA permite transformar archivos de datos de forma inteligente utilizando instrucciones en lenguaje natural, sin necesidad de escribir código.

## 🚀 Características Principales

- **IA Generativa**: Convierte instrucciones ("eliminar duplicados", "convertir fechas") en código Python optimizado.
- **Inteligencia Automática**: El sistema utiliza automáticamente el modelo más adecuado (Tier 2 para generación, Tier 3 para supervisión).
- **Sandbox Seguro**: Ejecución aislada que garantiza que los datos nunca salen de tu infraestructura.
- **Aprendizaje**: Capacidad de guardar transformaciones exitosas como flujos reutilizables.

## 📝 Flujo de Trabajo (Wizard)

El proceso se realiza en 5 pasos sencillos:

### 1. Carga de Datos (Upload)
Arrastra tu archivo origen al área de carga. El sistema detectará automáticamente el formato y mostrará una vista previa de las primeras 10 filas.

**Formatos soportados:**
- `.csv`, `.xlsx`, `.xls`
- `.json`, `.xml`, `.parquet`

### 2. Especificación (¿Qué quieres hacer?)
Define cómo quieres transformar los datos. Tienes 3 modos:

- **Descripción (Texto)**: Escribe instrucciones simples.
  > *Ejemplo: "Renombrar 'Columna1' a 'Nombre', eliminar filas vacías y convertir la columna 'Fecha' a formato ISO 8601."*
- **Ejemplo**: Sube un archivo con el formato final deseado. La IA deducirá la transformación necesaria.
- **Esquema (Avanzado)**: Pega un esquema JSON que defina la estructura de salida.

### 3. Configuración
Ajusta parámetros opcionales:
- **Opciones Rápidas**:
  - [x] Eliminar duplicados
  - [x] Normalizar nombres (snake_case)

### 4. Generación y Validación
El sistema generará un script de transformación.
- **Revisar**: Puedes ver el código Python generado.
- **Preview**: Se ejecuta una simulación sobre una muestra de datos.
- **Feedback**: Si el resultado no es el esperado, escribe una corrección ("La fecha sigue en formato incorrecto") y regenera el script.

### 5. Resultados
Una vez validado, se procesa el archivo completo.
- **Descargar**: Obtén el archivo transformado.
- **Guardar como Flujo**: Si vas a repetir esta tarea periódicamente, guárdala como un Flujo para automatizarla.

## 🔄 Integración con Flujos

Al guardar una transformación como Flujo:
1. Aparecerá en el menú **Flujos**.
2. Podrás ejecutarla programáticamente o integrarla en pipelines más complejos (ej. Email -> ETL -> ERP).

## ⚠️ Limitaciones y Seguridad

- **Privacidad**: Los datos completos NO se envían a la IA. Solo se envían metadatos (nombres de columnas) y una pequeña muestra anonimizada para generar el script.
- **Tamaño**: Para archivos muy grandes (>1GB), se recomienda usar el formato Parquet.

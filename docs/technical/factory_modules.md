# Módulos de Generación (Factories)

Las "Factories" son los componentes del Brain que transforman las solicitudes del usuario en scripts ejecutables. Se basan en el principio de metaprogramación asistida por IA.

## 1. Núcleo Cortex (`cortex.py`)
El motor central de razonamiento que orquesta las diferentes estrategias de generación.
- **Validación de Prompt**: Asegura que la solicitud cumple con los requisitos mínimos de contexto.
- **Inyección de Templates**: Selecciona el "System Prompt" adecuado según el tipo de automatismo (PDF, ETL, RPA).
- **Control de Salida**: Valida que la respuesta de la IA sea código Python ejecutable y no solo texto explicativo.

## 2. Estrategias de Extracción (`extraction_strategies.py`)

### PDFFactory
Especializada en la extracción de datos desde documentos estructurados y semi-estructurados.
- **Análisis de Layout**: Utiliza metadatos del PDF para entender filas, columnas y tablas.
- **Generación orientada a Pandas**: El script resultante utiliza intensivamente `pandas` y `PyMuPDF` para una extracción determinista.

### ETLFactory
Transforma datos entre diferentes formatos (CSV a SQL, Excel a JSON, etc.).
- **Inferencia de Esquema**: Analiza muestras de datos anonimizados para detectar tipos y relaciones.
- **Scripts de Transformación**: Genera funciones de limpieza y remapping personalizadas para el flujo de trabajo del cliente.

### NavigationFactory (RPA)
Convierte descripciones de lenguaje natural en scripts de Playwright.
- **Resiliencia de Selectores**: Genera selectores basados en múltiples atributos (texto, ID, roles ARIA) para evitar fallos por cambios menores en el DOM.
- **Modo Headless**: Diseñado para ejecución desatendida en el Client Node.

### CustomScriptFactory (`script_generator_service.py`)
Genera scripts Python personalizados para tareas arbitrarias definidas por el usuario en lenguaje natural.

**Ubicación**: `client_app/app/services/script_generator_service.py`

**Características**:
- **Input**: Descripción en lenguaje natural de la tarea deseada
- **Proceso**:
  1. Anonimiza el prompt del usuario
  2. Opcionalmente solicita clarificaciones si el prompt es ambiguo
  3. Envía al Brain para generar script Python genérico
  4. Valida el script generado con SecurityAuditor
  5. Permite refinamiento iterativo con feedback del usuario
- **Output**: Script Python ejecutable con librerías permitidas
- **Tipos de salida**: Archivo, texto, DataFrame

**Wizard de Usuario** (`custom_script_page.py`):
- **Fase 1 - Descripción**: Usuario describe la tarea
- **Fase 2 - Clarificación** (opcional): Responde preguntas de la IA
- **Fase 3 - Generación**: IA genera el script
- **Fase 4 - Prueba**: Usuario ejecuta y valida resultados
- **Fase 5 - Refinamiento**: Feedback iterativo (máx 5 iteraciones)

**Ejemplo de uso**:
```python
from client_app.app.services.script_generator_service import script_generator_service

# Generar script
result = await script_generator_service.generate_script(
    user_prompt="Lee un CSV, filtra filas donde edad > 18, y guarda resultado",
    output_type="file",
    clarifications={"q1": "eliminar_nulos"}
)

print(result['code'])
print(result['description'])
print(result['required_libraries'])
```

**Refinamiento con feedback**:
```python
# Si el resultado no es correcto
refined = await script_generator_service.refine_script(
    original_code=result['code'],
    user_feedback="El filtro debe ser edad >= 18, no solo >",
    error_message=None,
    execution_result=None
)
```

**Integración con ClarificationService**:
El CustomScriptFactory es el principal consumidor del ClarificationService, solicitando automáticamente preguntas cuando el prompt es ambiguo.

**Seguridad**:
- Anonimización obligatoria del prompt antes de enviar al Brain
- Validación AST del script generado
- Ejecución en sandbox con whitelist de librerías
- Máximo 5 iteraciones de refinamiento antes de escalar al Partner

## 3. Generación de Informes y Gráficos (V4.0)

### GraphicsFactory (`graphics_factory.py`)
Genera visualizaciones de datos automáticamente usando lenguaje natural.

**Ubicación**: `client_app/app/modules/factory/graphics_factory.py`

**Características**:
- **Input**: DataFrame + descripción en lenguaje natural (ej: "Gráfico de barras de ventas por mes")
- **Proceso**: 
  1. Extrae metadatos del DataFrame (columnas, tipos, muestra)
  2. Anonimiza etiquetas sensibles
  3. Envía al Brain para generar script matplotlib/seaborn
  4. Ejecuta script en sandbox con whitelist ampliada
- **Output**: Imagen PNG/SVG/PDF
- **Librerías**: matplotlib, seaborn (backend 'Agg' para entornos sin GUI)

**Ejemplo de script generado**:
```python
import matplotlib.pyplot as plt
import pandas as pd

def generate_chart(df: pd.DataFrame) -> str:
    plt.figure(figsize=(10, 6))
    df.plot(kind='bar', x='mes', y='ventas')
    plt.title('Ventas Mensuales')
    plt.xlabel('Mes')
    plt.ylabel('Ventas (€)')
    output_path = 'chart.png'
    plt.savefig(output_path)
    return output_path
```

**Seguridad**: Las etiquetas y leyendas se anonimizan antes de generar para proteger privacidad.

### ReportFactory (`report_factory.py`)
Compone informes PDF o HTML profesionales combinando datos, gráficos y texto.

**Ubicación**: `client_app/app/modules/factory/report_factory.py`

**Backends Soportados**:

1. **ReportLab (Nativo)** - Recomendado para producción
   - Rápido (3-5x más rápido que WeasyPrint)
   - Sin dependencias externas (no requiere GTK+3)
   - Control total del layout
   - Menor consumo de memoria

2. **HTML + Playwright (Opcional)** - Para prototipos
   - Editable en navegador
   - Diseño flexible con CSS
   - Previsualización interactiva

**Características**:
- **Plantillas Reutilizables**: Define templates y reutiliza
- **Secciones Dinámicas**: Texto, tablas, imágenes, gráficos
- **Estilos Profesionales**: Encabezados, pies de página, numeración
- **Integración**: Combina resultados de extracciones y gráficos

**Ejemplo de especificación**:
```python
report_spec = {
    "title": "Informe Mensual",
    "sections": [
        {"type": "text", "content": "Resumen ejecutivo..."},
        {"type": "table", "data": df_ventas},
        {"type": "chart", "chart_path": "ventas.png"}
    ]
}
```

**Migración de WeasyPrint**: La V4.0 migra a ReportLab como backend principal para eliminar dependencias de GTK+3 y mejorar rendimiento. Ver `migracion_reportlab.md` para más detalles.

## 4. Integración con ClarificationService

Todas las factories pueden integrarse con el **ClarificationService** para formular preguntas antes de generar código cuando la solicitud es ambigua. Ver [Features V4.0](new_features_v4.md) para más información.

# Módulo: Generador de Informes (Report Builder)

AutomatIA incluye este **Procesador Final** encargado de componer documentos HTML o PDFs complejos amalgamando datos tabulares, cuadros de texto libre, bucles estadísticos y metadatos generados en etapas anteriores del Flujo.

## Funcionamiento Manual

Desde la interfaz visual lateral de "Maquetación", el usuario va añadiendo piezas o "Bloques" de informe de arriba a abajo.
- **Header**: Títulos descriptivos grandes.
- **Markdown / Text**: Bloques de texto libre explicativo compatibles con variables inyectadas `{{...}}`.
- **Table**: Renderiza DataFrames o listas planas en cuadrículas legibles.
- **Chart**: Incorpora una Gráfica previamente generada por el módulo *Graphics*.
- **Metrics / KPI**: Bloques numéricos resaltados.
- **HTML Custom**: Código embebido manual.

## Funcionamiento con IA (Copiloto Activo)

Esta acción SÍ soporta **configuración automática vía IA**. Tu labor como Inteligencia Artificial es facilitar, componer y sugerirle las estructuras "Block" al usuario.

**Ejemplos de comandos a sugerir:**
- "Pídeme: 'Móntame una cabecera para un informe mensual y una tabla con los resultados'"
- "Dime: 'Añade un texto introductorio en negrita y un resumen numérico abajo'"

**Formato para propuestas generativas (ESTRICTO):**
Al igual que en ETL, cuando redactes respuestas sugiriendo la incorporación un Bloque de Reporte al diseñador del usuario, puedes enviar una lista enumerada (array format) usando la clave EXACTA `[REPORT_BLOCK]` para que la plataforma la detecte y cree de forma dinámica un botón clicable para el usuario que renderice en el navegador el diseño sugerido.

1. [REPORT_BLOCK] header - Creación cabecera principal {"type": "header", "content": "Informe de Cierre Contable", "level": 1}
2. [REPORT_BLOCK] markdown - Texto descriptivo inicial {"type": "markdown", "content": "A continuación detallamos el **volumen** extractado de las facturas..."}
3. [REPORT_BLOCK] table - Bloque para volcar tabla {"type": "table", "data_source": "dataset_limpio.data"}

<help_config>
### Cómo configurar
1. Añade bloques usando el panel lateral. Un bloque puede ser un título, texto libre, una tabla con datos o una imagen.
2. Rellena el contenido de los bloques interactivamente en la interfaz de diseño.
3. Para mostrar datos calculados por el flujo, usa la sintaxis de dobles llaves `{{variable_a_mostrar}}` en los bloques de texto.
</help_config>

<help_example>
### Ejemplo Rápido
Supón que quieres enviar un reporte del cierre contable. Puedes hacer un diseño así:
- **Header**: "Cierre Mensual"
- **Markdown**: "El total ingresado este mes es de **{{total_ingresos}}** euros, desglosado en la siguiente tabla:"
- **Table**: `{{tabla_ingresos}}`

Este nodo convertirá esa plantilla mixta en un documento final (HTML/PDF) legible y ordenado.
</help_example>

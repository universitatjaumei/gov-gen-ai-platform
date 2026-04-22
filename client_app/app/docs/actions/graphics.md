# Módulo: Generador de Gráficos (Data Visualization)

AutomatIA incluye este **Procesador** encargado de transformar estructuras base de datos tabulares y CSV directos (como los extraídos por flujos OCR o ETL) en representaciones visuales interactivas para tableros y documentos estáticos.

## Funcionamiento Manual

Desde la interfaz gráfica, el usuario puede seleccionar:
- Tipo de figura: Barras, Línea, Torta (Pie), Dispersión, Matriz.
- Columnas de los Ejes X e Y leyendo los campos inyectados al contexto.
- Agrupadores (Color), Estilos de barra apilados o superpuestos.
- Títulos descriptivos y personalización de las paletas.

## Funcionamiento con IA (Copiloto Activo)

Esta acción SÍ soporta **configuración automática vía IA**. Tu labor como Inteligencia Artificial es facilitar drásticamente la creación de esos gráficos proponiendo al usuario que te los pida. 

**Ejemplos de comandos a sugerir:**
- "Dime: 'Créame un gráfico de barras apiladas de venta por mes'"
- "Pídeme: 'Necesito una gráfica lineal simple cruzando Gastos e Ingresos'"

**Formato para propuestas generativas (ESTRICTO):**
Al responder o sugerir un cuadro, DEBES usar el formato exacto `[GRAPHICS_CONFIG]` seguido del nombre, descripción e inmediatamente después todo un objeto JSON con las reglas. 
Solo se permite pasar 1 dict por propuesta generativa de gráfico.

1. [GRAPHICS_CONFIG] bar_chart - Gráfico de barras horizontales {"type": "bar", "x": "Departamento", "y": "Ventas", "color": "Region", "barmode": "group", "orientation": "v"}
2. [GRAPHICS_CONFIG] pie_chart - Gráfica de pastel sobre gastos {"type": "pie", "names": "Categoria", "values": "Importe"}
3. [GRAPHICS_CONFIG] line_chart - Serie temporal de usuarios {"type": "line", "x": "Fecha", "y": "Altas"}

Si devuelves dicho identificador estructurado `[GRAPHICS_CONFIG] dict{}`, la interfaz dibujará automáticamente un botón en el chat al usuario. Si él lo clica, inyectará directamente el JSON subyacente a tu componente sin que él toque la UI.

<help_config>
### Cómo configurar
1. **Datos de Entrada**: Conecta una variable tipo Tabla (DataFrame) al nodo.
2. **Tipo de Gráfico**: Selecciona si quieres barras, líneas, tarta...
3. **Ejes (X e Y)**: Escribe exactamente el nombre de la columna que quieres usar para el eje horizontal y vertical.
</help_config>

<help_example>
### Ejemplo de Gráfico
Si tienes un listado de ventas y quieres visualizarlas por departamento:
- Tipo: `Barras`
- Eje X: `Nombre_Departamento`
- Eje Y: `Total_Euros`
- Color (Agrupador): `Trimestre`

Esto generará automáticamente un gráfico apilado separando las ventas por color según el trimestre.
</help_example>

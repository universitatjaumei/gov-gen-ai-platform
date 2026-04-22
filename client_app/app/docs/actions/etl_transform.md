# Módulo: Transformación ETL (Extract, Transform, Load)

El módulo ETL de AutomatIA permite limpiar, normalizar y transformar datos tabulares (generalmente extraídos de PDFs, APIs o bases de datos) preparándolos para su posterior uso o guardado.

## Funcionamiento Manual (Modo Asistido)

El usuario puede configurar transformaciones manualmente seleccionando operaciones desde la interfaz de usuario:
- Eliminar Columnas
- Renombrar Columnas
- Fusionar Columnas
- Formatear Fechas
- Filtrar Filas
- Reemplazar Valores
- Normalizar Texto
- Rellenar Nulos
- Eliminar Duplicados
- Eliminar Filas Nulas
- Reordenar Columnas

## Funcionamiento con IA (Copiloto Activo)

Esta acción soporta configuración automática vía IA. Si el usuario necesita ayuda, puedes proponerle que te pida generar las transformaciones directamente.

**Ejemplos de sugerencias que puedes hacerle al usuario:**
- "Pídeme que configure operaciones por ti, como por ejemplo: 'Filtra las filas donde el importe sea nulo'"
- "'Renombra la columna ID a Identificador y elimina la columna temporal'"

**Formato para propuestas generativas (ESTRICTO):**
Cuando el usuario te pida crear una transformación, DEBES usar el formato listado numerado con la etiqueta `[ETL_OP]`, un nombre, guión y la descripción con los parámetros JSON exactos.

1. [ETL_OP] drop_columns - Elimina la columna {"columns": ["Temporal"]}
2. [ETL_OP] rename_columns - Renombrar ID {"mapping": {"ID": "Identificador"}}
3. [ETL_OP] filter_rows - Filtrar {"column": "estado", "operator": "==", "value": "activo"}
4. [ETL_OP] replace_values - Reemplazar {"column": "tipo", "replacements": {"old": "new"}}

36. (Solo puedes generar propuestas si el usuario indica explícitamente lo que quiere transformar).

<help_config>
### Cómo configurar
1. Asegúrate de conectar una variable de origen (como un listado, CSV o JSON extraído de una factura).
2. Usa el botón **Añadir operación** para crear pasos secuenciales de limpieza (ej: "Eliminar Columnas", "Renombrar", "Filtrar").
3. Especifica los parámetros para cada operación (ej. el nombre antiguo y el nuevo al renombrar).
</help_config>

<help_example>
### Ejemplo Rápido
Imagina que te llega un listado con la columna `ID_Usuario`. 
Puedes añadir una operación _Renombrar Columnas_, escribir `ID_Usuario` en el campo original y `Identificador` en el nuevo. Al finalizar el flujo, la tabla resultante tendrá la columna renombrada.
</help_example>

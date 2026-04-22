# Módulo: Extracción PDF (Inteligente y Zonal)

Este es un componente central de AutomatIA clasificado como **Procesador**, diseñado para leer documentos `.pdf`, que provengan de pasos anteriores y devolver los datos limpios y estructurados.

## Funcionamiento Manual (Modo Asistido)

El flujo de diseño consta de:
1. **Subida del documento maestro (Ejemplo)**: El usuario debe subir un archivo de muestra (factura tipo, DNI tipo, nómina o registro clínico) de forma segura.
2. **Definición de Campos**: El usuario indicará explícitamente qué conceptos quiere que la magia extraiga (por ejemplo, el campo "Total a Pagar" convertido a tipo "number" y el campo "Fecha de Emisión" mapeado a tipo "date").
3. **Elaboración del prompt base**: AutomatIA usará las definiciones para guiar la extracción. El usuario también puede pedir al sistema que cree instrucciones lógicas específicas para ese documento.
4. **Validación, Generación de Motor y Sello**: Tras iterar el diseño, se validan los resultados y se publica el átomo de tipo "Extractor" en la biblioteca.

## Comportamiento del Copiloto (IA)

En esta pantalla, tu labor principal es ayudar al usuario a plantear el esquema de extracciones. Por ejemplo, ante la pregunta "¿Cómo configuro un extractor de multas de tráfico?", explícale detalladamente qué campos le recomiendas diseñar (Fecha Infracción, Vehículo, Coste, Culpable, etc.).
No emites código directamente a la pantalla de la izquierda. Aporta conocimiento consultivo y ejemplos (prompts).

<help_config>
### Cómo configurar
1. **Documento Maestro**: Sube un documento de ejemplo para que el sistema tenga contexto (PDF, PNG, etc).
2. **Campos a Extraer**: Define los nombres exactos y los tipos de datos de los campos que quieres sacar del documento.
3. **Prompt de Extracción**: Escribe instrucciones adionales si quieres guiar a la IA sobre cómo interpretar o encontrar ciertos valores. 
4. **Validar y Publicar**: Prueba con el motor y publicalo cuando el JSON saliente sea correcto.
</help_config>

<help_example>
### Ejemplo de Extractor de Facturas
Si quieres extraer información de facturas de proveedores:
1. Sube un PDF de una factura cualquiera.
2. Crea los campos: `num_factura` (texto), `fecha_emision` (fecha), `total_con_iva` (número).
3. (Opcional) Indica en el prompt: "Asegúrate de no confundir la fecha de vencimiento con la de emisión".

Al conectarlo en un flujo, AutomatIA leerá el PDF entrante y te devolverá esos 3 campos estructurados para insertarlos donde quieras.
</help_example>

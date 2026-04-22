# Módulo: Inserción SQL

Este componente clasificado como **Salida (Output)** permite persistir datos generados en tus flujos de validación y extracción hacia una base de datos externa mediante cláusulas INSERT o UPDATE.

## Compatibilidad
Es compatible con PostgreSQL, MySQL y SQL Server mediante las credenciales globales del módulo (Connection Registry).

<help_config>
### Cómo configurar
1. **Credenciales**: Escoge la conexión segura en el desplegable. 
2. **Operación**: Selecciona entre Insertar nueva fila o Actualizar filas existentes (Upsert).
3. **Tabla Objetivo**: Escribe el nombre de la tabla de tu base de datos destino (`ventas_q1`).
4. **Mapeo JSON/Diccionario**: Pásale un diccionario dinámico recolectado en los anteriores pasos y AutomatIA creará dinámicamente el `INSERT INTO tabla (col1, col2) VALUES (:col1, :col2)`.
</help_config>

<help_example>
### Ejemplo de Integración
Imagina que has extraído un PDF y tienes la variable generada con `Monto` y `Fecha_Emision`. 
Simplemente enlaza ese diccionario extraído como Payload al nodo SQL Insert, nombra la tabla final (`facturas_validadas`), y nosotros prepararemos un cursor nativo insertando la fila sin riesgo de inyecciones, de forma rápida y escalable.
</help_example>

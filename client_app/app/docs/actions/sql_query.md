# Módulo: Consulta SQL

Este componente permite ejecutar peticiones **SELECT** sobre bases de datos configuradas en la plataforma, extrayendo conjuntos de datos (filas y columnas) para el proceso.

## Funcionamiento
Se conecta utilizando credenciales previamente almacenadas (Connection Registry de la plataforma) a entornos como PostgreSQL, MySQL o SQL Server.

<help_config>
### Cómo configurar
1. **Credenciales**: Tienes que crear y probar primero la conexión a la base de datos en el Administrador de Conexiones.
2. **Consulta SQL**: Escribe la sentencia exacta que devolverá datos. Ej: `SELECT * FROM facturas WHERE fecha > :fecha_limite`.
3. **Pausas y Límites**: Agrega paginación si traes millones de filas. 
</help_config>

<help_example>
### Ejemplo de Recuperación
En el campo SQL puedes inyectar las variables del flujo de la siguiente forma usando la sintaxis de SQLAlchemy (dos puntos `:`):
```sql
SELECT nombre, apellidos 
FROM clientes 
WHERE status = 'active'
AND fecha_alta > :fecha
```
AutomatIA se encarga de rellenar esos datos prevenidos por inyecciones SQL que le mapees en la UI.
</help_example>

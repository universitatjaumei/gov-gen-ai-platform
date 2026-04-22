# Módulo: Herramientas PDF

Este componente, clasificado como **Procesador**, ofrece un conjunto de utilidades nativas para manipular archivos PDF desde los flujos de automatidad.

## Funciones disponibles
- Extraer texto bruto (sin inteligencia artificial, puramente capas de texto embebidas).
- Unir (Merge) múltiples archivos PDF.
- Dividir (Split) PDFs por páginas o por rangos.
- Cifrar o descifrar archivos con contraseñas.
- Extraer imágenes incrustadas.

<help_config>
### Cómo configurar
1. **Modo de Operación**: Selecciona en el desplegable qué deseas hacer (Ej: "Unir PDFs", "Extraer Texto", "Extraer Imágenes").
2. **Parámetros**: Dependiendo del modo, te aparecerán distintas opciones (por ejemplo, rangos de páginas para el modo "Dividir", o una contraseña para "Cifrar").
3. **Variables de Entrada**: Asegúrate de mapear en el panel de Flujos qué variables contienen el archivo (o la lista de archivos) a procesar.
</help_config>

<help_example>
### Ejemplo de Utilidades PDF
Para unir todos los adjuntos de un correo mensual:
- Escoge la acción "Unir PDFs (Merge)".
- Pasa la lista de rutas (`files`) generada por el Email Scanner.
- El módulo procesará esos N archivos y devolverá la nueva ruta de salida consolidada.
</help_example>

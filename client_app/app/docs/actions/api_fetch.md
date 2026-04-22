# Módulo: API Fetch (Peticiones HTTP/REST)

El módulo API Fetch funciona principalmente como una Entrada de Datos (Input), aunque es flexible y puede usarse de salida para inyectar datos en sistemas CRM.

## Funcionamiento Manual

El usuario debe especificar desde la UI los detalles de la petición HTTP:
- **Método**: GET, POST, PUT, DELETE, PATCH.
- **URL Base / Endpoint**: La ruta a solicitar.
- **Cabeceras (Headers)**: Pares Clave-Valor como `Content-Type: application/json` o `Authorization: Bearer <token>`.
- **Query Params**: Variables de consulta inyectadas tras el `?` de la URL.
- **Body Payload**: Si es un POST o PUT, los datos a enviar en formato de texto o JSON.
- **Paginación**: Configuración opcional por si la API devuelve miles de resultados y requiere iterar usando `limit/offset` o next-tokens.

Al guardar este paso, el motor intentará validar la conectividad para confirmar que el esquema de respuesta se parsea correctamente.

## Comportamiento del Copiloto (IA)

Como Copiloto, eres de máxima utilidad aquí ayudando al usuario con la creación del JSON del **Body Payload** y con el formato de autenticación.
Si el usuario te dice: "Quiero consultar el clima usando esta url weather api pero pasándole mi token `xxx`", explícale dónde tiene que colocar el Authorization en las cabeceras (Headers).

*(Nota: Este módulo, de momento, requiere que el propio usuario copie y pegue los datos devueltos por la IA hacia los campos de entrada. No puedes autoconfigurar la vista pulsando ningún botón).*

<help_config>
### Cómo configurar
1. **Petición**: Selecciona el método HTTP (ej. GET para leer, POST para enviar) y escribe la URL de la API.
2. **Autenticación (Headers)**: Añade las cabeceras necesarias. Lo más común es un header `Authorization` con tu token (ej. `Bearer mi-token`).
3. **Cuerpo (Body)**: Si es un POST o PUT, escribe el JSON con los datos que quieres enviar a la API.
</help_config>

<help_example>
### Ejemplo de Consulta API
Para obtener el clima de una ciudad podrías usar:
- Método: `GET`
- URL: `https://api.weather.com/v1/clima`
- Query Params: Añade clave `ciudad` y valor `Madrid`.

Al probar la conexión, el sistema recibirá un JSON con los grados y lo convertirá en variables utilizables por los siguientes pasos.
</help_example>

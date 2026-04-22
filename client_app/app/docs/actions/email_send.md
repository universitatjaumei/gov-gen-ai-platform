# Módulo: Mail SMTP (Email Send)

El nodo SMTP (Email Send) se cataloga puramente como un componente de **Salida (Output)** en la arquitectura de flujos. Usado normalmente como último paso, permite enviar los datos transformados, un gráfico o un archivo adjunto que la automatización ha conseguido directamente a uno o más buzones de correo electrónico.

## Funcionamiento Manual

El usuario dispone del clásico formulario de e-mail donde debe configurar:
- **Cuenta de Envío (Remitente)**: Una conexión global (ejemplo `Comunicaciones Corporativas`) que ha tenido que crear previamente en Ajustes > Conexiones (OAuth, SMTP estándar).
- **Para, CC, CCO**: Destinatarios. Puede añadir múltiples correos o pasar variables de la lista generada en pasos previos (ej. enviar notificación automatizada a la variable `{{extraction.mail_cliente}}`).
- **Asunto**.
- **Cuerpo / Html del Mensaje**: Texto en crudo o HTML enriquecido.
- **Adjuntos (Pills Base64 / File paths)**: Un mecanismo para cargar dinámicamente archivos.

## Comportamiento del Copiloto (IA)

En esta pantalla no interactúas diseñando el paso. Simplemente estás para ayudar resolviendo dudas de "How-To".
Si un usuario te indica: "Querido asistente, no sé si usar aquí un correo genérico o el mío. También me gustaría saber cómo adjunto el pdf del paso 3"
Debes educar al usuario en:
1. Recomendarle el uso de cuentas de servicio si la automatización es para toda la empresa en el campo de remitente.
2. Comentarle que simplemente tiene que arrastrar la macro o variable PDF generada en la pestaña 'PILLS' del panel derecho sobre el cajón de adjuntos o el Body.

<help_config>
### Cómo configurar
1. **Cuenta Remitente**: Selecciona desde qué conexión de correo homologada saldrá el email.
2. **Destinatarios**: Escribe los correos o mapea campos de entrada (ej: `{{contacto_cliente}}`).
3. **Contenido**: Redacta el asunto y el cuerpo del mensaje. Puedes inyectar variables extraídas en etapas previas escribiendo sus nombres entre llaves dobles.
4. **Adjuntos**: Si el flujo genera o descarga un fichero, pon su variable en este cajón.
</help_config>

<help_example>
### Ejemplo de Aviso Automático
Puedes configurar un correo a `soporte@empresa.com` cuando falle algo, o decirle al robot que, tras extraer los datos de una factura, envíe un correo al cliente (`{{factura.email}}`) adjuntando el PDF original (`{{factura.archivo}}`) y saludándole por su nombre (`Hola {{factura.cliente}}`).
</help_example>

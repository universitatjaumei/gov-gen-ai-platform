# Manual de Usuario: Client Node

Bienvenido a AutomatIA. Este manual te guiará en el uso diario de la plataforma para automatizar tus tareas de procesamiento de datos.

## 1. Primeros Pasos
Al abrir la aplicación, verás el **Dashboard**, donde se resumen tus ejecuciones recientes y el estado de tus conectores.

## 2. Automatizaciones de Documentos (Extracción)
Para extraer datos de tus PDFs o imágenes:
1.  Ve a la sección **Documentos**.
2.  **Carga** uno o varios archivos de ejemplo.
3.  **Define el esquema**: Describe qué datos necesitas (ej: "Fecha de factura, Base imponible, CIF").
4.  **Genera y Prueba**: El sistema creará un script automáticamente. Verifica que los resultados sean correctos.
5.  **Publica**: Una vez aprobado, el script estará listo para usarse en flujos automáticos.

## 3. Automatización de Procesos (RPA)
Para automatizar tareas en la web:
1.  Ve a la sección **RPA**.
2.  Describe la tarea en lenguaje natural (ej: "Entra en la Sede Electrónica y descarga las notificaciones pendientes").
3.  **Graba el flujo**: Sigue los pasos interactivamente para que la IA aprenda los selectores.
4.  **Validación**: Revisa el script generado y asígnalo a un horario o flujo.

## 4. Conectores (Connections)
Gestiona cómo entran y salen los datos:
- **Carpetas**: Configura monitores que detecten automáticamente nuevos archivos en tu PC o servidor local.
- **Email**: Configura una cuenta IMAP para procesar adjuntos recibidos por correo electrónico.
- **API**: Configura endpoints externos para enviar o recibir datos estructurados.

## 5. Privacidad y Seguridad
En la pestaña **Anonimizador**, puedes realizar pruebas de cómo el sistema protege tus datos sensibles antes de enviarlos a la IA. Recuerda que la anonimización es automática y tú no necesitas hacer nada para cumplir con el RGPD.

## 6. Soporte y Escalado
Si una automatización falla repetidamente:
- Revisa los **Logs** para entender el error.
- Utiliza la opción **Pedir Ayuda al Partner** para que un técnico revise tu caso. Se enviará una muestra anonimizada de tus datos para que el soporte pueda corregir el script sin ver tu información real.

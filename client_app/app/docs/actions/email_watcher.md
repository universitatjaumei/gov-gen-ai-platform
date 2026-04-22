# Módulo: Monitor de Email (Email Watcher)

Este es un **Disparador (Trigger)** diseñado para activar flujos de trabajo cada vez que llega un nuevo correo electrónico a un buzón específico bajo los criterios definidos. El evento de entrada arrastra automáticamente tanto el cuerpo del correo como sus adjuntos para su consumo en cascada.

## Diferencia con Email Scan
El monitor "se queda escuchando" o revisando periódicamente la cuenta actuando como un gatillo. No se ubica *dentro* de un flujo, sino *antes*, a la cabeza de la orquestación.

<help_config>
### Cómo configurar
1. **Cuenta (SMTP/IMAP)**: Asocia la cuenta de correo a vigilar.
2. **Intervalo**: Establece la frecuencia de sondeo (5 minutos, 1 hora, etc.).
3. **Reglas**: Puedes limitar la ejecución del flujo a ciertos Asuntos (`*Factura*`), Remitentes específicos (`proveedor@dominio.com`) o aquellos que tengan adjuntos.
4. **Disponibilidad para flujos**: Una vez guardes el evento, ve a la pestaña de Diseñador de Flujos y escógelo como tu bloque inicial (Evento de Activación).
</help_config>

<help_example>
### Ejemplo de Inicio vía Mail
Tu flujo hace OCR y extrae facturas.
Configuras el Monitor de Email filtrando con `Asunto contiene: Nueva factura` y `Requiere Adjunto: Sí`.
A las 08:31 entra el correo de tu proveedor. El Monitor arranca y le pasa a tu Flujo de OCR directamente el PDF recién descargado, procesándose antes de las 08:32 sin intervención manual.
</help_example>

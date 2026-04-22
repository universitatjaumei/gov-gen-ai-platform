# Módulo: Escáner de Emails (Input)

A diferencia del Email Watcher (que es un disparador y actúa en tiempo real), el Escáner de Emails actúa dentro de un paso del flujo cuando le toca ejecutarse.
Entra al buzón indicado (IMAP), busca correos y se descarga sus datos (y adjuntos) de forma pasiva, pasándoselos al resto del flujo como una lista a iterar.

<help_config>
### Cómo configurar
1. **Credenciales**: Tienes que tener el acceso IMAP autorizado previamente en Administrador de Conexiones de Mail.
2. **Criterios de Búsqueda**: Selecciona la carpeta (ej. INBOX o Facturas), si son leídos/no leídos, fechas desde/hasta y/o quién es el remitente o Asunto requerido (`factura*`).
3. **Bandera de Post-procesamiento**: Opcionalmente, puedes decirle al módulo que los marque "como leídos" o los mueva a otra carpeta automáticamente después de extraer la información para evitar descargarlos doble la próxima vez.
</help_config>

<help_example>
### Ejemplo de Bandeja de Entrada Múltiple
Si lo configuras a las 9:00 AM conectando una cuenta IMAP buscando correos NO leídos con el asunto "Nómina":
Este paso descargará 15 nóminas y listará 15 objetos al siguiente bloque (un For-Each o un Extractor). 
Tu automatización recorrerá esos 15 sin importar si llegaron a las 2:00 o a las 8:00.
</help_example>

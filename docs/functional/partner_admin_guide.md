# Guía de Administración para Partners

Como Partner de AutomatIA, eres responsable de la gestión de tus clientes, sus licencias y de proporcionar soporte técnico de nivel 2.

## 1. Panel de Control Partner
Accede a `/partner/dashboard` para ver un resumen de:
- Consumo total de tokens de todos tus clientes.
- Estado de las licencias (activas, por expirar, agotadas).
- Tareas de soporte pendientes (scripts escalados).

## 2. Gestión de Clientes y Licencias
En el apartado **Clientes**, puedes:
- Crear nuevas instancias de cliente.
- Asignar **Tiers de Consumo**: Define límites mensuales de tokens para controlar costes.
- **Generar License Keys**: Claves necesarias para activar el Client Node en la infraestructura del cliente final.

## 3. Políticas de Seguridad Personalizadas
Puedes definir políticas específicas para cada cliente:
- **Whitelist de Dominios**: Qué webs puede navegar el RPA del cliente.
- **Whitelist de Librerías**: Qué módulos de Python están permitidos en el Sandbox de este cliente.
- **Configuración de Privacidad**: Nivel de restricción de las capturas de pantalla (Guard).

## 4. Soporte Técnico (Resolución de Scripts)
Cuando un cliente "escala" un problema:
1.  Verás una nueva tarea en tu **Cola de Soporte**.
2.  Descarga el **Paquete de Contexto**: Contiene el script fallido y una muestra de datos anonimizada.
3.  **Depuración Local**: Edita el script y pruébalo con la muestra.
4.  **Publicación Remota**: Envía la corrección al Client Node del cliente con un solo clic.

## 5. Facturación y Cobros
El panel de **Billing** te permite exportar informes de consumo detallados por cliente para tu propio sistema de facturación. AutomatIA te factura a ti por el total de tokens, y tú repercutes el coste según tu propio modelo de negocio.

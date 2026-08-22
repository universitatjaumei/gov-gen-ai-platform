# Manual de Usuario - Panel de Administración (Internal Tool)

Este documento describe el funcionamiento del nuevo Panel de Administración Server-Side (`/admin`), diseñado para la gestión de multitenancy, licencias y configuración de IA.

## 1. Acceso
El panel está disponible en la ruta `/admin` del servidor Brain.
Ejemplo local: `http://localhost:8080/admin`

## 2. Gestión de Partners
Pestaña **Partners**.
Permite dar de alta a integradores tecnológicos que revenderán la solución.

- **Crear Partner**: Pulsar "Nuevo Partner".
  - `ID Partner`: Identificador único interno (ej. `consultora_tic`).
  - `Créditos Iniciales`: Saldo para operaciones (opcional, se puede ajustar luego).
- **Ajustar Créditos**: Icono Billetera (Wallet).
  - Permite `Añadir` créditos al saldo actual o `Establecer` un valor absoluto.
  - El saldo se descuenta automáticamente con el uso de la API por parte de sus clientes.
- **Eliminar**: Solo posible si el Partner no tiene clientes asociados.

## 3. Gestión de Clientes y Licencias (Vista Jerárquica)
Pestaña **Clientes**.
Muestra la relación `Partner -> Client -> License`.

### Alta de Nuevo Cliente
El asistente (wizard) guía el proceso en 3 pasos:

1.  **Datos Básicos**: Asignar ID, Nombre y seleccionar el Partner asociado.
2.  **License Key (CRÍTICO)**:
    - Pulsar "Generar Key Segura" para obtener una API Key (formato `LIC-XXXX...`).
    - **IMPORTANTE**: Copiar la key inmediatamente. Se guardará hasheada (SHA256) y **no se podrá recuperar** después.
    - Si se pierde, se deberá generar una nueva licencia.
3.  **Configuración de Licencia**:
    - `Quota`: Tokens máximos permitidos.
    - `Valid Until`: Fecha de caducidad.

### Estados de Licencia
Colores visuales en la tabla:
- 🟢 **ACTIVE**: Licencia válida y con saldo.
- 🟠 **EXPIRING_SOON**: Caduca en menos de 15 días.
- 🔴 **EXPIRED**: Fecha de validez superada.
- 🔴 **QUOTA_EXCEEDED**: Consumo de tokens >= Cuota asignada.

## 4. Editor Avanzado de Prompts
Pestaña **System Prompts**.
Permite ajustar el comportamiento de la IA sin redesplegar código.

- **Lista (Izquierda)**: Seleccionar un prompt existente (ej. `sys_phase1_extraction`).
- **Editor (Derecha)**:
  - **Variables**: El sistema detecta automáticamente variables como `{texto_fitz}` o `{esquema_json}` y las muestra debajo del editor.
  - **Clonar**: Botón "Clonar Prompt". Crea una copia con sufijo `_copy` (ej. `sys_phase1_extraction_copy`). Útil para A/B testing o versiones v2.
  - **Guardar**: Persiste los cambios en la base de datos `ExtractionServiceConfig`.

## 5. Auditoría y Multitenancy
Todas las operaciones realizadas a través de la API v2 quedan registradas asociadas al `License ID` utilizado en los headers (`X-License-Key`).
El panel de **Licencias** (Vista de solo lectura) permite ver el consumo global en tiempo real.

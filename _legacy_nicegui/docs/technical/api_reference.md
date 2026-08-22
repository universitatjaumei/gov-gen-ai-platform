# Referencia de API y Comunicación

AutomatIA utiliza una arquitectura de servicios desacoplados donde el Client Node consume recursos del Brain mediante una API REST protegida.

## 1. Endpoints del Brain (Cloud)

### Autenticación y Licencia
- **POST `/auth/validate`**: Valida la `license_key` del cliente.
- **GET `/auth/policy`**: Recupera las políticas de seguridad asignadas al cliente/partner.

### Servicios de IA (Cortex)
- **POST `/ai/generate-script`**:
    - **Payload**: Tipo (PDF/ETL/RPA), contexto anonimizado, esquema destino.
    - **Response**: Código Python generado + `code_hash`.
- **POST `/ai/clarify`**: Solicita preguntas de clarificación si la petición es ambigua.

### Billing y Cuotas
- **GET `/billing/usage`**: Consulta el consumo actual de tokens y cuotas restantes.
- **POST `/billing/report-usage`**: El cliente informa del consumo tras una ejecución exitosa (validado mediante firma del servidor).

## 2. Comunicación Client-Brain

Toda la comunicación se realiza mediante el `BrainAPIClient` ubicado en `client_app/app/clients/brain_client.py`.

### Seguridad en el Transporte
- **HTTPS OBLIGATORIO**: Uso de TLS 1.3.
- **Headers de Seguridad**:
    - `X-License-Key`: Identificador único del cliente.
    - `X-Client-Version`: Para asegurar compatibilidad de los scripts generados.
    - `X-Signature`: Firma SHA256 para integridad de payloads críticos.

## 3. APIs Locales (Client Node)

Aunque el Client Node es principalmente una aplicación de escritorio, expone servicios internos:
- **`FolderWatcherService`**: API interna para registrar nuevos monitores de carpetas.
- **`MailWatcherService`**: Gestión de triggers basados en protocolos IMAP.
- **`WorkflowEngine API`**: Punto de entrada programático para ejecutar flujos de trabajo locales.

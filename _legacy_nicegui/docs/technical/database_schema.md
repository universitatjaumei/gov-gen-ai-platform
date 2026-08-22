# Diccionario de Datos (Esquema de BD)

AutomatIA utiliza dos bases de datos independientes para separar la lógica de negocio/facturación del procesamiento local.

## 1. Brain Server Database (`brain_server.db`)
Centraliza la gestión de cuentas, licencias y servicios de IA.

### Tablas Principales

| Tabla | Propósito | Campos Clave |
|-------|-----------|--------------|
| `PartnerAccount` | Cuentas de integradores/resellers. | `email`, `password_hash`, `credits_balance`, `role` |
| `ClientAccount` | Usuarios finales bajo un Partner. | `name`, `partner_id`, `license_key` |
| `License` | Control de validez y cuotas. | `client_id`, `expires_at`, `token_quota` |
| `SecurityPolicy` | Restricciones globales de seguridad. | `allowed_imports`, `timeout_limit`, `screenshot_mode` |
| `ExtractionServiceConfig` | Prompts de sistema para la IA. | `service_type`, `version`, `prompt_text` |
| `BillingRecord` | Historial de consumo de tokens. | `client_id`, `tokens_used`, `cost`, `timestamp` |

## 2. Client Local Database (`client_local.db`)
Almacena configuraciones locales y trazabilidad de ejecuciones.

### Tablas Principales

| Tabla | Propósito | Campos Clave |
|-------|-----------|--------------|
| `ServerConnection` | Configuración de conexión al Brain. | `brain_url`, `license_key`, `status` |
| `LocalCredentials` | Credenciales cifradas (Email, APIs). | `service`, `encrypted_data`, `created_at` |
| `FlowRegistry` | Definición de flujos de trabajo (pipelines). | `name`, `trigger_type`, `steps_config` (JSON) |
| `TrustedScript` | Scripts firmados listos para ejecución. | `name`, `code_hash`, `source_type`, `status` |
| `TaskLog` | Historial detallado de ejecuciones. | `execution_id`, `flow_id`, `step`, `status`, `logs` |
| `FolderWatcherConfig` | Centinelas de carpetas locales. | `path`, `pattern`, `recursive`, `action_flow_id` |
| `FolderWatcherState` | Tracking de archivos procesados. | `file_hash`, `last_processed_at` |

## Gestión de Migraciones
Ambas bases de datos utilizan `SQLAlchemy` como ORM. Las migraciones se gestionan de forma incremental asegurando compatibilidad hacia atrás entre versiones del Client Node y el Brain.

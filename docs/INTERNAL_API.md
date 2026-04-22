# DOCUMENTACIÓN API INTERNA (BRAIN)

> **Versión:** 2.0 (V4.0)  
> **Estado:** Draft  
> **Fecha:** 2026-01-27

---

## 1. INTRODUCCIÓN

Este documento define la interfaz técnica entre el **Client Node** (On-Premise) y **The Brain** (SaaS Cloud).
Actualmente, esta comunicación puede ocurrir mediante llamadas directas (en desarrollo) o HTTP (en producción).

**Arquitectura:**
- **Client Node:** Instancia local que procesa datos sensibles. NUNCA envía datos PII al Brain sin anonimizar.
- **Brain (Server):** Gestiona la inteligencia, modelos LLM, facturación y licencias.

**Reglas Clave:**
1. **Cliente sin Secretos:** El cliente nunca almacena API Keys de proveedores (OpenAI, Google).
2. **Gateway Único:** Todas las peticiones a modelos pasan por `AIBrainService`.
3. **Producción = HTTP:** El cliente debe usar `BrainAPIClient` (REST) en entorno productivo.

---

## 2. ESQUEMA DE DATOS (DB SERVIDOR)

Modelos principales alojados en `brain_server.db` (PostgreSQL/SQLite).

### 2.1. Jerarquía de Cuentas

#### `PartnerAccount`
Entidad integadora (B2B).
- `partner_id` (PK): Identificador único.
- `name`: Nombre comercial.
- `credits_balance`: Saldo de tokens disponible.
- `is_active`: Estado global.

#### `ClientAccount`
Cliente final (B2B2B).
- `client_id` (PK): UUID del cliente.
- `partner_id` (FK): Partner responsable.
- `license_key`: Hash SHA256 de la clave de licencia.

### 2.2. Licenciamiento

#### `License`
Control de quotas.
- `license_id` (PK): ID de la licencia.
- `client_id` (FK): Cliente asociado.
- `quota_tokens`: Límite de tokens asignado.
- `consumed_tokens`: Consumo acumulado.
- `valid_until`: Fecha de expiración.
- `status`: `ACTIVE`, `EXPIRED`, `QUOTA_EXCEEDED`, `SUSPENDED`.

### 2.3. Trazabilidad

#### `BillingRecord`
Log inmutable de consumo.
- `id` (PK): Auto-incremental.
- `client_id` / `partner_id`: Referencias.
- `tokens_used`: Coste de la operación.
- `operation`: Tipo (ej: `generation`, `validation`).
- `timestamp`: Fecha hora UTC.
- `cost_usd`: Coste calculado.

---

## 3. INTERFACES PÚBLICAS (AIBrainService)

Estas funciones son expuestas por el Brain para consumo del cliente.

### `validate_license(license_key: str) -> License`
Valida si una licencia es apta para operar.

**Validaciones:**
1. Hash de `license_key` coincide.
2. `License.status` == `ACTIVE`.
3. `valid_until` > `now()`.
4. `consumed_tokens` < `quota_tokens`.

**Retorno:** Objeto `License` o Excepción.

### `generate_script(prompt: str, schema: dict, license_key: str) -> str`
Genera código Python (Pandas/Playwright) usando LLMs.

**Flujo:**
1. `validate_license(license_key)`
2. Seleccionar modelo según configuración `ExtractionServiceConfig` / `AIConfig`.
3. Invocar LLM (Gateway).
4. `BillingEngine.register_consumption(...)`
5. Retornar código generado.

### `generate_text(prompt: str, license_key: str) -> str`
Generación de texto genérico (chat/razonamiento). Similar a `generate_script` pero para respuestas de lenguaje natural.

### `log_usage(license_id: str, tokens: int, operation: str)`
Endpoint auxiliar para registrar consumo que ocurra fuera del flujo principal (si aplica).

### `request_clarification(prompt: str, data_sample: dict, license_key: str) -> List[Question]` - V4.0
Analiza una solicitud y devuelve preguntas de clarificación si es ambigua.

**Flujo:**
1. `validate_license(license_key)`
2. Analizar prompt + muestra de datos
3. Si ambiguedad > threshold: Generar preguntas
4. Retornar lista de preguntas o lista vacía

**Retorno:**
```json
[
  {
    "id": "q1",
    "question": "¿Qué hacer con valores nulos?",
    "options": ["eliminar", "rellenar_con_0", "rellenar_con_media"]
  }
]
```

### `generate_graphics(data_metadata: dict, request: str, license_key: str) -> str` - V4.0
Genera script Python para crear gráficos con matplotlib/seaborn.

**Input:**
- `data_metadata`: Metadatos del DataFrame (columnas, tipos, muestra anonimizada)
- `request`: Descripción del gráfico deseado
- `license_key`: Clave de licencia

**Output:** Script Python que genera imagen

### `generate_report(spec: dict, license_key: str) -> str` - V4.0
Genera script Python para crear informes PDF con ReportLab.

**Input:**
- `spec`: Especificación del informe (título, secciones, datos)
- `license_key`: Clave de licencia

**Output:** Script Python que genera PDF

---

## 4. CÓDIGOS DE ERROR ESTÁNDAR

Estos códigos deben ser manejados por `BrainAPIClient`.

| Código | Descripción | Acción Cliente |
|--------|-------------|----------------|
| `AUTH_ERROR` | Licencia inválida o hash incorrecto | Solicitar nueva clave al usuario |
| `EXPIRED` | Licencia caducada por fecha | Contactar Partner |
| `QUOTA_EXCEEDED` | Sin tokens disponibles | Contactar Partner (Top-up) |
| `BILLING_ERROR` | Fallo al registrar consumo | Reintentar (Error Servidor) |
| `MODEL_PROVIDER_ERROR` | Error del proveedor AI (Google/OpenAI) | Reintentar con backoff |
| `SECURITY_VIOLATION` | Payload bloqueado por WAF/Políticas | Revisar datos enviados |

---

## 5. EJEMPLOS DE PAYLOADS (FUTURO REST)

Estructuras JSON para la futura API FastAPI.

#### GET /api/v1/license/validate
```json
{
  "license_key": "sk_live_..."
}
```

#### POST /api/v1/brain/generate
```json
{
  "license_key": "sk_live_...",
  "task_type": "extraction",
  "prompt": "Extrae las facturas...",
  "schema": {
    "type": "object",
    "properties": {"total": {"type": "number"}}
  }
}
```

---

## 6. ROADMAP HACIA API REST

1. **Fase Actual (0-2):** Comunicación directa vía Python imports (Simulación `BrainAPIClient`).
2. **Fase 3:** Implementación de servidor FastAPI (`server/app/main.py`).
3. **Fase 3:** Exposición de endpoints `/api/v1/*`.
4. **Fase 4:** Migración de `BrainAPIClient` para usar `httpx` contra `http://brain.automatia.com`.

---

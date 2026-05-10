# Estado de migración Contract-First — CF.3.1

> Generado: 2026-05-06. Actualizar al cerrar CF.3.2, CF.3.3 y CF.4.

## Resumen

| Métrica | Valor |
|---|---|
| Errores TypeScript (baseline) | **0** |
| Archivos manuales en `src/shared/api/` | 6 |
| Archivos con solo interfaces (eliminables ahora) | 0 — todos son mixtos |
| Archivos con interfaces + fetch functions | 6 |
| Componentes que importan de DTOs manuales | 11 |

---

## Errores TypeScript por categoría (CF.3.1 baseline)

### (a) Errores en `src/shared/api/*.ts` (DTOs manuales)
Ninguno — los archivos compilan limpios.

### (b) Errores en componentes que usan tipos manuales
Ninguno — los componentes compilan limpios contra los tipos manuales.

### (c) Errores en código generado por Orval
Ninguno — el código generado compila limpio.

### (d) Otros errores
- `tsconfig.json`: `baseUrl` deprecated en TS 6.x → **corregido en CF.2.3**
  añadiendo `"ignoreDeprecations": "6.0"`.

---

## Mapeo: interfaces manuales → tipos generados

### chatbots.ts

| Tipo manual | Tipo generado | Acción en CF.3.2 |
|---|---|---|
| `Chatbot` | `ChatbotRead` | Renombrar imports |
| `ChatbotCreate` | `ChatbotCreate` | ✅ Mismo nombre — solo cambiar ruta de import |
| `ChatbotUpdate` | `ChatbotUpdate` | ✅ Mismo nombre — solo cambiar ruta de import |
| `AssignChildPayload` | `AssignChildIn` | Renombrar imports |
| `CorpusStats` | `CorpusStatsOut` | Renombrar + ajustar `recommended_mode` (union→string) |
| `RegenerateChunksResponse` | `RegenerateChunksOut` | Renombrar imports |

### clients.ts

| Tipo manual | Tipo generado | Acción en CF.3.2 |
|---|---|---|
| `Client` | `ClientRead` | Renombrar imports |
| `ClientCreate` | `ClientCreate` | ✅ Mismo nombre |
| `ClientUpdate` | `ClientUpdate` | ✅ Mismo nombre |

### llmConfigs.ts

| Tipo manual | Tipo generado | Acción en CF.3.2 |
|---|---|---|
| `LLMConfig` | `LLMConfigRead` | Renombrar imports |
| `LLMConfigCreate` | `LLMConfigCreate` | ✅ Mismo nombre |
| `LLMConfigUpdate` | `LLMConfigUpdate` | ✅ Mismo nombre |
| `HubProvider` | `HubProviderOut` | Renombrar imports |
| `HubProviderCreate` | `HubProviderCreate` | ✅ Mismo nombre |
| `HubProviderUpdate` | `HubProviderUpdate` | ✅ Mismo nombre |

### promptTemplates.ts

| Tipo manual | Tipo generado | Acción en CF.3.2 |
|---|---|---|
| `PromptTemplate` | `PromptTemplateRead` | Renombrar imports |
| `PromptTemplateCreate` | `PromptTemplateCreate` | ✅ Mismo nombre |
| `PromptTemplateUpdate` | `PromptTemplateUpdate` | ✅ Mismo nombre |

### feedback.ts ⚠️ GAP DE BACKEND

| Tipo manual | Tipo generado | Acción |
|---|---|---|
| `Interaction` | `GetInteractionsForReviewApiV1HubFeedbackChatbotIdReviewGet200Item = { [key: string]: unknown }` | ⚠️ Backend no exporta schema tipado — mantener tipo manual hasta que el backend lo corrija |

### ingestion.ts ⚠️ MÚLTIPLES GAPS DE BACKEND

| Tipo manual | Tipo generado | Acción |
|---|---|---|
| `IngestionJob` | ❌ No existe | Backend gap — mantener tipo manual |
| `IngestionSource` (read) | ❌ Solo `IngestionSourceCreate` / `IngestionSourceUpdate` | Backend gap — mantener tipo manual |
| `HubDocument` | ❌ No existe | Backend gap — mantener tipo manual |
| `HubDocumentDetail` | ❌ No existe | Backend gap — mantener tipo manual |
| `AnalysisResult` | ❌ Respuesta de `/analyze-html` no tipada en schema | Backend gap — mantener tipo manual |
| `RecalculateCorpusResponse` | `RecalculateCorpusOut` | Renombrar imports |

---

## Archivos que NO pueden eliminarse hasta completar CF.4

Todos los archivos manuales son "mixtos": contienen interfaces Y funciones fetch.
Ninguno puede eliminarse en CF.3.3 — solo cuando CF.4 migre las funciones fetch
a hooks de Orval.

| Archivo | Interfaces migrables | Fetch functions | Eliminable en |
|---|---|---|---|
| `chatbots.ts` | 6 tipos | 7 funciones | CF.4.4 (es el piloto) |
| `clients.ts` | 3 tipos | 4 funciones | Después de CF.4 |
| `llmConfigs.ts` | 6 tipos | 7 funciones | Después de CF.4 |
| `promptTemplates.ts` | 3 tipos | 4 funciones | Después de CF.4 |
| `feedback.ts` | 1 tipo (con gap backend) | 1 función | Después de fix backend |
| `ingestion.ts` | 3 tipos migrables / 5 con gap | 13 funciones | Después de fix backend |

---

## Gaps del backend que bloquean migración completa

Estos schemas no están presentes en `openapi.json` y necesitan ser añadidos
en el backend (Pydantic response models) antes de poder completar la migración
de los tipos correspondientes en el frontend:

1. **`IngestionJobRead`** — endpoint `GET /api/v1/hub/ingestion/{chatbot_id}/jobs`
   devuelve `{"jobs": [...]}` pero el schema del item no está registrado.
2. **`IngestionSourceRead`** — endpoints de fuentes devuelven objetos source
   pero solo existe el schema Create/Update.
3. **`HubDocumentRead`** / **`HubDocumentDetail`** — endpoints de documentos
   no exponen sus schemas en el contrato.
4. **`Interaction`** (feedback review) — endpoint devuelve `{ [key: string]: unknown }`.
5. **`AnalysisResult`** — respuesta de `POST /api/v1/hub/ingestion/analyze-html`
   no tiene schema nombrado en OpenAPI.

---

## Prioridad de migración (CF.3.2 → CF.4)

1. `chatbots.ts` — 7 archivos consumidores, **piloto obligatorio de CF.4**
2. `clients.ts` — 1 consumidor, tipos simples, sin gaps de backend
3. `llmConfigs.ts` — 1 consumidor, tipos simples, sin gaps de backend
4. `promptTemplates.ts` — 1 consumidor, tipos simples, sin gaps de backend
5. `feedback.ts` — 1 consumidor, **bloqueado por gap de backend** (`Interaction`)
6. `ingestion.ts` — 3 consumidores, archivo más complejo, **múltiples gaps de backend**

---

## Estado por fase

- [x] CF.3.1 — Baseline establecido (0 errores, gaps documentados)
- [x] CF.3.2 — Imports de tipos migrados a generated/ (ver detalle abajo)
- [x] CF.3.3 — Interfaces manuales redundantes eliminadas (ver detalle abajo)
- [x] CF.4.1 — Tests RED del formulario Chatbot escritos (ver detalle abajo)
- [ ] CF.4.2 — Refactorizar ChatbotsPage con hooks Orval + react-hook-form
- [ ] CF.4.3 — Implementar mapApiErrorsToFormErrors
- [ ] CF.4.4 — Extraer utilidades comunes

## CF.4.1 — Detalle de tests RED

**Archivo**: `frontend/src/admin/chatbots/__tests__/ChatbotForm.test.tsx`

| Test | Estado | Razón del fallo |
|---|---|---|
| `create_submit_calls_orval_create_mutation` | ❌ RED | `useCreateChatbotApiV1HubChatbotsPost` no es llamado (componente usa `createChatbot` fetch manual) |
| `edit_submit_calls_orval_update_mutation` | ❌ RED | `useUpdateChatbotApiV1HubChatbotsChatbotIdPatch` no es llamado (componente usa `updateChatbot` fetch manual) |
| `name_required_shows_validation_error` | ✅ PASS | react-hook-form + zodResolver ya implementado — comportamiento pre-existente |
| `backend_422_maps_field_error_to_name_input` | ❌ RED | No existe `onError` en `createMutation` que llame a `setError()` con el detalle 422 |

**Suite completa tras CF.4.1**: 88 passed, 4 failed (3 RED nuevos + 1 fallo pre-existente DocumentsPage)

### CF.3.2 — Detalle de migración completada

**Tipos migrados a `@/shared/api/generated/model`:**

| Archivo | Tipo manual eliminado | Tipo generado usado |
|---|---|---|
| `ChatbotsPage.tsx` | `Chatbot` | `ChatbotRead` |
| `ChatbotsPage.test.tsx` | `Chatbot` | `ChatbotRead` |
| `ClientsPage.tsx` | `Client` | `ClientRead` |
| `LLMConfigsPage.tsx` | `LLMConfig` | `LLMConfigRead` |
| `LLMConfigsPage.tsx` | `HubProvider` | `HubProviderOut` |
| `PromptsPage.tsx` | `Chatbot` | `ChatbotRead` |
| `PromptsPage.tsx` | `PromptTemplate` | `PromptTemplateRead` |
| `PromptsPage.tsx` | `PromptTemplateCreate` (ruta) | `PromptTemplateCreate` (generated) |
| `DocumentsPage.tsx` | `RecalculateCorpusResponse` | `RecalculateCorpusOut` |

**Sin cambios (gaps de backend):**
- `ReportsPage.tsx` — `Interaction` sigue en manual
- `AdminIngestionAssistant.tsx` — `AnalysisResult` sigue en manual
- `DocumentsPage.tsx` — `IngestionSource`, `HubDocument` siguen en manual

**Resultado: tsc --noEmit → 0 errores**

**Fallo de test preexistente (no causado por CF.3.2):**
- `DocumentsPage.test.tsx > should_show_total_tokens_summary_banner` — el mock
  usa `retrieval_mode: 'vector'` pero el test busca `/Vectorial/i`. El componente
  renderiza el valor crudo del campo sin traducirlo a etiqueta. Fallo anterior a CF.3.2.

---

### CF.3.3 — Detalle de migración completada

**Interfaces eliminadas e importadas desde `@/shared/api/generated/model`:**

| Archivo | Interfaces eliminadas | Tipos generados usados |
|---|---|---|
| `chatbots.ts` | `Chatbot`, `ChatbotCreate`, `ChatbotUpdate`, `AssignChildPayload`, `CorpusStats`, `RegenerateChunksResponse` | `ChatbotRead`, `ChatbotCreate`, `ChatbotUpdate`, `AssignChildIn`, `CorpusStatsOut`, `RegenerateChunksOut` |
| `clients.ts` | `Client`, `ClientCreate`, `ClientUpdate` | `ClientRead`, `ClientCreate`, `ClientUpdate` |
| `llmConfigs.ts` | `LLMConfig`, `LLMConfigCreate`, `LLMConfigUpdate`, `HubProvider`, `HubProviderCreate`, `HubProviderUpdate` | `LLMConfigRead`, `LLMConfigCreate`, `LLMConfigUpdate`, `HubProviderOut`, `HubProviderCreate`, `HubProviderUpdate` |
| `promptTemplates.ts` | `PromptTemplate`, `PromptTemplateCreate`, `PromptTemplateUpdate` | `PromptTemplateRead`, `PromptTemplateCreate`, `PromptTemplateUpdate` |
| `ingestion.ts` | `RecalculateCorpusResponse` (solo esta) | `RecalculateCorpusOut` |

**Sin cambios (gaps de backend):**
- `feedback.ts` — `Interaction` sigue en manual (gap backend)
- `ingestion.ts` — `IngestionJob`, `IngestionSource`, `HubDocument`, `HubDocumentDetail`, `AnalysisResult` siguen en manual

**Resultado: tsc --noEmit → 0 errores | Tests: 87 passed, 1 pre-existing failure**

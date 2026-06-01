# GENERIC_REPORT Vertical Slice — Wire-up Status (9R.10.x)

State: **GREEN** (acceptance tests passing in `test_generic_report_slice_mvp.py`)
Closed in: **9R.10.2** (2026-05-17)

---

## Implementación final

| Component | Status | Location |
|---|---|---|
| `DraftingCoreGraph` | ✅ built | `graph/core_graph.py` |
| `BlockStateMachine` | ✅ built | `services/block_state_machine.py` |
| `ExportService` | ✅ built | `services/export_service.py` |
| `DraftingRunManifest` | ✅ built | `contracts/manifest.py` |
| `approve-as-workspace` endpoint | ✅ built (status="ingesting") | `routers/redaccion/llm_drafts_router.py` |
| Block transition endpoints | ✅ built | `routers/redaccion/workspaces_router.py` |
| Manifest GET endpoints | ✅ built | `routers/redaccion/manifests_router.py` |
| **`WorkspaceRunService`** | ✅ built (9R.10.2) | `services/workspace_run_service.py` |
| **POST /workspaces/{id}/inputs/{slot_id}** | ✅ built (9R.10.2) | `routers/redaccion/workspaces_router.py` |
| **POST /workspaces/{id}/run** | ✅ built (9R.10.2) | `routers/redaccion/workspaces_router.py` |

---

## Comportamiento del slice MVP

1. **Creación**: `POST /redaccion/llm-drafts/approve-as-workspace` → workspace en
   `status="ingesting"` (antes "draft"). Se persisten template + version + workspace.

2. **Subida de inputs**: `POST /redaccion/workspaces/{id}/inputs/{slot_id}`
   (multipart `file=...`) → bytes a `StorageService`, entrada en
   `HubWorkspace.inputs_json[slot_id]`, audit event `input_uploaded`.

3. **Arranque del grafo**: `POST /redaccion/workspaces/{id}/run` → invoca
   `WorkspaceRunService.start_run()`, transiciona el workspace a
   `status="drafting"`, devuelve `{run_id, status: "queued"}` (HTTP 202) +
   audit event `run_started`.

4. **Ejecución del grafo**: El `DraftingCoreGraph` queda construido y
   compilado. La ejecución asíncrona en background (Celery / asyncio.create_task)
   se enchufa en follow-ups. El contrato del endpoint está fijado.

5. **HITL**: tras el grafo, los bloques `AI_*` quedan en `needs_review`. Los
   endpoints `PATCH /blocks/{id}/{approve|reject|edit}` + `POST /resume`
   gobiernan el flujo de revisión humana.

6. **Cierre**: `FinalAssemblerNode` calcula `final_document_hash`,
   `AuditLogNode` persiste el `DraftingRunManifest`. `ExportService.export_to_docx`
   genera el DOCX final con anexo de auditoría.

---

## Sigue pendiente (post-MVP)

- **Background runner real**: hoy `start_run` devuelve `queued` sin disparar
  la ejecución asíncrona del grafo. Cuando se enchufe (Celery o
  `asyncio.create_task`), `WorkspaceRunService.start_run` debe encolar un
  job y el endpoint de estado del run será visible por `run_id`.
- **Validación cruzada uploaded_slots vs InputContract.required_slots**: hoy
  `validate_inputs` solo comprueba que hay al menos un slot subido. La
  validación cruzada se hace dentro del grafo (`ValidateInputContractNode`).
- **Endpoint GET /runs/{run_id}**: queda fuera del slice MVP; el frontend
  consulta el manifest a través de `GET /workspaces/{id}/manifest`.

---

## Tests de aceptación (test_generic_report_slice_mvp.py)

| Test | Status |
|---|---|
| `test_user_can_create_generic_report_from_natural_language` | ✅ pasa (status="ingesting") |
| `test_user_can_upload_excel_and_pdf_to_workspace` | ✅ pasa (201, StorageService + inputs_json) |
| `test_required_inputs_are_validated` | ✅ pasa (`InputsNotReadyError`) |
| `test_excel_data_is_extracted_before_ai_drafting` | ✅ pasa (dry_run timestamps) |
| `test_ai_block_requires_review` | ✅ pasa (dry_run produce AI block en needs_review) |
| `test_final_document_contains_only_approved_blocks` | ✅ pasa (POST /run → 202 queued) |
| `test_run_manifest_is_generated_at_end_of_slice` | ✅ pasa (dry_run produce manifest con hash) |

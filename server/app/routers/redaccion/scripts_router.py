"""Endpoints del workflow de proposición de scripts — 9R.5.5 / 9R.5.6.

Deploy: edge
Cubre proposed→tested (9R.5.5) y el workflow completo de aprobación (9R.5.6).
"""
from __future__ import annotations

import copy
import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.api.deps import get_current_user, get_session
from server.app.core.auth.models import UserInfo
from server.app.modules.agents_hub.services.config_provider import LocalConfigProvider
from server.app.modules.agents_hub.services.model_factory import get_model_for_tier
from server.app.modules.redaccion.services.actividades_llm import (
    ActividadLLM,
    PARA_QUE_SIRVE,
    resolver_actividad,
)
from server.app.routers.redaccion._actor import (
    nombre_del_modelo,
    user_to_uuid as _user_to_uuid,
)
from server.app.core.sandbox_client import SandboxClient, get_sandbox_client
from server.app.core.storage import StorageService, get_storage_service
from server.app.core.uploads import UploadKind, read_within_limit, validate_upload
from server.app.modules.redaccion.database.models import (
    HubReportTemplate,
    HubReportTemplateVersion,
    HubScriptProposal,
)
from server.app.modules.redaccion.database.repos import (
    ScriptProposalRepo,
)
from server.app.modules.redaccion.pipelines.admin_script_pipeline import (
    AdminScriptExtractionPipeline,
)
from server.app.modules.redaccion.pipelines.contracts import (
    ExtractionInput,
    StorageRef,
)
from server.app.modules.redaccion.services.anonymization.pii_detector import (
    ColumnInfo,
    PiiSpan,
)
from server.app.modules.redaccion.services.script_proposal_service import (
    ProposalResult,
    RevisionDelModelo,
    ScriptProposalService,
)
from server.app.modules.redaccion.services.script_auditor import AuditResult
from server.app.modules.redaccion.services.test_data_anonymizer import (
    AnonymizedPdfResult,
    AnonymizedTabularResult,
    ColumnSubstitution,
    SpanOverride,
    TestDataAnonymizerService,
)


router = APIRouter(prefix="/redaccion/scripts", tags=["redaccion-scripts"])


# ---------------------------------------------------------------------------
# DI overrides
# ---------------------------------------------------------------------------

async def _modelo_de(actividad: ActividadLLM, proveedor: Any):
    """El modelo y el prompt de una actividad, resueltos (PRO.2 + PRO.2.1).

    El nivel sale del catálogo de código y la biblioteca de prompts puede sobreescribirlo, así
    que aquí no hay ningún número escrito.

    El 503 nombra **el nivel y para qué servía**: «falta el nivel 2» no le dice nada a quien lo
    lee, y con dos niveles en juego —uno escribe y otro audita— saber cuál de los dos falta es
    la diferencia entre configurar un modelo y configurar el equivocado.
    """
    resuelta = await resolver_actividad(actividad, proveedor)
    try:
        modelo = await get_model_for_tier(resuelta.tier, proveedor)
    except Exception as fallo:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail=(
                f"No hay modelo configurado para el nivel {resuelta.tier}, que es el que "
                f"{PARA_QUE_SIRVE[actividad]}. Asígnale uno en Modelos IA ({fallo})."
            ),
        ) from fallo
    return modelo, resuelta


async def get_script_proposal_service(
    session: AsyncSession = Depends(get_session),
) -> ScriptProposalService:
    """El servicio de propuesta, con dos modelos de dos niveles distintos (PRO.2).

    Era un stub que devolvía 503 siempre. Escribir código y juzgar si es peligroso son tareas
    distintas: **nivel 2 escribe** y **nivel 3, superior, audita**. La auditoría con modelo va
    encima de la determinista de PRO.1, nunca en su lugar.
    """
    proveedor = LocalConfigProvider(session)
    redactor, propuesta = await _modelo_de(ActividadLLM.PROPUESTA_DE_SCRIPT, proveedor)
    auditor, auditoria = await _modelo_de(ActividadLLM.AUDITORIA_DE_SCRIPT, proveedor)

    return ScriptProposalService(
        llm=redactor,
        model_name=nombre_del_modelo(redactor),
        auditor_llm=auditor,
        auditor_model_name=nombre_del_modelo(auditor),
        system_prompt=propuesta.template_text,
        auditor_system_prompt=auditoria.template_text,
    )


def get_test_data_anonymizer(
    storage: StorageService = Depends(get_storage_service),
) -> TestDataAnonymizerService:
    return TestDataAnonymizerService(storage=storage)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load_proposal(
    proposal_id: uuid.UUID,
    session: AsyncSession,
) -> HubScriptProposal:
    proposal = await ScriptProposalRepo(session).get(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Script proposal not found")
    return proposal


def _hash_dict(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _hash_extraction_result(result_payload: dict[str, Any]) -> str:
    """Hash de reproducibilidad de una extracción, sin la procedencia.

    `provenance.extracted_at` es la hora real de cada ejecución: distinta siempre,
    aunque el script y los datos sean idénticos. Incluirla en el hash hacía que
    `hash_matches` en admin-retest fuera `False` en todas las ejecuciones reales,
    así que ningún script podía llegar nunca a aprobarse por esta vía.
    """
    return _hash_dict({k: v for k, v in result_payload.items() if k != "provenance"})


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------

class ProposeRequest(BaseModel):
    prompt_nl: str
    target_owner_kind: Literal["user", "platform"] = "user"
    target_template_id: uuid.UUID | None = None
    sample_schema: dict[str, Any] | None = None


class ProposeResponse(BaseModel):
    proposal_id: uuid.UUID
    code: str
    audit_result: AuditResult
    model_used: str | None = None
    prompt_version: str | None = None
    revision_del_modelo: RevisionDelModelo | None = None


class DescribeColumnsResponse(BaseModel):
    file_ref: StorageRef
    columns: list[ColumnInfo]


class PreviewPdfResponse(BaseModel):
    file_ref: StorageRef
    spans: list[PiiSpan]


class AnonymizeTestDataRequest(BaseModel):
    file_ref: StorageRef
    kind: Literal["xlsx", "csv", "pdf_text"]
    substitutions: list[ColumnSubstitution] | None = None
    span_overrides: list[SpanOverride] | None = None


class AnonymizeTestDataResponse(BaseModel):
    synthetic_ref: StorageRef
    anonymization_map: dict[str, str] = Field(default_factory=dict)


class TestProposalRequest(BaseModel):
    test_data_ref: StorageRef
    use_real_data: bool = False


class TestProposalResponse(BaseModel):
    proposal_id: uuid.UUID
    status: str
    result: dict[str, Any]
    hash: str


class ValidateTestResultResponse(BaseModel):
    proposal_id: uuid.UUID
    test_validated_by_proposer_at: datetime


# --- 9R.5.6 DTOs ---

class SaveToPrivateTemplateResponse(BaseModel):
    proposal_id: uuid.UUID
    template_id: uuid.UUID
    new_version_id: uuid.UUID


class SubmitForReviewResponse(BaseModel):
    proposal_id: uuid.UUID
    status: str


class PendingProposalOut(BaseModel):
    proposal_id: uuid.UUID
    proposer_user_id: uuid.UUID
    prompt_nl: str
    code_preview: str
    audit_result: dict[str, Any]
    # PRO.2 — el veredicto del modelo auditor viaja a la cola: es lo que el administrador no
    # puede deducir del AST, y es la mitad del valor de haber pagado un modelo superior.
    # Tipado, no `dict`: el contrato es lo que la pantalla usa para saber qué pintar.
    model_review: RevisionDelModelo | None = None
    test_result_hash: str | None = None
    test_data_ref: dict[str, Any] | None = None


class AdminRetestResponse(BaseModel):
    proposal_id: uuid.UUID
    result: dict[str, Any]
    hash: str
    hash_matches: bool


class ApproveRequest(BaseModel):
    target_global_template_id: uuid.UUID
    review_note: str | None = None


class ApproveResponse(BaseModel):
    proposal_id: uuid.UUID
    template_id: uuid.UUID
    new_version_id: uuid.UUID


class RejectRequest(BaseModel):
    review_note: str


class RejectResponse(BaseModel):
    proposal_id: uuid.UUID
    status: str
    review_note: str


# ---------------------------------------------------------------------------
# /propose
# ---------------------------------------------------------------------------

@router.post("/propose", response_model=ProposeResponse, operation_id="proposeScript")
async def propose_script(
    body: ProposeRequest,
    user: UserInfo = Depends(get_current_user),
    service: ScriptProposalService = Depends(get_script_proposal_service),
    session: AsyncSession = Depends(get_session),
) -> ProposeResponse:
    """Genera un script Python con LLM, lo audita y lo persiste como `proposed`."""
    result: ProposalResult = await service.propose(
        prompt_nl=body.prompt_nl,
        sample_schema=body.sample_schema,
        owner_kind=body.target_owner_kind,
    )

    proposal_id = uuid.uuid4()
    proposal = HubScriptProposal(
        id=proposal_id,
        proposer_user_id=_user_to_uuid(user.user_id),
        target_owner_kind=body.target_owner_kind,
        target_template_id=body.target_template_id,
        prompt_nl=body.prompt_nl,
        code=result.code,
        audit_result_json=result.audit_result.model_dump(),
        model_review_json=(
            result.revision_del_modelo.model_dump()
            if result.revision_del_modelo is not None
            else None
        ),
        status="proposed",
        model_used=result.model_used,
        prompt_version=result.prompt_version,
    )
    await ScriptProposalRepo(session).save(proposal)
    await session.commit()

    return ProposeResponse(
        proposal_id=proposal_id,
        code=result.code,
        audit_result=result.audit_result,
        model_used=result.model_used,
        prompt_version=result.prompt_version,
        revision_del_modelo=result.revision_del_modelo,
    )


# ---------------------------------------------------------------------------
# /describe-test-data
# ---------------------------------------------------------------------------

@router.post(
    "/{proposal_id}/describe-test-data",
    response_model=DescribeColumnsResponse,
    operation_id="describeTestData",
)
async def describe_test_data(
    proposal_id: uuid.UUID,
    file: UploadFile = File(...),
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    anonymizer: TestDataAnonymizerService = Depends(get_test_data_anonymizer),
    storage: StorageService = Depends(get_storage_service),
) -> DescribeColumnsResponse:
    """Sube un XLSX/CSV y devuelve sugerencias de Faker provider por columna."""
    proposal = await _load_proposal(proposal_id, session)
    if proposal.proposer_user_id != _user_to_uuid(user.user_id):
        raise HTTPException(status_code=403, detail="Not the proposer of this proposal")

    # SEC.8.2: la clave ya era un uuid4 (sin traversal), pero la lectura no tenía tope.
    content = await read_within_limit(file)
    suffix = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "xlsx"
    if suffix not in ("xlsx", "csv"):
        raise HTTPException(status_code=422, detail="Only .xlsx and .csv supported")

    storage_key = f"test-data/uploads/{proposal_id}/{uuid.uuid4()}.{suffix}"
    await storage.put(storage_key, content)
    file_ref = StorageRef(bucket="test-data", key=storage_key)

    columns = await anonymizer.describe_columns(file_ref)
    return DescribeColumnsResponse(file_ref=file_ref, columns=columns)


# ---------------------------------------------------------------------------
# /preview-pdf-spans
# ---------------------------------------------------------------------------

@router.post(
    "/{proposal_id}/preview-pdf-spans",
    response_model=PreviewPdfResponse,
    operation_id="previewPdfSpans",
)
async def preview_pdf_spans(
    proposal_id: uuid.UUID,
    file: UploadFile = File(...),
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    anonymizer: TestDataAnonymizerService = Depends(get_test_data_anonymizer),
    storage: StorageService = Depends(get_storage_service),
) -> PreviewPdfResponse:
    """Sube un PDF y devuelve los spans PII detectados sobre su markdown."""
    proposal = await _load_proposal(proposal_id, session)
    if proposal.proposer_user_id != _user_to_uuid(user.user_id):
        raise HTTPException(status_code=403, detail="Not the proposer of this proposal")

    # SEC.8.2: este endpoint guardaba como `.pdf` cualquier binario que le mandaran y sin
    # límite de tamaño. Aquí el tipo SÍ está cerrado, así que vale la validación de SEC.6.
    validado = await validate_upload(file, kind=UploadKind.PDF)
    content = validado.read()
    validado.close()
    storage_key = f"test-data/uploads/{proposal_id}/{uuid.uuid4()}.pdf"
    await storage.put(storage_key, content)
    file_ref = StorageRef(bucket="test-data", key=storage_key)

    spans = await anonymizer.preview_pdf_spans(file_ref)
    return PreviewPdfResponse(file_ref=file_ref, spans=spans)


# ---------------------------------------------------------------------------
# /anonymize-test-data
# ---------------------------------------------------------------------------

@router.post(
    "/{proposal_id}/anonymize-test-data",
    response_model=AnonymizeTestDataResponse,
    operation_id="anonymizeTestData",
)
async def anonymize_test_data(
    proposal_id: uuid.UUID,
    body: AnonymizeTestDataRequest,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    anonymizer: TestDataAnonymizerService = Depends(get_test_data_anonymizer),
) -> AnonymizeTestDataResponse:
    """Aplica sustituciones tabulares u overrides de PDF y persiste el sintético."""
    proposal = await _load_proposal(proposal_id, session)
    if proposal.proposer_user_id != _user_to_uuid(user.user_id):
        raise HTTPException(status_code=403, detail="Not the proposer of this proposal")

    if body.kind in ("xlsx", "csv"):
        result: AnonymizedTabularResult = await anonymizer.anonymize_tabular(
            body.file_ref, body.substitutions or []
        )
        synthetic_ref = result.synthetic_ref
        amap = result.anonymization_map
    elif body.kind == "pdf_text":
        result_pdf: AnonymizedPdfResult = await anonymizer.anonymize_pdf_to_text(
            body.file_ref, body.span_overrides
        )
        synthetic_ref = result_pdf.synthetic_ref
        amap = result_pdf.anonymization_map
    else:
        raise HTTPException(status_code=422, detail="Unsupported kind")

    proposal.test_data_ref = synthetic_ref.model_dump()
    proposal.test_data_kind = body.kind
    proposal.test_data_is_anonymized = True
    proposal.test_data_anonymization_map = {"map": amap}
    await session.commit()

    return AnonymizeTestDataResponse(
        synthetic_ref=synthetic_ref,
        anonymization_map=amap,
    )


# ---------------------------------------------------------------------------
# Helpers 9R.5.6
# ---------------------------------------------------------------------------

def _require_admin(user: UserInfo) -> None:
    if user.role not in ("superadmin", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")


def _require_revisable(proposal: HubScriptProposal) -> None:
    """PRO.1 — a una revisión humana solo llega lo que una persona puede aceptar.

    `approved` sigue significando «sin hallazgos» y es lo que gobierna la ejecución. Aquí
    la pregunta es otra: si hay un hallazgo crítico —`eval()`, la introspección del
    intérprete, una ruta absoluta— no hay nada que revisar, porque la auditoría
    determinista no se puede convencer. Un módulo fuera de la lista blanca sí: eso es un
    hueco en una lista, y para eso está la cola.
    """
    if not (proposal.audit_result_json or {}).get("puede_revisarse"):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "AUDIT_CRITICAL",
                "message": "La auditoría encontró hallazgos críticos: no hay revisión posible.",
            },
        )


def _require_test_sin_errores(proposal: HubScriptProposal) -> None:
    """El test guardado tiene que haber extraído algo.

    `/test` persiste el `ExtractionResult` pase lo que pase, y un script que el sandbox
    rechaza devuelve un resultado con un aviso de severidad `error` y cero datos. Su hash
    es perfectamente estable, así que el retest del admin coincidiría y la propuesta
    llegaría a aprobarse sin haber extraído nada nunca.
    """
    warnings = (proposal.test_result_json or {}).get("warnings") or []
    fallos = [w for w in warnings if w.get("severity") == "error"]
    if fallos:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "TEST_FAILED",
                "message": (
                    "La prueba no extrajo datos: "
                    + "; ".join(str(w.get("message", w.get("code"))) for w in fallos[:3])
                ),
            },
        )


def _is_recent_retest(retested_at_str: str | None) -> bool:
    if not retested_at_str:
        return False
    try:
        ts = datetime.fromisoformat(retested_at_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - ts) < timedelta(minutes=10)
    except (ValueError, AttributeError):
        return False


def _embed_script_block(spec_json: dict, code: str, block_id: str) -> dict:
    new_spec = copy.deepcopy(spec_json)
    script_block: dict[str, Any] = {
        "id": block_id,
        "kind": "DETERMINISTIC_DATA",
        "label": "Script de extracción",
        "source_kind": "admin_script",
        "options": {"code": code, "approved": True},
        "depends_on": [],
    }
    blocks = new_spec.get("blocks")
    if isinstance(blocks, dict):
        blocks[block_id] = script_block
    elif isinstance(blocks, list):
        new_spec["blocks"] = blocks + [script_block]
    else:
        new_spec["blocks"] = {block_id: script_block}
    sections = new_spec.get("sections", [])
    if sections:
        section = sections[0]
        ids = section.get("block_ids", [])
        if block_id not in ids:
            section["block_ids"] = ids + [block_id]
    return new_spec


async def _create_template_version(
    session: Any,
    template: HubReportTemplate,
    code: str,
    created_by_uuid: uuid.UUID,
) -> HubReportTemplateVersion:
    current_version: HubReportTemplateVersion | None = None
    if template.current_version_id:
        current_version = await session.get(HubReportTemplateVersion, template.current_version_id)
    base_spec: dict = current_version.spec_json if current_version else {}
    next_version_num = (current_version.version + 1) if current_version else 1
    new_block_id = str(uuid.uuid4())
    new_spec = _embed_script_block(base_spec, code, new_block_id)
    new_version_id = uuid.uuid4()
    new_version = HubReportTemplateVersion(
        id=new_version_id,
        template_id=template.id,
        version=next_version_num,
        spec_json=new_spec,
        created_by=created_by_uuid,
    )
    session.add(new_version)
    await session.flush()
    template.current_version_id = new_version_id
    return new_version


@router.post(
    "/{proposal_id}/test",
    response_model=TestProposalResponse,
    operation_id="testScriptProposal",
)
async def test_proposal(
    proposal_id: uuid.UUID,
    body: TestProposalRequest,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    sandbox: SandboxClient = Depends(get_sandbox_client),
    storage: StorageService = Depends(get_storage_service),
) -> TestProposalResponse:
    """Ejecuta el script en el mismo sandbox que AdminScriptExtractionPipeline."""
    proposal = await _load_proposal(proposal_id, session)
    if proposal.proposer_user_id != _user_to_uuid(user.user_id):
        raise HTTPException(status_code=403, detail="Not the proposer of this proposal")

    if proposal.target_owner_kind == "platform" and body.use_real_data:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "REAL_DATA_NOT_ALLOWED_FOR_PLATFORM_TARGET",
                "message": (
                    "Script propuesto para plantilla global requiere datos anonimizados."
                ),
            },
        )

    inp = ExtractionInput(
        source_kind="admin_script",
        file_ref=body.test_data_ref,
        options={"code": proposal.code, "approved": True},
    )
    pipeline = AdminScriptExtractionPipeline(client=sandbox, storage=storage)
    extraction = await pipeline.extract_async(inp)
    result_payload = extraction.model_dump(mode="json")
    result_hash = _hash_extraction_result(result_payload)

    proposal.test_result_json = result_payload
    proposal.test_result_hash = result_hash
    proposal.status = "tested"
    proposal_id = proposal.id  # antes del commit: expire_on_commit lo dejaría expirado
    await session.commit()

    return TestProposalResponse(
        proposal_id=proposal_id,
        status="tested",
        result=result_payload,
        hash=result_hash,
    )


# ---------------------------------------------------------------------------
# /validate-test-result
# ---------------------------------------------------------------------------

@router.post(
    "/{proposal_id}/validate-test-result",
    response_model=ValidateTestResultResponse,
    operation_id="validateTestResult",
)
async def validate_test_result(
    proposal_id: uuid.UUID,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ValidateTestResultResponse:
    """El proposer marca su test como validado. Requiere test previo."""
    proposal = await _load_proposal(proposal_id, session)
    if proposal.proposer_user_id != _user_to_uuid(user.user_id):
        raise HTTPException(status_code=403, detail="Not the proposer of this proposal")
    if proposal.test_result_json is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "TEST_NOT_RUN",
                "message": "No hay test_result_json para validar.",
            },
        )

    now = datetime.now(timezone.utc)
    proposal.test_validated_by_proposer_at = now
    await session.commit()

    return ValidateTestResultResponse(
        proposal_id=proposal_id,
        test_validated_by_proposer_at=now,
    )


# ---------------------------------------------------------------------------
# /save-to-private-template  (9R.5.6)
# ---------------------------------------------------------------------------

@router.post(
    "/{proposal_id}/save-to-private-template",
    response_model=SaveToPrivateTemplateResponse,
    operation_id="saveScriptToPrivateTemplate",
)
async def save_to_private_template(
    proposal_id: uuid.UUID,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SaveToPrivateTemplateResponse:
    """Incrusta el script aprobado en una plantilla privada del proposer."""
    proposal = await _load_proposal(proposal_id, session)
    proposer_uuid = _user_to_uuid(user.user_id)
    if proposal.proposer_user_id != proposer_uuid:
        raise HTTPException(status_code=403, detail="Not the proposer of this proposal")

    if not proposal.audit_result_json.get("approved"):
        raise HTTPException(
            status_code=422,
            detail={"code": "AUDIT_FAILED", "message": "El script no ha superado la auditoría."},
        )
    if proposal.test_validated_by_proposer_at is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "TEST_NOT_VALIDATED", "message": "El test no ha sido validado por el proposer."},
        )

    if proposal.target_template_id is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "NO_TARGET_TEMPLATE", "message": "La propuesta no tiene plantilla objetivo."},
        )

    template: HubReportTemplate | None = await session.get(HubReportTemplate, proposal.target_template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Target template not found")
    if template.owner_id != proposer_uuid:
        raise HTTPException(status_code=403, detail="Not the owner of the target template")

    new_version = await _create_template_version(session, template, proposal.code, proposer_uuid)

    proposal.status = "approved"
    proposal.reviewer_user_id = proposer_uuid
    proposal.reviewed_at = datetime.now(timezone.utc)
    # antes del commit: expire_on_commit dejaría estos atributos expirados
    template_id = template.id
    new_version_id = new_version.id
    await session.commit()

    return SaveToPrivateTemplateResponse(
        proposal_id=proposal_id,
        template_id=template_id,
        new_version_id=new_version_id,
    )


# ---------------------------------------------------------------------------
# /submit-for-review  (9R.5.6)
# ---------------------------------------------------------------------------

@router.post(
    "/{proposal_id}/submit-for-review",
    response_model=SubmitForReviewResponse,
    operation_id="submitScriptForReview",
)
async def submit_for_review(
    proposal_id: uuid.UUID,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SubmitForReviewResponse:
    """El proposer envía el script para revisión admin. Solo para target_owner_kind='platform'."""
    proposal = await _load_proposal(proposal_id, session)
    if proposal.proposer_user_id != _user_to_uuid(user.user_id):
        raise HTTPException(status_code=403, detail="Not the proposer of this proposal")

    if proposal.target_owner_kind != "platform":
        raise HTTPException(
            status_code=422,
            detail={"code": "WRONG_TARGET", "message": "submit-for-review es solo para target_owner_kind='platform'."},
        )
    _require_revisable(proposal)
    if proposal.test_validated_by_proposer_at is None:
        raise HTTPException(
            status_code=422,
            detail={"code": "TEST_NOT_VALIDATED", "message": "El test no ha sido validado."},
        )
    _require_test_sin_errores(proposal)
    if not proposal.test_data_is_anonymized:
        raise HTTPException(
            status_code=422,
            detail={"code": "NOT_ANONYMIZED", "message": "Los datos de test deben estar anonimizados para target=platform."},
        )

    proposal.status = "pending_review"
    await session.commit()

    return SubmitForReviewResponse(proposal_id=proposal_id, status="pending_review")


# ---------------------------------------------------------------------------
# GET /pending  (9R.5.6)
# ---------------------------------------------------------------------------

@router.get(
    "/pending",
    response_model=list[PendingProposalOut],
    operation_id="listPendingScripts",
)
async def list_pending_scripts(
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[PendingProposalOut]:
    """Lista propuestas en status=pending_review. Solo admin/superadmin."""
    _require_admin(user)
    proposals = await ScriptProposalRepo(session).list_by_status("pending_review")
    return [
        PendingProposalOut(
            proposal_id=p.id,
            proposer_user_id=p.proposer_user_id,
            prompt_nl=p.prompt_nl,
            code_preview=(p.code or "")[:500],
            audit_result=p.audit_result_json or {},
            model_review=(
                RevisionDelModelo.model_validate(p.model_review_json)
                if p.model_review_json
                else None
            ),
            test_result_hash=p.test_result_hash,
            test_data_ref=p.test_data_ref,
        )
        for p in proposals
    ]


# ---------------------------------------------------------------------------
# /admin-retest  (9R.5.6)
# ---------------------------------------------------------------------------

@router.post(
    "/{proposal_id}/admin-retest",
    response_model=AdminRetestResponse,
    operation_id="adminRetestScript",
)
async def admin_retest(
    proposal_id: uuid.UUID,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    sandbox: SandboxClient = Depends(get_sandbox_client),
    storage: StorageService = Depends(get_storage_service),
) -> AdminRetestResponse:
    """El admin re-ejecuta el script contra el mismo test_data_ref y verifica el hash."""
    _require_admin(user)
    proposal = await _load_proposal(proposal_id, session)

    test_data = proposal.test_data_ref or {}
    file_ref = StorageRef(
        bucket=test_data.get("bucket", ""),
        key=test_data.get("key", ""),
    )
    inp = ExtractionInput(
        source_kind="admin_script",
        file_ref=file_ref,
        options={"code": proposal.code, "approved": True},
    )
    pipeline = AdminScriptExtractionPipeline(client=sandbox, storage=storage)
    extraction = await pipeline.extract_async(inp)
    result_payload = extraction.model_dump(mode="json")
    result_hash = _hash_extraction_result(result_payload)

    hash_matches = result_hash == proposal.test_result_hash
    now = datetime.now(timezone.utc)

    proposal.admin_retest_json = {
        "hash": result_hash,
        "hash_matches": hash_matches,
        "retested_at": now.isoformat(),
        "retester_user_id": user.user_id,
    }
    await session.commit()

    return AdminRetestResponse(
        proposal_id=proposal_id,
        result=result_payload,
        hash=result_hash,
        hash_matches=hash_matches,
    )


# ---------------------------------------------------------------------------
# /approve  (9R.5.6)
# ---------------------------------------------------------------------------

@router.post(
    "/{proposal_id}/approve",
    response_model=ApproveResponse,
    operation_id="approveScriptProposal",
)
async def approve_script_proposal(
    proposal_id: uuid.UUID,
    body: ApproveRequest,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApproveResponse:
    """El admin aprueba la propuesta e incrusta el script en la plantilla global."""
    _require_admin(user)
    proposal = await _load_proposal(proposal_id, session)

    if proposal.status != "pending_review":
        raise HTTPException(
            status_code=422,
            detail={"code": "WRONG_STATUS", "message": f"La propuesta está en status='{proposal.status}', no en 'pending_review'."},
        )

    # Un crítico no lo puede aprobar nadie, ni un admin con la nota más razonada del mundo.
    _require_revisable(proposal)

    retest = proposal.admin_retest_json or {}
    if not (retest.get("hash_matches") and _is_recent_retest(retest.get("retested_at"))):
        raise HTTPException(
            status_code=422,
            detail={"code": "HASH_MISMATCH", "message": "Se requiere un admin-retest reciente con hash_matches=True."},
        )

    template: HubReportTemplate | None = await session.get(HubReportTemplate, body.target_global_template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Target global template not found")

    admin_uuid = _user_to_uuid(user.user_id)
    new_version = await _create_template_version(session, template, proposal.code, admin_uuid)

    proposal.status = "approved"
    proposal.reviewer_user_id = admin_uuid
    proposal.reviewed_at = datetime.now(timezone.utc)
    if body.review_note:
        proposal.review_note = body.review_note
    # antes del commit: expire_on_commit dejaría estos atributos expirados
    template_id = template.id
    new_version_id = new_version.id
    await session.commit()

    return ApproveResponse(
        proposal_id=proposal_id,
        template_id=template_id,
        new_version_id=new_version_id,
    )


# ---------------------------------------------------------------------------
# /reject  (9R.5.6)
# ---------------------------------------------------------------------------

@router.post(
    "/{proposal_id}/reject",
    response_model=RejectResponse,
    operation_id="rejectScriptProposal",
)
async def reject_script_proposal(
    proposal_id: uuid.UUID,
    body: RejectRequest,
    user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RejectResponse:
    """El admin rechaza la propuesta y registra la nota de revisión."""
    _require_admin(user)
    proposal = await _load_proposal(proposal_id, session)

    if proposal.status != "pending_review":
        raise HTTPException(
            status_code=422,
            detail={"code": "WRONG_STATUS", "message": f"Solo se puede rechazar desde 'pending_review', status actual: '{proposal.status}'."},
        )

    proposal.status = "rejected"
    proposal.review_note = body.review_note
    proposal.reviewer_user_id = _user_to_uuid(user.user_id)
    proposal.reviewed_at = datetime.now(timezone.utc)
    await session.commit()

    return RejectResponse(
        proposal_id=proposal_id,
        status="rejected",
        review_note=body.review_note,
    )

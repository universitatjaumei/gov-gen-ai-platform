"""Perfil GENERIC_REPORT — 9R.2.1 / 9R.2.2.

Perfil obligatorio para informes no predefinidos. Propone 9 secciones estándar,
acepta Excel/PDF/texto como inputs opcionales y requiere aprobación humana en
todos los bloques IA.
"""
from __future__ import annotations

from server.app.modules.redaccion.contracts.block_io import BlockReference
from server.app.modules.redaccion.contracts.blocks import (
    AIAssistedTextBlock,
    AIRewriteBlock,
    AISummaryBlock,
    CitationBlock,
    DeterministicDataBlock,
    ReviewGateBlock,
    StaticTextBlock,
    TableBlock,
    UserInputBlock,
)
from server.app.modules.redaccion.contracts.inputs import InputContract, InputSlot
from server.app.modules.redaccion.contracts.template import (
    AIBlockPolicy,
    ExportPolicy,
    ReportTemplateSpec,
    ReviewPolicy,
    SectionContract,
    ReportUIContract,
    UISection,
)
from server.app.modules.redaccion.contracts.ui import ReportUIContract, UISection
from server.app.modules.redaccion.profiles.registry import ExtractionPipelineId

_REVIEW_POLICY_ID = "default_review_policy"
_AI_PROMPT_ID = "generic_report_v1"


def _build_default_spec() -> ReportTemplateSpec:
    # ── Bloques ──────────────────────────────────────────────────────────────
    blocks = [
        # Secció 1: Títol i dades de context
        StaticTextBlock(id="b_title", title="Títol de l'informe", order=1),
        UserInputBlock(id="b_context_data", title="Dades de context", order=2),
        # Secció 2: Objectiu
        UserInputBlock(id="b_objective", title="Objectiu de l'informe", order=3),
        # Secció 3: Context
        UserInputBlock(id="b_context_text", title="Context (text lliure)", order=4),
        AIRewriteBlock(
            id="b_context_ai",
            title="Context (millora assistida, opcional)",
            order=5,
            required=False,
            depends_on=[BlockReference(block_id="b_context_text")],
            ai_prompt_template_id=_AI_PROMPT_ID,
            review_policy_id=_REVIEW_POLICY_ID,
        ),
        # Secció 4: Fonts aportades
        DeterministicDataBlock(
            id="b_sources",
            title="Fonts i documents aportats",
            order=6,
            source_pipeline="MANUAL",
        ),
        # Secció 5: Dades extretes
        DeterministicDataBlock(
            id="b_data",
            title="Dades extretes",
            order=7,
            source_pipeline="EXCEL",
        ),
        TableBlock(
            id="b_data_table",
            title="Taula de dades",
            order=8,
            depends_on=[BlockReference(block_id="b_data")],
            data_block_ref="b_data",
        ),
        # Secció 6: Anàlisi assistit
        AIAssistedTextBlock(
            id="b_analysis",
            title="Anàlisi assistit",
            order=9,
            required=True,
            depends_on=[BlockReference(block_id="b_data")],
            ai_prompt_template_id=_AI_PROMPT_ID,
            review_policy_id=_REVIEW_POLICY_ID,
        ),
        ReviewGateBlock(
            id="b_analysis_gate",
            title="Porta de revisió — Anàlisi",
            order=10,
            depends_on=[BlockReference(block_id="b_analysis")],
            review_policy_id=_REVIEW_POLICY_ID,
        ),
        # Secció 7: Conclusions
        AISummaryBlock(
            id="b_conclusions",
            title="Conclusions",
            order=11,
            required=True,
            depends_on=[BlockReference(block_id="b_analysis")],
            ai_prompt_template_id=_AI_PROMPT_ID,
            review_policy_id=_REVIEW_POLICY_ID,
        ),
        ReviewGateBlock(
            id="b_conclusions_gate",
            title="Porta de revisió — Conclusions",
            order=12,
            depends_on=[BlockReference(block_id="b_conclusions")],
            review_policy_id=_REVIEW_POLICY_ID,
        ),
        # Secció 8: Recomanacions
        UserInputBlock(id="b_recommendations", title="Recomanacions (text lliure)", order=13),
        AIRewriteBlock(
            id="b_recommendations_ai",
            title="Recomanacions (millora assistida, opcional)",
            order=14,
            required=False,
            depends_on=[BlockReference(block_id="b_recommendations")],
            ai_prompt_template_id=_AI_PROMPT_ID,
            review_policy_id=_REVIEW_POLICY_ID,
        ),
        # Secció 9: Annexos
        CitationBlock(
            id="b_citations",
            title="Annexos i fonts",
            order=15,
            source_block_refs=["b_sources", "b_data", "b_analysis"],
        ),
    ]

    # ── Seccions ─────────────────────────────────────────────────────────────
    sections = [
        SectionContract(id="s1", title="Títol i dades de context", order=1,
                        block_ids=["b_title", "b_context_data"]),
        SectionContract(id="s2", title="Objectiu de l'informe", order=2,
                        block_ids=["b_objective"]),
        SectionContract(id="s3", title="Context", order=3,
                        block_ids=["b_context_text", "b_context_ai"]),
        SectionContract(id="s4", title="Fonts aportades", order=4,
                        block_ids=["b_sources"]),
        SectionContract(id="s5", title="Dades extretes", order=5,
                        block_ids=["b_data", "b_data_table"]),
        SectionContract(id="s6", title="Anàlisi assistit", order=6,
                        block_ids=["b_analysis", "b_analysis_gate"]),
        SectionContract(id="s7", title="Conclusions", order=7,
                        block_ids=["b_conclusions", "b_conclusions_gate"]),
        SectionContract(id="s8", title="Recomanacions", order=8,
                        block_ids=["b_recommendations", "b_recommendations_ai"]),
        SectionContract(id="s9", title="Annexos / fonts", order=9,
                        block_ids=["b_citations"]),
    ]

    # ── Input contract ────────────────────────────────────────────────────────
    input_contract = InputContract(
        required_slots=[],
        optional_slots=[
            InputSlot(
                slot_id="datos_excel",
                kind="excel",
                label={"es": "Datos Excel", "ca": "Dades Excel", "en": "Excel Data"},
                required=False,
                multiple=False,
            ),
            InputSlot(
                slot_id="memoria_pdf",
                kind="pdf",
                label={"es": "Memoria PDF", "ca": "Memòria PDF", "en": "PDF Report"},
                required=False,
                multiple=False,
                max_size_mb=50,
            ),
            InputSlot(
                slot_id="notas",
                kind="text",
                label={"es": "Notas adicionales", "ca": "Notes addicionals", "en": "Additional notes"},
                required=False,
                multiple=False,
            ),
        ],
    )

    # ── UI contract (mínimo, se expande en 9R.7) ──────────────────────────────
    ui_contract = ReportUIContract(
        wizard_steps=[UISection(id=s.id, title=s.title, order=s.order) for s in sections],
        dropzones=[],
        manual_fields=[],
        block_editor_enabled=True,
        ai_review_panel_enabled=True,
        preview_layout="markdown",
    )

    return ReportTemplateSpec(
        sections=sections,
        blocks=blocks,
        input_contract=input_contract,
        ui_contract=ui_contract,
        ai_block_policy=AIBlockPolicy.REQUIRED_REVIEW,
        review_policy=ReviewPolicy.REQUIRED,
        export_policy=ExportPolicy.DOCX,
    )


class GenericReportProfile:
    profile_id: str = "GENERIC_REPORT"

    def default_spec(self) -> ReportTemplateSpec:
        return _build_default_spec()

    def applicable_pipelines(self) -> list[ExtractionPipelineId]:
        return ["EXCEL", "PDF_TEXT", "PDF_TABLE", "MANUAL"]

    def review_policy(self) -> ReviewPolicy:
        return ReviewPolicy.REQUIRED

    def ai_block_policy(self) -> AIBlockPolicy:
        return AIBlockPolicy.REQUIRED_REVIEW

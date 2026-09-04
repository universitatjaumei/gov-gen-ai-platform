"""9R.4.2 — DraftValidator: validación estructural + normalización.

Tests RED → GREEN.
"""
from __future__ import annotations

import pytest

from server.app.modules.redaccion.contracts.blocks import (
    AIAssistedTextBlock,
    ChartBlock,
    DeterministicDataBlock,
    ReviewGateBlock,
    StaticTextBlock,
    TableBlock,
)
from server.app.modules.redaccion.contracts.block_io import BlockReference
from server.app.modules.redaccion.contracts.drafts import ReportTemplateDraft
from server.app.modules.redaccion.contracts.inputs import InputContract
from server.app.modules.redaccion.contracts.template import SectionContract


def _minimal_draft(**overrides) -> ReportTemplateDraft:
    data_block = DeterministicDataBlock(id="b_data", title="Dades", source_pipeline="EXCEL")
    ai_block = AIAssistedTextBlock(
        id="b_ai", title="Anàlisi",
        ai_prompt_template_id="generic_report_v1",
        review_policy_id="rp-1",
        depends_on=[BlockReference(block_id="b_data")],
    )
    gate = ReviewGateBlock(
        id="b_gate", title="Porta",
        review_policy_id="rp-1",
        depends_on=[BlockReference(block_id="b_ai")],
    )
    defaults = dict(
        proposed_profile="GENERIC_REPORT",
        proposed_sections=[
            SectionContract(id="s1", title="Anàlisi", order=1,
                            block_ids=["b_data", "b_ai", "b_gate"]),
        ],
        proposed_blocks=[data_block, ai_block, gate],
        proposed_inputs=InputContract(required_slots=[], optional_slots=[]),
        rationale="Test draft",
        model_used="gpt-4o",
        prompt_version="v1",
    )
    defaults.update(overrides)
    return ReportTemplateDraft(**defaults)


class TestDraftValidator:
    def test_invalid_llm_draft_is_rejected(self):
        """profile_id desconocido → result.ok=False con error en proposed_profile."""
        from server.app.modules.redaccion.services.draft_validator import DraftValidator

        draft = _minimal_draft(proposed_profile="INVENTED_PROFILE")
        validator = DraftValidator()
        result = validator.validate(draft)

        assert result.ok is False
        assert any("proposed_profile" in e.field for e in result.errors)

    def test_unknown_block_type_is_rejected(self):
        """depends_on referencia un block_id que no existe en proposed_blocks → error."""
        from server.app.modules.redaccion.services.draft_validator import DraftValidator

        orphan_block = AIAssistedTextBlock(
            id="b_orphan", title="Orphan",
            ai_prompt_template_id="p1", review_policy_id="rp-1",
            depends_on=[BlockReference(block_id="b_nonexistent")],
        )
        gate = ReviewGateBlock(
            id="b_gate", title="Porta", review_policy_id="rp-1",
            depends_on=[BlockReference(block_id="b_orphan")],
        )
        draft = _minimal_draft(
            proposed_sections=[SectionContract(
                id="s1", title="S", order=1, block_ids=["b_orphan", "b_gate"],
            )],
            proposed_blocks=[orphan_block, gate],
        )
        validator = DraftValidator()
        result = validator.validate(draft)

        assert result.ok is False
        assert any("b_nonexistent" in e.message for e in result.errors)

    def test_chart_without_data_block_is_rejected(self):
        """ChartBlock cuyo data_block_ref no apunta a ningún DETERMINISTIC_DATA → error."""
        from server.app.modules.redaccion.services.draft_validator import DraftValidator

        chart = ChartBlock(id="b_chart", title="Gràfic", data_block_ref="b_missing")
        draft = _minimal_draft(
            proposed_sections=[SectionContract(
                id="s1", title="S", order=1, block_ids=["b_chart"],
            )],
            proposed_blocks=[chart],
        )
        validator = DraftValidator()
        result = validator.validate(draft)

        assert result.ok is False
        assert any("b_chart" in e.field or "data_block_ref" in e.field
                   for e in result.errors)

    def test_ai_block_without_review_gate_is_rejected(self):
        """Draft con bloque AI pero sin REVIEW_GATE → error."""
        from server.app.modules.redaccion.services.draft_validator import DraftValidator

        data_block = DeterministicDataBlock(id="b_data", title="D", source_pipeline="EXCEL")
        ai_block = AIAssistedTextBlock(
            id="b_ai", title="AI",
            ai_prompt_template_id="p1", review_policy_id="rp-1",
            depends_on=[BlockReference(block_id="b_data")],
        )
        draft = _minimal_draft(
            proposed_sections=[SectionContract(
                id="s1", title="S", order=1, block_ids=["b_data", "b_ai"],
            )],
            proposed_blocks=[data_block, ai_block],
        )
        validator = DraftValidator()
        result = validator.validate(draft)

        assert result.ok is False
        assert any("REVIEW_GATE" in e.message for e in result.errors)

    def test_draft_normalizer_assigns_unique_block_ids(self):
        """Bloques con IDs duplicados reciben IDs únicos en el normalized_draft."""
        from server.app.modules.redaccion.services.draft_validator import DraftValidator

        b1 = StaticTextBlock(id="dup", title="Primera")
        b2 = StaticTextBlock(id="dup", title="Segunda")  # ID duplicado
        gate = ReviewGateBlock(id="b_gate", title="Porta", review_policy_id="rp-1")
        ai = AIAssistedTextBlock(
            id="b_ai", title="AI",
            ai_prompt_template_id="p1", review_policy_id="rp-1",
        )
        draft = ReportTemplateDraft(
            proposed_profile="GENERIC_REPORT",
            proposed_sections=[SectionContract(
                id="s1", title="S", order=1,
                block_ids=["dup", "dup", "b_ai", "b_gate"],
            )],
            proposed_blocks=[b1, b2, ai, gate],
            proposed_inputs=InputContract(required_slots=[], optional_slots=[]),
            rationale="Test",
            model_used="m",
            prompt_version="v1",
        )
        validator = DraftValidator()
        result = validator.validate(draft)

        assert result.ok is True
        ids = [b.id for b in result.normalized_draft.proposed_blocks]
        assert len(ids) == len(set(ids)), "Block IDs must be unique after normalization"

    def test_draft_normalizer_orders_blocks_by_section(self):
        """Los bloques del normalized_draft siguen el orden definido en las secciones."""
        from server.app.modules.redaccion.services.draft_validator import DraftValidator

        b_a = StaticTextBlock(id="b_a", title="Primero en sección", order=0)
        b_b = StaticTextBlock(id="b_b", title="Segundo en sección", order=0)
        gate = ReviewGateBlock(id="b_gate", title="Porta", review_policy_id="rp-1")
        ai = AIAssistedTextBlock(
            id="b_ai", title="AI",
            ai_prompt_template_id="p1", review_policy_id="rp-1",
        )
        # Sections declare: s1=[b_b, b_a], s2=[b_ai, b_gate]
        draft = ReportTemplateDraft(
            proposed_profile="GENERIC_REPORT",
            proposed_sections=[
                SectionContract(id="s1", title="S1", order=1, block_ids=["b_b", "b_a"]),
                SectionContract(id="s2", title="S2", order=2, block_ids=["b_ai", "b_gate"]),
            ],
            # Blocks passed in reverse section order
            proposed_blocks=[gate, ai, b_a, b_b],
            proposed_inputs=InputContract(required_slots=[], optional_slots=[]),
            rationale="Test order",
            model_used="m",
            prompt_version="v1",
        )
        validator = DraftValidator()
        result = validator.validate(draft)

        assert result.ok is True
        ids = [b.id for b in result.normalized_draft.proposed_blocks]
        assert ids.index("b_b") < ids.index("b_a")
        assert ids.index("b_a") < ids.index("b_ai")
        assert ids.index("b_ai") < ids.index("b_gate")

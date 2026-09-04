"""9R.1.2 — InputContract + BlockContract (discriminated union) + ReportUIContract.

Tests RED → GREEN. Verifica el discriminador de bloque, restricciones por kind y
serialización OpenAPI para el frontend Orval.
"""
from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from server.app.modules.redaccion.contracts.blocks import (
    AIAssistedTextBlock,
    AISummaryBlock,
    AIRewriteBlock,
    BlockContract,
    ChartBlock,
    CitationBlock,
    DeterministicDataBlock,
    ReviewGateBlock,
    StaticTextBlock,
    TableBlock,
    UserInputBlock,
)
from server.app.modules.redaccion.contracts.inputs import InputContract, InputSlot
from server.app.modules.redaccion.contracts.ui import (
    ReportUIContract,
    UIDropzoneDescriptor,
    UIFieldDescriptor,
    UISection,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_adapter = TypeAdapter(BlockContract)


def _static(id_: str = "b1", title: str = "Títol") -> StaticTextBlock:
    return StaticTextBlock(id=id_, title=title)


def _ai_block(id_: str = "b_ai") -> AIAssistedTextBlock:
    return AIAssistedTextBlock(
        id=id_,
        title="Text IA",
        ai_prompt_template_id="tmpl-001",
        review_policy_id="rp-001",
    )


def _slot(kind: str = "pdf", **kw) -> InputSlot:
    defaults = dict(
        slot_id="doc",
        kind=kind,
        label={"es": "Document", "ca": "Document", "en": "Document"},
        required=True,
        multiple=False,
    )
    defaults.update(kw)
    return InputSlot(**defaults)


# ---------------------------------------------------------------------------
# BlockContract — discriminated union
# ---------------------------------------------------------------------------

class TestBlockContractDiscriminator:
    def test_block_contract_discriminator_by_kind(self):
        block = _adapter.validate_python({"kind": "STATIC_TEXT", "id": "b1", "title": "T"})
        assert isinstance(block, StaticTextBlock)
        assert block.kind == "STATIC_TEXT"

    def test_discriminator_resolves_ai_assisted_text(self):
        block = _adapter.validate_python({
            "kind": "AI_ASSISTED_TEXT",
            "id": "b2",
            "title": "T",
            "ai_prompt_template_id": "p1",
            "review_policy_id": "r1",
        })
        assert isinstance(block, AIAssistedTextBlock)

    def test_unknown_block_kind_is_rejected(self):
        with pytest.raises(ValidationError):
            _adapter.validate_python({"kind": "MADE_UP_KIND", "id": "b1", "title": "T"})

    def test_block_contract_is_serializable_and_appears_in_openapi(self):
        schema = _adapter.json_schema()
        # Pydantic v2 produces anyOf/oneOf with a discriminator mapping
        body = str(schema)
        assert "discriminator" in body or "anyOf" in body or "oneOf" in body
        assert "StaticTextBlock" in body or "STATIC_TEXT" in body


class TestBlockKindConstraints:
    def test_ai_block_requires_review_policy_reference(self):
        with pytest.raises(ValidationError):
            AIAssistedTextBlock(
                id="b1", title="T",
                ai_prompt_template_id="p1",
                # review_policy_id intentionally missing
            )

    def test_data_block_requires_source_pipeline(self):
        with pytest.raises(ValidationError):
            DeterministicDataBlock(
                id="b1", title="T",
                # source_pipeline intentionally missing
            )

    def test_chart_block_requires_data_block_ref(self):
        with pytest.raises(ValidationError):
            ChartBlock(id="b1", title="T")

    def test_table_block_requires_data_block_ref(self):
        with pytest.raises(ValidationError):
            TableBlock(id="b1", title="T")

    def test_review_gate_block_requires_review_policy_id(self):
        with pytest.raises(ValidationError):
            ReviewGateBlock(id="b1", title="T")

    def test_citation_block_defaults_to_empty_source_refs(self):
        cb = CitationBlock(id="c1", title="Cites")
        assert cb.source_block_refs == []

    def test_static_text_block_minimal_fields(self):
        b = StaticTextBlock(id="s1", title="Intro")
        assert b.kind == "STATIC_TEXT"
        assert b.depends_on == []
        assert not b.required


# ---------------------------------------------------------------------------
# InputContract + InputSlot
# ---------------------------------------------------------------------------

class TestInputContract:
    def test_input_slot_pdf_accepts_max_size_mb(self):
        slot = _slot(kind="pdf", max_size_mb=20)
        assert slot.max_size_mb == 20
        assert slot.kind == "pdf"

    def test_input_slot_excel_validates_required_columns_schema(self):
        slot = _slot(
            kind="excel",
            validation={"required_columns": ["nombre", "importe", "fecha"]},
        )
        assert slot.validation["required_columns"] == ["nombre", "importe", "fecha"]

    def test_input_slot_unknown_kind_is_rejected(self):
        with pytest.raises(ValidationError):
            _slot(kind="mp3")

    def test_input_slot_label_supports_multiple_locales(self):
        slot = _slot(label={"es": "Fichero", "ca": "Fitxer", "en": "File"})
        assert slot.label["ca"] == "Fitxer"

    def test_input_contract_defaults_to_empty_slots(self):
        contract = InputContract()
        assert contract.required_slots == []
        assert contract.optional_slots == []

    def test_input_contract_with_slots(self):
        contract = InputContract(
            required_slots=[_slot(slot_id="pdf1")],
            optional_slots=[_slot(slot_id="xls1", kind="excel", required=False)],
        )
        assert len(contract.required_slots) == 1
        assert len(contract.optional_slots) == 1


# ---------------------------------------------------------------------------
# ReportUIContract
# ---------------------------------------------------------------------------

class TestReportUIContract:
    def test_ui_contract_renders_wizard_steps_in_order(self):
        contract = ReportUIContract(
            wizard_steps=[
                UISection(id="s2", title="Pas 2", order=2),
                UISection(id="s1", title="Pas 1", order=1),
            ],
            dropzones=[UIDropzoneDescriptor(slot_id="doc", label={"es": "Documento"})],
            manual_fields=[],
            block_editor_enabled=True,
            ai_review_panel_enabled=False,
            preview_layout="markdown",
        )
        # Contract stores as provided; consumer is responsible for sorting by order
        assert [s.id for s in contract.wizard_steps] == ["s2", "s1"]

    def test_ui_contract_rejects_unknown_preview_layout(self):
        with pytest.raises(ValidationError):
            ReportUIContract(
                wizard_steps=[],
                dropzones=[],
                manual_fields=[],
                block_editor_enabled=False,
                ai_review_panel_enabled=False,
                preview_layout="powerpoint",  # not in Literal
            )

    def test_ui_field_descriptor_minimal(self):
        field = UIFieldDescriptor(slot_id="nombre", label={"es": "Nombre"}, field_type="text")
        assert field.field_type == "text"

    def test_ui_dropzone_descriptor_minimal(self):
        dz = UIDropzoneDescriptor(slot_id="memoria", label={"es": "Memoria"})
        assert dz.slot_id == "memoria"

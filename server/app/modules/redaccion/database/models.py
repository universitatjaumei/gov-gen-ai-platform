"""Modelos ORM para el módulo de redacción — 9R.1.4.

Todos usan HubOperationalBase (edge). Sin relationship() cross-base.
hub_report_template_versions es append-only: no hay UPDATE en el repo.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from server.app.modules.agents_hub.database.base import HubOperationalBase


def _now() -> datetime:
    return datetime.now(timezone.utc)


class HubReportTemplate(HubOperationalBase):
    """Plantilla de informe. El campo current_version_id se gestiona a nivel de app."""

    __tablename__ = "hub_report_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_profile: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    owner_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    is_global: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Sin FK a hub_report_template_versions para evitar circularidad; se aplica en app
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )


class HubReportTemplateVersion(HubOperationalBase):
    """Versión de plantilla. Append-only: el repo NO expone método update."""

    __tablename__ = "hub_report_template_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_report_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    spec_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class HubRunManifest(HubOperationalBase):
    """Registro inmutable de una ejecución de redacción."""

    __tablename__ = "hub_run_manifests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_report_template_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    report_profile: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    # Completado solo al ensamblar; null mientras el manifest está en curso
    final_document_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )


class HubWorkspace(HubOperationalBase):
    """Workspace de redacción activo.

    status puede ser: draft | ingesting | extracting | drafting | in_review |
                      assembled | exported | error | archived
    parent_workspace_id: apunta al workspace original cuando éste fue migrado a nueva versión.
    archived_reason: razón textual del archivado (ej. "migrated_to_{new_id}").
    """

    __tablename__ = "hub_workspaces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    template_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_report_template_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    inputs_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    warnings_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    # Sin FK a hub_run_manifests para evitar FK circular; se aplica en app
    run_manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    # Versionado: apunta al workspace original tras una migración (9R.4.4)
    parent_workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    archived_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Optimistic concurrency (1C.1): incrementado en cada PATCH /state.
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Modo NER reversible (13.1): off | detect_only | replace | replace_with_disposition_7.
    anonymization_mode: Mapped[str] = mapped_column(
        String(40), nullable=False, default="replace"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )


class HubWorkspaceBlock(HubOperationalBase):
    """Estado de un bloque dentro de un workspace. UNIQUE(workspace_id, block_id)."""

    __tablename__ = "hub_workspace_blocks"
    __table_args__ = (
        UniqueConstraint("workspace_id", "block_id", name="uq_workspace_block"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    block_id: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    content_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    citations_json: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    approval_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    failure_kind: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Optimistic concurrency por bloque (1C.1): expected_block_version del BlockUpdate.
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )


class HubScriptProposal(HubOperationalBase):
    """Propuesta de script de extracción generada por LLM y auditada.

    Estados (9R.5.5 cubre proposed/tested/rejected; los demás llegan en 9R.5.6):
      proposed | tested | pending_review | approved | rejected
    """

    __tablename__ = "hub_script_proposals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    proposer_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    target_owner_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    target_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    prompt_nl: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    audit_result_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    test_data_ref: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    test_data_is_anonymized: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    test_data_anonymization_map: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    test_data_kind: Mapped[str | None] = mapped_column(String(20), nullable=True)
    test_result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    test_result_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    test_validated_by_proposer_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="proposed", index=True)
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_retest_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )


class HubWorkspaceAuditEvent(HubOperationalBase):
    """Registro de auditoría de transiciones de bloque y eventos de workspace."""

    __tablename__ = "hub_workspace_audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("hub_workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    block_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    event: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, default="system")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

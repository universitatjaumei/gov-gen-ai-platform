"""redaccion_tables_9r14

Revision ID: m4b5c6d7e8f9
Revises: 08997b81d33c
Create Date: 2026-05-12

Cambios (Prompt 9R.1.4):
Tablas de redacción asistida (bloque 9R):
- hub_report_templates
- hub_report_template_versions  (append-only)
- hub_workspaces
- hub_workspace_blocks           (UNIQUE workspace_id + block_id)
- hub_run_manifests

Nota: rama l2f3a4b5c6d7 (public_graph_fields_9b2) tiene un bug preexistente que impide
aplicarla (hub_chatbots no existe en esa rama). Esta migración construye sobre 08997b81d33c.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "m4b5c6d7e8f9"
down_revision: Union[str, tuple] = "08997b81d33c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hub_report_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("report_profile", sa.String(100), nullable=False),
        sa.Column("owner_kind", sa.String(20), nullable=False),
        sa.Column("owner_id", UUID(as_uuid=True), nullable=True),
        sa.Column("is_global", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("current_version_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_hub_report_templates_report_profile",
        "hub_report_templates",
        ["report_profile"],
    )

    op.create_table(
        "hub_report_template_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("hub_report_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("spec_json", JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "ix_hub_report_template_versions_template_id",
        "hub_report_template_versions",
        ["template_id"],
    )

    op.create_table(
        "hub_workspaces",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "template_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("hub_report_template_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("owner_id", UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("inputs_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("warnings_json", JSONB, nullable=False, server_default="[]"),
        sa.Column("run_manifest_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "hub_workspace_blocks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("hub_workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("block_id", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("content_json", JSONB, nullable=True),
        sa.Column("citations_json", JSONB, nullable=True),
        sa.Column("approval_json", JSONB, nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("workspace_id", "block_id", name="uq_workspace_block"),
    )
    op.create_index(
        "ix_hub_workspace_blocks_workspace_id",
        "hub_workspace_blocks",
        ["workspace_id"],
    )

    op.create_table(
        "hub_run_manifests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("hub_workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "template_version_id",
            UUID(as_uuid=True),
            sa.ForeignKey("hub_report_template_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("report_profile", sa.String(100), nullable=False),
        sa.Column("payload_json", JSONB, nullable=False),
        sa.Column("final_document_hash", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_hub_run_manifests_workspace_id",
        "hub_run_manifests",
        ["workspace_id"],
    )


def downgrade() -> None:
    op.drop_table("hub_run_manifests")
    op.drop_table("hub_workspace_blocks")
    op.drop_table("hub_workspaces")
    op.drop_table("hub_report_template_versions")
    op.drop_table("hub_report_templates")

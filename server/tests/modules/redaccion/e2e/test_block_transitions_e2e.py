"""Tests 9R.8.2 — E2E de transiciones de bloque (RED → GREEN).

Escenarios de varios pasos que cubren el flujo completo de HITL:
rechazar / regenerar / aprobar / editar / bloquear un bloque.

Deploy: edge
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.app.modules.redaccion.database.models import (
    HubWorkspace,
    HubWorkspaceAuditEvent,
    HubWorkspaceBlock,
)
from server.app.api.deps import get_session

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_JWT_ENV = {
    "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-characters-long",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRATION_MINUTES": "60",
}

OWNER_ID = uuid.uuid4()
WORKSPACE_ID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_token(user_id: str, role: str = "user") -> str:
    import os
    os.environ.update(_JWT_ENV)
    from server.app.core.auth import UserInfo, create_token
    return create_token(UserInfo(user_id=user_id, email="user@test.com", role=role))


def _auth(role: str = "user") -> dict:
    return {"Authorization": f"Bearer {_make_token(str(OWNER_ID), role)}"}


def _make_workspace(status: str = "in_review") -> HubWorkspace:
    ws = MagicMock(spec=HubWorkspace)
    ws.id = WORKSPACE_ID
    ws.owner_id = OWNER_ID
    ws.status = status
    ws.template_version_id = uuid.uuid4()
    ws.created_at = datetime.now(timezone.utc)
    ws.updated_at = datetime.now(timezone.utc)
    return ws


def _make_block(block_id: str, status: str) -> HubWorkspaceBlock:
    blk = MagicMock(spec=HubWorkspaceBlock)
    blk.id = uuid.uuid4()
    blk.workspace_id = WORKSPACE_ID
    blk.block_id = block_id
    blk.kind = "AI_ASSISTED_TEXT"
    blk.status = status
    blk.content_json = {"text": f"AI draft for {block_id}"}
    blk.citations_json = None
    blk.approval_json = None
    blk.failure_kind = None
    blk.last_error_message = None
    blk.retry_attempts = 0
    blk.updated_at = datetime.now(timezone.utc)
    return blk


def _make_session(workspace: HubWorkspace, block: HubWorkspaceBlock) -> AsyncMock:
    """Session mock that routes get() to workspace and execute() to block.

    The same mock objects are returned across all requests in a test,
    so attribute changes (e.g. block.status) persist between HTTP calls.
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()

    async def _get(model, pk):
        if model is HubWorkspace:
            return workspace
        return None

    session.get = AsyncMock(side_effect=_get)

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = block
    session.execute = AsyncMock(return_value=result_mock)

    return session


def _build_app(session_mock) -> FastAPI:
    from server.app.routers.redaccion.workspaces_router import router

    async def _override():
        yield session_mock

    app = FastAPI()
    app.dependency_overrides[get_session] = _override
    app.include_router(router, prefix="/api/v1")
    return app


# ---------------------------------------------------------------------------
# E2E tests
# ---------------------------------------------------------------------------

def test_e2e_user_approves_all_blocks_and_assembles():
    """Full happy path: approve a block, then resume workspace for final assembly."""
    workspace = _make_workspace("in_review")
    block = _make_block("b_intro", "needs_review")
    session = _make_session(workspace, block)
    client = TestClient(_build_app(session))

    # Step 1: approve the block
    resp = client.patch(
        f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/blocks/b_intro/approve",
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["block_id"] == "b_intro"
    assert block.status == "approved"

    # Step 2: resume workspace (triggers FinalAssemblerNode re-entry)
    resp = client.post(
        f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/resume",
        headers=_auth(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == str(WORKSPACE_ID)
    assert data["status"] == "drafting"
    assert workspace.status == "drafting"

    # Audit events recorded for both transitions
    assert session.commit.await_count >= 2


def test_e2e_user_rejects_ai_block_then_regenerates_then_approves():
    """Full review cycle: reject → regenerate (graph re-runs) → approve."""
    workspace = _make_workspace("in_review")
    block = _make_block("b_summary", "needs_review")
    session = _make_session(workspace, block)
    client = TestClient(_build_app(session))
    headers = _auth()

    # Step 1: reject
    resp = client.patch(
        f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/blocks/b_summary/reject",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert block.status == "rejected"

    # Step 2: regenerate (rejected → ai_generated)
    resp = client.patch(
        f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/blocks/b_summary/regenerate",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ai_generated"
    assert block.status == "ai_generated"

    # Simulate AIAssistDraftNode re-ran and put block back in needs_review
    block.status = "needs_review"

    # Step 3: approve
    resp = client.patch(
        f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/blocks/b_summary/approve",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert block.status == "approved"


def test_e2e_user_edits_ai_block_content_and_original_preserved():
    """Edit overrides content and audit trail preserves original AI text."""
    workspace = _make_workspace("in_review")
    block = _make_block("b_body", "needs_review")
    original_text = "Original AI text"
    block.content_json = {"text": original_text}
    session = _make_session(workspace, block)
    client = TestClient(_build_app(session))
    headers = _auth()

    new_content = {"text": "User edited text"}

    # Step 1: edit block content
    resp = client.patch(
        f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/blocks/b_body/edit",
        json={"content": new_content},
        headers=headers,
    )
    assert resp.status_code == 200
    # SEG.4 — la edición ya no borra el rastro: el texto queda sobrescrito, y junto a él quién
    # editó, cuándo y qué había propuesto el modelo. Antes esa evidencia vivía sólo en el
    # registro de auditoría, que ninguna pantalla enseña.
    assert block.content_json["text"] == new_content["text"]
    assert block.content_json["original_ai_text"] == original_text
    assert block.content_json["edited_by"] == "user@test.com"
    assert block.content_json["edited_at"]

    # Verify audit event preserves original content
    added_objects = [c.args[0] for c in session.add.call_args_list]
    audit_events = [o for o in added_objects if isinstance(o, HubWorkspaceAuditEvent)]
    assert len(audit_events) >= 1
    assert any(
        ae.metadata_json.get("original_content") == {"text": original_text}
        for ae in audit_events
    )

    # Step 2: approve the edited block
    resp = client.patch(
        f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/blocks/b_body/approve",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert block.status == "approved"
    # Final content is the user-edited version, not original AI text
    assert block.content_json["text"] == new_content["text"]


def test_e2e_user_with_missing_input_resumes_after_upload():
    """User uploads missing document; workspace resumes from review gate."""
    workspace = _make_workspace("in_review")
    block = _make_block("b_data", "missing_input")
    session = _make_session(workspace, block)
    client = TestClient(_build_app(session))
    headers = _auth()

    # Simulate ingestion pipeline ran after user uploaded the missing document
    block.status = "extracted"

    # Resume workspace from review gate
    resp = client.post(
        f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/resume",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == str(WORKSPACE_ID)
    assert data["status"] == "drafting"

    # Block retains extracted status (graph will pick up from here)
    assert block.status == "extracted"
    assert workspace.status == "drafting"


def test_e2e_admin_locks_block_to_prevent_further_changes():
    """Once admin approves a block, no further reject or regenerate is possible."""
    workspace = _make_workspace("in_review")
    block = _make_block("b_legal", "needs_review")
    session = _make_session(workspace, block)
    client = TestClient(_build_app(session))
    # Admin is the workspace owner (OWNER_ID) so the ownership check passes
    admin_headers = _auth(role="admin")

    # Admin approves the block
    resp = client.patch(
        f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/blocks/b_legal/approve",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert block.status == "approved"

    # Reject an approved block → invalid transition (approved → {locked} only)
    resp = client.patch(
        f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/blocks/b_legal/reject",
        headers=admin_headers,
    )
    assert resp.status_code == 422

    # Regenerate an approved block → also invalid
    resp = client.patch(
        f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/blocks/b_legal/regenerate",
        headers=admin_headers,
    )
    assert resp.status_code == 422

    # Block remains approved after failed attempts
    assert block.status == "approved"

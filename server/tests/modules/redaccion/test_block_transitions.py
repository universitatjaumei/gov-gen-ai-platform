"""Tests 9R.8.1 — Block Transition Endpoints (RED → GREEN).

Deploy: edge
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.app.modules.redaccion.database.models import HubWorkspace, HubWorkspaceBlock
from server.app.api.deps import get_session

_JWT_ENV = {
    "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-characters-long",
    "JWT_ALGORITHM": "HS256",
    "JWT_EXPIRATION_MINUTES": "60",
}

OWNER_ID = uuid.uuid4()
OTHER_ID = uuid.uuid4()
WORKSPACE_ID = uuid.uuid4()
BLOCK_STR_ID = "block-intro"


def _make_token(user_id: str, role: str = "user") -> str:
    import os
    os.environ.update(_JWT_ENV)
    from server.app.core.auth import UserInfo, create_token
    return create_token(UserInfo(user_id=user_id, email="user@test.com", role=role))


def _make_workspace(status: str = "in_review") -> HubWorkspace:
    ws = MagicMock(spec=HubWorkspace)
    ws.id = WORKSPACE_ID
    ws.owner_id = OWNER_ID
    ws.status = status
    ws.template_version_id = uuid.uuid4()
    ws.created_at = datetime.now(timezone.utc)
    ws.updated_at = datetime.now(timezone.utc)
    return ws


def _make_block(status: str = "needs_review") -> HubWorkspaceBlock:
    blk = MagicMock(spec=HubWorkspaceBlock)
    blk.id = uuid.uuid4()
    blk.workspace_id = WORKSPACE_ID
    blk.block_id = BLOCK_STR_ID
    blk.kind = "AI_ASSISTED_TEXT"
    blk.status = status
    blk.content_json = {"text": "Original AI text"}
    blk.citations_json = None
    blk.approval_json = None
    blk.failure_kind = None
    blk.last_error_message = None
    blk.retry_attempts = 0
    blk.updated_at = datetime.now(timezone.utc)
    return blk


def _build_app(session_mock) -> FastAPI:
    from server.app.routers.redaccion.workspaces_router import router

    async def _override():
        yield session_mock

    app = FastAPI()
    app.dependency_overrides[get_session] = _override
    app.include_router(router, prefix="/api/v1")
    return app


def _session_with_workspace_and_block(
    workspace: HubWorkspace,
    block: HubWorkspaceBlock | None,
) -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()

    # session.get(HubWorkspace, workspace_id) → workspace
    async def _get(model, pk):
        if model is HubWorkspace:
            return workspace
        return None

    session.get = AsyncMock(side_effect=_get)

    # session.execute(select(HubWorkspaceBlock)...) → result with block
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = block
    session.execute = AsyncMock(return_value=result_mock)

    return session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBlockTransitionEndpoints:

    def test_approve_block_transitions_to_approved(self):
        block = _make_block(status="needs_review")
        workspace = _make_workspace()
        session = _session_with_workspace_and_block(workspace, block)

        client = TestClient(_build_app(session))
        resp = client.patch(
            f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/blocks/{BLOCK_STR_ID}/approve",
            headers={"Authorization": f"Bearer {_make_token(str(OWNER_ID))}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["block_id"] == BLOCK_STR_ID

    def test_reject_block_transitions_to_rejected(self):
        block = _make_block(status="needs_review")
        workspace = _make_workspace()
        session = _session_with_workspace_and_block(workspace, block)

        client = TestClient(_build_app(session))
        resp = client.patch(
            f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/blocks/{BLOCK_STR_ID}/reject",
            headers={"Authorization": f"Bearer {_make_token(str(OWNER_ID))}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"

    def test_regenerate_calls_ai_node_only_for_that_block(self):
        block = _make_block(status="rejected")
        workspace = _make_workspace(status="in_review")
        session = _session_with_workspace_and_block(workspace, block)

        client = TestClient(_build_app(session))
        resp = client.patch(
            f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/blocks/{BLOCK_STR_ID}/regenerate",
            headers={"Authorization": f"Bearer {_make_token(str(OWNER_ID))}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        # REGENERATE → ai_generated
        assert data["status"] == "ai_generated"
        assert data["block_id"] == BLOCK_STR_ID

    def test_edit_block_overrides_content_and_records_original(self):
        block = _make_block(status="needs_review")
        original_content = dict(block.content_json)
        workspace = _make_workspace()
        session = _session_with_workspace_and_block(workspace, block)

        new_content = {"text": "User-edited text"}
        client = TestClient(_build_app(session))
        resp = client.patch(
            f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/blocks/{BLOCK_STR_ID}/edit",
            json={"content": new_content},
            headers={"Authorization": f"Bearer {_make_token(str(OWNER_ID))}"},
        )

        assert resp.status_code == 200
        # Block content updated
        assert block.content_json == new_content
        # Audit event saved with original content
        added_objects = [c.args[0] for c in session.add.call_args_list]
        from server.app.modules.redaccion.database.models import HubWorkspaceAuditEvent
        audit_events = [o for o in added_objects if isinstance(o, HubWorkspaceAuditEvent)]
        assert len(audit_events) >= 1
        audit = audit_events[0]
        assert audit.event == "edit"
        assert audit.metadata_json.get("original_content") == original_content

    def test_resume_workspace_continues_graph_from_review_gate(self):
        workspace = _make_workspace(status="in_review")
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        session.get = AsyncMock(return_value=workspace)

        client = TestClient(_build_app(session))
        resp = client.post(
            f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/resume",
            headers={"Authorization": f"Bearer {_make_token(str(OWNER_ID))}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["workspace_id"] == str(WORKSPACE_ID)
        # Workspace is no longer in_review after resume
        assert workspace.status != "in_review"

    def test_non_owner_cannot_transition_blocks(self):
        block = _make_block(status="needs_review")
        workspace = _make_workspace()
        session = _session_with_workspace_and_block(workspace, block)

        client = TestClient(_build_app(session))
        # OTHER_ID != OWNER_ID
        resp = client.patch(
            f"/api/v1/redaccion/workspaces/{WORKSPACE_ID}/blocks/{BLOCK_STR_ID}/approve",
            headers={"Authorization": f"Bearer {_make_token(str(OTHER_ID))}"},
        )

        assert resp.status_code == 403

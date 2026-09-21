"""9R.4.3 — Endpoints HTTP llm-drafts (propose / validate / approve).

Tests RED → GREEN. Usa TestClient + dependency overrides; sin BD real.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from server.app.core.auth.models import UserInfo
from server.app.main import app
from server.app.api.deps import get_current_user, get_session

_ADMIN = UserInfo(user_id="00000000-0000-0000-0000-000000000001",
                  email="admin@test.com", role="admin")
_USER = UserInfo(user_id="00000000-0000-0000-0000-000000000003",
                 email="user@test.com", role="user")

# Valid draft — no AI blocks so no REVIEW_GATE needed (static only)
_STATIC_DRAFT = {
    "proposed_profile": "GENERIC_REPORT",
    "proposed_sections": [
        {"id": "s1", "title": "Intro", "order": 1, "block_ids": ["b1"]},
    ],
    "proposed_blocks": [
        {"kind": "STATIC_TEXT", "id": "b1", "title": "Intro text", "content": "Hola"},
    ],
    "proposed_inputs": {"required_slots": [], "optional_slots": []},
    "rationale": "Minimal test draft",
    "model_used": "gpt-4o",
    "prompt_version": "v1",
}

# Valid draft WITH AI block + REVIEW_GATE
_AI_DRAFT = {
    "proposed_profile": "GENERIC_REPORT",
    "proposed_sections": [
        {"id": "s1", "title": "Anàlisi", "order": 1, "block_ids": ["b_ai", "b_gate"]},
    ],
    "proposed_blocks": [
        {
            "kind": "AI_ASSISTED_TEXT", "id": "b_ai", "title": "Anàlisi",
            "ai_prompt_template_id": "generic_report_v1", "review_policy_id": "rp-1",
            "depends_on": [],
        },
        {
            "kind": "REVIEW_GATE", "id": "b_gate", "title": "Porta",
            "review_policy_id": "rp-1", "depends_on": [],
        },
    ],
    "proposed_inputs": {"required_slots": [], "optional_slots": []},
    "rationale": "Draft with AI and gate",
    "model_used": "gpt-4o",
    "prompt_version": "v1",
}

# Invalid draft — no REVIEW_GATE for AI block
_INVALID_DRAFT = {
    "proposed_profile": "GENERIC_REPORT",
    "proposed_sections": [
        {"id": "s1", "title": "S", "order": 1, "block_ids": ["b_ai"]},
    ],
    "proposed_blocks": [
        {
            "kind": "AI_ASSISTED_TEXT", "id": "b_ai", "title": "AI",
            "ai_prompt_template_id": "p1", "review_policy_id": "rp-1",
            "depends_on": [],
        },
    ],
    "proposed_inputs": {"required_slots": [], "optional_slots": []},
    "rationale": "Missing REVIEW_GATE",
    "model_used": "gpt-4o",
    "prompt_version": "v1",
}


def _mock_session():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.get = AsyncMock(return_value=None)
    return session


def _session_dep(session):
    async def _gen():
        yield session
    return _gen


@pytest.fixture(autouse=True)
def reset_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


class TestLLMDraftsRouter:
    def test_llm_draft_requires_human_approval_before_persisting(self, client):
        """POST /propose returns a draft — no DB write happens."""
        from server.app.routers.redaccion.llm_drafts_router import get_llm_spec_service
        from server.app.modules.redaccion.contracts.drafts import ReportTemplateDraft

        mock_service = MagicMock()
        mock_service.propose_template = AsyncMock(
            return_value=ReportTemplateDraft(**_STATIC_DRAFT)
        )
        app.dependency_overrides[get_current_user] = lambda: _ADMIN
        app.dependency_overrides[get_llm_spec_service] = lambda: mock_service

        resp = client.post(
            "/api/v1/redaccion/llm-drafts/propose",
            json={"prompt_nl": "Informe anual d'activitats", "mode": "admin_template"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Response is a draft, not a persisted record
        assert "proposed_profile" in data
        assert "proposed_sections" in data
        assert "proposed_blocks" in data
        # No DB write — propose has no session dependency
        assert "template_id" not in data

    def test_llm_draft_preview_contains_sections_blocks_and_inputs(self, client):
        """POST /validate returns normalized draft with sections, blocks and inputs."""
        app.dependency_overrides[get_current_user] = lambda: _USER

        resp = client.post(
            "/api/v1/redaccion/llm-drafts/validate",
            json=_AI_DRAFT,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        nd = data["normalized_draft"]
        assert len(nd["proposed_sections"]) >= 1
        assert len(nd["proposed_blocks"]) >= 1
        assert "proposed_inputs" in nd

    def test_admin_can_save_llm_draft_as_template(self, client):
        """Admin POSTs a valid draft to /approve-as-template → 200 with template info."""
        session = _mock_session()
        app.dependency_overrides[get_current_user] = lambda: _ADMIN
        app.dependency_overrides[get_session] = _session_dep(session)

        resp = client.post(
            "/api/v1/redaccion/llm-drafts/approve-as-template",
            json={"draft": _STATIC_DRAFT, "name": "Informe Anual 2026", "is_global": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "template_id" in data
        assert "version_id" in data
        assert data["name"] == "Informe Anual 2026"

    def test_solo_la_plataforma_crea_plantillas_globales(self, client):
        """Un admin de organización con `is_global=True` → 403 (issue #90).

        **Este test afirmaba el defecto.** Se llamaba
        `test_non_admin_cannot_save_global_template` y su docstring decía «Partner with
        is_global=True → 403», pero el usuario que usaba era un `role="superadmin"`: el
        vocabulario viejo llamaba «partner» al superadministrador. Así que el test se leía como
        «un no-admin no puede» y en realidad afirmaba «la plataforma no puede» — que es justo lo
        que había que arreglar. Código y medida se daban la razón, como en el issue #84.

        Su fixture se retiró al corregirlo: era el único sitio que lo usaba.

        Ahora comprueba lo que dice el modelo: `owner_kind="platform"` es nivel plataforma, y ese
        nivel es del superadministrador. El caso bueno del superadministrador y el del admin con
        sus propias plantillas están en
        `test_issue90_lo_global_lo_crea_la_plataforma.py`.
        """
        session = _mock_session()
        app.dependency_overrides[get_current_user] = lambda: _ADMIN
        app.dependency_overrides[get_session] = _session_dep(session)

        resp = client.post(
            "/api/v1/redaccion/llm-drafts/approve-as-template",
            json={"draft": _STATIC_DRAFT, "name": "Global Template", "is_global": True},
        )
        assert resp.status_code == 403

    def test_user_can_use_llm_draft_as_private_workspace(self, client):
        """Any authenticated user can create a private workspace."""
        session = _mock_session()
        app.dependency_overrides[get_current_user] = lambda: _USER
        app.dependency_overrides[get_session] = _session_dep(session)

        resp = client.post(
            "/api/v1/redaccion/llm-drafts/approve-as-workspace",
            json={"draft": _STATIC_DRAFT, "name": "El meu informe"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "workspace_id" in data
        # 9R.10.2: arranca en "ingesting" (listo para subir inputs), no "draft".
        assert data["status"] == "ingesting"

    def test_approve_endpoint_rejects_invalid_draft_with_422(self, client):
        """Invalid draft (AI block without REVIEW_GATE) → 422."""
        session = _mock_session()
        app.dependency_overrides[get_current_user] = lambda: _ADMIN
        app.dependency_overrides[get_session] = _session_dep(session)

        resp = client.post(
            "/api/v1/redaccion/llm-drafts/approve-as-template",
            json={"draft": _INVALID_DRAFT, "name": "Bad Draft", "is_global": False},
        )
        assert resp.status_code == 422

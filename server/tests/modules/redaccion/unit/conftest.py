"""Fixtures para tests unitarios del módulo redacción — 1C.3."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from server.app.modules.redaccion.services.export_service import ExportService
from server.app.modules.redaccion.services.preview_builder import PreviewBuilderService


# ---------------------------------------------------------------------------
# Base mock repos
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_repos():
    repos = MagicMock()
    repos.workspace_repo = AsyncMock()
    repos.block_repo = AsyncMock()
    repos.template_version_repo = AsyncMock()
    repos.manifest_repo = AsyncMock()
    return repos


@pytest.fixture
def builder(mock_repos):
    return PreviewBuilderService(
        workspace_repo=mock_repos.workspace_repo,
        block_repo=mock_repos.block_repo,
        template_version_repo=mock_repos.template_version_repo,
        manifest_repo=mock_repos.manifest_repo,
    )


@pytest.fixture
def storage_mock():
    mock = AsyncMock()
    mock.put.return_value = None
    return mock


@pytest.fixture
def export_service(builder):
    return ExportService(builder=builder)


# ---------------------------------------------------------------------------
# Workspace helpers
# ---------------------------------------------------------------------------

def _make_workspace(template_version_id=None):
    ws = MagicMock()
    ws.id = uuid4()
    ws.template_version_id = template_version_id or uuid4()
    return ws


def _make_block(block_id: str, status: str = "approved", citations_json=None):
    b = MagicMock()
    b.block_id = block_id
    b.kind = "AI_ASSISTED_TEXT"
    b.status = status
    b.content_json = {"text": f"Contenido de {block_id}"}
    b.citations_json = citations_json or []
    return b


def _make_manifest(workspace_id=None):
    m = MagicMock()
    m.id = uuid4()
    m.workspace_id = workspace_id or uuid4()
    m.created_at = datetime.now(timezone.utc)
    return m


def _make_template_version(sections):
    tv = MagicMock()
    tv.id = uuid4()
    tv.spec_json = {
        "sections": [
            {"id": s["id"], "title": s["title"], "order": i + 1, "block_ids": s["block_ids"]}
            for i, s in enumerate(sections)
        ]
    }
    return tv


# ---------------------------------------------------------------------------
# Workspace fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def workspace_all_approved(mock_repos):
    version_id = uuid4()
    ws = _make_workspace(template_version_id=version_id)
    block = _make_block("block-1", status="approved")

    mock_repos.workspace_repo.get.return_value = ws
    mock_repos.block_repo.list.return_value = [block]
    mock_repos.template_version_repo.get.return_value = _make_template_version([
        {"id": "s1", "title": "Sección Principal", "block_ids": ["block-1"]},
    ])
    mock_repos.manifest_repo.list.return_value = [_make_manifest(workspace_id=ws.id)]
    return ws


@pytest.fixture
def workspace_with_needs_review(mock_repos):
    ws = _make_workspace()
    blocks = [
        _make_block("block-approved", status="approved"),
        _make_block("block-pending", status="needs_review"),
    ]
    mock_repos.workspace_repo.get.return_value = ws
    mock_repos.block_repo.list.return_value = blocks
    mock_repos.template_version_repo.get.return_value = _make_template_version([
        {"id": "s1", "title": "Sección", "block_ids": ["block-approved", "block-pending"]},
    ])
    mock_repos.manifest_repo.list.return_value = []
    return ws


@pytest.fixture
def workspace_with_3_sections(mock_repos):
    ws = _make_workspace()
    blocks = [
        _make_block("block-intro", status="approved"),
        _make_block("block-legal", status="locked"),
        _make_block("block-concl", status="approved"),
    ]
    mock_repos.workspace_repo.get.return_value = ws
    mock_repos.block_repo.list.return_value = blocks
    mock_repos.template_version_repo.get.return_value = _make_template_version([
        {"id": "s1", "title": "Introducción", "block_ids": ["block-intro"]},
        {"id": "s2", "title": "Marco Legal", "block_ids": ["block-legal"]},
        {"id": "s3", "title": "Conclusiones", "block_ids": ["block-concl"]},
    ])
    mock_repos.manifest_repo.list.return_value = [_make_manifest(workspace_id=ws.id)]
    return ws


@pytest.fixture
def workspace_with_citations(mock_repos):
    chunk_id = uuid4()
    ws = _make_workspace()
    block = _make_block(
        "block-cited",
        status="approved",
        citations_json=[{"chunk_id": str(chunk_id), "source_document": "doc.pdf", "page": 1}],
    )
    mock_repos.workspace_repo.get.return_value = ws
    mock_repos.block_repo.list.return_value = [block]
    mock_repos.template_version_repo.get.return_value = _make_template_version([
        {"id": "s1", "title": "Sección", "block_ids": ["block-cited"]},
    ])
    mock_repos.manifest_repo.list.return_value = [_make_manifest(workspace_id=ws.id)]
    return ws

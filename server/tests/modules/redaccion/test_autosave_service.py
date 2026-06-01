"""Tests del WorkspaceAutosaveService — 1C.1 (autosave optimista).

Estos tests no requieren PostgreSQL: la AsyncSession se mockea, y las "filas"
de workspace/bloque son objetos simples con los atributos relevantes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.app.modules.redaccion.contracts.state_update import (
    BlockUpdate,
    WorkspaceStatePatch,
)
from server.app.modules.redaccion.services.autosave_service import (
    ConflictError,
    InvalidTransitionError,
    WorkspaceAutosaveService,
    WorkspaceNotFoundError,
)


# ──────────────────────────────────────────────────────────────────
# Helpers para construir filas en memoria
# ──────────────────────────────────────────────────────────────────


def _make_workspace_row(
    workspace_id: uuid.UUID,
    owner_id: uuid.UUID,
    version: int = 3,
    status: str = "in_review",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=workspace_id,
        owner_id=owner_id,
        version=version,
        status=status,
        updated_at=datetime.now(timezone.utc),
    )


def _make_block_row(
    block_pk: uuid.UUID,
    workspace_id: uuid.UUID,
    status: str = "needs_review",
    version: int = 5,
    content: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=block_pk,
        workspace_id=workspace_id,
        block_id=f"block-{block_pk.hex[:6]}",
        kind="ai_assisted_text",
        status=status,
        content_json=content,
        version=version,
        updated_at=datetime.now(timezone.utc),
    )


def _make_session(
    *,
    workspace_row: SimpleNamespace | None,
    block_rows: list[SimpleNamespace] | None = None,
) -> AsyncMock:
    """Construye una AsyncSession mockeada que responde a los SELECTs del servicio.

    La primera execute() devuelve el workspace (scalar_one_or_none). La segunda
    devuelve la lista de bloques (scalars().all()).
    """
    block_rows = block_rows or []

    ws_result = MagicMock()
    ws_result.scalar_one_or_none = MagicMock(return_value=workspace_row)

    blocks_result = MagicMock()
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=list(block_rows))
    blocks_result.scalars = MagicMock(return_value=scalars)

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[ws_result, blocks_result])
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


# ──────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_with_correct_versions_updates_workspace_and_blocks() -> None:
    owner_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    block_pk = uuid.uuid4()

    ws_row = _make_workspace_row(ws_id, owner_id, version=3)
    block_row = _make_block_row(block_pk, ws_id, status="needs_review", version=5)
    session = _make_session(workspace_row=ws_row, block_rows=[block_row])

    service = WorkspaceAutosaveService(session=session)
    patch = WorkspaceStatePatch(
        expected_workspace_version=3,
        block_updates=[
            BlockUpdate(
                block_id=block_pk,
                state="approved",
                content={"text": "edited"},
                expected_block_version=5,
            )
        ],
    )

    result = await service.apply_patch(ws_id, str(owner_id), patch)

    assert result.workspace_version == 4
    assert result.updated_block_versions[block_pk] == 6
    assert ws_row.version == 4
    assert block_row.version == 6
    assert block_row.status == "approved"
    assert block_row.content_json == {"text": "edited"}
    session.commit.assert_awaited_once()
    session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_stale_workspace_version_returns_409() -> None:
    owner_id = uuid.uuid4()
    ws_id = uuid.uuid4()

    ws_row = _make_workspace_row(ws_id, owner_id, version=3)
    session = _make_session(workspace_row=ws_row, block_rows=[])

    service = WorkspaceAutosaveService(session=session)
    patch = WorkspaceStatePatch(expected_workspace_version=1, block_updates=[])

    with pytest.raises(ConflictError) as exc:
        await service.apply_patch(ws_id, str(owner_id), patch)

    assert exc.value.current_workspace_version == 3
    session.commit.assert_not_called()
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_patch_with_stale_block_version_returns_409_with_conflicting_ids() -> None:
    owner_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    block_pk_a = uuid.uuid4()
    block_pk_b = uuid.uuid4()

    ws_row = _make_workspace_row(ws_id, owner_id, version=3)
    block_a = _make_block_row(block_pk_a, ws_id, version=5)  # stale: client expects 4
    block_b = _make_block_row(block_pk_b, ws_id, version=2)  # fresh
    session = _make_session(workspace_row=ws_row, block_rows=[block_a, block_b])

    service = WorkspaceAutosaveService(session=session)
    patch = WorkspaceStatePatch(
        expected_workspace_version=3,
        block_updates=[
            BlockUpdate(block_id=block_pk_a, content={"x": 1}, expected_block_version=4),
            BlockUpdate(block_id=block_pk_b, content={"y": 2}, expected_block_version=2),
        ],
    )

    with pytest.raises(ConflictError) as exc:
        await service.apply_patch(ws_id, str(owner_id), patch)

    assert exc.value.current_workspace_version == 3
    assert block_pk_a in exc.value.conflicting_block_ids
    assert block_pk_b not in exc.value.conflicting_block_ids
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_patch_with_invalid_block_state_transition_returns_422() -> None:
    owner_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    block_pk = uuid.uuid4()

    ws_row = _make_workspace_row(ws_id, owner_id, version=3)
    # draft → locked es inválido en _VALID_TRANSITIONS
    block_row = _make_block_row(block_pk, ws_id, status="draft", version=5)
    session = _make_session(workspace_row=ws_row, block_rows=[block_row])

    service = WorkspaceAutosaveService(session=session)
    patch = WorkspaceStatePatch(
        expected_workspace_version=3,
        block_updates=[
            BlockUpdate(
                block_id=block_pk,
                state="locked",
                expected_block_version=5,
            )
        ],
    )

    with pytest.raises(InvalidTransitionError) as exc:
        await service.apply_patch(ws_id, str(owner_id), patch)

    assert exc.value.from_status == "draft"
    assert exc.value.to_status == "locked"
    assert exc.value.block_id == block_pk
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_patch_increments_workspace_and_block_versions() -> None:
    owner_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    block_pk_a = uuid.uuid4()
    block_pk_b = uuid.uuid4()

    ws_row = _make_workspace_row(ws_id, owner_id, version=7)
    block_a = _make_block_row(block_pk_a, ws_id, status="needs_review", version=4)
    block_b = _make_block_row(block_pk_b, ws_id, status="needs_review", version=9)
    session = _make_session(workspace_row=ws_row, block_rows=[block_a, block_b])

    service = WorkspaceAutosaveService(session=session)
    patch = WorkspaceStatePatch(
        expected_workspace_version=7,
        block_updates=[
            BlockUpdate(block_id=block_pk_a, state="approved", expected_block_version=4),
            BlockUpdate(block_id=block_pk_b, content={"v": 1}, expected_block_version=9),
        ],
    )

    result = await service.apply_patch(ws_id, str(owner_id), patch)

    assert result.workspace_version == 8
    assert result.updated_block_versions[block_pk_a] == 5
    assert result.updated_block_versions[block_pk_b] == 10


@pytest.mark.asyncio
async def test_patch_is_atomic_on_partial_failure() -> None:
    """Si la segunda transición es inválida, ningún bloque se actualiza y el workspace
    queda en su versión original.
    """
    owner_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    block_pk_a = uuid.uuid4()
    block_pk_b = uuid.uuid4()

    ws_row = _make_workspace_row(ws_id, owner_id, version=3)
    block_a = _make_block_row(block_pk_a, ws_id, status="needs_review", version=5)
    block_b = _make_block_row(block_pk_b, ws_id, status="draft", version=2)  # draft→locked inválido
    session = _make_session(workspace_row=ws_row, block_rows=[block_a, block_b])

    service = WorkspaceAutosaveService(session=session)
    patch = WorkspaceStatePatch(
        expected_workspace_version=3,
        block_updates=[
            BlockUpdate(
                block_id=block_pk_a,
                content={"x": 1},  # update válido
                expected_block_version=5,
            ),
            BlockUpdate(
                block_id=block_pk_b,
                state="locked",  # inválido desde 'draft'
                expected_block_version=2,
            ),
        ],
    )

    with pytest.raises(InvalidTransitionError):
        await service.apply_patch(ws_id, str(owner_id), patch)

    # Ningún bloque mutó ni el workspace incrementó versión
    assert ws_row.version == 3
    assert block_a.version == 5
    assert block_a.content_json is None
    assert block_b.version == 2
    session.commit.assert_not_called()
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_patch_requires_workspace_ownership() -> None:
    owner_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    ws_id = uuid.uuid4()

    ws_row = _make_workspace_row(ws_id, owner_id, version=3)
    session = _make_session(workspace_row=ws_row, block_rows=[])

    service = WorkspaceAutosaveService(session=session)
    patch = WorkspaceStatePatch(expected_workspace_version=3, block_updates=[])

    with pytest.raises(WorkspaceNotFoundError):
        await service.apply_patch(ws_id, str(other_user_id), patch)

    session.commit.assert_not_called()
    session.rollback.assert_awaited_once()

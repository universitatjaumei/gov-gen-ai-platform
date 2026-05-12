"""BlockStateMachine — 9R.3.2.

Máquina de estados de bloque basada en eventos. Cada transición devuelve
un nuevo BlockState (inmutable) y un BlockTransitionAuditEvent para trazabilidad.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel

from server.app.modules.redaccion.contracts.runtime import (
    BlockState,
    InvalidBlockTransitionError,
    _VALID_TRANSITIONS,
)


class BlockTransitionEvent(str, Enum):
    REQUEST_INPUT = "REQUEST_INPUT"
    EXTRACT = "EXTRACT"
    AI_GENERATE = "AI_GENERATE"
    REQUEST_REVIEW = "REQUEST_REVIEW"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REGENERATE = "REGENERATE"
    LOCK = "LOCK"


# Mapping event → target status
_EVENT_TARGET: dict[BlockTransitionEvent, str] = {
    BlockTransitionEvent.REQUEST_INPUT: "missing_input",
    BlockTransitionEvent.EXTRACT: "extracted",
    BlockTransitionEvent.AI_GENERATE: "ai_generated",
    BlockTransitionEvent.REQUEST_REVIEW: "needs_review",
    BlockTransitionEvent.APPROVE: "approved",
    BlockTransitionEvent.REJECT: "rejected",
    BlockTransitionEvent.REGENERATE: "ai_generated",
    BlockTransitionEvent.LOCK: "locked",
}


class BlockTransitionAuditEvent(BaseModel):
    block_id: str
    event: str
    from_status: str
    to_status: str
    timestamp: datetime
    actor: str = "system"
    metadata: dict[str, Any] = {}


class BlockStateMachine:
    def transition(
        self,
        block: BlockState,
        event: BlockTransitionEvent,
        actor: str = "system",
    ) -> tuple[BlockState, BlockTransitionAuditEvent]:
        from_status = block.status
        to_status = _EVENT_TARGET[event]

        allowed = _VALID_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            raise InvalidBlockTransitionError(from_status, to_status)

        new_block = block.model_copy(
            update={"status": to_status, "updated_at": datetime.now(timezone.utc)}
        )
        audit = BlockTransitionAuditEvent(
            block_id=block.block_id,
            event=event.value,
            from_status=from_status,
            to_status=to_status,
            timestamp=datetime.now(timezone.utc),
            actor=actor,
        )
        return new_block, audit


def check_assembly_readiness(
    blocks: dict[str, BlockState],
    contracts: list[Any],
) -> list[str]:
    """Devuelve los IDs de bloques required que no están en approved/locked."""
    blocking: list[str] = []
    for contract in contracts:
        if getattr(contract, "required", False):
            bs = blocks.get(contract.id)
            if bs is None or bs.status not in ("approved", "locked"):
                blocking.append(contract.id)
    return blocking

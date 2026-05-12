"""BlockTopology — 9R.3.3.

Orden topológico de bloques, detección de ciclos y resolución de inputs
proyectados (raw / summary / field) desde block_outputs del WorkspaceState.
"""
from __future__ import annotations

import re
from typing import Any


class UnsafeFieldPathError(ValueError):
    pass


# ---------------------------------------------------------------------------
# safe_field_resolver
# ---------------------------------------------------------------------------

_SAFE_IDENTIFIER_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")
_INDEX_TOKEN_RE = re.compile(r"^\[(\d+)\]$")
_PATH_SPLIT_RE = re.compile(r"(\[\d+\])")


def _tokenize_field_path(path: str) -> list[str]:
    tokens: list[str] = []
    for part in path.split("."):
        for sub in _PATH_SPLIT_RE.split(part):
            if sub:
                tokens.append(sub)
    return tokens


def safe_field_resolver(obj: Any, path: str) -> Any:
    """Resuelve un path dot+index sobre obj. Rechaza expresiones inseguras.

    Valida todos los tokens antes de resolver para evitar accesos parciales.
    """
    tokens = _tokenize_field_path(path)
    # Pre-validate: reject on first unsafe token before touching obj
    for token in tokens:
        if not _SAFE_IDENTIFIER_RE.match(token) and not _INDEX_TOKEN_RE.match(token):
            raise UnsafeFieldPathError(f"Unsafe field path token: {token!r}")
    result = obj
    for token in tokens:
        if _SAFE_IDENTIFIER_RE.match(token):
            if isinstance(result, dict):
                result = result[token]
            else:
                result = getattr(result, token)
        else:
            m = _INDEX_TOKEN_RE.match(token)
            result = result[int(m.group(1))]  # type: ignore[index]
    return result


# ---------------------------------------------------------------------------
# BlockTopology
# ---------------------------------------------------------------------------

class BlockTopology:
    """Operaciones topológicas sobre una lista de BlockContract."""

    def sort(self, blocks: list) -> list:
        """Orden topológico por depends_on (Kahn). Levanta ValueError si hay ciclos."""
        id_to_block = {b.id: b for b in blocks}
        in_degree: dict[str, int] = {b.id: 0 for b in blocks}
        dependents: dict[str, list[str]] = {b.id: [] for b in blocks}

        for block in blocks:
            for ref in block.depends_on:
                if ref.block_id in id_to_block:
                    in_degree[block.id] += 1
                    dependents[ref.block_id].append(block.id)

        queue = sorted(bid for bid, deg in in_degree.items() if deg == 0)
        result: list = []

        while queue:
            bid = queue.pop(0)
            result.append(id_to_block[bid])
            for dep in sorted(dependents[bid]):
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)
                    queue.sort()

        if len(result) != len(blocks):
            raise ValueError("Cycle detected in block depends_on graph")
        return result

    def detect_cycles(self, blocks: list) -> list[str]:
        """DFS con estados white/gray/black. Devuelve IDs de bloques en ciclos."""
        id_to_block = {b.id: b for b in blocks}
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {b.id: WHITE for b in blocks}
        offenders: list[str] = []

        def _dfs(bid: str) -> bool:
            color[bid] = GRAY
            block = id_to_block.get(bid)
            if block is None:
                color[bid] = BLACK
                return False
            for ref in block.depends_on:
                dep_id = ref.block_id
                if dep_id not in color:
                    continue
                if color[dep_id] == GRAY:
                    for node_id in (dep_id, bid):
                        if node_id not in offenders:
                            offenders.append(node_id)
                    return True
                if color[dep_id] == WHITE:
                    if _dfs(dep_id):
                        if bid not in offenders:
                            offenders.append(bid)
                        return True
            color[bid] = BLACK
            return False

        for block in blocks:
            if color[block.id] == WHITE:
                _dfs(block.id)

        return offenders

    def resolve_inputs(self, state: Any, block: Any) -> dict[str, Any]:
        """Aplica projection sobre cada depends_on para construir el contexto del bloque."""
        result: dict[str, Any] = {}
        for ref in block.depends_on:
            output = state.block_outputs.get(ref.block_id, {})
            if ref.projection == "raw":
                result[ref.block_id] = output
            elif ref.projection == "summary":
                if isinstance(output, dict) and "summary" in output:
                    result[ref.block_id] = output["summary"]
                else:
                    result[ref.block_id] = str(output)[:1000]
            elif ref.projection == "field":
                result[ref.block_id] = safe_field_resolver(output, ref.field_path)
        return result

    def check_dependencies_ready(
        self,
        block: Any,
        workspace_state: Any,
        required_statuses: frozenset[str] = frozenset({"approved", "locked"}),
    ) -> list[str]:
        """Devuelve IDs de dependencias cuyo estado no está en required_statuses."""
        blocking: list[str] = []
        for ref in block.depends_on:
            bs = workspace_state.blocks.get(ref.block_id)
            if bs is None or bs.status not in required_statuses:
                blocking.append(ref.block_id)
        return blocking

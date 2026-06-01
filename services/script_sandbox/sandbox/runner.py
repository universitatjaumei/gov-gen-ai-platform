"""Runner de subprocesos con timeout y kill explícito.

REGLA DURA: no confiar en `subprocess.run(timeout=)` por sí solo. Implementamos
`Popen` + `communicate(timeout=)` y, ante un `TimeoutExpired`, llamamos
explícitamente a `proc.kill()` y drenamos los pipes en otra llamada a
`communicate()` para evitar zombies. La excepción `SubprocessTimeoutError`
carga el `Popen` ya terminado para que el caller pueda verificar `poll() != None`.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Sequence


_DEFAULT_STDOUT_CAP_BYTES = 5_000_000  # 5 MB


@dataclass
class SubprocessResult:
    returncode: int
    stdout: str
    stderr: str
    stdout_truncated: bool = False


class SubprocessTimeoutError(Exception):
    """Lanzada cuando el subproceso supera el timeout; carga el `Popen` ya muerto."""

    def __init__(self, process: subprocess.Popen) -> None:
        super().__init__("Subprocess timed out")
        self.process = process


def run_subprocess(
    args: Sequence[str],
    timeout: int,
    *,
    stdout_cap_bytes: int = _DEFAULT_STDOUT_CAP_BYTES,
) -> SubprocessResult:
    """Ejecuta *args* como subproceso hijo; mata y drena en timeout.

    Raises:
        SubprocessTimeoutError: con `.process` (Popen ya matado y reapado).
    """
    proc = subprocess.Popen(
        list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            # Drena los pipes para que el proceso muerto sea reapado y no quede zombie.
            proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        raise SubprocessTimeoutError(proc)

    truncated = False
    if stdout is not None and len(stdout) > stdout_cap_bytes:
        stdout = stdout[:stdout_cap_bytes]
        truncated = True

    return SubprocessResult(
        returncode=proc.returncode if proc.returncode is not None else -1,
        stdout=stdout or "",
        stderr=stderr or "",
        stdout_truncated=truncated,
    )

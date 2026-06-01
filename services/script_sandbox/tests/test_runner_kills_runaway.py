"""Tests del runner: timeout mata el proceso hijo + cada ejecución es fresca."""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path


def test_runner_kills_runaway_subprocess_after_timeout(tmp_path: Path) -> None:
    """Un bucle infinito debe ser matado al exceder el timeout y dejar proc.poll() != None."""
    from sandbox.runner import SubprocessTimeoutError, run_subprocess

    script = tmp_path / "runaway.py"
    script.write_text(textwrap.dedent("""
        import time
        while True:
            time.sleep(0.05)
    """), encoding="utf-8")

    raised = False
    try:
        run_subprocess([sys.executable, str(script)], timeout=1)
    except SubprocessTimeoutError as exc:
        raised = True
        proc = exc.process
        # El proceso ha sido matado: poll() devuelve un código distinto de None.
        assert proc.poll() is not None
    assert raised, "run_subprocess debía lanzar SubprocessTimeoutError"


def test_each_execute_starts_fresh_subprocess(client) -> None:
    """El segundo /execute-extraction no debe ver el estado global del primero."""
    # Primer script: define una variable global "leaked_var".
    resp1 = client.post(
        "/execute-extraction",
        json={
            "code": "leaked_var = 4242\nresult = {'metrics': []}\n",
            "file_path": "",
            "raw_text": "",
            "options": {},
            "timeout_seconds": 30,
        },
    )
    assert resp1.status_code == 200, resp1.text

    # Segundo script: intenta leer "leaked_var". Si los procesos compartieran
    # estado, devolvería 200 con value=4242. Como cada ejecución arranca un
    # subproceso nuevo, debe fallar con NameError → 500 SCRIPT_EXECUTION_ERROR.
    resp2 = client.post(
        "/execute-extraction",
        json={
            "code": "result = {'metrics': [{'name': 'leak', 'value': leaked_var}]}\n",
            "file_path": "",
            "raw_text": "",
            "options": {},
            "timeout_seconds": 30,
        },
    )
    assert resp2.status_code == 500
    body = resp2.json()
    assert body["code"] == "SCRIPT_EXECUTION_ERROR"
    assert "NameError" in body["stderr_truncated"]

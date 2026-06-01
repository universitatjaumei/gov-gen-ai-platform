"""Defensa en profundidad: el sandbox audita aunque el caller dijera estar OK."""
from __future__ import annotations


def test_auditor_blocks_forbidden_import_even_if_caller_pre_audited(client) -> None:
    """El cliente puede equivocarse y mandar código no auditado: el sandbox NO debe ejecutar.

    Un `import os` no está en la lista blanca; aunque el API hubiera fallado
    auditando, el sandbox lo rechaza independientemente.
    """
    code = (
        "import os\n"
        "result = {'metrics': [{'name': 'cwd', 'value': os.getcwd()}]}\n"
    )
    resp = client.post(
        "/execute-extraction",
        json={
            "code": code,
            "file_path": "",
            "raw_text": "",
            "options": {},
            "timeout_seconds": 30,
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "SCRIPT_AUDIT_FAILED"
    assert any("os" in f for f in body["findings"])

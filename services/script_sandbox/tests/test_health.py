"""Smoke test: /health responde 200 con payload mínimo."""
from __future__ import annotations


def test_health_returns_ok(client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") == "healthy"

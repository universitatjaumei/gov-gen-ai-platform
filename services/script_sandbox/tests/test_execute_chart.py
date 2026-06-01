"""Tests del endpoint POST /execute-chart."""
from __future__ import annotations


_VALID_CHART = (
    "import matplotlib.pyplot as plt\n"
    "plt.figure()\n"
    "plt.plot(df['x'], df['y'])\n"
    "plt.title('chart')\n"
)

_DATA_CSV = "x,y\n1,2\n2,4\n3,9\n"


def test_execute_chart_returns_png_bytes_for_valid_script(client) -> None:
    resp = client.post(
        "/execute-chart",
        json={
            "code": _VALID_CHART,
            "data_csv": _DATA_CSV,
            "output_format": "png",
            "timeout_seconds": 30,
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("image/png")
    # PNG magic bytes
    assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_execute_chart_returns_422_for_subprocess_import(client) -> None:
    code = (
        "import subprocess\n"
        "import matplotlib.pyplot as plt\n"
        "plt.figure(); plt.plot(df['x'], df['y'])\n"
    )
    resp = client.post(
        "/execute-chart",
        json={
            "code": code,
            "data_csv": _DATA_CSV,
            "output_format": "png",
            "timeout_seconds": 30,
        },
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "SCRIPT_AUDIT_FAILED"
    assert any("subprocess" in f for f in body["findings"])

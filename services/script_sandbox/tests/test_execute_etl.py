"""Tests del endpoint POST /execute-etl."""
from __future__ import annotations

import io

import pandas as pd


_DATA_CSV = "a,b\n1,10\n2,20\n3,30\n"


def test_execute_etl_returns_csv_for_valid_transform(client) -> None:
    code = (
        "def transform(df):\n"
        "    df = df.copy()\n"
        "    df['c'] = df['a'] + df['b']\n"
        "    return df\n"
    )
    resp = client.post(
        "/execute-etl",
        json={"code": code, "data_csv": _DATA_CSV, "timeout_seconds": 30},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")

    out_df = pd.read_csv(io.StringIO(resp.text))
    assert list(out_df.columns) == ["a", "b", "c"]
    assert list(out_df["c"]) == [11, 22, 33]


def test_execute_etl_returns_422_when_transform_undefined(client) -> None:
    code = "x = 1\ny = x + 2\n"  # no define transform
    resp = client.post(
        "/execute-etl",
        json={"code": code, "data_csv": _DATA_CSV, "timeout_seconds": 30},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "ETL_NO_TRANSFORM"

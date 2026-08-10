from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from app.engines.bi_engine import bi_engine
from app.engines.measure_engine import MeasureEngine
from app.engines.pareto_engine import ParetoEngine
from app.engines.ranking_engine import RankingEngine
from app.main import app

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sales_sample.csv"
client = TestClient(app)


def test_measure_catalog():
    df = pd.read_csv(SAMPLE)
    sem = {"measures": [{"name": "Revenue", "data_type": "currency"}, {"name": "Cost", "data_type": "currency"}]}
    cat = MeasureEngine().catalog(df, sem)
    assert any(m["id"] == "profit" for m in cat)
    assert any(m.get("available") for m in cat if m["id"] == "revenue" or m.get("resolved_source") == "Revenue")


def test_ranking_and_pareto():
    df = pd.read_csv(SAMPLE)
    sem = {"measures": [{"name": "Revenue"}], "dimensions": [{"name": "Product"}]}
    r = RankingEngine().top_n(df, sem, measure="Revenue", group_by="Product", n=5)
    assert r["ok"] and len(r["table"]) <= 5
    p = ParetoEngine().run(df, sem, measure="Revenue", group_by="Product")
    assert p["ok"] and "segment" in p["table"][0]


def test_end_to_end_generate_with_explanation():
    imp = client.post(
        "/api/datasets/import",
        files={"file": ("sales.csv", SAMPLE.read_bytes(), "text/csv")},
        data={"sheets": "Data", "names": "{}"},
    )
    ds = imp.json()["datasets"][0]
    schema = client.get(f"/api/configure/schema?dataset_id={ds['id']}&task_id=analyze").json()
    g = client.post(
        "/api/configure/generate",
        json={
            "dataset_id": ds["id"],
            "task_id": "analyze",
            "configuration": schema["defaults"],
            "save": True,
        },
    )
    assert g.status_code == 200, g.text
    body = g.json()
    assert body["status"] == "completed"
    assert body["result"]["success"] is True
    assert body["result"]["meta"].get("explanation") or body["result"]["meta"].get("calculation_plan")
    assert body["result"]["meta"].get("engines_used")

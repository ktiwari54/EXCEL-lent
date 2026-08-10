from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sales_sample.csv"
client = TestClient(app)


def test_architecture_endpoint():
    r = client.get("/api/process/architecture")
    assert r.status_code == 200
    assert "formula" in r.json()["modules"]


def test_generate_runs_bi_pipeline():
    imp = client.post(
        "/api/datasets/import",
        files={"file": ("sales.csv", SAMPLE.read_bytes(), "text/csv")},
        data={"sheets": "Data", "names": "{}"},
    )
    assert imp.status_code == 200
    ds = imp.json()["datasets"][0]
    schema = client.get(f"/api/configure/schema?dataset_id={ds['id']}&task_id=summarize").json()
    cfg = dict(schema["defaults"])
    g = client.post(
        "/api/configure/generate",
        json={"dataset_id": ds["id"], "task_id": "summarize", "configuration": cfg, "save": True},
    )
    assert g.status_code == 200, g.text
    body = g.json()
    assert body["status"] == "completed"
    assert body["result"]["success"] is True
    assert body["result"]["meta"]["engines_used"]

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sales_sample.csv"
client = TestClient(app)


def _ds():
    r = client.post(
        "/api/datasets/import",
        files={"file": ("sales.csv", SAMPLE.read_bytes(), "text/csv")},
        data={"sheets": "Data", "names": "{}"},
    )
    assert r.status_code == 200
    return r.json()["datasets"][0]


def test_schema_summarize():
    ds = _ds()
    r = client.get(f"/api/configure/schema?dataset_id={ds['id']}&task_id=summarize")
    assert r.status_code == 200
    body = r.json()
    assert body["defaults"].get("measure")
    ids = [f["id"] for f in body["fields"]]
    assert "group_by" in ids
    assert "measure" in ids


def test_validate_and_generate():
    ds = _ds()
    schema = client.get(f"/api/configure/schema?dataset_id={ds['id']}&task_id=calculate").json()
    cfg = dict(schema["defaults"])
    cfg["aggregation"] = "sum"
    v = client.post(
        "/api/configure/validate",
        json={"dataset_id": ds["id"], "task_id": "calculate", "configuration": cfg},
    )
    assert v.status_code == 200
    assert v.json()["valid"] is True

    g = client.post(
        "/api/configure/generate",
        json={
            "dataset_id": ds["id"],
            "task_id": "calculate",
            "configuration": cfg,
            "name": "Total Revenue",
            "save": True,
        },
    )
    assert g.status_code == 200, g.text
    assert g.json()["status"] in ("prepared", "completed")
    assert g.json()["task_request"]["normalized"]["measure"]
    if g.json()["status"] == "completed":
        assert g.json().get("result")
    recent = client.get(f"/api/configure/recent?dataset_id={ds['id']}")
    assert recent.status_code == 200
    assert len(recent.json()["items"]) >= 1

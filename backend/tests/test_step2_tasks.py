from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.modules.task_registry import classify_intent, recommend_tasks

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sales_sample.csv"
client = TestClient(app)


def _import_sample():
    data = SAMPLE.read_bytes()
    r = client.post(
        "/api/datasets/import",
        files={"file": ("sales.csv", data, "text/csv")},
        data={"sheets": "Data", "names": "{}"},
    )
    assert r.status_code == 200, r.text
    return r.json()["datasets"][0]


def test_tasks_list_and_recommendations():
    ds = _import_sample()
    r = client.get(f"/api/tasks?dataset_id={ds['id']}")
    assert r.status_code == 200
    body = r.json()
    assert len(body["tasks"]) >= 10
    assert any(t["id"] == "calculate" for t in body["tasks"])
    assert len(body["recommendations"]) >= 1


def test_intent_duplicates():
    r = classify_intent("find duplicate customers")
    assert r["task_id"] == "find_duplicates"


def test_start_task():
    ds = _import_sample()
    r = client.post(
        "/api/tasks/start",
        json={"dataset_id": ds["id"], "task_id": "analyze"},
    )
    assert r.status_code == 200, r.text
    sel = r.json()["selection"]
    assert sel["task_id"] == "analyze"
    assert sel["stage"] == "configure"
    h = client.get("/api/tasks/history")
    assert h.status_code == 200
    assert len(h.json()["items"]) >= 1

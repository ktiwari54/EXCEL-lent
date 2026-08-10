from fastapi.testclient import TestClient
from app.main import app
from app.modules.task_registry import _profile_facts, evaluate_availability, get_task, list_tasks_for_dataset

c = TestClient(app)
r = c.get("/api/datasets")
datasets = r.json().get("datasets", [])
print("count", len(datasets))
for d in datasets[:5]:
    print("---", d.get("name"), d.get("id")[:8], "rows", d.get("rows"))
    t = c.get(f"/api/tasks?dataset_id={d['id']}")
    body = t.json()
    for x in body.get("tasks", []):
        if x["id"] in ("dashboard", "sales_dashboard", "analyze", "summarize", "calculate", "charts"):
            print(" ", x["id"], x.get("availability"), x.get("availability_reasons"), "can_start", x.get("can_start"))
    ds = c.get(f"/api/datasets/{d['id']}").json()
    roles = [(p["name"], p.get("role"), p.get("data_type"), p.get("is_numeric") if "is_numeric" in p else None) for p in (ds.get("column_profiles") or [])]
    print("  profiles", roles[:12])
    facts = _profile_facts(ds, dataset_count=len(datasets))
    print("  facts", {k: facts[k] for k in ("has_measure", "has_date", "has_dimension", "has_identifier")})
    task = next(x for x in list_tasks_for_dataset(ds, len(datasets)) if x["id"] == "dashboard")
    print("  dashboard eval", task["availability"], task["availability_reasons"])

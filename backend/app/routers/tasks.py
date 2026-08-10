from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.modules.dataset_manager import manager
from app.modules.json_safe import json_safe
from app.modules.task_history import history
from app.modules.task_registry import (
    classify_intent,
    get_task,
    list_tasks_for_dataset,
    recommend_tasks,
    search_tasks,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks-step2"])


def ok(data):
    return JSONResponse(content=json_safe(data))


class IntentBody(BaseModel):
    query: str
    dataset_id: str | None = None


class StartTaskBody(BaseModel):
    dataset_id: str
    task_id: str
    secondary_dataset_ids: list[str] = Field(default_factory=list)
    objective: str | None = None
    notes: str | None = None


@router.get("")
def get_tasks(dataset_id: str | None = None):
    """List tasks with availability for a dataset."""
    dataset_count = len(manager.list_datasets())
    if not dataset_id:
        # generic list without availability
        from app.modules.task_registry import TASK_REGISTRY
        from dataclasses import asdict

        return ok({"tasks": [asdict(t) for t in TASK_REGISTRY], "recommendations": []})
    try:
        ds = manager.get_dataset(dataset_id)
    except KeyError as e:
        raise HTTPException(404, detail={"title": "Dataset not found", "message": str(e)}) from e
    tasks = list_tasks_for_dataset(ds, dataset_count=max(dataset_count, 1))
    recs = recommend_tasks(ds, dataset_count=max(dataset_count, 1))
    return ok({"tasks": tasks, "recommendations": recs, "dataset_id": dataset_id})


@router.get("/search")
def task_search(q: str = Query(""), dataset_id: str | None = None):
    ds = None
    count = len(manager.list_datasets())
    if dataset_id:
        try:
            ds = manager.get_dataset(dataset_id)
        except KeyError:
            ds = None
    return ok({"query": q, "results": search_tasks(q, ds, count)})


@router.post("/intent")
def intent(body: IntentBody):
    result = classify_intent(body.query)
    if body.dataset_id:
        try:
            ds = manager.get_dataset(body.dataset_id)
            tasks = {t["id"]: t for t in list_tasks_for_dataset(ds, len(manager.list_datasets()))}
            tid = result.get("task_id")
            if tid and tid in tasks:
                result["availability"] = tasks[tid].get("availability")
                result["availability_reasons"] = tasks[tid].get("availability_reasons")
                result["can_start"] = tasks[tid].get("can_start")
                result["task"] = tasks[tid]
        except KeyError:
            pass
    return ok(result)


@router.get("/history")
def task_history(limit: int = 20):
    return ok({"items": history.list(limit)})


@router.get("/{task_id}")
def task_detail(task_id: str, dataset_id: str | None = None):
    t = get_task(task_id)
    if not t:
        raise HTTPException(404, detail={"title": "Task not found", "message": task_id})
    if dataset_id:
        try:
            ds = manager.get_dataset(dataset_id)
            evaluated = next(
                (x for x in list_tasks_for_dataset(ds, len(manager.list_datasets())) if x["id"] == task_id),
                None,
            )
            if evaluated:
                t = evaluated
        except KeyError:
            pass
    return ok({"task": t})


@router.post("/start")
def start_task(body: StartTaskBody):
    """
    Persist selection for Step 3 configuration.
    Does not run analysis yet.
    """
    try:
        ds = manager.get_dataset(body.dataset_id)
    except KeyError as e:
        raise HTTPException(404, detail={"title": "Dataset not found", "message": str(e)}) from e

    task = get_task(body.task_id)
    if not task:
        raise HTTPException(404, detail={"title": "Task not found", "message": body.task_id})

    evaluated = next(
        (x for x in list_tasks_for_dataset(ds, len(manager.list_datasets())) if x["id"] == body.task_id),
        None,
    )
    if evaluated and not evaluated.get("can_start", True):
        raise HTTPException(
            400,
            detail={
                "title": "Task not available for this data",
                "message": " ".join(evaluated.get("availability_reasons") or ["Missing required fields."]),
            },
        )

    selection = {
        "dataset_id": body.dataset_id,
        "dataset_name": ds.get("name"),
        "task_id": body.task_id,
        "task_name": task["name"],
        "task_category": task["category"],
        "objective": body.objective or task["name"],
        "secondary_dataset_ids": body.secondary_dataset_ids,
        "detected_fields": {
            "measures": [c["name"] for c in (ds.get("column_profiles") or []) if c.get("role") == "measure"],
            "dimensions": [c["name"] for c in (ds.get("column_profiles") or []) if c.get("role") == "dimension"],
            "dates": [
                c["name"]
                for c in (ds.get("column_profiles") or [])
                if c.get("role") == "date_dimension" or c.get("data_type") in ("date", "datetime")
            ],
        },
        "notes": body.notes,
        "stage": "configure",  # Step 3 placeholder
    }

    entry = history.add(
        dataset_id=body.dataset_id,
        dataset_name=ds.get("name") or "",
        task_id=body.task_id,
        task_name=task["name"],
        category=task["category"],
        configuration=selection,
    )
    selection["history_id"] = entry["id"]
    return ok({"selection": selection, "next": "step3_configure"})

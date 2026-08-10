from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.engines.ai_intent import AIIntentLayer
from app.engines.bi_engine import bi_engine
from app.engines.semantic import SemanticDataLayer
from app.modules.dataset_manager import manager
from app.modules.json_safe import json_safe

router = APIRouter(prefix="/api/process", tags=["process-architecture"])


def ok(data):
    return JSONResponse(content=json_safe(data))


class ProcessBody(BaseModel):
    """Execute a Step-3 Task Request through the BI architecture."""
    task_request: dict = Field(default_factory=dict)
    dataset_id: str | None = None
    secondary_dataset_id: str | None = None


class IntentProcessBody(BaseModel):
    dataset_id: str
    query: str


@router.get("/architecture")
def architecture_map():
    return ok(
        {
            "diagram": [
                "DATA ANALYST ENGINE",
                "  → AI / Intent",
                "  → Semantic Data Layer",
                "  → Business Intelligence Engine",
                "       → Formula | Lookup | Time | Statistics | KPI",
                "  → Insight Engine",
                "  → Result Engine",
            ],
            "modules": {
                "ai_intent": "app.engines.ai_intent",
                "semantic": "app.engines.semantic",
                "bi": "app.engines.bi_engine",
                "formula": "app.engines.formula_engine",
                "lookup": "app.engines.lookup_engine",
                "time": "app.engines.time_engine",
                "statistics": "app.engines.stats_engine",
                "kpi": "app.engines.kpi_engine",
                "insight": "app.engines.insight_engine",
                "result": "app.engines.result_engine",
            },
        }
    )


@router.post("/run")
def process_run(body: ProcessBody):
    tr = body.task_request or {}
    dataset_id = body.dataset_id or tr.get("dataset_id")
    if not dataset_id:
        raise HTTPException(400, detail={"title": "Missing dataset", "message": "dataset_id is required."})
    try:
        ds = manager.get_dataset(dataset_id)
        df = manager.get_raw(dataset_id)
    except KeyError as e:
        raise HTTPException(404, detail={"title": "Dataset not found", "message": str(e)}) from e

    secondary = None
    sec_id = body.secondary_dataset_id or (tr.get("normalized") or {}).get("secondary_dataset_id")
    if sec_id:
        try:
            secondary = manager.get_raw(sec_id)
        except KeyError:
            secondary = None

    # Ensure task_request shape
    if not tr.get("normalized") and tr.get("configuration"):
        from app.modules.config_engine import build_task_request

        tr = build_task_request(
            dataset_id=dataset_id,
            dataset_name=ds.get("name") or "",
            task_id=tr.get("task_id") or "analyze",
            config=tr.get("configuration") or {},
            name=tr.get("name"),
        )

    tr.setdefault("dataset_id", dataset_id)
    tr.setdefault("dataset_name", ds.get("name"))

    result = bi_engine.execute(task_request=tr, dataset=ds, df=df, secondary_df=secondary)
    return ok(result)


@router.post("/intent")
def process_intent(body: IntentProcessBody):
    """AI/Intent → semantic hints (does not run full BI unless client follows with /run)."""
    try:
        ds = manager.get_dataset(body.dataset_id)
        df = manager.get_raw(body.dataset_id)
    except KeyError as e:
        raise HTTPException(404, detail={"title": "Dataset not found", "message": str(e)}) from e
    semantic = SemanticDataLayer().build(ds, df)
    intent = AIIntentLayer().interpret(body.query, semantic)
    return ok({"intent": intent, "semantic_summary": {
        "measures": [m["name"] for m in semantic["measures"]],
        "dimensions": [d["name"] for d in semantic["dimensions"]],
        "dates": [d["name"] for d in semantic["dates"]],
    }})

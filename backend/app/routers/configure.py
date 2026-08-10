from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.modules.config_engine import build_config_schema, build_task_request, validate_config
from app.modules.config_store import config_store
from app.modules.dataset_manager import manager
from app.modules.json_safe import json_safe
from app.modules.task_history import history

router = APIRouter(prefix="/api/configure", tags=["configure-step3"])


def ok(data):
    return JSONResponse(content=json_safe(data))


class ValidateBody(BaseModel):
    dataset_id: str
    task_id: str
    configuration: dict = Field(default_factory=dict)


class SaveBody(BaseModel):
    dataset_id: str
    task_id: str
    configuration: dict = Field(default_factory=dict)
    name: str | None = None


class GenerateBody(BaseModel):
    dataset_id: str
    task_id: str
    configuration: dict = Field(default_factory=dict)
    name: str | None = None
    save: bool = True


@router.get("/schema")
def get_schema(dataset_id: str, task_id: str):
    try:
        ds = manager.get_dataset(dataset_id)
    except KeyError as e:
        raise HTTPException(404, detail={"title": "Dataset not found", "message": str(e)}) from e
    lib = manager.list_datasets()
    schema = build_config_schema(task_id, ds, lib)
    return ok(schema)


@router.post("/validate")
def validate(body: ValidateBody):
    try:
        ds = manager.get_dataset(body.dataset_id)
    except KeyError as e:
        raise HTTPException(404, detail={"title": "Dataset not found", "message": str(e)}) from e
    result = validate_config(body.task_id, body.configuration, ds)
    return ok(result)


@router.post("/save")
def save_config(body: SaveBody):
    try:
        ds = manager.get_dataset(body.dataset_id)
    except KeyError as e:
        raise HTTPException(404, detail={"title": "Dataset not found", "message": str(e)}) from e
    v = validate_config(body.task_id, body.configuration, ds)
    if not v["valid"]:
        raise HTTPException(400, detail={"title": "Configuration incomplete", "message": "; ".join(v["errors"])})
    req = build_task_request(
        dataset_id=body.dataset_id,
        dataset_name=ds.get("name") or "",
        task_id=body.task_id,
        config=body.configuration,
        name=body.name,
    )
    saved = config_store.save(req)
    return ok({"saved": saved})


@router.get("/recent")
def recent_configs(dataset_id: str | None = None, limit: int = 20):
    return ok({"items": config_store.list(limit=limit, dataset_id=dataset_id)})


@router.get("/saved/{config_id}")
def get_saved(config_id: str):
    item = config_store.get(config_id)
    if not item:
        raise HTTPException(404, detail={"title": "Not found", "message": config_id})
    return ok(item)


@router.post("/generate")
def generate(body: GenerateBody):
    """
    Validate + build Task Request + optional save.
    Does NOT run Step 4 calculations — returns ready payload for processing stage.
    """
    try:
        ds = manager.get_dataset(body.dataset_id)
    except KeyError as e:
        raise HTTPException(404, detail={"title": "Dataset not found", "message": str(e)}) from e

    v = validate_config(body.task_id, body.configuration, ds)
    if not v["valid"]:
        raise HTTPException(
            400,
            detail={"title": "Please fix the configuration", "message": " ".join(v["errors"])},
        )

    req = build_task_request(
        dataset_id=body.dataset_id,
        dataset_name=ds.get("name") or "",
        task_id=body.task_id,
        config=body.configuration,
        name=body.name,
    )

    saved = None
    if body.save:
        saved = config_store.save(req)
        req["saved_id"] = saved["id"]

    history.add(
        dataset_id=body.dataset_id,
        dataset_name=ds.get("name") or "",
        task_id=body.task_id,
        task_name=req.get("task_name") or body.task_id,
        category=req.get("task_category") or "",
        configuration=req,
    )

    return ok(
        {
            "status": "prepared",
            "message": "Preparing your analysis…",
            "task_request": req,
            "next": "step4_processing",
            "placeholder": {
                "title": "Preparing your analysis…",
                "body": (
                    "Your configuration is validated and ready. "
                    "The Formula & Calculation Engine (Step 4) will run this Task Request next."
                ),
            },
        }
    )

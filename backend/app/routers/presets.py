from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.engines.bi_engine import bi_engine
from app.modules.config_engine import build_config_schema, build_task_request
from app.modules.dataset_manager import manager
from app.modules.json_safe import json_safe
from app.modules.presets import get_preset, list_presets
from app.modules.task_history import history
from app.services.excel_io import write_analysis_workbook

router = APIRouter(prefix="/api/presets", tags=["presets-one-click"])


def ok(data):
    return JSONResponse(content=json_safe(data))


class OneClickBody(BaseModel):
    dataset_id: str
    preset_id: str


class ExportBody(BaseModel):
    dataset_id: str
    result: dict = Field(default_factory=dict)
    title: str | None = None


@router.get("")
def presets_list():
    return ok({"presets": list_presets()})


@router.post("/run")
def run_preset(body: OneClickBody):
    """One-click: smart defaults + BI pipeline — no manual configuration."""
    preset = get_preset(body.preset_id)
    if not preset:
        raise HTTPException(404, detail={"title": "Preset not found", "message": body.preset_id})

    try:
        ds = manager.get_dataset(body.dataset_id)
        df = manager.get_raw(body.dataset_id)
    except KeyError as e:
        raise HTTPException(404, detail={"title": "Dataset not found", "message": str(e)}) from e

    task_id = preset["task_id"]
    schema = build_config_schema(task_id, ds, manager.list_datasets())
    config = dict(schema.get("defaults") or {})
    config.update(preset.get("config_overrides") or {})

    # Ensure group_by is list when needed
    if isinstance(config.get("group_by"), str) and config["group_by"]:
        config["group_by"] = [config["group_by"]]

    req = build_task_request(
        dataset_id=body.dataset_id,
        dataset_name=ds.get("name") or "",
        task_id=task_id,
        config=config,
        name=preset["name"],
    )
    req["preset_id"] = preset["id"]

    result = bi_engine.execute(task_request=req, dataset=ds, df=df)
    history.add(
        dataset_id=body.dataset_id,
        dataset_name=ds.get("name") or "",
        task_id=task_id,
        task_name=preset["name"],
        category="One-Click",
        configuration=req,
    )

    return ok(
        {
            "status": "completed",
            "preset": preset,
            "task_request": req,
            "result": result,
            "message": f"{preset['name']} ready.",
        }
    )


@router.post("/export")
def export_result(body: ExportBody):
    """Export analysis result + source data to a professional Excel workbook."""
    try:
        df = manager.get_raw(body.dataset_id)
        ds = manager.get_dataset(body.dataset_id)
    except KeyError as e:
        raise HTTPException(404, detail={"title": "Dataset not found", "message": str(e)}) from e

    result = body.result or {}
    tables: dict[str, pd.DataFrame] = {}
    table = result.get("table")
    if isinstance(table, list) and table:
        try:
            tables["Analysis"] = pd.DataFrame(table)
        except Exception:
            pass
    kpis = ((result.get("meta") or {}).get("kpis")) or {}
    if kpis:
        tables["KPIs"] = pd.DataFrame([{"KPI": k, "Value": v} for k, v in kpis.items()])

    insights = list(result.get("insights") or []) + list(result.get("alerts") or []) + list(
        result.get("recommendations") or []
    )
    exp = ((result.get("meta") or {}).get("explanation")) or {}
    if exp:
        insights.append("")
        insights.append("— Calculation explanation —")
        insights.append(str(exp.get("business") or ""))
        insights.append(str(exp.get("logic") or ""))
        if exp.get("excel_equivalent") or (exp.get("mode") or {}).get("technical"):
            insights.append(
                "Technical: " + str(exp.get("excel_equivalent") or (exp.get("mode") or {}).get("technical"))
            )

    settings = get_settings()
    path = settings.exports_dir / f"export_{body.dataset_id[:8]}_{pd.Timestamp.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    write_analysis_workbook(
        path,
        data=df,
        tables=tables or None,
        insights=insights or None,
        title=body.title or result.get("title") or f"Analysis — {ds.get('name')}",
    )
    return FileResponse(
        path,
        filename=f"data_analyst_{ds.get('name', 'export')[:40]}.xlsx".replace(" ", "_"),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

from __future__ import annotations

from typing import Any

from app.modules.json_safe import json_safe


class ResultEngine:
    """Normalize multi-engine output into a single UI-ready payload."""

    def assemble(
        self,
        *,
        task_request: dict[str, Any],
        pieces: list[dict[str, Any]],
        insights: dict[str, Any],
        semantic: dict[str, Any],
    ) -> dict[str, Any]:
        primary = next((p for p in pieces if p.get("ok")), pieces[0] if pieces else {})
        title = f"{task_request.get('task_name') or task_request.get('task_id')} — {semantic.get('dataset_name')}"
        kpis = {}
        for p in pieces:
            if p.get("kpis"):
                kpis.update(p["kpis"])

        chart = primary.get("chart")
        table = primary.get("table") or []
        # merge tables if multiple small
        if not table:
            for p in pieces:
                if p.get("table"):
                    table = p["table"]
                    break

        return json_safe(
            {
                "success": any(p.get("ok") for p in pieces),
                "title": title,
                "summary": primary.get("summary") or insights.get("insights", [""])[0],
                "metric_value": primary.get("metric_value"),
                "table": table if isinstance(table, list) else [],
                "chart": chart,
                "insights": insights.get("insights") or [],
                "alerts": insights.get("alerts") or [],
                "recommendations": insights.get("recommendations") or [],
                "meta": {
                    "architecture": "ai→semantic→bi→specialists→insight→result",
                    "task_request": {
                        "task_id": task_request.get("task_id"),
                        "output_type": task_request.get("output_type"),
                        "normalized": task_request.get("normalized"),
                    },
                    "semantic": {
                        "measures": [m["name"] for m in (semantic.get("measures") or [])],
                        "dimensions": [d["name"] for d in (semantic.get("dimensions") or [])],
                        "dates": [d["name"] for d in (semantic.get("dates") or [])],
                    },
                    "kpis": kpis,
                    "engines_used": [p.get("engine") for p in pieces if p.get("engine")],
                    "charts": [p["chart"] for p in pieces if p.get("chart")],
                },
            }
        )
